# v4_html_report.py
# HTML dashboard generator - self-contained interactive Plotly dashboards
# =============================================================================

from datetime import datetime
from pathlib import Path


def generate_html_report(storyline_results: dict, config: dict, output_path: str):
    """
    Generate a self-contained HTML dashboard with interactive Plotly charts.

    Parameters
    ----------
    storyline_results : dict
        Keys are storyline names (e.g., 's1_portfolio_health').
        Values are dicts with:
            'title': str - display title
            'sections': list of dicts, each with:
                'heading': str
                'narrative': str (insight text)
                'figures': list of go.Figure
                'tables': list of (title, pd.DataFrame)  [optional]
    config : dict
        Client config for header info.
    output_path : str
        Where to write the HTML file.
    """
    client_name = config.get("client_name", "Client")
    client_id = config.get("client_id", "")
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Build sidebar nav
    nav_items = []
    for key, result in storyline_results.items():
        nav_items.append(f'<a href="#{key}" class="nav-link">{result["title"]}</a>')
    nav_html = "\n".join(nav_items)

    # Build content sections
    content_sections = []
    for key, result in storyline_results.items():
        section_html = f'<div id="{key}" class="storyline-section">\n'
        section_html += f'<h2 class="storyline-title">{result["title"]}</h2>\n'

        for section in result.get("sections", []):
            section_html += f"<h3>{section['heading']}</h3>\n"

            if section.get("narrative"):
                section_html += f'<div class="narrative">{section["narrative"]}</div>\n'

            for fig in section.get("figures", []):
                chart_html = fig.to_html(
                    full_html=False,
                    include_plotlyjs=False,
                    config={"displayModeBar": True, "responsive": True},
                )
                section_html += f'<div class="chart-container">{chart_html}</div>\n'

            for table_title, table_df in section.get("tables", []):
                section_html += f"<h4>{table_title}</h4>\n"
                section_html += '<div class="table-container">\n'
                section_html += table_df.to_html(
                    classes="data-table",
                    index=False,
                    border=0,
                    escape=False,
                )
                section_html += "\n</div>\n"

        section_html += "</div>\n"
        content_sections.append(section_html)

    content_html = "\n".join(content_sections)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{client_name} - Transaction Analysis Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
:root {{
    --primary: #2E4057;
    --secondary: #048A81;
    --accent: #F18F01;
    --positive: #2D936C;
    --negative: #C73E1D;
    --neutral: #8B95A2;
    --light-bg: #F7F9FC;
    --white: #FFFFFF;
    --border: #E2E8F0;
    --sidebar-width: 260px;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--light-bg);
    color: var(--primary);
    line-height: 1.6;
}}

/* Sidebar */
.sidebar {{
    position: fixed;
    top: 0;
    left: 0;
    width: var(--sidebar-width);
    height: 100vh;
    background: var(--primary);
    color: var(--white);
    overflow-y: auto;
    z-index: 100;
    padding: 0;
}}

.sidebar-header {{
    padding: 24px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}}

.sidebar-header h1 {{
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 4px;
}}

.sidebar-header .client-id {{
    font-size: 12px;
    opacity: 0.6;
}}

.sidebar-header .generated {{
    font-size: 11px;
    opacity: 0.5;
    margin-top: 8px;
}}

.sidebar nav {{
    padding: 12px 0;
}}

.nav-link {{
    display: block;
    padding: 10px 20px;
    color: rgba(255,255,255,0.7);
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
    border-left: 3px solid transparent;
    transition: all 0.2s;
}}

.nav-link:hover,
.nav-link.active {{
    color: var(--white);
    background: rgba(255,255,255,0.08);
    border-left-color: var(--accent);
}}

/* Main content */
.main-content {{
    margin-left: var(--sidebar-width);
    padding: 40px;
    max-width: 1200px;
}}

.page-header {{
    margin-bottom: 40px;
    padding-bottom: 20px;
    border-bottom: 2px solid var(--primary);
}}

.page-header h1 {{
    font-size: 28px;
    font-weight: 700;
    color: var(--primary);
}}

