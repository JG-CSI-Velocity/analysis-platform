"""
dctr.py — Comprehensive Debit Card Take Rate (DCTR) Analysis
=============================================================
Combines all A6 (data) + A7 (charts/visualizations) analyses.
Charts built inline with each analysis.

Core (A6 data):
  DCTR-1    Historical DCTR by year/decade (eligible)
  DCTR-2    Open vs Eligible comparison + chart (A7.1)
  DCTR-3    Last 12 months + chart (A7.3)
  DCTR-4/5  Personal & Business historical + chart (A7.2)
  DCTR-6/7  Personal & Business L12M monthly
  DCTR-8    Comprehensive summary table
  DCTR-9    Branch DCTR (all/personal/business × historical/L12M)
  DCTR-10   Account age breakdown + chart (A7.12)
  DCTR-11   Account holder age + chart (A7.11)
  DCTR-12   Balance range breakdown
  DCTR-13   Cross-tab: holder age × balance
  DCTR-14   Cross-tab: account age × balance
  DCTR-15   Cross-tab: branch × account age
  DCTR-16   Branch L12M monthly performance table

Extended (A7 visualizations):
  SegTrend  Segment trends: P/B × Historical/L12M grouped bar (A7.4)
  Decade    Decade trend line chart with P/B overlay (A7.5)
  L12MTrend L12M monthly DCTR trend line chart (A7.6a)
  Funnel    Historical account & debit card funnel (A7.7)
  L12MFun   L12M funnel with Personal/Business split (A7.8)
  BrTrend   Branch historical vs L12M change tracking (A7.10a)
  Heatmap   Monthly DCTR heatmap by branch (A7.13)
  Season    Seasonality: month/quarter/day-of-week (A7.14)
  Vintage   Vintage curves & cohort analysis (A7.15)
  Combo     Side-by-side combo slide (A7.1 + A7.3)

Usage:
    from dctr import run_dctr_suite
    ctx = run_dctr_suite(ctx)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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
             'square': (12, 12), 'large': (28, 14)}
    return plt.subplots(figsize=sizes.get(size, (14, 7)))


def _save_chart(fig, path):
    fig.savefig(str(path), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category='DCTR'):
    ctx['all_slides'].append({'id': slide_id, 'category': category,
                              'data': data, 'include': True})


def _dctr(df, debit_col='Debit?', yes='Yes'):
    t = len(df); w = len(df[df[debit_col] == yes])
    return t, w, (w / t if t > 0 else 0)


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get('_save_to_excel')
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   ⚠️ Export {sheet}: {e}")


def _total_row(df, label_col, label='TOTAL'):
    """Add a total row to a DCTR breakdown DataFrame."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals = {label_col: label}
    for c in num_cols:
        if 'DCTR' in c or '%' in c:
            # Recalculate rate from With Debit / Total
            wd = df['With Debit'].sum() if 'With Debit' in df.columns else 0
            ta = df['Total Accounts'].sum() if 'Total Accounts' in df.columns else 0
            totals[c] = wd / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


# =============================================================================
# CATEGORIZATION
# =============================================================================

AGE_ORDER = ['0-6 months', '6-12 months', '1-2 years', '2-5 years', '5-10 years', '10+ years']
HOLDER_AGE_ORDER = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+']
BALANCE_ORDER = ['Negative', '$0-$499', '$500-$999', '$1K-$2.5K', '$2.5K-$5K',
                 '$5K-$10K', '$10K-$25K', '$25K-$50K', '$50K-$100K', '$100K+']


def categorize_account_age(days):
    if pd.isna(days): return 'Unknown'
    if days < 180: return '0-6 months'
    if days < 365: return '6-12 months'
    if days < 730: return '1-2 years'
    if days < 1825: return '2-5 years'
    if days < 3650: return '5-10 years'
    return '10+ years'


def categorize_holder_age(age):
    if pd.isna(age): return 'Unknown'
    if age < 25: return '18-24'
    if age < 35: return '25-34'
    if age < 45: return '35-44'
    if age < 55: return '45-54'
    if age < 65: return '55-64'
    return '65+'


def categorize_balance(bal):
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


def simplify_account_age(age_range):
    if age_range in ('0-6 months', '6-12 months'): return 'New (0-1 year)'
    if age_range in ('1-2 years', '2-5 years'): return 'Recent (1-5 years)'
    if age_range in ('5-10 years', '10+ years'): return 'Mature (5+ years)'
    return 'Unknown'


def map_to_decade(year):
    if pd.isna(year): return None
    recent = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
    if year < 1970: return "Before 1970"
    if int(year) in recent: return str(int(year))
    return f"{(int(year) // 10) * 10}s"


# =============================================================================
# CORE: analyze_historical_dctr
# =============================================================================

def analyze_historical_dctr(dataset, name="Eligible"):
    """Returns (yearly_df, decade_df, insights_dict)."""
    if dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            'total_accounts': 0, 'with_debit_count': 0, 'overall_dctr': 0, 'recent_dctr': 0}

    df = dataset.copy()
    df['Date Opened'] = pd.to_datetime(df['Date Opened'], errors='coerce')
    df['Year'] = df['Date Opened'].dt.year
    valid = df.dropna(subset=['Year'])
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame(), {
            'total_accounts': 0, 'with_debit_count': 0, 'overall_dctr': 0, 'recent_dctr': 0}

    valid = valid.copy()
    valid['Decade'] = valid['Year'].apply(map_to_decade)

    # Yearly
    rows = []
    for yr in sorted(valid['Year'].dropna().unique()):
        yd = valid[valid['Year'] == yr]
        t, w, d = _dctr(yd)
        p = yd[yd['Business?'] == 'No']; b = yd[yd['Business?'] == 'Yes']
        rows.append({'Year': int(yr), 'Total Accounts': t, 'With Debit': w,
                     'Without Debit': t - w, 'DCTR %': d,
                     'Personal w/Debit': len(p[p['Debit?'] == 'Yes']),
                     'Business w/Debit': len(b[b['Debit?'] == 'Yes'])})
    yearly = pd.DataFrame(rows)
    if not yearly.empty:
        yearly = _total_row(yearly, 'Year')

    # Decade
    drows = []
    decade_keys = sorted(valid['Decade'].dropna().unique(),
                         key=lambda x: int(x) if x.isdigit() else (0 if 'Before' in str(x) else int(str(x).replace('s', ''))))
    for dec in decade_keys:
        dd = valid[valid['Decade'] == dec]
        t, w, d = _dctr(dd)
        drows.append({'Decade': dec, 'Total Accounts': t, 'With Debit': w,
                      'Without Debit': t - w, 'DCTR %': d})
    decade = pd.DataFrame(drows)

    # Overall insights
    t_all, w_all, o_dctr = _dctr(valid)
    recent = valid[valid['Year'].isin([2023, 2024, 2025, 2026])]
    _, _, r_dctr = _dctr(recent) if len(recent) else (0, 0, 0)

    return yearly, decade, {
        'total_accounts': t_all, 'with_debit_count': w_all,
        'overall_dctr': o_dctr, 'recent_dctr': r_dctr,
        'years_covered': len(rows)
    }


# =============================================================================
# CORE: L12M monthly breakdown
# =============================================================================

def _l12m_monthly(dataset, last_12_months):
    """Monthly DCTR table for L12M accounts."""
    if dataset.empty:
        return pd.DataFrame(), {'total_accounts': 0, 'with_debit': 0, 'dctr': 0, 'months_active': 0}

    dc = dataset.copy()
    dc['Date Opened'] = pd.to_datetime(dc['Date Opened'], errors='coerce')
    dc['Month_Year'] = dc['Date Opened'].dt.strftime('%b%y')

    rows = []
    for my in last_12_months:
        ma = dc[dc['Month_Year'] == my]
        t, w, d = _dctr(ma)
        rows.append({'Month': my, 'Total Accounts': t, 'With Debit': w,
                     'Without Debit': t - w, 'DCTR %': d})
    monthly = pd.DataFrame(rows)
    if not monthly.empty:
        monthly = _total_row(monthly, 'Month')

    active = sum(1 for r in rows if r['Total Accounts'] > 0)
    ta = monthly[monthly['Month'] == 'TOTAL']['Total Accounts'].iloc[0] if not monthly.empty else 0
    tw = monthly[monthly['Month'] == 'TOTAL']['With Debit'].iloc[0] if not monthly.empty else 0
    return monthly, {'total_accounts': int(ta), 'with_debit': int(tw),
                     'dctr': tw / ta if ta else 0, 'months_active': active}


# =============================================================================
# CORE: branch DCTR
# =============================================================================

def _branch_dctr(dataset, branch_mapping=None):
    if dataset.empty:
        return pd.DataFrame(), {}
    dc = dataset.copy()
    if branch_mapping:
        dc['Branch Name'] = dc['Branch'].map(branch_mapping).fillna(dc['Branch'])
    else:
        dc['Branch Name'] = dc['Branch']

    rows = []
    for bn in sorted(dc['Branch Name'].unique()):
        ba = dc[dc['Branch Name'] == bn]
        t, w, d = _dctr(ba)
        rows.append({'Branch': bn, 'Total Accounts': t, 'With Debit': w,
                     'Without Debit': t - w, 'DCTR %': d})
    bdf = pd.DataFrame(rows).sort_values('DCTR %', ascending=False)
    if not bdf.empty:
        bdf = _total_row(bdf, 'Branch')

    dr = bdf[bdf['Branch'] != 'TOTAL']
    ins = {}
    if not dr.empty:
        best = dr.loc[dr['DCTR %'].idxmax()]
        worst = dr.loc[dr['DCTR %'].idxmin()]
        ins = {'total_branches': len(dr),
               'best_branch': best['Branch'], 'best_dctr': best['DCTR %'],
               'worst_branch': worst['Branch'], 'worst_dctr': worst['DCTR %']}
    return bdf, ins


# =============================================================================
# CORE: dimension DCTR
# =============================================================================

def _by_dimension(dataset, col, cat_fn, order, label):
    if dataset.empty:
        return pd.DataFrame(), {}
    dc = dataset.copy()
    dc[label] = dc[col].apply(cat_fn)
    valid = dc[dc[label] != 'Unknown']

    rows = []
    for cat in order:
        seg = valid[valid[label] == cat]
        if len(seg) == 0: continue
        t, w, d = _dctr(seg)
        p = seg[seg['Business?'] == 'No']; b = seg[seg['Business?'] == 'Yes']
        rows.append({label: cat, 'Total Accounts': t, 'With Debit': w,
                     'Without Debit': t - w, 'DCTR %': d,
                     'Personal w/Debit': len(p[p['Debit?'] == 'Yes']),
                     'Business w/Debit': len(b[b['Debit?'] == 'Yes'])})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = _total_row(df, label)

    dr = df[df[label] != 'TOTAL']
    ins = {}
    if not dr.empty:
        hi = dr.loc[dr['DCTR %'].idxmax()]
        lo = dr.loc[dr['DCTR %'].idxmin()]
        ins = {'highest': hi[label], 'highest_dctr': hi['DCTR %'],
               'lowest': lo[label], 'lowest_dctr': lo['DCTR %'],
               'spread': hi['DCTR %'] - lo['DCTR %'],
               'total_with_data': len(valid), 'coverage': len(valid) / len(dataset) if len(dataset) else 0}
    return df, ins


# =============================================================================
# CORE: cross-tab
# =============================================================================

def _crosstab(dataset, rc, rfn, ro, rl, cc, cfn, co, cl):
    if dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
    dc = dataset.copy()
    dc[rl] = dc[rc].apply(rfn); dc[cl] = dc[cc].apply(cfn)
    valid = dc[(dc[rl] != 'Unknown') & (dc[cl] != 'Unknown')]

    rows = []
    for r in ro:
        for c in co:
            seg = valid[(valid[rl] == r) & (valid[cl] == c)]
            if len(seg) > 0:
                t, w, d = _dctr(seg)
                rows.append({rl: r, cl: c, 'Total Accounts': t, 'With Debit': w, 'DCTR %': d})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame(), {}

    dp = detail.pivot_table(index=rl, columns=cl, values='DCTR %')
    cp = detail.pivot_table(index=rl, columns=cl, values='Total Accounts')
    dp = dp.reindex(index=[x for x in ro if x in dp.index],
                    columns=[x for x in co if x in dp.columns])
    cp = cp.reindex(index=[x for x in ro if x in cp.index],
                    columns=[x for x in co if x in cp.columns])

    meaningful = detail[detail['Total Accounts'] > 10]
    ins = {}
    if not meaningful.empty:
        hi = meaningful.loc[meaningful['DCTR %'].idxmax()]
        lo = meaningful.loc[meaningful['DCTR %'].idxmin()]
        ins = {'highest_seg': f"{hi[rl]} × {hi[cl]}", 'highest_dctr': hi['DCTR %'],
               'lowest_seg': f"{lo[rl]} × {lo[cl]}", 'lowest_dctr': lo['DCTR %'],
               'segments': len(detail)}
    return detail, dp, cp, ins


# =============================================================================
# DCTR-1: Historical DCTR (Eligible)
# =============================================================================

def run_dctr_1(ctx):
    _report(ctx, "\n📅 DCTR-1 — Historical DCTR (Eligible)")
    yearly, decade, ins = analyze_historical_dctr(ctx['eligible_data'], "Eligible")
    _save(ctx, {'Yearly': yearly, 'Decade': decade}, 'DCTR-1-Historical',
          'Historical Debit Card Take Rate',
          {'Overall DCTR': f"{ins['overall_dctr']:.1%}", 'Accounts': f"{ins['total_accounts']:,}",
           'With Debit': f"{ins['with_debit_count']:,}", 'Recent DCTR': f"{ins['recent_dctr']:.1%}"})
    ctx['results']['dctr_1'] = {'yearly': yearly, 'decade': decade, 'insights': ins}
    _report(ctx, f"   Overall: {ins['overall_dctr']:.1%} | Recent: {ins['recent_dctr']:.1%}")
    return ctx


# =============================================================================
# DCTR-2: Open vs Eligible + Chart (A6.2 + A7.1)
# =============================================================================

def run_dctr_2(ctx):
    _report(ctx, "\n📊 DCTR-2 — Open vs Eligible Comparison")
    oa = ctx['open_accounts']; ed = ctx['eligible_data']
    open_yearly, open_decade, open_ins = analyze_historical_dctr(oa, "Open")
    hist_ins = ctx['results']['dctr_1']['insights']

    comparison = pd.DataFrame([
        {'Account Group': 'All Open', 'Total Accounts': len(oa),
         'With Debit': open_ins['with_debit_count'], 'DCTR %': open_ins['overall_dctr']},
        {'Account Group': 'Eligible Only', 'Total Accounts': hist_ins['total_accounts'],
         'With Debit': hist_ins['with_debit_count'], 'DCTR %': hist_ins['overall_dctr']},
    ])
    diff = hist_ins['overall_dctr'] - open_ins['overall_dctr']

    _save(ctx, {'Comparison': comparison, 'Open-Yearly': open_yearly, 'Open-Decade': open_decade},
          'DCTR-2-OpenVsEligible', 'DCTR: Open vs Eligible',
          {'Open DCTR': f"{open_ins['overall_dctr']:.1%}", 'Eligible DCTR': f"{hist_ins['overall_dctr']:.1%}",
           'Difference': f"{diff:+.1%}"})

    # Chart A7.1
    try:
        chart_dir = ctx['chart_dir']
        fig, ax = _fig(ctx, 'half')
        od, ed_v = open_ins['overall_dctr'] * 100, hist_ins['overall_dctr'] * 100
        bars = ax.bar(['All Open\nAccounts', 'Eligible\nAccounts'], [od, ed_v],
                      color=['#70AD47', '#4472C4'], width=0.5, edgecolor='black', linewidth=2, alpha=0.8)
        for bar, v, c in zip(bars, [od, ed_v], [open_ins['with_debit_count'], hist_ins['with_debit_count']]):
            ax.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.1f}%',
                    ha='center', fontweight='bold', fontsize=22)
            ax.text(bar.get_x() + bar.get_width()/2, v/2, f'{c:,}\naccounts',
                    ha='center', fontweight='bold', fontsize=18, color='white')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('DCTR: Open vs Eligible Accounts', fontsize=24, fontweight='bold', pad=20)
        ax.set_ylim(0, max(od, ed_v) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='both', labelsize=18)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        color = 'green' if diff > 0 else 'red'
        ax.text(0.5, 0.5, f'{"↑" if diff > 0 else "↓"} {abs(diff*100):.1f}%\nimprovement',
                transform=ax.transAxes, ha='center', fontsize=20, fontweight='bold', color=color,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=color, linewidth=2))
        ax.grid(False); ax.set_axisbelow(True)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_open_vs_eligible.png')
        ctx['results']['dctr_2_chart'] = cp
    except Exception as e:
        cp = None
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['dctr_2'] = {'comparison': comparison, 'insights': {
        'open_dctr': open_ins['overall_dctr'], 'eligible_dctr': hist_ins['overall_dctr'],
        'difference': diff, 'open_total': len(oa), 'eligible_total': hist_ins['total_accounts']}}
    _report(ctx, f"   Open: {open_ins['overall_dctr']:.1%} | Eligible: {hist_ins['overall_dctr']:.1%} | Δ {diff:+.1%}")
    return ctx


