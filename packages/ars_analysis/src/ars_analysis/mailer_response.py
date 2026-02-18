"""
mailer_response.py — A13+A14 Mailer Response & Demographics Analysis
=====================================================================
Per-month combined slides (one per mail month):
  Title: "{Mmm YYYY} Mailer Summary"
  Layout: 3-column
    Col 1: Donut chart (response share by segment)
    Col 2: Bar chart (response rates by segment)
    Col 3: Stacked text insights (up to 3)

Plus supplemental outputs:
  All-Time Mailer Summary (same 3-column layout, all months combined)
  Response Rate Trend (line chart, if 2+ months)
  Responder Account Age Distribution (A14.2)
  Response Count Matrix (Excel-only)

Column patterns:
  MmmYY Mail — mail segment (NU, TH-10, TH-15, TH-20, TH-25)
  MmmYY Resp — response code (NU 5+, NU 1-4, TH-10..TH-25)

Usage:
    from mailer_response import run_mailer_response_suite
    ctx = run_mailer_response_suite(ctx)
"""

import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from datetime import datetime

from ars_analysis.mailer_common import (
    RESPONSE_SEGMENTS, TH_SEGMENTS, MAILED_SEGMENTS,
    report as _report, save_chart as _save_chart, slide as _slide,
    save_to_excel as _save, parse_month as _parse_month,
    discover_pairs as _discover_pairs,
)

# =============================================================================
# MODULE-SPECIFIC CONSTANTS
# =============================================================================

SEGMENT_COLORS = {
    'NU 5+': '#E74C3C', 'NU': '#E74C3C',
    'TH-10': '#3498DB', 'TH-15': '#2ECC71',
    'TH-20': '#F39C12', 'TH-25': '#9B59B6',
}
BAR_COLORS = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6']

VALID_RESPONSES = {
    'NU': ['NU 5+'],
    'TH-10': ['TH-10'],
    'TH-15': ['TH-15'],
    'TH-20': ['TH-20'],
    'TH-25': ['TH-25'],
}

AGE_SEGMENTS = [
    ('< 2 years', 0, 2),
    ('2-5 years', 2, 5),
    ('5-10 years', 5, 10),
    ('10-20 years', 10, 20),
    ('> 20 years', 20, 999),
]


# =============================================================================
# MODULE-SPECIFIC HELPERS
# =============================================================================

def _format_title(month_str):
    """Convert 'Aug25' -> 'August 2025'."""
    try:
        dt = pd.to_datetime(month_str, format='%b%y')
        return dt.strftime('%B %Y')
    except Exception:
        return month_str


# =============================================================================
# SINGLE-MONTH ANALYSIS — compute segment stats
# =============================================================================

def _analyze_month(data, resp_col, mail_col):
    """
    Compute response stats for one mail month.
    Returns dict keyed by display segment (NU 5+, TH-10, etc.) with
    {mailed, responders, rate}.
    """
    seg_details = {}
    for seg in MAILED_SEGMENTS:
        seg_data = data[data[mail_col] == seg]
        n_mailed = len(seg_data)
        if n_mailed == 0:
            continue
        valid = VALID_RESPONSES[seg]
        n_resp = len(seg_data[seg_data[resp_col].isin(valid)])
        rate = n_resp / n_mailed * 100 if n_mailed > 0 else 0
        display = 'NU 5+' if seg == 'NU' else seg
        seg_details[display] = {'mailed': n_mailed, 'responders': n_resp, 'rate': rate}

    total_mailed = sum(d['mailed'] for d in seg_details.values())
    total_resp = sum(d['responders'] for d in seg_details.values())
    overall_rate = total_resp / total_mailed * 100 if total_mailed > 0 else 0

    return seg_details, total_mailed, total_resp, overall_rate


# =============================================================================
# BUILD INSIGHTS TEXT — for the right-hand column
# =============================================================================