.page-header .subtitle {{
    font-size: 14px;
    color: var(--neutral);
    margin-top: 4px;
}}

/* Storyline sections */
.storyline-section {{
    margin-bottom: 60px;
    scroll-margin-top: 20px;
}}

.storyline-title {{
    font-size: 22px;
    font-weight: 700;
    color: var(--primary);
    padding-bottom: 12px;
    border-bottom: 2px solid var(--secondary);
    margin-bottom: 24px;
}}

h3 {{
    font-size: 16px;
    font-weight: 600;
    color: var(--primary);
    margin: 24px 0 12px 0;
}}

h4 {{
    font-size: 14px;
    font-weight: 600;
    color: var(--neutral);
    margin: 16px 0 8px 0;
}}

/* Narrative insight boxes */
.narrative {{
    background: var(--white);
    border-left: 4px solid var(--accent);
    padding: 16px 20px;
    margin: 12px 0 20px 0;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    line-height: 1.7;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

/* Chart containers */
.chart-container {{
    background: var(--white);
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

/* Tables */
.table-container {{
    background: var(--white);
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    overflow-x: auto;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}

.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}

.data-table th {{
    background: var(--primary);
    color: var(--white);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.data-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
}}

.data-table tr:hover td {{
    background: var(--light-bg);
}}

.data-table tr:nth-child(even) td {{
    background: rgba(247,249,252,0.5);
}}

/* KPI cards */
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin: 20px 0;
}}

.kpi-card {{
    background: var(--white);
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    text-align: center;
}}

.kpi-value {{
    font-size: 28px;
    font-weight: 700;
    color: var(--primary);
}}

.kpi-label {{
    font-size: 12px;
    color: var(--neutral);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Responsive */
@media (max-width: 768px) {{
    .sidebar {{ display: none; }}
    .main-content {{ margin-left: 0; padding: 20px; }}
}}

/* Print */
@media print {{
    .sidebar {{ display: none; }}
    .main-content {{ margin-left: 0; }}
    .chart-container {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>

<div class="sidebar">
    <div class="sidebar-header">
        <h1>{client_name}</h1>
        <div class="client-id">Client ID: {client_id}</div>
        <div class="generated">Generated: {generated}</div>
    </div>
    <nav>
        {nav_html}
    </nav>
</div>

<div class="main-content">
    <div class="page-header">
        <h1>Transaction Analysis Dashboard</h1>
        <div class="subtitle">{client_name} | Generated {generated}</div>
    </div>

    {content_html}
</div>

<script>
// Highlight active nav link on scroll
const sections = document.querySelectorAll('.storyline-section');
const navLinks = document.querySelectorAll('.nav-link');

const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
        if (entry.isIntersecting) {{
            navLinks.forEach(link => link.classList.remove('active'));
            const activeLink = document.querySelector(`.nav-link[href="#${{entry.target.id}}"]`);
            if (activeLink) activeLink.classList.add('active');
        }}
    }});
}}, {{ threshold: 0.3 }});

sections.forEach(section => observer.observe(section));
</script>

</body>
</html>"""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(f"  HTML dashboard: {output}")


def build_kpi_html(kpis: list[dict]) -> str:
    """
    Build KPI card row HTML.

    Parameters
    ----------
    kpis : list of dict
        Each dict has 'label' and 'value' keys.
        Optional 'change' key for trend indicator.

    Returns
    -------
    str : HTML string for embedding in narrative.
    """
    cards = []
    for kpi in kpis:
        change_html = ""
        if "change" in kpi:
            change = kpi["change"]
            color = "var(--positive)" if change >= 0 else "var(--negative)"
            arrow = "&#9650;" if change >= 0 else "&#9660;"
            change_html = (
                f'<div style="color:{color};font-size:13px;margin-top:4px;">'
                f"{arrow} {abs(change):.1f}%</div>"
            )
        cards.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-value">{kpi["value"]}</div>'
            f'<div class="kpi-label">{kpi["label"]}</div>'
            f"{change_html}"
            f"</div>"
        )
    return f'<div class="kpi-row">{"".join(cards)}</div>'
