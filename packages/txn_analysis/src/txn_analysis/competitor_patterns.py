"""Competitor merchant patterns for M6 competitor analysis.

Three-tier precision matching: exact > starts_with > contains.
Seven categories of financial competitors plus false-positive exclusions.
"""

from __future__ import annotations

from typing import NamedTuple

MATCH_TIERS = ("exact", "starts_with", "contains")


class MatchResult(NamedTuple):
    """Result of classify_merchant()."""

    category: str | None
    tier: str | None
    pattern: str | None


COMPETITOR_MERCHANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "big_nationals": {
        "exact": ("CHASE", "BOA", "KEYBANK", "SANTANDER", "CITI", "CITIZENS"),
        "starts_with": (
            "BANK OF AMERICA",
            "BANKOFAMERICA",
            "B OF A",
            "BK OF AMERICA",
            "BK OF AMER",
            "WELLS FARGO",
            "WELLSFARGO",
            "WF BANK",
            "WF HOME",
            "CHASE BANK",
            "CHASE BK",
            "CHASE CREDIT",
            "CHASE CARD",
            "CHASE HOME",
            "CHASE AUTO",
            "CHASE MTG",
            "JPMORGAN",
            "JP MORGAN",
            "CITIBANK",
            "CITI BANK",
            "CITI CARD",
            "CITICORP",
            "CITI MORTGAGE",
            "CITIMORTGAGE",
            "TD BANK",
            "TD BK",
            "TDBANK",
            "TD BANKNORTH",
            "CITIZENS BANK",
            "CITIZENS BK",
            "CITIZENS FINANCIAL",
            "SANTANDER BANK",
            "M&T BANK",
            "M&T BK",
            "M AND T BANK",
            "M AND T BK",
            "M & T BANK",
            "MANUFACTURERS AND TRADERS",
            "KEYBANK",
            "KEY BANK",
            "KEY BK",
            "PNC BANK",
            "PNC BK",
            "US BANK",
            "U.S. BANK",
            "US BK",
            "CAPITAL ONE",
            "CAPITAL ONE BK",
            "CAPITAL ONE BANK",
            "CAPITAL ONE 360",
            "CAP ONE BANK",
            "CAPITALONE BK",
        ),
        "contains": (),
    },
    "regionals": {
        "exact": ("BANKWELL",),
        "starts_with": (
            "WEBSTER BANK",
            "WEBSTER BK",
            "WEBSTERBANK",
            "LIBERTY BANK",
            "LIBERTY BK",
            "ION BANK",
            "ION BK",
            "UNION SAVINGS",
            "UNION SVG",
            "NEWTOWN SAVINGS",
            "NEWTOWN SVG",
            "BEACON BANK",
            "FAIRFIELD COUNTY BANK",
            "FAIRFIELD COUNTY BK",
            "FIRST COUNTY BANK",
            "FIRST COUNTY BK",
            "IVES BANK",
            "IVES BK",
            "THOMASTON SAVINGS",
            "THOMASTON SVG",
            "NORTHWEST COMMUNITY",
            "NW COMMUNITY BANK",
            "CHELSEA GROTON",
            "ASCEND BANK",
            "ASCEND BK",
            "WINDSOR FEDERAL",
            "GUILFORD SAVINGS",
            "GUILFORD SVG",
            "GSB BANK",
            "ESSEX SAVINGS",
            "ESSEX SVG",
            "MILFORD BANK",
            "THE MILFORD BANK",
            "BANKWELL",
            "PATRIOT BANK",
            "PATRIOT BK",
            "CENTREVILLE BANK",
            "BANK OF NEW HAVEN",
            "CONNECTICUT COMMUNITY",
            "CT COMMUNITY BANK",
            "PEOPLES BANK",
            "PEOPLESBANK",
            "PEOPLES BK",
            "SAVINGS BANK OF DANBURY",
            "BERKSHIRE BANK",
            "BERKSHIRE BK",
            "NBT BANK",
            "NBT BK",
            "DIME BANK",
            "SI FINANCIAL",
            "WASHINGTON TRUST",
            "SAVINGS BANK OF WALPOLE",
            "PEOPLES UNITED",
            "FIRST NATIONAL BANK CT",
            "PATRIOT NATIONAL",
            # Midwest regionals (from original patterns)
            "BMO",
            "BMO HARRIS",
            "FIFTH THIRD",
            "5/3 BANK",
            "HUNTINGTON",
            "OLD NATIONAL",
            "FIRST MIDWEST",
            "WINTRUST",
            "TOWN BANK",
            "NORTH SHORE BANK",
            "LAKE FOREST BANK",
            "BYLINE BANK",
            "FIRST AMERICAN BANK",
            "ASSOCIATED BANK",
            "CIBC BANK",
            "MARQUETTE BANK",
            "REPUBLIC BANK",
            "FIRST MERCHANTS",
            "PROVIDENCE BANK",
        ),
        "contains": (),
    },
    "credit_unions": {
        "exact": (),
        "starts_with": (
            # CT credit unions
            "NEW HAVEN COUNTY CREDIT",
            "NEW HAVEN COUNTY CU",
            "NHCCU",
            "CROSSPOINT FEDERAL",
            "CROSSPOINT FCU",
            "CROSSPOINT CU",
            "AFFINITY FEDERAL CU",
            "AFFINITY FCU",
            "AFFINITY CU",
            "USALLIANCE FINANCIAL",
            "USALLIANCE FED",
            "USALLIANCE",
            "GE CREDIT UNION",
            "GE CU",
            "SCIENT FEDERAL",
            "SCIENT FCU",
            "SCIENT CU",
            "SCIENCE PARK FCU",
            "SCIENCE PARK FED",
            "MUTUAL SECURITY CU",
            "MUTUAL SECURITY CREDIT",
            "CT STATE EMPLOYEES CU",
            "CONNECTICUT STATE EMPLOYEES",
            "ACHIEVE FINANCIAL CU",
            "ACHIEVE FINANCIAL CREDIT",
            "NUTMEG STATE FINANCIAL",
            "NUTMEG STATE CU",
            "NUTMEG CU",
            "NUTMEG STATE FCU",
            "FINEX CREDIT UNION",
            "FINEX CU",
            "FINEX FCU",
            "WESTERN CT FCU",
            "WESTERN CONNECTICUT FCU",
            "ISLAND FEDERAL CU",
            "ISLAND FEDERAL CREDIT",
            "AMERICAN EAGLE FCU",
            "CHARTER OAK FCU",
            "SIKORSKY FCU",
            "TEACHERS FCU",
            "YALE FEDERAL",
            # National CUs
            "NAVY FEDERAL",
            "NAVY FED",
            "NFCU",
            "GOLDEN 1 CREDIT",
            "GOLDEN 1 CU",
            "PENTAGON FEDERAL",
            "PENTAGON FCU",
            "PENFED",
            "STATE EMPLOYEES CU",
            "USAA",
            "ALLIANT CREDIT",
            "ALLIANT CU",
            "DIGITAL FCU",
            # From original patterns
            "CONSUMERS CREDIT UNION",
            "BAXTER CREDIT UNION",
            "BCU",
            "CREDIT UNION 1",
            "CU1",
            "CORPORATE AMERICA FAMILY",
            "CAFCU",
            "FIRST NORTHERN CREDIT UNION",
            "ABRI CREDIT UNION",
            "NUMARK CREDIT UNION",
            "EARTHMOVER CREDIT UNION",
            "CHICAGO PATROLMEN",
            "NORTHSTAR CREDIT UNION",
            "UNITED CREDIT UNION",
            "SELFRELIANCE",
            "CHICAGO MUNICIPAL EMPLOYEES",
        ),
        "contains": (),
    },
    "digital_banks": {
        "exact": ("CHIME", "REVOLUT", "BETTERMENT", "WEALTHFRONT", "SOFI", "ROBINHOOD", "MARCUS"),
        "starts_with": (
            "ALLY BANK",
            "ALLY BK",
            "ALLY FINANCIAL",
            "DISCOVER BANK",
            "DISCOVER BK",
            "DISCOVER SAVINGS",
            "SOFI BANK",
            "SOFI MONEY",
            "SOFI LENDING",
            "SOFI CREDIT",
            "SOFI INVEST",
            "CHIME BANK",
            "CHIME FINANCIAL",
            "VARO BANK",
            "VARO MONEY",
            "GO2BANK",
            "GREEN DOT BANK",
            "GREEN DOT BK",
            "GREENDOT",
            "THE BANCORP",
            "BANCORP BANK",
            "STRIDE BANK",
            "CURRENT CARD",
            "CURRENT MOBILE",
            "MARCUS BY GS",
            "MARCUS BY GOLDMAN",
            "MARCUS GOLDMAN",
            "MARCUS SAVINGS",
            "GOLDMAN SACHS BANK",
            "SCHWAB BANK",
            "CHARLES SCHWAB BK",
            "SCHWAB BK",
            "CHARLES SCHWAB",
            "FIDELITY CASH",
            "FIDELITY BROKERAGE",
            "ROBINHOOD CASH",
            "ROBINHOOD MONEY",
            "CAPITAL ONE 360",
            "REVOLUT",
            "N26 BANK",
            "N26",
            "DAVE INC",
            "DAVE APP",
            "EARNIN",
            "BRIGIT",
            "POSSIBLE FINANCE",
        ),
        "contains": (
            "CHIME",
            "VARO",
            "GREEN DOT",
            "SYNCHRONY",
        ),
    },
    "wallets_p2p": {
        "exact": ("PAYPAL", "VENMO"),
        "starts_with": (
            "PAYPAL",
            "VENMO",
            "CASH APP",
            "CASHAPP",
            "APPLE CASH",
            "APPLE CARD",
            "APPLE PAY CASH",
            "GOOGLE PAY",
            "GOOGLEPAY",
            "ZELLE",
            "SQ *",
        ),
        "contains": (
            "PAYPAL",
            "VENMO",
            "CASH APP",
            "CASHAPP",
            "APPLE CASH",
            "GOOGLE PAY",
            "ZELLE",
        ),
    },
    "bnpl": {
        "exact": ("KLARNA", "AFTERPAY", "SEZZLE"),
        "starts_with": (
            "KLARNA",
            "AFTERPAY",
            "AFFIRM",
            "AFFIRM INC",
            "SEZZLE",
            "QUADPAY",
            "ZIP PAY",
            "ZIPPAY",
            "ZIP CO",
            "ZIP.CO",
        ),
        "contains": (
            "AFTERPAY",
            "KLARNA",
            "AFFIRM",
            "SEZZLE",
            "QUADPAY",
        ),
    },
    "alt_finance": {
        "exact": (),
        "starts_with": (
            "FLEX FINANCE",
            "FLEXFINANCE",
            "MONEYLION",
            "ALBERT SAVINGS",
            "EMPOWER FINANCE",
        ),
        "contains": (),
    },
}