def _build_insights(ctx, data, resp_col, seg_details,
                    total_mailed, total_resp, overall_rate):
    """Build insight strings for the text panel."""
    ins = []

    ins.append(f"Total Sent: {total_mailed:,}")
    ins.append(f"Total Response: {total_resp:,}")
    ins.append(f"Response Rate: {overall_rate:.2f}%")

    # Accounts under 2 years
    if 'Date Opened' in data.columns:
        responders = data[data[resp_col].isin(RESPONSE_SEGMENTS)]
        if len(responders) > 0:
            do = pd.to_datetime(responders['Date Opened'], errors='coerce')
            age = (pd.Timestamp.now() - do).dt.days / 365.25
            under_2 = int((age < 2).sum())
            ins.append(f"Accounts Under 2 Years: {under_2:,}")

    return ins


# =============================================================================
# COMPUTE "INSIDE THE NUMBERS" METRICS
# =============================================================================

def _compute_inside_numbers(ctx, data, resp_col):
    """
    Compute percentage metrics for the 'Inside the Numbers' panel.
    Returns list of (pct_string, description) tuples.
    """
    metrics = []
    responders = data[data[resp_col].isin(RESPONSE_SEGMENTS)]
    n_resp = len(responders)
    if n_resp == 0:
        return metrics

    # % of responders with accounts opened < 2 years ago
    if 'Date Opened' in data.columns:
        do = pd.to_datetime(responders['Date Opened'], errors='coerce')
        age_years = (pd.Timestamp.now() - do).dt.days / 365.25
        under_2 = int((age_years < 2).sum())
        pct = under_2 / n_resp * 100
        metrics.append((f"{pct:.0f}%", "of Responders were accounts opened fewer than 2 years ago"))

    # % of responders opted into Reg E
    reg_e_col = ctx.get('latest_reg_e_column')
    if reg_e_col and reg_e_col in data.columns:
        opted_in = responders[reg_e_col].astype(str).str.strip().str.upper()
        n_opted = int(opted_in.isin(['Y', 'YES', '1']).sum())
        pct = n_opted / n_resp * 100
        metrics.append((f"{pct:.0f}%", "of Responders opted into Reg E"))

    return metrics


# =============================================================================
# RENDER STANDALONE DONUT CHART — Response Share
# =============================================================================

def _render_donut_chart(seg_details, chart_path, month_title=None):
    """
    Render standalone donut chart showing response share by segment.
    Returns saved chart path or None.
    """
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return None

    resp_counts = [seg_details[s]['responders'] for s in active]
    colors = [SEGMENT_COLORS.get(s, '#888') for s in active]
    total = sum(resp_counts)

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor('white')

    if total > 0:
        wedges, texts, autotexts = ax.pie(
            resp_counts, labels=active, autopct='%1.0f%%',
            colors=colors, startangle=90, pctdistance=0.78,
            textprops={'fontsize': 18, 'fontweight': 'bold'})
        for at in autotexts:
            at.set_fontsize(16)
            at.set_fontweight('bold')
        centre = plt.Circle((0, 0), 0.50, fc='white')
        ax.add_artist(centre)
        ax.text(0, 0.06, 'Total', ha='center', va='center',
                fontsize=18, fontweight='bold', color='#555')
        ax.text(0, -0.12, f'{total:,}', ha='center', va='center',
                fontsize=28, fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No Responders', ha='center', va='center',
                fontsize=16, transform=ax.transAxes)
        ax.axis('off')

    plt.tight_layout()
    _save_chart(fig, chart_path)
    return str(chart_path)


# =============================================================================
# RENDER STANDALONE HORIZONTAL BAR CHART — Response Rates
# =============================================================================

