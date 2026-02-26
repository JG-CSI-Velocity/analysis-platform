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
    ["Overview", "stat_codes", "A1", "Stat Code Distribution", "Bar", 9, "screenshot", "ODD", ""],
    ["Overview", "product_codes", "A1b", "Product Code Distribution", "Bar", 9, "screenshot", "ODD", ""],
    ["Overview", "eligibility", "A3", "Eligibility Analysis", "Scatter", 9, "screenshot", "ODD", ""],
    # DCTR - Penetration
    ["DCTR", "penetration", "DCTR-1", "Historical Debit Card Take Rate", "Line", 9, "screenshot", "ODD", "Stored in ctx.results"],
    ["DCTR", "penetration", "DCTR-2", "DCTR: Open vs Eligible", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-3", "DCTR Snapshot: Open to TTM", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-4", "Personal DCTR", "Line", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-5", "Business DCTR", "Line", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-6", "Personal L12M DCTR", "Line", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-7", "Business L12M DCTR", "Line", 9, "screenshot", "ODD", ""],
    ["DCTR", "penetration", "DCTR-8", "Comprehensive DCTR Summary", "Grouped Bar", 9, "screenshot", "ODD", ""],
    # DCTR - Trends
    ["DCTR", "trends", "A7.4", "DCTR Recent Trend", "Line", 9, "screenshot", "ODD", "Reads penetration results"],
    ["DCTR", "trends", "A7.5", "DCTR Segment Analysis", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "trends", "A7.6a", "DCTR Trajectory + Segments", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["DCTR", "trends", "A7.6b", "DCTR Segment Breakdown", "Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "trends", "A7.14", "DCTR Cohort Analysis", "Line", 9, "screenshot", "ODD", ""],
    ["DCTR", "trends", "A7.15", "DCTR Cohort Detail", "Grouped Bar", 9, "screenshot", "ODD", ""],
    # DCTR - Branches
    ["DCTR", "branches", "DCTR-9", "Branch DCTR Comparison", "Heatmap", 9, "screenshot", "ODD", ""],
    ["DCTR", "branches", "A7.10a", "Branch Performance Matrix", "Heatmap", 13, "screenshot", "ODD", "Wide layout"],
    ["DCTR", "branches", "A7.10b", "Branch Detail View", "Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "branches", "A7.10c", "Branch KPI Summary", "KPI Panel", 4, "screenshot_kpi", "ODD", ""],
    ["DCTR", "branches", "DCTR-15", "Branch Rank", "Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "branches", "DCTR-16", "Branch Change", "Lollipop", 9, "screenshot", "ODD", ""],
    ["DCTR", "branches", "A7.13", "Branch Appendix Detail", "Heatmap", 9, "screenshot", "ODD", "Appendix"],
    # DCTR - Funnel
    ["DCTR", "funnel", "A7.7", "DCTR Funnel: Historical vs TTM", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["DCTR", "funnel", "A7.8", "Account Eligibility Funnel", "Funnel", 9, "screenshot", "ODD", ""],
    ["DCTR", "funnel", "A7.9", "Funnel Detail Breakdown", "Bar", 9, "screenshot", "ODD", ""],
    # DCTR - Overlays
    ["DCTR", "overlays", "DCTR-10", "Age Distribution Overlay", "Histogram", 9, "screenshot", "ODD", ""],
    ["DCTR", "overlays", "DCTR-11", "Product Code Breakdown", "Donut", 9, "screenshot", "ODD", ""],
    ["DCTR", "overlays", "DCTR-12", "Personal vs Business", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "overlays", "DCTR-13", "Balance Tier Analysis", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["DCTR", "overlays", "DCTR-14", "Account Age Impact", "Scatter", 9, "screenshot", "ODD", ""],
    # Reg E - Status
    ["Reg E", "status", "A8.1", "Reg E Overall Rate", "Line", 9, "screenshot", "ODD", ""],
    ["Reg E", "status", "A8.2", "Reg E: Open vs Eligible", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["Reg E", "status", "A8.3", "Reg E Snapshot", "Grouped Bar", 9, "screenshot", "ODD", ""],
    ["Reg E", "status", "A8.12", "Reg E Summary KPI", "KPI", 5, "screenshot_kpi", "ODD", ""],
    # Reg E - Dimensions
    ["Reg E", "dimensions", "A8.5", "Reg E Opportunity: Age", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["Reg E", "dimensions", "A8.6", "Reg E by Age Detail", "Bar", 9, "screenshot", "ODD", ""],
    ["Reg E", "dimensions", "A8.7", "Reg E by Tenure", "Heatmap", 9, "screenshot", "ODD", ""],
    ["Reg E", "dimensions", "A8.10", "Reg E Funnel", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["Reg E", "dimensions", "A8.11", "Reg E Funnel Detail", "Funnel", 9, "screenshot", "ODD", ""],
    # Reg E - Branches
    ["Reg E", "branches", "A8.4a", "Branch Reg E Matrix", "Heatmap", 13, "screenshot", "ODD", "Wide layout"],
    ["Reg E", "branches", "A8.4b", "Branch Reg E Detail", "Bar", 9, "screenshot", "ODD", ""],
    ["Reg E", "branches", "A8.4c", "Branch Appendix", "Heatmap", 9, "screenshot", "ODD", "Appendix"],
    ["Reg E", "branches", "A8.13", "Reg E Branch Rank", "Bar", 9, "screenshot", "ODD", ""],
    # Attrition - Rates
    ["Attrition", "rates", "A9.1", "Overall Attrition Rate", "KPI + Bar", 5, "screenshot_kpi", "ODD", ""],
    ["Attrition", "rates", "A9.2", "Closure Duration", "Horizontal Bar", 4, "screenshot", "ODD", ""],
    ["Attrition", "rates", "A9.3", "Open vs Closed", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    # Attrition - Dimensions
    ["Attrition", "dimensions", "A9.4", "Closure by Branch", "Horizontal Bar", 4, "screenshot", "ODD", ""],
    ["Attrition", "dimensions", "A9.5", "Closure by Product", "Bar", 4, "screenshot", "ODD", ""],
    ["Attrition", "dimensions", "A9.6", "Personal vs Business", "Multi-chart", 6, "multi_screenshot", "ODD", "Merged pair"],
    ["Attrition", "dimensions", "A9.7", "Closure by Tenure", "Bar", 4, "screenshot", "ODD", ""],
    ["Attrition", "dimensions", "A9.8", "Closure by Balance", "Bar", 4, "screenshot", "ODD", ""],
    # Attrition - Impact
    ["Attrition", "impact", "A9.9", "Debit Retention Impact", "KPI + Chart", 5, "screenshot_kpi", "ODD", ""],
    ["Attrition", "impact", "A9.10", "Mailer Retention Impact", "KPI + Chart", 5, "screenshot_kpi", "ODD", ""],
    ["Attrition", "impact", "A9.11", "Revenue Lost", "KPI + Chart", 5, "screenshot_kpi", "ODD", ""],
    ["Attrition", "impact", "A9.12", "L12M Velocity Impact", "KPI + Line", 5, "screenshot_kpi", "ODD", ""],
    ["Attrition", "impact", "A9.13", "ARS vs Non-ARS Attrition", "Bar", 4, "screenshot", "ODD", ""],
    # Value
    ["Value", "analysis", "A11.1", "Value of Debit Card", "Waterfall", 13, "screenshot", "ODD", ""],
    ["Value", "analysis", "A11.2", "Value of Reg E", "Waterfall", 13, "screenshot", "ODD", ""],
    # Mailer - Insights (monthly, dynamic count)
    ["Mailer", "insights", "A13.{month}", "Monthly Response Summary", "Composite", 13, "mailer_summary", "ODD", "One per mailer month"],
    ["Mailer", "insights", "A12.{month}.Swipes", "Monthly Swipes Trend", "Line", 13, "screenshot", "ODD", "Paired with monthly"],
    ["Mailer", "insights", "A12.{month}.Spend", "Monthly Spend Trend", "Line", 13, "screenshot", "ODD", "Paired with monthly"],
    # Mailer - Response
    ["Mailer", "response", "A13.5", "Program Response Count Trend", "Line", 13, "screenshot", "ODD", ""],
    ["Mailer", "response", "A13.6", "Response Rate Trend", "Line", 9, "screenshot", "ODD", ""],
    ["Mailer", "response", "A13.Agg", "Aggregate Program Summary", "Donut/Bar", 13, "mailer_summary", "ODD", ""],
    ["Mailer", "response", "A14.2", "Mailer Revisit Analysis", "Bar", 9, "screenshot", "ODD", ""],
    # Mailer - Impact
    ["Mailer", "impact", "A15.1", "Mailer Lift Revenue", "KPI", 13, "screenshot", "ODD", ""],
    ["Mailer", "impact", "A15.2", "Mailer Response Driver", "Bar", 13, "screenshot", "ODD", ""],
    ["Mailer", "impact", "A15.3", "Mailer Effectiveness", "Line", 13, "screenshot", "ODD", ""],
    ["Mailer", "impact", "A15.4", "Mailer ROI Summary", "KPI", 13, "screenshot", "ODD", ""],
    # Insights
    ["Insights", "synthesis", "S1", "Growth Drivers", "Text + Chart", 9, "screenshot", "ODD", ""],
    ["Insights", "synthesis", "S2", "Risk Factors", "Text + Chart", 9, "screenshot", "ODD", ""],
    ["Insights", "synthesis", "S3", "Opportunity Analysis", "Text + Chart", 9, "screenshot", "ODD", ""],
    ["Insights", "synthesis", "S4", "Program Impact", "Text + Chart", 9, "screenshot", "ODD", ""],
    ["Insights", "synthesis", "S5", "Recommendations", "Text + Chart", 9, "screenshot", "ODD", ""],
    ["Insights", "conclusions", "S6", "Conclusion 1", "Text", 9, "screenshot", "ODD", ""],
    ["Insights", "conclusions", "S7", "Conclusion 2", "Text", 9, "screenshot", "ODD", ""],
    ["Insights", "conclusions", "S8", "Conclusion 3", "Text", 9, "screenshot", "ODD", ""],
]

TXN_DATA = [
    # M1: Overall
    ["M1 Overall", "overall", "top_merchants_by_spend", "Top Merchants by Spend", "Lollipop", "", "screenshot", "TXN CSV", "Top 25"],
    ["M1 Overall", "overall", "top_merchants_by_transactions", "Top Merchants by Transactions", "Lollipop", "", "screenshot", "TXN CSV", "Top 25"],
    ["M1 Overall", "overall", "top_merchants_by_accounts", "Top Merchants by Accounts", "Lollipop", "", "screenshot", "TXN CSV", "Top 25"],
    # M2: MCC
    ["M2 MCC", "mcc", "mcc_by_accounts", "MCC by Accounts", "Table", "", "", "TXN CSV", ""],
    ["M2 MCC", "mcc", "mcc_by_transactions", "MCC by Transactions", "Table", "", "", "TXN CSV", ""],
    ["M2 MCC", "mcc", "mcc_by_spend", "MCC by Spend", "Table", "", "", "TXN CSV", ""],
    ["M2 MCC", "mcc", "mcc_comparison", "MCC Comparison", "3-Panel Bar", "", "screenshot", "TXN CSV", "Needs all 3 MCC results"],
    # M3: Business
    ["M3 Business", "business", "business_top_by_spend", "Business Top by Spend", "Lollipop", "", "screenshot", "TXN CSV", ""],
    ["M3 Business", "business", "business_top_by_transactions", "Business Top by Transactions", "Lollipop", "", "screenshot", "TXN CSV", ""],
    ["M3 Business", "business", "business_top_by_accounts", "Business Top by Accounts", "Lollipop", "", "screenshot", "TXN CSV", ""],
    # M4: Personal
    ["M4 Personal", "personal", "personal_top_by_spend", "Personal Top by Spend", "Lollipop", "", "screenshot", "TXN CSV", "Caused #62 decompression bomb"],
    ["M4 Personal", "personal", "personal_top_by_transactions", "Personal Top by Transactions", "Lollipop", "", "screenshot", "TXN CSV", ""],
    ["M4 Personal", "personal", "personal_top_by_accounts", "Personal Top by Accounts", "Lollipop", "", "screenshot", "TXN CSV", ""],
    # M5: Trends
    ["M5 Trends", "trends", "monthly_rank_tracking", "Monthly Rank Trajectory", "Line", "", "screenshot", "TXN CSV", ""],
    ["M5 Trends", "trends", "growth_leaders_decliners", "Growth Leaders & Decliners", "Grouped Bar", "", "screenshot", "TXN CSV", ""],
    ["M5 Trends", "trends", "spending_consistency", "Spending Consistency", "Scatter", "", "", "TXN CSV", "No chart registered"],
    ["M5 Trends", "trends", "new_vs_declining_merchants", "New vs Declining Merchants", "Bar", "", "screenshot", "TXN CSV", ""],
    ["M5 Trends", "trends", "business_monthly_movers", "Business Monthly Movers", "Table", "", "", "TXN CSV", ""],
    ["M5 Trends", "trends", "personal_monthly_movers", "Personal Monthly Movers", "Table", "", "", "TXN CSV", ""],
    # M6: Competitor
    ["M6 Competitor", "competitor", "competitor_detection", "Competitor Detection", "Data", "", "", "TXN CSV", "Must run first; populates context"],
    ["M6 Competitor", "competitor", "competitor_high_level", "Competitor High Level", "KPI", "", "", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "top_20_competitors", "Top 20 Competitors", "Table", "", "", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "competitor_categories", "Competitor Categories", "Heatmap", "", "screenshot", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "competitor_biz_personal", "Competitor Biz vs Personal", "Table", "", "", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "competitor_monthly_trends", "Competitor Monthly Trends", "Line", "", "", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "competitor_threat_assessment", "Competitor Threat Assessment", "Scatter", "", "screenshot", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "competitor_segmentation", "Competitor Segmentation", "Bar", "", "screenshot", "TXN CSV", ""],
    ["M6 Competitor", "competitor", "unmatched_financial", "Unmatched Financial", "Table", "", "", "TXN CSV", "Data quality check"],
    # M7: Financial
    ["M7 Financial", "financial", "financial_services_detection", "Financial Services Detection", "Data", "", "", "TXN CSV", "Must run before M7B"],
    ["M7 Financial", "financial", "financial_services_summary", "Financial Services Summary", "KPI", "", "", "TXN CSV", ""],
    # M8: Interchange
    ["M8 Interchange", "interchange", "interchange_summary", "Interchange Summary", "KPI", "", "", "TXN CSV", ""],
    # M10: Member
    ["M10 Member", "member", "member_segments", "Member Segments", "KPI", "", "", "TXN CSV", ""],
    # M11: Demographics
    ["M11 Demographics", "demographics", "demographics", "Demographics (Generation)", "Table/Charts", "", "", "TXN + ODD", "Requires ODD with generation col"],
    # M15: Recurring
    ["M15 Recurring", "recurring", "recurring_payments", "Recurring Payment Merchants", "Bar", "", "screenshot", "TXN CSV", ""],
    ["M15 Recurring", "recurring", "recurring_payments:onsets", "Recurring Merchant Onsets", "Line", "", "screenshot", "TXN CSV", "Composite key"],
    # M9: Scorecard
    ["M9 Scorecard", "scorecard", "portfolio_scorecard", "Portfolio Scorecard", "Bullet Chart", "", "screenshot", "TXN CSV", "Must run last; reads all results"],
]

ICS_DATA = [
    # Summary
    ["Summary", "summary", "ax01", "Total ICS Accounts", "KPI Gauge", "", "", "ICS Excel", ""],
    ["Summary", "summary", "ax02", "Open ICS Accounts", "KPI", "", "", "ICS Excel", ""],
    ["Summary", "summary", "ax07", "ICS by Stat Code", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Summary", "summary", "ax06", "Product Code Distribution", "Donut", "", "screenshot", "ICS Excel", ""],
    ["Summary", "summary", "ax05", "Debit Distribution", "Donut", "", "screenshot", "ICS Excel", ""],
    ["Summary", "summary", "ax64", "Debit x Product Code", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Summary", "summary", "ax04", "Debit x Branch", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Summary", "summary", "ax03", "ICS Penetration by Branch", "Bar", "", "screenshot", "ICS Excel", ""],
    # Source
    ["Source", "source", "ax08", "Source Distribution", "Donut", "", "screenshot", "ICS Excel", "REF/DM/Both"],
    ["Source", "source", "ax85", "Source x Stat Code", "Stacked Bar", "", "screenshot", "ICS Excel", ""],
    ["Source", "source", "ax09", "Source x Product Code", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Source", "source", "ax10", "Source x Branch", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Source", "source", "ax11", "Account Type", "Donut", "", "screenshot", "ICS Excel", "Biz vs Personal"],
    ["Source", "source", "ax12", "Source by Year", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Source", "source", "ax13", "Source Acquisition Mix", "Waterfall", "", "screenshot", "ICS Excel", ""],
    # DM Deep-Dive
    ["DM Deep-Dive", "dm_source", "ax45", "DM Overview", "Table", "", "", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax46", "DM by Branch", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax47", "DM by Debit Status", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax48", "DM by Product", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax49", "DM by Year", "Line", "", "screenshot", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax50", "DM Activity Summary", "KPI", "", "", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax51", "DM Activity by Branch", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["DM Deep-Dive", "dm_source", "ax52", "DM Monthly Trends", "Line", "", "screenshot", "ICS Excel", ""],
    # REF Deep-Dive
    ["REF Deep-Dive", "ref_source", "ax73", "REF Overview", "Table", "", "", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax74", "REF by Branch", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax75", "REF by Debit Status", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax76", "REF by Product", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax77", "REF by Year", "Line", "", "screenshot", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax78", "REF Activity Summary", "KPI", "", "", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax79", "REF Activity by Branch", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["REF Deep-Dive", "ref_source", "ax80", "REF Monthly Trends", "Line", "", "screenshot", "ICS Excel", ""],
    # Demographics
    ["Demographics", "demographics", "ax14", "Age Comparison", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax15", "Closures", "Donut", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax16", "Open vs Close", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax17", "Balance Tiers", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax83", "Stat Open Close", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax18", "Age vs Balance", "Scatter", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax19", "Balance Tier Detail", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax20", "Age Distribution", "Histogram", "", "screenshot", "ICS Excel", ""],
    ["Demographics", "demographics", "ax21", "Balance Trajectory", "Line", "", "screenshot", "ICS Excel", ""],
    # Activity
    ["Activity", "activity", "ax22", "Activity Summary", "KPI", "", "", "ICS Excel", ""],
    ["Activity", "activity", "ax23", "Activity by Debit+Source", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax24", "Activity by Balance", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax25", "Activity by Branch", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax63", "Monthly Trends", "Line", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax71", "Activity Source Comparison", "Line", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax72", "Monthly Interchange", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Activity", "activity", "ax26", "Business vs Personal", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    # Cohort
    ["Cohort", "cohort", "ax27", "Cohort Activation", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax28", "Cohort Heatmap", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax29", "Cohort Milestones", "Line", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax30", "Activation Summary", "KPI", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax31", "Growth Patterns", "Line", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax32", "Activation Personas", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Cohort", "cohort", "ax33", "Branch Activation", "Bar", "", "screenshot", "ICS Excel", ""],
    # Strategic
    ["Strategic", "strategic", "ax38", "Activation Funnel", "Funnel", "", "screenshot", "ICS Excel", ""],
    ["Strategic", "strategic", "ax39", "Revenue Impact", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Strategic", "strategic", "ax65", "Revenue by Branch", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Strategic", "strategic", "ax66", "Revenue by Source", "Donut", "", "screenshot", "ICS Excel", ""],
    ["Strategic", "strategic", "ax84", "Dormant High-Balance", "Table", "", "", "ICS Excel", ""],
    # Portfolio
    ["Portfolio", "portfolio", "ax40", "Engagement Decay", "Line", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax41", "Net Portfolio Growth", "Line", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax42", "Spend Concentration", "Scatter", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax67", "Closure by Source", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax68", "Closure by Branch", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax69", "Closure by Account Age", "Line", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax70", "Net Growth by Source", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Portfolio", "portfolio", "ax82", "Closure Rate Trend", "Line", "", "screenshot", "ICS Excel", ""],
    # Performance
    ["Performance", "performance", "ax43", "Days to First Use", "Histogram", "", "screenshot", "ICS Excel", ""],
    ["Performance", "performance", "ax44", "Branch Performance Index", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Performance", "performance", "ax81", "Product Code Performance", "Bar", "", "screenshot", "ICS Excel", ""],
    # Persona
    ["Persona", "persona", "ax55", "Persona Overview", "Bubble", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax56", "Persona Contribution", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax57", "Persona by Branch", "Heatmap", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax58", "Persona by Source", "Grouped Bar", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax59", "Persona Revenue", "Bar", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax60", "Persona by Balance", "Table", "", "", "ICS Excel", ""],
    ["Persona", "persona", "ax61", "Persona Velocity", "Line", "", "screenshot", "ICS Excel", ""],
    ["Persona", "persona", "ax62", "Persona Cohort Trend", "Line", "", "screenshot", "ICS Excel", ""],
    # Referral Intelligence Engine
    ["Referral", "referral", "REF-1", "Top Referrers", "Horizontal Bar", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-2", "Emerging Referrers", "Bar", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-3", "Dormant High-Value Referrers", "Table", "", "", "ICS + Referral", ""],
    ["Referral", "referral", "REF-4", "One-time vs Repeat Referrers", "Donut", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-5", "Staff Multipliers", "Grouped Bar", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-6", "Branch Influence Density", "Heatmap", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-7", "Code Health Report", "Bar", "", "screenshot", "ICS + Referral", ""],
    ["Referral", "referral", "REF-8", "Overview KPIs", "Multi-KPI", "", "", "ICS + Referral", "Runs last; aggregates"],
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


def main() -> None:
    wb = Workbook()
    wb.remove(wb.active)

    _write_sheet(wb, "ARS", ARS_DATA)
    _write_sheet(wb, "TXN", TXN_DATA)
    _write_sheet(wb, "ICS", ICS_DATA)

    out = "docs/slide_catalog.xlsx"
    wb.save(out)
    print(f"Saved {out} -- ARS: {len(ARS_DATA)} rows, TXN: {len(TXN_DATA)} rows, ICS: {len(ICS_DATA)} rows")


if __name__ == "__main__":
    main()
