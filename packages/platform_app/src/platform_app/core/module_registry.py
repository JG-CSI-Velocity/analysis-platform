"""Unified module registry -- exposes all analysis modules across pipelines.

Each module is described by ModuleInfo metadata. The registry is built
dynamically from existing ANALYSIS_REGISTRY lists in ics_toolkit and
txn_analysis, plus ARS pipeline modules.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class Product(StrEnum):
    ARS = "ars"
    TXN = "txn"
    TXN_V4 = "txn_v4"
    ICS = "ics"


class ModuleStatus(StrEnum):
    STABLE = "stable"
    BETA = "beta"
    DRAFT = "draft"


@dataclass(frozen=True)
class ModuleInfo:
    """Metadata for a single analysis module."""

    key: str  # unique identifier
    name: str  # display name
    product: Product
    category: str  # grouping label (e.g. "Summary", "Cohort", "Competitor")
    description: str = ""
    output_types: tuple[str, ...] = ("excel",)
    status: ModuleStatus = ModuleStatus.STABLE
    version: str = "1.0.0"
    tags: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()  # keys of modules that must run first
    run_order: int = 0  # execution order within pipeline (0 = any)


# ---------------------------------------------------------------------------
# ARS modules (declared statically -- ARS pipeline runs as monolith)
# ---------------------------------------------------------------------------
_ARS_MODULES = [
    ModuleInfo(
        "ars_attrition",
        "Attrition Analysis",
        Product.ARS,
        "Core",
        "OD/NSF attrition modeling",
        ("excel", "pptx"),
        tags=("od", "nsf", "attrition"),
        run_order=1,
    ),
    ModuleInfo(
        "ars_reg_e",
        "Reg E Impact",
        Product.ARS,
        "Regulatory",
        "Regulation E adoption and impact",
        ("excel", "pptx"),
        tags=("reg-e", "regulatory", "compliance"),
        run_order=2,
    ),
    ModuleInfo(
        "ars_value",
        "Value Segmentation",
        Product.ARS,
        "Segmentation",
        "Account value tier segmentation",
        ("excel", "pptx"),
        tags=("segmentation", "value"),
        run_order=3,
    ),
    ModuleInfo(
        "ars_mailer_impact",
        "Mailer Campaign Impact",
        Product.ARS,
        "Campaigns",
        "Direct mail campaign effectiveness",
        ("excel", "pptx"),
        tags=("mailer", "campaign"),
        run_order=4,
    ),
    ModuleInfo(
        "ars_mailer_response",
        "Mailer Response Analysis",
        Product.ARS,
        "Campaigns",
        "Response rate analysis by segment",
        ("excel", "pptx"),
        tags=("mailer", "response"),
        run_order=5,
    ),
    ModuleInfo(
        "ars_mailer_insights",
        "Mailer Insights",
        Product.ARS,
        "Campaigns",
        "Campaign insight narrative generation",
        ("excel", "pptx"),
        tags=("mailer", "insights"),
        run_order=6,
    ),
    ModuleInfo(
        "ars_dctr",
        "DCTR Analysis",
        Product.ARS,
        "Risk",
        "Delinquency & charge-off transaction reporting",
        ("excel", "pptx"),
        tags=("dctr", "delinquency", "risk"),
        run_order=7,
    ),
    ModuleInfo(
        "ars_deck",
        "Deck Builder",
        Product.ARS,
        "Output",
        "PowerPoint presentation generation",
        ("pptx",),
        tags=("output", "deck"),
        depends_on=(
            "ars_attrition",
            "ars_reg_e",
            "ars_value",
            "ars_mailer_impact",
            "ars_mailer_response",
            "ars_mailer_insights",
            "ars_dctr",
        ),
        run_order=99,
    ),
]

# ---------------------------------------------------------------------------
# ICS modules (built from ics_toolkit ANALYSIS_REGISTRY)
# ---------------------------------------------------------------------------
_ICS_CATEGORIES = {
    "Total ICS Accounts": "Summary",
    "Open ICS Accounts": "Summary",
    "ICS by Stat Code": "Summary",
    "Product Code Distribution": "Summary",
    "Debit Distribution": "Summary",
    "Debit x Prod Code": "Summary",
    "Debit x Branch": "Summary",
    "Source Distribution": "Source",
    "Source x Stat Code": "Source",
    "Source x Prod Code": "Source",
    "Source x Branch": "Source",
    "Account Type": "Source",
    "Source by Year": "Source",
    "Age Comparison": "Demographics",
    "Closures": "Demographics",
    "Open vs Close": "Demographics",
    "Balance Tiers": "Demographics",
    "Stat Open Close": "Demographics",
    "Age vs Balance": "Demographics",
    "Balance Tier Detail": "Demographics",
    "Age Distribution": "Demographics",
    "Activity Summary": "Activity",
    "Activity by Debit+Source": "Activity",
    "Activity by Balance": "Activity",
    "Activity by Branch": "Activity",
    "Monthly Trends": "Activity",
    "Cohort Activation": "Cohort",
    "Cohort Heatmap": "Cohort",
    "Cohort Milestones": "Cohort",
    "Activation Summary": "Cohort",
    "Growth Patterns": "Cohort",
    "Activation Personas": "Cohort",
    "Branch Activation": "Cohort",
    "Activation Funnel": "Strategic",
    "Revenue Impact": "Strategic",
    "Engagement Decay": "Portfolio",
    "Net Portfolio Growth": "Portfolio",
    "Spend Concentration": "Portfolio",
    "Days to First Use": "Performance",
    "Branch Performance Index": "Performance",
    "Executive Summary": "Executive",
}

# ---------------------------------------------------------------------------
# TXN modules (built from txn_analysis ANALYSIS_REGISTRY)
# ---------------------------------------------------------------------------
# TXN modules: (category, description, depends_on, run_order)
# Dependencies from analyses/__init__.py:
#   M6A (competitor_detection) MUST precede M6B-G
#   M7A (financial_services_detection) MUST precede M7B
#   M8 (interchange) + M10 (member_segments) MUST precede M9 (scorecard)
_TXN_MODULES: list[tuple[str, str, str, tuple[str, ...], int]] = [
    # M1: Overall
    ("top_merchants_by_spend", "Overall", "Top merchants by total spend", (), 1),
    ("top_merchants_by_transactions", "Overall", "Top merchants by transaction count", (), 2),
    ("top_merchants_by_accounts", "Overall", "Top merchants by unique accounts", (), 3),
    # M2: MCC
    ("mcc_by_accounts", "MCC", "MCC categories by account count", (), 4),
    ("mcc_by_transactions", "MCC", "MCC categories by transactions", (), 5),
    ("mcc_by_spend", "MCC", "MCC categories by spend volume", (), 6),
    # M3: Business
    ("business_top_by_spend", "Business", "Business spending leaders", (), 7),
    ("business_top_by_transactions", "Business", "Business transaction volume", (), 8),
    ("business_top_by_accounts", "Business", "Business account reach", (), 9),
    # M4: Personal
    ("personal_top_by_spend", "Personal", "Personal spending leaders", (), 10),
    ("personal_top_by_transactions", "Personal", "Personal transaction volume", (), 11),
    ("personal_top_by_accounts", "Personal", "Personal account reach", (), 12),
    # M5: Trends
    ("monthly_rank_tracking", "Trends", "Month-over-month rank shifts", (), 13),
    ("growth_leaders_decliners", "Trends", "Fastest growing and declining merchants", (), 14),
    ("spending_consistency", "Trends", "Merchant spending consistency", (), 15),
    ("new_vs_declining_merchants", "Trends", "New entrants vs declining merchants", (), 16),
    ("business_monthly_movers", "Trends", "Business monthly movers", (), 17),
    ("personal_monthly_movers", "Trends", "Personal monthly movers", (), 18),
    # M6: Competitor (detection populates context for metrics)
    ("competitor_detection", "Competitor", "Detect competitor transactions", (), 19),
    (
        "competitor_high_level",
        "Competitor",
        "High-level competitor metrics",
        ("txn_competitor_detection",),
        20,
    ),
    (
        "top_20_competitors",
        "Competitor",
        "Top 20 competitor merchants",
        ("txn_competitor_detection",),
        21,
    ),
    (
        "competitor_categories",
        "Competitor",
        "Competitor category breakdown",
        ("txn_competitor_detection",),
        22,
    ),
    (
        "competitor_biz_personal",
        "Competitor",
        "Business vs personal competitor split",
        ("txn_competitor_detection",),
        23,
    ),
    (
        "competitor_monthly_trends",
        "Competitor",
        "Competitor trend analysis",
        ("txn_competitor_detection",),
        24,
    ),
    (
        "competitor_threat_assessment",
        "Competitor",
        "Competitive threat scoring",
        ("txn_competitor_detection",),
        25,
    ),
    (
        "competitor_segmentation",
        "Competitor",
        "Competitor member segmentation",
        ("txn_competitor_detection",),
        26,
    ),
    # M7: Financial Services (detection before summary)
    ("financial_services_detection", "Financial", "Financial services detection", (), 27),
    (
        "financial_services_summary",
        "Financial",
        "Financial services summary",
        ("txn_financial_services_detection",),
        28,
    ),
    # M8: Interchange Revenue
    ("interchange_summary", "Revenue", "Interchange revenue breakdown", (), 29),
    # M10: Member Segmentation
    ("member_segments", "Segmentation", "Member activity segmentation", (), 30),
    # M9: Scorecard (MUST be last -- reads all prior results)
    (
        "portfolio_scorecard",
        "Scorecard",
        "Portfolio performance scorecard",
        ("txn_interchange_summary", "txn_member_segments"),
        99,
    ),
]

# V4 storylines: (category, description, depends_on, run_order)
# S3 sets ctx["s3_tagged_df"] + ctx["s3_competitor_df"] read by S3b/S3c
_V4_STORYLINES: list[tuple[str, str, str, tuple[str, ...], int]] = [
    ("s0", "Executive", "Executive Summary", (), 0),
    ("s1", "Health", "Portfolio Health", (), 1),
    ("s2", "Merchant", "Merchant Intelligence", (), 2),
    ("s3", "Competition", "Competitive Landscape", (), 3),
    ("s3b", "Competition", "Threat Intelligence", ("v4_s3",), 4),
    ("s3c", "Segmentation", "Account Segmentation", ("v4_s3",), 5),
    ("s4", "Financial", "Financial Services", (), 6),
    ("s5", "Demographics", "Demographics & Branches", (), 7),
    ("s6", "Risk", "Risk & Balance", (), 8),
    ("s7", "Campaigns", "Campaign Effectiveness", (), 9),
    ("s8", "Payroll", "Payroll & Circular Economy", (), 10),
    ("s9", "Lifecycle", "Lifecycle Management", (), 11),
]


def build_registry() -> list[ModuleInfo]:
    """Build the complete module registry from all pipeline registries."""
    modules: list[ModuleInfo] = []

    # ARS
    modules.extend(_ARS_MODULES)

    # ICS -- Executive Summary depends on all others
    ics_non_exec = [
        k
        for k in (
            f"ics_{name.lower().replace(' ', '_').replace('+', '_')}"
            for name in _ICS_CATEGORIES
            if name != "Executive Summary"
        )
    ]
    for i, (name, category) in enumerate(_ICS_CATEGORIES.items(), 1):
        key = f"ics_{name.lower().replace(' ', '_').replace('+', '_')}"
        is_exec = name == "Executive Summary"
        modules.append(
            ModuleInfo(
                key=key,
                name=name,
                product=Product.ICS,
                category=category,
                output_types=("excel", "pptx"),
                tags=(category.lower(),),
                depends_on=tuple(ics_non_exec) if is_exec else (),
                run_order=99 if is_exec else i,
            )
        )

    # TXN Base
    for key, category, desc, deps, order in _TXN_MODULES:
        modules.append(
            ModuleInfo(
                key=f"txn_{key}",
                name=key.replace("_", " ").title(),
                product=Product.TXN,
                category=category,
                description=desc,
                output_types=("excel", "png"),
                tags=(category.lower(),),
                depends_on=deps,
                run_order=order,
            )
        )

    # TXN V4
    for key, category, desc, deps, order in _V4_STORYLINES:
        modules.append(
            ModuleInfo(
                key=f"v4_{key}",
                name=f"{key.upper()}: {desc}",
                product=Product.TXN_V4,
                category=category,
                description=desc,
                output_types=("excel", "html"),
                tags=(category.lower(), "storyline"),
                depends_on=deps,
                run_order=order,
            )
        )

    return modules


def get_registry() -> list[ModuleInfo]:
    """Return cached module registry."""
    global _CACHED_REGISTRY
    if _CACHED_REGISTRY is None:
        _CACHED_REGISTRY = build_registry()
    return _CACHED_REGISTRY


def get_modules_by_product(product: Product) -> list[ModuleInfo]:
    """Filter registry by product."""
    return [m for m in get_registry() if m.product == product]


def get_categories(product: Product | None = None) -> list[str]:
    """Return sorted unique categories, optionally filtered by product."""
    modules = get_modules_by_product(product) if product else get_registry()
    return sorted({m.category for m in modules})


_CACHED_REGISTRY: list[ModuleInfo] | None = None