def _render_hbar_chart(seg_details, month_title, chart_path):
    """
    Render horizontal bar chart with count/total inside bars and % labels.
    Sized to fit in a ~4" column on the mailer summary slide.
    Returns saved chart path or None.
    """
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return None

    rates = [seg_details[s]['rate'] for s in active]
    resp_counts = [seg_details[s]['responders'] for s in active]
    mailed_counts = [seg_details[s]['mailed'] for s in active]
    colors = [SEGMENT_COLORS.get(s, '#888') for s in active]

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor('white')

    y = np.arange(len(active))
    bars = ax.barh(y, rates, color=colors, edgecolor='none',
                   height=0.65, alpha=0.90)

    # Labels inside and outside bars
    max_rate = max(rates) if rates else 1
    for bar, rate, resp, mailed in zip(bars, rates, resp_counts, mailed_counts):
        count_label = f'{resp}/{mailed}'
        pct_label = f'{rate:.1f}%'
        bar_cy = bar.get_y() + bar.get_height() / 2

        if bar.get_width() > max_rate * 0.25:
            # Count inside bar, percentage just outside
            ax.text(bar.get_width() * 0.5, bar_cy,
                    count_label, ha='center', va='center',
                    fontsize=18, fontweight='bold', color='white')
            ax.text(bar.get_width() + max_rate * 0.02, bar_cy,
                    pct_label, ha='left', va='center',
                    fontsize=18, fontweight='bold')
        else:
            # Small bar — stack count above, pct below to stay legible
            x_off = bar.get_width() + max_rate * 0.02
            ax.text(x_off, bar_cy,
                    count_label, ha='left', va='bottom',
                    fontsize=13, fontweight='bold', color='#333')
            ax.text(x_off, bar_cy,
                    pct_label, ha='left', va='top',
                    fontsize=14, fontweight='bold', color='#333')

    ax.set_yticks(y)
    ax.set_yticklabels(active, fontsize=18, fontweight='bold')
    ax.set_xlabel('Response Rate (%)', fontsize=18, fontweight='bold')
    ax.set_xlim(0, max_rate * 1.45 if max_rate > 0 else 1)
    ax.invert_yaxis()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='x', labelsize=15)

    plt.tight_layout()
    _save_chart(fig, chart_path)
    return str(chart_path)


# =============================================================================
# RENDER 3-COLUMN SUMMARY FIGURE — Donut | Bar | Insights  (LEGACY)
# =============================================================================

def _render_3col(seg_details, insights, title, chart_path):
    """
    Single figure: Donut (share) | Bar (rates) | Text insights.
    Returns saved chart path or None.
    """
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return None

    fig = plt.figure(figsize=(22, 10))
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.30)

    resp_counts = [seg_details[s]['responders'] for s in active]
    rates = [seg_details[s]['rate'] for s in active]
    volumes = [seg_details[s]['mailed'] for s in active]
    colors = [SEGMENT_COLORS.get(s, '#888') for s in active]
    total = sum(resp_counts)

    # ── COL 1: DONUT ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    if total > 0:
        wedges, texts, autotexts = ax1.pie(
            resp_counts, labels=active, autopct='%1.1f%%',
            colors=colors, startangle=90, pctdistance=0.78,
            textprops={'fontsize': 14, 'fontweight': 'bold'})
        for at in autotexts:
            at.set_fontsize(13)
            at.set_fontweight('bold')
        centre = plt.Circle((0, 0), 0.50, fc='white')
        ax1.add_artist(centre)
        ax1.text(0, 0, f'{total:,}\nTotal', ha='center', va='center',
                 fontsize=16, fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'No Responders', ha='center', va='center',
                 fontsize=16, transform=ax1.transAxes)
        ax1.axis('off')
    ax1.set_title('Response Share', fontsize=18, fontweight='bold', pad=15)

    # ── COL 2: BAR ────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    x = np.arange(len(active))
    bars = ax2.bar(x, rates, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
    for bar, rate, vol in zip(bars, rates, volumes):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f'{rate:.1f}%', ha='center', va='bottom',
                 fontsize=14, fontweight='bold')
        if bar.get_height() > 0:
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                     f'{vol:,}\nmailed', ha='center', va='center',
                     fontsize=11, color='white', fontweight='bold')

    ax2.set_xticks(x)
    ax2.set_xticklabels(active, fontsize=13, fontweight='bold')
    ax2.set_ylabel('Response Rate (%)', fontsize=14, fontweight='bold')
    ax2.set_title('Response Rate', fontsize=18, fontweight='bold', pad=15)
    ax2.tick_params(axis='y', labelsize=12)
    if rates:
        ax2.set_ylim(0, max(rates) * 1.30)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # ── COL 3: TEXT INSIGHTS ──────────────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    ax3.axis('off')
    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)

    # Background box
    rect = mpatches.FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                          boxstyle='round,pad=0.03',
                          facecolor='#F8F9FA', edgecolor='#BDC3C7', linewidth=2)
    ax3.add_patch(rect)

    ax3.text(0.50, 0.93, 'Key Insights', ha='center', va='top',
             fontsize=18, fontweight='bold')

    y = 0.83
    spacing = 0.085
    for i, txt in enumerate(insights[:8]):
        ax3.text(0.08, y - i * spacing, f"• {txt}",
                 ha='left', va='top', fontsize=13, wrap=True)

    # Title
    fig.suptitle(title, fontsize=24, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.93])

    _save_chart(fig, chart_path)
    return str(chart_path)


