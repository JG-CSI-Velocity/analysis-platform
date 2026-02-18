"""Tests for exports/kpi_slides.py -- KPI slide builders."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.exports.kpi_slides import (
    build_executive_kpi_slide,
    build_narrative_slide,
    generate_declarative_title,
)


def _exec_summary_result(hero_kpis=None, traffic_lights=None, narrative=None):
    """Build an AnalysisResult with executive summary metadata."""
    metadata = {}
    if hero_kpis is not None:
        metadata["hero_kpis"] = hero_kpis
    if traffic_lights is not None:
        metadata["traffic_lights"] = traffic_lights
    if narrative is not None:
        metadata["narrative"] = narrative
    return AnalysisResult(
        name="Executive Summary",
        title="Executive Summary - Key ICS Metrics",
        df=pd.DataFrame({"Metric": ["A"], "Value": [1]}),
        metadata=metadata,
    )


class TestBuildExecutiveKpiSlide:
    def test_returns_slide_content(self):
        result = _exec_summary_result(
            hero_kpis={"Total ICS Accounts": 500, "Active Rate": 55.0},
            traffic_lights={"Active Rate": "yellow"},
        )
        slide = build_executive_kpi_slide(result)
        assert slide is not None
        assert slide.slide_type == "summary"
        assert "Key Performance Indicators" in slide.title

    def test_formats_kpi_bullets(self):
        result = _exec_summary_result(
            hero_kpis={
                "Total ICS Accounts": 1200,
                "Penetration Rate": 72.5,
                "Estimated Interchange": 45000.0,
            },
        )
        slide = build_executive_kpi_slide(result)
        assert any("1,200" in b for b in slide.bullets if b)
        assert any("72.5%" in b for b in slide.bullets if b)
        assert any("$45,000" in b for b in slide.bullets if b)

    def test_includes_traffic_light_indicator(self):
        result = _exec_summary_result(
            hero_kpis={"Active Rate": 55.0},
            traffic_lights={"Active Rate": "green"},
        )
        slide = build_executive_kpi_slide(result)
        assert any("[GREEN]" in b for b in slide.bullets if b)

    def test_returns_none_without_hero_kpis(self):
        result = _exec_summary_result()
        assert build_executive_kpi_slide(result) is None

    def test_pads_to_six_bullets(self):
        result = _exec_summary_result(hero_kpis={"A": 1, "B": 2})
        slide = build_executive_kpi_slide(result)
        assert len(slide.bullets) >= 6


class TestBuildNarrativeSlide:
    def test_returns_slide_content(self):
        result = _exec_summary_result(
            narrative=[
                {"type": "what", "text": "62% active."},
                {"type": "so_what", "text": "Revenue left on table."},
                {"type": "now_what", "text": "Target dormant accounts."},
            ],
        )
        slide = build_narrative_slide(result)
        assert slide is not None
        assert slide.slide_type == "summary"
        assert "Narrative" in slide.title

    def test_formats_bullets(self):
        result = _exec_summary_result(
            narrative=[
                {"type": "what", "text": "Active rate is 62%."},
                {"type": "now_what", "text": "Run campaign."},
            ],
        )
        slide = build_narrative_slide(result)
        assert any("WHAT:" in b for b in slide.bullets)
        assert any("NOW WHAT:" in b for b in slide.bullets)

    def test_returns_none_without_narrative(self):
        result = _exec_summary_result()
        assert build_narrative_slide(result) is None


class TestGenerateDeclarativeTitle:
    def test_fallback_to_title(self):
        result = AnalysisResult(
            name="Unknown",
            title="Some Title",
            df=pd.DataFrame({"x": [1]}),
        )
        assert generate_declarative_title(result) == "Some Title"

    def test_empty_df_falls_back(self):
        result = AnalysisResult(
            name="Activation Funnel",
            title="Activation Funnel",
            df=pd.DataFrame(),
        )
        assert generate_declarative_title(result) == "Activation Funnel"

    def test_activation_funnel(self):
        df = pd.DataFrame(
            {
                "Stage": ["Total", "Active"],
                "Count": [1000, 600],
            }
        )
        result = AnalysisResult(
            name="Activation Funnel",
            title="Activation Funnel",
            df=df,
        )
        title = generate_declarative_title(result)
        assert "60%" in title
        assert "active" in title.lower()

    def test_days_to_first_use(self):
        df = pd.DataFrame(
            {
                "Days Bucket": ["0-30", "31-60", "Never Used"],
                "Count": [50, 30, 20],
            }
        )
        result = AnalysisResult(
            name="Days to First Use",
            title="Days to First Use",
            df=df,
        )
        title = generate_declarative_title(result)
        assert "80%" in title
        assert "activate" in title.lower()

    def test_engagement_decay(self):
        df = pd.DataFrame(
            {
                "Category": ["Active", "Decayed", "Never Active"],
                "Count": [60, 25, 15],
                "% of Total": [60.0, 25.0, 15.0],
            }
        )
        result = AnalysisResult(
            name="Engagement Decay",
            title="Engagement Decay",
            df=df,
        )
        title = generate_declarative_title(result)
        assert "25.0%" in title
        assert "decay" in title.lower()

    def test_spend_concentration(self):
        df = pd.DataFrame(
            {
                "Percentile": ["Top 10%", "Top 20%", "Top 50%"],
                "Account Count": [10, 20, 50],
                "Spend Share %": [65.0, 80.0, 95.0],
            }
        )
        result = AnalysisResult(
            name="Spend Concentration",
            title="Spend Concentration",
            df=df,
        )
        title = generate_declarative_title(result)
        assert "65%" in title
        assert "Top 10%" in title

    def test_branch_performance_index(self):
        df = pd.DataFrame(
            {
                "Branch": ["Branch A", "Branch B"],
                "Composite Score": [120.0, 95.0],
            }
        )
        result = AnalysisResult(
            name="Branch Performance Index",
            title="Branch Performance Index",
            df=df,
        )
        title = generate_declarative_title(result)
        assert "Branch A" in title
        assert "120" in title
