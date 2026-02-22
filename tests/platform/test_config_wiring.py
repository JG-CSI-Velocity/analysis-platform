"""Tests for config wiring through orchestrator to ARS and ICS runners."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.context import PipelineContext


class TestArsRunnerReceivesConfig:
    """ARS runner._load_client_config() handles master format."""

    def test_load_client_config_extracts_entry(self, tmp_path):
        from ars_analysis.runner import _load_client_config

        data = {
            "1759": {"EligibleStatusCodes": ["O", "A"], "ICRate": 0.019},
            "1776": {"EligibleStatusCodes": ["O"]},
        }
        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps(data))

        result = _load_client_config(
            {"config_path": str(config_file), "client_id": "1759"}
        )
        assert result["EligibleStatusCodes"] == ["O", "A"]
        assert result["ICRate"] == 0.019

    def test_load_client_config_missing_client_fallback(self, tmp_path):
        from ars_analysis.runner import _load_client_config

        data = {
            "1776": {"EligibleStatusCodes": ["O"]},
            "1800": {"EligibleStatusCodes": ["A"]},
        }
        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps(data))

        result = _load_client_config(
            {"config_path": str(config_file), "client_id": "9999"}
        )
        # With 2+ clients and no match, falls back to raw_config
        assert result.get("config_path") == str(config_file)

    def test_no_config_path_returns_raw(self, monkeypatch):
        from ars_analysis.runner import _load_client_config

        # Mock away the fallback resolver so it doesn't find local config
        monkeypatch.setattr(
            "ars_analysis.runner._resolve_config_fallback", lambda: None
        )
        raw = {"client_id": "1759", "some_key": "val"}
        result = _load_client_config(raw)
        assert result == raw


class TestIcsRunnerForwardsConfig:
    """ICS runner passes config_path from ctx.client_config to Settings."""

    def test_config_path_forwarded(self, tmp_path):
        """Verify that config_path from client_config ends up in Settings kwargs."""
        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps({"1759": {"open_stat_codes": ["O"]}}))

        data_file = tmp_path / "test_data.xlsx"
        data_file.write_bytes(b"")

        ctx = PipelineContext(
            client_id="1759",
            input_files={"ics": data_file},
            output_dir=tmp_path / "out",
            client_config={"config_path": str(config_file)},
        )

        captured_kwargs: dict = {}

        def fake_for_analysis(data_file, **kwargs):
            captured_kwargs.update(kwargs)
            raise RuntimeError("stop early")

        with patch("ics_toolkit.settings.Settings.for_analysis", side_effect=fake_for_analysis):
            with pytest.raises(RuntimeError, match="stop early"):
                from ics_toolkit.runner import run_ics

                run_ics(ctx)

        assert "client_config_path" in captured_kwargs
        assert captured_kwargs["client_config_path"] == str(config_file)

    def test_no_config_path_omitted(self, tmp_path):
        """Without config_path, client_config_path is not passed."""
        data_file = tmp_path / "test_data.xlsx"
        data_file.write_bytes(b"")

        ctx = PipelineContext(
            client_id="1759",
            input_files={"ics": data_file},
            output_dir=tmp_path / "out",
            client_config={},
        )

        captured_kwargs: dict = {}

        def fake_for_analysis(data_file, **kwargs):
            captured_kwargs.update(kwargs)
            raise RuntimeError("stop early")

        with patch("ics_toolkit.settings.Settings.for_analysis", side_effect=fake_for_analysis):
            with pytest.raises(RuntimeError, match="stop early"):
                from ics_toolkit.runner import run_ics

                run_ics(ctx)

        assert "client_config_path" not in captured_kwargs


class TestOrchestratorPassesConfig:
    """Orchestrator run_pipeline() passes client_config to PipelineContext."""

    def test_client_config_reaches_context(self, tmp_path):
        """Verify client_config flows through orchestrator to PipelineContext."""
        from platform_app.orchestrator import run_pipeline

        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps({"1759": {"ICRate": 0.019}}))

        captured_ctx = {}

        def fake_run_ars(ctx):
            captured_ctx["client_config"] = ctx.client_config
            return {}

        with patch("ars_analysis.runner.run_ars", fake_run_ars, create=True):
            run_pipeline(
                "ars",
                input_files={"oddd": tmp_path / "test.xlsx"},
                output_dir=tmp_path / "out",
                client_id="1759",
                client_config={"config_path": str(config_file), "client_id": "1759"},
            )

        assert captured_ctx["client_config"]["config_path"] == str(config_file)
        assert captured_ctx["client_config"]["client_id"] == "1759"


class TestArsCliMasterFormat:
    """ARS CLI _load_client_info detects master format."""

    def test_master_format_detected(self, tmp_path):
        from ars_analysis.cli import _load_client_info

        data = {
            "1759": {
                "ClientName": "Connex CU",
                "EligibleStatusCodes": ["O", "A"],
                "ICRate": "0.019",
                "NSF_OD_Fee": "25",
                "RegEOptInCode": ["Y"],
            }
        }
        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps(data))

        file_path = tmp_path / "1759_Connex CU_2026.02.xlsx"
        file_path.write_bytes(b"")

        info = _load_client_info(str(config_file), file_path)
        assert info.client_id == "1759"
        assert info.client_name == "Connex CU"
        assert info.eligible_stat_codes == ["O", "A"]
        assert info.ic_rate == 0.019
        assert info.nsf_od_fee == 25.0
        assert info.reg_e_opt_in == ["Y"]

    def test_master_format_missing_client(self, tmp_path):
        from ars_analysis.cli import _load_client_info

        data = {"1776": {"ClientName": "Liberty CU"}}
        config_file = tmp_path / "clients.json"
        config_file.write_text(json.dumps(data))

        file_path = tmp_path / "9999_Unknown_2026.01.xlsx"
        file_path.write_bytes(b"")

        info = _load_client_info(str(config_file), file_path)
        assert info.client_id == "9999"
        assert info.client_name == "Unknown"

    def test_single_client_flat_format(self, tmp_path):
        from ars_analysis.cli import _load_client_info

        data = {
            "client_id": "1759",
            "client_name": "Connex CU",
            "eligible_stat_codes": ["O"],
            "ic_rate": 0.019,
        }
        config_file = tmp_path / "client.json"
        config_file.write_text(json.dumps(data))

        file_path = tmp_path / "1759_Connex CU_2026.02.xlsx"
        file_path.write_bytes(b"")

        info = _load_client_info(str(config_file), file_path)
        assert info.client_id == "1759"
        assert info.eligible_stat_codes == ["O"]
        assert info.ic_rate == 0.019

    def test_auto_resolve_config(self, tmp_path, monkeypatch):
        """CLI auto-resolves config when --config not passed."""
        from ars_analysis.cli import _load_client_info

        data = {"1759": {"ClientName": "Connex CU", "EligibleStatusCodes": ["O"]}}
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "clients_config.json"
        config_file.write_text(json.dumps(data))

        monkeypatch.delenv("ICS_CLIENT_CONFIG", raising=False)
        monkeypatch.delenv("CLIENT_CONFIG_PATH", raising=False)
        monkeypatch.chdir(tmp_path)

        file_path = tmp_path / "1759_Connex CU_2026.02.xlsx"
        file_path.write_bytes(b"")

        info = _load_client_info(None, file_path)
        assert info.client_name == "Connex CU"
        assert info.eligible_stat_codes == ["O"]
