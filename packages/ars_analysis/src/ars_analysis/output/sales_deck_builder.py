"""RPE Sales Conference Deck Builder.

Generates a 13-slide keynote-style presentation for credit union conferences.
Introduces the Retail Performance Engine (RPE) lifecycle platform with
synthetic illustrative data. No client data is used.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from ars_analysis.output.deck_builder import (
    LAYOUT_CUSTOM,
    LAYOUT_TITLE,
    LAYOUT_TITLE_RPE,
    DeckBuilder,
    SlideContent,
)
from ars_analysis.output.sales_charts import (
    competition_chart,
    financial_services_chart,
    ics_source_chart,
    lifecycle_diagram,
    lifecycle_kpi_dashboard,
    mrpc_fallback_chart,
    service_adoption_chart,
    swipe_ladder_chart,
)


@dataclass(frozen=True)
class SalesDeckConfig:
    """Configuration for a sales conference deck."""

    conference_name: str = "2026 Credit Union Conference"
    conference_date: str = ""
    booth_number: str = ""
    contact_info: str = ""
    tagline: str = "The Complete Debit Card Lifecycle Platform"
    mrpc_chart_path: Path | None = None
    output_path: Path = field(default_factory=lambda: Path("RPE_Sales_Deck.pptx"))


# ---------------------------------------------------------------------------
# Speaker notes for each slide
# ---------------------------------------------------------------------------

_NOTES = {
    1: (
        "Welcome everyone. Today we're introducing the Retail Performance Engine -- "
        "a complete platform that gives credit unions intelligence and results at every "
        "stage of the debit card member lifecycle. Four products, one platform."
    ),
    2: (
        "Let's start with a question. Your members go through 4 stages with their debit "
        "card -- from getting the card, to using early services, to swiping regularly, "
        "to premium engagement. How many of those stages can you actually see and measure?"
    ),
    3: (
        "Here's what's at stake. These are industry benchmarks showing the cost of blind "
        "spots at each lifecycle stage. Whether it's dormant new accounts, low service "
        "adoption, competitor card leakage, or missed premium revenue -- every gap costs "
        "your credit union real dollars."
    ),
    4: (
        "RPE solves this with four connected products. ICS handles acquisition intelligence. "
        "Account Engagement tracks service adoption in the critical first 90 days. ARS "
        "manages ongoing card usage and campaign intelligence. And MRPC delivers premium "
        "engagement with recurring fee revenue. Each product hands off to the next."
    ),
    5: (
        "ICS -- Instant Card Solutions -- tracks where your new debit card accounts are "
        "coming from. Branch referrals, direct mail, digital channels. You see which "
        "sources actually produce active cardholders, not just accounts on paper."
    ),
    6: (
        "Account Engagement monitors the critical first 90 days. Members who adopt 3 or "
        "more services early -- eStatements, online banking, direct deposit -- are far "
        "more likely to stay long-term. This product flags who's engaging and who's drifting."
    ),
    7: (
        "ARS puts every member on a swipe ladder. From non-users through threshold 25. "
        "We track exactly where they are and which direction they're moving. Targeted mailer "
        "campaigns move members UP to the next tier. Early detection catches members moving "
        "DOWN before they go dormant."
    ),
    8: (
        "Here's something unique. We analyze 38 competitive patterns across 6 categories. "
        "Big national banks, regional banks, other credit unions, digital neobanks, "
        "wallets and P2P, and buy-now-pay-later. Local AND national. You see exactly "
        "which competitors are capturing your members' spend, in which categories."
    ),
    9: (
        "Debit card transactions reveal more than spending habits -- they reveal your "
        "members' entire financial lives. When a member makes payments to an auto lender, "
        "a mortgage company, or a brokerage, RPE captures it. That's cross-sell intelligence "
        "you can't get anywhere else."
    ),
    10: (
        "MRPC is our premium debit card product. It's a card with bundled services and a "
        "monthly fee that generates significantly more revenue per account. The data speaks "
        "for itself -- MRPC cardholders generate more recurring fee income plus higher "
        "card usage."
    ),
    11: (
        "Here's the complete picture. Every lifecycle stage is now measurable and actionable. "
        "ICS tells you where accounts come from. Engagement shows who's adopting services. "
        "ARS tracks spending and campaign ROI. MRPC delivers premium revenue. One platform, "
        "complete visibility."
    ),
    12: (
        "We're not just talking about potential. Over 300 credit unions already use RPE to "
        "manage their debit card lifecycle. They're seeing real results at every stage."
    ),
    13: (
        "We'd love to show you what RPE can do for your credit union. Stop by our booth "
        "or scan the QR code to schedule a demo. Thank you."
    ),
}


def build_sales_deck(config: SalesDeckConfig) -> Path:
    """Generate the complete RPE sales conference deck.

    Args:
        config: Conference and output configuration.

    Returns:
        Path to the saved PPTX file.
    """
    # Template ships with the package
    template = Path(__file__).parent / "template" / "2025-CSI-PPT-Template.pptx"
    if not template.exists():
        raise FileNotFoundError(f"Template not found: {template}")

    # Generate synthetic charts in a temp directory
    tmp = Path(tempfile.mkdtemp(prefix="rpe_sales_"))
    try:
        charts = _generate_charts(tmp, config)
        slides = _build_slide_definitions(config, charts)
        builder = DeckBuilder(str(template))
        output = str(config.output_path)
        builder.build(slides, output)
        logger.info("Sales deck saved to {path}", path=output)
        return config.output_path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _generate_charts(tmp: Path, config: SalesDeckConfig) -> dict[str, str]:
    """Generate all synthetic chart PNGs and return path mapping."""
    charts: dict[str, str] = {}

    charts["lifecycle"] = str(lifecycle_diagram(tmp))
    charts["ics_source"] = str(ics_source_chart(tmp))
    charts["service_adoption"] = str(service_adoption_chart(tmp))
    charts["swipe_ladder"] = str(swipe_ladder_chart(tmp))
    charts["competition"] = str(competition_chart(tmp))
    charts["financial_services"] = str(financial_services_chart(tmp))
    charts["lifecycle_kpi"] = str(lifecycle_kpi_dashboard(tmp))

    # MRPC: use user-provided chart if available, otherwise generate fallback
    if config.mrpc_chart_path and config.mrpc_chart_path.exists():
        charts["mrpc"] = str(config.mrpc_chart_path)
    else:
        charts["mrpc"] = str(mrpc_fallback_chart(tmp))

    return charts


def _build_slide_definitions(
    config: SalesDeckConfig,
    charts: dict[str, str],
) -> list[SlideContent]:
    """Build the 13 SlideContent objects for the sales deck."""
    conf_subtitle = config.conference_name
    if config.conference_date:
        conf_subtitle += f" | {config.conference_date}"

    slides: list[SlideContent] = []

    # --- Slide 1: Title ---
    slides.append(
        SlideContent(
            slide_type="title",
            title=f"Retail Performance Engine\n{config.tagline}",
            layout_index=LAYOUT_TITLE_RPE,
            notes_text=_NOTES[1],
        )
    )

    # --- Slide 2: The Lifecycle Gap ---
    slides.append(
        SlideContent(
            slide_type="title",
            title=(
                "Your members' debit card journey has 4 stages.\n"
                "How many can you see?"
            ),
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[2],
        )
    )

    # --- Slide 3: What's at Stake (KPI Hero) ---
    slides.append(
        SlideContent(
            slide_type="kpi_hero",
            title="What's at Stake -- The Cost of Lifecycle Blind Spots",
            kpis={
                "New accounts that never activate": "40%",
                "Higher attrition with 1 service vs 3+": "2.5x",
                "Everyday spend going to competitors": "35%",
                "More revenue per premium account": "$12+",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[3],
        )
    )

    # --- Slide 4: Introducing RPE (Lifecycle Diagram) ---
    slides.append(
        SlideContent(
            slide_type="chart_narrative",
            title="One Platform. Four Products. Complete Lifecycle Intelligence.",
            images=[charts["lifecycle"]],
            bullets=[
                "ICS -- Know where new accounts come from and which sources perform best",
                "Account Engagement -- Track service adoption in the critical first 90 days",
                "ARS -- Move members up the swipe ladder and prove mailer ROI",
                "MRPC -- Premium debit with bundled services and recurring fee revenue",
            ],
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[4],
        )
    )

    # --- Slide 5: ICS ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "Know where your new debit card accounts are coming from\n"
                "-- and which sources perform best"
            ),
            images=[charts["ics_source"]],
            kpis={
                "Acquisition source tracking": "Referral, direct mail, branch, digital",
                "New account activation rates": "By source and channel",
                "Branch and staff performance": "Referral conversion tracking",
                "Cost per activated account": "Acquisition efficiency by channel",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[5],
        )
    )

    # --- Slide 6: Account Engagement ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "The deeper the relationship starts, the longer it lasts\n"
                "More services used early and often"
            ),
            images=[charts["service_adoption"]],
            kpis={
                "Service adoption tracking": "eStatements, online banking, direct deposit, bill pay, mobile",
                "Adoption velocity": "How quickly new members engage with multiple services",
                "Cross-sell identification": "Opportunities flagged in the first 90 days",
                "Retention correlation": "Early adoption predicts long-term membership",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[6],
        )
    )

    # --- Slide 7: ARS -- Swipe Ladder ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "Move members up the swipe ladder\n"
                "-- and catch the ones sliding down before it's too late"
            ),
            images=[charts["swipe_ladder"]],
            kpis={
                "Every member on the ladder": "ARS tracks exactly where they are and which direction they're moving",
                "Targeted mailer campaigns": "Move members UP to the next tier",
                "Early detection": "Catch members moving DOWN -- intervene before dormancy",
                "First-time vs repeat tracking": "Response intelligence across campaigns",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[7],
        )
    )

    # --- Slide 8: Competitive Intelligence ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "We analyze 38 competitive patterns across 6 categories\n"
                "-- local and national"
            ),
            images=[charts["competition"]],
            kpis={
                "38 competitive patterns": "Analyzed for every client",
                "Local AND national": "From community banks to Chase and Chime",
                "Spend share by category": "Know exactly where you're losing wallet share",
                "6 competitor types": "Big banks, regional, CUs, neobanks, wallets, BNPL",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[8],
        )
    )

    # --- Slide 9: Financial Services Intelligence ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "See where your members go for financial services\n"
                "-- and where you're missing the relationship"
            ),
            images=[charts["financial_services"]],
            kpis={
                "8 financial service categories": "Auto loans, banks, business loans, student loans, credit cards, mortgage/HELOC, treasury, investments",
                "Services outside your CU": "Identifies cross-sell opportunities you can't see otherwise",
                "Opportunity sizing": "Dollar-weighted by service bucket",
                "Competitive positioning": "Lending, investing, and deposit products",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[9],
        )
    )

    # --- Slide 10: MRPC ---
    slides.append(
        SlideContent(
            slide_type="screenshot_kpi",
            title=(
                "A premium debit card with bundled services\n"
                "-- and the revenue to prove it"
            ),
            images=[charts["mrpc"]],
            kpis={
                "Revenue per account": "MRPC vs standard cardholder comparison",
                "Monthly fee + card usage": "Recurring fee income plus higher interchange",
                "Bundled service adoption": "Premium cardholders use more services",
                "Program growth": "Expanding premium membership base",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[10],
        )
    )

    # --- Slide 11: Complete Picture (KPI Dashboard) ---
    slides.append(
        SlideContent(
            slide_type="kpi_dashboard",
            title="Complete Visibility. Every Stage. Every Metric. One Platform.",
            kpis={
                "ICS\nNew Accounts": "847/mo|green",
                "Engagement\nActivated 30d": "72%|yellow",
                "ARS\nPenetration": "34.2%|green",
                "MRPC\nRevenue/Acct": "$18.40|green",
            },
            layout_index=LAYOUT_CUSTOM,
            notes_text=_NOTES[11],
        )
    )

    # --- Slide 12: Social Proof ---
    slides.append(
        SlideContent(
            slide_type="title",
            title=(
                "300+ Credit Unions Trust RPE\n"
                "to Manage Their Debit Card Lifecycle"
            ),
            layout_index=LAYOUT_TITLE,
            notes_text=_NOTES[12],
        )
    )

    # --- Slide 13: CTA ---
    cta_lines = ["Ready to See Your Complete Debit Card Lifecycle?"]
    if config.booth_number:
        cta_lines.append(f"Visit us at Booth #{config.booth_number}")
    if config.contact_info:
        cta_lines.append(config.contact_info)
    slides.append(
        SlideContent(
            slide_type="title",
            title="\n".join(cta_lines),
            layout_index=LAYOUT_TITLE_RPE,
            notes_text=_NOTES[13],
        )
    )

    return slides
