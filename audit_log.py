import json
from pathlib import Path

LOG_PATH = Path(__file__).parent / "logs" / "audit_log.jsonl"


def log_entry(entry: dict) -> None:
    """Appends one structured entry to the audit log."""
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_log(limit: int = 50) -> list:
    """Returns the most recent audit log entries, newest first."""
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    return list(reversed(entries))[:limit]