# =============================================================================
# DCTR-3: Last 12 Months + Chart (A6.3 + A7.3)
# =============================================================================

def run_dctr_3(ctx):
    _report(ctx, "\n📅 DCTR-3 — Last 12 Months")
    el12 = ctx['eligible_last_12m']; l12m = ctx['last_12_months']
    sd, ed = ctx['start_date'], ctx['end_date']

    if el12 is None or el12.empty:
        ctx['results']['dctr_3'] = {'insights': {'total_accounts': 0, 'dctr': 0}}
        _report(ctx, "   ⚠️ No L12M data"); return ctx

    # Filter to exact date range
    el12f = el12[(pd.to_datetime(el12['Date Opened'], errors='coerce') >= sd) &
                 (pd.to_datetime(el12['Date Opened'], errors='coerce') <= ed)].copy()

    monthly, l12m_ins = _l12m_monthly(el12f, l12m)
    yearly, decade, yins = analyze_historical_dctr(el12f, "L12M")

    overall = ctx['results']['dctr_1']['insights']['overall_dctr']
    comp = l12m_ins['dctr'] - overall

    _save(ctx, {'Monthly': monthly, 'Yearly': yearly}, 'DCTR-3-L12M',
          'Last 12 Months DCTR',
          {'L12M DCTR': f"{l12m_ins['dctr']:.1%}", 'vs Overall': f"{comp:+.1%}",
           'Accounts': f"{l12m_ins['total_accounts']:,}",
           'Period': f"{sd.strftime('%b %Y')} - {ed.strftime('%b %Y')}"})

    # Chart A7.3: Historical vs L12M
    try:
        chart_dir = ctx['chart_dir']
        fig, ax = _fig(ctx, 'half')
        hd = overall * 100; ld = l12m_ins['dctr'] * 100
        ht = ctx['results']['dctr_1']['insights']['total_accounts']
        lt = l12m_ins['total_accounts']
        bars = ax.bar(['Historical\n(All Time)', 'Trailing Twelve Months'], [hd, ld],
                      color=['#5B9BD5', '#FFC000'], width=0.5, edgecolor='black', linewidth=2, alpha=0.8)
        for bar, v, c in zip(bars, [hd, ld], [ht, lt]):
            ax.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.1f}%',
                    ha='center', fontweight='bold', fontsize=22)
            ax.text(bar.get_x() + bar.get_width()/2, v/2, f'{c:,}\naccounts',
                    ha='center', fontweight='bold', fontsize=18, color='white')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('Historical vs Recent DCTR', fontsize=24, fontweight='bold', pad=20)
        ax.set_ylim(0, max(hd, ld) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='both', labelsize=18)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        t = comp * 100; tc = 'green' if t > 0 else 'red' if t < 0 else 'gray'
        ax.text(0.5, 0.5, f'{"↑" if t > 0 else "↓"} {abs(t):.1f}%',
                transform=ax.transAxes, ha='center', fontsize=20, fontweight='bold', color=tc,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=tc, linewidth=2))
        ax.grid(False); ax.set_axisbelow(True)
        plt.tight_layout()
        cp3 = _save_chart(fig, chart_dir / 'dctr_hist_vs_l12m.png')
        ctx['results']['dctr_3_chart'] = cp3
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    l12m_ins['comparison_to_overall'] = comp
    ctx['results']['dctr_3'] = {'monthly': monthly, 'yearly': yearly, 'insights': l12m_ins}
    _report(ctx, f"   L12M: {l12m_ins['dctr']:.1%} ({l12m_ins['total_accounts']:,} accts) | vs Overall: {comp:+.1%}")
    return ctx


# =============================================================================
# DCTR-4/5: Personal & Business Historical + Chart (A6.4/5 + A7.2)
# =============================================================================

def run_dctr_4_5(ctx):
    _report(ctx, "\n👤 DCTR-4/5 — Personal & Business Historical")
    ep = ctx['eligible_personal']; eb = ctx['eligible_business']

    p_yr, p_dec, p_ins = analyze_historical_dctr(ep, "Personal")
    _save(ctx, {'Yearly': p_yr, 'Decade': p_dec}, 'DCTR-4-Personal', 'Personal DCTR',
          {'Personal DCTR': f"{p_ins.get('overall_dctr', 0):.1%}", 'Count': f"{len(ep):,}"})

    has_biz = len(eb) > 0
    if has_biz:
        b_yr, b_dec, b_ins = analyze_historical_dctr(eb, "Business")
        _save(ctx, {'Yearly': b_yr, 'Decade': b_dec}, 'DCTR-5-Business', 'Business DCTR',
              {'Business DCTR': f"{b_ins.get('overall_dctr', 0):.1%}", 'Count': f"{len(eb):,}"})
    else:
        b_yr, b_dec, b_ins = pd.DataFrame(), pd.DataFrame(), {'total_accounts': 0, 'overall_dctr': 0, 'with_debit_count': 0}

    # Chart A7.2: Personal vs Business bar
    try:
        chart_dir = ctx['chart_dir']
        overall = ctx['results']['dctr_1']['insights']['overall_dctr'] * 100
        fig, ax = _fig(ctx, 'single')

        if has_biz:
            cats = ['Personal', 'Business']; vals = [p_ins['overall_dctr']*100, b_ins['overall_dctr']*100]
            colors = ['#4472C4', '#ED7D31']
            cts = [p_ins['with_debit_count'], b_ins['with_debit_count']]
        else:
            cats = ['Personal']; vals = [p_ins['overall_dctr']*100]
            colors = ['#4472C4']; cts = [p_ins['with_debit_count']]

        bars = ax.bar(cats, vals, color=colors, edgecolor='black', linewidth=2, alpha=0.9, width=0.5)
        for bar, v, c in zip(bars, vals, cts):
            ax.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.1f}%',
                    ha='center', fontweight='bold', fontsize=22)
            if v > 10:
                ax.text(bar.get_x() + bar.get_width()/2, v/2, f'{c:,}\naccts',
                        ha='center', fontsize=18, fontweight='bold', color='white')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('Personal vs Business DCTR', fontsize=24, fontweight='bold', pad=20)
        ax.set_ylim(0, max(vals) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='both', labelsize=18)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        ax.text(0.02, 0.98, f'Overall: {overall:.1f}%', transform=ax.transAxes,
                fontsize=18, va='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='#eee', alpha=0.8))
        plt.tight_layout()
        _save_chart(fig, chart_dir / 'dctr_personal_vs_business.png')
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['dctr_4'] = {'yearly': p_yr, 'decade': p_dec, 'insights': p_ins}
    ctx['results']['dctr_5'] = {'yearly': b_yr, 'decade': b_dec, 'insights': b_ins}
    _report(ctx, f"   Personal: {p_ins.get('overall_dctr', 0):.1%} | Business: {b_ins.get('overall_dctr', 0):.1%}")
    return ctx


# =============================================================================
# DCTR-6/7: Personal & Business L12M Monthly (A6.6/7)
# =============================================================================

def run_dctr_6_7(ctx):
    _report(ctx, "\n📅 DCTR-6/7 — Personal & Business L12M Monthly")
    l12m = ctx['last_12_months']

    # Personal L12M
    epl = ctx['eligible_personal_last_12m']
    pl_monthly, pl_ins = _l12m_monthly(epl, l12m)
    _save(ctx, pl_monthly, 'DCTR-6-Personal-L12M', 'Personal L12M DCTR',
          {'DCTR': f"{pl_ins['dctr']:.1%}", 'Accounts': f"{pl_ins['total_accounts']:,}",
           'Active Months': f"{pl_ins['months_active']}"})
    ctx['results']['dctr_6'] = {'monthly': pl_monthly, 'insights': pl_ins}
    _report(ctx, f"   Personal L12M: {pl_ins['dctr']:.1%} ({pl_ins['total_accounts']:,} accts)")

    # Business L12M
    ebl = ctx['eligible_business_last_12m']
    bl_monthly, bl_ins = _l12m_monthly(ebl, l12m)
    _save(ctx, bl_monthly, 'DCTR-7-Business-L12M', 'Business L12M DCTR',
          {'DCTR': f"{bl_ins['dctr']:.1%}", 'Accounts': f"{bl_ins['total_accounts']:,}"})
    ctx['results']['dctr_7'] = {'monthly': bl_monthly, 'insights': bl_ins}
    _report(ctx, f"   Business L12M: {bl_ins['dctr']:.1%} ({bl_ins['total_accounts']:,} accts)")
    return ctx


# =============================================================================
# DCTR-8: Comprehensive Summary Table (A6.8)
# =============================================================================

def run_dctr_8(ctx):
    _report(ctx, "\n📊 DCTR-8 — Comprehensive Summary")
    r = ctx['results']
    rows = []

    def _add(label, cat, ins_key, total_key='total_accounts', wd_key='with_debit_count', dctr_key='overall_dctr'):
        ins = r.get(ins_key, {}).get('insights', {})
        if not ins: return
        ta = ins.get(total_key, 0)
        if ta == 0: return
        wd = ins.get(wd_key, ins.get('with_debit', 0))
        dc = ins.get(dctr_key, ins.get('dctr', 0))
        rows.append({'Account Type': label, 'Category': cat, 'Total Accounts': ta,
                     'With Debit': wd, 'Without Debit': ta - wd, 'DCTR %': dc})

    _add('Eligible Accounts', 'Overall', 'dctr_1')
    _add('Open Accounts (All)', 'Overall', 'dctr_2',
         total_key='open_total', wd_key='open_total', dctr_key='open_dctr')

    # Fix Open — get from comparison
    d2 = r.get('dctr_2', {}).get('insights', {})
    if d2:
        ot = d2.get('open_total', 0)
        od = d2.get('open_dctr', 0)
        if ot > 0:
            # Replace last entry if it was wrong
            rows = [x for x in rows if x['Account Type'] != 'Open Accounts (All)']
            ow = int(od * ot)
            rows.append({'Account Type': 'Open Accounts (All)', 'Category': 'Overall',
                         'Total Accounts': ot, 'With Debit': ow, 'Without Debit': ot - ow, 'DCTR %': od})

    # L12M All
    d3 = r.get('dctr_3', {}).get('insights', {})
    if d3.get('total_accounts', 0) > 0:
        ta = d3['total_accounts']; wd = d3['with_debit']; dc = d3['dctr']
        rows.append({'Account Type': 'Trailing Twelve Months (All)', 'Category': 'Time Period',
                     'Total Accounts': ta, 'With Debit': wd, 'Without Debit': ta - wd, 'DCTR %': dc})

    _add('Personal (Historical)', 'Account Type', 'dctr_4')
    _add('Business (Historical)', 'Account Type', 'dctr_5')

    # Personal/Business L12M
    for k, lbl in [('dctr_6', 'Personal (TTM)'), ('dctr_7', 'Business (TTM)')]:
        ins = r.get(k, {}).get('insights', {})
        if ins.get('total_accounts', 0) > 0:
            ta = ins['total_accounts']; wd = ins['with_debit']; dc = ins['dctr']
            rows.append({'Account Type': lbl, 'Category': 'Time Period',
                         'Total Accounts': ta, 'With Debit': wd, 'Without Debit': ta - wd, 'DCTR %': dc})

    summary = pd.DataFrame(rows)
    _save(ctx, summary, 'DCTR-8-Summary', 'Comprehensive DCTR Summary',
          {'Categories': f"{len(rows)}"})
    ctx['results']['dctr_8'] = {'summary': summary}
    _report(ctx, f"   {len(rows)} categories summarized")
    return ctx


# =============================================================================
# DCTR-9: Branch DCTR (A6.9 a/b/c/d + A7.10b chart)
# =============================================================================

def run_dctr_9(ctx):
    _report(ctx, "\n🏢 DCTR-9 — Branch Analysis")
    bm = ctx['config'].get('BranchMapping', {})
    chart_dir = ctx['chart_dir']

    # A6.9a: All eligible historical
    br_all, br_ins = _branch_dctr(ctx['eligible_data'], bm)
    _save(ctx, br_all, 'DCTR-9a-Branch-All', 'Branch DCTR - All Eligible',
          {'Branches': f"{br_ins.get('total_branches', 0)}",
           'Best': f"{br_ins.get('best_branch', 'N/A')} ({br_ins.get('best_dctr', 0):.1%})",
           'Worst': f"{br_ins.get('worst_branch', 'N/A')} ({br_ins.get('worst_dctr', 0):.1%})"})
    _report(ctx, f"   All: {br_ins.get('total_branches', 0)} branches | Best: {br_ins.get('best_branch', 'N/A')} ({br_ins.get('best_dctr', 0):.1%})")

    # A6.9b: All L12M
    br_l12, br_l12_ins = _branch_dctr(ctx['eligible_last_12m'], bm)
    if not br_l12.empty:
        _save(ctx, br_l12, 'DCTR-9b-Branch-L12M', 'Branch DCTR - L12M',
              {'Branches': f"{br_l12_ins.get('total_branches', 0)}"})

    # A6.9c: Personal L12M
    br_pl, br_pl_ins = _branch_dctr(ctx['eligible_personal_last_12m'], bm)
    if not br_pl.empty:
        _save(ctx, br_pl, 'DCTR-9c-Branch-Personal-L12M', 'Branch DCTR - Personal L12M',
              {'Branches': f"{br_pl_ins.get('total_branches', 0)}"})

    # A6.9d: Business L12M
    br_bl, br_bl_ins = _branch_dctr(ctx['eligible_business_last_12m'], bm)
    if not br_bl.empty:
        _save(ctx, br_bl, 'DCTR-9d-Branch-Business-L12M', 'Branch DCTR - Business L12M',
              {'Branches': f"{br_bl_ins.get('total_branches', 0)}"})

    # Chart A7.10b: Historical vs L12M by branch
    try:
        hist_dr = br_all[br_all['Branch'] != 'TOTAL'].copy()
        l12m_dr = br_l12[br_l12['Branch'] != 'TOTAL'].copy()
        if not hist_dr.empty and not l12m_dr.empty:
            merged = hist_dr[['Branch', 'DCTR %', 'Total Accounts']].rename(
                columns={'DCTR %': 'Historical DCTR', 'Total Accounts': 'Hist Volume'})
            l12m_cols = l12m_dr[['Branch', 'DCTR %', 'Total Accounts']].rename(
                columns={'DCTR %': 'L12M DCTR', 'Total Accounts': 'L12M Volume'})
            merged = merged.merge(l12m_cols, on='Branch', how='left').fillna(0)
            merged = merged.sort_values('Historical DCTR', ascending=False)
            merged['Change'] = merged['L12M DCTR'] - merged['Historical DCTR']

            fig, ax1 = plt.subplots(figsize=(16, 8))
            x = np.arange(len(merged)); w = 0.35
            b1 = ax1.bar(x - w/2, merged['Hist Volume'], w, label='Historical', color='#BDC3C7', edgecolor='white', alpha=0.8)
            b2 = ax1.bar(x + w/2, merged['L12M Volume'], w, label='TTM', color='#85C1E9', edgecolor='white', alpha=0.8)
            ax1.set_ylabel('Accounts', fontsize=20, fontweight='bold')
            ax1.set_xticks(x)
            ax1.set_xticklabels(merged['Branch'], rotation=45, ha='right', fontsize=18)
            ax1.tick_params(axis='y', labelsize=18)

            ax2 = ax1.twinx()
            ax2.plot(x, merged['Historical DCTR']*100, 'o-', color='#1a5276', lw=3, ms=10, label='Hist DCTR')
            ax2.plot(x, merged['L12M DCTR']*100, 'o-', color='#2E7D32', lw=3, ms=12, label='TTM DCTR')
            for i, v in enumerate(merged['L12M DCTR']*100):
                if v > 0:
                    ax2.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=18, fontweight='bold', color='#2E7D32')
            ax2.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax2.tick_params(axis='y', labelsize=18)
            ax2.grid(False); [s.set_visible(False) for s in ax2.spines.values()]

            plt.title('Branch DCTR: Volume & Rate Comparison', fontsize=24, fontweight='bold', pad=20)
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=16)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / 'dctr_branch_comparison.png')
            # Note: This is a supplementary view; A7.10a slide comes from run_dctr_branch_trend

            improving = (merged['Change'] > 0).sum()
            _save(ctx, merged, 'DCTR-Branch-Comparison', 'Branch DCTR Comparison',
                  {'Improving': f"{improving} of {len(merged)}"})
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch comparison chart: {e}")

    # Branch bar chart (top 10)
    try:
        fig, ax = _fig(ctx, 'single')
        dr = br_all[br_all['Branch'] != 'TOTAL'].head(10).iloc[::-1]
        ax.barh(dr['Branch'].astype(str), dr['DCTR %'] * 100, color='#2E86AB',
                edgecolor='black', linewidth=1.5, alpha=0.9)
        ax.set_xlabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('Branch Debit Card Take Rate — Top 10', fontsize=24, fontweight='bold', pad=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='both', labelsize=18)
        for i, (d, t) in enumerate(zip(dr['DCTR %'], dr['Total Accounts'])):
            ax.text(d * 100 + 0.5, i, f'{d:.1%} ({int(t):,})', va='center', fontsize=18, fontweight='bold')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        plt.tight_layout()
        cp2 = _save_chart(fig, chart_dir / 'dctr_branch_top10.png')
        _slide(ctx, 'A7.10c - Branch Top 10', {
            'title': 'Branch Debit Card Take Rate',
            'subtitle': f"{br_ins.get('best_branch', '')} leads at {br_ins.get('best_dctr', 0):.1%}",
            'kpis': {'Branches': f"{br_ins.get('total_branches', 0)}",
                     'Best': f"{br_ins.get('best_dctr', 0):.1%}"},
            'chart_path': cp2, 'layout_index': 4})
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch bar chart: {e}")

    ctx['results']['dctr_9'] = {'all': br_ins, 'l12m': br_l12_ins}
    return ctx


