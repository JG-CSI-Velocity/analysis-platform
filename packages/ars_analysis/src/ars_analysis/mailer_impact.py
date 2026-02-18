"""
mailer_impact.py -- A15 Market Reach & Responder Impact Visuals
================================================================
A15.1 - Market Reach Bubble: nested circles showing eligible cardholders
        vs unique responders (proportional area).
A15.2 - Spend Share: horizontal bars showing total spend from all open
        accounts, eligible accounts, and responders with proportion KPIs.

Usage:
    from mailer_impact import run_mailer_impact_suite
    ctx = run_mailer_impact_suite(ctx)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from ars_analysis.mailer_common import (
    RESPONSE_SEGMENTS, MAILED_SEGMENTS, SPEND_PATTERN,
    report as _report, save_chart as _save_chart, slide as _slide,
    parse_month as _parse_month, discover_pairs as _discover_pairs,
)

# =============================================================================
# CHART COLORS
# =============================================================================

COLOR_OUTER = '#3498DB'   # blue - eligible w/ card
COLOR_INNER = '#E74C3C'   # red - responders
COLOR_RESP = '#2ECC71'    # green - responder bar
COLOR_NON = '#95A5A6'     # gray - non-responder bar


# =============================================================================
# A15.1 -- MARKET REACH BUBBLE
# =============================================================================

def run_market_reach(ctx):
    """Nested proportional circles: eligible w/ card vs unique responders."""
    _report(ctx, "\n📊 A15.1 -- Market Reach")

    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   No mailer data -- skipping A15.1")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']

    # Eligible with a debit card
    eligible_debit = ctx.get('eligible_with_debit')
    if eligible_debit is None or eligible_debit.empty:
        _report(ctx, "   No eligible-with-debit subset -- skipping")
        return ctx
    n_eligible = len(eligible_debit)

    # Unique responders across all mail months
    resp_mask = pd.Series(False, index=data.index)
    mailed_mask = pd.Series(False, index=data.index)
    for month, resp_col, mail_col in pairs:
        resp_mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
        mailed_mask |= data[mail_col].isin(MAILED_SEGMENTS)
    n_responders = int(resp_mask.sum())
    n_mailed = int(mailed_mask.sum())

    if n_eligible == 0:
        _report(ctx, "   No eligible accounts -- skipping")
        return ctx

    resp_rate = n_responders / n_mailed * 100 if n_mailed > 0 else 0
    penetration = n_responders / n_eligible * 100

    # --- Draw proportional nested circles ---
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('white')

    # Radii proportional to sqrt(count) so area is proportional
    max_radius = 2.5
    r_outer = max_radius
    r_inner = max_radius * np.sqrt(n_responders / n_eligible)

    cx, cy = 0.35, 0.0  # center (shifted left to make room for KPIs)

    # Outer circle
    outer = plt.Circle((cx, cy), r_outer, facecolor=COLOR_OUTER,
                        alpha=0.25, edgecolor=COLOR_OUTER, linewidth=2.5)
    ax.add_patch(outer)

    # Inner circle
    inner = plt.Circle((cx, cy), r_inner, facecolor=COLOR_INNER,
                        alpha=0.35, edgecolor=COLOR_INNER, linewidth=2.5)
    ax.add_patch(inner)

    # Labels inside circles
    ax.text(cx, cy + r_outer * 0.65, 'Eligible with a Card',
            ha='center', va='center', fontsize=16, fontweight='bold',
            color=COLOR_OUTER)
    ax.text(cx, cy + r_outer * 0.45, f'{n_eligible:,}',
            ha='center', va='center', fontsize=22, fontweight='bold',
            color=COLOR_OUTER)

    ax.text(cx, cy - 0.15, 'Unique',
            ha='center', va='center', fontsize=14, fontweight='bold',
            color='white')
    ax.text(cx, cy - 0.50, 'Responders',
            ha='center', va='center', fontsize=14, fontweight='bold',
            color='white')
    ax.text(cx, cy - 0.90, f'{n_responders:,}',
            ha='center', va='center', fontsize=20, fontweight='bold',
            color='white')

    # KPI callouts on the right side
    kpi_x = 4.2
    kpis = [
        (f'{n_mailed:,}', 'Total Mailed'),
        (f'{n_responders:,}', 'Unique Responders'),
        (f'{resp_rate:.1f}%', 'Response Rate'),
        (f'{penetration:.1f}%', 'Market Penetration'),
    ]
    for i, (val, label) in enumerate(kpis):
        y = 1.8 - i * 1.3
        ax.text(kpi_x, y, val, ha='left', va='center',
                fontsize=24, fontweight='bold', color='#1E3D59')
        ax.text(kpi_x, y - 0.4, label, ha='left', va='center',
                fontsize=14, color='#555')

    ax.set_xlim(-3.0, 7.5)
    ax.set_ylim(-3.5, 3.5)
    ax.set_aspect('equal')
    ax.axis('off')

    plt.tight_layout()
    cp = _save_chart(fig, chart_dir / 'a15_1_market_reach.png')

    _slide(ctx, 'A15.1 - Market Reach', {
        'title': f'Market Reach\n{penetration:.0f}% of eligible cardholders responding',
        'layout_index': 13,
        'chart_path': cp,
        'category': 'Mailer',
    })
    _report(ctx, f"   Eligible: {n_eligible:,} | Responders: {n_responders:,} "
                 f"| Penetration: {penetration:.1f}%")
    return ctx


# =============================================================================
# A15.2 -- SPEND SHARE: ALL OPEN > ELIGIBLE > RESPONDERS
# =============================================================================

def run_spend_share(ctx):
    """Waterfall: total spend from all open, eligible, and responders."""
    _report(ctx, "\n📊 A15.2 -- Spend Share")

    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   No mailer data -- skipping A15.2")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']
    cols = list(data.columns)

    # Get subsets
    open_accounts = ctx.get('open_accounts')
    eligible_data = ctx.get('eligible_data')
    if open_accounts is None or eligible_data is None:
        _report(ctx, "   Missing open/eligible subsets -- skipping")
        return ctx

    # Find latest spend column
    spend_cols = sorted(
        [c for c in cols if SPEND_PATTERN.match(c)], key=_parse_month)
    if not spend_cols:
        _report(ctx, "   No spend columns found -- skipping")
        return ctx

    latest_spend_col = spend_cols[-1]
    latest_month = latest_spend_col.replace(' Spend', '')

    # Verify spend column exists in all subsets
    if latest_spend_col not in open_accounts.columns:
        _report(ctx, f"   {latest_spend_col} not in open accounts -- skipping")
        return ctx

    # Compute unique responders across all mail months
    resp_mask = pd.Series(False, index=data.index)
    for month, resp_col, mail_col in pairs:
        resp_mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
    responder_indices = data.index[resp_mask]

    # Filter to open accounts only for responders
    open_resp = open_accounts[open_accounts.index.isin(responder_indices)]

    # Total spend at each level
    spend_all_open = open_accounts[latest_spend_col].fillna(0).sum()
    spend_eligible = eligible_data[latest_spend_col].fillna(0).sum()
    spend_responders = open_resp[latest_spend_col].fillna(0).sum()

    n_open = len(open_accounts)
    n_eligible = len(eligible_data)
    n_resp = len(open_resp)

    if spend_all_open == 0:
        _report(ctx, "   Zero spend across open accounts -- skipping")
        return ctx

    # Proportions
    elig_pct_of_open = spend_eligible / spend_all_open * 100
    resp_pct_of_eligible = (spend_responders / spend_eligible * 100
                            if spend_eligible > 0 else 0)
    resp_pct_of_open = spend_responders / spend_all_open * 100

    # --- Draw chart: horizontal bars descending, responder bar highlighted ---
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 7),
                                   gridspec_kw={'width_ratios': [1.4, 1]})
    fig.patch.set_facecolor('white')

    labels = ['All Open Accounts', 'Eligible Accounts', 'Responders']
    values = [spend_all_open, spend_eligible, spend_responders]
    acct_counts = [n_open, n_eligible, n_resp]
    bar_colors = [COLOR_OUTER, '#1E3D59', COLOR_INNER]

    y_pos = [2, 1, 0]
    bars = ax.barh(y_pos, values, color=bar_colors, height=0.6,
                   edgecolor='none', alpha=0.85)

    # Value + count labels
    max_val = max(values)
    for bar, val, count in zip(bars, values, acct_counts):
        bar_cy = bar.get_y() + bar.get_height() / 2
        ax.text(val + max_val * 0.02, bar_cy,
                f'${val:,.0f}',
                ha='left', va='center', fontsize=15, fontweight='bold')
        # Account count inside bar
        if bar.get_width() > max_val * 0.10:
            ax.text(bar.get_width() * 0.5, bar_cy,
                    f'{count:,} accounts',
                    ha='center', va='center', fontsize=12,
                    fontweight='bold', color='white')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=16, fontweight='bold')
    ax.set_xlabel(f'Total Spend ({latest_month})', fontsize=14,
                  fontweight='bold')
    ax.set_xlim(0, max_val * 1.35)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='x', labelsize=12)
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Right panel: proportion KPIs
    ax2.axis('off')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(-0.5, 3)

    kpi_items = [
        ('Eligible Share of Open Spend', f'{elig_pct_of_open:.1f}%',
         '#1E3D59', 2.4),
        ('Responder Share of Eligible Spend', f'{resp_pct_of_eligible:.1f}%',
         COLOR_INNER, 1.4),
        ('Responder Share of All Open Spend', f'{resp_pct_of_open:.1f}%',
         COLOR_INNER, 0.4),
    ]
    for label, val, color, y in kpi_items:
        ax2.text(0.1, y + 0.15, label, ha='left', va='center',
                 fontsize=12, color='#555')
        ax2.text(0.1, y - 0.15, val, ha='left', va='center',
                 fontsize=26, fontweight='bold', color=color)

    plt.tight_layout()
    cp = _save_chart(fig, chart_dir / 'a15_2_spend_share.png')

    subtitle = (f'Responders account for {resp_pct_of_eligible:.0f}% '
                f'of eligible spend ({latest_month})')

    _slide(ctx, 'A15.2 - Spend Share', {
        'title': f'Spend Composition\n{subtitle}',
        'layout_index': 13,
        'chart_path': cp,
        'category': 'Mailer',
    })
    _report(ctx, f"   Open: ${spend_all_open:,.0f} | "
                 f"Eligible: ${spend_eligible:,.0f} ({elig_pct_of_open:.1f}%) | "
                 f"Responders: ${spend_responders:,.0f} ({resp_pct_of_eligible:.1f}% of elig)")
    return ctx


# =============================================================================
# A15.3 -- REVENUE ATTRIBUTION
# =============================================================================

def run_revenue_attribution(ctx):
    """Interchange revenue from responders vs non-responders."""
    _report(ctx, "\n📊 A15.3 -- Revenue Attribution")

    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   No mailer data -- skipping A15.3")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']
    cols = list(data.columns)
    ic_rate = ctx.get('ic_rate', 0.0)

    if ic_rate <= 0:
        _report(ctx, "   No IC rate configured -- skipping")
        return ctx

    # Find latest month with spend data
    latest_month = None
    latest_resp_col = None
    latest_mail_col = None
    latest_spend_col = None

    for month, resp_col, mail_col in reversed(pairs):
        sc = f"{month} Spend"
        if sc in cols:
            latest_month = month
            latest_resp_col = resp_col
            latest_mail_col = mail_col
            latest_spend_col = sc
            break

    if not latest_spend_col:
        _report(ctx, "   No spend data -- skipping")
        return ctx

    mailed = data[data[latest_mail_col].isin(MAILED_SEGMENTS)].copy()
    if mailed.empty:
        return ctx

    resp_mask = mailed[latest_resp_col].isin(RESPONSE_SEGMENTS)
    responders = mailed[resp_mask]
    non_responders = mailed[~resp_mask]
    n_resp = len(responders)
    n_non = len(non_responders)

    if n_resp == 0 or n_non == 0:
        _report(ctx, "   Need both groups -- skipping")
        return ctx

    # Revenue calculations
    resp_spend_total = responders[latest_spend_col].fillna(0).sum()
    non_spend_total = non_responders[latest_spend_col].fillna(0).sum()
    resp_ic = resp_spend_total * ic_rate
    non_ic = non_spend_total * ic_rate

    resp_ic_per = resp_ic / n_resp
    non_ic_per = non_ic / n_non
    incremental_per = resp_ic_per - non_ic_per
    incremental_total = incremental_per * n_resp

    # --- Draw chart ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7),
                                    gridspec_kw={'width_ratios': [1, 1.2]})
    fig.patch.set_facecolor('white')

    # Left: IC revenue per account
    labels = ['Responders', 'Non-Responders']
    values = [resp_ic_per, non_ic_per]
    colors = [COLOR_RESP, COLOR_NON]

    bars = ax1.barh([1, 0], values, color=colors, height=0.5,
                    edgecolor='none', alpha=0.9)
    for bar, val in zip(bars, values):
        bar_cy = bar.get_y() + bar.get_height() / 2
        ax1.text(val + max(values) * 0.03, bar_cy,
                 f'${val:,.2f}', ha='left', va='center',
                 fontsize=16, fontweight='bold')

    ax1.set_yticks([0, 1])
    ax1.set_yticklabels(['Non-Responders', 'Responders'],
                        fontsize=14, fontweight='bold')
    ax1.set_xlabel('IC Revenue per Account', fontsize=14, fontweight='bold')
    ax1.set_xlim(0, max(values) * 1.4)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f'${x:,.2f}'))
    ax1.set_title('Per Account', fontsize=16, fontweight='bold')

    # Right: KPI text block
    ax2.axis('off')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    lift_sign = '+' if incremental_per >= 0 else ''
    total_sign = '+' if incremental_total >= 0 else ''
    kpi_data = [
        ('Responder IC Revenue', f'${resp_ic:,.0f}', 0.85),
        ('Non-Responder IC Revenue', f'${non_ic:,.0f}', 0.65),
        ('Lift per Account', f'{lift_sign}${incremental_per:,.2f}', 0.45),
        ('Incremental Program Revenue', f'{total_sign}${incremental_total:,.0f}', 0.22),
    ]
    for label, val, y in kpi_data:
        ax2.text(0.1, y + 0.05, label, ha='left', va='center',
                 fontsize=13, color='#555')
        color = '#1E3D59' if 'Incremental' not in label else COLOR_RESP
        ax2.text(0.1, y - 0.05, val, ha='left', va='center',
                 fontsize=20, fontweight='bold', color=color)

    # Highlight box around incremental total
    rect = mpatches.FancyBboxPatch(
        (0.03, 0.10), 0.94, 0.22,
        boxstyle='round,pad=0.02',
        facecolor=COLOR_RESP, alpha=0.08, edgecolor=COLOR_RESP, linewidth=2)
    ax2.add_patch(rect)

    plt.tight_layout()
    cp = _save_chart(fig, chart_dir / 'a15_3_revenue_attribution.png')

    _slide(ctx, 'A15.3 - Revenue Attribution', {
        'title': (f'Revenue Attribution\n'
                  f'{total_sign}${incremental_total:,.0f} incremental interchange '
                  f'from {n_resp:,} responders'),
        'layout_index': 13,
        'chart_path': cp,
        'category': 'Mailer',
    })
    _report(ctx, f"   Resp IC: ${resp_ic:,.0f} | Non-resp IC: ${non_ic:,.0f} | "
                 f"Incremental: {total_sign}${incremental_total:,.0f}")
    return ctx


# =============================================================================
# A15.4 -- PRE/POST SPEND DELTA
# =============================================================================

def run_pre_post_delta(ctx):
    """Compare avg spend before vs after mailer for responders and non-responders."""
    _report(ctx, "\n📊 A15.4 -- Pre/Post Spend Delta")

    pairs = _discover_pairs(ctx)
    if not pairs:
        _report(ctx, "   No mailer data -- skipping A15.4")
        return ctx

    data = ctx['data']
    chart_dir = ctx['chart_dir']
    cols = list(data.columns)

    # Discover all spend columns sorted chronologically
    spend_cols = sorted(
        [c for c in cols if SPEND_PATTERN.match(c)], key=_parse_month)

    if len(spend_cols) < 4:
        _report(ctx, "   Need 4+ spend months for pre/post -- skipping")
        return ctx

    # Use the first mail month as the event boundary
    first_mail_month = pairs[0][0]
    first_resp_col = pairs[0][1]
    first_mail_col = pairs[0][2]
    mail_date = _parse_month(first_mail_month)

    # Split spend columns into pre and post relative to mail date
    pre_cols = [c for c in spend_cols if _parse_month(c) < mail_date]
    post_cols = [c for c in spend_cols if _parse_month(c) >= mail_date]

    if len(pre_cols) < 2 or len(post_cols) < 2:
        _report(ctx, "   Need 2+ months before and after mailer -- skipping")
        return ctx

    # Use up to 3 months before and 3 months after
    pre_cols = pre_cols[-3:]
    post_cols = post_cols[:3]

    # Identify responders and non-responders
    mailed = data[data[first_mail_col].isin(MAILED_SEGMENTS)].copy()
    if mailed.empty:
        return ctx

    resp_mask = mailed[first_resp_col].isin(RESPONSE_SEGMENTS)
    n_resp = int(resp_mask.sum())
    n_non = int((~resp_mask).sum())

    if n_resp == 0 or n_non == 0:
        _report(ctx, "   Need both groups -- skipping")
        return ctx

    # Compute average monthly spend per account
    resp_pre = mailed.loc[resp_mask, pre_cols].fillna(0).mean(axis=1).mean()
    resp_post = mailed.loc[resp_mask, post_cols].fillna(0).mean(axis=1).mean()
    non_pre = mailed.loc[~resp_mask, pre_cols].fillna(0).mean(axis=1).mean()
    non_post = mailed.loc[~resp_mask, post_cols].fillna(0).mean(axis=1).mean()

    resp_delta = resp_post - resp_pre
    non_delta = non_post - non_pre
    resp_pct = resp_delta / resp_pre * 100 if resp_pre > 0 else 0
    non_pct = non_delta / non_pre * 100 if non_pre > 0 else 0

    # --- Draw grouped bar chart ---
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor('white')

    x = np.arange(2)
    bar_w = 0.32

    pre_vals = [resp_pre, non_pre]
    post_vals = [resp_post, non_post]

    bars_pre = ax.bar(x - bar_w / 2, pre_vals, bar_w,
                      color='#BDC3C7', edgecolor='none', label='Before Mailer')
    bars_post = ax.bar(x + bar_w / 2, post_vals, bar_w,
                       color=[COLOR_RESP, COLOR_NON], edgecolor='none',
                       label='After Mailer')

    # Value labels on bars
    for bar in list(bars_pre) + list(bars_post):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + max(pre_vals + post_vals) * 0.02,
                f'${h:,.0f}', ha='center', va='bottom',
                fontsize=13, fontweight='bold')

    # Delta annotations
    deltas = [(resp_delta, resp_pct, 0), (non_delta, non_pct, 1)]
    for delta, pct, i in deltas:
        sign = '+' if delta >= 0 else ''
        color = COLOR_RESP if delta > 0 else '#E74C3C'
        ax.text(i, max(pre_vals + post_vals) * 1.15,
                f'{sign}${delta:,.0f}/acct ({sign}{pct:.0f}%)',
                ha='center', va='center', fontsize=14,
                fontweight='bold', color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(['Responders', 'Non-Responders'],
                       fontsize=18, fontweight='bold')
    ax.set_ylabel('Avg Monthly Spend per Account', fontsize=14,
                  fontweight='bold')
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, p: f'${v:,.0f}'))
    ax.set_ylim(0, max(pre_vals + post_vals) * 1.30)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', labelsize=13)
    ax.legend(fontsize=14, loc='upper right')

    # Framing text
    pre_label = f"{len(pre_cols)}-mo avg before {first_mail_month}"
    post_label = f"{len(post_cols)}-mo avg after {first_mail_month}"
    ax.text(0.5, -0.10,
            f"Before: {pre_label}  |  After: {post_label}",
            transform=ax.transAxes, ha='center', va='top',
            fontsize=12, color='#777')

    if resp_delta > 0 and non_delta <= 0:
        framing = ("Responders grew while non-responders declined "
                   "-- the program is protecting and growing revenue.")
    elif resp_delta > non_delta > 0:
        framing = ("Both groups grew, but responders outpaced "
                   f"by ${resp_delta - non_delta:,.0f}/account.")
    elif resp_delta > non_delta:
        framing = ("Responder activity held stronger than non-responders "
                   "-- the program is mitigating decline.")
    else:
        r_sign = '+' if resp_delta >= 0 else ''
        n_sign = '+' if non_delta >= 0 else ''
        framing = f"Spend delta: responders {r_sign}${resp_delta:,.0f} vs non-responders {n_sign}${non_delta:,.0f}."

    ax.text(0.5, -0.16, framing,
            transform=ax.transAxes, ha='center', va='top',
            fontsize=13, fontstyle='italic', color='#555')

    # Net Program Lift KPI
    net_lift = resp_delta - non_delta
    nl_sign = '+' if net_lift >= 0 else ''
    ax.text(0.5, -0.22,
            f"Net program lift: {nl_sign}${net_lift:,.0f}/account "
            f"(after adjusting for market trends)",
            transform=ax.transAxes, ha='center', va='top',
            fontsize=12, color='#1E3D59')

    plt.tight_layout()
    cp = _save_chart(fig, chart_dir / 'a15_4_pre_post_delta.png')

    if resp_delta > 0:
        sub = f'+${resp_delta:,.0f}/acct responder lift after {first_mail_month} mailer'
    else:
        sub = f'${resp_delta:,.0f}/acct responder change after {first_mail_month} mailer'

    _slide(ctx, 'A15.4 - Pre/Post Spend Delta', {
        'title': f'Before vs After Mailer\n{sub}',
        'layout_index': 13,
        'chart_path': cp,
        'category': 'Mailer',
    })
    _report(ctx, f"   Resp: ${resp_pre:,.0f} -> ${resp_post:,.0f} ({resp_pct:+.0f}%) | "
                 f"Non: ${non_pre:,.0f} -> ${non_post:,.0f} ({non_pct:+.0f}%)")
    return ctx


# =============================================================================
# SUITE ENTRY POINT
# =============================================================================

def run_mailer_impact_suite(ctx):
    """Run all A15 market impact analyses."""
    _report(ctx, "\n📊 A15 -- Market Impact Analysis")
    ctx = run_market_reach(ctx)
    ctx = run_spend_share(ctx)
    ctx = run_revenue_attribution(ctx)
    ctx = run_pre_post_delta(ctx)
    _report(ctx, "   A15 complete")
    return ctx