# =============================================================================
# PER-MONTH COMBINED SLIDES  (core deliverable)
# =============================================================================

def run_monthly_summaries(ctx):
    """One composite summary slide per mail month."""
    _report(ctx, "\n📊 Generating per-month Mailer Summary slides...")
    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   ⚠️ No mailer data — skipping")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']
    all_results = {}
    prev_resp = None  # for comparison insight

    for month, resp_col, mail_col in pairs:
        _report(ctx, f"   📅 {month}")

        seg_details, total_mailed, total_resp, overall_rate = \
            _analyze_month(data, resp_col, mail_col)

        if not seg_details:
            _report(ctx, f"      ⚠️ No data for {month}")
            continue

        month_title = _format_title(month)
        title = f"ARS Response – {month} Mailer Summary"

        # Render separate charts
        donut_path = chart_dir / f'a13_{month.lower()}_donut.png'
        hbar_path = chart_dir / f'a13_{month.lower()}_hbar.png'

        dp = _render_donut_chart(seg_details, donut_path, month_title=month)
        hp = _render_hbar_chart(seg_details, month, hbar_path)

        if not dp or not hp:
            _report(ctx, f"      ⚠️ Chart render failed for {month}")
            continue

        # Compute "Inside the Numbers" metrics
        inside_numbers = _compute_inside_numbers(ctx, data, resp_col)

        # Build comparison insight text (avoid repeating KPI stats)
        if prev_resp is not None and prev_resp > 0:
            change_pct = (total_resp - prev_resp) / prev_resp * 100
            direction = "increase" if change_pct > 0 else "decrease"
            insight_text = (f"{abs(change_pct):.0f}% {direction} in "
                           f"responses vs. prior mailer.")
        else:
            insight_text = f"Baseline campaign — first mailer in series."

        # KPIs
        kpis = {
            'Mail pieces sent': f'{total_mailed:,}',
            'Respondents': f'{total_resp:,}',
            'Total Response Rate': f'{overall_rate:.0f}%',
        }

        _slide(ctx, f'A13 - {month} Mailer Summary', {
            'title': title,
            'slide_type': 'mailer_summary',
            'layout_index': 13,
            'donut_path': dp,
            'hbar_path': hp,
            'kpis': kpis,
            'inside_numbers': inside_numbers,
            'insight_text': insight_text,
            'category': 'Mailer',
        })
        _report(ctx, f"      ✅ {title}")

        prev_resp = total_resp

        all_results[month] = {
            'seg_details': seg_details, 'total_mailed': total_mailed,
            'total_resp': total_resp, 'overall_rate': overall_rate,
        }

        # Per-month Excel
        rows = [{'Segment': s, 'Mailed': d['mailed'], 'Responders': d['responders'],
                 'Rate %': round(d['rate'], 2)} for s, d in seg_details.items()]
        _save(ctx, pd.DataFrame(rows), f'A13-{month}',
              f'{_format_title(month)} Mailer Response',
              {'Total Mailed': f'{total_mailed:,}',
               'Responders': f'{total_resp:,}',
               'Rate': f'{overall_rate:.2f}%'})

    ctx['results']['monthly_summaries'] = all_results
    return ctx


# =============================================================================
# ALL-TIME AGGREGATE SLIDE  (same 3-column layout)
# =============================================================================

