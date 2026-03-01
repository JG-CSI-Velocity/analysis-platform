"""Tests for speaker notes generator."""

from ars_analysis.output.notes import generate_notes


class TestGenerateNotes:
    def test_basic_format(self):
        notes = generate_notes(
            slide_id="DCTR-1",
            headline="Debit adoption at 34.2%",
            insights={},
        )
        assert "KEY FINDING: Debit adoption at 34.2%" in notes
        assert "TALKING POINT:" in notes
        assert "strategic goals" in notes

    def test_with_kpis(self):
        notes = generate_notes(
            slide_id="DCTR-1",
            headline="Debit adoption at 34.2%",
            insights={},
            kpis={"Overall DCTR": "34.2%", "Total Accounts": "12,400"},
        )
        assert "Overall DCTR: 34.2%" in notes
        assert "Total Accounts: 12,400" in notes

    def test_kpi_subtitle_excluded(self):
        notes = generate_notes(
            slide_id="DCTR-1",
            headline="Debit adoption at 34.2%",
            insights={},
            kpis={"subtitle": "Some subtitle", "Rate": "34%"},
        )
        assert "subtitle" not in notes.split("TALKING POINT")[0]
        assert "Rate: 34%" in notes

    def test_with_context_notes(self):
        notes = generate_notes(
            slide_id="DCTR-1",
            headline="Debit adoption at 34.2%",
            insights={"insights": {"notes": "Historical trend shows improvement."}},
        )
        assert "CONTEXT: Historical trend shows improvement." in notes

    def test_empty_insights(self):
        notes = generate_notes(
            slide_id="DCTR-1",
            headline="Fallback Title",
            insights={},
        )
        assert notes.startswith("KEY FINDING: Fallback Title")
        assert "TALKING POINT:" in notes

    def test_no_kpis(self):
        notes = generate_notes(
            slide_id="A9.1",
            headline="Attrition at 6.2%",
            insights={},
            kpis=None,
        )
        lines = notes.strip().split("\n")
        assert lines[0] == "KEY FINDING: Attrition at 6.2%"
        # No KPI lines between finding and talking point
        assert any("TALKING POINT:" in line for line in lines)

    def test_non_dict_insights(self):
        notes = generate_notes(
            slide_id="DCTR-8",
            headline="Summary",
            insights="not a dict",
        )
        assert "KEY FINDING: Summary" in notes
        assert "TALKING POINT:" in notes

    def test_talking_points_always_present(self):
        notes = generate_notes(
            slide_id="A9.9",
            headline="Debit cards drive retention",
            insights={"insights": {"retention_lift": 0.083}},
            kpis={"Retention Lift": "8.3%"},
        )
        assert "What actions" in notes
        assert "strategic goals" in notes
