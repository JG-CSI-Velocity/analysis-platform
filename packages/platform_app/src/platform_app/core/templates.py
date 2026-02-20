"""Saved analysis templates -- reusable module combinations.

Templates are stored in a YAML file and editable via the UI.
Each template maps a name to a list of module keys.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES_FILE = Path("config/analysis_templates.yaml")

# Built-in templates (always available, not editable)
BUILTIN_TEMPLATES: dict[str, list[str]] = {
    "ARS Full Suite": [
        "ars_attrition",
        "ars_reg_e",
        "ars_value",
        "ars_mailer_impact",
        "ars_mailer_response",
        "ars_mailer_insights",
        "ars_dctr",
        "ars_deck",
    ],
    "ARS Monthly Standard": [
        "ars_attrition",
        "ars_reg_e",
        "ars_value",
        "ars_deck",
    ],
    "ICS Full Suite": [
        f"ics_{name.lower().replace(' ', '_').replace('+', '_')}"
        for name in [
            "Total ICS Accounts",
            "Open ICS Accounts",
            "ICS by Stat Code",
            "Activity Summary",
            "Cohort Activation",
            "Revenue Impact",
            "Executive Summary",
        ]
    ],
    "TXN Competitive Intelligence": [
        "txn_competitor_detection",
        "txn_competitor_high_level",
        "txn_top_20_competitors",
        "txn_competitor_threat_assessment",
        "txn_competitor_segmentation",
    ],
    "TXN Portfolio Overview": [
        "txn_top_merchants_by_spend",
        "txn_top_merchants_by_transactions",
        "txn_member_segments",
        "txn_portfolio_scorecard",
    ],
    "TXN Full Suite": [
        "txn_top_merchants_by_spend",
        "txn_top_merchants_by_transactions",
        "txn_top_merchants_by_accounts",
        "txn_mcc_by_accounts",
        "txn_mcc_by_transactions",
        "txn_mcc_by_spend",
        "txn_business_top_by_spend",
        "txn_business_top_by_transactions",
        "txn_business_top_by_accounts",
        "txn_personal_top_by_spend",
        "txn_personal_top_by_transactions",
        "txn_personal_top_by_accounts",
        "txn_monthly_rank_tracking",
        "txn_growth_leaders_decliners",
        "txn_spending_consistency",
        "txn_new_vs_declining_merchants",
        "txn_business_monthly_movers",
        "txn_personal_monthly_movers",
        "txn_competitor_detection",
        "txn_competitor_high_level",
        "txn_top_20_competitors",
        "txn_competitor_categories",
        "txn_competitor_biz_personal",
        "txn_competitor_monthly_trends",
        "txn_competitor_threat_assessment",
        "txn_competitor_segmentation",
        "txn_financial_services_detection",
        "txn_financial_services_summary",
        "txn_interchange_summary",
        "txn_member_segments",
        "txn_demographics",
        "txn_campaigns",
        "txn_payroll",
        "txn_lifecycle",
        "txn_portfolio_scorecard",
    ],
}


def load_templates(path: Path = DEFAULT_TEMPLATES_FILE) -> dict[str, list[str]]:
    """Load saved templates. Returns builtins merged with user templates."""
    templates = dict(BUILTIN_TEMPLATES)

    if path.exists():
        try:
            with open(path) as f:
                user_templates = yaml.safe_load(f) or {}
            if isinstance(user_templates, dict):
                templates.update(user_templates)
                logger.info("Loaded %d user templates from %s", len(user_templates), path)
        except Exception as e:
            logger.warning("Failed to load user templates: %s", e)

    return templates


def save_template(
    name: str,
    module_keys: list[str],
    path: Path = DEFAULT_TEMPLATES_FILE,
) -> None:
    """Save or update a user template."""
    existing = {}
    if path.exists():
        try:
            with open(path) as f:
                existing = yaml.safe_load(f) or {}
        except Exception:
            existing = {}

    existing[name] = module_keys

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)

    logger.info("Saved template %r (%d modules) to %s", name, len(module_keys), path)


def delete_template(name: str, path: Path = DEFAULT_TEMPLATES_FILE) -> bool:
    """Delete a user template. Returns True if deleted."""
    if name in BUILTIN_TEMPLATES:
        return False  # can't delete builtins

    if not path.exists():
        return False

    try:
        with open(path) as f:
            existing = yaml.safe_load(f) or {}
    except Exception:
        return False

    if name not in existing:
        return False

    del existing[name]
    with open(path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)
    return True