def run_aggregate_summary(ctx):
    """Single all-time aggregate slide using composite layout."""
    _report(ctx, "\n📊 Generating All-Time Mailer Summary...")
    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   ⚠️ No mailer data"); return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']

    # Combine across all months
    combined = {}
    for month, resp_col, mail_col in pairs:
        seg_d, _, _, _ = _analyze_month(data, resp_col, mail_col)
        for seg, stats in seg_d.items():
            if seg not in combined:
                combined[seg] = {'mailed': 0, 'responders': 0}
            combined[seg]['mailed'] += stats['mailed']
            combined[seg]['responders'] += stats['responders']

    for seg in combined:
        m = combined[seg]['mailed']
        combined[seg]['rate'] = combined[seg]['responders'] / m * 100 if m > 0 else 0

    total_m = sum(d['mailed'] for d in combined.values())
    total_r = sum(d['responders'] for d in combined.values())
    overall = total_r / total_m * 100 if total_m > 0 else 0

    title = "ARS Response – All-Time Mailer Summary"

    # Render separate charts
    donut_path = chart_dir / 'a13_aggregate_donut.png'
    hbar_path = chart_dir / 'a13_aggregate_hbar.png'

    dp = _render_donut_chart(combined, donut_path, month_title='All-Time')
    hp = _render_hbar_chart(combined, 'All-Time', hbar_path)

    if dp and hp:
        # Compute inside numbers from all resp columns combined
        inside_numbers = []
        if 'Date Opened' in data.columns:
            all_resp_mask = pd.Series(False, index=data.index)
            for month, resp_col, mail_col in pairs:
                all_resp_mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
            responders = data[all_resp_mask]
            n_resp = len(responders)
            if n_resp > 0:
                do = pd.to_datetime(responders['Date Opened'], errors='coerce')
                age_years = (pd.Timestamp.now() - do).dt.days / 365.25
                under_2 = int((age_years < 2).sum())
                pct = under_2 / n_resp * 100
                inside_numbers.append((f"{pct:.0f}%", "of Responders were accounts opened fewer than 2 years ago"))

                reg_e_col = ctx.get('latest_reg_e_column')
                if reg_e_col and reg_e_col in data.columns:
                    opted_in = responders[reg_e_col].astype(str).str.strip().str.upper()
                    n_opted = int(opted_in.isin(['Y', 'YES', '1']).sum())
                    pct_re = n_opted / n_resp * 100
                    inside_numbers.append((f"{pct_re:.0f}%", "of Responders opted into Reg E"))

        kpis = {
            'Mail pieces sent': f'{total_m:,}',
            'Respondents': f'{total_r:,}',
            'Total Response Rate': f'{overall:.0f}%',
        }

        insight_text = f"{len(pairs)} campaigns analyzed across all mailer periods."

        _slide(ctx, 'A13 - All-Time Mailer Summary', {
            'title': title,
            'slide_type': 'mailer_summary',
            'layout_index': 13,
            'donut_path': dp,
            'hbar_path': hp,
            'kpis': kpis,
            'inside_numbers': inside_numbers,
            'insight_text': insight_text,
            'category': 'Mailer',
        })
        _report(ctx, f"   ✅ {title}")

    rows = [{'Segment': s, 'Total Mailed': d['mailed'],
             'Total Responders': d['responders'], 'Rate %': round(d['rate'], 2)}
            for s, d in combined.items()]
    _save(ctx, pd.DataFrame(rows), 'A13-AllTime', 'All-Time Mailer Summary',
          {'Campaigns': str(len(pairs)), 'Overall Rate': f'{overall:.2f}%'})

    ctx['results']['aggregate_summary'] = {
        'combined': combined, 'total_mailed': total_m,
        'total_resp': total_r, 'overall_rate': overall,
    }
    return ctx


# =============================================================================
# A13.6 — RESPONSE RATE TREND  (line chart, 2+ months)
# =============================================================================

