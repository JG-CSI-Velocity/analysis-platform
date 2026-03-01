"""Tests for headline generator registry."""

from ars_analysis.output.headlines import (
    HEADLINE_GENERATORS,
    _fmt_currency,
    _fmt_pct,
    _is_valid,
    generate_headline,
    insights_key,
)

# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestIsValid:
    def test_none(self):
        assert _is_valid(None) is False

    def test_nan(self):
        assert _is_valid(float("nan")) is False

    def test_inf(self):
        assert _is_valid(float("inf")) is False

    def test_zero(self):
        assert _is_valid(0) is True

    def test_normal(self):
        assert _is_valid(0.342) is True

    def test_string(self):
        assert _is_valid("hello") is False


class TestFormatters:
    def test_fmt_pct(self):
        assert _fmt_pct(0.342) == "34.2%"

    def test_fmt_pct_zero(self):
        assert _fmt_pct(0.0) == "0.0%"

    def test_fmt_currency_millions(self):
        assert _fmt_currency(2_500_000) == "$2.5M"

    def test_fmt_currency_thousands(self):
        assert _fmt_currency(142_000) == "$142K"

    def test_fmt_currency_small(self):
        assert _fmt_currency(500) == "$500"


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestInsightsKey:
    def test_dctr_1(self):
        assert insights_key("DCTR-1") == "dctr_1"

    def test_attrition_1(self):
        assert insights_key("A9.1") == "attrition_1"

    def test_unknown(self):
        assert insights_key("UNKNOWN-99") is None


class TestGenerateHeadline:
    def test_fallback_on_unknown_slide_id(self):
        result = generate_headline("UNKNOWN-99", {}, fallback_title="Generic Title")
        assert result == "Generic Title"

    def test_fallback_on_empty_insights(self):
        result = generate_headline("DCTR-1", {}, fallback_title="Fallback")
        assert result == "Fallback"

    def test_fallback_on_nan_insights(self):
        insights = {"insights": {"overall_dctr": float("nan"), "total_accounts": 100}}
        result = generate_headline("DCTR-1", insights, fallback_title="Fallback")
        assert result == "Fallback"

    def test_fallback_on_zero_denominator(self):
        insights = {"insights": {"overall_dctr": 0.34, "total_accounts": 0}}
        result = generate_headline("DCTR-1", insights, fallback_title="Fallback")
        assert result == "Fallback"

    def test_fallback_on_generator_returning_empty(self):
        # DCTR-8 always returns "" (summary table)
        result = generate_headline("DCTR-8", {"summary": "df"}, fallback_title="Summary")
        assert result == "Summary"


# ---------------------------------------------------------------------------
# DCTR Generator tests
# ---------------------------------------------------------------------------


class TestDCTRHeadlines:
    def test_dctr_1_normal(self):
        insights = {
            "insights": {
                "overall_dctr": 0.342,
                "total_accounts": 12400,
                "recent_dctr": 0.38,
            }
        }
        result = generate_headline("DCTR-1", insights)
        assert "34.2%" in result
        assert "12,400" in result
        assert "trending up" in result

    def test_dctr_1_softening(self):
        insights = {
            "insights": {
                "overall_dctr": 0.40,
                "total_accounts": 5000,
                "recent_dctr": 0.30,
            }
        }
        result = generate_headline("DCTR-1", insights)
        assert "softening" in result

    def test_dctr_2_with_gap(self):
        insights = {
            "insights": {
                "open_dctr": 0.28,
                "eligible_dctr": 0.34,
                "difference": 0.06,
            }
        }
        result = generate_headline("DCTR-2", insights)
        assert "28.0%" in result
        assert "34.0%" in result
        assert "6pp" in result

    def test_dctr_3_above_baseline(self):
        insights = {
            "insights": {
                "dctr": 0.38,
                "comparison_to_overall": 0.04,
            }
        }
        result = generate_headline("DCTR-3", insights)
        assert "38.0%" in result
        assert "+4pp" in result

    def test_dctr_4_personal(self):
        insights = {
            "insights": {
                "overall_dctr": 0.35,
                "total_accounts": 10000,
                "recent_dctr": 0.35,
            }
        }
        result = generate_headline("DCTR-4", insights)
        assert "Personal" in result
        assert "35.0%" in result

    def test_dctr_5_business_no_accounts(self):
        insights = {"insights": {"overall_dctr": 0, "total_accounts": 0}}
        result = generate_headline("DCTR-5", insights, fallback_title="Business DCTR")
        assert result == "Business DCTR"

    def test_dctr_6_personal_l12m(self):
        insights = {"insights": {"dctr": 0.36, "total_accounts": 8000}}
        result = generate_headline("DCTR-6", insights)
        assert "Personal TTM" in result
        assert "36.0%" in result
        assert "8,000" in result

    def test_dctr_7_business_l12m(self):
        insights = {"insights": {"dctr": 0.22, "total_accounts": 500}}
        result = generate_headline("DCTR-7", insights)
        assert "Business TTM" in result
        assert "22.0%" in result


