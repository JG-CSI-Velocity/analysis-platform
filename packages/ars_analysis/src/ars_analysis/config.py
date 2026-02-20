"""Pydantic settings for the ARS pipeline -- JSON config files."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class PathsConfig(BaseModel):
    """File system paths for the pipeline.

    All derived paths resolve from ars_base, matching the production
    M: drive layout from the original ars_config.py.
    """

    ars_base: Path

    # Derived directories (defaults match M:\\ARS structure)
    watch_root: Path = Path("Ready for Analysis")
    incoming_dir: Path = Path("Incoming")
    retrieve_dir: Path = Path("Incoming/ODDD Files")
    presentations_dir: Path = Path("Presentations/Presentation Excels")
    archive_dir: Path = Path("Presentations/Presentation Excels/Archive")
    config_dir: Path = Path("Scripts/Config")
    log_dir: Path = Path("Logs")

    # Template can be absolute or relative to ars_base
    template_path: Path = Path("Presentations/Template12.25.pptx")

    # Run tracker for history
    tracker_path: Path = Path("Config/run_tracker.json")

    @model_validator(mode="after")
    def _resolve_relative_paths(self) -> "PathsConfig":
        """Resolve relative paths against ars_base."""
        base = self.ars_base
        for field_name in (
            "watch_root",
            "incoming_dir",
            "retrieve_dir",
            "presentations_dir",
            "archive_dir",
            "config_dir",
            "log_dir",
            "template_path",
            "tracker_path",
        ):
            val = getattr(self, field_name)
            if not val.is_absolute():
                object.__setattr__(self, field_name, base / val)
        return self


class CSMSourcesConfig(BaseModel):
    """CSM M: drive source folders for ODD retrieval."""

    sources: dict[str, Path] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Pipeline behavior settings."""

    skip_pptx: bool = False
    skip_excel_archive: bool = False
    chart_dpi: int = Field(default=150, ge=72, le=600)
    max_workers: int = Field(default=1, ge=1, le=16)
    use_local_temp: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: Path = Path("logs")
    rotation: str = "10 MB"
    retention_days: int = Field(default=30, ge=1)


class ReviewScheduleConfig(BaseModel):
    """Review scheduling defaults."""

    default_cadence: Literal[
        "monthly", "bimonthly", "quarterly", "semiannual", "annual", "ad-hoc"
    ] = "monthly"
    review_day: int = Field(default=15, ge=1, le=28)


class ARSSettings(BaseSettings):
    """Main settings, loaded from JSON config files + environment variables."""

    model_config = SettingsConfigDict(
        json_file=["configs/ars_config.default.json", "ars_config.json"],
        env_prefix="ARS_",
        env_nested_delimiter="__",
    )

    paths: PathsConfig
    pipeline: PipelineConfig = PipelineConfig()
    logging: LoggingConfig = LoggingConfig()
    review_schedule: ReviewScheduleConfig = ReviewScheduleConfig()
    csm_sources: CSMSourcesConfig = CSMSourcesConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            JsonConfigSettingsSource(settings_cls),
        )


# ---------------------------------------------------------------------------
# Config migration -- merge old clients_config.json into the new location
# ---------------------------------------------------------------------------


def migrate_config(old_path: str | Path, target_path: str | Path | None = None) -> dict:
    """Merge an old clients_config.json into the canonical location.

    Existing entries in the target are preserved. Old entries that don't
    exist yet are added. For entries present in both files, the old file's
    ICRate, NSF_OD_Fee, and BranchMapping win (these are manually-entered
    fields that would be empty in a freshly-parsed config).

    Returns the merged config dict.
    """
    old_path = Path(old_path)
    if not old_path.exists():
        raise FileNotFoundError(f"Old config not found: {old_path}")

    with open(old_path, encoding="utf-8") as f:
        old_cfg = json.load(f)

    # Resolve target: explicit path > default location
    if target_path:
        dest = Path(target_path)
    else:
        dest = Path("configs/clients_config.json")

    if dest.exists():
        with open(dest, encoding="utf-8") as f:
            new_cfg = json.load(f)
    else:
        new_cfg = {}

    added = 0
    enriched = 0
    for cid, old_entry in old_cfg.items():
        if cid not in new_cfg:
            new_cfg[cid] = old_entry
            added += 1
        else:
            for key in ("ICRate", "NSF_OD_Fee", "BranchMapping"):
                old_val = old_entry.get(key)
                new_val = new_cfg[cid].get(key)
                if old_val and not new_val:
                    new_cfg[cid][key] = old_val
                    enriched += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, indent=4)

    return {"added": added, "enriched": enriched, "total": len(new_cfg), "path": str(dest)}
