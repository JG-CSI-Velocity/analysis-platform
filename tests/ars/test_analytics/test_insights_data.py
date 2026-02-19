"""Tests for insights safe accessor functions."""

from ars_analysis.analytics.insights._data import (
    get_a3,
    get_attrition_1,
    get_attrition_9,
    get_attrition_10,
    get_attrition_11,
    get_attrition_12,
    get_dctr_1,
    get_dctr_3,
    get_dctr_9,
    get_market_reach,
    get_pre_post_delta,
    get_reg_e_1,
    get_revenue_attribution,
    get_value_1,
    get_value_2,
)
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext


def _empty_ctx(tmp_path):
    """Minimal context with no results."""
    return PipelineContext(
        client=ClientInfo(client_id="0", client_name="Empty", month="2024.01"),
        paths=OutputPaths(
            base_dir=tmp_path, charts_dir=tmp_path,
            excel_dir=tmp_path, pptx_dir=tmp_path,
        ),
    )


class TestDefaultsOnEmpty:
    """Every accessor returns sensible defaults when ctx.results is empty."""

    def test_value_1_defaults(self, tmp_path):
        r = get_value_1(_empty_ctx(tmp_path))
        assert r["delta"] == 0
        assert r["accts_without"] == 0

    def test_value_2_defaults(self, tmp_path):
        r = get_value_2(_empty_ctx(tmp_path))
        assert r["delta"] == 0

    def test_attrition_1_defaults(self, tmp_path):
        r = get_attrition_1(_empty_ctx(tmp_path))
        assert r["overall_rate"] == 0
        assert r["closed"] == 0

    def test_attrition_9_defaults(self, tmp_path):
        assert get_attrition_9(_empty_ctx(tmp_path))["retention_lift"] == 0

    def test_attrition_10_defaults(self, tmp_path):
        assert get_attrition_10(_empty_ctx(tmp_path))["lift"] == 0

    def test_attrition_11_defaults(self, tmp_path):
        r = get_attrition_11(_empty_ctx(tmp_path))
        assert r["total_lost"] == 0
        assert r["avg_lost"] == 0

    def test_attrition_12_defaults(self, tmp_path):
        r = get_attrition_12(_empty_ctx(tmp_path))
        assert r["total_l12m"] == 0

    def test_dctr_1_defaults(self, tmp_path):
        r = get_dctr_1(_empty_ctx(tmp_path))
        assert r["overall_dctr"] == 0

    def test_dctr_3_defaults(self, tmp_path):
        r = get_dctr_3(_empty_ctx(tmp_path))
        assert r["dctr"] == 0

    def test_dctr_9_defaults(self, tmp_path):
        r = get_dctr_9(_empty_ctx(tmp_path))
        assert r["best_dctr"] == 0

    def test_reg_e_1_defaults(self, tmp_path):
        r = get_reg_e_1(_empty_ctx(tmp_path))
        assert r["opt_in_rate"] == 0

    def test_market_reach_defaults(self, tmp_path):
        r = get_market_reach(_empty_ctx(tmp_path))
        assert r["n_responders"] == 0

    def test_revenue_attribution_defaults(self, tmp_path):
        r = get_revenue_attribution(_empty_ctx(tmp_path))
        assert r["incremental_total"] == 0

    def test_pre_post_delta_defaults(self, tmp_path):
        r = get_pre_post_delta(_empty_ctx(tmp_path))
        assert r["resp_delta"] == 0

    def test_a3_defaults(self, tmp_path):
        r = get_a3(_empty_ctx(tmp_path))
        assert r["eligible_accounts"] == 0


class TestExtractsPopulated:
    """Accessors extract correct values from populated ctx."""

    def test_value_1_populated(self, insights_ctx):
        r = get_value_1(insights_ctx)
        assert r["delta"] == 85.50
        assert r["accts_without"] == 800

    def test_attrition_9_populated(self, insights_ctx):
        assert get_attrition_9(insights_ctx)["retention_lift"] == 0.035

    def test_dctr_1_nested(self, insights_ctx):
        r = get_dctr_1(insights_ctx)
        assert r["overall_dctr"] == 0.60

    def test_dctr_9_nested(self, insights_ctx):
        r = get_dctr_9(insights_ctx)
        assert r["best_branch"] == "Downtown"
        assert r["best_dctr"] == 0.78

    def test_a3_nested(self, insights_ctx):
        r = get_a3(insights_ctx)
        assert r["eligible_accounts"] == 2000

    def test_revenue_attribution_populated(self, insights_ctx):
        r = get_revenue_attribution(insights_ctx)
        assert r["incremental_total"] == 1400.0
