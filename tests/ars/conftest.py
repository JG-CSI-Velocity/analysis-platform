"""Shared test fixtures -- synthetic data, temp dirs, matplotlib cleanup."""

from datetime import date

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for CI

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from ars_analysis.pipeline.context import (  # noqa: E402
    ClientInfo,
    DataSubsets,
    OutputPaths,
    PipelineContext,
)


@pytest.fixture
def synthetic_odd_df():
    """Minimal ODD DataFrame with all required columns."""
    return pd.DataFrame(
        {
            "Date Opened": pd.to_datetime(["2025-01-15"] * 10),
            "Client ID": ["1200"] * 10,
            "Account Number": [f"ACC{i:04d}" for i in range(10)],
            "Product Code": ["DDA"] * 5 + ["SAV"] * 5,
            "Stat Code": ["A01"] * 3 + ["A02"] * 4 + ["A03"] * 3,
            "Branch": ["Main"] * 6 + ["North"] * 4,
            "Balance": [1000.0 + i * 100 for i in range(10)],
        }
    )


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary output directory for test artifacts."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture(autouse=True)
def _close_all_figures():
    """Prevent matplotlib figure leaks across tests."""
    yield
    plt.close("all")


# -- DCTR fixtures -----------------------------------------------------------


@pytest.fixture
def dctr_eligible_df():
    """DataFrame with DCTR-relevant columns spanning years/branches."""
    n = 50
    return pd.DataFrame(
        {
            "Date Opened": pd.date_range("2020-01-01", periods=n, freq="ME"),
            "Debit?": ["Yes"] * 30 + ["No"] * 20,
            "Business?": ["No"] * 35 + ["Yes"] * 15,
            "Branch": ["Main"] * 20 + ["North"] * 15 + ["South"] * 15,
            "Account Holder Age": [25 + i % 50 for i in range(n)],
            "Avg Bal": [500.0 + i * 200 for i in range(n)],
            "Stat Code": ["O"] * 40 + ["C"] * 10,
            "Product Code": ["DDA"] * n,
        }
    )


@pytest.fixture
def overview_df():
    """DataFrame with all overview-relevant columns."""
    n = 20
    return pd.DataFrame(
        {
            "Stat Code": ["O"] * 12 + ["C"] * 5 + ["F"] * 3,
            "Product Code": ["DDA"] * 10 + ["SAV"] * 5 + ["CD"] * 3 + ["DDA"] * 2,
            "Business?": ["No"] * 14 + ["Yes"] * 6,
            "Date Opened": pd.date_range("2023-01-01", periods=n, freq="ME"),
            "Debit?": ["Yes"] * 12 + ["No"] * 8,
            "Branch": ["Main"] * 10 + ["North"] * 10,
            "Avg Bal": [1000.0 + i * 100 for i in range(n)],
        }
    )


@pytest.fixture
def overview_ctx(overview_df, tmp_output_dir):
    """PipelineContext with overview data + eligible subsets."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = overview_df
    open_accts = df[df["Stat Code"] == "O"]
    eligible = open_accts[open_accts["Product Code"].isin(["DDA", "SAV"])]
    pers = eligible[eligible["Business?"] == "No"]
    biz = eligible[eligible["Business?"] == "Yes"]

    subs = DataSubsets(
        open_accounts=open_accts,
        eligible_data=eligible,
        eligible_personal=pers,
        eligible_business=biz,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2026.02",
            eligible_stat_codes=["O"],
            eligible_prod_codes=["DDA", "SAV"],
        ),
        paths=paths,
        data=df,
        subsets=subs,
    )


# -- DCTR fixtures -----------------------------------------------------------


@pytest.fixture
def dctr_ctx(dctr_eligible_df, tmp_output_dir):
    """PipelineContext with DCTR-ready data and subsets."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = dctr_eligible_df
    open_accts = df[df["Stat Code"] == "O"]
    eligible = open_accts.copy()
    pers = eligible[eligible["Business?"] == "No"]
    biz = eligible[eligible["Business?"] == "Yes"]
    with_debit = eligible[eligible["Debit?"] == "Yes"]

    subs = DataSubsets(
        open_accounts=open_accts,
        eligible_data=eligible,
        eligible_personal=pers,
        eligible_business=biz,
        eligible_with_debit=with_debit,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2024.02",
            eligible_stat_codes=["O"],
        ),
        paths=paths,
        data=df,
        subsets=subs,
        start_date=date(2023, 3, 1),
        end_date=date(2024, 2, 28),
    )


