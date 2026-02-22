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
GENERIC_ENV_VAR = "CLIENT_CONFIG_PATH"

# Default M drive paths (platform-dependent)
_DEFAULT_PATHS = (
    [
        Path(r"M:\ICS\Config\clients_config.json"),
        Path(r"M:\Config\clients_config.json"),
    ]
    if platform.system() == "Windows"
    else [
        Path("/Volumes/M/ICS/Config/clients_config.json"),
        Path("/Volumes/M/Config/clients_config.json"),
    ]
)

# ARS-style key -> canonical snake_case key
_ARS_KEY_MAP: dict[str, str] = {
    "BranchMapping": "branch_mapping",
    "ICRate": "interchange_rate",
    "NSF_OD_Fee": "nsf_od_fee",
}


class MasterClientConfig(BaseModel):
    """Full per-client config from the master file.

    Preserves extra fields (e.g. ARS-only keys) via extra="allow" so they
    can be retrieved from model_extra by downstream consumers.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    client_name: str | None = None
    open_stat_codes: list[str] | None = None
    closed_stat_codes: list[str] | None = None
    interchange_rate: float | None = None
    branch_mapping: dict[str, str] | None = None
    prod_code_mapping: dict[str, str] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_ars_keys(cls, data: Any) -> Any:
        """Map ARS-style PascalCase keys to snake_case.

        Uses copy (not pop) so the original ARS keys remain available
        in model_extra for downstream consumers like the ARS runner.
        """
        if not isinstance(data, dict):
            return data
        for ars_key, canon_key in _ARS_KEY_MAP.items():
            if ars_key in data and canon_key not in data:
                data[canon_key] = data[ars_key]
        return data


def resolve_master_config_path(explicit_path: Path | None = None) -> Path | None:
    """Resolve master config path with priority chain:

    1. explicit_path argument
    2. ICS_CLIENT_CONFIG env var
    3. CLIENT_CONFIG_PATH env var (generic)
    4. Default M drive paths
    5. Repo-local config/clients_config.json (walk up from CWD)

    Returns None if no file found (graceful degradation).
    """
    # 1. Explicit path from config.yaml client_config_path
    if explicit_path is not None:
        p = Path(explicit_path).expanduser().resolve()
        if p.exists():
            return p
        logger.warning("client_config_path not found: %s", p)
        return None

    # 2. ICS-specific environment variable
    env_path = os.environ.get(ENV_VAR_NAME)
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists():
            return p
        logger.warning("%s set but file not found: %s", ENV_VAR_NAME, p)
        return None

    # 3. Generic environment variable
    generic_env = os.environ.get(GENERIC_ENV_VAR)
    if generic_env:
        p = Path(generic_env).expanduser().resolve()
        if p.exists():
            return p
        logger.warning("%s set but file not found: %s", GENERIC_ENV_VAR, p)
        return None

    # 4. Default M drive paths
    for default_path in _DEFAULT_PATHS:
        if default_path.exists():
            return default_path

    # 5. Walk up from CWD to find config/clients_config.json
    try:
        current = Path.cwd().resolve()
        for _ in range(6):  # max 6 levels up
            candidate = current / "config" / "clients_config.json"
            if candidate.exists():
                return candidate
            parent = current.parent
            if parent == current:
                break
            current = parent
    except OSError:
        pass

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


def load_raw_client_entry(path: Path, client_id: str) -> dict:
    """Load a single client's raw dict from a master JSON/YAML config.

    Returns the raw dict (no Pydantic validation) for use by runners
    that need the original PascalCase keys. Returns empty dict on errors.
    """
    suffix = path.suffix.lower()
    try:
        with open(path) as f:
            if suffix == ".json":
                raw = json.load(f)
            elif suffix in (".yaml", ".yml"):
                raw = yaml.safe_load(f) or {}
            else:
                return {}
    except (json.JSONDecodeError, yaml.YAMLError, OSError):
        return {}

    if not isinstance(raw, dict):
        return {}

    cid = str(client_id).strip()
    entry = raw.get(cid) or raw.get(int(cid) if cid.isdigit() else cid)
    if isinstance(entry, dict):
        return entry
    return {}