def run_rate_trend(ctx):
    """Response rate trend across months per campaign type."""
    _report(ctx, "\n📊 A13.6 — Response Rate Trend")
    pairs = _discover_pairs(ctx)
    if len(pairs) < 2:
        _report(ctx, "   ⚠️ Need 2+ months for trend — skipping")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']

    months = []
    trend = {seg: [] for seg in MAILED_SEGMENTS}

    for month, resp_col, mail_col in pairs:
        months.append(month)
        for seg in MAILED_SEGMENTS:
            seg_data = data[data[mail_col] == seg]
            n = len(seg_data)
            valid = VALID_RESPONSES[seg]
            r = len(seg_data[seg_data[resp_col].isin(valid)])
            trend[seg].append(r / n * 100 if n > 0 else 0)

    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor('white')
        x = np.arange(len(months))

        for seg in MAILED_SEGMENTS:
            if trend[seg] and len(trend[seg]) == len(months):
                color = SEGMENT_COLORS.get(seg, '#888')
                label = 'NU 5+' if seg == 'NU' else seg
                ax.plot(x, trend[seg], marker='o', color=color,
                        linewidth=2.5, markersize=8, label=label)

        ax.set_xticks(x)
        ax.set_xticklabels(months, fontsize=16, fontweight='bold',
                           rotation=45, ha='right')
        ax.set_ylabel('Response Rate (%)', fontsize=16, fontweight='bold')
        ax.set_title('Response Rate Trend by Campaign', fontsize=20, fontweight='bold')
        ax.tick_params(axis='y', labelsize=14)
        ax.legend(fontsize=14)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'a13_6_rate_trend.png')

        _slide(ctx, 'A13.6 - Response Rate Trend', {
            'title': 'Response Rate Trend by Campaign',
            'subtitle': f'{len(months)} months tracked',
            'layout_index': 9, 'chart_path': cp,
            'insights': [f"{'NU 5+' if s == 'NU' else s}: {trend[s][-1]:.1f}% (latest)"
                         for s in MAILED_SEGMENTS if trend.get(s)],
            'category': 'Mailer',
        })
        _report(ctx, f"   ✅ Rate trend — {len(months)} months")
    except Exception as e:
        _report(ctx, f"   ⚠️ A13.6 chart: {e}")

    ctx['results']['rate_trend'] = trend
    return ctx


# =============================================================================
# A13.5 — RESPONDER COUNT TREND  (stacked bar, 2+ months)
# =============================================================================

def run_count_trend(ctx):
    """Stacked bar chart of responder counts per month by segment."""
    _report(ctx, "\n📊 A13.5 — Responder Count Trend")
    pairs = _discover_pairs(ctx)
    if len(pairs) < 2:
        _report(ctx, "   ⚠️ Need 2+ months for trend — skipping")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']

    months = []
    counts = {seg: [] for seg in MAILED_SEGMENTS}
    totals = []

    for month, resp_col, mail_col in pairs:
        months.append(month)
        month_total = 0
        for seg in MAILED_SEGMENTS:
            seg_data = data[data[mail_col] == seg]
            valid = VALID_RESPONSES[seg]
            n_resp = len(seg_data[seg_data[resp_col].isin(valid)])
            counts[seg].append(n_resp)
            month_total += n_resp
        totals.append(month_total)

    # Generate dynamic insight title: rank the latest month
    latest_total = totals[-1]
    sorted_totals = sorted(totals, reverse=True)
    rank = sorted_totals.index(latest_total) + 1
    ordinal = {1: 'highest', 2: '2nd highest', 3: '3rd highest'}
    rank_str = ordinal.get(rank, f'{rank}th highest')

    # Find the month where high counts started for "since" phrasing
    if len(months) > 2:
        mid = len(months) // 2
        since_month = months[mid]
        title = f"Our {rank_str} response since {since_month}"
    else:
        title = f"Our {rank_str} response"

    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor('white')
        x = np.arange(len(months))
        bar_width = 0.6

        bottom = np.zeros(len(months))
        display_segs = []
        for seg in MAILED_SEGMENTS:
            if any(c > 0 for c in counts[seg]):
                label = 'NU 5+' if seg == 'NU' else seg
                color = SEGMENT_COLORS.get(seg, '#888')
                ax.bar(x, counts[seg], bar_width, bottom=bottom,
                       color=color, edgecolor='white', linewidth=0.5,
                       label=label)
                bottom += np.array(counts[seg])
                display_segs.append(label)

        # Category count labels centered inside each bar segment
        bottom_labels = np.zeros(len(months))
        for seg in MAILED_SEGMENTS:
            if any(c > 0 for c in counts[seg]):
                for i, val in enumerate(counts[seg]):
                    if val > 0:
                        y_center = bottom_labels[i] + val / 2
                        ax.text(i, y_center, f'{val:,}',
                                ha='center', va='center',
                                fontsize=9, fontweight='bold', color='white')
                bottom_labels += np.array(counts[seg])

        # Total labels above each bar
        for i, total in enumerate(totals):
            ax.text(i, total + max(totals) * 0.01, f'Total: {total:,}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(months, fontsize=14, fontweight='bold',
                           rotation=45, ha='right')
        ax.set_ylabel('Count of Responders', fontsize=16, fontweight='bold')
        ax.tick_params(axis='y', labelsize=14)
        ax.legend(fontsize=12, loc='upper left')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_ylim(0, max(totals) * 1.12)

        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'a13_5_count_trend.png')

        _slide(ctx, 'A13.5 - Responder Count Trend', {
            'title': title,
            'subtitle': 'Responder Counts by Month and Category',
            'layout_index': 13, 'chart_path': cp,
            'insights': [f"Latest: {latest_total:,} responders",
                         f"Rank: {rank_str} of {len(months)} months"],
            'category': 'Mailer',
        })
        _report(ctx, f"   ✅ Count trend — {len(months)} months, latest rank: {rank_str}")
    except Exception as e:
        _report(ctx, f"   ⚠️ A13.5 chart: {e}")

    return ctx