# =============================================================================
# DCTR-10: Account Age (A6.10)
# =============================================================================

def run_dctr_10(ctx):
    _report(ctx, "\n📅 DCTR-10 — Account Age Breakdown")
    ed = ctx['eligible_data'].copy()
    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    ed['Account Age Days'] = (pd.Timestamp.now() - ed['Date Opened']).dt.days
    df, ins = _by_dimension(ed, 'Account Age Days', categorize_account_age, AGE_ORDER, 'Account Age')
    _save(ctx, df, 'DCTR-10-AccountAge', 'DCTR by Account Age',
          {'Highest': f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
           'Lowest': f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})"})

    # Chart A7.12: Account Age DCTR — line chart with volume bars (matching notebook)
    try:
        chart_dir = ctx['chart_dir']
        overall = ctx['results']['dctr_1']['insights']['overall_dctr'] * 100
        dr = df[df['Account Age'] != 'TOTAL']
        if not dr.empty:
            fig, ax = plt.subplots(figsize=(14, 7))
            x = np.arange(len(dr))
            vals = dr['DCTR %'].values * 100
            volumes = dr['Total Accounts'].values

            # Volume bars on secondary axis
            ax2 = ax.twinx()
            ax2.bar(x, volumes, alpha=0.3, color='gray', edgecolor='none', width=0.6)
            for i, v in enumerate(volumes):
                if v > 0:
                    ax2.text(i, v * 0.05, f'{v:,}', ha='center', va='bottom',
                             fontsize=16, color='gray')
            ax2.set_ylabel('Account Volume', fontsize=24, color='gray')
            ax2.set_ylim(0, max(volumes) * 2 if len(volumes) else 100)
            ax2.tick_params(axis='y', colors='gray', labelsize=20)

            # DCTR line chart on primary axis
            ax.plot(x, vals, color='#2E86AB', linewidth=4, marker='o', markersize=12,
                    label='DCTR %', zorder=3)
            for i, v in enumerate(vals):
                ax.text(i, v + 2, f'{v:.1f}%', ha='center', va='bottom',
                        fontsize=20, fontweight='bold', color='#2E86AB')

            ax.set_title('Eligible Accounts DCTR by Account Age/Maturity',
                         fontsize=24, fontweight='bold', pad=25)
            ax.set_xlabel('Account Age', fontsize=20, fontweight='bold')
            ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold', color='#2E86AB')
            ax.set_xticks(x)
            ax.set_xticklabels(dr['Account Age'].values, fontsize=18, rotation=45, ha='right')
            ax.tick_params(axis='y', labelsize=20, colors='#2E86AB')
            ax.set_ylim(0, max(vals) * 1.2 if len(vals) else 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
            ax.spines['top'].set_visible(False)
            ax2.spines['top'].set_visible(False)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / 'dctr_account_age.png')

            newest = vals[0] if len(vals) else 0
            oldest = vals[-1] if len(vals) else 0
            gap = newest - oldest
            trend = "newer accounts have higher DCTR" if gap > 5 else \
                    "mature accounts have higher DCTR" if gap < -5 else \
                    "DCTR is consistent across account ages"
            _slide(ctx, 'A7.12 - DCTR by Account Age', {
                'title': 'Eligible Accounts DCTR by Account Age/Maturity',
                'subtitle': f"Ranges from {ins.get('lowest_dctr', 0):.0%} to {ins.get('highest_dctr', 0):.0%} — {trend}",
                'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Account age chart: {e}")

    ctx['results']['dctr_10'] = {'df': df, 'insights': ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest | {ins.get('lowest', '?')} lowest")
    return ctx


# =============================================================================
# DCTR-11: Account Holder Age + Chart (A6.11 + A7.11)
# =============================================================================

def run_dctr_11(ctx):
    _report(ctx, "\n👤 DCTR-11 — Account Holder Age")
    ed = ctx['eligible_data']

    if 'Account Holder Age' not in ed.columns:
        _report(ctx, "   ⚠️ No 'Account Holder Age' column")
        ctx['results']['dctr_11'] = {}; return ctx

    edc = ed.copy()
    edc['Account Holder Age'] = pd.to_numeric(edc['Account Holder Age'], errors='coerce')
    valid = edc[(edc['Account Holder Age'] >= 18) & (edc['Account Holder Age'] <= 120)].copy()
    df, ins = _by_dimension(valid, 'Account Holder Age', categorize_holder_age, HOLDER_AGE_ORDER, 'Age Group')
    _save(ctx, df, 'DCTR-11-HolderAge', 'DCTR by Holder Age',
          {'Highest': f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
           'Lowest': f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})",
           'Coverage': f"{ins.get('coverage', 0):.1%}"})

    # Chart A7.11: Holder Age DCTR — gradient blues, large fonts (matching notebook)
    try:
        chart_dir = ctx['chart_dir']
        fig, ax = plt.subplots(figsize=(14, 7))
        dr = df[df['Age Group'] != 'TOTAL']
        vals = dr['DCTR %'].values * 100
        volumes = dr['Total Accounts'].values
        x = np.arange(len(dr))

        # Gradient blues matching notebook
        colors = plt.cm.Blues(np.linspace(0.5, 0.9, len(dr)))
        bars = ax.bar(x, vals, color=colors, edgecolor='black', linewidth=2, alpha=0.9)

        for i, (bar, v, vol) in enumerate(zip(bars, vals, volumes)):
            ax.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.1f}%',
                    ha='center', fontsize=24, fontweight='bold')
            if v > 10:
                ax.text(bar.get_x() + bar.get_width()/2, v/2, f'{vol:,}\naccts',
                        ha='center', fontsize=18, fontweight='bold', color='white')

        ax.set_title('Eligible Accounts DCTR by Account Holder Age',
                     fontsize=24, fontweight='bold', pad=25)
        ax.set_xlabel('Age Group', fontsize=20, fontweight='bold')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(dr['Age Group'].values, fontsize=20)
        ax.tick_params(axis='y', labelsize=20)
        ax.set_ylim(0, max(vals) * 1.15 if len(vals) else 100)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_holder_age.png')
        _slide(ctx, 'A7.11 - DCTR by Account Holder Age', {
            'title': 'Eligible Accounts DCTR by Account Holder Age',
            'subtitle': f"Ranges from {ins.get('lowest_dctr', 0):.0%} ({ins.get('lowest', '')}) "
                        f"to {ins.get('highest_dctr', 0):.0%} ({ins.get('highest', '')})",
            'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx['results']['dctr_11'] = {'df': df, 'insights': ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest at {ins.get('highest_dctr', 0):.1%}")
    return ctx


# =============================================================================
# DCTR-12: Balance Range (A6.12)
# =============================================================================

def run_dctr_12(ctx):
    _report(ctx, "\n💰 DCTR-12 — Balance Range")
    ed = ctx['eligible_data']
    if 'Avg Bal' not in ed.columns:
        _report(ctx, "   ⚠️ No 'Avg Bal' column")
        ctx['results']['dctr_12'] = {}; return ctx

    edc = ed.copy()
    edc['Avg Bal'] = pd.to_numeric(edc['Avg Bal'], errors='coerce')
    valid = edc[edc['Avg Bal'].notna()].copy()
    df, ins = _by_dimension(valid, 'Avg Bal', categorize_balance, BALANCE_ORDER, 'Balance Range')
    _save(ctx, df, 'DCTR-12-Balance', 'DCTR by Balance Range',
          {'Highest': f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
           'Lowest': f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})"})
    ctx['results']['dctr_12'] = {'df': df, 'insights': ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest | {ins.get('lowest', '?')} lowest")
    return ctx


# =============================================================================
# DCTR-13: Cross-tab Holder Age × Balance (A6.13)
# =============================================================================

def run_dctr_13(ctx):
    _report(ctx, "\n🔀 DCTR-13 — Cross-Tab: Holder Age × Balance")
    ed = ctx['eligible_data']
    if 'Account Holder Age' not in ed.columns or 'Avg Bal' not in ed.columns:
        _report(ctx, "   ⚠️ Missing columns"); ctx['results']['dctr_13'] = {}; return ctx

    dc = ed.copy()
    dc['Account Holder Age'] = pd.to_numeric(dc['Account Holder Age'], errors='coerce')
    dc['Avg Bal'] = pd.to_numeric(dc['Avg Bal'], errors='coerce')
    valid = dc[(dc['Account Holder Age'] >= 18) & (dc['Account Holder Age'] <= 120) & dc['Avg Bal'].notna()].copy()

    detail, dpiv, cpiv, ins = _crosstab(valid, 'Account Holder Age', categorize_holder_age,
                                         HOLDER_AGE_ORDER, 'Age Group',
                                         'Avg Bal', categorize_balance, BALANCE_ORDER, 'Balance Range')
    if not detail.empty:
        _save(ctx, detail, 'DCTR-13-AgeBalance', 'Cross-Tab: Holder Age × Balance',
              {'Segments': f"{ins.get('segments', 0)}",
               'Highest': f"{ins.get('highest_seg', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
               'Lowest': f"{ins.get('lowest_seg', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})"})
        if not dpiv.empty:
            _save(ctx, dpiv, 'DCTR-13-Pivot', 'DCTR % by Age × Balance')
    ctx['results']['dctr_13'] = ins
    _report(ctx, f"   {ins.get('segments', 0)} segments")
    return ctx


# =============================================================================
# DCTR-14: Cross-tab Account Age × Balance (A6.14)
# =============================================================================

def run_dctr_14(ctx):
    _report(ctx, "\n🔀 DCTR-14 — Cross-Tab: Account Age × Balance")
    ed = ctx['eligible_data']
    if 'Avg Bal' not in ed.columns:
        _report(ctx, "   ⚠️ Missing 'Avg Bal'"); ctx['results']['dctr_14'] = {}; return ctx

    dc = ed.copy()
    dc['Date Opened'] = pd.to_datetime(dc['Date Opened'], errors='coerce')
    dc['Account Age Days'] = (pd.Timestamp.now() - dc['Date Opened']).dt.days
    dc['Avg Bal'] = pd.to_numeric(dc['Avg Bal'], errors='coerce')
    valid = dc[dc['Account Age Days'].notna() & dc['Avg Bal'].notna()].copy()

    detail, dpiv, cpiv, ins = _crosstab(valid, 'Account Age Days', categorize_account_age,
                                         AGE_ORDER, 'Account Age',
                                         'Avg Bal', categorize_balance, BALANCE_ORDER, 'Balance Range')
    if not detail.empty:
        _save(ctx, detail, 'DCTR-14-AcctAgeBalance', 'Cross-Tab: Account Age × Balance',
              {'Segments': f"{ins.get('segments', 0)}"})
        if not dpiv.empty:
            _save(ctx, dpiv, 'DCTR-14-Pivot', 'DCTR % by Account Age × Balance')
    ctx['results']['dctr_14'] = ins
    _report(ctx, f"   {ins.get('segments', 0)} segments")
    return ctx


# =============================================================================
# DCTR-15: Cross-tab Branch × Account Age (A6.15)
# =============================================================================

def run_dctr_15(ctx):
    _report(ctx, "\n🔀 DCTR-15 — Cross-Tab: Branch × Account Age")
    ed = ctx['eligible_data'].copy()
    bm = ctx['config'].get('BranchMapping', {})

    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    ed['Account Age Days'] = (pd.Timestamp.now() - ed['Date Opened']).dt.days
    if bm:
        ed['Branch Name'] = ed['Branch'].map(bm).fillna(ed['Branch'])
    else:
        ed['Branch Name'] = ed['Branch']
    valid = ed[ed['Account Age Days'].notna()].copy()
    valid['Simple Age'] = valid['Account Age Days'].apply(categorize_account_age).apply(simplify_account_age)

    rows = []
    simple_order = ['New (0-1 year)', 'Recent (1-5 years)', 'Mature (5+ years)']
    for branch in sorted(valid['Branch Name'].unique()):
        bd = valid[valid['Branch Name'] == branch]
        for ac in simple_order:
            seg = bd[bd['Simple Age'] == ac]
            if len(seg) > 0:
                t, w, d = _dctr(seg)
                rows.append({'Branch': branch, 'Age Category': ac,
                             'Total Accounts': t, 'With Debit': w, 'DCTR %': d})

    detail = pd.DataFrame(rows)
    if not detail.empty:
        pivot = detail.pivot_table(index='Branch', columns='Age Category', values='DCTR %')
        pivot = pivot.reindex(columns=simple_order)
        _save(ctx, detail, 'DCTR-15-BranchAge', 'Cross-Tab: Branch × Account Age',
              {'Branches': f"{len(detail['Branch'].unique())}"})
        _save(ctx, pivot, 'DCTR-15-Pivot', 'Branch DCTR by Account Age')

        # Find best at new accounts
        new_data = detail[detail['Age Category'] == 'New (0-1 year)']
        best_new = new_data.loc[new_data['DCTR %'].idxmax()] if not new_data.empty else None
        ins = {'branches': len(detail['Branch'].unique())}
        if best_new is not None:
            ins['best_new_branch'] = best_new['Branch']
            ins['best_new_dctr'] = best_new['DCTR %']
        ctx['results']['dctr_15'] = ins
        _report(ctx, f"   {ins['branches']} branches × 3 age categories")
    else:
        ctx['results']['dctr_15'] = {}
    return ctx


# =============================================================================
# DCTR-16: Branch L12M Monthly Performance Table (A7.16)
# =============================================================================

def run_dctr_16(ctx):
    _report(ctx, "\n📊 DCTR-16 — Branch L12M Monthly Table")
    ed = ctx['eligible_data'].copy()
    l12m = ctx['last_12_months']
    bm = ctx['config'].get('BranchMapping', {})
    chart_dir = ctx['chart_dir']

    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    ed['Month_Year'] = ed['Date Opened'].dt.strftime('%b%y')
    if bm:
        ed['Branch Name'] = ed['Branch'].map(bm).fillna(ed['Branch'])
    else:
        ed['Branch Name'] = ed['Branch']

    all_branches = sorted(ed['Branch Name'].unique())
    rows = []
    for branch in all_branches:
        bd = ed[ed['Branch Name'] == branch]
        row = {'Branch': branch}
        te = td = 0
        for month in l12m:
            md = bd[bd['Month_Year'] == month]
            elig = len(md); debits = len(md[md['Debit?'] == 'Yes'])
            te += elig; td += debits
            row[month] = f"{(debits/elig*100):.1f}%" if elig > 0 else ""
        row['12M Debits'] = td
        row['12M Eligible'] = te
        row['12M Take Rate'] = f"{(td/te*100):.1f}%" if te > 0 else "0.0%"
        rows.append(row)

    table = pd.DataFrame(rows)
    grand_d = sum(r['12M Debits'] for r in rows)
    grand_e = sum(r['12M Eligible'] for r in rows)
    grand_r = (grand_d / grand_e * 100) if grand_e > 0 else 0

    _save(ctx, table, 'DCTR-16-Branch-L12M-Table', 'Branch L12M Performance',
          {'Overall': f"{grand_r:.1f}%", 'Branches': f"{len(all_branches)}",
           'Total Eligible': f"{grand_e:,}", 'Total Debits': f"{grand_d:,}"})

    # Table slide
    _slide(ctx, 'A7.16 - Branch L12M Table', {
        'title': 'Branch Debit Card Analysis (TTM)',
        'subtitle': f"Overall take rate {grand_r:.1f}% across {len(all_branches)} branches",
        'layout_index': 11,
        'insights': [f"Period: {l12m[0]} to {l12m[-1]}",
                     f"Total eligible: {grand_e:,}", f"Total debits: {grand_d:,}",
                     f"Overall take rate: {grand_r:.1f}%"]})

    ctx['results']['dctr_16'] = {'grand_rate': grand_r, 'branches': len(all_branches),
                                  'grand_eligible': grand_e, 'grand_debits': grand_d}
    _report(ctx, f"   {len(all_branches)} branches | Overall: {grand_r:.1f}%")
    return ctx


# =============================================================================
# FUNNEL: Account & Debit Card Funnel (A7.7)
# =============================================================================

def run_dctr_funnel(ctx):
    _report(ctx, "\n🎯 DCTR — Account Funnel")
    chart_dir = ctx['chart_dir']
    data = ctx['data']; oa = ctx['open_accounts']
    ed = ctx['eligible_data']; ewd = ctx['eligible_with_debit']

    ta = len(data); to = len(oa); te = len(ed); td = len(ewd)
    through = td / ta * 100 if ta else 0
    dctr_e = td / te * 100 if te else 0

    # Personal/Business splits
    tp = len(data[data['Business?'] == 'No']); tb = len(data[data['Business?'] == 'Yes'])
    has_biz = tb > 0
    op = len(oa[oa['Business?'] == 'No']); ob = len(oa[oa['Business?'] == 'Yes'])
    ep = len(ctx['eligible_personal']); eb_cnt = len(ctx['eligible_business'])
    dp = ctx['results'].get('dctr_4', {}).get('insights', {}).get('with_debit_count', 0)
    db_cnt = ctx['results'].get('dctr_5', {}).get('insights', {}).get('with_debit_count', 0)

    try:
        import matplotlib.patches as patches
        import matplotlib.colors as mcolors

        fig, ax = plt.subplots(figsize=(12, 10))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#f8f9fa')

        stages = [
            {'name': 'Total\nAccounts', 'total': ta, 'personal': tp, 'business': tb, 'color': '#1f77b4'},
            {'name': 'Open\nAccounts', 'total': to, 'personal': op, 'business': ob, 'color': '#2c7fb8'},
            {'name': 'Eligible\nAccounts', 'total': te, 'personal': ep, 'business': eb_cnt, 'color': '#ff7f0e'},
            {'name': 'Eligible With\nDebit Card', 'total': td, 'personal': dp, 'business': db_cnt, 'color': '#41b6c4'},
        ]

        max_width = 0.8; stage_height = 0.15; y_start = 0.85; stage_gap = 0.02
        current_y = y_start

        for i, stage in enumerate(stages):
            width = max_width * (stage['total'] / stages[0]['total']) if stages[0]['total'] > 0 else 0.1

            if has_biz and stage['total'] > 0:
                p_ratio = stage['personal'] / stage['total']
                p_width = width * p_ratio
                b_width = width * (1 - p_ratio)
                # Personal (lighter)
                rect_p = patches.FancyBboxPatch(
                    (0.5 - width/2, current_y - stage_height), p_width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=stage['color'],
                    edgecolor='white', linewidth=2, alpha=0.9)
                ax.add_patch(rect_p)
                # Business (darker)
                rgb = mcolors.hex2color(stage['color'])
                darker = mcolors.rgb2hex(tuple([c * 0.7 for c in rgb]))
                rect_b = patches.FancyBboxPatch(
                    (0.5 - width/2 + p_width, current_y - stage_height), b_width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=darker,
                    edgecolor='white', linewidth=2, alpha=0.9)
                ax.add_patch(rect_b)
                # Labels inside
                if p_width > 0.05:
                    ax.text(0.5 - width/2 + p_width/2, current_y - stage_height/2,
                            f"{stage['personal']:,}", ha='center', va='center',
                            fontsize=20, color='white', fontweight='bold')
                if b_width > 0.05:
                    ax.text(0.5 - width/2 + p_width + b_width/2, current_y - stage_height/2,
                            f"{stage['business']:,}", ha='center', va='center',
                            fontsize=20, color='white', fontweight='bold')
                # Total to right
                ax.text(0.5 + width/2 + 0.05, current_y - stage_height/2,
                        f"Total\n{stage['total']:,}", ha='left', va='center',
                        fontsize=18, fontweight='bold', color='black',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                  edgecolor='black', alpha=0.9))
            else:
                rect = patches.FancyBboxPatch(
                    (0.5 - width/2, current_y - stage_height), width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=stage['color'],
                    edgecolor='white', linewidth=3, alpha=0.9)
                ax.add_patch(rect)
                ax.text(0.5, current_y - stage_height/2, f"{stage['total']:,}",
                        ha='center', va='center', fontsize=28, fontweight='bold',
                        color='white', zorder=10)

            # Stage name on left
            ax.text(0.5 - width/2 - 0.05, current_y - stage_height/2,
                    stage['name'], ha='right', va='center',
                    fontsize=20, fontweight='600', color='#2c3e50')

            # Conversion arrow between stages
            if i > 0 and stages[i-1]['total'] > 0:
                conv = stage['total'] / stages[i-1]['total'] * 100
                arrow_y = current_y + stage_gap/2
                ax.annotate('', xy=(0.5, arrow_y - stage_gap + 0.01),
                            xytext=(0.5, arrow_y - 0.01),
                            arrowprops=dict(arrowstyle='->', lw=3, color='#e74c3c'))
                ax.text(0.45, arrow_y - stage_gap/2, f"{conv:.1f}%",
                        ha='center', va='center', fontsize=18, fontweight='bold',
                        color='#e74c3c',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#e74c3c', alpha=0.9))
            current_y -= (stage_height + stage_gap)

        # Title and subtitle
        ax.text(0.5, 0.98, "Historical Account Eligibility & Debit Card Funnel",
                ha='center', va='top', fontsize=28, fontweight='bold',
                color='#1e3d59', transform=ax.transAxes)
        ax.text(0.5, 0.93, "All-Time Analysis",
                ha='center', va='top', fontsize=20, style='italic',
                color='#7f8c8d', transform=ax.transAxes)

        # Legend if business accounts
        if has_biz:
            legend_elements = [
                patches.Patch(facecolor='#808080', edgecolor='black', label='Personal (Lighter shade)'),
                patches.Patch(facecolor='#404040', edgecolor='black', label='Business (Darker shade)')]
            ax.legend(handles=legend_elements, loc='lower right', fontsize=16, frameon=True, fancybox=True)

        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_funnel.png')

        subtitle = f"{through:.1f}% of all accounts end up with debit cards — {dctr_e:.1f}% DCTR among eligible"
        insights_list = [
            f"Total accounts: {ta:,}",
            f"Open accounts: {to:,} ({to/ta*100:.1f}% of total)" if ta else "Open: 0",
            f"Eligible accounts: {te:,} ({te/to*100:.1f}% of open)" if to else "Eligible: 0",
            f"With debit card: {td:,} ({dctr_e:.1f}% DCTR)" if te else "With debit: 0",
            f"End-to-end conversion: {through:.1f}%",
        ]
        if has_biz:
            pd_dctr = ctx['results'].get('dctr_4', {}).get('insights', {}).get('overall_dctr', 0) * 100
            bd_dctr = ctx['results'].get('dctr_5', {}).get('insights', {}).get('overall_dctr', 0) * 100
            insights_list.append(f"Personal DCTR: {pd_dctr:.1f}% | Business DCTR: {bd_dctr:.1f}%")

        _slide(ctx, 'A7.7 - Historical Funnel', {
            'title': 'Historical Account & Debit Card Funnel',
            'subtitle': subtitle,
            'kpis': {'Through Rate': f"{through:.1f}%", 'Eligible DCTR': f"{dctr_e:.1f}%"},
            'chart_path': cp, 'layout_index': 9,
            'insights': insights_list})
    except Exception as e:
        _report(ctx, f"   ⚠️ Funnel chart: {e}")

    ctx['results']['dctr_funnel'] = {'through_rate': through, 'dctr_eligible': dctr_e}
    _report(ctx, f"   {ta:,} → {to:,} → {te:,} → {td:,} | Through: {through:.1f}%")
    return ctx


# =============================================================================
# COMBINED SLIDE: Open vs Eligible + Historical vs L12M (A7.1 + A7.3)
# =============================================================================

def run_dctr_combo_slide(ctx):
    """Build a side-by-side slide if both comparison charts exist."""
    _report(ctx, "\n📊 DCTR — Combo Slide (A7.1+A7.3)")
    cp1 = ctx['results'].get('dctr_2_chart')
    cp3 = ctx['results'].get('dctr_3_chart')
    if not cp1 or not cp3:
        _report(ctx, "   ⚠️ Missing one or both comparison charts — skipping combo")
        return ctx

    d2 = ctx['results'].get('dctr_2', {}).get('insights', {})
    d3 = ctx['results'].get('dctr_3', {}).get('insights', {})
    diff = d2.get('difference', 0) * 100
    comp = d3.get('comparison_to_overall', 0) * 100
    trend = "improving" if comp > 0 else "declining" if comp < 0 else "stable"

    _slide(ctx, 'A7 - DCTR Comparison', {
        'title': 'DCTR Comparison',
        'subtitle': f"Eligible {diff:+.1f}pp higher — Recent trend: {trend}",
        'chart_path': cp1,
        'chart_path_2': cp3,
        'layout_index': 6,
        'slide_type': 'multi_screenshot',
        'insights': [f"Open vs Eligible gap: {diff:+.1f}pp",
                     f"TTM vs Historical: {comp:+.1f}pp ({trend})"]})
    _report(ctx, f"   Combo slide created — gap: {diff:+.1f}pp, trend: {trend}")
    return ctx


# =============================================================================
# SEGMENT TRENDS: Personal/Business × Historical/L12M (A7.4)
# =============================================================================

def run_dctr_segment_trends(ctx):
    """A7.4: Grouped bar chart — Personal/Business × Historical/L12M DCTR."""
    _report(ctx, "\n📊 DCTR — Segment Trends (A7.4)")
    chart_dir = ctx['chart_dir']

    # Gather rates from earlier results
    p_ins = ctx['results'].get('dctr_4', {}).get('insights', {})
    b_ins = ctx['results'].get('dctr_5', {}).get('insights', {})
    p6_ins = ctx['results'].get('dctr_6', {}).get('insights', {})
    b7_ins = ctx['results'].get('dctr_7', {}).get('insights', {})

    p_hist = p_ins.get('overall_dctr', 0) * 100
    p_l12m = p6_ins.get('dctr', 0) * 100
    p_trend = p_l12m - p_hist
    has_biz = b_ins.get('total_accounts', 0) > 0
    b_hist = b_ins.get('overall_dctr', 0) * 100
    b_l12m = b7_ins.get('dctr', 0) * 100
    b_trend = b_l12m - b_hist

    # Build summary table
    rows = [{'Segment': 'Personal', 'Historical DCTR %': p_hist, 'L12M DCTR %': p_l12m,
             'Change pp': p_trend, 'Hist Accounts': p_ins.get('total_accounts', 0),
             'L12M Accounts': p6_ins.get('total_accounts', 0)}]
    if has_biz:
        rows.append({'Segment': 'Business', 'Historical DCTR %': b_hist, 'L12M DCTR %': b_l12m,
                     'Change pp': b_trend, 'Hist Accounts': b_ins.get('total_accounts', 0),
                     'L12M Accounts': b7_ins.get('total_accounts', 0)})
    df = pd.DataFrame(rows)
    _save(ctx, df, 'DCTR-SegmentTrends', 'DCTR Segment Trends',
          {'Personal Trend': f"{p_trend:+.1f}pp",
           'Business Trend': f"{b_trend:+.1f}pp" if has_biz else 'N/A'})

    # Chart A7.4: Grouped bar — matching notebook format
    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        if has_biz:
            cats = ['Personal\nHistorical', 'Personal\nTTM', 'Business\nHistorical', 'Business\nTTM']
            vals = [p_hist, p_l12m, b_hist, b_l12m]
            colors = ['#4472C4', '#5B9BD5', '#ED7D31', '#F4B183']
        else:
            cats = ['Personal\nHistorical', 'Personal\nTTM']
            vals = [p_hist, p_l12m]
            colors = ['#4472C4', '#5B9BD5']

        x_pos = np.arange(len(cats))
        bars = ax.bar(x_pos, vals, color=colors, edgecolor='black', linewidth=2, alpha=0.9, width=0.6)
        for i, (bar, v) in enumerate(zip(bars, vals)):
            ax.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.1f}%',
                    ha='center', fontweight='bold', fontsize=22)
            ct = [p_ins.get('total_accounts', 0), p6_ins.get('total_accounts', 0),
                  b_ins.get('total_accounts', 0), b7_ins.get('total_accounts', 0)]
            if i < len(ct) and ct[i] > 0 and v > 10:
                ax.text(bar.get_x() + bar.get_width()/2, v/2, f'{ct[i]:,}\naccts',
                        ha='center', fontsize=16, fontweight='bold', color='white')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('DCTR Segment Trends: Historical vs Trailing Twelve Months',
                     fontsize=24, fontweight='bold', pad=20)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(cats, fontsize=20)
        ax.tick_params(axis='y', labelsize=20)
        ax.set_ylim(0, max(vals) * 1.2 if vals else 100)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)

        # Divider between Personal and Business
        if has_biz:
            ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=2, alpha=0.5)

        # Trend annotations
        mid_p = 0.5
        ax.annotate(f'{p_trend:+.1f}pp', xy=(mid_p, max(p_hist, p_l12m) + 3),
                    fontsize=20, fontweight='bold', ha='center',
                    color='green' if p_trend > 0 else 'red' if p_trend < 0 else 'gray')
        if has_biz:
            mid_b = 2.5
            ax.annotate(f'{b_trend:+.1f}pp', xy=(mid_b, max(b_hist, b_l12m) + 3),
                        fontsize=20, fontweight='bold', ha='center',
                        color='green' if b_trend > 0 else 'red' if b_trend < 0 else 'gray')
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_segment_trends.png')

        subtitle = f"Personal {p_trend:+.1f}pp"
        if has_biz:
            subtitle += f" | Business {b_trend:+.1f}pp"
        subtitle += " — Trailing twelve months vs historical"
        _slide(ctx, 'A7.4 - Segment Trends', {
            'title': 'DCTR Segment Trends',
            'subtitle': subtitle, 'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Segment trends chart: {e}")

    ctx['results']['dctr_segment_trends'] = {
        'personal_trend': p_trend, 'business_trend': b_trend, 'has_business': has_biz}
    _report(ctx, f"   Personal: {p_hist:.1f}% → {p_l12m:.1f}% ({p_trend:+.1f}pp)")
    return ctx


# =============================================================================
# DECADE TREND: Line chart with P/B overlay (A7.5)
# =============================================================================

def run_dctr_decade_trend(ctx):
    """A7.5: DCTR trend by decade with Personal/Business overlay."""
    _report(ctx, "\n📈 DCTR — Decade Trend (A7.5)")
    chart_dir = ctx['chart_dir']

    d1 = ctx['results'].get('dctr_1', {}).get('decade', pd.DataFrame())
    d4 = ctx['results'].get('dctr_4', {}).get('decade', pd.DataFrame())
    d5 = ctx['results'].get('dctr_5', {}).get('decade', pd.DataFrame())

    if d1.empty:
        _report(ctx, "   ⚠️ No decade data"); return ctx

    _save(ctx, d1, 'DCTR-DecadeTrend', 'DCTR by Decade')

    try:
        fig = plt.figure(figsize=(16, 8))
        ax = plt.gca()
        ax2 = ax.twinx()
        decades = d1['Decade'].values
        overall = d1['DCTR %'].values * 100
        x = np.arange(len(decades))

        # Volume bars on secondary axis (notebook: alpha=0.2, gray, no edge)
        total_vol = d1['Total Accounts'].values
        bars = ax2.bar(x, total_vol, alpha=0.2, color='gray', edgecolor='none', width=0.8)
        ax2.set_ylabel('Account Volume', fontsize=24, color='gray')
        max_vol = max(total_vol) if len(total_vol) > 0 else 100
        ax2.set_ylim(0, max_vol * 2)
        ax2.tick_params(axis='y', colors='gray', labelsize=24)

        # Volume labels at base of bars (notebook style)
        for bar, vol in zip(bars, total_vol):
            if vol > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., vol * 0.02,
                         f'{int(vol):,}', ha='center', va='bottom',
                         fontsize=24, color='black', alpha=0.8)

        # Overall DCTR line (notebook: black, dashed, markersize=18)
        ax.plot(x, overall, color='black', linewidth=3, linestyle='--',
                marker='o', markersize=18, label='Overall', zorder=2)

        # Personal overlay (notebook: blue, lw=4, ms=12)
        has_biz = False
        if not d4.empty:
            p_merged = d4.set_index('Decade').reindex(decades)
            p_vals = p_merged['DCTR %'].values * 100
            valid_mask = ~np.isnan(p_vals)
            if valid_mask.any():
                ax.plot(x[valid_mask], p_vals[valid_mask], color='#4472C4', linewidth=4,
                        marker='o', markersize=12, label='Personal', zorder=3)
                for i, v in zip(x[valid_mask], p_vals[valid_mask]):
                    offset = 2 if not (not d5.empty and d5['Total Accounts'].sum() > 0) else 2
                    ax.text(i, v + offset, f'{v:.0f}%', ha='center', va='bottom',
                            fontsize=24, fontweight='bold', color='#4472C4')

        # Business overlay (notebook: orange, lw=4, square markers)
        if not d5.empty and d5['Total Accounts'].sum() > 0:
            has_biz = True
            b_merged = d5.set_index('Decade').reindex(decades)
            b_vals = b_merged['DCTR %'].values * 100
            valid_mask = ~np.isnan(b_vals)
            if valid_mask.any():
                ax.plot(x[valid_mask], b_vals[valid_mask], color='#ED7D31', linewidth=4,
                        marker='s', markersize=12, label='Business', zorder=3)
                for i, v in zip(x[valid_mask], b_vals[valid_mask]):
                    ax.text(i, v - 3, f'{v:.0f}%', ha='center', va='top',
                            fontsize=24, fontweight='bold', color='#ED7D31')

        # Axis formatting (notebook: fontsize=24 everywhere)
        ax.set_xticks(x)
        ax.set_xticklabels(decades, fontsize=24, rotation=45 if len(decades) > 8 else 0)
        ax.set_xlabel('Decade', fontsize=24, fontweight='bold')
        ax.set_ylabel('DCTR (%)', fontsize=24, fontweight='bold')
        ax.set_title('Historical DCTR Trend by Decade - Eligible Accounts Only',
                     fontsize=24, fontweight='bold', pad=20)
        ax.set_ylim(0, 110)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{int(x)}%'))
        ax.tick_params(axis='y', labelsize=24)

        # Legend (notebook style)
        legend_items = 1
        if not d4.empty: legend_items += 1
        if has_biz: legend_items += 1
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                  ncol=legend_items, fontsize=18, frameon=True)

        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False); ax2.spines['top'].set_visible(False)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_decade_trend.png')

        change = overall[-1] - overall[0] if len(overall) >= 2 else 0
        trend = "improving" if change > 0 else "declining" if change < 0 else "stable"
        _slide(ctx, 'A7.5 - Decade Trend', {
            'title': 'Historical DCTR Trend by Decade',
            'subtitle': f"Overall {trend}: {overall[0]:.0f}% → {overall[-1]:.0f}% ({change:+.1f}pp) across {len(decades)} decades",
            'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Decade trend chart: {e}")

    ctx['results']['dctr_decade_trend'] = {'decades': len(d1)}
    _report(ctx, f"   {len(d1)} decades plotted")
    return ctx


# =============================================================================
# L12M TREND: Monthly DCTR line chart (A7.6a)
# =============================================================================

def run_dctr_l12m_trend(ctx):
    """A7.6a: L12M monthly DCTR trend line chart with P/B overlay."""
    _report(ctx, "\n📈 DCTR — L12M Monthly Trend (A7.6a)")
    chart_dir = ctx['chart_dir']
    l12m_months = ctx['last_12_months']

    # Get monthly data from L12M subsets
    ed = ctx['eligible_last_12m']
    ep = ctx['eligible_personal_last_12m']
    eb = ctx['eligible_business_last_12m']

    if ed is None or ed.empty:
        _report(ctx, "   ⚠️ No L12M data"); return ctx

    def _monthly_rates(dataset, months):
        dc = dataset.copy()
        dc['Date Opened'] = pd.to_datetime(dc['Date Opened'], errors='coerce')
        dc['Month_Year'] = dc['Date Opened'].dt.strftime('%b%y')
        rates = []
        for m in months:
            md = dc[dc['Month_Year'] == m]
            t, w, d = _dctr(md)
            rates.append(d * 100 if t > 0 else np.nan)
        return rates

    overall_rates = _monthly_rates(ed, l12m_months)
    personal_rates = _monthly_rates(ep, l12m_months) if ep is not None and not ep.empty else [np.nan] * len(l12m_months)
    has_biz = eb is not None and not eb.empty and len(eb) > 0
    business_rates = _monthly_rates(eb, l12m_months) if has_biz else [np.nan] * len(l12m_months)

    # Build data table
    trend_df = pd.DataFrame({
        'Month': l12m_months, 'Overall DCTR %': overall_rates,
        'Personal DCTR %': personal_rates, 'Business DCTR %': business_rates})
    _save(ctx, trend_df, 'DCTR-L12M-Trend', 'L12M Monthly DCTR Trend')

    try:
        fig = plt.figure(figsize=(16, 8))
        ax = plt.gca()
        ax2 = ax.twinx()
        x = np.arange(len(l12m_months))

        # Volume bars on secondary axis (notebook style)
        ed_copy = ed.copy()
        ed_copy['Date Opened'] = pd.to_datetime(ed_copy['Date Opened'], errors='coerce')
        ed_copy['Month_Year'] = ed_copy['Date Opened'].dt.strftime('%b%y')
        total_volume = [len(ed_copy[ed_copy['Month_Year'] == m]) for m in l12m_months]
        bars = ax2.bar(x, total_volume, alpha=0.25, color='gray', edgecolor='darkgray',
                       linewidth=1, width=0.8)
        # Volume labels with white background (notebook style)
        for bar, vol in zip(bars, total_volume):
            if vol > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., vol * 0.05,
                         f'{int(vol):,}', ha='center', va='bottom',
                         fontsize=18, fontweight='bold', color='black', alpha=0.9,
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        max_vol = max(total_volume) if total_volume else 100
        ax2.set_ylim(0, max_vol * 2)
        ax2.set_ylabel('Number of Accounts', fontsize=24, color='gray', labelpad=15)
        ax2.tick_params(axis='y', labelsize=20, colors='gray')

        # Overall DCTR line (notebook: black, dashed, lw=4, ms=12)
        ov = np.array(overall_rates)
        mask = ~np.isnan(ov)
        if mask.any():
            ax.plot(x[mask], ov[mask], color='black', linewidth=4, linestyle='--',
                    marker='o', markersize=12, label='Overall', zorder=2)
            # Data labels — only first, last, and every 3rd
            for idx, (i, v) in enumerate(zip(x[mask], ov[mask])):
                if idx == 0 or idx == mask.sum() - 1 or idx % 3 == 0:
                    ax.text(i, v + 1.5, f'{v:.0f}%', ha='center', fontsize=18,
                            fontweight='bold', color='black')

        # Personal DCTR line (notebook: blue, lw=5, ms=14)
        pr = np.array(personal_rates)
        pmask = ~np.isnan(pr)
        if pmask.any():
            ax.plot(x[pmask], pr[pmask], color='#4472C4', linewidth=5,
                    marker='o', markersize=14, label='Personal', zorder=3)

        # Business DCTR line (notebook: orange)
        if has_biz:
            br = np.array(business_rates)
            bmask = ~np.isnan(br)
            if bmask.any():
                ax.plot(x[bmask], br[bmask], color='#ED7D31', linewidth=4,
                        marker='s', markersize=12, label='Business', zorder=3)

        # Axis formatting (notebook: fontsize 24-32)
        ax.set_xticks(x)
        ax.set_xticklabels(l12m_months, rotation=45, ha='right', fontsize=22)
        ax.set_xlabel('Month', fontsize=28, fontweight='bold', labelpad=15)
        ax.set_ylabel('DCTR (%)', fontsize=28, fontweight='bold', labelpad=15)
        ax.set_title('Trailing Twelve Months DCTR Trend (Eligible Accounts)',
                     fontsize=32, fontweight='bold', pad=25)
        ax.tick_params(axis='y', labelsize=24)
        valid_rates = [v for v in overall_rates if not np.isnan(v)]
        if valid_rates:
            ax.set_ylim(min(valid_rates) - 5, max(valid_rates) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{int(x)}%'))
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                  ncol=3, fontsize=18, frameon=True)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False); ax2.spines['top'].set_visible(False)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_l12m_trend.png')

        start_v = next((v for v in overall_rates if not np.isnan(v)), 0)
        end_v = next((v for v in reversed(overall_rates) if not np.isnan(v)), 0)
        change = end_v - start_v
        trend = "improving" if change > 2 else "declining" if change < -2 else "stable"
        _slide(ctx, 'A7.6a - Last 12 Months DCTR Trend', {
            'title': 'Trailing Twelve Months DCTR Trend',
            'subtitle': f"DCTR {trend} from {start_v:.0f}% to {end_v:.0f}% ({change:+.1f}pp) over trailing twelve months",
            'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ L12M trend chart: {e}")

    ctx['results']['dctr_l12m_trend'] = {'trend_df': trend_df}
    _report(ctx, f"   {len(l12m_months)} months plotted")
    return ctx


# =============================================================================
# L12M FUNNEL: Last 12 Months Funnel with P/B Split (A7.8)
# =============================================================================

def run_dctr_l12m_funnel(ctx):
    """A7.8: L12M proportional funnel chart with Personal/Business split."""
    _report(ctx, "\n🎯 DCTR — L12M Funnel (A7.8)")
    chart_dir = ctx['chart_dir']
    data = ctx['data'].copy()
    sd, ed_date = ctx['start_date'], ctx['end_date']

    data['Date Opened'] = pd.to_datetime(data['Date Opened'], errors='coerce')
    l12m_all = data[(data['Date Opened'] >= sd) & (data['Date Opened'] <= ed_date)]
    l12m_open = ctx['open_last_12m'] if ctx.get('open_last_12m') is not None else pd.DataFrame()
    l12m_elig = ctx['eligible_last_12m'] if ctx.get('eligible_last_12m') is not None else pd.DataFrame()
    l12m_debit = l12m_elig[l12m_elig['Debit?'] == 'Yes'] if not l12m_elig.empty else pd.DataFrame()

    ta = len(l12m_all); to = len(l12m_open); te = len(l12m_elig); td = len(l12m_debit)
    through = td / ta * 100 if ta else 0
    dctr_e = td / te * 100 if te else 0

    # P/B splits
    has_biz = 'Business?' in l12m_elig.columns and len(l12m_elig[l12m_elig['Business?'] == 'Yes']) > 0
    if has_biz:
        ep = l12m_elig[l12m_elig['Business?'] == 'No']
        eb = l12m_elig[l12m_elig['Business?'] == 'Yes']
        pd_dctr = len(ep[ep['Debit?'] == 'Yes']) / len(ep) * 100 if len(ep) else 0
        bd_dctr = len(eb[eb['Debit?'] == 'Yes']) / len(eb) * 100 if len(eb) else 0
    else:
        pd_dctr = dctr_e; bd_dctr = 0

    funnel_df = pd.DataFrame([
        {'Stage': 'Total TTM Accounts', 'Count': ta, 'Pct of Total': 100},
        {'Stage': 'Open Accounts', 'Count': to, 'Pct of Total': to/ta*100 if ta else 0},
        {'Stage': 'Eligible Accounts', 'Count': te, 'Pct of Total': te/ta*100 if ta else 0},
        {'Stage': 'With Debit Card', 'Count': td, 'Pct of Total': through},
    ])
    _save(ctx, funnel_df, 'DCTR-L12M-Funnel', 'L12M Account Funnel',
          {'Through Rate': f"{through:.1f}%", 'DCTR': f"{dctr_e:.1f}%",
           'Period': f"{sd.strftime('%b %Y')} - {ed_date.strftime('%b %Y')}"})

    try:
        import matplotlib.patches as patches
        import matplotlib.colors as mcolors

        fig, ax = plt.subplots(figsize=(12, 10))
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#f8f9fa')

        # Build P/B split counts
        tp_a = len(l12m_all[l12m_all['Business?'] == 'No']) if 'Business?' in l12m_all.columns else ta
        tb_a = ta - tp_a
        op_a = len(l12m_open[l12m_open['Business?'] == 'No']) if not l12m_open.empty and 'Business?' in l12m_open.columns else to
        ob_a = to - op_a
        ep_a = len(l12m_elig[l12m_elig['Business?'] == 'No']) if not l12m_elig.empty and 'Business?' in l12m_elig.columns else te
        eb_a = te - ep_a
        dp_a = len(l12m_debit[l12m_debit['Business?'] == 'No']) if not l12m_debit.empty and 'Business?' in l12m_debit.columns else td
        db_a = td - dp_a

        stages = [
            {'name': 'Total New\nAccounts', 'total': ta, 'personal': tp_a, 'business': tb_a, 'color': '#1f77b4'},
            {'name': 'Open\nAccounts', 'total': to, 'personal': op_a, 'business': ob_a, 'color': '#2c7fb8'},
            {'name': 'Eligible\nAccounts', 'total': te, 'personal': ep_a, 'business': eb_a, 'color': '#ff7f0e'},
            {'name': 'Eligible With\nDebit Card', 'total': td, 'personal': dp_a, 'business': db_a, 'color': '#41b6c4'},
        ]

        max_width = 0.8; stage_height = 0.15; y_start = 0.85; stage_gap = 0.02
        current_y = y_start

        for i, stage in enumerate(stages):
            width = max_width * (stage['total'] / stages[0]['total']) if stages[0]['total'] > 0 else 0.1

            if has_biz and stage['total'] > 0:
                p_ratio = stage['personal'] / stage['total']
                p_width = width * p_ratio
                b_width = width * (1 - p_ratio)
                # Personal (lighter)
                rect_p = patches.FancyBboxPatch(
                    (0.5 - width/2, current_y - stage_height), p_width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=stage['color'],
                    edgecolor='white', linewidth=2, alpha=0.9)
                ax.add_patch(rect_p)
                # Business (darker)
                rgb = mcolors.hex2color(stage['color'])
                darker = mcolors.rgb2hex(tuple([c * 0.7 for c in rgb]))
                rect_b = patches.FancyBboxPatch(
                    (0.5 - width/2 + p_width, current_y - stage_height), b_width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=darker,
                    edgecolor='white', linewidth=2, alpha=0.9)
                ax.add_patch(rect_b)
                if p_width > 0.05:
                    ax.text(0.5 - width/2 + p_width/2, current_y - stage_height/2,
                            f"{stage['personal']:,}", ha='center', va='center',
                            fontsize=20, color='white', fontweight='bold')
                if b_width > 0.05:
                    ax.text(0.5 - width/2 + p_width + b_width/2, current_y - stage_height/2,
                            f"{stage['business']:,}", ha='center', va='center',
                            fontsize=20, color='white', fontweight='bold')
                ax.text(0.5 + width/2 + 0.05, current_y - stage_height/2,
                        f"Total\n{stage['total']:,}", ha='left', va='center',
                        fontsize=18, fontweight='bold', color='black',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                  edgecolor='black', alpha=0.9))
            else:
                rect = patches.FancyBboxPatch(
                    (0.5 - width/2, current_y - stage_height), width, stage_height,
                    boxstyle="round,pad=0.01", facecolor=stage['color'],
                    edgecolor='white', linewidth=3, alpha=0.9)
                ax.add_patch(rect)
                ax.text(0.5, current_y - stage_height/2, f"{stage['total']:,}",
                        ha='center', va='center', fontsize=28, fontweight='bold',
                        color='white', zorder=10)

            ax.text(0.5 - width/2 - 0.05, current_y - stage_height/2,
                    stage['name'], ha='right', va='center',
                    fontsize=20, fontweight='600', color='#2c3e50')

            if i > 0 and stages[i-1]['total'] > 0:
                conv = stage['total'] / stages[i-1]['total'] * 100
                arrow_y = current_y + stage_gap/2
                ax.annotate('', xy=(0.5, arrow_y - stage_gap + 0.01),
                            xytext=(0.5, arrow_y - 0.01),
                            arrowprops=dict(arrowstyle='->', lw=3, color='#e74c3c'))
                ax.text(0.45, arrow_y - stage_gap/2, f"{conv:.1f}%",
                        ha='center', va='center', fontsize=18, fontweight='bold',
                        color='#e74c3c',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#e74c3c', alpha=0.9))
            current_y -= (stage_height + stage_gap)

        # Title and subtitle
        ax.text(0.5, 0.98, "Trailing Twelve Months Account Eligibility & Debit Card Funnel",
                ha='center', va='top', fontsize=28, fontweight='bold',
                color='#1e3d59', transform=ax.transAxes)
        ax.text(0.5, 0.93, f"{sd.strftime('%B %Y')} - {ed_date.strftime('%B %Y')}",
                ha='center', va='top', fontsize=20, style='italic',
                color='#7f8c8d', transform=ax.transAxes)

        if has_biz:
            legend_elements = [
                patches.Patch(facecolor='#808080', edgecolor='black', label='Personal (Lighter shade)'),
                patches.Patch(facecolor='#404040', edgecolor='black', label='Business (Darker shade)')]
            ax.legend(handles=legend_elements, loc='lower right', fontsize=16, frameon=True, fancybox=True)

        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_l12m_funnel.png')

        _slide(ctx, 'A7.8 - L12M Funnel', {
            'title': 'Trailing Twelve Months Account & Debit Card Funnel',
            'subtitle': f"{through:.1f}% conversion — {dctr_e:.1f}% DCTR among eligible",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"TTM accounts: {ta:,}", f"Eligible: {te:,}", f"With debit: {td:,}",
                         f"DCTR: {dctr_e:.1f}%"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ L12M funnel chart: {e}")

    ctx['results']['dctr_l12m_funnel'] = {'through': through, 'dctr': dctr_e}
    _report(ctx, f"   {ta:,} → {to:,} → {te:,} → {td:,} | Through: {through:.1f}%")
    return ctx


# =============================================================================
# BRANCH TREND: Historical vs L12M Change Tracking (A7.10a)
# =============================================================================

def run_dctr_branch_trend(ctx):
    """A7.10a: Dedicated branch historical vs L12M with change tracking."""
    _report(ctx, "\n🏢 DCTR — Branch Trend (A7.10a)")
    chart_dir = ctx['chart_dir']
    bm = ctx['config'].get('BranchMapping', {})

    # Get branch data from eligible sets
    hist_df, hist_ins = _branch_dctr(ctx['eligible_data'], bm)
    l12m_df, l12m_ins = _branch_dctr(ctx['eligible_last_12m'], bm)

    if hist_df.empty or l12m_df.empty:
        _report(ctx, "   ⚠️ Insufficient branch data"); return ctx

    # Merge for comparison
    hd = hist_df[hist_df['Branch'] != 'TOTAL'][['Branch', 'DCTR %', 'Total Accounts']].rename(
        columns={'DCTR %': 'Historical DCTR', 'Total Accounts': 'Hist Volume'})
    ld = l12m_df[l12m_df['Branch'] != 'TOTAL'][['Branch', 'DCTR %', 'Total Accounts']].rename(
        columns={'DCTR %': 'L12M DCTR', 'Total Accounts': 'L12M Volume'})
    merged = hd.merge(ld, on='Branch', how='outer').fillna(0)
    merged['Change pp'] = (merged['L12M DCTR'] - merged['Historical DCTR']) * 100
    merged['Historical DCTR %'] = merged['Historical DCTR'] * 100
    merged['L12M DCTR %'] = merged['L12M DCTR'] * 100
    merged = merged.sort_values('Historical DCTR', ascending=False)

    # Export table
    export_df = merged[['Branch', 'Historical DCTR %', 'L12M DCTR %', 'Change pp',
                         'Hist Volume', 'L12M Volume']].copy()
    improving = (merged['Change pp'] > 0).sum()
    avg_change = merged['Change pp'].mean()

    _save(ctx, export_df, 'DCTR-BranchTrend', 'Branch DCTR: Historical vs L12M',
          {'Improving': f"{improving} of {len(merged)}",
           'Avg Change': f"{avg_change:+.1f}pp"})

    # Chart: Horizontal grouped bars — matching notebook A7.10a format
    try:
        n = len(merged)
        fig_h = max(10, n * 0.6 + 2)
        fig, ax = plt.subplots(figsize=(14, fig_h))
        y = np.arange(n)
        h = 0.35
        ax.barh(y + h/2, merged['Historical DCTR %'], h, label='Historical', color='#BDC3C7',
                edgecolor='black', linewidth=1.5)
        ax.barh(y - h/2, merged['L12M DCTR %'], h, label='TTM', color='#2E86AB',
                edgecolor='black', linewidth=1.5)
        ax.set_yticks(y); ax.set_yticklabels(merged['Branch'].values, fontsize=18, fontweight='bold')
        ax.set_xlabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('Branch DCTR: Historical vs Trailing Twelve Months', fontsize=24, fontweight='bold', pad=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='x', labelsize=18)
        ax.legend(loc='lower right', fontsize=18)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)

        # Change annotations
        for i, (_, row) in enumerate(merged.iterrows()):
            chg = row['Change pp']
            color = '#27AE60' if chg > 0 else '#E74C3C' if chg < 0 else '#95A5A6'
            marker = '▲' if chg > 0 else '▼' if chg < 0 else '–'
            ax.text(max(row['Historical DCTR %'], row['L12M DCTR %']) + 1, i,
                    f'{marker} {chg:+.1f}pp', va='center', fontsize=18, color=color, fontweight='bold')

        # Period text
        sd = ctx['start_date']; ed_d = ctx['end_date']
        period_text = f'{sd.strftime("%b %Y")} - {ed_d.strftime("%b %Y")}'
        ax.text(0.98, 0.02, period_text, transform=ax.transAxes,
                fontsize=18, ha='right', va='bottom', style='italic', color='gray')

        plt.subplots_adjust(left=0.25, right=0.95)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_branch_trend.png')

        trend = "improving" if avg_change > 0 else "declining" if avg_change < 0 else "stable"
        _slide(ctx, 'A7.10a - Branch DCTR (Hist vs L12M)', {
            'title': 'Branch DCTR: Historical vs Trailing Twelve Months',
            'subtitle': f"{improving} of {len(merged)} branches {trend} — Avg change: {avg_change:+.1f}pp",
            'chart_path': cp, 'layout_index': 13})
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch trend chart: {e}")

    ctx['results']['dctr_branch_trend'] = {
        'improving': improving, 'total': len(merged), 'avg_change': avg_change}
    _report(ctx, f"   {improving}/{len(merged)} branches improving | Avg: {avg_change:+.1f}pp")
    return ctx


# =============================================================================
# HEATMAP: Monthly DCTR Heatmap by Branch (A7.13)
# =============================================================================

def run_dctr_heatmap(ctx):
    """A7.13: Monthly DCTR heatmap by branch for L12M."""
    _report(ctx, "\n🗺️ DCTR — Monthly Heatmap (A7.13)")
    chart_dir = ctx['chart_dir']
    l12m_months = ctx['last_12_months']
    bm = ctx['config'].get('BranchMapping', {})

    ed = ctx['eligible_data'].copy()
    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    ed['Month_Year'] = ed['Date Opened'].dt.strftime('%b%y')
    if bm:
        ed['Branch Name'] = ed['Branch'].map(bm).fillna(ed['Branch'])
    else:
        ed['Branch Name'] = ed['Branch']

    branches = sorted(ed['Branch Name'].unique())
    if len(branches) == 0 or len(l12m_months) == 0:
        _report(ctx, "   ⚠️ No branch/month data"); return ctx

    # Build heatmap matrix
    heat_data = []
    for branch in branches:
        bd = ed[ed['Branch Name'] == branch]
        row = {'Branch': branch}
        for month in l12m_months:
            md = bd[bd['Month_Year'] == month]
            t = len(md); w = len(md[md['Debit?'] == 'Yes'])
            row[month] = (w / t * 100) if t > 0 else np.nan
        heat_data.append(row)

    heat_df = pd.DataFrame(heat_data).set_index('Branch')
    _save(ctx, heat_df.reset_index(), 'DCTR-Heatmap', 'Monthly DCTR Heatmap by Branch')

    try:
        n_branches = len(branches)
        n_months = len(l12m_months)
        fig_h = max(8, n_branches * 0.6 + 2)
        fig, ax = plt.subplots(figsize=(max(14, n_months * 1.2), fig_h))

        # Custom colormap: red → yellow → green
        cmap = LinearSegmentedColormap.from_list('dctr', ['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71', '#27AE60'])
        data_vals = heat_df.values
        valid_vals = data_vals[~np.isnan(data_vals)]
        vmin = np.percentile(valid_vals, 5) if len(valid_vals) else 0
        vmax = np.percentile(valid_vals, 95) if len(valid_vals) else 100

        im = ax.imshow(data_vals, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)

        # Labels
        ax.set_xticks(range(n_months)); ax.set_xticklabels(l12m_months, rotation=45, ha='right', fontsize=14)
        ax.set_yticks(range(n_branches)); ax.set_yticklabels(branches, fontsize=14)

        # Cell text
        for i in range(n_branches):
            for j in range(n_months):
                v = data_vals[i, j]
                if not np.isnan(v):
                    txt_color = 'white' if v < (vmin + vmax) / 2 else 'black'
                    ax.text(j, i, f'{v:.0f}', ha='center', va='center',
                            fontsize=12, fontweight='bold', color=txt_color)

        plt.colorbar(im, ax=ax, label='DCTR %', shrink=0.8)
        ax.set_title('Monthly DCTR Heatmap by Branch (TTM)', fontsize=20, fontweight='bold')
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_heatmap.png')

        # Overall weighted DCTR
        t_all = len(ed[ed['Month_Year'].isin(l12m_months)])
        w_all = len(ed[(ed['Month_Year'].isin(l12m_months)) & (ed['Debit?'] == 'Yes')])
        weighted_avg = w_all / t_all * 100 if t_all else 0

        _slide(ctx, 'A7.13 - Monthly Heatmap', {
            'title': 'Monthly DCTR Heatmap by Branch (TTM)',
            'subtitle': f"Weighted avg: {weighted_avg:.1f}% across {n_branches} branches × {n_months} months",
            'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Heatmap: {e}")

    ctx['results']['dctr_heatmap'] = {'branches': len(branches)}
    _report(ctx, f"   {len(branches)} branches × {len(l12m_months)} months")
    return ctx


# =============================================================================
# SEASONALITY: Month/Quarter/Day-of-Week Analysis (A7.14)
# =============================================================================

def run_dctr_seasonality(ctx):
    """A7.14: DCTR seasonality by month, quarter, and day-of-week."""
    _report(ctx, "\n📅 DCTR — Seasonality (A7.14)")
    chart_dir = ctx['chart_dir']
    ed = ctx['eligible_data'].copy()
    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    valid = ed[ed['Date Opened'].notna()].copy()

    if valid.empty:
        _report(ctx, "   ⚠️ No date data"); return ctx

    valid['Month Name'] = valid['Date Opened'].dt.month_name()
    valid['Quarter'] = 'Q' + valid['Date Opened'].dt.quarter.astype(str)
    valid['Day of Week'] = valid['Date Opened'].dt.day_name()

    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    q_order = ['Q1', 'Q2', 'Q3', 'Q4']

    # Monthly DCTR
    m_rows = []
    for m in month_order:
        md = valid[valid['Month Name'] == m]
        if len(md) > 0:
            t, w, d = _dctr(md)
            m_rows.append({'Month Name': m, 'Total Accounts': t, 'With Debit': w, 'DCTR %': d * 100})
    monthly = pd.DataFrame(m_rows)

    # Quarterly
    q_rows = []
    for q in q_order:
        qd = valid[valid['Quarter'] == q]
        if len(qd) > 0:
            t, w, d = _dctr(qd)
            q_rows.append({'Quarter': q, 'Total Accounts': t, 'With Debit': w, 'DCTR %': d * 100})
    quarterly = pd.DataFrame(q_rows)

    # Day of week
    d_rows = []
    for d in dow_order:
        dd = valid[valid['Day of Week'] == d]
        if len(dd) > 0:
            t, w, d_val = _dctr(dd)
            d_rows.append({'Day of Week': d, 'Total Accounts': t, 'With Debit': w, 'DCTR %': d_val * 100})
    dow = pd.DataFrame(d_rows)

    _save(ctx, {'Monthly': monthly, 'Quarterly': quarterly, 'Day of Week': dow},
          'DCTR-Seasonality', 'DCTR Seasonality Analysis')

    try:
        fig, axes = plt.subplots(1, 3, figsize=(22, 8))

        # Monthly
        if not monthly.empty:
            ax = axes[0]
            vals = monthly['DCTR %'].values
            ax.bar(range(len(monthly)), vals, color='#2E86AB', edgecolor='white')
            ax.set_xticks(range(len(monthly)))
            ax.set_xticklabels([m[:3] for m in monthly['Month Name']], rotation=45, fontsize=14)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f'{v:.0f}%', ha='center', fontsize=12, fontweight='bold')
            ax.set_ylabel('DCTR (%)', fontsize=14); ax.set_title('By Month', fontweight='bold', fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax.tick_params(axis='y', labelsize=12)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        # Quarterly
        if not quarterly.empty:
            ax = axes[1]
            vals = quarterly['DCTR %'].values
            ax.bar(quarterly['Quarter'], vals, color='#4ECDC4', edgecolor='white', width=0.6)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=14, fontweight='bold')
            ax.set_ylabel('DCTR (%)', fontsize=14); ax.set_title('By Quarter', fontweight='bold', fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax.tick_params(axis='both', labelsize=12)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        # Day of Week
        if not dow.empty:
            ax = axes[2]
            vals = dow['DCTR %'].values
            weekday_mask = [d not in ['Saturday', 'Sunday'] for d in dow['Day of Week']]
            colors = ['#2E86AB' if wd else '#E74C3C' for wd in weekday_mask]
            ax.bar(range(len(dow)), vals, color=colors, edgecolor='white')
            ax.set_xticks(range(len(dow)))
            ax.set_xticklabels([d[:3] for d in dow['Day of Week']], fontsize=14)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f'{v:.0f}%', ha='center', fontsize=12, fontweight='bold')
            ax.set_ylabel('DCTR (%)', fontsize=14); ax.set_title('By Day of Week', fontweight='bold', fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
            ax.tick_params(axis='y', labelsize=12)
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        plt.suptitle('DCTR Seasonality Analysis', fontsize=22, fontweight='bold', y=1.02)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_seasonality.png')

        # Insights
        best_month = monthly.loc[monthly['DCTR %'].idxmax(), 'Month Name'] if not monthly.empty else 'N/A'
        worst_month = monthly.loc[monthly['DCTR %'].idxmin(), 'Month Name'] if not monthly.empty else 'N/A'
        best_dctr = monthly['DCTR %'].max() if not monthly.empty else 0
        worst_dctr = monthly['DCTR %'].min() if not monthly.empty else 0
        spread = best_dctr - worst_dctr

        weekday_avg = dow[~dow['Day of Week'].isin(['Saturday', 'Sunday'])]['DCTR %'].mean() if not dow.empty else 0
        weekend_avg = dow[dow['Day of Week'].isin(['Saturday', 'Sunday'])]['DCTR %'].mean() if not dow.empty else 0

        _slide(ctx, 'A7.14 - Seasonality', {
            'title': 'DCTR Seasonality Analysis',
            'subtitle': f"Best: {best_month} ({best_dctr:.0f}%) — Worst: {worst_month} ({worst_dctr:.0f}%) — {spread:.0f}pp spread",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"Monthly DCTR spread: {spread:.1f}pp",
                         f"Weekday avg: {weekday_avg:.1f}% | Weekend avg: {weekend_avg:.1f}%"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Seasonality chart: {e}")

    ctx['results']['dctr_seasonality'] = {
        'best_month': best_month if not monthly.empty else 'N/A',
        'worst_month': worst_month if not monthly.empty else 'N/A',
        'spread': spread if not monthly.empty else 0}
    _report(ctx, f"   Best: {best_month if not monthly.empty else 'N/A'} | Worst: {worst_month if not monthly.empty else 'N/A'}")
    return ctx


# =============================================================================
# VINTAGE: Vintage Curves & Cohort Analysis (A7.15)
# =============================================================================

def run_dctr_vintage(ctx):
    """A7.15: Vintage curves (DCTR by account age) + cohort analysis by year."""
    _report(ctx, "\n📊 DCTR — Vintage & Cohort (A7.15)")
    chart_dir = ctx['chart_dir']
    ed = ctx['eligible_data'].copy()
    ed['Date Opened'] = pd.to_datetime(ed['Date Opened'], errors='coerce')
    valid = ed[ed['Date Opened'].notna()].copy()

    if valid.empty:
        _report(ctx, "   ⚠️ No data"); return ctx

    valid['Account Age Days'] = (pd.Timestamp.now() - valid['Date Opened']).dt.days
    valid['Year'] = valid['Date Opened'].dt.year

    # Vintage buckets (fine-grained)
    vintage_buckets = [
        ('0-30 days', 0, 30), ('31-90 days', 31, 90), ('91-180 days', 91, 180),
        ('181-365 days', 181, 365), ('1-2 years', 366, 730), ('2-3 years', 731, 1095),
        ('3-5 years', 1096, 1825), ('5-10 years', 1826, 3650), ('10+ years', 3651, 999999)]

    v_rows = []
    cum_debit = 0; cum_total = 0
    for label, lo, hi in vintage_buckets:
        seg = valid[(valid['Account Age Days'] >= lo) & (valid['Account Age Days'] <= hi)]
        if len(seg) > 0:
            t, w, d = _dctr(seg)
            cum_total += t; cum_debit += w
            v_rows.append({'Age Bucket': label, 'Total Accounts': t, 'With Debit': w,
                           'DCTR %': d * 100,
                           'Cumulative Capture %': cum_debit / cum_total * 100 if cum_total else 0})
    vintage_df = pd.DataFrame(v_rows)

    # Cohort analysis by year
    cohort_years = sorted(valid['Year'].dropna().unique())
    c_rows = []
    for yr in cohort_years:
        seg = valid[valid['Year'] == yr]
        if len(seg) > 10:
            t, w, d = _dctr(seg)
            c_rows.append({'Cohort Year': int(yr), 'Total Accounts': t, 'With Debit': w, 'DCTR %': d * 100})
    cohort_df = pd.DataFrame(c_rows)

    _save(ctx, {'Vintage': vintage_df, 'Cohort': cohort_df}, 'DCTR-Vintage', 'Vintage & Cohort Analysis')

    try:
        fig = plt.figure(figsize=(18, 12))

        # Top: Vintage curve with cumulative line
        ax1 = plt.subplot(2, 1, 1)
        if not vintage_df.empty:
            x_pos = np.arange(len(vintage_df))
            bars = ax1.bar(x_pos, vintage_df['DCTR %'], color='#2E86AB', alpha=0.8, edgecolor='white')
            for bar, v in zip(bars, vintage_df['DCTR %']):
                ax1.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.0f}%',
                         ha='center', fontsize=14, fontweight='bold')

            ax1_twin = ax1.twinx()
            ax1_twin.plot(x_pos, vintage_df['Cumulative Capture %'],
                          color='#E74C3C', marker='o', ms=9, lw=3, label='Cumulative Capture %')
            for x, y in zip(x_pos, vintage_df['Cumulative Capture %']):
                ax1_twin.text(x, y + 2, f'{y:.0f}%', ha='center', fontsize=12, color='#E74C3C', fontweight='bold')

            ax1.set_xticks(x_pos)
            ax1.set_xticklabels(vintage_df['Age Bucket'], rotation=30, ha='right', fontsize=14)
            ax1.set_ylabel('DCTR %', color='#2E86AB', fontsize=16)
            ax1.set_title('DCTR by Account Age (Vintage Curve)', fontweight='bold', fontsize=18)
            ax1_twin.set_ylabel('Cumulative Capture %', color='#E74C3C', fontsize=16)
            ax1_twin.set_ylim(0, 110)
            ax1.tick_params(axis='y', labelsize=14)
            ax1_twin.tick_params(axis='y', labelsize=14)
            ax1.grid(axis='y', alpha=0.2, ls='--')

        # Bottom: Cohort trend
        ax2 = plt.subplot(2, 1, 2)
        if not cohort_df.empty and len(cohort_df) >= 2:
            years = cohort_df['Cohort Year'].values
            dctr_by_year = cohort_df['DCTR %'].values
            bars2 = ax2.bar(range(len(years)), dctr_by_year, color='#4ECDC4', edgecolor='white', alpha=0.8)
            for i, (bar, v) in enumerate(zip(bars2, dctr_by_year)):
                ax2.text(bar.get_x() + bar.get_width()/2, v + 1, f'{v:.0f}%',
                         ha='center', fontsize=14, fontweight='bold')

            # Trend line
            z = np.polyfit(range(len(years)), dctr_by_year, 1)
            p = np.poly1d(z)
            ax2.plot(range(len(years)), p(range(len(years))), color='red', ls='--', lw=2, alpha=0.7)

            ax2.set_xticks(range(len(years)))
            ax2.set_xticklabels(years, fontsize=14, rotation=30, ha='right')
            ax2.set_ylabel('DCTR %', fontsize=16)
            ax2.set_title('DCTR by Account Opening Year (Cohort Analysis)', fontweight='bold', fontsize=18)
            ax2.tick_params(axis='y', labelsize=14)
            ax2.grid(axis='y', alpha=0.2, ls='--')

            slope = z[0]
            trend = f"+{slope:.1f}pp/yr" if slope > 0 else f"{slope:.1f}pp/yr"
            tc = 'green' if slope > 0 else 'red'
            ax2.text(0.98, 0.95, f'Trend: {trend}', transform=ax2.transAxes, fontsize=16,
                     ha='right', va='top', fontweight='bold', color=tc,
                     bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor=tc))
        else:
            slope = 0

        plt.suptitle('Vintage Curves & Cohort Analysis', fontsize=22, fontweight='bold', y=1.01)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_vintage.png')

        # Insights
        new_dctr = vintage_df.iloc[0]['DCTR %'] if not vintage_df.empty else 0
        mature_dctr = vintage_df.iloc[-1]['DCTR %'] if not vintage_df.empty else 0
        gap = new_dctr - mature_dctr

        _slide(ctx, 'A7.15 - Vintage & Cohort', {
            'title': 'Vintage Curves & Cohort Analysis',
            'subtitle': f"New accounts at {new_dctr:.0f}% vs mature at {mature_dctr:.0f}% — "
                        f"Cohort trend {'improving' if slope > 0 else 'declining'} at {slope:.1f}pp/year",
            'chart_path': cp, 'layout_index': 9,
            'insights': [f"New (0-30 days) DCTR: {new_dctr:.1f}%",
                         f"Mature (10+ years) DCTR: {mature_dctr:.1f}%",
                         f"Gap: {gap:+.1f}pp",
                         f"Cohort years: {len(cohort_df)}"]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Vintage chart: {e}")

    ctx['results']['dctr_vintage'] = {
        'new_dctr': vintage_df.iloc[0]['DCTR %'] if not vintage_df.empty else 0,
        'mature_dctr': vintage_df.iloc[-1]['DCTR %'] if not vintage_df.empty else 0,
        'cohort_slope': slope if 'slope' in dir() else 0}
    _report(ctx, f"   {len(vintage_df)} vintage buckets | {len(cohort_df)} cohort years")
    return ctx


# =============================================================================
# PERSONAL VS BUSINESS BY DECADE (A7.6b)
# =============================================================================

def run_dctr_decade_pb(ctx):
    """A7.6b: Personal vs Business DCTR by decade — grouped bar chart."""
    _report(ctx, "\n📊 DCTR — Personal vs Business by Decade (A7.6b)")
    chart_dir = ctx['chart_dir']

    d4 = ctx['results'].get('dctr_4', {}).get('decade', pd.DataFrame())
    d5 = ctx['results'].get('dctr_5', {}).get('decade', pd.DataFrame())

    if d4.empty:
        _report(ctx, "   ⚠️ No personal decade data"); return ctx

    has_biz = not d5.empty and d5['Total Accounts'].sum() > 0
    p_dec = d4[d4['Decade'] != 'TOTAL'].copy()

    if has_biz:
        b_dec = d5[d5['Decade'] != 'TOTAL'].copy()
        all_decades = sorted(set(p_dec['Decade'].tolist()) | set(b_dec['Decade'].tolist()))
    else:
        all_decades = p_dec['Decade'].tolist()

    try:
        fig, ax = plt.subplots(figsize=(16, 8))
        x = np.arange(len(all_decades))

        # Personal DCTR by decade
        p_rates = []
        for d in all_decades:
            match = p_dec[p_dec['Decade'] == d]
            p_rates.append(match['DCTR %'].iloc[0] * 100 if not match.empty else 0)

        if has_biz:
            width = 0.35
            b_rates = []
            for d in all_decades:
                match = b_dec[b_dec['Decade'] == d]
                b_rates.append(match['DCTR %'].iloc[0] * 100 if not match.empty else 0)

            ax.bar(x - width/2, p_rates, width, label='Personal', color='#4472C4',
                   alpha=0.9, edgecolor='black', linewidth=2)
            ax.bar(x + width/2, b_rates, width, label='Business', color='#ED7D31',
                   alpha=0.9, edgecolor='black', linewidth=2)

            for i, v in enumerate(p_rates):
                if v > 0:
                    ax.text(i - width/2, v + 1, f'{v:.0f}%', ha='center', fontsize=18,
                            fontweight='bold', color='#4472C4')
            for i, v in enumerate(b_rates):
                if v > 0:
                    ax.text(i + width/2, v + 1, f'{v:.0f}%', ha='center', fontsize=18,
                            fontweight='bold', color='#ED7D31')
        else:
            ax.bar(x, p_rates, 0.6, label='Personal', color='#4472C4',
                   alpha=0.9, edgecolor='black', linewidth=2)
            for i, v in enumerate(p_rates):
                if v > 0:
                    ax.text(i, v + 1, f'{v:.0f}%', ha='center', fontsize=20, fontweight='bold')

        ax.set_title('Eligible Personal vs Business DCTR by Decade',
                     fontsize=24, fontweight='bold', pad=20)
        ax.set_xlabel('Decade', fontsize=20, fontweight='bold')
        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(all_decades, fontsize=20)
        ax.tick_params(axis='y', labelsize=20)
        max_v = max(p_rates + (b_rates if has_biz else []))
        ax.set_ylim(0, max_v * 1.15 if max_v > 0 else 100)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=18, frameon=True)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--'); ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_decade_pb.png')

        subtitle = f"Personal: {p_rates[0]:.0f}% → {p_rates[-1]:.0f}%"
        if has_biz and b_rates:
            subtitle += f" | Business: {b_rates[0]:.0f}% → {b_rates[-1]:.0f}%"
        _slide(ctx, 'A7.6b - Personal vs Business by Decade', {
            'title': 'Eligible Personal vs Business DCTR by Decade',
            'subtitle': subtitle, 'chart_path': cp, 'layout_index': 9})
    except Exception as e:
        _report(ctx, f"   ⚠️ Decade P/B chart: {e}")

    ctx['results']['dctr_decade_pb'] = {'decades': len(all_decades)}
    _report(ctx, f"   {len(all_decades)} decades plotted")
    return ctx


# =============================================================================
# ELIGIBLE VS NON-ELIGIBLE DCTR (A7.9)
# =============================================================================

def run_dctr_eligible_vs_non(ctx):
    """A7.9: Eligible vs Non-Eligible DCTR comparison (Last 12 Months)."""
    _report(ctx, "\n📊 DCTR — Eligible vs Non-Eligible (A7.9)")
    chart_dir = ctx['chart_dir']
    sd, ed_date = ctx['start_date'], ctx['end_date']

    data = ctx['data'].copy()
    data['Date Opened'] = pd.to_datetime(data['Date Opened'], errors='coerce')
    l12m_all = data[(data['Date Opened'] >= sd) & (data['Date Opened'] <= ed_date)]

    # Open accounts in L12M
    open_l12m = ctx.get('open_last_12m')
    if open_l12m is None or open_l12m.empty:
        open_l12m = l12m_all[l12m_all['Date Closed'].isna()] if 'Date Closed' in l12m_all.columns else l12m_all

    elig_l12m = ctx.get('eligible_last_12m')
    if elig_l12m is None or elig_l12m.empty:
        _report(ctx, "   ⚠️ No L12M eligible data"); return ctx

    # Non-eligible = open but not eligible
    non_elig = open_l12m[~open_l12m.index.isin(elig_l12m.index)]

    e_total = len(elig_l12m)
    e_debit = len(elig_l12m[elig_l12m['Debit?'] == 'Yes'])
    e_dctr = (e_debit / e_total * 100) if e_total > 0 else 0

    n_total = len(non_elig)
    n_debit = len(non_elig[non_elig['Debit?'] == 'Yes']) if not non_elig.empty else 0
    n_dctr = (n_debit / n_total * 100) if n_total > 0 else 0

    gap = e_dctr - n_dctr

    # Excel export
    comp_df = pd.DataFrame([
        {'Account Type': 'Eligible', 'Total': e_total, 'With Debit': e_debit, 'DCTR %': e_dctr / 100},
        {'Account Type': 'Non-Eligible', 'Total': n_total, 'With Debit': n_debit, 'DCTR %': n_dctr / 100},
    ])
    _save(ctx, comp_df, 'DCTR-EligVsNon-L12M', 'Eligible vs Non-Eligible DCTR',
          {'Eligible DCTR': f"{e_dctr:.1f}%", 'Non-Eligible DCTR': f"{n_dctr:.1f}%",
           'Gap': f"{gap:+.1f}pp"})

    # Chart A7.9: Side-by-side bars matching notebook
    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        categories = ['Eligible\nAccounts', 'Non-Eligible\nAccounts']
        dctr_vals = [e_dctr, n_dctr]
        counts = [e_total, n_total]
        debit_counts = [e_debit, n_debit]
        colors = ['#2ecc71', '#e74c3c']

        bars = ax.bar(categories, dctr_vals, color=colors, edgecolor='black', linewidth=2, alpha=0.8)
        for bar, d, cnt, wd in zip(bars, dctr_vals, counts, debit_counts):
            ax.text(bar.get_x() + bar.get_width()/2, d + 1, f'{d:.1f}%',
                    ha='center', va='bottom', fontsize=24, fontweight='bold')
            if d > 20:
                ax.text(bar.get_x() + bar.get_width()/2, d/2,
                        f'{cnt:,}\naccounts\n\n{wd:,}\nwith debit',
                        ha='center', va='center', fontsize=16, fontweight='bold', color='white')

        # Gap indicator
        gap_text = f'Gap: {gap:+.1f}pp\n{"Eligible performs better" if gap > 0 else "Non-eligible performs better"}'
        gc = 'green' if gap > 0 else 'red'
        ax.text(0.5, 0.5, gap_text, transform=ax.transAxes, ha='center', va='center',
                fontsize=20, fontweight='bold', color=gc,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=gc, linewidth=2))

        ax.set_ylabel('DCTR (%)', fontsize=20, fontweight='bold')
        ax.set_title('Trailing Twelve Months: Eligible vs Non-Eligible DCTR',
                     fontsize=24, fontweight='bold', pad=20)
        ax.set_ylim(0, max(dctr_vals) * 1.15 if max(dctr_vals) > 0 else 100)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax.tick_params(axis='both', labelsize=20)
        ax.grid(False); ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        period_text = f'Period: {sd.strftime("%b %Y")} - {ed_date.strftime("%b %Y")}'
        ax.text(0.5, -0.10, period_text, transform=ax.transAxes,
                fontsize=16, ha='center', style='italic', color='gray')
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_eligible_vs_non.png')

        better = "Eligible" if gap > 0 else "Non-Eligible"
        _slide(ctx, 'A7.9 - Eligible vs Non-Eligible DCTR', {
            'title': 'Eligible vs Non-Eligible DCTR (Trailing Twelve Months)',
            'subtitle': f"Eligible at {e_dctr:.0f}% vs Non-Eligible at {n_dctr:.0f}% — Gap of {gap:+.1f}pp",
            'chart_path': cp, 'layout_index': 9,
            'insights': [
                f"Period: {sd.strftime('%b %Y')} to {ed_date.strftime('%b %Y')}",
                f"Eligible: {e_total:,} ({e_dctr:.1f}% DCTR)",
                f"Non-Eligible: {n_total:,} ({n_dctr:.1f}% DCTR)",
                f"{better} outperform by {abs(gap):.1f}pp",
            ]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Eligible vs Non chart: {e}")

    ctx['results']['dctr_elig_vs_non'] = {'eligible_dctr': e_dctr, 'non_eligible_dctr': n_dctr, 'gap': gap}
    _report(ctx, f"   Eligible: {e_dctr:.1f}% | Non-Eligible: {n_dctr:.1f}% | Gap: {gap:+.1f}pp")
    return ctx


# =============================================================================
# BRANCH DCTR L12M FOCUS — VERTICAL BARS (A7.10b)
# =============================================================================

def run_dctr_branch_l12m(ctx):
    """A7.10b: Branch DCTR with L12M focus — vertical bars sorted by L12M, volume + DCTR lines."""
    _report(ctx, "\n🏢 DCTR — Branch L12M Focus (A7.10b)")
    chart_dir = ctx['chart_dir']
    bm = ctx['config'].get('BranchMapping', {})

    hist_df, _ = _branch_dctr(ctx['eligible_data'], bm)
    l12m_df, _ = _branch_dctr(ctx['eligible_last_12m'], bm)

    if hist_df.empty or l12m_df.empty:
        _report(ctx, "   ⚠️ Insufficient branch data"); return ctx

    hd = hist_df[hist_df['Branch'] != 'TOTAL'][['Branch', 'DCTR %', 'Total Accounts']].rename(
        columns={'DCTR %': 'Historical DCTR', 'Total Accounts': 'Hist Volume'})
    ld = l12m_df[l12m_df['Branch'] != 'TOTAL'][['Branch', 'DCTR %', 'Total Accounts']].rename(
        columns={'DCTR %': 'L12M DCTR', 'Total Accounts': 'L12M Volume'})
    merged = hd.merge(ld, on='Branch', how='outer').fillna(0)
    merged = merged.sort_values('L12M DCTR', ascending=False).reset_index(drop=True)
    merged['Historical DCTR %'] = merged['Historical DCTR'] * 100
    merged['L12M DCTR %'] = merged['L12M DCTR'] * 100
    merged['Change %'] = merged['L12M DCTR %'] - merged['Historical DCTR %']

    # Weighted averages
    hist_wa = (merged['Historical DCTR'] * merged['Hist Volume']).sum() / merged['Hist Volume'].sum() * 100 if merged['Hist Volume'].sum() > 0 else 0
    l12m_wa = (merged['L12M DCTR'] * merged['L12M Volume']).sum() / merged['L12M Volume'].sum() * 100 if merged['L12M Volume'].sum() > 0 else 0

    n = len(merged)
    improving = (merged['Change %'] > 0).sum()
    avg_change = merged['Change %'].mean()

    # Chart A7.10b: Large vertical bars + DCTR lines (matching notebook)
    try:
        fig, ax1 = plt.subplots(figsize=(28, 14))
        x_pos = np.arange(n)

        # Volume bars
        bars = ax1.bar(x_pos, merged['L12M Volume'], width=0.6, color='#D9D9D9',
                       edgecolor='black', linewidth=2)
        ax1.set_ylabel('Eligible Accounts (TTM)', fontsize=28, fontweight='bold')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(merged['Branch'].values, rotation=45, ha='right', fontsize=24, fontweight='bold')
        ax1.tick_params(axis='y', labelsize=22)
        ax1.grid(False)
        for spine in ax1.spines.values():
            spine.set_visible(False)

        # Volume labels
        for i, v in enumerate(merged['L12M Volume']):
            ax1.text(i, v + max(merged['L12M Volume']) * 0.015, f'{int(v):,}',
                     ha='center', va='bottom', fontsize=22, fontweight='bold', color='#333')

        # DCTR lines on secondary axis
        ax2 = ax1.twinx()
        hist_line = ax2.plot(x_pos, merged['Historical DCTR %'], 'o-', color='#BDC3C7',
                             lw=3, ms=10, label='Historical DCTR')
        l12m_line = ax2.plot(x_pos, merged['L12M DCTR %'], 'o-', color='#2E86AB',
                             lw=4, ms=14, label='TTM DCTR', zorder=5)

        # Data labels on lines
        for i, v in enumerate(merged['L12M DCTR %']):
            ax2.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=22, fontweight='bold', color='#2E86AB')
        for i, v in enumerate(merged['Historical DCTR %']):
            ax2.text(i, v - 3, f'{v:.0f}%', ha='center', fontsize=18, color='#BDC3C7')

        ax2.set_ylabel('DCTR (%)', fontsize=28, fontweight='bold')
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x:.0f}%'))
        ax2.tick_params(axis='y', labelsize=22)
        max_dctr = max(merged['L12M DCTR %'].max(), merged['Historical DCTR %'].max())
        ax2.set_ylim(0, max_dctr * 1.2 if max_dctr > 0 else 100)
        ax2.grid(False)
        for spine in ax2.spines.values():
            spine.set_visible(False)

        plt.title('Debit Card Take Rate by Branch\nHistorical vs Trailing Twelve Months',
                  fontsize=34, fontweight='bold', pad=30)
        ax2.legend(handles=[hist_line[0], l12m_line[0]],
                   labels=['Historical DCTR', 'TTM DCTR'],
                   loc='upper right', bbox_to_anchor=(1.0, 0.98),
                   fontsize=22, frameon=True, fancybox=True)
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / 'dctr_branch_l12m.png')

        trend = "improving" if avg_change > 0 else "declining" if avg_change < 0 else "stable"
        _slide(ctx, 'A7.10b - Branch DCTR (L12M Focus)', {
            'title': 'Branch DCTR: TTM Performance',
            'subtitle': f"TTM avg at {l12m_wa:.0f}% — {improving} of {n} branches {trend} ({avg_change:+.1f}pp)",
            'chart_path': cp, 'layout_index': 9,
            'insights': [
                f"Branches analyzed: {n}",
                f"TTM weighted average: {l12m_wa:.1f}%",
                f"Historical weighted average: {hist_wa:.1f}%",
                f"Branches improving: {improving} of {n}",
            ]})
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch L12M chart: {e}")

    ctx['results']['dctr_branch_l12m'] = {'improving': improving, 'total': n, 'avg_change': avg_change}
    _report(ctx, f"   {improving}/{n} branches improving | L12M avg: {l12m_wa:.1f}%")
    return ctx


# =============================================================================
# MAIN SUITE RUNNER
# =============================================================================

def run_dctr_suite(ctx):
    """Run the full DCTR analysis suite (A6 + A7 combined)."""
    from ars_analysis.pipeline import save_to_excel
    ctx['_save_to_excel'] = save_to_excel

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
    _report(ctx, "💳 A6/A7 — DEBIT CARD TAKE RATE (DCTR) ANALYSIS")
    _report(ctx, "=" * 60)

    # Core A6 data analyses
    _report(ctx, "\n── A6: Core DCTR Data ──")
    ctx = _safe(run_dctr_1, 'DCTR-1')
    ctx = _safe(run_dctr_2, 'DCTR-2')
    ctx = _safe(run_dctr_3, 'DCTR-3')
    ctx = _safe(run_dctr_4_5, 'DCTR-4/5')
    ctx = _safe(run_dctr_6_7, 'DCTR-6/7')
    ctx = _safe(run_dctr_8, 'DCTR-8')

    _report(ctx, "\n── A6: Branch & Dimensional ──")
    ctx = _safe(run_dctr_9, 'DCTR-9')
    ctx = _safe(run_dctr_10, 'DCTR-10')
    ctx = _safe(run_dctr_11, 'DCTR-11')
    ctx = _safe(run_dctr_12, 'DCTR-12')
    ctx = _safe(run_dctr_13, 'DCTR-13')
    ctx = _safe(run_dctr_14, 'DCTR-14')
    ctx = _safe(run_dctr_15, 'DCTR-15')
    ctx = _safe(run_dctr_16, 'DCTR-16')

    # Extended A7 visualizations
    _report(ctx, "\n── A7: Extended Visualizations ──")
    ctx = _safe(run_dctr_segment_trends, 'Segment Trends')
    ctx = _safe(run_dctr_decade_trend, 'Decade Trend')
    ctx = _safe(run_dctr_decade_pb, 'Decade P/B')
    ctx = _safe(run_dctr_l12m_trend, 'L12M Trend')
    ctx = _safe(run_dctr_funnel, 'Funnel')
    ctx = _safe(run_dctr_l12m_funnel, 'L12M Funnel')
    ctx = _safe(run_dctr_eligible_vs_non, 'Eligible vs Non')
    ctx = _safe(run_dctr_branch_trend, 'Branch Trend')
    ctx = _safe(run_dctr_branch_l12m, 'Branch L12M')
    ctx = _safe(run_dctr_heatmap, 'Heatmap')
    ctx = _safe(run_dctr_seasonality, 'Seasonality')
    ctx = _safe(run_dctr_vintage, 'Vintage')
    ctx = _safe(run_dctr_combo_slide, 'Combo Slide')

    # Reorder DCTR slides to match mapping sequence
    DCTR_ORDER = [
        # Act 1: The Headline
        'A7 - DCTR Comparison',
        # Act 2: Recent Trajectory
        'A7.6a - Last 12 Months DCTR Trend',
        'A7.4 - Segment Trends',
        # Act 3: The Funnel (Root Cause)
        'A7.8 - L12M Funnel',
        'A7.7 - Historical Funnel',
        # Act 4: Branch Accountability
        'A7.10a - Branch DCTR (Hist vs L12M)',
        # Act 5: The Opportunity
        'A7.9 - Eligible vs Non-Eligible DCTR',
        'A7.11 - DCTR by Account Holder Age',
        'A7.12 - DCTR by Account Age',
        # Act 6: Remaining Branch Detail
        'A7.10b - Branch DCTR (L12M Focus)',
        'A7.10c - Branch Top 10',
        # Act 7: Supporting Detail
        'A7.5 - Decade Trend',
        'A7.6b - Personal vs Business by Decade',
        'A7.13 - Monthly Heatmap',
        'A7.14 - Seasonality',
        'A7.15 - Vintage & Cohort',
        'A7.16 - Branch L12M Table',
    ]
    order_map = {sid: i for i, sid in enumerate(DCTR_ORDER)}
    dctr_slides = [s for s in ctx['all_slides'] if s['category'] == 'DCTR']
    non_dctr = [s for s in ctx['all_slides'] if s['category'] != 'DCTR']
    dctr_slides.sort(key=lambda s: order_map.get(s['id'], 999))
    ctx['all_slides'] = non_dctr + dctr_slides

    slides = len(dctr_slides)
    _report(ctx, f"\n✅ A6/A7 complete — {slides} DCTR slides created (reordered to mapping)")
    return ctx


if __name__ == '__main__':
    print("DCTR module — import and call run_dctr_suite(ctx)")