FALSE_POSITIVES: tuple[str, ...] = (
    "TOWING",
    "TOW SERVICE",
    "BODY SHOP",
    "AUTO REPAIR",
    "AUTO PARTS",
    "AUTOZONE",
    "AUTO TRADER",
    "TRADER JOE",
    "CHASE OUTDOORS",
    "CURRENT ELECTRIC",
)


FINANCIAL_MCC_CODES: tuple[str, ...] = (
    "6010",
    "6011",
    "6012",
    "6050",
    "6051",
    "6211",
    "6300",
    "6399",
    "6513",
)


# Pre-built exact-match lookup sets (computed once at import)
_EXACT_LOOKUP: dict[str, frozenset[str]] = {
    category: frozenset(tiers.get("exact", ())) for category, tiers in COMPETITOR_MERCHANTS.items()
}

# All exact patterns merged for fast O(1) first-pass lookup
_ALL_EXACT: dict[str, str] = {}
for _cat, _tiers in COMPETITOR_MERCHANTS.items():
    for _pat in _tiers.get("exact", ()):
        if _pat not in _ALL_EXACT:
            _ALL_EXACT[_pat] = _cat


def classify_merchant(merchant_name: str) -> MatchResult:
    """Classify a merchant name via 3-tier matching.

    Priority: exact > starts_with > contains. Returns on first match.
    Expects upper-cased input. Does NOT apply false-positive filtering.
    """
    name = merchant_name.strip()

    # Tier 1: exact (O(1) dict lookup)
    cat = _ALL_EXACT.get(name)
    if cat is not None:
        return MatchResult(cat, "exact", name)

    # Tier 2: starts_with
    for category, tiers in COMPETITOR_MERCHANTS.items():
        for prefix in tiers.get("starts_with", ()):
            if name.startswith(prefix):
                return MatchResult(category, "starts_with", prefix)

    # Tier 3: contains
    for category, tiers in COMPETITOR_MERCHANTS.items():
        for substr in tiers.get("contains", ()):
            if substr in name:
                return MatchResult(category, "contains", substr)

    return MatchResult(None, None, None)


def is_false_positive(merchant_name: str) -> bool:
    """Check if a merchant name matches any false-positive pattern."""
    name = merchant_name.strip()
    return any(fp in name for fp in FALSE_POSITIVES)


# Backward-compat: flattened tuple of all patterns across all tiers
ALL_COMPETITOR_PATTERNS: tuple[str, ...] = tuple(
    p
    for tiers in COMPETITOR_MERCHANTS.values()
    for tier_patterns in tiers.values()
    for p in tier_patterns
)