# =============================================================================
# A14.2 — RESPONDER ACCOUNT AGE DISTRIBUTION
# =============================================================================

def run_account_age(ctx):
    """Responder distribution by account age across all mail months."""
    _report(ctx, "\n📊 A14.2 — Responder Account Age Distribution")
    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   ⚠️ No mailer data"); return ctx

    data = ctx['data'].copy()
    chart_dir = ctx['chart_dir']

    data['Date Opened'] = pd.to_datetime(data['Date Opened'], errors='coerce')
    data['_age'] = (pd.Timestamp.now() - data['Date Opened']).dt.days / 365.25

    all_rows = []
    for month, resp_col, mail_col in pairs:
        resp = data[data[resp_col].isin(RESPONSE_SEGMENTS)]
        if resp.empty:
            continue
        counts = {'Month': month, 'Total Responders': len(resp)}
        for lbl, lo, hi in AGE_SEGMENTS:
            counts[lbl] = int(((resp['_age'] >= lo) & (resp['_age'] < hi)).sum())
        all_rows.append(counts)

    if not all_rows:
        _report(ctx, "   ⚠️ No responders with valid dates"); return ctx

    age_df = pd.DataFrame(all_rows).set_index('Month')
    labels = [s[0] for s in AGE_SEGMENTS]
    totals = {l: int(age_df[l].sum()) for l in labels if l in age_df.columns}
    grand = sum(totals.values())
    pcts = {k: v / grand * 100 if grand > 0 else 0 for k, v in totals.items()}

    largest = max(pcts, key=pcts.get) if pcts else 'N/A'

    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor('white')
        lbl_list = list(totals.keys())
        cts = [totals[l] for l in lbl_list]
        ps = [pcts[l] for l in lbl_list]
        x = np.arange(len(lbl_list))

        bars = ax.bar(x, cts, color=BAR_COLORS[:len(lbl_list)],
                      edgecolor='black', linewidth=2, alpha=0.8)
        for bar, ct, pct in zip(bars, cts, ps):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(cts) * 0.02,
                    f'{pct:.1f}%', ha='center', va='bottom',
                    fontsize=16, fontweight='bold')
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() / 2,
                    f'{ct:,}', ha='center', va='center',
                    fontsize=14, color='white', fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(lbl_list, fontsize=16, fontweight='bold')
        ax.set_ylabel('Number of Responders', fontsize=16, fontweight='bold')
        ax.set_title('Responder Distribution by Account Age',
                     fontsize=20, fontweight='bold')
        ax.tick_params(axis='y', labelsize=14)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'a14_2_account_age.png')

        new_ct = totals.get('< 2 years', 0) + totals.get('2-5 years', 0)
        est_ct = totals.get('10-20 years', 0) + totals.get('> 20 years', 0)
        subtitle = f"{largest} dominates at {pcts[largest]:.0f}% — {grand:,} responders"
        ins = [f"Total: {grand:,}", f"Campaigns: {len(all_rows)} months",
               f"New (<5yr): {new_ct:,} ({new_ct / grand * 100:.1f}%)" if grand else '',
               f"Established (10+yr): {est_ct:,} ({est_ct / grand * 100:.1f}%)" if grand else '']
        ins = [i for i in ins if i]

        _slide(ctx, 'A14.2 - Responder Account Age', {
            'title': 'Responder Account Age Distribution',
            'subtitle': subtitle, 'layout_index': 9,
            'chart_path': cp, 'insights': ins, 'category': 'Mailer',
        })
        _report(ctx, f"   ✅ Account age — {grand:,} responders")
    except Exception as e:
        _report(ctx, f"   ⚠️ A14.2 chart: {e}")

    _save(ctx, age_df.reset_index(), 'A14.2-ResponderAge',
          'Responder Account Age Distribution',
          {'Total': f'{grand:,}', 'Dominant': f'{largest} ({pcts[largest]:.0f}%)'})

    ctx['results']['account_age'] = {'age_df': age_df, 'totals': totals}
    return ctx