# ---------------------------------------------------------------------------
# Attrition Generator tests
# ---------------------------------------------------------------------------


class TestAttritionHeadlines:
    def test_a9_1_elevated(self):
        insights = {"insights": {"overall_rate": 0.12, "closed": 1500}}
        result = generate_headline("A9.1", insights)
        assert "elevated" in result
        assert "12.0%" in result
        assert "1,500" in result

    def test_a9_1_healthy(self):
        insights = {"insights": {"overall_rate": 0.03, "closed": 200}}
        result = generate_headline("A9.1", insights)
        assert "healthy" in result

    def test_a9_1_moderate(self):
        insights = {"insights": {"overall_rate": 0.07, "closed": 500}}
        result = generate_headline("A9.1", insights)
        assert "moderate" in result

    def test_a9_2_first_year(self):
        insights = {"insights": {"first_year_pct": 0.45}}
        result = generate_headline("A9.2", insights)
        assert "45.0%" in result
        assert "first year" in result

    def test_a9_9_retention(self):
        insights = {"insights": {"retention_lift": 0.083}}
        result = generate_headline("A9.9", insights)
        assert "8.3%" in result
        assert "retention" in result

    def test_a9_10_mailer(self):
        insights = {"insights": {"lift": 0.12}}
        result = generate_headline("A9.10", insights)
        assert "12.0%" in result
        assert "less often" in result

    def test_a9_11_revenue(self):
        insights = {"insights": {"total_lost": 142000}}
        result = generate_headline("A9.11", insights)
        assert "$142K" in result
        assert "risk" in result

    def test_a9_12_velocity(self):
        insights = {"insights": {"total_l12m": 350, "trend": "increasing"}}
        result = generate_headline("A9.12", insights)
        assert "350" in result
        assert "increasing" in result

    def test_a9_13_ars_lower(self):
        insights = {"insights": {"diff": -0.035}}
        result = generate_headline("A9.13", insights)
        assert "3.5pp" in result
        assert "lower" in result

    def test_a9_13_ars_higher(self):
        insights = {"insights": {"diff": 0.02}}
        result = generate_headline("A9.13", insights)
        assert "higher" in result

    def test_a9_3_no_data(self):
        # A9.3 has no ctx.results stored
        result = generate_headline("A9.3", {}, fallback_title="Open vs Closed")
        assert result == "Open vs Closed"

    def test_a9_4_branches(self):
        insights = {"insights": {"n_branches": 12}}
        result = generate_headline("A9.4", insights)
        assert "12" in result


# ---------------------------------------------------------------------------
# DCTR Detail Generator tests
# ---------------------------------------------------------------------------


class TestDCTRDetailHeadlines:
    def test_dctr_10_account_age(self):
        insights = {"insights": {"highest": "0-2 Years", "highest_dctr": 0.42, "lowest": "10+ Years", "lowest_dctr": 0.18}}
        result = generate_headline("DCTR-10", insights)
        assert "0-2 Years" in result
        assert "42.0%" in result

    def test_dctr_11_holder_age(self):
        insights = {"insights": {"highest": "25-34", "highest_dctr": 0.55, "lowest": "65+"}}
        result = generate_headline("DCTR-11", insights)
        assert "25-34" in result
        assert "55.0%" in result

    def test_dctr_12_balance(self):
        insights = {"insights": {"highest": "$5K-$10K", "highest_dctr": 0.48}}
        result = generate_headline("DCTR-12", insights)
        assert "$5K-$10K" in result

    def test_dctr_13_cross_tab(self):
        insights = {"segments": 24}
        result = generate_headline("DCTR-13", insights)
        assert "24" in result

    def test_dctr_15_best_branch(self):
        insights = {"best_new_branch": "Downtown"}
        result = generate_headline("DCTR-15", insights)
        assert "Downtown" in result

    def test_dctr_16_network(self):
        insights = {"grand_rate": 0.34, "branches": 8}
        result = generate_headline("DCTR-16", insights)
        assert "34.0%" in result
        assert "8" in result

    def test_a7_4_segment_trends(self):
        insights = {"personal_trend": 0.36, "business_trend": 0.22, "has_business": True}
        result = generate_headline("A7.4", insights)
        assert "36.0%" in result
        assert "22.0%" in result

    def test_a7_7_funnel(self):
        insights = {"through_rate": 0.82, "dctr_eligible": 0.38}
        result = generate_headline("A7.7", insights)
        assert "82.0%" in result

    def test_a7_8_ttm_funnel(self):
        insights = {"through": 0.85, "dctr": 0.40}
        result = generate_headline("A7.8", insights)
        assert "85.0%" in result

    def test_a7_9_eligible_gap(self):
        insights = {"eligible_dctr": 0.38, "non_eligible_dctr": 0.12, "gap": 0.26}
        result = generate_headline("A7.9", insights)
        assert "38.0%" in result
        assert "26pp" in result

    def test_a7_10a_improving(self):
        insights = {"improving": 6, "total": 8, "avg_change": 0.02}
        result = generate_headline("A7.10a", insights)
        assert "6" in result
        assert "8" in result


