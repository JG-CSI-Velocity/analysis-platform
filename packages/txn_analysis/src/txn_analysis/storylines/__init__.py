"""V4 Storyline modules for transaction analysis.

Each storyline module exposes a ``run(ctx: dict) -> dict`` function that
returns::

    {
        "title": str,
        "description": str,
        "sections": [
            {"heading": str, "narrative": str, "figures": [...], "tables": [...]},
            ...
        ],
        "sheets": [
            {"name": str, "df": pd.DataFrame, "currency_cols": [...], ...},
            ...
        ],
    }

Storyline ordering (some have cross-dependencies via ctx keys):

    S1  Portfolio Health
    S2  Merchant Intelligence
    S3  Competitive Landscape  (sets ctx["s3_tagged_df"], ctx["s3_competitor_df"])
    S3b Competitive Threats    (reads ctx["s3_tagged_df"])
    S3c Account Segmentation   (reads ctx["s3_tagged_df"], ctx["s3_competitor_df"])
    S4  Financial Services
    S5  Demographics & Branch
    S6  Risk & Balance
    S7  Campaign Effectiveness
    S8  Payroll & Circular Economy
    S9  Lifecycle Management
"""

from txn_analysis.storylines import (
    v4_s1_portfolio_health,
    v4_s2_merchant_intel,
    v4_s3_competition,
    v4_s3_segmentation,
    v4_s3_threat_analysis,
    v4_s4_finserv,
    v4_s5_demographics,
    v4_s6_risk,
    v4_s7_campaigns,
    v4_s8_payroll,
    v4_s9_lifecycle,
)

STORYLINE_REGISTRY = [
    ("s1_portfolio", v4_s1_portfolio_health),
    ("s2_merchant", v4_s2_merchant_intel),
    ("s3_competition", v4_s3_competition),
    ("s3b_threats", v4_s3_threat_analysis),
    ("s3c_segmentation", v4_s3_segmentation),
    ("s4_finserv", v4_s4_finserv),
    ("s5_demographics", v4_s5_demographics),
    ("s6_risk", v4_s6_risk),
    ("s7_campaigns", v4_s7_campaigns),
    ("s8_payroll", v4_s8_payroll),
    ("s9_lifecycle", v4_s9_lifecycle),
]