# -- Value fixtures ----------------------------------------------------------


@pytest.fixture
def value_df():
    """DataFrame with value-relevant columns (spend, items, Reg E)."""
    n = 30
    return pd.DataFrame(
        {
            "Date Opened": pd.date_range("2022-01-01", periods=n, freq="ME"),
            "Debit?": ["Yes"] * 20 + ["No"] * 10,
            "Business?": ["No"] * 25 + ["Yes"] * 5,
            "Stat Code": ["O"] * 28 + ["C"] * 2,
            "Product Code": ["DDA"] * n,
            "Branch": ["Main"] * 15 + ["North"] * 15,
            "L12M Spend": [500.0 + i * 100 for i in range(n)],
            "L12M Items": [5 + i for i in range(n)],
            "Reg E Code 2024.02": ["Y"] * 12 + ["N"] * 8 + ["Y"] * 5 + ["N"] * 5,
        }
    )


@pytest.fixture
def value_ctx(value_df, tmp_output_dir):
    """PipelineContext with value analysis data + fee config."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = value_df
    open_accts = df[df["Stat Code"] == "O"]
    eligible = open_accts.copy()
    pers = eligible[eligible["Business?"] == "No"]
    biz = eligible[eligible["Business?"] == "Yes"]
    with_debit = eligible[eligible["Debit?"] == "Yes"]

    subs = DataSubsets(
        open_accounts=open_accts,
        eligible_data=eligible,
        eligible_personal=pers,
        eligible_business=biz,
        eligible_with_debit=with_debit,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2024.02",
            eligible_stat_codes=["O"],
            nsf_od_fee=35.0,
            ic_rate=0.0015,
            reg_e_opt_in=["Y"],
            reg_e_column="Reg E Code 2024.02",
        ),
        paths=paths,
        data=df,
        subsets=subs,
        start_date=date(2023, 3, 1),
        end_date=date(2024, 2, 28),
    )


# -- Reg E fixtures ----------------------------------------------------------


@pytest.fixture
def rege_df():
    """DataFrame with Reg E-relevant columns spanning branches/years."""
    n = 40
    return pd.DataFrame(
        {
            "Date Opened": pd.date_range("2021-01-01", periods=n, freq="ME"),
            "Debit?": ["Yes"] * 30 + ["No"] * 10,
            "Business?": ["No"] * 30 + ["Yes"] * 10,
            "Branch": ["Main"] * 15 + ["North"] * 15 + ["South"] * 10,
            "Stat Code": ["O"] * 35 + ["C"] * 5,
            "Product Code": ["DDA"] * n,
            "Reg E Code 2024.02": ["Y"] * 15 + ["N"] * 15 + ["Y"] * 5 + ["N"] * 5,
            "Account Holder Age": [30 + i % 40 for i in range(n)],
            "Avg Bal": [1000.0 + i * 200 for i in range(n)],
        }
    )


@pytest.fixture
def rege_ctx(rege_df, tmp_output_dir):
    """PipelineContext with Reg E data and subsets."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = rege_df
    open_accts = df[df["Stat Code"] == "O"]
    eligible = open_accts.copy()
    pers = eligible[eligible["Business?"] == "No"]
    biz = eligible[eligible["Business?"] == "Yes"]
    with_debit = eligible[eligible["Debit?"] == "Yes"]

    subs = DataSubsets(
        open_accounts=open_accts,
        eligible_data=eligible,
        eligible_personal=pers,
        eligible_business=biz,
        eligible_with_debit=with_debit,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2024.02",
            eligible_stat_codes=["O"],
            reg_e_opt_in=["Y"],
            reg_e_column="Reg E Code 2024.02",
        ),
        paths=paths,
        data=df,
        subsets=subs,
        start_date=date(2023, 3, 1),
        end_date=date(2024, 2, 28),
    )


# -- Mailer fixtures ---------------------------------------------------------