# ---------------------------------------------------------------------------
# Reg E + Value Generator tests
# ---------------------------------------------------------------------------


class TestRegEValueHeadlines:
    def test_a8_1_opt_in(self):
        insights = {"opt_in_rate": 0.67, "total_base": 15000}
        result = generate_headline("A8.1", insights)
        assert "67.0%" in result
        assert "15,000" in result

    def test_a11_1_debit_value(self):
        insights = {"delta": 85.0, "rev_per_with": 210.0, "rev_per_without": 125.0}
        result = generate_headline("A11.1", insights)
        assert "$85" in result
        assert "$210" in result

    def test_a11_2_rege_value(self):
        insights = {"delta": 45.0, "rev_per_with": 180.0}
        result = generate_headline("A11.2", insights)
        assert "$45" in result


# ---------------------------------------------------------------------------
# Overview Generator tests
# ---------------------------------------------------------------------------


class TestOverviewHeadlines:
    def test_a3_eligibility(self):
        insights = {"insights": {"eligible_accounts": 8500, "eligibility_rate": 0.72}}
        result = generate_headline("A3", insights)
        assert "8,500" in result
        assert "72.0%" in result

    def test_a1_with_insight_text(self):
        insights = {"insight": "Personal accounts dominate at 85% of portfolio"}
        result = generate_headline("A1", insights)
        assert "Personal accounts" in result


# ---------------------------------------------------------------------------
# Insights Generator tests
# ---------------------------------------------------------------------------


class TestInsightsHeadlines:
    def test_s1_revenue_gap(self):
        insights = {"total_gap": 500000, "realistic_capture": 200000}
        result = generate_headline("S1", insights)
        assert "$500K" in result
        assert "$200K" in result

    def test_s2_cost_of_attrition(self):
        insights = {"revenue_destroyed": 180000, "preventable_revenue": 90000}
        result = generate_headline("S2", insights)
        assert "$180K" in result
        assert "$90K" in result

    def test_s3_program_roi(self):
        insights = {"annual_program_value": 350000, "total_program_roi": 4.2}
        result = generate_headline("S3", insights)
        assert "$350K" in result
        assert "4.2x" in result

    def test_s4_branch_gap(self):
        insights = {"branch_gap_revenue": 120000, "spread": 0.15}
        result = generate_headline("S4", insights)
        assert "$120K" in result
        assert "15.0%" in result

    def test_s5_cascade(self):
        insights = {"total_cascade": 800000}
        result = generate_headline("S5", insights)
        assert "$800K" in result

    def test_s6_opportunity(self):
        insights = {"total_addressable": 1200000, "total_realistic": 600000}
        result = generate_headline("S6", insights)
        assert "$1.2M" in result
        assert "$600K" in result

    def test_s7_what_if(self):
        insights = {"new_debit_accounts": 500, "total_annual_gain": 250000}
        result = generate_headline("S7", insights)
        assert "500" in result
        assert "$250K" in result

    def test_s8_action_plan(self):
        insights = {"combined": 400000}
        result = generate_headline("S8", insights)
        assert "$400K" in result


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestAllGeneratorsRegistered:
    """Verify registry completeness."""

    def test_dctr_core_count(self):
        dctr = [k for k in HEADLINE_GENERATORS if k.startswith("DCTR-")]
        assert len(dctr) == 16

    def test_dctr_detail_count(self):
        a7 = [k for k in HEADLINE_GENERATORS if k.startswith("A7.")]
        assert len(a7) == 12

    def test_attrition_count(self):
        att = [k for k in HEADLINE_GENERATORS if k.startswith("A9.")]
        assert len(att) == 13

    def test_rege_count(self):
        rege = [k for k in HEADLINE_GENERATORS if k.startswith("A8.")]
        assert len(rege) == 13

    def test_value_count(self):
        val = [k for k in HEADLINE_GENERATORS if k.startswith("A11.")]
        assert len(val) == 2

    def test_insights_count(self):
        ins = [k for k in HEADLINE_GENERATORS if k.startswith("S")]
        assert len(ins) == 8

    def test_overview_count(self):
        ov = [k for k in HEADLINE_GENERATORS if k in ("A1", "A1b", "A3")]
        assert len(ov) == 3

    def test_total_generators(self):
        assert len(HEADLINE_GENERATORS) >= 75
