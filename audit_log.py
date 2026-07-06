import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
DB_PATH = LOG_DIR / "submissions.db"
APPEALS_PATH = LOG_DIR / "appeals.jsonl"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS submissions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id              TEXT NOT NULL UNIQUE,
    creator_id              TEXT NOT NULL,
    submitted_at            TEXT NOT NULL,
    text                    TEXT NOT NULL,
    label                   TEXT NOT NULL,
    confidence              REAL NOT NULL,
    note                    TEXT,
    message                 TEXT,
    llm_score               REAL NOT NULL,
    llm_reasoning           TEXT NOT NULL,
    stylometric_score       REAL NOT NULL,
    stylometric_explanation TEXT NOT NULL,
    status                  TEXT NOT NULL
)
"""


def _get_connection() -> sqlite3.Connection:
    """Opens a connection to submissions.db, creating the table if needed."""
    LOG_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def _row_to_entry(row: sqlite3.Row) -> dict:
    """Reshapes a submissions row back into the entry dict shape app.py expects."""
    return {
        "content_id": row["content_id"],
        "creator_id": row["creator_id"],
        "submitted_at": row["submitted_at"],
        "text": row["text"],
        "label": row["label"],
        "confidence": float(row["confidence"]),
        "note": row["note"],
        "message": row["message"],
        "llm_score": float(row["llm_score"]),
        "llm_reasoning": row["llm_reasoning"],
        "stylometric_score": float(row["stylometric_score"]),
        "stylometric_explanation": row["stylometric_explanation"],
        "status": row["status"],
    }


def log_entry(entry: dict) -> None:
    """Inserts one structured entry into the submissions table."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO submissions
                (content_id, creator_id, submitted_at, text, label, confidence, note, message,
                 llm_score, llm_reasoning, stylometric_score, stylometric_explanation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["content_id"],
                entry["creator_id"],
                entry["submitted_at"],
                entry["text"],
                entry["label"],
                entry["confidence"],
                entry.get("note"),
                entry.get("message"),
                entry["llm_score"],
                entry["llm_reasoning"],
                entry["stylometric_score"],
                entry["stylometric_explanation"],
                entry["status"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _read_appeals() -> list:
    if not APPEALS_PATH.exists():
        return []
    with APPEALS_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_submission(content_id: str) -> dict | None:
    """Returns the stored submission entry for `content_id`, or None if unknown."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM submissions WHERE content_id = ?", (content_id,)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_entry(row) if row is not None else None


def update_status(content_id: str, status: str) -> bool:
    """Flips the stored `status` for `content_id`. Returns False if the id is unknown."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE submissions SET status = ? WHERE content_id = ?",
            (status, content_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_appeal(content_id: str) -> dict | None:
    """Returns the appeal already filed for `content_id`, or None if none exists."""
    for appeal in _read_appeals():
        if appeal.get("content_id") == content_id:
            return appeal
    return None


def file_appeal(content_id: str, reasoning: str) -> dict:
    """Appends {content_id, reasoning, filed_at} to appeals.jsonl and returns it.

    Does not touch submissions.db -- the original score and label are left
    untouched, per planning.md's appeals workflow.
    """
    appeal = {
        "content_id": content_id,
        "reasoning": reasoning,
        "filed_at": datetime.now(timezone.utc).isoformat(),
    }
    LOG_DIR.mkdir(exist_ok=True)
    with APPEALS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(appeal) + "\n")
    return appeal


def get_log(limit: int = 50, status: str | None = None, label: str | None = None) -> list:
    """Returns submissions newest-first, optionally filtered by `status`/`label`."""
    query = "SELECT * FROM submissions WHERE 1=1"
    params: list = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if label is not None:
        query += " AND label = ?"
        params.append(label)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    conn = _get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [_row_to_entry(row) for row in rows]