@pytest.fixture
def mailer_df():
    """DataFrame with mailer-relevant columns (2 mail months, 4 metric months)."""
    n = 50

    # Mail segment assignment (same for both months)
    mail_seg = ["NU"] * 20 + ["TH-10"] * 10 + ["TH-15"] * 10 + [None] * 10

    # Apr24 responses: NU 8 resp, TH-10 5 resp, TH-15 3 resp = 16 total
    apr_resp = (
        ["NU 5+"] * 8
        + ["NU 1-4"] * 4
        + [None] * 8
        + ["TH-10"] * 5
        + [None] * 5
        + ["TH-15"] * 3
        + [None] * 7
        + [None] * 10
    )

    # May24 responses: NU 10 resp, TH-10 6 resp, TH-15 4 resp = 20 total
    may_resp = (
        ["NU 5+"] * 10
        + ["NU 1-4"] * 3
        + [None] * 7
        + ["TH-10"] * 6
        + [None] * 4
        + ["TH-15"] * 4
        + [None] * 6
        + [None] * 10
    )

    return pd.DataFrame(
        {
            "Date Opened": pd.date_range("2021-01-01", periods=n, freq="ME"),
            "Stat Code": ["O"] * 45 + ["C"] * 5,
            "Product Code": ["DDA"] * n,
            "Debit?": ["Yes"] * 35 + ["No"] * 15,
            "Business?": ["No"] * 40 + ["Yes"] * 10,
            "Branch": ["Main"] * 25 + ["North"] * 25,
            # Pre-mail spend/swipes (for pre/post delta)
            "Feb24 Spend": [400.0 + i * 40 for i in range(n)],
            "Feb24 Swipes": [8 + i for i in range(n)],
            "Mar24 Spend": [450.0 + i * 45 for i in range(n)],
            "Mar24 Swipes": [9 + i for i in range(n)],
            # Mail month 1
            "Apr24 Mail": mail_seg,
            "Apr24 Resp": apr_resp,
            "Apr24 Spend": [500.0 + i * 50 for i in range(n)],
            "Apr24 Swipes": [10 + i for i in range(n)],
            # Mail month 2
            "May24 Mail": mail_seg,
            "May24 Resp": may_resp,
            "May24 Spend": [600.0 + i * 50 for i in range(n)],
            "May24 Swipes": [12 + i for i in range(n)],
        }
    )


@pytest.fixture
def mailer_ctx(mailer_df, tmp_output_dir):
    """PipelineContext with mailer data, subsets, and fee config."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    df = mailer_df
    open_accts = df[df["Stat Code"] == "O"]
    eligible = open_accts.copy()
    pers = eligible[eligible["Business?"] == "No"]
    biz = eligible[eligible["Business?"] == "Yes"]
    with_debit = eligible[eligible["Debit?"] == "Yes"]

    subs = DataSubsets(
        open_accounts=open_accts,
        eligible_data=eligible,
        eligible_personal=pers,
        eligible_business=biz,
        eligible_with_debit=with_debit,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="9999",
            client_name="Test CU",
            month="2024.05",
            eligible_stat_codes=["O"],
            ic_rate=0.0015,
        ),
        paths=paths,
        data=df,
        subsets=subs,
        start_date=date(2023, 6, 1),
        end_date=date(2024, 5, 31),
    )


# -- Attrition fixtures ----------------------------------------------------


@pytest.fixture
def attrition_df():
    """DataFrame with attrition-relevant columns (open + closed accounts)."""
    n = 60
    dates_opened = pd.date_range("2019-01-01", periods=n, freq="ME")
    # 30 open (NaT), 30 closed (dates in 2023-2024)
    dates_closed = [pd.NaT] * 30 + list(pd.date_range("2023-01-31", periods=30, freq="ME"))
    return pd.DataFrame(
        {
            "Date Opened": dates_opened,
            "Date Closed": dates_closed,
            "Stat Code": ["O"] * 30 + ["C"] * 30,
            "Product Code": ["DDA"] * 40 + ["SAV"] * 20,
            "Branch": ["Main"] * 20 + ["North"] * 20 + ["South"] * 20,
            "Business?": ["No"] * 45 + ["Yes"] * 15,
            "Debit?": ["Yes"] * 40 + ["No"] * 20,
            "Avg Bal": [500.0 + i * 200 for i in range(n)],
            "Account Holder Age": [25 + i % 50 for i in range(n)],
            # Mailer columns for A9.10
            "Apr24 Mail": ["NU"] * 20 + [None] * 40,
            "Apr24 Resp": ["NU 5+"] * 10 + [None] * 50,
            # Spend column for A9.11
            "Apr24 Spend": [300.0 + i * 30 for i in range(n)],
        }
    )


@pytest.fixture
def attrition_ctx(attrition_df, tmp_output_dir):
    """PipelineContext with attrition data and fee config."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    return PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2024.02",
            eligible_stat_codes=["O"],
            eligible_prod_codes=["DDA", "SAV"],
            nsf_od_fee=35.0,
            ic_rate=0.0015,
        ),
        paths=paths,
        data=attrition_df,
        start_date=date(2023, 3, 1),
        end_date=date(2024, 2, 28),
    )


