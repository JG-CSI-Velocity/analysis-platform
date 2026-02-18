"""Tests for analyses/templates.py -- reusable analysis templates."""

import pandas as pd
import pytest

from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    binned_summary,
    crosstab_summary,
    grouped_summary,
    kpi_summary,
)


@pytest.fixture
def simple_df():
    return pd.DataFrame(
        {
            "Category": ["A", "A", "B", "B", "C"],
            "Value": [10, 20, 30, 40, 50],
            "Flag": ["Yes", "No", "Yes", "Yes", "No"],
        }
    )


class TestGroupedSummary:
    def test_basic_groupby(self, simple_df):
        result = grouped_summary(
            simple_df,
            group_col="Category",
            agg_specs={"Count": ("Value", "size"), "Total": ("Value", "sum")},
        )
        assert "Category" in result.columns
        assert "Count" in result.columns
        assert "Total" in result.columns
        assert len(result) == 3

    def test_with_pct_of(self, simple_df):
        result = grouped_summary(
            simple_df,
            group_col="Category",
            agg_specs={"Count": ("Value", "size")},
            pct_of=["Count"],
        )
        assert "% of Count" in result.columns
        pct_sum = result["% of Count"].sum()
        assert abs(pct_sum - 100.0) < 0.1

    def test_with_label_map(self, simple_df):
        result = grouped_summary(
            simple_df,
            group_col="Category",
            agg_specs={"Count": ("Value", "size")},
            label_map={"A": "Alpha", "B": "Beta"},
        )
        assert "Alpha" in result["Category"].values
        assert "Beta" in result["Category"].values

    def test_empty_df(self, simple_df):
        empty = simple_df.iloc[0:0]
        result = grouped_summary(
            empty,
            group_col="Category",
            agg_specs={"Count": ("Value", "size")},
        )
        assert result.empty

    def test_sorted_descending(self, simple_df):
        result = grouped_summary(
            simple_df,
            group_col="Category",
            agg_specs={"Count": ("Value", "size")},
        )
        # B has 2, A has 2, C has 1 -- B and A tied, C last
        assert result.iloc[-1]["Count"] <= result.iloc[0]["Count"]


class TestBinnedSummary:
    def test_basic_binning(self, simple_df):
        result = binned_summary(
            simple_df,
            value_col="Value",
            bins=[0, 25, 50, 100],
            labels=["Low", "Med", "High"],
            bin_name="Tier",
            agg_specs={"Count": ("Value", "size")},
        )
        assert "Tier" in result.columns
        assert "Count" in result.columns
        assert result["Count"].sum() == 5

    def test_with_pct(self, simple_df):
        result = binned_summary(
            simple_df,
            value_col="Value",
            bins=[0, 25, 50, 100],
            labels=["Low", "Med", "High"],
            bin_name="Tier",
            agg_specs={"Count": ("Value", "size")},
            pct_of=["Count"],
        )
        assert "% of Count" in result.columns

    def test_empty_df(self, simple_df):
        empty = simple_df.iloc[0:0]
        result = binned_summary(
            empty,
            value_col="Value",
            bins=[0, 25, 50, 100],
            labels=["Low", "Med", "High"],
            bin_name="Tier",
            agg_specs={"Count": ("Value", "size")},
        )
        assert result.empty


class TestCrosstabSummary:
    def test_basic_crosstab(self, simple_df):
        result = crosstab_summary(simple_df, row_col="Category", col_col="Flag")
        assert "Category" in result.columns
        assert "Total" in result.columns

    def test_with_rate_col(self, simple_df):
        result = crosstab_summary(
            simple_df,
            row_col="Category",
            col_col="Flag",
            add_rate_col="% Yes",
            rate_numerator="Yes",
        )
        assert "% Yes" in result.columns

    def test_empty_df(self, simple_df):
        empty = simple_df.iloc[0:0]
        result = crosstab_summary(empty, row_col="Category", col_col="Flag")
        assert result.empty

    def test_totals_present(self, simple_df):
        result = crosstab_summary(simple_df, row_col="Category", col_col="Flag")
        assert "Total" in result["Category"].values


class TestKpiSummary:
    def test_creates_metric_value_table(self):
        result = kpi_summary(
            [
                ("Total Accounts", 1000),
                ("Active Rate", "75.0%"),
            ]
        )
        assert list(result.columns) == ["Metric", "Value"]
        assert len(result) == 2
        assert result.iloc[0]["Metric"] == "Total Accounts"


class TestAppendGrandTotalRow:
    def test_appends_total(self):
        df = pd.DataFrame(
            {
                "Category": ["A", "B"],
                "Count": [10, 20],
                "% of Count": [33.3, 66.7],
            }
        )
        result = append_grand_total_row(df, label_col="Category")
        assert len(result) == 3
        assert result.iloc[-1]["Category"] == "Total"
        assert result.iloc[-1]["Count"] == 30
        assert result.iloc[-1]["% of Count"] == 100.0

    def test_empty_df(self):
        df = pd.DataFrame(columns=["Category", "Count"])
        result = append_grand_total_row(df, label_col="Category")
        assert result.empty
