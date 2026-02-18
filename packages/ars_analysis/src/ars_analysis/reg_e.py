"""
reg_e.py — Comprehensive Reg E (Regulation E) Opt-In Analysis
==============================================================
All A8 analyses: data tables + charts + Excel exports + PowerPoint slides.

Analyses:
  A8.1    Overall Reg E status (donut chart)
  A8.2    Historical by Year + Decade (bar charts)
  A8.3    L12M Monthly opt-in rates (bar + line)
  A8.4    By Branch: horizontal bars, vertical bars, scatter (4a/4b/4c)
  A8.5    By Account Age (bar chart)
  A8.6    By Account Holder Age (grouped bar)
  A8.7    By Product Code (bar + scatter)
  A8.8    Monthly Reg E Heatmap (branch × month)
  A8.9    Branch Performance Summary Table
  A8.10   All-Time Account Funnel with Reg E
  A8.11   L12M Funnel with Reg E
  A8.12   24-Month Reg E Trend (line chart)
  A8.13   Complete Branch × Month Pivot Table

Usage:
    from reg_e import run_reg_e_suite
    ctx = run_reg_e_suite(ctx)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
from matplotlib.ticker import FuncFormatter
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime


# =============================================================================
# HELPERS
# =============================================================================

def _report(ctx, msg):
    print(msg)
    cb = ctx.get('_progress_callback')
    if cb:
        cb(msg)


def _fig(ctx, size='single'):
    mf = ctx.get('_make_figure')
    if mf:
        return mf(size)
    sizes = {'single': (14, 7), 'half': (10, 6), 'wide': (16, 7),
             'square': (12, 12), 'large': (28, 14), 'tall': (14, 10)}
    return plt.subplots(figsize=sizes.get(size, (14, 7)))


def _save_chart(fig, path):
    fig.savefig(str(path), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category='Reg E'):
    ctx['all_slides'].append({'id': slide_id, 'category': category,
                              'data': data, 'include': True})


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get('_save_to_excel')
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   ⚠️ Export {sheet}: {e}")


def _rege(df, col, opt_list):
    """Calculate Reg E opt-in stats. Returns (total, opted_in, rate)."""
    t = len(df)
    if t == 0:
        return 0, 0, 0
    oi = len(df[df[col].isin(opt_list)])
    return t, oi, oi / t


def _opt_list(ctx):
    """Return normalised opt-in values list."""
    raw = ctx.get('reg_e_opt_in', [])
    if isinstance(raw, str):
        return [raw]
    return [str(v).strip() for v in raw] if raw else []


def _reg_col(ctx):
    """Return the latest Reg E column name."""
    return ctx.get('latest_reg_e_column')


def _total_row(df, label_col, label='TOTAL'):
    """Add a total row to a Reg E breakdown DataFrame."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals = {label_col: label}
    for c in num_cols:
        if 'Rate' in c or '%' in c:
            oi = df['Opted In'].sum() if 'Opted In' in df.columns else 0
            ta = df['Total Accounts'].sum() if 'Total Accounts' in df.columns else 0
            totals[c] = oi / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


# =============================================================================
# CATEGORIZATION (reuse from dctr patterns)
# =============================================================================

ACCT_AGE_ORDER = ['0-6 months', '6-12 months', '1-2 years', '2-5 years',
                  '5-10 years', '10-20 years', '20+ years']
HOLDER_AGE_ORDER = ['18-24', '25-34', '35-44', '45-54', '55-64', '65-74', '75+']
BALANCE_ORDER = ['Negative', '$0-$499', '$500-$999', '$1K-$2.5K', '$2.5K-$5K',
                 '$5K-$10K', '$10K-$25K', '$25K-$50K', '$50K-$100K', '$100K+']


def _cat_acct_age(days):
    if pd.isna(days): return 'Unknown'
    if days < 180: return '0-6 months'
    if days < 365: return '6-12 months'
    if days < 730: return '1-2 years'
    if days < 1825: return '2-5 years'
    if days < 3650: return '5-10 years'
    if days < 7300: return '10-20 years'
    return '20+ years'


def _cat_holder_age(age):
    if pd.isna(age): return 'Unknown'
    if age < 25: return '18-24'
    if age < 35: return '25-34'
    if age < 45: return '35-44'
    if age < 55: return '45-54'
    if age < 65: return '55-64'
    if age < 75: return '65-74'
    return '75+'


def _cat_balance(bal):
    if pd.isna(bal): return 'Unknown'
    if bal < 0: return 'Negative'
    if bal < 500: return '$0-$499'
    if bal < 1000: return '$500-$999'
    if bal < 2500: return '$1K-$2.5K'
    if bal < 5000: return '$2.5K-$5K'
    if bal < 10000: return '$5K-$10K'
    if bal < 25000: return '$10K-$25K'
    if bal < 50000: return '$25K-$50K'
    if bal < 100000: return '$50K-$100K'
    return '$100K+'


# =============================================================================
# A8.1 — OVERALL REG E STATUS
# =============================================================================