# -- Insights fixtures -------------------------------------------------------


@pytest.fixture
def insights_ctx(tmp_output_dir):
    """PipelineContext with pre-populated upstream results for insights modules."""
    paths = OutputPaths(
        base_dir=tmp_output_dir,
        charts_dir=tmp_output_dir / "charts",
        excel_dir=tmp_output_dir,
        pptx_dir=tmp_output_dir,
    )
    ctx = PipelineContext(
        client=ClientInfo(
            client_id="1200",
            client_name="Test CU",
            month="2024.02",
            eligible_stat_codes=["O"],
            eligible_prod_codes=["DDA", "SAV"],
            nsf_od_fee=35.0,
            ic_rate=0.0015,
            reg_e_opt_in=["Y"],
            reg_e_column="Reg E Code 2024.02",
        ),
        paths=paths,
        start_date=date(2023, 3, 1),
        end_date=date(2024, 2, 28),
    )
    # Pre-populate upstream module results
    ctx.results["value_1"] = {
        "delta": 85.50,
        "accts_with": 1200,
        "accts_without": 800,
        "rev_per_with": 142.30,
        "rev_per_without": 56.80,
        "hist_dctr": 0.60,
        "l12m_dctr": 0.65,
        "pot_hist": 41040.0,
        "pot_l12m": 44460.0,
        "pot_100": 68400.0,
    }
    ctx.results["value_2"] = {
        "delta": 45.20,
        "accts_with": 900,
        "accts_without": 300,
        "rev_per_with": 98.50,
        "rev_per_without": 53.30,
        "hist_rege": 0.75,
        "l12m_rege": 0.78,
        "pot_hist": 10170.0,
        "pot_l12m": 10576.80,
        "pot_100": 13560.0,
    }
    ctx.results["attrition_1"] = {
        "overall_rate": 0.12,
        "l12m_rate": 0.10,
        "total": 2000,
        "closed": 240,
    }
    ctx.results["attrition_9"] = {"retention_lift": 0.035}
    ctx.results["attrition_10"] = {"lift": 0.025}
    ctx.results["attrition_11"] = {"total_lost": 18500.0, "avg_lost": 77.08}
    ctx.results["attrition_12"] = {"total_l12m": 240, "trend": "stable"}
    ctx.results["dctr_1"] = {
        "insights": {
            "overall_dctr": 0.60,
            "recent_dctr": 0.65,
            "total_accounts": 2000,
        },
    }
    ctx.results["dctr_3"] = {
        "insights": {"dctr": 0.65, "total_accounts": 2000},
    }
    ctx.results["dctr_9"] = {
        "all": {
            "total_branches": 5,
            "best_branch": "Downtown",
            "best_dctr": 0.78,
            "worst_branch": "Rural",
            "worst_dctr": 0.42,
        },
    }
    ctx.results["reg_e_1"] = {
        "opt_in_rate": 0.75,
        "l12m_rate": 0.78,
        "total_base": 1200,
        "opted_in": 900,
        "opted_out": 300,
    }
    ctx.results["market_reach"] = {
        "n_eligible": 1500,
        "n_responders": 350,
        "n_mailed": 800,
        "penetration": 23.3,
    }
    ctx.results["revenue_attribution"] = {
        "resp_ic": 4200.0,
        "non_ic": 2800.0,
        "incremental_total": 1400.0,
    }
    ctx.results["pre_post_delta"] = {
        "resp_pre": 420.0,
        "resp_post": 510.0,
        "resp_delta": 90.0,
        "non_pre": 380.0,
        "non_post": 395.0,
        "non_delta": 15.0,
    }
    ctx.results["a3"] = {
        "insights": {
            "total_accounts": 2500,
            "eligible_accounts": 2000,
            "eligibility_rate": 80.0,
        },
    }
    return ctx
