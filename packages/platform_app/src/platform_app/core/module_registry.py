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
    ),
    ModuleInfo(
        "ars_reg_e",
        "Reg E Impact",
        Product.ARS,
        "Regulatory",
        "Regulation E adoption and impact",
        ("excel", "pptx"),
        tags=("reg-e", "regulatory", "compliance"),
    ),
    ModuleInfo(
        "ars_value",
        "Value Segmentation",
        Product.ARS,
        "Segmentation",
        "Account value tier segmentation",
        ("excel", "pptx"),
        tags=("segmentation", "value"),
    ),
    ModuleInfo(
        "ars_mailer_impact",
        "Mailer Campaign Impact",
        Product.ARS,
        "Campaigns",
        "Direct mail campaign effectiveness",
        ("excel", "pptx"),
        tags=("mailer", "campaign"),
    ),
    ModuleInfo(
        "ars_mailer_response",
        "Mailer Response Analysis",
        Product.ARS,
        "Campaigns",
        "Response rate analysis by segment",
        ("excel", "pptx"),
        tags=("mailer", "response"),
    ),
    ModuleInfo(
        "ars_mailer_insights",
        "Mailer Insights",
        Product.ARS,
        "Campaigns",
        "Campaign insight narrative generation",
        ("excel", "pptx"),
        tags=("mailer", "insights"),
    ),
    ModuleInfo(
        "ars_dctr",
        "DCTR Analysis",
        Product.ARS,
        "Risk",
        "Delinquency & charge-off transaction reporting",
        ("excel", "pptx"),
        tags=("dctr", "delinquency", "risk"),
    ),
    ModuleInfo(
        "ars_deck",
        "Deck Builder",
        Product.ARS,
        "Output",
        "PowerPoint presentation generation",
        ("pptx",),
        tags=("output", "deck"),
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
_TXN_CATEGORIES = {
    "top_merchants_by_spend": ("Overall", "Top merchants by total spend"),
    "top_merchants_by_transactions": ("Overall", "Top merchants by transaction count"),
    "top_merchants_by_accounts": ("Overall", "Top merchants by unique accounts"),
    "mcc_by_accounts": ("MCC", "MCC categories by account count"),
    "mcc_by_transactions": ("MCC", "MCC categories by transactions"),
    "mcc_by_spend": ("MCC", "MCC categories by spend volume"),
    "business_top_by_spend": ("Business", "Business spending leaders"),
    "business_top_by_transactions": ("Business", "Business transaction volume"),
    "business_top_by_accounts": ("Business", "Business account reach"),
    "personal_top_by_spend": ("Personal", "Personal spending leaders"),
    "personal_top_by_transactions": ("Personal", "Personal transaction volume"),
    "personal_top_by_accounts": ("Personal", "Personal account reach"),
    "monthly_rank_tracking": ("Trends", "Month-over-month rank shifts"),
    "growth_leaders_decliners": ("Trends", "Fastest growing and declining merchants"),
    "spending_consistency": ("Trends", "Merchant spending consistency"),
    "new_vs_declining_merchants": ("Trends", "New entrants vs declining merchants"),
    "business_monthly_movers": ("Trends", "Business monthly movers"),
    "personal_monthly_movers": ("Trends", "Personal monthly movers"),
    "competitor_detection": ("Competitor", "Detect competitor transactions"),
    "competitor_high_level": ("Competitor", "High-level competitor metrics"),
    "top_20_competitors": ("Competitor", "Top 20 competitor merchants"),
    "competitor_categories": ("Competitor", "Competitor category breakdown"),
    "competitor_biz_personal": ("Competitor", "Business vs personal competitor split"),
    "competitor_monthly_trends": ("Competitor", "Competitor trend analysis"),
    "competitor_threat_assessment": ("Competitor", "Competitive threat scoring"),
    "competitor_segmentation": ("Competitor", "Competitor member segmentation"),
    "financial_services_detection": ("Financial", "Financial services detection"),
    "financial_services_summary": ("Financial", "Financial services summary"),
    "interchange_summary": ("Revenue", "Interchange revenue breakdown"),
    "member_segments": ("Segmentation", "Member activity segmentation"),
    "portfolio_scorecard": ("Scorecard", "Portfolio performance scorecard"),
}

# V4 storylines
_V4_STORYLINES = {
    "s0": ("Executive", "Executive Summary"),
    "s1": ("Health", "Portfolio Health"),
    "s2": ("Merchant", "Merchant Intelligence"),
    "s3": ("Competition", "Competitive Landscape"),
    "s3b": ("Competition", "Threat Intelligence"),
    "s3c": ("Segmentation", "Account Segmentation"),
    "s4": ("Financial", "Financial Services"),
    "s5": ("Demographics", "Demographics & Branches"),
    "s6": ("Risk", "Risk & Balance"),
    "s7": ("Campaigns", "Campaign Effectiveness"),
    "s8": ("Payroll", "Payroll & Circular Economy"),
    "s9": ("Lifecycle", "Lifecycle Management"),
}


def build_registry() -> list[ModuleInfo]:
    """Build the complete module registry from all pipeline registries."""
    modules: list[ModuleInfo] = []

    # ARS
    modules.extend(_ARS_MODULES)

    # ICS
    for name, category in _ICS_CATEGORIES.items():
        key = f"ics_{name.lower().replace(' ', '_').replace('+', '_')}"
        modules.append(
            ModuleInfo(
                key=key,
                name=name,
                product=Product.ICS,
                category=category,
                output_types=("excel", "pptx"),
                tags=(category.lower(),),
            )
        )

    # TXN Base
    for key, (category, desc) in _TXN_CATEGORIES.items():
        modules.append(
            ModuleInfo(
                key=f"txn_{key}",
                name=key.replace("_", " ").title(),
                product=Product.TXN,
                category=category,
                description=desc,
                output_types=("excel", "png"),
                tags=(category.lower(),),
            )
        )

    # TXN V4
    for key, (category, desc) in _V4_STORYLINES.items():
        modules.append(
            ModuleInfo(
                key=f"v4_{key}",
                name=f"{key.upper()}: {desc}",
                product=Product.TXN_V4,
                category=category,
                description=desc,
                output_types=("excel", "html"),
                tags=(category.lower(), "storyline"),
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
