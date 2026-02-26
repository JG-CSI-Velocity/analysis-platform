"""Generate slide_catalog.xlsx -- one tab per pipeline with every analysis/slide."""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)

COLUMNS = [
    "Section",
    "Module",
    "Slide / Analysis ID",
    "Title",
    "Chart Type",
    "Layout Index",
    "Slide Type",
    "Data Source",
    "Notes",
]

ARS_DATA = [
    # Overview
    ["Overview", "stat_codes", "A1", "Stat Code Distribution", "Bar", 9, "screenshot", "ODD", "Full-width bar; many categories"],
    ["Overview", "product_codes", "A1b", "Product Code Distribution", "Bar", 5, "chart_narrative", "ODD", "Chart + product mix commentary"],
    ["Overview", "eligibility", "A3", "Eligibility Analysis", "Scatter", 5, "chart_narrative", "ODD", "Scatter + eligibility criteria explanation"],
    # DCTR - Penetration
    ["DCTR", "penetration", "DCTR-1", "Historical Debit Card Take Rate", "Line", 5, "chart_narrative", "ODD", "Trend line + rate narrative; stored in ctx.results"],
    ["DCTR", "penetration", "DCTR-2", "DCTR: Open vs Eligible", "Grouped Bar", 6, "comparison", "ODD", "Side-by-side comparison of two populations"],
    ["DCTR", "penetration", "DCTR-3", "DCTR Snapshot: Open to TTM", "Grouped Bar", 4, "chart_kpi", "ODD", "Chart + KPI callouts for current vs TTM"],
    ["DCTR", "penetration", "DCTR-4", "Personal DCTR", "Line", 6, "comparison", "ODD", "Pair with DCTR-5 (Personal vs Business side-by-side)"],
    ["DCTR", "penetration", "DCTR-5", "Business DCTR", "Line", 6, "comparison", "ODD", "Pair with DCTR-4 (Personal vs Business side-by-side)"],
    ["DCTR", "penetration", "DCTR-6", "Personal L12M DCTR", "Line", 6, "comparison", "ODD", "Pair with DCTR-7 (L12M Personal vs Business)"],
    ["DCTR", "penetration", "DCTR-7", "Business L12M DCTR", "Line", 6, "comparison", "ODD", "Pair with DCTR-6 (L12M Personal vs Business)"],
    ["DCTR", "penetration", "DCTR-8", "Comprehensive DCTR Summary", "Grouped Bar", 9, "screenshot", "ODD", "Full-width; dense multi-group data"],
    # DCTR - Trends
    ["DCTR", "trends", "A7.4", "DCTR Recent Trend", "Line", 5, "chart_narrative", "ODD", "Trend line + narrative on trajectory; reads penetration results"],
    ["DCTR", "trends", "A7.5", "DCTR Segment Analysis", "Grouped Bar", 9, "screenshot", "ODD", "Full-width; many segments x groups"],
    ["DCTR", "trends", "A7.6a", "DCTR Trajectory + Segments", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair (trajectory left, segments right)"],
    ["DCTR", "trends", "A7.6b", "DCTR Segment Breakdown", "Bar", 5, "chart_narrative", "ODD", "Chart + segment insight callout"],
    ["DCTR", "trends", "A7.14", "DCTR Cohort Analysis", "Line", 5, "chart_narrative", "ODD", "Cohort curves + cohort explanation text"],
    ["DCTR", "trends", "A7.15", "DCTR Cohort Detail", "Grouped Bar", 9, "screenshot", "ODD", "Full-width detail breakdown"],
    # DCTR - Branches
    ["DCTR", "branches", "DCTR-9", "Branch DCTR Comparison", "Heatmap", 9, "screenshot", "ODD", "Full-width heatmap; many branches x periods"],
    ["DCTR", "branches", "A7.10a", "Branch Performance Matrix", "Heatmap", 13, "wide_custom", "ODD", "Wide layout; dense branch matrix"],
    ["DCTR", "branches", "A7.10b", "Branch Detail View", "Bar", 5, "chart_narrative", "ODD", "Bar + branch performance commentary"],
    ["DCTR", "branches", "A7.10c", "Branch KPI Summary", "KPI Panel", 7, "kpi_grid", "ODD", "6-cell KPI grid for branch metrics"],
    ["DCTR", "branches", "DCTR-15", "Branch Rank", "Bar", 6, "comparison", "ODD", "Pair with DCTR-16 (rank left, change right)"],
    ["DCTR", "branches", "DCTR-16", "Branch Change", "Lollipop", 6, "comparison", "ODD", "Pair with DCTR-15 (rank left, change right)"],
    ["DCTR", "branches", "A7.13", "Branch Appendix Detail", "Heatmap", 9, "screenshot", "ODD", "Appendix; full-width reference heatmap"],
    # DCTR - Funnel
    ["DCTR", "funnel", "A7.7", "DCTR Funnel: Historical vs TTM", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair (historical left, TTM right)"],
    ["DCTR", "funnel", "A7.8", "Account Eligibility Funnel", "Funnel", 5, "chart_narrative", "ODD", "Funnel chart + stage-by-stage explanation"],
    ["DCTR", "funnel", "A7.9", "Funnel Detail Breakdown", "Bar", 9, "screenshot", "ODD", "Full-width detail bar"],
    # DCTR - Overlays
    ["DCTR", "overlays", "DCTR-10", "Age Distribution Overlay", "Histogram", 5, "chart_narrative", "ODD", "Histogram + age distribution insights"],
    ["DCTR", "overlays", "DCTR-11", "Product Code Breakdown", "Donut", 5, "chart_narrative", "ODD", "Donut + product mix narrative"],
    ["DCTR", "overlays", "DCTR-12", "Personal vs Business", "Grouped Bar", 6, "comparison", "ODD", "Natural comparison; split layout"],
    ["DCTR", "overlays", "DCTR-13", "Balance Tier Analysis", "Grouped Bar", 5, "chart_narrative", "ODD", "Chart + tier threshold explanation"],
    ["DCTR", "overlays", "DCTR-14", "Account Age Impact", "Scatter", 5, "chart_narrative", "ODD", "Scatter + correlation narrative"],
    # Reg E - Status
    ["Reg E", "status", "A8.1", "Reg E Overall Rate", "Line", 5, "chart_narrative", "ODD", "Trend line + rate trajectory narrative"],
    ["Reg E", "status", "A8.2", "Reg E: Open vs Eligible", "Grouped Bar", 6, "comparison", "ODD", "Side-by-side comparison"],
    ["Reg E", "status", "A8.3", "Reg E Snapshot", "Grouped Bar", 4, "chart_kpi", "ODD", "Chart + 2 KPI callout zones"],
    ["Reg E", "status", "A8.12", "Reg E Summary KPI", "KPI", 7, "kpi_grid", "ODD", "6-cell KPI grid for Reg E metrics"],
    # Reg E - Dimensions
    ["Reg E", "dimensions", "A8.5", "Reg E Opportunity: Age", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair (opportunity left, detail right)"],
    ["Reg E", "dimensions", "A8.6", "Reg E by Age Detail", "Bar", 5, "chart_narrative", "ODD", "Chart + age-band commentary"],
    ["Reg E", "dimensions", "A8.7", "Reg E by Tenure", "Heatmap", 9, "screenshot", "ODD", "Full-width heatmap; many tenure bands"],
    ["Reg E", "dimensions", "A8.10", "Reg E Funnel", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["Reg E", "dimensions", "A8.11", "Reg E Funnel Detail", "Funnel", 5, "chart_narrative", "ODD", "Funnel + stage explanation"],
    # Reg E - Branches
    ["Reg E", "branches", "A8.4a", "Branch Reg E Matrix", "Heatmap", 13, "wide_custom", "ODD", "Wide layout; dense branch matrix"],
    ["Reg E", "branches", "A8.4b", "Branch Reg E Detail", "Bar", 5, "chart_narrative", "ODD", "Bar + branch commentary"],
    ["Reg E", "branches", "A8.4c", "Branch Appendix", "Heatmap", 9, "screenshot", "ODD", "Appendix; full-width reference"],
    ["Reg E", "branches", "A8.13", "Reg E Branch Rank", "Bar", 9, "screenshot", "ODD", "Full-width rank bar; many branches"],
    # Attrition - Rates
    ["Attrition", "rates", "A9.1", "Overall Attrition Rate", "KPI + Bar", 4, "chart_kpi", "ODD", "Chart + 2 KPI zones (rate + YoY change)"],
    ["Attrition", "rates", "A9.2", "Closure Duration", "Horizontal Bar", 5, "chart_narrative", "ODD", "Hbar + duration distribution insights"],
    ["Attrition", "rates", "A9.3", "Open vs Closed", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair (open left, closed right)"],
    # Attrition - Dimensions
    ["Attrition", "dimensions", "A9.4", "Closure by Branch", "Horizontal Bar", 9, "screenshot", "ODD", "Full-width; many branches"],
    ["Attrition", "dimensions", "A9.5", "Closure by Product", "Bar", 5, "chart_narrative", "ODD", "Chart + product attrition narrative"],
    ["Attrition", "dimensions", "A9.6", "Personal vs Business", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair (personal left, business right)"],
    ["Attrition", "dimensions", "A9.7", "Closure by Tenure", "Bar", 5, "chart_narrative", "ODD", "Chart + tenure band insights"],
    ["Attrition", "dimensions", "A9.8", "Closure by Balance", "Bar", 5, "chart_narrative", "ODD", "Chart + balance tier insights"],
    # Attrition - Impact
    ["Attrition", "impact", "A9.9", "Debit Retention Impact", "KPI + Chart", 4, "chart_kpi", "ODD", "Chart + retention rate + revenue KPIs"],
    ["Attrition", "impact", "A9.10", "Mailer Retention Impact", "KPI + Chart", 4, "chart_kpi", "ODD", "Chart + mailer lift + response KPIs"],
    ["Attrition", "impact", "A9.11", "Revenue Lost", "KPI + Chart", 4, "chart_kpi", "ODD", "Chart + lost revenue + account count KPIs"],
    ["Attrition", "impact", "A9.12", "L12M Velocity Impact", "KPI + Line", 5, "chart_narrative", "ODD", "Trend line + velocity narrative"],
    ["Attrition", "impact", "A9.13", "ARS vs Non-ARS Attrition", "Bar", 6, "comparison", "ODD", "Natural comparison; ARS left vs Non-ARS right"],
    # Value
    ["Value", "analysis", "A11.1", "Value of Debit Card", "Waterfall", 5, "chart_narrative", "ODD", "Waterfall + value buildup narrative"],
    ["Value", "analysis", "A11.2", "Value of Reg E", "Waterfall", 5, "chart_narrative", "ODD", "Waterfall + Reg E value narrative"],
    # Mailer - Insights (monthly, dynamic count)
    ["Mailer", "insights", "A13.{month}", "Monthly Response Summary", "Composite", 7, "kpi_grid", "ODD", "6-cell KPI grid; one per mailer month"],
    ["Mailer", "insights", "A12.{month}.Swipes", "Monthly Swipes Trend", "Line", 6, "comparison", "ODD", "Pair with Spend (swipes left, spend right)"],
    ["Mailer", "insights", "A12.{month}.Spend", "Monthly Spend Trend", "Line", 6, "comparison", "ODD", "Pair with Swipes (swipes left, spend right)"],
    # Mailer - Response
    ["Mailer", "response", "A13.5", "Program Response Count Trend", "Line", 5, "chart_narrative", "ODD", "Trend line + response trajectory text"],
    ["Mailer", "response", "A13.6", "Response Rate Trend", "Line", 5, "chart_narrative", "ODD", "Trend line + rate commentary"],
    ["Mailer", "response", "A13.Agg", "Aggregate Program Summary", "Donut/Bar", 7, "kpi_grid", "ODD", "Multi-KPI aggregate summary"],
    ["Mailer", "response", "A14.2", "Mailer Revisit Analysis", "Bar", 5, "chart_narrative", "ODD", "Chart + revisit pattern narrative"],
    # Mailer - Impact
    ["Mailer", "impact", "A15.1", "Mailer Lift Revenue", "KPI", 4, "chart_kpi", "ODD", "Chart + revenue lift + ROI KPIs"],
    ["Mailer", "impact", "A15.2", "Mailer Response Driver", "Bar", 5, "chart_narrative", "ODD", "Chart + driver analysis text"],
    ["Mailer", "impact", "A15.3", "Mailer Effectiveness", "Line", 5, "chart_narrative", "ODD", "Trend line + effectiveness narrative"],
    ["Mailer", "impact", "A15.4", "Mailer ROI Summary", "KPI", 7, "kpi_grid", "ODD", "6-cell KPI grid for ROI metrics"],
    # Insights
    ["Insights", "synthesis", "S1", "Growth Drivers", "Text + Chart", 5, "chart_narrative", "ODD", "Chart + growth driver narrative"],
    ["Insights", "synthesis", "S2", "Risk Factors", "Text + Chart", 5, "chart_narrative", "ODD", "Chart + risk factor narrative"],
    ["Insights", "synthesis", "S3", "Opportunity Analysis", "Text + Chart", 5, "chart_narrative", "ODD", "Chart + opportunity narrative"],
    ["Insights", "synthesis", "S4", "Program Impact", "Text + Chart", 5, "chart_narrative", "ODD", "Chart + program impact narrative"],
    ["Insights", "synthesis", "S5", "Recommendations", "Text + Chart", 5, "chart_narrative", "ODD", "Chart + actionable recommendations"],
    ["Insights", "conclusions", "S6", "Conclusion 1", "Text", 2, "section_text", "ODD", "Divider layout with conclusion text in content area"],
    ["Insights", "conclusions", "S7", "Conclusion 2", "Text", 2, "section_text", "ODD", "Divider layout with conclusion text in content area"],
    ["Insights", "conclusions", "S8", "Conclusion 3", "Text", 2, "section_text", "ODD", "Divider layout with conclusion text in content area"],
]

TXN_DATA = [
    # M1: Overall
    ["M1 Overall", "overall", "top_merchants_by_spend", "Top Merchants by Spend", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; top 25 merchants"],
    ["M1 Overall", "overall", "top_merchants_by_transactions", "Top Merchants by Transactions", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; top 25 merchants"],
    ["M1 Overall", "overall", "top_merchants_by_accounts", "Top Merchants by Accounts", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; top 25 merchants"],
    # M2: MCC
    ["M2 MCC", "mcc", "mcc_by_accounts", "MCC by Accounts", "Table", "", "data_only", "TXN CSV", "Excel-only data table; no chart"],
    ["M2 MCC", "mcc", "mcc_by_transactions", "MCC by Transactions", "Table", "", "data_only", "TXN CSV", "Excel-only data table; no chart"],
    ["M2 MCC", "mcc", "mcc_by_spend", "MCC by Spend", "Table", "", "data_only", "TXN CSV", "Excel-only data table; no chart"],
    ["M2 MCC", "mcc", "mcc_comparison", "MCC Comparison", "3-Panel Bar", 8, "grid_thirds", "TXN CSV", "3 panels in 3-col grid; needs all 3 MCC results"],
    # M3: Business
    ["M3 Business", "business", "business_top_by_spend", "Business Top by Spend", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; many merchants"],
    ["M3 Business", "business", "business_top_by_transactions", "Business Top by Transactions", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; many merchants"],
    ["M3 Business", "business", "business_top_by_accounts", "Business Top by Accounts", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; many merchants"],
    # M4: Personal
    ["M4 Personal", "personal", "personal_top_by_spend", "Personal Top by Spend", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; #62 decompression bomb fixed"],
    ["M4 Personal", "personal", "personal_top_by_transactions", "Personal Top by Transactions", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; many merchants"],
    ["M4 Personal", "personal", "personal_top_by_accounts", "Personal Top by Accounts", "Lollipop", 9, "screenshot", "TXN CSV", "Full-width; many merchants"],
    # M5: Trends
    ["M5 Trends", "trends", "monthly_rank_tracking", "Monthly Rank Trajectory", "Line", 5, "chart_narrative", "TXN CSV", "Trajectory line + rank movement commentary"],
    ["M5 Trends", "trends", "growth_leaders_decliners", "Growth Leaders & Decliners", "Grouped Bar", 4, "chart_kpi", "TXN CSV", "Chart + top leader/decliner KPI callouts"],
    ["M5 Trends", "trends", "spending_consistency", "Spending Consistency", "Scatter", 5, "chart_narrative", "TXN CSV", "Scatter + consistency explanation; no chart yet"],
    ["M5 Trends", "trends", "new_vs_declining_merchants", "New vs Declining Merchants", "Bar", 6, "comparison", "TXN CSV", "Natural split: new left vs declining right"],
    ["M5 Trends", "trends", "business_monthly_movers", "Business Monthly Movers", "Table", "", "data_only", "TXN CSV", "Excel-only table"],
    ["M5 Trends", "trends", "personal_monthly_movers", "Personal Monthly Movers", "Table", "", "data_only", "TXN CSV", "Excel-only table"],
    # M6: Competitor
    ["M6 Competitor", "competitor", "competitor_detection", "Competitor Detection", "Data", "", "data_only", "TXN CSV", "Engine step; populates context for downstream"],
    ["M6 Competitor", "competitor", "competitor_high_level", "Competitor High Level", "KPI", 7, "kpi_grid", "TXN CSV", "6-cell KPI grid: share, count, trend metrics"],
    ["M6 Competitor", "competitor", "top_20_competitors", "Top 20 Competitors", "Table", "", "data_only", "TXN CSV", "Excel-only table"],
    ["M6 Competitor", "competitor", "competitor_categories", "Competitor Categories", "Heatmap", 9, "screenshot", "TXN CSV", "Full-width heatmap; many categories x competitors"],
    ["M6 Competitor", "competitor", "competitor_biz_personal", "Competitor Biz vs Personal", "Table", 6, "comparison", "TXN CSV", "Split: business left vs personal right"],
    ["M6 Competitor", "competitor", "competitor_monthly_trends", "Competitor Monthly Trends", "Line", 5, "chart_narrative", "TXN CSV", "Trend line + competitive shift narrative"],
    ["M6 Competitor", "competitor", "competitor_threat_assessment", "Competitor Threat Assessment", "Scatter", 5, "chart_narrative", "TXN CSV", "Scatter + threat level explanation"],
    ["M6 Competitor", "competitor", "competitor_segmentation", "Competitor Segmentation", "Bar", 5, "chart_narrative", "TXN CSV", "Chart + segmentation breakdown text"],
    ["M6 Competitor", "competitor", "unmatched_financial", "Unmatched Financial", "Table", "", "data_only", "TXN CSV", "Data quality audit; Excel-only"],
    # M7: Financial
    ["M7 Financial", "financial", "financial_services_detection", "Financial Services Detection", "Data", "", "data_only", "TXN CSV", "Engine step; must run before M7B"],
    ["M7 Financial", "financial", "financial_services_summary", "Financial Services Summary", "KPI", 7, "kpi_grid", "TXN CSV", "6-cell KPI grid for financial services metrics"],
    # M8: Interchange
    ["M8 Interchange", "interchange", "interchange_summary", "Interchange Summary", "KPI", 7, "kpi_grid", "TXN CSV", "6-cell KPI grid for interchange metrics"],
    # M10: Member
    ["M10 Member", "member", "member_segments", "Member Segments", "KPI", 7, "kpi_grid", "TXN CSV", "6-cell KPI grid for segment breakdown"],
    # M11: Demographics
    ["M11 Demographics", "demographics", "demographics", "Demographics (Generation)", "Table/Charts", 5, "chart_narrative", "TXN + ODD", "Chart + demographic narrative; requires ODD generation col"],
    # M15: Recurring
    ["M15 Recurring", "recurring", "recurring_payments", "Recurring Payment Merchants", "Bar", 5, "chart_narrative", "TXN CSV", "Chart + recurring merchant narrative"],
    ["M15 Recurring", "recurring", "recurring_payments:onsets", "Recurring Merchant Onsets", "Line", 5, "chart_narrative", "TXN CSV", "Trend line + onset timing narrative"],
    # M9: Scorecard
    ["M9 Scorecard", "scorecard", "portfolio_scorecard", "Portfolio Scorecard", "Bullet Chart", 8, "grid_thirds", "TXN CSV", "6-cell grid of bullet gauges; must run last"],
]

ICS_DATA = [
    # Summary
    ["Summary", "summary", "ax01", "Total ICS Accounts", "KPI Gauge", 7, "kpi_grid", "ICS Excel", "6-cell KPI grid: total, open, closed, rate"],
    ["Summary", "summary", "ax02", "Open ICS Accounts", "KPI", 7, "kpi_grid", "ICS Excel", "Combine with ax01 on same KPI grid"],
    ["Summary", "summary", "ax07", "ICS by Stat Code", "Bar", 9, "screenshot", "ICS Excel", "Full-width; many stat codes"],
    ["Summary", "summary", "ax06", "Product Code Distribution", "Donut", 5, "chart_narrative", "ICS Excel", "Donut + product mix commentary"],
    ["Summary", "summary", "ax05", "Debit Distribution", "Donut", 5, "chart_narrative", "ICS Excel", "Donut + debit penetration narrative"],
    ["Summary", "summary", "ax64", "Debit x Product Code", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; multi-group cross-tab"],
    ["Summary", "summary", "ax04", "Debit x Branch", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; many branches"],
    ["Summary", "summary", "ax03", "ICS Penetration by Branch", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + penetration rate narrative"],
    # Source
    ["Source", "source", "ax08", "Source Distribution", "Donut", 5, "chart_narrative", "ICS Excel", "Donut + REF/DM/Both breakdown narrative"],
    ["Source", "source", "ax85", "Source x Stat Code", "Stacked Bar", 9, "screenshot", "ICS Excel", "Full-width; complex stacked breakdown"],
    ["Source", "source", "ax09", "Source x Product Code", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; multi-group cross-tab"],
    ["Source", "source", "ax10", "Source x Branch", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; many branches x sources"],
    ["Source", "source", "ax11", "Account Type", "Donut", 6, "comparison", "ICS Excel", "Split: business left vs personal right"],
    ["Source", "source", "ax12", "Source by Year", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + year-over-year acquisition narrative"],
    ["Source", "source", "ax13", "Source Acquisition Mix", "Waterfall", 5, "chart_narrative", "ICS Excel", "Waterfall + acquisition channel explanation"],
    # DM Deep-Dive
    ["DM Deep-Dive", "dm_source", "ax45", "DM Overview", "Table", "", "data_only", "ICS Excel", "Excel-only summary table"],
    ["DM Deep-Dive", "dm_source", "ax46", "DM by Branch", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; many branches"],
    ["DM Deep-Dive", "dm_source", "ax47", "DM by Debit Status", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + DM debit activation narrative"],
    ["DM Deep-Dive", "dm_source", "ax48", "DM by Product", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + DM product mix narrative"],
    ["DM Deep-Dive", "dm_source", "ax49", "DM by Year", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + DM acquisition trajectory"],
    ["DM Deep-Dive", "dm_source", "ax50", "DM Activity Summary", "KPI", 7, "kpi_grid", "ICS Excel", "6-cell KPI grid for DM activity metrics"],
    ["DM Deep-Dive", "dm_source", "ax51", "DM Activity by Branch", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    ["DM Deep-Dive", "dm_source", "ax52", "DM Monthly Trends", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + monthly trajectory narrative"],
    # REF Deep-Dive
    ["REF Deep-Dive", "ref_source", "ax73", "REF Overview", "Table", "", "data_only", "ICS Excel", "Excel-only summary table"],
    ["REF Deep-Dive", "ref_source", "ax74", "REF by Branch", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; many branches"],
    ["REF Deep-Dive", "ref_source", "ax75", "REF by Debit Status", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + REF debit activation narrative"],
    ["REF Deep-Dive", "ref_source", "ax76", "REF by Product", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + REF product mix narrative"],
    ["REF Deep-Dive", "ref_source", "ax77", "REF by Year", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + REF acquisition trajectory"],
    ["REF Deep-Dive", "ref_source", "ax78", "REF Activity Summary", "KPI", 7, "kpi_grid", "ICS Excel", "6-cell KPI grid for REF activity metrics"],
    ["REF Deep-Dive", "ref_source", "ax79", "REF Activity by Branch", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    ["REF Deep-Dive", "ref_source", "ax80", "REF Monthly Trends", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + monthly trajectory narrative"],
    # Demographics
    ["Demographics", "demographics", "ax14", "Age Comparison", "Grouped Bar", 6, "comparison", "ICS Excel", "Split: ICS vs non-ICS age distributions"],
    ["Demographics", "demographics", "ax15", "Closures", "Donut", 5, "chart_narrative", "ICS Excel", "Donut + closure pattern narrative"],
    ["Demographics", "demographics", "ax16", "Open vs Close", "Grouped Bar", 6, "comparison", "ICS Excel", "Natural split: open left vs closed right"],
    ["Demographics", "demographics", "ax17", "Balance Tiers", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + balance tier distribution narrative"],
    ["Demographics", "demographics", "ax83", "Stat Open Close", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; stat codes x open/close"],
    ["Demographics", "demographics", "ax18", "Age vs Balance", "Scatter", 5, "chart_narrative", "ICS Excel", "Scatter + age-balance correlation narrative"],
    ["Demographics", "demographics", "ax19", "Balance Tier Detail", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; many tiers x breakdowns"],
    ["Demographics", "demographics", "ax20", "Age Distribution", "Histogram", 5, "chart_narrative", "ICS Excel", "Histogram + age distribution insights"],
    ["Demographics", "demographics", "ax21", "Balance Trajectory", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + balance trajectory narrative"],
    # Activity
    ["Activity", "activity", "ax22", "Activity Summary", "KPI", 7, "kpi_grid", "ICS Excel", "6-cell KPI grid: active, dormant, rates"],
    ["Activity", "activity", "ax23", "Activity by Debit+Source", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; multi-factor cross-tab"],
    ["Activity", "activity", "ax24", "Activity by Balance", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + balance-activity correlation narrative"],
    ["Activity", "activity", "ax25", "Activity by Branch", "Grouped Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    ["Activity", "activity", "ax63", "Monthly Trends", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + monthly activity narrative"],
    ["Activity", "activity", "ax71", "Activity Source Comparison", "Line", 6, "comparison", "ICS Excel", "Split: DM trend left vs REF trend right"],
    ["Activity", "activity", "ax72", "Monthly Interchange", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + interchange revenue narrative"],
    ["Activity", "activity", "ax26", "Business vs Personal", "Grouped Bar", 6, "comparison", "ICS Excel", "Split: business left vs personal right"],
    # Cohort
    ["Cohort", "cohort", "ax27", "Cohort Activation", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; cohorts x months"],
    ["Cohort", "cohort", "ax28", "Cohort Heatmap", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; cohorts x metrics"],
    ["Cohort", "cohort", "ax29", "Cohort Milestones", "Line", 5, "chart_narrative", "ICS Excel", "Milestone curves + activation timeline narrative"],
    ["Cohort", "cohort", "ax30", "Activation Summary", "KPI", 7, "kpi_grid", "ICS Excel", "6-cell KPI grid: activation rates by cohort"],
    ["Cohort", "cohort", "ax31", "Growth Patterns", "Line", 5, "chart_narrative", "ICS Excel", "Growth curves + pattern narrative"],
    ["Cohort", "cohort", "ax32", "Activation Personas", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + persona profile narrative"],
    ["Cohort", "cohort", "ax33", "Branch Activation", "Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    # Strategic
    ["Strategic", "strategic", "ax38", "Activation Funnel", "Funnel", 5, "chart_narrative", "ICS Excel", "Funnel + stage-by-stage explanation"],
    ["Strategic", "strategic", "ax39", "Revenue Impact", "Bar", 4, "chart_kpi", "ICS Excel", "Chart + revenue KPI callouts"],
    ["Strategic", "strategic", "ax65", "Revenue by Branch", "Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    ["Strategic", "strategic", "ax66", "Revenue by Source", "Donut", 5, "chart_narrative", "ICS Excel", "Donut + source revenue narrative"],
    ["Strategic", "strategic", "ax84", "Dormant High-Balance", "Table", "", "data_only", "ICS Excel", "Action list; Excel-only table"],
    # Portfolio
    ["Portfolio", "portfolio", "ax40", "Engagement Decay", "Line", 5, "chart_narrative", "ICS Excel", "Decay curve + retention strategy narrative"],
    ["Portfolio", "portfolio", "ax41", "Net Portfolio Growth", "Line", 5, "chart_narrative", "ICS Excel", "Growth line + portfolio health narrative"],
    ["Portfolio", "portfolio", "ax42", "Spend Concentration", "Scatter", 5, "chart_narrative", "ICS Excel", "Scatter + concentration risk narrative"],
    ["Portfolio", "portfolio", "ax67", "Closure by Source", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + source attrition narrative"],
    ["Portfolio", "portfolio", "ax68", "Closure by Branch", "Bar", 9, "screenshot", "ICS Excel", "Full-width; many branches"],
    ["Portfolio", "portfolio", "ax69", "Closure by Account Age", "Line", 5, "chart_narrative", "ICS Excel", "Line + age-attrition correlation narrative"],
    ["Portfolio", "portfolio", "ax70", "Net Growth by Source", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + source growth narrative"],
    ["Portfolio", "portfolio", "ax82", "Closure Rate Trend", "Line", 5, "chart_narrative", "ICS Excel", "Trend line + closure rate narrative"],
    # Performance
    ["Performance", "performance", "ax43", "Days to First Use", "Histogram", 5, "chart_narrative", "ICS Excel", "Histogram + activation speed narrative"],
    ["Performance", "performance", "ax44", "Branch Performance Index", "Bar", 9, "screenshot", "ICS Excel", "Full-width; ranked branches"],
    ["Performance", "performance", "ax81", "Product Code Performance", "Bar", 9, "screenshot", "ICS Excel", "Full-width; ranked products"],
    # Persona
    ["Persona", "persona", "ax55", "Persona Overview", "Bubble", 5, "chart_narrative", "ICS Excel", "Bubble chart + persona definition narrative"],
    ["Persona", "persona", "ax56", "Persona Contribution", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + contribution breakdown narrative"],
    ["Persona", "persona", "ax57", "Persona by Branch", "Heatmap", 9, "screenshot", "ICS Excel", "Full-width heatmap; personas x branches"],
    ["Persona", "persona", "ax58", "Persona by Source", "Grouped Bar", 5, "chart_narrative", "ICS Excel", "Chart + source-persona narrative"],
    ["Persona", "persona", "ax59", "Persona Revenue", "Bar", 5, "chart_narrative", "ICS Excel", "Chart + per-persona revenue narrative"],
    ["Persona", "persona", "ax60", "Persona by Balance", "Table", "", "data_only", "ICS Excel", "Detail table; Excel-only"],
    ["Persona", "persona", "ax61", "Persona Velocity", "Line", 5, "chart_narrative", "ICS Excel", "Velocity curves + spend trajectory narrative"],
    ["Persona", "persona", "ax62", "Persona Cohort Trend", "Line", 5, "chart_narrative", "ICS Excel", "Cohort lines + persona evolution narrative"],
    # Referral Intelligence Engine
    ["Referral", "referral", "REF-1", "Top Referrers", "Horizontal Bar", 9, "screenshot", "ICS + Referral", "Full-width; ranked referrer list"],
    ["Referral", "referral", "REF-2", "Emerging Referrers", "Bar", 5, "chart_narrative", "ICS + Referral", "Chart + emerging referrer narrative"],
    ["Referral", "referral", "REF-3", "Dormant High-Value Referrers", "Table", "", "data_only", "ICS + Referral", "Action list; Excel-only"],
    ["Referral", "referral", "REF-4", "One-time vs Repeat Referrers", "Donut", 6, "comparison", "ICS + Referral", "Split: one-time left vs repeat right"],
    ["Referral", "referral", "REF-5", "Staff Multipliers", "Grouped Bar", 5, "chart_narrative", "ICS + Referral", "Chart + staff impact narrative"],
    ["Referral", "referral", "REF-6", "Branch Influence Density", "Heatmap", 9, "screenshot", "ICS + Referral", "Full-width heatmap; branches x influence"],
    ["Referral", "referral", "REF-7", "Code Health Report", "Bar", 5, "chart_narrative", "ICS + Referral", "Chart + code health narrative"],
    ["Referral", "referral", "REF-8", "Overview KPIs", "Multi-KPI", 7, "kpi_grid", "ICS + Referral", "6-cell KPI grid; runs last; aggregates"],
]


def _write_sheet(wb: Workbook, name: str, data: list[list]) -> None:
    ws = wb.create_sheet(title=name)

    # Header row
    for col_idx, header in enumerate(COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Data rows
    for row_idx, row_data in enumerate(data, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = Font(name="Calibri", size=10)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=col_idx == 9)

    # Auto-width columns
    for col_idx in range(1, len(COLUMNS) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(COLUMNS[col_idx - 1])
        for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
            for cell in row:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 45)

    # Freeze header
    ws.freeze_panes = "A2"

    # Auto-filter
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{len(data) + 1}"


LAYOUT_COLUMNS = [
    "Layout Index",
    "Layout Name",
    "Purpose",
    "Key Placeholders",
    "Used For",
    "Notes",
]

LAYOUT_DATA = [
    [
        0,
        "Cover / Intro - Slide 1",
        "Title slide with logo area, 3 text sections, KPI images",
        "ph[0] title, ph[32] subtitle, ph[14/33/34] 3 picture slots, "
        "ph[26-31] 3 paired header+body blocks, ph[19] body text",
        "Opening / title slide",
        "3 picture placeholders for logos/icons; 3 header+body pairs for KPI text",
    ],
    [
        1,
        "Cover / Intro - Slide 2",
        "Minimal cover, centered title only",
        "ph[0] title (6.3\" x 0.9\")",
        "Simple cover / closing",
        "No content areas; title is center-positioned",
    ],
    [
        2,
        "Divider - Slide 2",
        "Section divider with subtitle bar + large content area",
        "ph[0] title, ph[13] subtitle bar, ph[1] content (5.1\" x 4.0\")",
        "Section dividers between modules",
        "Left-aligned layout; content area can hold bullets or overview text",
    ],
    [
        3,
        "Divider - Slide 3",
        "Minimal section divider with subtitle bar",
        "ph[0] title, ph[13] subtitle bar",
        "Section dividers (minimal)",
        "Full-width title; no content area beyond subtitle",
    ],
    [
        4,
        "Analysis - Slide 1 (Chart + 2 Text)",
        "Chart on left, 2 header+body text sections on right",
        "ph[0] title, ph[13] subtitle, ph[14] picture (5.5\" x 3.4\" left), "
        "ph[26/19] top header+body, ph[27/28] bottom header+body",
        "screenshot_kpi slides (chart + KPI callouts)",
        "Right side has 2 independent text zones for insights/KPIs",
    ],
    [
        5,
        "Analysis - Slide 2 (Chart + 1 Text)",
        "Chart on left, single tall text section on right",
        "ph[0] title, ph[13] subtitle, ph[14] picture (5.5\" x 3.4\" left), "
        "ph[26] header, ph[19] body (5.7\" x 4.0\" right)",
        "screenshot_kpi slides (chart + narrative)",
        "Right body is 4\" tall -- good for longer narratives or bullet lists",
    ],
    [
        6,
        "Analysis - Slide 3 - Split",
        "Two equal content areas side-by-side",
        "ph[0] title, ph[13] subtitle, ph[14] left (5.8\" x 4.3\"), ph[1] right (5.8\" x 4.3\")",
        "multi_screenshot (2 charts side-by-side)",
        "Both zones are generic OBJECT placeholders; can hold images or text",
    ],
    [
        7,
        "Analysis - Slide 4 - Split",
        "6-cell KPI grid (3 header+body pairs per column)",
        "ph[0] title, ph[13] subtitle, ph[26-30] left 3 pairs, ph[32-36] right 3 pairs",
        "KPI summary / data grid slides",
        "12 text placeholders total; designed for structured KPI readouts",
    ],
    [
        8,
        "Analysis - Slide 5 - Thirds",
        "6-cell grid (3 columns x 2 rows of content blocks)",
        "ph[0] title, ph[13] subtitle, ph[1/15/16] top row, ph[17/19/20] bottom row",
        "Multi-chart grids, comparison panels",
        "Each cell is 3.6\" x 2.1\"; all OBJECT type (images or text)",
    ],
    [
        9,
        "Analysis - Slide 6 - Main",
        "Full-width single content area (the workhorse screenshot layout)",
        "ph[0] title, ph[13] subtitle, ph[1] content (11.7\" x 4.3\")",
        "screenshot (single full-width chart)",
        "Most common layout; used for any single chart/image",
    ],
    [
        10,
        "Analysis - Slide 7 - Stacked Two",
        "2 rows: each has text on left + 3 pictures on right",
        "ph[0] title, ph[15/35] row headers, ph[19/36] row body, "
        "ph[29-31] top 3 pics, ph[32-34] bottom 3 pics",
        "Before/after comparisons, multi-image galleries",
        "6 picture placeholders (2.1\" x 1.8\" each); good for small chart grids",
    ],
    [
        11,
        "Analysis - Slide 8 - Blank",
        "Blank slide with right-aligned title",
        "ph[0] title (6.4\" x 1.6\", right side)",
        "Custom-built slides, freeform content",
        "No content placeholders; shapes must be added programmatically",
    ],
    [
        12,
        "Analysis - Slide 11 - Header1",
        "Pure background / decorative header",
        "(no placeholders)",
        "Visual separator, background-only",
        "No usable placeholders; purely decorative",
    ],
    [
        13,
        "Analysis - Slide 11 - Header2",
        "Background header with footer/slide number",
        "ph[11] footer, ph[12] slide number",
        "Mailer summaries, wide charts (custom positioning)",
        "No title/content placeholders; content placed via freeform shapes",
    ],
]


def _write_layout_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet(title="Template Layouts")

    # Header row
    for col_idx, header in enumerate(LAYOUT_COLUMNS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    # Data rows
    for row_idx, row_data in enumerate(LAYOUT_DATA, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = Font(name="Calibri", size=10)
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=col_idx >= 4)

    # Column widths
    widths = [14, 36, 52, 70, 42, 60]
    for col_idx, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    # Freeze header
    ws.freeze_panes = "A2"

    # Auto-filter
    ws.auto_filter.ref = f"A1:{get_column_letter(len(LAYOUT_COLUMNS))}{len(LAYOUT_DATA) + 1}"


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)

    _write_sheet(wb, "ARS", ARS_DATA)
    _write_sheet(wb, "TXN", TXN_DATA)
    _write_sheet(wb, "ICS", ICS_DATA)
    _write_layout_sheet(wb)

    out = "docs/slide_catalog.xlsx"
    wb.save(out)
    print(
        f"Saved {out} -- ARS: {len(ARS_DATA)} rows, TXN: {len(TXN_DATA)} rows, "
        f"ICS: {len(ICS_DATA)} rows, Layouts: {len(LAYOUT_DATA)} rows"
    )


if __name__ == "__main__":
    main()
