"""Tests for effectiveness proof analysis (A18 series)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from ars_analysis.analytics.insights.effectiveness import (
    EffectivenessProof,
    _load_benchmarks,
)
from ars_analysis.pipeline.context import (
    ClientInfo,
    DataSubsets,
    OutputPaths,
    PipelineContext,
)


@pytest.fixture
def effectiveness_ctx(cohort_mailer_df, tmp_output_dir):
    """PipelineContext with upstream results seeded for effectiveness tests."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = cohort_mailer_df
    open_accts = df[df["Stat Code"] == "O"]

    ctx = PipelineContext(
        client=ClientInfo(
            client_id="9999",
            client_name="Test CU",
            month="2024.09",
            eligible_stat_codes=["O"],
            ic_rate=0.0015,
        ),
        paths=paths,
        data=df,
        subsets=DataSubsets(
            open_accounts=open_accts,
            eligible_data=open_accts.copy(),
            eligible_personal=open_accts[open_accts["Business?"] == "No"],
            eligible_business=open_accts[open_accts["Business?"] == "Yes"],
            eligible_with_debit=open_accts[open_accts["Debit?"] == "Yes"],
        ),
        start_date=date(2024, 2, 1),
        end_date=date(2024, 9, 30),
    )

    # Seed upstream results that A18 reads
    ctx.results["dctr_1"] = {
        "insights": {
            "overall_dctr": 0.45,
            "recent_dctr": 0.50,
            "total_accounts": 1000,
        }
    }
    ctx.results["dctr_3"] = {
        "insights": {
            "dctr": 0.52,
            "total_accounts": 800,
        }
    }
    ctx.results["reg_e_1"] = {
        "opt_in_rate": 0.38,
        "l12m_rate": 0.42,
        "total_base": 1000,
        "opted_in": 380,
        "opted_out": 620,
    }
    ctx.results["value_1"] = {
        "delta": 150.0,
        "accts_with": 500,
        "accts_without": 300,
        "rev_per_with": 250.0,
        "rev_per_without": 100.0,
        "hist_dctr": 0.45,
        "l12m_dctr": 0.52,
        "pot_hist": 50000.0,
        "pot_l12m": 35000.0,
        "pot_100": 120000.0,
    }

    return ctx


class TestLoadBenchmarks:
    def test_loads_defaults(self):
        benchmarks = _load_benchmarks()
        assert "debit_penetration_rate" in benchmarks
        assert benchmarks["debit_penetration_rate"] > 0

    def test_has_source(self):
        benchmarks = _load_benchmarks()
        assert "source" in benchmarks


class TestEffectivenessProofModule:
    def test_produces_slides(self, effectiveness_ctx):
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        assert len(results) >= 2
        assert all(r.success for r in results)

    def test_a18_1_dctr_progression(self, effectiveness_ctx):
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        a18_1 = [r for r in results if r.slide_id == "A18.1"]
        assert len(a18_1) == 1
        assert a18_1[0].chart_path.exists()
        assert "Historical" in a18_1[0].notes

    def test_a18_2_cumulative_value(self, effectiveness_ctx):
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        a18_2 = [r for r in results if r.slide_id == "A18.2"]
        assert len(a18_2) == 1
        assert a18_2[0].chart_path.exists()
        assert "$" in a18_2[0].notes

    def test_a18_3_benchmarks(self, effectiveness_ctx):
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        a18_3 = [r for r in results if r.slide_id == "A18.3"]
        assert len(a18_3) == 1
        assert a18_3[0].chart_path.exists()
        assert "benchmark" in a18_3[0].notes.lower()

    def test_no_dctr_results_still_works(self, effectiveness_ctx):
        effectiveness_ctx.results.pop("dctr_1", None)
        effectiveness_ctx.results.pop("dctr_3", None)
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        # Should still produce A18.2 at minimum (from mail data)
        successful = [r for r in results if r.success]
        assert len(successful) >= 1

    def test_no_mail_data_partial(self, effectiveness_ctx):
        effectiveness_ctx.data = effectiveness_ctx.data.drop(
            columns=["Apr24 Mail", "Apr24 Resp", "May24 Mail", "May24 Resp"]
        )
        effectiveness_ctx.results.pop("_mailer_pairs", None)
        module = EffectivenessProof()
        results = module.run(effectiveness_ctx)
        # A18.1 and A18.3 should still work (from DCTR results)
        assert any(r.slide_id == "A18.1" for r in results)
