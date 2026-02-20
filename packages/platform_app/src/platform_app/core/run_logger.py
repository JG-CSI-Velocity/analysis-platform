"""Run history logger -- tracks all pipeline executions.

Stored as JSON Lines in logs/run_history.jsonl for append-only writes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LOG_DIR = Path("logs")


@dataclass(frozen=True)
class RunRecord:
    """Single pipeline execution record."""

    run_id: str
    timestamp: str
    csm: str
    client_id: str
    client_name: str
    pipeline: str
    modules_run: list[str]
    runtime_seconds: float
    status: str  # "success", "partial", "error"
    output_dir: str
    input_file_hash: str = ""
    error_message: str = ""
    result_count: int = 0


def generate_run_id() -> str:
    """Generate a short unique run ID."""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def hash_file(path: Path) -> str:
    """SHA-256 hash of a file (first 16 hex chars)."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def log_run(record: RunRecord, log_dir: Path = DEFAULT_LOG_DIR) -> Path:
    """Append a run record to the history file. Returns log file path."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_history.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(asdict(record), default=str) + "\n")

    logger.info("Run %s logged to %s", record.run_id, log_file)
    return log_file


def load_history(log_dir: Path = DEFAULT_LOG_DIR, limit: int = 100) -> list[RunRecord]:
    """Load recent run records (newest first)."""
    log_file = log_dir / "run_history.jsonl"
    if not log_file.exists():
        return []

    records: list[RunRecord] = []
    for line in log_file.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            # Handle modules_run as list
            if isinstance(data.get("modules_run"), str):
                data["modules_run"] = [data["modules_run"]]
            records.append(RunRecord(**data))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Skipping malformed log line: %s", e)

    # Newest first, limited
    return list(reversed(records[-limit:]))
