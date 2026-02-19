"""
ars_config.py
-------------
Centralized path configuration for the ARS pipeline.

All paths resolve from ARS_BASE (default: M:\\ARS).
Override via:
  1. ARS_BASE environment variable
  2. ars_config.toml file in the project root (gitignored, for dev/testing)
  3. Falls back to M:\\ARS (the shared network folder)
"""

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent

_DEFAULT_BASE = Path(r"M:\ARS")


def _get_base() -> Path:
    """Resolve ARS base path: env var > local toml > default."""
    # 1. Environment variable
    env_base = os.environ.get("ARS_BASE")
    if env_base:
        return Path(env_base)

    # 2. Local config file (for dev/testing on non-Windows machines)
    local_cfg = _PROJECT_ROOT / "ars_config.toml"
    if local_cfg.is_file():
        import tomllib

        with open(local_cfg, "rb") as f:
            data = tomllib.load(f)
        base = data.get("paths", {}).get("ars_base")
        if base:
            return Path(base)

    # 3. Default shared folder
    return _DEFAULT_BASE


ARS_BASE = _get_base()

# ---------------------------------------------------------------------------
# Derived paths — everything resolves from ARS_BASE
# ---------------------------------------------------------------------------

WATCH_ROOT = ARS_BASE / "Input"
CONFIG_PATH = ARS_BASE / "Config" / "clients_config.json"
TRACKER_PATH = ARS_BASE / "Config" / "run_tracker.json"
PRESENTATIONS_PATH = ARS_BASE / "Output"
ARCHIVE_PATH = ARS_BASE / "Output" / "Archive"
_NETWORK_TEMPLATE = ARS_BASE / "Presentations" / "Template12.25.pptx"
_BUNDLED_TEMPLATE = Path(__file__).resolve().parent / "templates" / "Template12.25.pptx"
TEMPLATE_PATH = _NETWORK_TEMPLATE if _NETWORK_TEMPLATE.exists() else _BUNDLED_TEMPLATE
LOG_DIR = ARS_BASE / "Logs"
TEST_REPORTS_DIR = ARS_BASE / "Test-Reports"

# ---------------------------------------------------------------------------
# CSM source folders (where raw ODD files land on M: drive)
# ---------------------------------------------------------------------------

CSM_SOURCES = {
    "JamesG": Path(r"M:\JamesG\OD Data Dumps"),
    "GMiller": Path(r"M:\GMiller\OD Data Dumps"),
    "Aburgard": Path(r"M:\Aburgard\ODDD"),
    "JBerkowitz": Path(r"M:\JBerkowitz\OD Data Dumps"),
    "DanWood": Path(r"M:\Dan Wood"),
}


# ---------------------------------------------------------------------------
# Config migration — merge old config file into the canonical location
# ---------------------------------------------------------------------------


def migrate_config(old_path: str | Path) -> dict:
    """Merge an old clients_config.json into CONFIG_PATH.

    Existing entries in CONFIG_PATH are preserved.  Old entries that
    don't exist yet are added.  For entries present in both files, the
    old file's ICRate, NSF_OD_Fee, and BranchMapping win (these are
    the manually-entered fields that would be empty in a freshly-parsed
    config).

    Returns the merged config dict.
    """
    import json

    old_path = Path(old_path)
    if not old_path.exists():
        raise FileNotFoundError(f"Old config not found: {old_path}")

    with open(old_path) as f:
        old_cfg = json.load(f)

    # Load current canonical config (or start empty)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
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
            # Merge manual fields from old into new
            for key in ("ICRate", "NSF_OD_Fee", "BranchMapping"):
                old_val = old_entry.get(key)
                new_val = new_cfg[cid].get(key)
                if old_val and not new_val:
                    new_cfg[cid][key] = old_val
                    enriched += 1

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(new_cfg, f, indent=4)

    print(f"Migration complete -> {CONFIG_PATH}")
    print(f"  {added} client(s) added from old config")
    print(f"  {enriched} field(s) enriched (ICRate/NSF_OD_Fee/BranchMapping)")
    print(f"  Total clients: {len(new_cfg)}")
    return new_cfg