def run_reg_e_1(ctx):
    """A8.1 — Overall Reg E opt-in status with donut chart."""
    _report(ctx, "\n📊 A8.1 — Overall Reg E Status")
    base = ctx['reg_e_eligible_base']
    base_l12m = ctx['reg_e_eligible_base_l12m']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    t_all, oi_all, r_all = _rege(base, col, opts)
    t_l12m, oi_l12m, r_l12m = 0, 0, 0
    if base_l12m is not None and not base_l12m.empty:
        t_l12m, oi_l12m, r_l12m = _rege(base_l12m, col, opts)

    summary = pd.DataFrame([
        {'Category': 'All-Time', 'Total Accounts': t_all, 'Opted In': oi_all,
         'Opted Out': t_all - oi_all, 'Opt-In Rate %': r_all},
        {'Category': 'Last 12 Months', 'Total Accounts': t_l12m, 'Opted In': oi_l12m,
         'Opted Out': t_l12m - oi_l12m, 'Opt-In Rate %': r_l12m},
    ])

    _save(ctx, summary, 'A8.1-RegE-Overall', 'Overall Reg E Opt-In Status', {
        'Total Eligible': f"{t_all:,}", 'Opt-In Rate': f"{r_all:.1%}",
        'L12M Rate': f"{r_l12m:.1%}", 'Opted Out': f"{t_all - oi_all:,}"})

    # Donut chart
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        fig.patch.set_facecolor('white')
        colors = ['#2E8B57', '#E0E0E0']

        for ax, sizes, title, rate in [
            (ax1, [oi_all, t_all - oi_all], 'All-Time', r_all),
            (ax2, [oi_l12m, max(t_l12m - oi_l12m, 0)], 'Trailing Twelve Months', r_l12m)
        ]:
            if sum(sizes) == 0:
                sizes = [0, 1]
            ax.pie(sizes, labels=None, startangle=90, colors=colors, explode=(0.08, 0))
            ax.add_artist(plt.Circle((0, 0), 0.55, fc='white'))
            ax.text(0, 0, f"{rate:.1%}", ha='center', va='center',
                    fontsize=24, fontweight='bold')
            ax.set_title(title, fontsize=18, fontweight='bold', pad=15)
            # Legend
            labels = [f"Opted In: {sizes[0]:,}", f"Opted Out: {sizes[1]:,}"]
            ax.legend(labels, loc='lower center', fontsize=14,
                     bbox_to_anchor=(0.5, -0.05))

        fig.suptitle(f"Reg E Opt-In Status — {ctx.get('client_name', '')}",
                     fontsize=20, fontweight='bold', y=1.02)
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_1_reg_e_status.png')

        change = r_l12m - r_all
        trend = f"improving (+{change:.1f}pp)" if change > 0.01 else \
                f"declining ({change:.1f}pp)" if change < -0.01 else "stable"

        _slide(ctx, 'A8.1 - Reg E Overall Status', {
            'title': 'Reg E Opt-In Status Overview',
            'subtitle': f"Opt-in rate at {r_all:.1%} — {t_all - oi_all:,} accounts opted out",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"Total personal w/debit: {t_all:,}",
                         f"Opted in: {oi_all:,} ({r_all:.1%})",
                         f"Opted out: {t_all - oi_all:,} ({1 - r_all:.1%})",
                         f"TTM opt-in rate: {r_l12m:.1%}",
                         f"Trend: {trend}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_1'] = {
        'opt_in_rate': r_all, 'l12m_rate': r_l12m,
        'total_base': t_all, 'opted_in': oi_all, 'opted_out': t_all - oi_all}
    _report(ctx, f"   All-time: {r_all:.1%} ({oi_all:,}/{t_all:,})  |  L12M: {r_l12m:.1%}")
    return ctx


# =============================================================================
# A8.2 — HISTORICAL BY YEAR + DECADE
# =============================================================================

def run_reg_e_2(ctx):
    """A8.2 — Historical Reg E by Year and Decade with bar charts."""
    _report(ctx, "\n📊 A8.2 — Historical Reg E (Year/Decade)")
    base = ctx['reg_e_eligible_base']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    df = base.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Year'] = df['Date Opened'].dt.year
    valid = df.dropna(subset=['Year']).copy()

    # Yearly
    rows = []
    for yr in sorted(valid['Year'].dropna().unique()):
        yd = valid[valid['Year'] == yr]
        t, oi, r = _rege(yd, col, opts)
        rows.append({'Year': int(yr), 'Total Accounts': t, 'Opted In': oi,
                     'Opted Out': t - oi, 'Opt-In Rate': r})
    yearly = pd.DataFrame(rows)
    if not yearly.empty:
        yearly = _total_row(yearly, 'Year')

    # Decade
    valid['Decade'] = (valid['Year'] // 10 * 10).astype(int).astype(str) + 's'
    drows = []
    for dec in sorted(valid['Decade'].unique()):
        dd = valid[valid['Decade'] == dec]
        t, oi, r = _rege(dd, col, opts)
        drows.append({'Decade': dec, 'Total Accounts': t, 'Opted In': oi,
                     'Opted Out': t - oi, 'Opt-In Rate': r})
    decade = pd.DataFrame(drows)
    if not decade.empty:
        decade = _total_row(decade, 'Decade')

    _save(ctx, yearly, 'A8.2a-RegE-Yearly', 'Reg E Opt-In by Year')
    _save(ctx, decade, 'A8.2b-RegE-Decade', 'Reg E Opt-In by Decade')

    # Charts
    try:
        chart_yearly = yearly[yearly['Year'] != 'TOTAL'].copy()
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
        fig.patch.set_facecolor('white')

        # Yearly bars
        if not chart_yearly.empty:
            x = range(len(chart_yearly))
            total_rows = yearly[yearly['Year'] == 'TOTAL']['Opt-In Rate']
            overall = total_rows.values[0] if len(total_rows) > 0 else chart_yearly['Opt-In Rate'].mean()
            bars = ax1.bar(x, chart_yearly['Opt-In Rate'] * 100, color='#5B9BD5',
                          edgecolor='black', linewidth=1.5)
            for i, (bar, rate) in enumerate(zip(bars, chart_yearly['Opt-In Rate'])):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f"{rate:.1%}", ha='center', fontsize=16, fontweight='bold')
            ax1.axhline(y=overall * 100, color='red', linestyle='--', linewidth=2, alpha=0.7)
            ax1.text(len(chart_yearly) - 0.5, overall * 100 + 0.5, f'Avg: {overall:.1%}',
                    ha='right', fontsize=16, color='red', fontweight='bold')
            ax1.set_xticks(list(x))
            ax1.set_xticklabels([str(int(y)) for y in chart_yearly['Year']], rotation=45, ha='right', fontsize=14)
            ax1.set_ylabel('Opt-In Rate (%)', fontsize=16)
            ax1.set_title('Reg E Opt-In Rate by Year', fontsize=20, fontweight='bold')
            ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
            ax1.tick_params(axis='y', labelsize=14)

        # Decade bars
        chart_decade = decade[decade['Decade'] != 'TOTAL'].copy()
        if not chart_decade.empty:
            x2 = range(len(chart_decade))
            bars2 = ax2.bar(x2, chart_decade['Opt-In Rate'] * 100, color='#A23B72',
                           edgecolor='black', linewidth=1.5)
            for bar, rate in zip(bars2, chart_decade['Opt-In Rate']):
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f"{rate:.1%}", ha='center', fontsize=16, fontweight='bold')
            ax2.set_xticks(list(x2))
            ax2.set_xticklabels(chart_decade['Decade'].tolist(), rotation=45, ha='right', fontsize=14)
            ax2.set_ylabel('Opt-In Rate (%)', fontsize=16)
            ax2.set_title('Reg E Opt-In Rate by Decade', fontsize=20, fontweight='bold')
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
            ax2.tick_params(axis='y', labelsize=14)

        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_2_reg_e_historical.png')

        # Insights
        if not chart_yearly.empty and len(chart_yearly) > 0:
            best_yr = chart_yearly.loc[chart_yearly['Opt-In Rate'].idxmax(), 'Year']
            best_rt = chart_yearly['Opt-In Rate'].max()
            worst_yr = chart_yearly.loc[chart_yearly['Opt-In Rate'].idxmin(), 'Year']
            worst_rt = chart_yearly['Opt-In Rate'].min()

            _slide(ctx, 'A8.2 - Reg E Historical', {
                'title': 'Reg E Opt-In Rate by Year & Decade',
                'subtitle': f"Best: {int(best_yr)} ({best_rt:.1%}) — Worst: {int(worst_yr)} ({worst_rt:.1%})",
                'chart_path': cp, 'layout_index': 9,
                'insights': [f"Years analyzed: {len(chart_yearly)}",
                             f"Overall rate: {overall:.1%}",
                             f"Best year: {int(best_yr)} at {best_rt:.1%}",
                             f"Worst year: {int(worst_yr)} at {worst_rt:.1%}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_2'] = {'yearly': yearly, 'decade': decade}
    _report(ctx, f"   {len(rows)} years | {len(drows)} decades")
    return ctx


# =============================================================================
# A8.3 — L12M MONTHLY
# =============================================================================

def run_reg_e_3(ctx):
    """A8.3 — Last 12 Months monthly Reg E opt-in rates."""
    _report(ctx, "\n📊 A8.3 — L12M Monthly Reg E")
    base_l12m = ctx['reg_e_eligible_base_l12m']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)
    l12m = ctx['last_12_months']

    if base_l12m is None or base_l12m.empty:
        _report(ctx, "   ⚠️ No L12M Reg E data")
        ctx['results']['reg_e_3'] = {}
        return ctx

    df = base_l12m.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Month_Year'] = df['Date Opened'].dt.strftime('%b%y')

    rows = []
    for my in l12m:
        ma = df[df['Month_Year'] == my]
        t, oi, r = _rege(ma, col, opts) if len(ma) > 0 else (0, 0, 0)
        rows.append({'Month': my, 'Total Accounts': t, 'Opted In': oi,
                     'Opted Out': t - oi, 'Opt-In Rate': r})
    monthly = pd.DataFrame(rows)
    monthly = _total_row(monthly, 'Month')

    _save(ctx, monthly, 'A8.3-RegE-L12M', 'L12M Reg E Opt-In by Month', {
        'Total L12M': f"{monthly[monthly['Month'] == 'TOTAL']['Total Accounts'].iloc[0]:,}",
        'Overall Rate': f"{monthly[monthly['Month'] == 'TOTAL']['Opt-In Rate'].iloc[0]:.1%}"})

    # Chart
    try:
        chart = monthly[monthly['Month'] != 'TOTAL'].copy()
        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor('white')

        x = range(len(chart))
        rates = chart['Opt-In Rate'] * 100
        vols = chart['Total Accounts']

        bars = ax.bar(x, rates, color='#2E8B57', edgecolor='black', linewidth=1.5, alpha=0.8)
        for i, (bar, rate, vol) in enumerate(zip(bars, rates, vols)):
            if vol > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                       f"{rate:.1f}%", ha='center', fontsize=16, fontweight='bold')
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                       f"n={int(vol)}", ha='center', fontsize=12, color='white', fontweight='bold')

        overall = monthly[monthly['Month'] == 'TOTAL']['Opt-In Rate'].iloc[0] * 100
        ax.axhline(y=overall, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.text(len(chart) - 0.5, overall + 0.3, f'Overall: {overall:.1f}%',
               ha='right', fontsize=16, color='red', fontweight='bold')

        ax.set_xticks(list(x))
        ax.set_xticklabels(chart['Month'].tolist(), rotation=45, ha='right', fontsize=14)
        ax.set_ylabel('Opt-In Rate (%)', fontsize=16)
        ax.set_title(f"TTM Reg E Opt-In Rate by Month — {ctx.get('client_name', '')}",
                    fontsize=20, fontweight='bold')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.tick_params(axis='y', labelsize=14)
        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_3_reg_e_l12m.png')

        active = chart[chart['Total Accounts'] > 0]
        best = active.loc[active['Opt-In Rate'].idxmax()] if not active.empty else None
        _slide(ctx, 'A8.3 - Reg E L12M Monthly', {
            'title': 'TTM Reg E Opt-In by Month', 'chart_path': cp, 'layout_index': 9,
            'subtitle': f"Overall TTM: {overall:.1f}% — Best: {best['Month']} ({best['Opt-In Rate']:.1%})" if best is not None else f"Overall TTM: {overall:.1f}%",
            'insights': [f"Months analyzed: {len(active)}",
                         f"Overall TTM rate: {overall:.1f}%"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_3'] = {'monthly': monthly}
    _report(ctx, f"   {len(rows)} months")
    return ctx


# =============================================================================
# A8.4 — BY BRANCH (horizontal + scatter)
# =============================================================================

def run_reg_e_4(ctx):
    """A8.4 — Reg E opt-in by Branch with Historical vs L12M comparison."""
    _report(ctx, "\n📊 A8.4 — Reg E by Branch")
    base = ctx['reg_e_eligible_base']
    base_l12m = ctx['reg_e_eligible_base_l12m']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    def branch_rates(df):
        if df is None or df.empty:
            return pd.DataFrame()
        rows = []
        for br in sorted(df['Branch'].dropna().unique()):
            bd = df[df['Branch'] == br]
            t, oi, r = _rege(bd, col, opts)
            rows.append({'Branch': br, 'Total Accounts': t, 'Opted In': oi,
                         'Opted Out': t - oi, 'Opt-In Rate': r})
        result = pd.DataFrame(rows)
        return _total_row(result, 'Branch') if not result.empty else result

    hist = branch_rates(base)
    l12m = branch_rates(base_l12m)

    # Comparison
    comparison = []
    if not hist.empty:
        branches = hist[hist['Branch'] != 'TOTAL']['Branch'].unique()
        for br in branches:
            h = hist[hist['Branch'] == br]
            l = l12m[l12m['Branch'] == br] if not l12m.empty else pd.DataFrame()
            if not h.empty:
                hr = h['Opt-In Rate'].iloc[0]
                hv = h['Total Accounts'].iloc[0]
                lr = l['Opt-In Rate'].iloc[0] if not l.empty else 0
                lv = l['Total Accounts'].iloc[0] if not l.empty else 0
                comparison.append({'Branch': br, 'Historical Rate': hr, 'L12M Rate': lr,
                                   'Change': lr - hr, 'Historical Volume': hv, 'L12M Volume': lv})
    comp_df = pd.DataFrame(comparison)
    if not comp_df.empty:
        comp_df = comp_df.sort_values('Historical Rate', ascending=False)

    _save(ctx, comp_df if not comp_df.empty else hist, 'A8.4-RegE-Branch',
          'Reg E by Branch — Historical vs L12M', {
              'Branches': len(comp_df) if not comp_df.empty else 0})

    # Horizontal bar chart
    try:
        if not comp_df.empty:
            fig, ax = plt.subplots(figsize=(18, max(10, len(comp_df) * 0.8)))
            fig.patch.set_facecolor('white')
            y_pos = np.arange(len(comp_df))
            w = 0.35

            ax.barh(y_pos + w / 2, comp_df['Historical Rate'] * 100, w,
                   label='Historical', color='#1a5276', alpha=0.8, edgecolor='black')
            ax.barh(y_pos - w / 2, comp_df['L12M Rate'] * 100, w,
                   label='Trailing Twelve Months', color='#2E7D32', alpha=0.8, edgecolor='black')

            for i in range(len(comp_df)):
                hr = comp_df.iloc[i]['Historical Rate'] * 100
                lr = comp_df.iloc[i]['L12M Rate'] * 100
                if hr > 0:
                    ax.text(hr + 0.3, y_pos[i] + w / 2, f'{hr:.1f}%', va='center', fontsize=16)
                if lr > 0:
                    ax.text(lr + 0.3, y_pos[i] - w / 2, f'{lr:.1f}%', va='center', fontsize=16)

            # Weighted averages
            if comp_df['Historical Volume'].sum() > 0:
                h_avg = (comp_df['Historical Rate'] * comp_df['Historical Volume']).sum() / comp_df['Historical Volume'].sum() * 100
                ax.axvline(x=h_avg, color='#1a5276', linestyle='--', linewidth=2, alpha=0.5)
            if comp_df['L12M Volume'].sum() > 0:
                l_avg = (comp_df['L12M Rate'] * comp_df['L12M Volume']).sum() / comp_df['L12M Volume'].sum() * 100
                ax.axvline(x=l_avg, color='#2E7D32', linestyle='--', linewidth=2, alpha=0.5)

            ax.set_yticks(y_pos)
            ax.set_yticklabels(comp_df['Branch'].tolist(), fontsize=16)
            ax.set_xlabel('Opt-In Rate (%)', fontsize=18)
            ax.set_title(f"Reg E Opt-In by Branch — {ctx.get('client_name', '')}",
                        fontsize=20, fontweight='bold')
            ax.legend(fontsize=16)
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
            ax.tick_params(axis='x', labelsize=14)
            fig.tight_layout()
            cp = _save_chart(fig, ctx['chart_dir'] / 'a8_4a_reg_e_branch.png')

            best = comp_df.iloc[0]
            worst = comp_df.iloc[-1]
            spread = best['Historical Rate'] * 100 - worst['Historical Rate'] * 100
            improving = len(comp_df[comp_df['Change'] > 0])

            _slide(ctx, 'A8.4a - Reg E by Branch', {
                'title': 'Reg E Opt-In by Branch (Historical vs TTM)',
                'subtitle': f"Range: {worst['Historical Rate']:.1%} to {best['Historical Rate']:.1%} — {spread:.0f}pp gap",
                'chart_path': cp, 'layout_index': 13,
                'insights': [f"Branches: {len(comp_df)}",
                             f"Top: {best['Branch']} at {best['Historical Rate']:.1%}",
                             f"Bottom: {worst['Branch']} at {worst['Historical Rate']:.1%}",
                             f"Improving (TTM): {improving} of {len(comp_df)}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch chart: {e}")

    # Scatter plot
    try:
        scatter = hist[hist['Branch'] != 'TOTAL'].copy()
        if not scatter.empty and len(scatter) > 1:
            fig2, ax2 = plt.subplots(figsize=(14, 7))
            fig2.patch.set_facecolor('white')
            ax2.scatter(scatter['Total Accounts'], scatter['Opt-In Rate'] * 100,
                       s=300, alpha=0.6, color='#5B9BD5', edgecolor='black', linewidth=2)
            for _, row in scatter.iterrows():
                ax2.annotate(row['Branch'], (row['Total Accounts'], row['Opt-In Rate'] * 100),
                            xytext=(6, 6), textcoords='offset points', fontsize=14)

            avg_vol = scatter['Total Accounts'].mean()
            avg_rate = (scatter['Opted In'].sum() / scatter['Total Accounts'].sum()) * 100
            ax2.axhline(y=avg_rate, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
            ax2.axvline(x=avg_vol, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
            ax2.set_xlabel('Total Accounts', fontsize=16)
            ax2.set_ylabel('Opt-In Rate (%)', fontsize=16)
            ax2.set_title('Branch Volume vs Opt-In Rate', fontsize=20, fontweight='bold')
            ax2.tick_params(axis='both', labelsize=14)
            fig2.tight_layout()
            cp2 = _save_chart(fig2, ctx['chart_dir'] / 'a8_4c_reg_e_scatter.png')

            hv_lr = len(scatter[(scatter['Total Accounts'] > avg_vol) & (scatter['Opt-In Rate'] * 100 <= avg_rate)])
            _slide(ctx, 'A8.4c - Reg E Branch Scatter', {
                'title': 'Reg E: Branch Volume vs Opt-In Rate',
                'subtitle': f"{hv_lr} high-volume branches below avg rate",
                'chart_path': cp2, 'layout_index': 9,
                'insights': [f"Avg volume: {avg_vol:,.0f}", f"Avg rate: {avg_rate:.1f}%",
                             f"Priority branches (high vol, low rate): {hv_lr}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Scatter chart: {e}")

    ctx['results']['reg_e_4'] = {'comparison': comp_df, 'historical': hist, 'l12m': l12m}
    _report(ctx, f"   {len(comparison)} branches compared")
    return ctx


# =============================================================================
# A8.4b — BY BRANCH (vertical bars + DCTR lines, L12M-focused)
# =============================================================================

def run_reg_e_4b(ctx):
    """A8.4b — Reg E by Branch — Vertical bars sorted by L12M, with rate overlay lines."""
    _report(ctx, "\n📊 A8.4b — Reg E by Branch (Vertical, L12M Focus)")

    comp_df = ctx['results'].get('reg_e_4', {}).get('comparison')
    if comp_df is None or comp_df.empty:
        _report(ctx, "   ⚠️ No branch comparison data"); return ctx

    chart_data = comp_df.sort_values('L12M Rate', ascending=False).reset_index(drop=True)
    branches = chart_data['Branch'].tolist()
    n = len(branches)

    hist_rates = chart_data['Historical Rate'] * 100
    l12m_rates = chart_data['L12M Rate'] * 100
    l12m_vols = chart_data['L12M Volume']

    # Weighted averages
    h_wa = (chart_data['Historical Rate'] * chart_data['Historical Volume']).sum() / chart_data['Historical Volume'].sum() * 100 if chart_data['Historical Volume'].sum() > 0 else 0
    l_wa = (chart_data['L12M Rate'] * chart_data['L12M Volume']).sum() / chart_data['L12M Volume'].sum() * 100 if chart_data['L12M Volume'].sum() > 0 else 0

    try:
        fig, ax1 = plt.subplots(figsize=(28, 14))
        x_pos = np.arange(n)

        # L12M volume bars
        bars = ax1.bar(x_pos, l12m_vols, width=0.6, color='#D9D9D9',
                       edgecolor='black', linewidth=2)
        ax1.set_ylabel('Eligible Accounts (TTM)', fontsize=28, fontweight='bold')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(branches, rotation=45, ha='right', fontsize=24, fontweight='bold')
        ax1.tick_params(axis='y', labelsize=22)
        ax1.grid(False)
        for spine in ax1.spines.values():
            spine.set_visible(False)

        # Volume labels
        max_vol = l12m_vols.max() if n > 0 else 1
        for i, v in enumerate(l12m_vols):
            ax1.text(i, v + max_vol * 0.015, f'{int(v):,}',
                     ha='center', va='bottom', fontsize=22, fontweight='bold', color='#333')

        # Rate lines on secondary axis
        ax2 = ax1.twinx()
        hist_line = ax2.plot(x_pos, hist_rates, 'o-', color='#1a5276', lw=3, ms=10,
                             label='Historical Opt-In %')
        l12m_line = ax2.plot(x_pos, l12m_rates, 'o-', color='#2E7D32', lw=4, ms=14,
                             label='TTM Opt-In %', zorder=5)

        # Data labels
        for i, val in enumerate(l12m_rates):
            if val > 0:
                ax2.text(i, val + 2, f"{val:.0f}%", ha='center', fontsize=22,
                         fontweight='bold', color='#2E7D32')
        for i, val in enumerate(hist_rates):
            if val > 0:
                ax2.text(i, val - 4, f"{val:.0f}%", ha='center', va='top', fontsize=22,
                         fontweight='bold', color='#1a5276', alpha=0.9)

        # Weighted average lines
        ax2.axhline(h_wa, color='#1a5276', linestyle='--', linewidth=3, alpha=0.5)
        ax2.axhline(l_wa, color='#2E7D32', linestyle='--', linewidth=3, alpha=0.5)

        ax2.set_ylabel('Opt-In Rate (%)', fontsize=28, fontweight='bold')
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f'{int(v)}%'))
        ax2.tick_params(axis='y', labelsize=22)
        ax2.grid(False)
        for spine in ax2.spines.values():
            spine.set_visible(False)

        plt.title('Reg E Opt-In Performance by Branch\nTTM Opt-In Rate with Volume Context',
                  fontsize=34, fontweight='bold', pad=30)
        ax2.legend(handles=[hist_line[0], l12m_line[0]],
                   labels=['Historical Opt-In %', 'TTM Opt-In %'],
                   loc='upper right', bbox_to_anchor=(1.0, 0.98),
                   fontsize=22, frameon=True, fancybox=True)
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15)
        plt.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_4b_reg_e_branch_vertical.png')

        best_branch = branches[0]; best_rate = l12m_rates.iloc[0]
        worst_branch = branches[-1]; worst_rate = l12m_rates.iloc[-1]
        spread = best_rate - worst_rate
        improving = (chart_data['L12M Rate'] > chart_data['Historical Rate']).sum()
        trend_change = l_wa - h_wa

        _slide(ctx, 'A8.4b - Reg E by Branch (Vertical)', {
            'title': 'Reg E Opt-In by Branch (TTM Focus)',
            'subtitle': f"TTM avg at {l_wa:.0f}% — Top: {best_branch} ({best_rate:.0f}%) — {spread:.0f}pp spread",
            'chart_path': cp, 'layout_index': 9,
            'insights': [
                f"Branches analyzed: {n}",
                f"TTM weighted avg: {l_wa:.1f}%",
                f"Historical weighted avg: {h_wa:.1f}%",
                f"Trend: {'improving' if trend_change > 0 else 'declining'} ({trend_change:+.1f}pp)",
                f"Top (TTM): {best_branch} at {best_rate:.1f}%",
                f"Bottom (TTM): {worst_branch} at {worst_rate:.1f}%",
                f"Branches improving: {improving} of {n}",
            ]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Vertical branch chart: {e}")

    ctx['results']['reg_e_4b'] = {'best': branches[0] if branches else '', 'improving': improving if 'improving' in dir() else 0}
    _report(ctx, f"   {n} branches plotted vertically")
    return ctx


# =============================================================================
# A8.5 — BY ACCOUNT AGE
# =============================================================================

def run_reg_e_5(ctx):
    """A8.5 — Reg E opt-in by Account Age."""
    _report(ctx, "\n📊 A8.5 — Reg E by Account Age")
    base = ctx['reg_e_eligible_base']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    df = base.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Age Days'] = (pd.Timestamp.now() - df['Date Opened']).dt.days
    df['Age Range'] = df['Age Days'].apply(_cat_acct_age)

    rows = []
    for age in ACCT_AGE_ORDER:
        ad = df[df['Age Range'] == age]
        if len(ad) > 0:
            t, oi, r = _rege(ad, col, opts)
            rows.append({'Account Age': age, 'Total Accounts': t, 'Opted In': oi,
                         'Opted Out': t - oi, 'Opt-In Rate': r})
    result = pd.DataFrame(rows)
    result = _total_row(result, 'Account Age')

    _save(ctx, result, 'A8.5-RegE-AcctAge', 'Reg E by Account Age')

    # Chart
    try:
        chart = result[result['Account Age'] != 'TOTAL'].copy()
        overall = result[result['Account Age'] == 'TOTAL']['Opt-In Rate'].iloc[0] * 100
        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor('white')
        x = range(len(chart))
        rates = chart['Opt-In Rate'] * 100

        colors = ['#e74c3c' if r < overall else '#27ae60' for r in rates]
        bars = ax.bar(x, rates, color=colors, edgecolor='black', linewidth=1.5)
        for bar, rate, vol in zip(bars, rates, chart['Total Accounts']):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                   f"{rate:.1f}%", ha='center', fontsize=16, fontweight='bold')
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                   f"n={int(vol):,}", ha='center', fontsize=12, color='white', fontweight='bold')

        ax.axhline(y=overall, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.text(len(chart) - 0.5, overall + 0.3, f'Avg: {overall:.1f}%',
               ha='right', fontsize=16, color='red', fontweight='bold')
        ax.set_xticks(list(x))
        ax.set_xticklabels(chart['Account Age'].tolist(), rotation=30, ha='right', fontsize=14)
        ax.set_ylabel('Opt-In Rate (%)', fontsize=16)
        ax.set_title('Reg E Opt-In Rate by Account Age', fontsize=20, fontweight='bold')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.tick_params(axis='y', labelsize=14)
        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_5_reg_e_acct_age.png')

        newest = chart.iloc[0]['Opt-In Rate'] if not chart.empty else 0
        oldest = chart.iloc[-1]['Opt-In Rate'] if not chart.empty else 0
        trend = 'increasing' if oldest > newest else 'decreasing'
        _slide(ctx, 'A8.5 - Reg E by Account Age', {
            'title': 'Reg E Opt-In by Account Age',
            'subtitle': f"Rate {trend}s with age — Newest: {newest:.1%}, Oldest: {oldest:.1%}",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"Age ranges: {len(chart)}", f"Overall: {overall:.1f}%",
                         f"Newest (0-6mo): {newest:.1%}", f"Oldest: {oldest:.1%}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_5'] = {'data': result}
    _report(ctx, f"   {len(rows)} age ranges")
    return ctx


# =============================================================================
# A8.6 — BY ACCOUNT HOLDER AGE
# =============================================================================

def run_reg_e_6(ctx):
    """A8.6 — Reg E opt-in by Account Holder Age."""
    _report(ctx, "\n📊 A8.6 — Reg E by Holder Age")
    base = ctx['reg_e_eligible_base']
    base_l12m = ctx['reg_e_eligible_base_l12m']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    def by_holder_age(df):
        if df is None or df.empty:
            return pd.DataFrame()
        d = df.copy()
        d['Date Opened'] = pd.to_datetime(d['Date Opened'], errors='coerce')
        if 'Birth Date' in d.columns:
            d['Birth Date'] = pd.to_datetime(d['Birth Date'], errors='coerce')
            d['Holder Age'] = (pd.Timestamp.now() - d['Birth Date']).dt.days / 365.25
        elif 'Age' in d.columns:
            d['Holder Age'] = pd.to_numeric(d['Age'], errors='coerce')
        else:
            return pd.DataFrame()
        d['Age Group'] = d['Holder Age'].apply(_cat_holder_age)
        rows = []
        for ag in HOLDER_AGE_ORDER:
            seg = d[d['Age Group'] == ag]
            if len(seg) > 0:
                t, oi, r = _rege(seg, col, opts)
                rows.append({'Age Group': ag, 'Total Accounts': t, 'Opted In': oi,
                             'Opted Out': t - oi, 'Opt-In Rate': r})
        result = pd.DataFrame(rows)
        return _total_row(result, 'Age Group') if not result.empty else result

    hist = by_holder_age(base)
    l12m_df = by_holder_age(base_l12m)

    if hist.empty:
        _report(ctx, "   ⚠️ No holder age data (missing Birth Date/Age column)")
        ctx['results']['reg_e_6'] = {}
        return ctx

    _save(ctx, hist, 'A8.6-RegE-HolderAge', 'Reg E by Account Holder Age')

    # Chart
    try:
        ch = hist[hist['Age Group'] != 'TOTAL'].copy()
        cl = l12m_df[l12m_df['Age Group'] != 'TOTAL'].copy() if not l12m_df.empty else pd.DataFrame()

        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor('white')
        x = np.arange(len(ch))
        w = 0.35

        ax.bar(x - w / 2, ch['Opt-In Rate'] * 100, w, label='Historical',
              color='#5B9BD5', edgecolor='black', linewidth=1.5)
        if not cl.empty:
            # Match age groups
            l12m_rates = []
            for ag in ch['Age Group']:
                match = cl[cl['Age Group'] == ag]
                l12m_rates.append(match['Opt-In Rate'].iloc[0] * 100 if not match.empty else 0)
            ax.bar(x + w / 2, l12m_rates, w, label='Trailing Twelve Months',
                  color='#FF7F0E', edgecolor='black', linewidth=1.5)

        ax.set_xticks(x)
        ax.set_xticklabels(ch['Age Group'].tolist(), rotation=30, ha='right', fontsize=14)
        ax.set_ylabel('Opt-In Rate (%)', fontsize=16)
        ax.set_title('Reg E Opt-In by Account Holder Age', fontsize=20, fontweight='bold')
        ax.legend(fontsize=16)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.tick_params(axis='y', labelsize=14)
        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_6_reg_e_holder_age.png')

        best = ch.loc[ch['Opt-In Rate'].idxmax()]
        worst = ch.loc[ch['Opt-In Rate'].idxmin()]
        _slide(ctx, 'A8.6 - Reg E by Holder Age', {
            'title': 'Reg E Opt-In by Account Holder Age',
            'subtitle': f"Best: {best['Age Group']} ({best['Opt-In Rate']:.1%}) — "
                        f"Worst: {worst['Age Group']} ({worst['Opt-In Rate']:.1%})",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"Age groups: {len(ch)}", f"Best: {best['Age Group']} at {best['Opt-In Rate']:.1%}",
                         f"Worst: {worst['Age Group']} at {worst['Opt-In Rate']:.1%}",
                         f"Spread: {(best['Opt-In Rate'] - worst['Opt-In Rate']) * 100:.1f}pp"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_6'] = {'historical': hist, 'l12m': l12m_df}
    _report(ctx, f"   {len(hist) - 1} age groups")
    return ctx


# =============================================================================
# A8.7 — BY PRODUCT CODE
# =============================================================================

def run_reg_e_7(ctx):
    """A8.7 — Reg E opt-in by Product Code."""
    _report(ctx, "\n📊 A8.7 — Reg E by Product Code")
    base = ctx['reg_e_eligible_base']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    if 'Product Code' not in base.columns and 'Prod Code' not in base.columns:
        _report(ctx, "   ⚠️ No Product Code column found")
        ctx['results']['reg_e_7'] = {}
        return ctx

    pc_col = 'Product Code' if 'Product Code' in base.columns else 'Prod Code'
    df = base.copy()

    rows = []
    for pc in sorted(df[pc_col].dropna().unique()):
        seg = df[df[pc_col] == pc]
        t, oi, r = _rege(seg, col, opts)
        rows.append({'Product Code': pc, 'Total Accounts': t, 'Opted In': oi,
                     'Opted Out': t - oi, 'Opt-In Rate': r})
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values('Total Accounts', ascending=False)
        result = _total_row(result, 'Product Code')

    _save(ctx, result, 'A8.7-RegE-Product', 'Reg E by Product Code')

    # Chart — top 15 products by volume
    try:
        chart = result[result['Product Code'] != 'TOTAL'].head(15).copy()
        chart = chart.sort_values('Opt-In Rate', ascending=True)
        fig, ax = plt.subplots(figsize=(14, max(8, len(chart) * 0.6)))
        fig.patch.set_facecolor('white')

        overall = result[result['Product Code'] == 'TOTAL']['Opt-In Rate'].iloc[0] * 100
        bars = ax.barh(range(len(chart)), chart['Opt-In Rate'] * 100,
                      color='#5B9BD5', edgecolor='black', linewidth=1.5)
        for i, (rate, vol) in enumerate(zip(chart['Opt-In Rate'], chart['Total Accounts'])):
            ax.text(rate * 100 + 0.3, i, f'{rate:.1%} (n={int(vol):,})', va='center', fontsize=16)
        ax.axvline(x=overall, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.set_yticks(range(len(chart)))
        ax.set_yticklabels(chart['Product Code'].tolist(), fontsize=14)
        ax.set_xlabel('Opt-In Rate (%)', fontsize=16)
        ax.set_title('Reg E Opt-In by Product Code', fontsize=20, fontweight='bold')
        ax.tick_params(axis='x', labelsize=14)
        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_7_reg_e_product.png')

        _slide(ctx, 'A8.7 - Reg E by Product', {
            'title': 'Reg E Opt-In by Product Code', 'chart_path': cp, 'layout_index': 9,
            'subtitle': f"{len(chart)} products — Overall: {overall:.1f}%",
            'insights': [f"Products analyzed: {len(result) - 1}", f"Overall rate: {overall:.1f}%"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['reg_e_7'] = {'data': result}
    _report(ctx, f"   {len(rows)} product codes")
    return ctx


# =============================================================================
# A8.8 — MONTHLY HEATMAP (BRANCH × MONTH) — two datasets → A8.8a + A8.8b
# =============================================================================

def _build_heatmap(df_src, col, opts, l12m, label):
    """Build a branch × month heatmap DataFrame from an L12M dataset."""
    df = df_src.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Month_Year'] = df['Date Opened'].dt.strftime('%b%y')
    branches = sorted(df['Branch'].dropna().unique())
    pivot = {}
    for br in branches:
        month_rates = {}
        for my in l12m:
            seg = df[(df['Branch'] == br) & (df['Month_Year'] == my)]
            if len(seg) > 0:
                _, _, r = _rege(seg, col, opts)
                month_rates[my] = r
            else:
                month_rates[my] = np.nan
        pivot[br] = month_rates
    hm = pd.DataFrame(pivot).T
    if hm.empty:
        return hm, branches
    hm['avg'] = hm.mean(axis=1)
    hm = hm.sort_values('avg', ascending=False).drop(columns=['avg'])
    return hm, branches


def _render_heatmap(ctx, heatmap_df, branches, cmap_name, slide_id, chart_fname, dataset_label):
    """Render and save a single heatmap chart + slide."""
    fig_h = max(10, len(branches) * 0.7)
    fig, ax = plt.subplots(figsize=(18, fig_h))
    fig.patch.set_facecolor('white')

    display = heatmap_df * 100
    vmin = np.nanpercentile(display.values, 5) if display.notna().any().any() else 0
    vmax = np.nanpercentile(display.values, 95) if display.notna().any().any() else 100

    import seaborn as sns
    sns.heatmap(display, annot=True, fmt='.0f', cmap=cmap_name,
               vmin=vmin, vmax=vmax, linewidths=0.5, annot_kws={'fontsize': 14},
               cbar_kws={'label': 'Opt-In Rate (%)'}, ax=ax)
    ax.set_title(f"Monthly Reg E Opt-In — {dataset_label}\n{ctx.get('client_name', '')}",
                fontsize=24, fontweight='bold', pad=20)
    ax.set_ylabel('')
    ax.tick_params(axis='x', labelsize=14)
    ax.tick_params(axis='y', labelsize=14)
    fig.tight_layout()
    cp = _save_chart(fig, ctx['chart_dir'] / chart_fname)

    overall = np.nanmean(heatmap_df.values) * 100
    _slide(ctx, slide_id, {
        'title': f'Reg E Heatmap — {dataset_label}',
        'subtitle': f"Overall avg: {overall:.1f}% — {len(branches)} branches × {heatmap_df.shape[1]} months",
        'chart_path': cp, 'layout_index': 9,
        'insights': [f"Branches: {len(branches)}", f"Overall avg: {overall:.1f}%",
                     f"Dataset: {dataset_label}"]})
    return overall


def run_reg_e_8(ctx):
    """A8.8 — Monthly Reg E heatmaps: A8.8a (Open Personal) + A8.8b (Eligible Personal)."""
    _report(ctx, "\n📊 A8.8 — Reg E Monthly Heatmaps")
    col = _reg_col(ctx)
    opts = _opt_list(ctx)
    l12m = ctx['last_12_months']
    heatmaps = {}

    # ── A8.8a: Open Personal w/Debit ──
    open_accts = ctx.get('open_accounts')
    if open_accts is not None and not open_accts.empty:
        sd = ctx['start_date']
        ed = ctx['end_date']
        op = open_accts.copy()
        op['Date Opened'] = pd.to_datetime(op['Date Opened'], errors='coerce')
        open_l12m = op[(op['Business?'] == 'No') &
                       (op['Debit?'] == 'Yes') &
                       (op['Date Opened'] >= sd) &
                       (op['Date Opened'] <= ed)]
        if col in open_l12m.columns and len(open_l12m) > 0:
            hm_a, br_a = _build_heatmap(open_l12m, col, opts, l12m, 'Open Personal')
            if not hm_a.empty:
                _save(ctx, hm_a.reset_index().rename(columns={'index': 'Branch'}),
                      'A8.8a-RegE-Open', 'Monthly Reg E Heatmap — Open Personal')
                try:
                    avg = _render_heatmap(ctx, hm_a, br_a, 'Oranges',
                                          'A8.8a - Reg E Heatmap (Open Personal)',
                                          'a8_8a_reg_e_heatmap_open.png', 'Open Personal w/Debit')
                    heatmaps['open'] = hm_a
                    _report(ctx, f"   A8.8a: {len(br_a)} branches, avg {avg:.1f}%")
                except Exception as e:
                    _report(ctx, f"   ⚠️ A8.8a chart: {e}")

    # ── A8.8b: Eligible Personal w/Debit ──
    base_l12m = ctx['reg_e_eligible_base_l12m']
    if base_l12m is not None and not base_l12m.empty:
        hm_b, br_b = _build_heatmap(base_l12m, col, opts, l12m, 'Eligible Personal')
        if not hm_b.empty:
            _save(ctx, hm_b.reset_index().rename(columns={'index': 'Branch'}),
                  'A8.8b-RegE-Eligible', 'Monthly Reg E Heatmap — Eligible Personal')
            try:
                avg = _render_heatmap(ctx, hm_b, br_b, 'Greens',
                                      'A8.8b - Reg E Heatmap (Eligible Personal)',
                                      'a8_8b_reg_e_heatmap_eligible.png', 'Eligible Personal w/Debit')
                heatmaps['eligible'] = hm_b
                _report(ctx, f"   A8.8b: {len(br_b)} branches, avg {avg:.1f}%")
            except Exception as e:
                _report(ctx, f"   ⚠️ A8.8b chart: {e}")

    if not heatmaps:
        _report(ctx, "   ⚠️ No heatmap data available")

    ctx['results']['reg_e_8'] = {'heatmap': heatmaps.get('eligible', pd.DataFrame()), **heatmaps}
    return ctx


# =============================================================================
# A8.9 — BRANCH PERFORMANCE SUMMARY TABLE
# =============================================================================

def _build_branch_summary(heatmap_df):
    """Build a branch performance summary from a heatmap DataFrame."""
    rows = []
    for br in heatmap_df.index:
        vals = heatmap_df.loc[br].dropna()
        if len(vals) == 0:
            continue
        avg_r = vals.mean()
        cur_r = vals.iloc[-1] if len(vals) > 0 else 0
        best_r = vals.max()
        worst_r = vals.min()
        rng = (best_r - worst_r) * 100

        trend = '→'
        change = 0
        if len(vals) >= 6:
            early = vals.iloc[:3].mean()
            recent = vals.iloc[-3:].mean()
            change = (recent - early) * 100
            trend = '↑' if change > 1 else '↓' if change < -1 else '→'

        rows.append({'Branch': br, 'Avg Rate': avg_r, 'Current': cur_r,
                     'Best': best_r, 'Worst': worst_r, 'Range (pp)': round(rng, 1),
                     'Months': len(vals), 'Trend': trend, 'Change (pp)': round(change, 1)})
    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values('Avg Rate', ascending=False)
    return summary


def _render_summary_chart(ctx, summary, slide_id, chart_fname, dataset_label):
    """Render branch summary bar chart and create slide."""
    fig, ax = plt.subplots(figsize=(14, max(10, len(summary) * 0.6)))
    fig.patch.set_facecolor('white')
    overall = summary['Avg Rate'].mean() * 100

    colors = ['#27ae60' if r * 100 >= overall else '#e74c3c' for r in summary['Avg Rate']]
    bars = ax.barh(range(len(summary)), summary['Avg Rate'] * 100,
                  color=colors, edgecolor='black', linewidth=1.5)
    for i, (rate, trend, chg) in enumerate(zip(summary['Avg Rate'], summary['Trend'], summary['Change (pp)'])):
        label = f"{rate:.1%} {trend}"
        ax.text(rate * 100 + 0.3, i, label, va='center', fontsize=14)

    ax.axvline(x=overall, color='navy', linestyle='--', linewidth=2, alpha=0.5)
    ax.set_yticks(range(len(summary)))
    ax.set_yticklabels(summary['Branch'].tolist(), fontsize=14)
    ax.set_xlabel('Avg Opt-In Rate (%)', fontsize=16)
    ax.set_title(f'Branch Reg E Summary — {dataset_label}', fontsize=20, fontweight='bold')
    ax.tick_params(axis='x', labelsize=14)
    fig.tight_layout()
    cp = _save_chart(fig, ctx['chart_dir'] / chart_fname)

    improving = len(summary[summary['Trend'] == '↑'])
    declining = len(summary[summary['Trend'] == '↓'])
    stable = len(summary[summary['Trend'] == '→'])
    _slide(ctx, slide_id, {
        'title': f'Branch Reg E Summary — {dataset_label}',
        'subtitle': f"{len(summary)} branches — Avg: {overall:.1f}%",
        'chart_path': cp, 'layout_index': 9,
        'insights': [f"Improving: {improving}", f"Declining: {declining}",
                     f"Stable: {stable}", f"Dataset: {dataset_label}"]})


def run_reg_e_9(ctx):
    """A8.9 — Branch Reg E performance summary per dataset (A8.9a Open, A8.9b Eligible)."""
    _report(ctx, "\n📊 A8.9 — Branch Performance Summary")
    re8 = ctx['results'].get('reg_e_8', {})
    summaries = {}

    # A8.9a — Open Personal
    open_hm = re8.get('open')
    if open_hm is not None and not open_hm.empty:
        try:
            s = _build_branch_summary(open_hm)
            if not s.empty:
                _save(ctx, s, 'A8.9a-RegE-BranchOpen', 'Branch Summary — Open Personal')
                _render_summary_chart(ctx, s, 'A8.9a - Reg E Branch Summary (Open)',
                                       'a8_9a_open_summary.png', 'Open Personal w/Debit')
                summaries['open'] = s
                _report(ctx, f"   A8.9a: {len(s)} branches")
        except Exception as e:
            _report(ctx, f"   ⚠️ A8.9a: {e}")

    # A8.9b — Eligible Personal
    elig_hm = re8.get('eligible') if 'eligible' in re8 else re8.get('heatmap')
    if elig_hm is not None and not elig_hm.empty:
        try:
            s = _build_branch_summary(elig_hm)
            if not s.empty:
                _save(ctx, s, 'A8.9b-RegE-BranchElig', 'Branch Summary — Eligible Personal')
                _render_summary_chart(ctx, s, 'A8.9b - Reg E Branch Summary (Eligible)',
                                       'a8_9b_eligible_summary.png', 'Eligible Personal w/Debit')
                summaries['eligible'] = s
                _report(ctx, f"   A8.9b: {len(s)} branches")
        except Exception as e:
            _report(ctx, f"   ⚠️ A8.9b: {e}")

    if not summaries:
        _report(ctx, "   ⚠️ No heatmap data for summaries")

    ctx['results']['reg_e_9'] = summaries
    return ctx


# =============================================================================
# SHARED FUNNEL RENDERER — matches DCTR funnel style (dctr.py)
# =============================================================================

def _render_reg_e_funnel(ax, stages, title_text, subtitle_text, metrics_text):
    """Render a proportional funnel chart matching the DCTR funnel style.

    stages: list of dicts with keys: name, total, color
    """
    ax.set_facecolor('#f8f9fa')

    max_width = 0.8
    stage_height = 0.15
    y_start = 0.85
    stage_gap = 0.02
    current_y = y_start

    for i, stage in enumerate(stages):
        width = max_width * (stage['total'] / stages[0]['total']) if stages[0]['total'] > 0 else 0.1

        rect = patches.FancyBboxPatch(
            (0.5 - width / 2, current_y - stage_height), width, stage_height,
            boxstyle="round,pad=0.01", facecolor=stage['color'],
            edgecolor='white', linewidth=3, alpha=0.9)
        ax.add_patch(rect)

        ax.text(0.5, current_y - stage_height / 2, f"{stage['total']:,}",
                ha='center', va='center', fontsize=28, fontweight='bold',
                color='white', zorder=10)

        # Stage name on left
        ax.text(0.5 - width / 2 - 0.05, current_y - stage_height / 2,
                stage['name'], ha='right', va='center',
                fontsize=20, fontweight='600', color='#2c3e50')

        # Conversion arrow between stages
        if i > 0 and stages[i - 1]['total'] > 0:
            conv = stage['total'] / stages[i - 1]['total'] * 100
            arrow_y = current_y + stage_gap / 2
            ax.annotate('', xy=(0.5, arrow_y - stage_gap + 0.01),
                        xytext=(0.5, arrow_y - 0.01),
                        arrowprops=dict(arrowstyle='->', lw=3, color='#e74c3c'))
            ax.text(0.45, arrow_y - stage_gap / 2, f"{conv:.1f}%",
                    ha='center', va='center', fontsize=18, fontweight='bold',
                    color='#e74c3c',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#e74c3c', alpha=0.9))

        current_y -= (stage_height + stage_gap)

    # Title and subtitle (in-canvas, matching DCTR style)
    ax.text(0.5, 0.98, title_text,
            ha='center', va='top', fontsize=28, fontweight='bold',
            color='#1e3d59', transform=ax.transAxes)
    ax.text(0.5, 0.93, subtitle_text,
            ha='center', va='top', fontsize=20, style='italic',
            color='#7f8c8d', transform=ax.transAxes)

    # Metrics box (bottom left)
    ax.text(0.02, 0.02, metrics_text, transform=ax.transAxes,
            fontsize=16, ha='left', va='bottom',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ecf0f1',
                      edgecolor='#34495e', linewidth=1.5))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')


# =============================================================================
# A8.10 — ALL-TIME ACCOUNT FUNNEL WITH REG E
# =============================================================================

def run_reg_e_10(ctx):
    """A8.10 — All-time account funnel: Open → Eligible → Debit → Reg E."""
    _report(ctx, "\n📊 A8.10 — All-Time Funnel (with Reg E)")

    total_open = len(ctx['open_accounts']) if ctx['open_accounts'] is not None else 0
    total_eligible = len(ctx['eligible_data']) if ctx['eligible_data'] is not None else 0
    total_with_debit = len(ctx['eligible_with_debit']) if ctx['eligible_with_debit'] is not None else 0
    personal_w_debit = len(ctx['eligible_personal_with_debit']) if ctx['eligible_personal_with_debit'] is not None else 0
    personal_w_rege = len(ctx['reg_e_opted_in']) if ctx['reg_e_opted_in'] is not None else 0

    stages = [
        {'name': 'Open\nAccounts', 'total': total_open, 'color': '#2c7fb8'},
        {'name': 'Eligible\nAccounts', 'total': total_eligible, 'color': '#ff7f0e'},
        {'name': 'Eligible\nw/Debit', 'total': total_with_debit, 'color': '#41b6c4'},
        {'name': 'Personal\nw/Debit', 'total': personal_w_debit, 'color': '#2ca02c'},
        {'name': 'Personal\nw/Reg E', 'total': personal_w_rege, 'color': '#9467bd'},
    ]

    funnel_df = pd.DataFrame([{'Stage': s['name'].replace('\n', ' '), 'Count': s['total']} for s in stages])
    _save(ctx, funnel_df, 'A8.10-RegE-Funnel', 'All-Time Account Funnel with Reg E')

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        fig.patch.set_facecolor('white')

        rege_rate = personal_w_rege / personal_w_debit * 100 if personal_w_debit > 0 else 0
        through_rate = personal_w_rege / total_open * 100 if total_open > 0 else 0

        _render_reg_e_funnel(
            ax, stages,
            title_text="All-Time Account Eligibility & Reg E Funnel",
            subtitle_text="All-Time Analysis",
            metrics_text=f"Reg E Rate (Personal w/Debit): {rege_rate:.1f}%\nEnd-to-End: {through_rate:.1f}%")

        plt.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_10_reg_e_funnel.png')

        _slide(ctx, 'A8.10 - Reg E All-Time Funnel', {
            'title': 'All-Time Account Funnel with Reg E', 'chart_path': cp, 'layout_index': 9,
            'subtitle': f"Open: {total_open:,} → Reg E: {personal_w_rege:,} ({rege_rate:.1f}% of personal w/debit)",
            'insights': [f"Open: {total_open:,}", f"Eligible: {total_eligible:,}",
                         f"Personal w/Debit: {personal_w_debit:,}",
                         f"Reg E Opted In: {personal_w_rege:,} ({rege_rate:.1f}%)"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Funnel chart: {e}")

    ctx['results']['reg_e_10'] = {'funnel': funnel_df}
    _report(ctx, f"   5 stages | Reg E rate: {personal_w_rege / personal_w_debit * 100 if personal_w_debit else 0:.1f}%")
    return ctx


# =============================================================================
# A8.11 — L12M FUNNEL WITH REG E
# =============================================================================

def run_reg_e_11(ctx):
    """A8.11 — L12M new accounts funnel with Reg E."""
    _report(ctx, "\n📊 A8.11 — L12M Funnel (with Reg E)")
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    el12m = ctx.get('eligible_last_12m')
    if el12m is None or el12m.empty:
        _report(ctx, "   ⚠️ No L12M eligible data")
        ctx['results']['reg_e_11'] = {}
        return ctx

    open_l12m = ctx.get('open_last_12m')
    total_l12m = len(open_l12m) if isinstance(open_l12m, pd.DataFrame) and not open_l12m.empty else 0
    elig_l12m = len(el12m)

    wd_l12m = 0
    if 'Debit?' in el12m.columns:
        wd_l12m = int((el12m['Debit?'] == 'Yes').sum())

    p_wd_l12m = 0
    if 'Debit?' in el12m.columns and 'Business?' in el12m.columns:
        mask = (el12m['Debit?'] == 'Yes') & (el12m['Business?'] == 'No')
        p_wd_l12m = int(mask.sum())

    # Reg E in L12M
    rege_l12m = 0
    if col and p_wd_l12m > 0 and 'Debit?' in el12m.columns and 'Business?' in el12m.columns:
        mask = (el12m['Debit?'] == 'Yes') & (el12m['Business?'] == 'No')
        p_debit_df = el12m[mask]
        if col in p_debit_df.columns:
            rege_l12m = int(p_debit_df[col].astype(str).str.strip().isin(opts).sum())

    stages = [
        {'name': 'TTM\nOpens', 'total': total_l12m, 'color': '#2c7fb8'},
        {'name': 'TTM\nEligible', 'total': elig_l12m, 'color': '#ff7f0e'},
        {'name': 'TTM\nw/Debit', 'total': wd_l12m, 'color': '#41b6c4'},
        {'name': 'TTM Personal\nw/Debit', 'total': p_wd_l12m, 'color': '#2ca02c'},
        {'name': 'TTM\nw/Reg E', 'total': rege_l12m, 'color': '#9467bd'},
    ]

    funnel_df = pd.DataFrame([{'Stage': s['name'].replace('\n', ' '), 'Count': s['total']} for s in stages])
    _save(ctx, funnel_df, 'A8.11-RegE-L12M-Funnel', 'L12M Account Funnel with Reg E')

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        fig.patch.set_facecolor('white')

        rege_rate = rege_l12m / p_wd_l12m * 100 if p_wd_l12m > 0 else 0
        through_rate = rege_l12m / total_l12m * 100 if total_l12m > 0 else 0
        sd = ctx['start_date']
        ed_date = ctx['end_date']

        _render_reg_e_funnel(
            ax, stages,
            title_text="Trailing Twelve Months Account Eligibility & Reg E Funnel",
            subtitle_text=f"{sd.strftime('%B %Y')} - {ed_date.strftime('%B %Y')}",
            metrics_text=f"Reg E Rate (Personal w/Debit): {rege_rate:.1f}%\nEnd-to-End: {through_rate:.1f}%")

        plt.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_11_reg_e_l12m_funnel.png')

        _slide(ctx, 'A8.11 - Reg E L12M Funnel', {
            'title': 'TTM Account Funnel with Reg E', 'chart_path': cp, 'layout_index': 9,
            'subtitle': f"TTM Opens: {total_l12m:,} → Reg E: {rege_l12m:,} ({rege_rate:.1f}%)",
            'insights': [f"TTM opens: {total_l12m:,}", f"Eligible: {elig_l12m:,}",
                         f"Personal w/Debit: {p_wd_l12m:,}",
                         f"Reg E: {rege_l12m:,} ({rege_rate:.1f}%)"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Funnel chart: {e}")

    ctx['results']['reg_e_11'] = {'funnel': funnel_df}
    _report(ctx, f"   L12M Reg E: {rege_l12m:,}")
    return ctx


# =============================================================================
# A8.12 — 24-MONTH TREND
# =============================================================================

def run_reg_e_12(ctx):
    """A8.12 — Reg E opt-in trend over last 24 months."""
    _report(ctx, "\n📊 A8.12 — Reg E 24-Month Trend")
    base = ctx['reg_e_eligible_base']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)

    df = base.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Year_Month'] = df['Date Opened'].dt.to_period('M')
    df[col] = df[col].astype(str).str.strip()
    df['Has_RegE'] = df[col].isin(opts).astype(int)

    monthly = df.groupby('Year_Month').agg(
        Total=('Has_RegE', 'count'),
        With_RegE=('Has_RegE', 'sum')
    ).reset_index()
    monthly['Rate'] = (monthly['With_RegE'] / monthly['Total']).round(4)
    monthly['Date'] = monthly['Year_Month'].dt.to_timestamp()
    monthly['Year_Month'] = monthly['Year_Month'].astype(str)

    last_24 = monthly.tail(24)

    export_24 = last_24[['Year_Month', 'Total', 'With_RegE', 'Rate']].copy()
    _save(ctx, export_24, 'A8.12-RegE-Trend', 'Reg E 24-Month Trend')

    # Chart
    try:
        fig, ax = plt.subplots(figsize=(16, 7))
        fig.patch.set_facecolor('white')

        ax.plot(last_24['Date'], last_24['Rate'] * 100, 'o-',
               color='#2E8B57', linewidth=2.5, markersize=6, label='Reg E Rate')

        # Trend line
        if len(last_24) >= 4:
            x_num = np.arange(len(last_24))
            z = np.polyfit(x_num, last_24['Rate'].values * 100, 1)
            p = np.poly1d(z)
            ax.plot(last_24['Date'], p(x_num), '--', color='navy', linewidth=2,
                   alpha=0.6, label=f'Trend ({z[0]:+.2f}pp/mo)')

        ax.set_ylabel('Opt-In Rate (%)', fontsize=16)
        ax.set_title(f"Reg E Opt-In Trend (24 Months) — {ctx.get('client_name', '')}",
                    fontsize=20, fontweight='bold')
        ax.legend(fontsize=16)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.tick_params(axis='both', labelsize=14)
        ax.grid(True, alpha=0.3, linestyle='--')
        fig.autofmt_xdate()
        fig.tight_layout()
        cp = _save_chart(fig, ctx['chart_dir'] / 'a8_12_reg_e_trend.png')

        start_r = last_24.iloc[0]['Rate'] * 100
        end_r = last_24.iloc[-1]['Rate'] * 100
        change = end_r - start_r
        slope = z[0] if len(last_24) >= 4 else 0
        direction = 'improving' if slope > 0.1 else 'declining' if slope < -0.1 else 'stable'

        _slide(ctx, 'A8.12 - Reg E Trend', {
            'title': 'Reg E Opt-In Trend (24 Months)', 'chart_path': cp, 'layout_index': 9,
            'subtitle': f"Trend: {direction} — {start_r:.1f}% → {end_r:.1f}% ({change:+.1f}pp)",
            'insights': [f"Months analyzed: {len(last_24)}",
                         f"Current rate: {end_r:.1f}%", f"Change: {change:+.1f}pp",
                         f"Slope: {slope:+.2f}pp/month", f"Direction: {direction}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Trend chart: {e}")

    ctx['results']['reg_e_12'] = {'monthly': last_24}
    _report(ctx, f"   {len(last_24)} months plotted")
    return ctx


# =============================================================================
# A8.13 — COMPLETE BRANCH × MONTH PIVOT
# =============================================================================

def run_reg_e_13(ctx):
    """A8.13 — Complete branch × month Reg E pivot table."""
    _report(ctx, "\n📊 A8.13 — Branch × Month Pivot")
    base_l12m = ctx['reg_e_eligible_base_l12m']
    col = _reg_col(ctx)
    opts = _opt_list(ctx)
    l12m = ctx['last_12_months']

    if base_l12m is None or base_l12m.empty:
        _report(ctx, "   ⚠️ No L12M data for pivot")
        ctx['results']['reg_e_13'] = {}
        return ctx

    df = base_l12m.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Month_Year'] = df['Date Opened'].dt.strftime('%b%y')

    # Build comprehensive pivot
    branches = sorted(df['Branch'].dropna().unique())
    pivot_rows = []

    for br in branches:
        row = {'Branch': br}
        br_total = 0
        br_opted = 0
        for my in l12m:
            seg = df[(df['Branch'] == br) & (df['Month_Year'] == my)]
            t = len(seg)
            oi = len(seg[seg[col].astype(str).str.strip().isin(opts)]) if t > 0 else 0
            row[f"{my} Opens"] = t
            row[f"{my} Opt-In"] = oi
            row[f"{my} Rate"] = oi / t if t > 0 else 0
            br_total += t
            br_opted += oi

        row['Total Opens'] = br_total
        row['Total Opt-In'] = br_opted
        row['Overall Rate'] = br_opted / br_total if br_total > 0 else 0
        pivot_rows.append(row)

    pivot = pd.DataFrame(pivot_rows)
    if not pivot.empty:
        pivot = pivot.sort_values('Overall Rate', ascending=False)

        # Grand total
        totals = {'Branch': 'TOTAL'}
        for my in l12m:
            totals[f"{my} Opens"] = pivot[f"{my} Opens"].sum()
            totals[f"{my} Opt-In"] = pivot[f"{my} Opt-In"].sum()
            t_sum = pivot[f"{my} Opens"].sum()
            oi_sum = pivot[f"{my} Opt-In"].sum()
            totals[f"{my} Rate"] = oi_sum / t_sum if t_sum > 0 else 0
        totals['Total Opens'] = pivot['Total Opens'].sum()
        totals['Total Opt-In'] = pivot['Total Opt-In'].sum()
        totals['Overall Rate'] = pivot['Total Opt-In'].sum() / pivot['Total Opens'].sum() if pivot['Total Opens'].sum() > 0 else 0
        pivot = pd.concat([pivot, pd.DataFrame([totals])], ignore_index=True)

    _save(ctx, pivot, 'A8.13-RegE-Pivot', 'Branch × Month Reg E Pivot', {
        'Branches': len(branches), 'Months': len(l12m),
        'Overall Rate': f"{pivot[pivot['Branch'] == 'TOTAL']['Overall Rate'].iloc[0]:.1%}" if not pivot.empty else "N/A"})

    ctx['results']['reg_e_13'] = {'pivot': pivot}
    _report(ctx, f"   {len(branches)} branches × {len(l12m)} months")
    return ctx


# =============================================================================
# MAIN SUITE RUNNER
# =============================================================================

def run_reg_e_suite(ctx):
    """Run the full Reg E analysis suite (A8)."""
    from ars_analysis.pipeline import save_to_excel
    ctx['_save_to_excel'] = save_to_excel

    # Guard — skip if no Reg E data
    if ctx.get('reg_e_eligible_base') is None or ctx['reg_e_eligible_base'].empty:
        _report(ctx, "\n⚠️ A8 — Skipped (no Reg E eligible accounts)")
        return ctx
    if _reg_col(ctx) is None:
        _report(ctx, "\n⚠️ A8 — Skipped (no Reg E column found)")
        return ctx

    def _safe(fn, label):
        """Run an analysis function; log errors and continue."""
        try:
            return fn(ctx)
        except Exception as e:
            _report(ctx, f"   ⚠️ {label} failed: {e}")
            import traceback
            traceback.print_exc()
            return ctx

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "📋 A8 — REG E OPT-IN ANALYSIS")
    _report(ctx, "=" * 60)

    # Core data analyses
    _report(ctx, "\n── A8: Core Reg E Data ──")
    ctx = _safe(run_reg_e_1, 'A8.1')
    ctx = _safe(run_reg_e_2, 'A8.2')
    ctx = _safe(run_reg_e_3, 'A8.3')

    _report(ctx, "\n── A8: Branch & Dimensional ──")
    ctx = _safe(run_reg_e_4, 'A8.4')
    ctx = _safe(run_reg_e_4b, 'A8.4b')
    ctx = _safe(run_reg_e_5, 'A8.5')
    ctx = _safe(run_reg_e_6, 'A8.6')
    ctx = _safe(run_reg_e_7, 'A8.7')

    # A8.8/A8.9 heatmaps and branch summaries are NOT in the mapping.
    # Keep data computation but skip slide creation by not calling them.
    # Uncomment if these slides are needed in a future mapping revision.
    # _report(ctx, "\n── A8: Heatmaps & Summaries ──")
    # ctx = _safe(run_reg_e_8, 'A8.8')
    # ctx = _safe(run_reg_e_9, 'A8.9')

    _report(ctx, "\n── A8: Funnels & Trends ──")
    ctx = _safe(run_reg_e_10, 'A8.10')
    ctx = _safe(run_reg_e_11, 'A8.11')
    ctx = _safe(run_reg_e_12, 'A8.12')
    ctx = _safe(run_reg_e_13, 'A8.13')

    # Fix A8.4b/A8.4c order: run_reg_e_4 creates A8.4a then A8.4c,
    # but mapping requires A8.4a → A8.4b → A8.4c.
    reg_slides = [s for s in ctx['all_slides'] if s['category'] == 'Reg E']
    non_reg = [s for s in ctx['all_slides'] if s['category'] != 'Reg E']
    REG_ORDER = [
        # Act 1: The Headline
        'A8.1 - Reg E Overall Status',
        # Act 2: Trajectory
        'A8.12 - Reg E Trend',
        'A8.3 - Reg E L12M Monthly',
        # Act 3: The Funnel (Diagnosis)
        'A8.11 - Reg E L12M Funnel',
        'A8.10 - Reg E All-Time Funnel',
        # Act 4: The Opportunity
        'A8.5 - Reg E by Account Age',
        'A8.6 - Reg E by Holder Age',
        'A8.7 - Reg E by Product',
        # Act 5: Branch Accountability
        'A8.4b - Reg E by Branch (Vertical)',
        'A8.4a - Reg E by Branch',
        'A8.4c - Reg E Branch Scatter',
        # Act 6: Historical Context
        'A8.2 - Reg E Historical',
    ]
    order_map = {sid: i for i, sid in enumerate(REG_ORDER)}
    reg_slides.sort(key=lambda s: order_map.get(s['id'], 999))
    ctx['all_slides'] = non_reg + reg_slides

    slides = len(reg_slides)
    _report(ctx, f"\n✅ A8 complete — {slides} Reg E slides created (reordered to mapping)")
    return ctx


if __name__ == '__main__':
    print("Reg E module — import and call run_reg_e_suite(ctx)")
