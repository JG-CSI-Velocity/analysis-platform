"""Client registry: load per-client config from a master YAML/JSON file."""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)

ENV_VAR_NAME = "ICS_CLIENT_CONFIG"

# Default M drive paths (platform-dependent)
_DEFAULT_PATHS = (
    [Path(r"M:\ICS\Config\clients_config.json")]
    if platform.system() == "Windows"
    else [Path("/Volumes/M/ICS/Config/clients_config.json")]
)

# ARS-style key -> canonical snake_case key
_ARS_KEY_MAP: dict[str, str] = {
    "BranchMapping": "branch_mapping",
    "ICRate": "interchange_rate",
    "NSF_OD_Fee": "nsf_od_fee",
}


class MasterClientConfig(BaseModel):
    """Full per-client config from the master file.

    Tolerates extra fields (e.g. ARS-only keys) via extra="ignore".
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    client_name: str | None = None
    open_stat_codes: list[str] | None = None
    closed_stat_codes: list[str] | None = None
    interchange_rate: float | None = None
    branch_mapping: dict[str, str] | None = None
    prod_code_mapping: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_ars_keys(cls, data: Any) -> Any:
        """Map ARS-style PascalCase keys to snake_case."""
        if not isinstance(data, dict):
            return data
        for ars_key, canon_key in _ARS_KEY_MAP.items():
            if ars_key in data and canon_key not in data:
                data[canon_key] = data.pop(ars_key)
        return data


def resolve_master_config_path(explicit_path: Path | None = None) -> Path | None:
    """Resolve master config path: explicit > env var > default M drive.

    Returns None if no file found (graceful degradation).
    """
    # 1. Explicit path from config.yaml client_config_path
    if explicit_path is not None:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists():
            return p
        logger.warning("client_config_path not found: %s", p)
        return None

    # 2. Environment variable
    env_path = os.environ.get(ENV_VAR_NAME)
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists():
            return p
        logger.warning("%s set but file not found: %s", ENV_VAR_NAME, p)
        return None

    # 3. Default paths
    for default_path in _DEFAULT_PATHS:
        if default_path.exists():
            return default_path

    return None


def load_master_config(path: Path) -> dict[str, MasterClientConfig]:
    """Load and parse master config file (JSON or YAML).

    Returns dict of client_id -> MasterClientConfig.
    Returns empty dict on parse errors (never raises).
    """
    suffix = path.suffix.lower()
    try:
        with open(path) as f:
            if suffix == ".json":
                raw = json.load(f)
            elif suffix in (".yaml", ".yml"):
                raw = yaml.safe_load(f) or {}
            else:
                logger.error("Unsupported master config format: %s", suffix)
                return {}
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error("Failed to parse master config %s: %s", path, e)
        return {}

    if not isinstance(raw, dict):
        logger.error("Master config must be a dict, got %s", type(raw).__name__)
        return {}

    registry: dict[str, MasterClientConfig] = {}
    for client_id, entry in raw.items():
        cid = str(client_id).strip()
        if not isinstance(entry, dict):
            logger.warning("Skipping client %s: entry is not a dict", cid)
            continue
        try:
            registry[cid] = MasterClientConfig(**entry)
        except Exception as e:
            logger.warning("Skipping client %s: %s", cid, e)

    logger.info("Loaded master config: %d clients from %s", len(registry), path)
    return registry


def get_client_config(
    client_id: str,
    registry: dict[str, MasterClientConfig],
) -> MasterClientConfig | None:
    """Look up a client in the registry. Returns None if not found."""
    cfg = registry.get(client_id.strip())
    if cfg is None:
        logger.info("Client %s not in master config; using defaults", client_id)
    return cfg
