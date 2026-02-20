"""Tests for referral settings models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ics_toolkit.settings import (
    ReferralScoringWeights,
    ReferralSettings,
    ReferralStaffWeights,
    Settings,
)


class TestReferralScoringWeights:
    """Tests for influence score weight validation."""

    def test_defaults_sum_to_one(self):
        w = ReferralScoringWeights()
        total = w.unique_accounts + w.burst_count + w.channels_used + w.velocity + w.longevity
        assert abs(total - 1.0) < 1e-6

    def test_accepts_valid_custom_weights(self):
        w = ReferralScoringWeights(
            unique_accounts=0.50,
            burst_count=0.20,
            channels_used=0.10,
            velocity=0.10,
            longevity=0.10,
        )
        assert w.unique_accounts == 0.50

    def test_rejects_weights_not_summing_to_one(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            ReferralScoringWeights(
                unique_accounts=0.50,
                burst_count=0.50,
                channels_used=0.50,
                velocity=0.10,
                longevity=0.10,
            )

    def test_frozen(self):
        w = ReferralScoringWeights()
        with pytest.raises(ValidationError):
            w.unique_accounts = 0.99

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ReferralScoringWeights(unknown_field=0.5)


class TestReferralStaffWeights:
    """Tests for staff multiplier weight validation."""

    def test_defaults_sum_to_one(self):
        w = ReferralStaffWeights()
        total = w.avg_referrer_score + w.unique_referrers
        assert abs(total - 1.0) < 1e-6

    def test_rejects_bad_sum(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            ReferralStaffWeights(avg_referrer_score=0.50, unique_referrers=0.60)


class TestReferralSettings:
    """Tests for the referral settings model."""

    def test_defaults(self):
        s = ReferralSettings()
        assert s.data_file is None
        assert s.burst_window_days == 14
        assert s.dormancy_days == 180
        assert s.top_n_referrers == 25
        assert s.header_row == 0

    def test_validates_data_file_exists(self, tmp_path):
        path = tmp_path / "exists.xlsx"
        path.touch()
        s = ReferralSettings(data_file=path)
        assert s.data_file == path

    def test_rejects_missing_file(self, tmp_path):
        path = tmp_path / "nope.xlsx"
        with pytest.raises(ValidationError, match="not found"):
            ReferralSettings(data_file=path)

    def test_rejects_unsupported_format(self, tmp_path):
        path = tmp_path / "bad.json"
        path.touch()
        with pytest.raises(ValidationError, match="Unsupported file type"):
            ReferralSettings(data_file=path)

    def test_derives_client_id_from_filename(self, tmp_path):
        path = tmp_path / "1776_referral.xlsx"
        path.touch()
        s = ReferralSettings(data_file=path)
        assert s.client_id == "1776"
        assert s.client_name == "Client 1776"

    def test_client_id_unknown_for_non_numeric(self, tmp_path):
        path = tmp_path / "referral_data.xlsx"
        path.touch()
        s = ReferralSettings(data_file=path)
        assert s.client_id == "unknown"

    def test_code_prefix_map_defaults(self):
        s = ReferralSettings()
        assert "150A" in s.code_prefix_map
        assert s.code_prefix_map["150A"] == "BRANCH_STANDARD"
        assert s.code_prefix_map["PC"] == "DIGITAL_PROCESS"

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ReferralSettings(bogus_field=True)


class TestSettingsIntegration:
    """Tests for referral settings within the unified Settings model."""

    def test_settings_has_referral_key(self):
        s = Settings()
        assert isinstance(s.referral, ReferralSettings)

    def test_for_referral_factory(self, tmp_path):
        path = tmp_path / "1776_test.xlsx"
        path.touch()
        s = Settings.for_referral(data_file=path)
        assert s.referral.data_file == path
        assert s.referral.client_id == "1776"

    def test_from_yaml_with_referral(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.write_text("referral:\n  burst_window_days: 21\n  top_n_referrers: 10\n")
        s = Settings.from_yaml(config_path=config)
        assert s.referral.burst_window_days == 21
        assert s.referral.top_n_referrers == 10

    def test_existing_settings_unaffected(self):
        s = Settings()
        assert hasattr(s, "append")
        assert hasattr(s, "analysis")
        assert hasattr(s, "referral")