# =============================================================================
# RESPONSE COUNT MATRIX — Excel-only
# =============================================================================

def run_count_matrix(ctx):
    """Export month × segment response count matrix to Excel."""
    _report(ctx, "\n📊 Exporting Response Count Matrix...")
    pairs = _discover_pairs(ctx)
    if not pairs:
        return ctx

    data = ctx['data']
    ctypes = ['NU 5+'] + TH_SEGMENTS
    rows = []
    for month, resp_col, mail_col in pairs:
        row = {'Month': month}
        for ct in ctypes:
            row[ct] = len(data[data[resp_col] == ct])
        row['Total'] = sum(row[ct] for ct in ctypes)
        rows.append(row)

    if rows:
        df = pd.DataFrame(rows)
        totals = df[ctypes + ['Total']].sum()
        totals['Month'] = 'TOTAL'
        df = pd.concat([df, totals.to_frame().T], ignore_index=True)
        _save(ctx, df, 'A13-CountMatrix', 'Response Count Matrix',
              {'Months': str(len(pairs)), 'Total': f"{int(totals['Total']):,}"})
        _report(ctx, f"   ✅ Count matrix — {len(pairs)} months")

    return ctx


# =============================================================================
# SUITE RUNNER
# =============================================================================

def run_mailer_response_suite(ctx):
    """Run the full A13+A14 Mailer Response & Demographics suite."""
    from ars_analysis.pipeline import save_to_excel
    ctx['_save_to_excel'] = save_to_excel

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "📧 A13+A14 — MAILER RESPONSE & DEMOGRAPHICS")
    _report(ctx, "=" * 60)

    def _safe(fn, label):
        try:
            return fn(ctx)
        except Exception as e:
            _report(ctx, f"   ⚠️ {label} failed: {e}")
            import traceback
            traceback.print_exc()
            return ctx

    # Core: one 3-column slide per month
    ctx = _safe(run_monthly_summaries, 'Per-Month Summaries')

    # All-time aggregate (same layout)
    ctx = _safe(run_aggregate_summary, 'All-Time Summary')

    # Responder count stacked bar (if 2+ months)
    ctx = _safe(run_count_trend, 'Count Trend')

    # Account age distribution
    ctx = _safe(run_account_age, 'Account Age')

    # Count matrix (Excel only)
    ctx = _safe(run_count_matrix, 'Count Matrix')

    slides = len([s for s in ctx['all_slides'] if s['category'] == 'Mailer'
                  and s['id'].startswith(('A13', 'A14'))])
    _report(ctx, f"\n✅ A13+A14 complete — {slides} slides")
    return ctx


if __name__ == '__main__':
    print("mailer_response module — import and call run_mailer_response_suite(ctx)")
