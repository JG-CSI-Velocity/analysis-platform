"""Data-driven merchant name consolidation rules.

Replaces a 765-line if/elif chain with declarative MerchantRule tuples.
Each rule specifies required substrings, a canonical name, and optional exclusions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantRule:
    """Single merchant consolidation rule.

    required: ALL of these substrings must be present in the uppercased merchant name.
    canonical: The standardized name to return on match.
    excluded: If ANY of these are present, the rule is skipped.
    startswith: If set, merchant_upper must start with this string.
    """

    required: tuple[str, ...]
    canonical: str
    excluded: tuple[str, ...] = ()
    startswith: str | None = None


# Ordered tuple -- first match wins (mirrors original if/elif precedence).
MERCHANT_RULES: tuple[MerchantRule, ...] = (
    # ==========================================================================
    # TECH & DIGITAL SERVICES
    # ==========================================================================
    # Apple
    MerchantRule(required=("APPLE.COM",), canonical="APPLE.COM/BILL"),
    MerchantRule(required=("APPLE COM",), canonical="APPLE.COM/BILL"),
    MerchantRule(required=("APPLE CASH", "SENT MONEY"), canonical="APPLE CASH - SENT MONEY"),
    MerchantRule(
        required=("APPLE CASH",),
        canonical="APPLE CASH - TRANSFERS",
        excluded=("SENT MONEY", "BALANCE ADD"),
    ),
    MerchantRule(required=("APPLE CASH", "BALANCE ADD"), canonical="APPLE CASH - BALANCE ADD"),
    MerchantRule(required=("APPLE", "STORE"), canonical="APPLE STORE"),
    # Google
    MerchantRule(required=("GOOGLE", "PLAY"), canonical="GOOGLE PLAY"),
    MerchantRule(required=("GOOGLE", "STORAGE"), canonical="GOOGLE STORAGE"),
    MerchantRule(required=("GOOGLE", "DRIVE"), canonical="GOOGLE STORAGE"),
    MerchantRule(required=("GOOGLE", "YOUTUBE"), canonical="YOUTUBE"),
    MerchantRule(
        required=("GOOGLE",),
        canonical="GOOGLE",
        excluded=("PLAY", "STORAGE", "DRIVE", "YOUTUBE"),
    ),
    # Amazon
    MerchantRule(required=("AMAZON", "PRIME"), canonical="AMAZON PRIME"),
    MerchantRule(required=("AMAZON",), canonical="AMAZON", excluded=("PRIME",)),
    MerchantRule(required=("AMZN",), canonical="AMAZON"),
    MerchantRule(required=("PRIME VIDEO",), canonical="PRIME VIDEO"),
    # Streaming
    MerchantRule(required=("NETFLIX",), canonical="NETFLIX"),
    MerchantRule(required=("SPOTIFY",), canonical="SPOTIFY"),
    MerchantRule(required=("HULU",), canonical="HULU"),
    MerchantRule(required=("DISNEY", "PLUS"), canonical="DISNEY+"),
    MerchantRule(required=("HBO",), canonical="HBO MAX"),
    # PayPal / P2P
    MerchantRule(required=("PAYPAL", "TRANSFER"), canonical="PAYPAL TRANSFERS"),
    MerchantRule(required=("PAYPAL", "INST XFER"), canonical="PAYPAL TRANSFERS"),
    MerchantRule(required=("PAYPAL",), canonical="PAYPAL", excluded=("TRANSFER", "INST XFER")),
    MerchantRule(required=("VENMO",), canonical="VENMO"),
    MerchantRule(required=("ZELLE",), canonical="ZELLE"),
    MerchantRule(required=("CASH APP",), canonical="CASH APP"),
    MerchantRule(required=("CASHAPP",), canonical="CASH APP"),
    # ==========================================================================
    # RETAIL - BIG BOX
    # ==========================================================================
    MerchantRule(required=("WALMART.COM",), canonical="WALMART.COM"),
    MerchantRule(required=("WALMART COM",), canonical="WALMART.COM"),
    MerchantRule(
        required=("WALMART",),
        canonical="WALMART (ALL LOCATIONS)",
        excluded=("WALMART.COM", "WALMART COM"),
    ),
    MerchantRule(required=("WAL-MART",), canonical="WALMART (ALL LOCATIONS)"),
    MerchantRule(required=("WM SUPERCENTER",), canonical="WALMART (ALL LOCATIONS)"),
    MerchantRule(required=("TARGET", "T-"), canonical="TARGET (ALL LOCATIONS)"),
    MerchantRule(required=("TARGET", "STORE"), canonical="TARGET (ALL LOCATIONS)"),
    MerchantRule(required=("COSTCO",), canonical="COSTCO"),
    MerchantRule(required=("SAMS CLUB",), canonical="SAMS CLUB"),
    MerchantRule(required=("SAM'S CLUB",), canonical="SAMS CLUB"),
    MerchantRule(required=("BJ'S",), canonical="BJ'S WHOLESALE"),
    MerchantRule(required=("BJS",), canonical="BJ'S WHOLESALE"),
    # ==========================================================================
    # RETAIL - DOLLAR STORES
    # ==========================================================================
    MerchantRule(required=("DOLLAR TREE",), canonical="DOLLAR TREE"),
    MerchantRule(required=("DOLLARTREE",), canonical="DOLLAR TREE"),
    MerchantRule(required=("DOLLAR GENERAL",), canonical="DOLLAR GENERAL"),
    MerchantRule(required=("DOLLARGENERAL",), canonical="DOLLAR GENERAL"),
    MerchantRule(required=("FAMILY DOLLAR",), canonical="FAMILY DOLLAR"),
    MerchantRule(required=("FIVE BELOW",), canonical="FIVE BELOW"),
    MerchantRule(required=("5 BELOW",), canonical="FIVE BELOW"),
    # ==========================================================================
    # RETAIL - DEPARTMENT STORES
    # ==========================================================================
    MerchantRule(required=("BURLINGTON",), canonical="BURLINGTON"),
    MerchantRule(required=("KOHLS",), canonical="KOHL'S"),
    MerchantRule(required=("KOHL'S",), canonical="KOHL'S"),
    MerchantRule(required=("MARSHALLS",), canonical="MARSHALLS"),
    MerchantRule(required=("TJ MAXX",), canonical="TJ MAXX"),
    MerchantRule(required=("TJMAXX",), canonical="TJ MAXX"),
    MerchantRule(required=("ROSS", "DRESS"), canonical="ROSS DRESS FOR LESS"),
    MerchantRule(required=("NORDSTROM",), canonical="NORDSTROM"),
    MerchantRule(required=("MACY'S",), canonical="MACY'S"),
    MerchantRule(required=("MACYS",), canonical="MACY'S"),
    # ==========================================================================
    # RETAIL - SPECIALTY
    # ==========================================================================
    MerchantRule(required=("HOBBY LOBBY",), canonical="HOBBY LOBBY"),
    MerchantRule(required=("HOBBYLOBBY",), canonical="HOBBY LOBBY"),
    MerchantRule(required=("MICHAELS", "STORES"), canonical="MICHAELS"),
    MerchantRule(required=("HOME DEPOT",), canonical="HOME DEPOT"),
    MerchantRule(required=("HOMEDEPOT",), canonical="HOME DEPOT"),
    MerchantRule(required=("LOWE'S",), canonical="LOWE'S"),
    MerchantRule(required=("LOWES",), canonical="LOWE'S"),
    MerchantRule(required=("MENARDS",), canonical="MENARDS"),
    MerchantRule(required=("ACE HDWE",), canonical="ACE HARDWARE"),
    MerchantRule(required=("ACE HARDWARE",), canonical="ACE HARDWARE"),
    MerchantRule(required=("TRUE VALUE",), canonical="TRUE VALUE"),
    MerchantRule(required=("TRUEVALUE",), canonical="TRUE VALUE"),
    MerchantRule(required=("BED BATH",), canonical="BED BATH & BEYOND"),
    MerchantRule(required=("BEST BUY",), canonical="BEST BUY"),
    MerchantRule(required=("BESTBUY",), canonical="BEST BUY"),
    MerchantRule(required=("DICKS SPORTING",), canonical="DICKS SPORTING GOODS"),
    MerchantRule(required=("DICK'S SPORTING",), canonical="DICKS SPORTING GOODS"),
    MerchantRule(required=("PETCO",), canonical="PETCO"),
    MerchantRule(required=("PETSMART",), canonical="PETSMART"),
    # ==========================================================================
    # ONLINE RETAIL
    # ==========================================================================
    MerchantRule(required=("TIKTOK", "SHOP"), canonical="TIKTOK SHOP"),
    MerchantRule(required=("SHEIN",), canonical="SHEIN"),
    MerchantRule(required=("TEMU",), canonical="TEMU"),
    MerchantRule(required=("ETSY",), canonical="ETSY"),
    MerchantRule(required=("EBAY",), canonical="EBAY"),
    MerchantRule(required=("AFTERPAY",), canonical="AFTERPAY"),
    MerchantRule(required=("KLARNA",), canonical="KLARNA"),
    MerchantRule(required=("AFFIRM",), canonical="AFFIRM"),
    # ==========================================================================
    # GROCERS
    # ==========================================================================
    MerchantRule(required=("JEWEL", "OSCO"), canonical="JEWEL-OSCO (ALL LOCATIONS)"),
    MerchantRule(required=("WOODMANS",), canonical="WOODMANS FOOD MARKET (ALL LOCATIONS)"),
    MerchantRule(required=("WOODMAN",), canonical="WOODMANS FOOD MARKET (ALL LOCATIONS)"),
    MerchantRule(required=("MEIJER",), canonical="MEIJER (ALL LOCATIONS)"),
    MerchantRule(required=("HY-VEE",), canonical="HY-VEE"),
    MerchantRule(required=("HYVEE",), canonical="HY-VEE"),
    MerchantRule(required=("SCHNUCKS",), canonical="SCHNUCKS"),
    MerchantRule(required=("STOP & SHOP",), canonical="STOP & SHOP"),
    MerchantRule(required=("STOP AND SHOP",), canonical="STOP & SHOP"),
    MerchantRule(required=("MARKET BASKET",), canonical="MARKET BASKET"),
    MerchantRule(required=("SHAWS",), canonical="SHAW'S"),
    MerchantRule(required=("SHAW'S",), canonical="SHAW'S"),
    MerchantRule(required=("HANNAFORD",), canonical="HANNAFORD"),
    MerchantRule(required=("WEGMANS",), canonical="WEGMANS"),
    MerchantRule(required=("GIANT FOOD",), canonical="GIANT"),
    MerchantRule(required=("GIANT EAGLE",), canonical="GIANT"),
    MerchantRule(required=("PUBLIX",), canonical="PUBLIX"),
    MerchantRule(required=("KROGER",), canonical="KROGER"),
    MerchantRule(required=("HARRIS TEETER",), canonical="HARRIS TEETER"),
    MerchantRule(required=("FOOD LION",), canonical="FOOD LION"),
    MerchantRule(required=("ALBERTSONS",), canonical="ALBERTSONS"),
    MerchantRule(required=("SAFEWAY",), canonical="SAFEWAY"),
    MerchantRule(required=("VONS",), canonical="VONS"),
    MerchantRule(required=("RALPHS",), canonical="RALPHS"),
    MerchantRule(required=("FRED MEYER",), canonical="FRED MEYER"),
    MerchantRule(required=("WHOLE FOODS",), canonical="WHOLE FOODS"),
    MerchantRule(required=("TRADER JOE",), canonical="TRADER JOE'S"),
    MerchantRule(required=("ALDI",), canonical="ALDI"),
    MerchantRule(required=("LIDL",), canonical="LIDL"),
    MerchantRule(required=("FRESH MARKET",), canonical="FRESH MARKET"),
    # ==========================================================================
    # GAS STATIONS / CONVENIENCE
    # ==========================================================================
    MerchantRule(required=("SPEEDWAY",), canonical="SPEEDWAY"),
    MerchantRule(required=("SHELL", "OIL"), canonical="SHELL"),
    MerchantRule(required=("SHELL", "SERVICE"), canonical="SHELL"),
    MerchantRule(required=("SHELL",), canonical="SHELL", startswith="SHELL "),
    MerchantRule(required=("MARATHON",), canonical="MARATHON"),
    # TMOBILE must come before MOBIL to avoid false match ("TMOBILE" contains "MOBIL")
    MerchantRule(required=("TMOBILE",), canonical="T-MOBILE"),
    MerchantRule(required=("T-MOBILE",), canonical="T-MOBILE"),
    MerchantRule(required=("T MOBILE",), canonical="T-MOBILE"),
    MerchantRule(required=("MOBIL",), canonical="EXXON/MOBIL"),
    MerchantRule(required=("EXXON",), canonical="EXXON/MOBIL"),
    MerchantRule(required=("CHEVRON",), canonical="CHEVRON"),
    MerchantRule(required=("CITGO",), canonical="CITGO"),
    MerchantRule(required=("SUNOCO",), canonical="SUNOCO"),
    MerchantRule(required=("VALERO",), canonical="VALERO"),
    MerchantRule(required=("CIRCLE K",), canonical="CIRCLE K"),
    MerchantRule(required=("CIRCLEK",), canonical="CIRCLE K"),
    MerchantRule(required=("7-ELEVEN",), canonical="7-ELEVEN"),
    MerchantRule(required=("7ELEVEN",), canonical="7-ELEVEN"),
    MerchantRule(required=("7 ELEVEN",), canonical="7-ELEVEN"),
    MerchantRule(required=("WAWA",), canonical="WAWA"),
    MerchantRule(required=("SHEETZ",), canonical="SHEETZ"),
    MerchantRule(required=("QUICKTRIP",), canonical="QUICKTRIP"),
    MerchantRule(required=("QT",), canonical="QUICKTRIP"),
    MerchantRule(required=("CUMBERLAND",), canonical="CUMBERLAND FARMS"),
    MerchantRule(required=("SMARTREWARDS",), canonical="CUMBERLAND FARMS"),
    MerchantRule(required=("PILOT", "FLYING"), canonical="PILOT FLYING J"),
    MerchantRule(required=("PILOT", "TRAVEL"), canonical="PILOT FLYING J"),
    MerchantRule(required=("LOVE'S",), canonical="LOVE'S TRAVEL STOPS"),
    MerchantRule(required=("LOVES",), canonical="LOVE'S TRAVEL STOPS"),
    # ==========================================================================
    # DELIVERY SERVICES (before restaurants so DOORDASH*MCDONALDS -> DOORDASH)
    # ==========================================================================
    MerchantRule(required=("DOORDASH",), canonical="DOORDASH"),
    MerchantRule(required=("UBER", "EATS"), canonical="UBER EATS"),
    MerchantRule(required=("GRUBHUB",), canonical="GRUBHUB"),
    MerchantRule(required=("INSTACART",), canonical="INSTACART"),
    # ==========================================================================
    # RESTAURANTS - FAST FOOD
    # ==========================================================================
    MerchantRule(required=("MCDONALDS",), canonical="MCDONALD'S"),
    MerchantRule(required=("MCDONALD'S",), canonical="MCDONALD'S"),
    MerchantRule(required=("BURGER KING",), canonical="BURGER KING"),
    MerchantRule(required=("WENDY'S",), canonical="WENDY'S"),
    MerchantRule(required=("WENDYS",), canonical="WENDY'S"),
    MerchantRule(required=("TACO BELL",), canonical="TACO BELL"),
    MerchantRule(required=("CHIPOTLE",), canonical="CHIPOTLE"),
    MerchantRule(required=("SUBWAY",), canonical="SUBWAY"),
    MerchantRule(required=("CHICK-FIL-A",), canonical="CHICK-FIL-A"),
    MerchantRule(required=("CHICKFILA",), canonical="CHICK-FIL-A"),
    MerchantRule(required=("POPEYES",), canonical="POPEYES"),
    MerchantRule(required=("KFC",), canonical="KFC"),
    MerchantRule(required=("PANERA",), canonical="PANERA BREAD"),
    MerchantRule(required=("JIMMY JOHN",), canonical="JIMMY JOHN'S"),
    MerchantRule(required=("ARBY",), canonical="ARBY'S"),
    MerchantRule(required=("SONIC", "DRIVE"), canonical="SONIC DRIVE-IN"),
    MerchantRule(required=("FIVE GUYS",), canonical="FIVE GUYS"),
    MerchantRule(required=("CULVERS",), canonical="CULVER'S"),
    MerchantRule(required=("CULVER'S",), canonical="CULVER'S"),
    MerchantRule(required=("PORTILLOS",), canonical="PORTILLO'S"),
    MerchantRule(required=("PORTILLO'S",), canonical="PORTILLO'S"),
    # ==========================================================================
    # RESTAURANTS - CASUAL / DELIVERY
    # ==========================================================================
    MerchantRule(required=("STARBUCKS",), canonical="STARBUCKS"),
    MerchantRule(required=("DUNKIN",), canonical="DUNKIN"),
    MerchantRule(required=("TROPICAL SMOOTHIE",), canonical="TROPICAL SMOOTHIE CAFE"),
    MerchantRule(required=("SMOOTHIE KING",), canonical="SMOOTHIE KING"),
    MerchantRule(required=("JAMBA",), canonical="JAMBA JUICE"),
    # DOORDASH, UBER EATS, GRUBHUB, INSTACART moved to delivery section above
    MerchantRule(required=("UBER",), canonical="UBER", excluded=("EATS",)),
    # ==========================================================================
    # UTILITIES
    # ==========================================================================
    MerchantRule(required=("COMED",), canonical="COMED"),
    MerchantRule(required=("COM ED",), canonical="COMED"),
    MerchantRule(required=("DUKE ENERGY",), canonical="DUKE ENERGY"),
    MerchantRule(required=("DOMINION", "ENERGY"), canonical="DOMINION ENERGY"),
    MerchantRule(required=("NATIONAL GRID",), canonical="NATIONAL GRID"),
    MerchantRule(required=("EVERSOURCE",), canonical="EVERSOURCE"),
    MerchantRule(required=("AMEREN",), canonical="AMEREN"),
    MerchantRule(required=("NICOR",), canonical="NICOR GAS"),
    MerchantRule(required=("PEOPLES GAS",), canonical="PEOPLES GAS"),
    MerchantRule(required=("NATIONAL FUEL",), canonical="NATIONAL FUEL"),
    MerchantRule(required=("WATER", "DEPT"), canonical="WATER UTILITY"),
    MerchantRule(required=("WATER", "DEPARTMENT"), canonical="WATER UTILITY"),
    MerchantRule(required=("NARRAGANSETT",), canonical="NARRAGANSETT BAY (UTILITIES)"),
    # ==========================================================================
    # TELECOM
    # ==========================================================================
    MerchantRule(required=("COMCAST",), canonical="COMCAST/XFINITY"),
    MerchantRule(required=("XFINITY",), canonical="COMCAST/XFINITY"),
    MerchantRule(required=("SPECTRUM",), canonical="SPECTRUM"),
    MerchantRule(required=("COX", "CABLE"), canonical="COX COMMUNICATIONS"),
    MerchantRule(required=("COX", "COMM"), canonical="COX COMMUNICATIONS"),
    MerchantRule(required=("VERIZON FIOS",), canonical="VERIZON FIOS"),
    MerchantRule(required=("ATT*",), canonical="AT&T"),
    MerchantRule(required=("AT&T",), canonical="AT&T"),
    MerchantRule(required=("AT T",), canonical="AT&T"),
    # TMOBILE rules already placed before MOBIL in gas stations section
    MerchantRule(required=("VERIZON", "WIRELESS"), canonical="VERIZON WIRELESS"),
    MerchantRule(required=("SPRINT",), canonical="SPRINT"),
    MerchantRule(required=("CRICKET", "WIRELESS"), canonical="CRICKET WIRELESS"),
    MerchantRule(required=("BOOST MOBILE",), canonical="BOOST MOBILE"),
    MerchantRule(required=("METRO", "PCS"), canonical="METRO BY T-MOBILE"),
    MerchantRule(required=("METRO", "MOBILE"), canonical="METRO BY T-MOBILE"),
    # ==========================================================================
    # INSURANCE
    # ==========================================================================
    MerchantRule(required=("STATE FARM",), canonical="STATE FARM"),
    MerchantRule(required=("GEICO",), canonical="GEICO"),
    MerchantRule(required=("PROGRESSIVE",), canonical="PROGRESSIVE"),
    MerchantRule(required=("ALLSTATE",), canonical="ALLSTATE"),
    MerchantRule(required=("FARMERS", "INSURANCE"), canonical="FARMERS INSURANCE"),
    MerchantRule(required=("LIBERTY MUTUAL",), canonical="LIBERTY MUTUAL"),
    MerchantRule(required=("NATIONWIDE",), canonical="NATIONWIDE"),
    MerchantRule(required=("USAA",), canonical="USAA"),
    MerchantRule(required=("AMERICAN FAMILY",), canonical="AMERICAN FAMILY INSURANCE"),
    # ==========================================================================
    # TOLLS
    # ==========================================================================
    MerchantRule(required=("E-ZPASS",), canonical="E-ZPASS"),
    MerchantRule(required=("EZPASS",), canonical="E-ZPASS"),
    MerchantRule(required=("EZ PASS",), canonical="E-ZPASS"),
    MerchantRule(required=("IL TOLLWAY",), canonical="ILLINOIS TOLLWAY"),
    MerchantRule(required=("ILLINOIS TOLLWAY",), canonical="ILLINOIS TOLLWAY"),
    MerchantRule(required=("I-PASS",), canonical="ILLINOIS TOLLWAY"),
    MerchantRule(required=("SUNPASS",), canonical="SUNPASS"),
    MerchantRule(required=("FASTRAK",), canonical="FASTRAK"),
    MerchantRule(required=("TOLL", "ROAD"), canonical="TOLL AUTHORITY"),
    MerchantRule(required=("TOLL", "AUTHORITY"), canonical="TOLL AUTHORITY"),
    # ==========================================================================
    # FINANCIAL SERVICES
    # ==========================================================================
    MerchantRule(required=("DAVE", "INC"), canonical="DAVE"),
    MerchantRule(required=("DAVE", "APP"), canonical="DAVE"),
    MerchantRule(required=("CHIME",), canonical="CHIME"),
    MerchantRule(required=("VARO",), canonical="VARO"),
    MerchantRule(required=("CURRENT", "CARD"), canonical="CURRENT"),
    MerchantRule(required=("FLEX FINANCE",), canonical="FLEX FINANCE"),
    MerchantRule(required=("FLEXFINANCE",), canonical="FLEX FINANCE"),
    MerchantRule(required=("EARNIN",), canonical="EARNIN"),
    MerchantRule(required=("BRIGIT",), canonical="BRIGIT"),
    MerchantRule(required=("POSSIBLE FINANCE",), canonical="POSSIBLE FINANCE"),
    MerchantRule(required=("CHASE", "BANK"), canonical="CHASE"),
    MerchantRule(required=("CHASE", "CARD"), canonical="CHASE"),
    MerchantRule(required=("CHASE", "PAYMENT"), canonical="CHASE"),
    MerchantRule(required=("BANK OF AMERICA",), canonical="BANK OF AMERICA"),
    MerchantRule(required=("BOFA",), canonical="BANK OF AMERICA"),
    MerchantRule(required=("WELLS FARGO",), canonical="WELLS FARGO"),
    MerchantRule(required=("CITIBANK",), canonical="CITIBANK"),
    MerchantRule(required=("CITI CARD",), canonical="CITIBANK"),
    MerchantRule(required=("US BANK",), canonical="US BANK"),
    MerchantRule(required=("U.S. BANK",), canonical="US BANK"),
    MerchantRule(required=("PNC BANK",), canonical="PNC"),
    MerchantRule(required=("TD BANK",), canonical="TD BANK"),
    MerchantRule(required=("CAPITAL ONE",), canonical="CAPITAL ONE"),
    MerchantRule(required=("DISCOVER", "CARD"), canonical="DISCOVER"),
    MerchantRule(required=("DISCOVER", "PAYMENT"), canonical="DISCOVER"),
    MerchantRule(required=("AMEX",), canonical="AMERICAN EXPRESS"),
    MerchantRule(required=("AMERICAN EXPRESS",), canonical="AMERICAN EXPRESS"),
    MerchantRule(required=("SYNCHRONY",), canonical="SYNCHRONY"),
    MerchantRule(required=("ONEMAIN",), canonical="ONEMAIN FINANCIAL"),
    MerchantRule(required=("ONE MAIN",), canonical="ONEMAIN FINANCIAL"),
    MerchantRule(required=("LENDING CLUB",), canonical="LENDING CLUB"),
    MerchantRule(required=("SOFI",), canonical="SOFI"),
    MerchantRule(required=("UPSTART",), canonical="UPSTART"),
    MerchantRule(required=("ROCKET", "MORTGAGE"), canonical="ROCKET MORTGAGE"),
    MerchantRule(required=("ROCKET", "LOANS"), canonical="ROCKET MORTGAGE"),
    MerchantRule(required=("DEPT EDUCATION",), canonical="DEPT OF EDUCATION (STUDENT LOANS)"),
    MerchantRule(
        required=("DEPARTMENT OF EDUCATION",), canonical="DEPT OF EDUCATION (STUDENT LOANS)"
    ),
    MerchantRule(required=("ED FINANCIAL",), canonical="DEPT OF EDUCATION (STUDENT LOANS)"),
    MerchantRule(required=("NAVIENT",), canonical="NAVIENT"),
    MerchantRule(required=("NELNET",), canonical="NELNET"),
    MerchantRule(required=("GREAT LAKES", "LOAN"), canonical="GREAT LAKES (STUDENT LOANS)"),
    MerchantRule(required=("MOHELA",), canonical="MOHELA"),
    # ==========================================================================
    # GAMING / BETTING
    # ==========================================================================
    MerchantRule(required=("FANDUEL",), canonical="FANDUEL"),
    MerchantRule(required=("DRAFTKINGS",), canonical="DRAFTKINGS"),
    MerchantRule(required=("BETMGM",), canonical="BETMGM"),
    MerchantRule(required=("CAESARS", "SPORTSBOOK"), canonical="CAESARS SPORTSBOOK"),
    MerchantRule(required=("CAESARS", "CASINO"), canonical="CAESARS SPORTSBOOK"),
    MerchantRule(required=("POINTSBET",), canonical="POINTSBET"),
    MerchantRule(required=("BETRIVERS",), canonical="BETRIVERS"),
    MerchantRule(required=("BARSTOOL", "SPORTSBOOK"), canonical="BARSTOOL SPORTSBOOK"),
    MerchantRule(required=("BETFAIR",), canonical="BETFAIR"),
    MerchantRule(required=("ILLINOIS STATE LOTTERY",), canonical="ILLINOIS STATE LOTTERY"),
    MerchantRule(required=("IL LOTTERY",), canonical="ILLINOIS STATE LOTTERY"),
    # ==========================================================================
    # GOVERNMENT / MUNICIPAL
    # ==========================================================================
    MerchantRule(
        required=("TOWN OF",),
        canonical="MUNICIPAL PAYMENTS (TOWNS)",
        startswith="TOWN OF",
    ),
    MerchantRule(
        required=("CITY OF",),
        canonical="MUNICIPAL PAYMENTS (CITIES)",
        startswith="CITY OF",
    ),
    MerchantRule(required=("COMMONWEALTH", "SEC OF MA"), canonical="COMMONWEALTH OF MA"),
    MerchantRule(required=("IRS", "TAX"), canonical="IRS (TAX PAYMENTS)"),
    MerchantRule(required=("IRS", "PAYMENT"), canonical="IRS (TAX PAYMENTS)"),
    MerchantRule(required=("DMV",), canonical="DMV"),
    MerchantRule(required=("MOTOR VEHICLE", "DEPT"), canonical="DMV"),
    # ==========================================================================
    # HEALTHCARE
    # ==========================================================================
    MerchantRule(required=("BLUE CROSS",), canonical="BLUE CROSS BLUE SHIELD"),
    MerchantRule(required=("BCBS",), canonical="BLUE CROSS BLUE SHIELD"),
    MerchantRule(required=("UNITED HEALTHCARE",), canonical="UNITED HEALTHCARE"),
    MerchantRule(required=("UNITEDHEALTHCARE",), canonical="UNITED HEALTHCARE"),
    MerchantRule(required=("AETNA",), canonical="AETNA"),
    MerchantRule(required=("CIGNA",), canonical="CIGNA"),
    MerchantRule(required=("HUMANA",), canonical="HUMANA"),
    MerchantRule(required=("KAISER",), canonical="KAISER PERMANENTE"),
    MerchantRule(required=("CVS", "PHARMACY"), canonical="CVS PHARMACY"),
    MerchantRule(required=("WALGREENS",), canonical="WALGREENS"),
    MerchantRule(required=("RITE AID",), canonical="RITE AID"),
)


def standardize_merchant_name(merchant_name: str) -> str:
    """Return the canonical merchant name, or the original if no rule matches."""
    merchant_upper = str(merchant_name).upper()
    for rule in MERCHANT_RULES:
        if rule.startswith and not merchant_upper.startswith(rule.startswith):
            continue
        if all(p in merchant_upper for p in rule.required):
            if rule.excluded and any(ex in merchant_upper for ex in rule.excluded):
                continue
            return rule.canonical
    return merchant_name
