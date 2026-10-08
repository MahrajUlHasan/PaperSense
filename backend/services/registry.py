"""SQLite registry: uploaded documents (status, stats, scores) and research context per workspace."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    progress TEXT,
    error TEXT,
    mode TEXT,
    page_count INTEGER,
    stats TEXT,
    score INTEGER,
    score_explanation TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents(workspace_id);
CREATE TABLE IF NOT EXISTS research (
    workspace_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT NOT NULL,
    breakdown TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_UPDATABLE = {"status", "progress", "error", "mode", "page_count", "stats", "score", "score_explanation"}
_UNFINISHED = ("queued", "parsing", "enriching", "embedding")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    if data.get("stats"):
        data["stats"] = json.loads(data["stats"])
    return data


class DocumentRegistry:
    def __init__(self, db_path: str | Path | None = None):
        path = Path(db_path) if db_path else Path(settings.data_dir) / "registry.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def create(self, document_id: str, workspace_id: str, filename: str) -> dict:
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO documents (id, workspace_id, filename, status, progress, created_at, updated_at) "
                "VALUES (?, ?, ?, 'queued', 'Waiting to start', ?, ?)",
                (document_id, workspace_id, filename, now, now),
            )
            self._conn.commit()
        return self.get(document_id)

    def update(self, document_id: str, **fields) -> None:
        """Change some columns of a document.

        Only the columns in _UPDATABLE are accepted, so column names never come from
        outside and the generated SQL stays safe.
        """
        unknown = set(fields) - _UPDATABLE
        if unknown:
            raise ValueError(f"Cannot update columns: {sorted(unknown)}")
        if "stats" in fields and fields["stats"] is not None and not isinstance(fields["stats"], str):
            fields["stats"] = json.dumps(fields["stats"])
        assignments = ", ".join(f"{column} = ?" for column in fields)
        with self._lock:
            self._conn.execute(
                f"UPDATE documents SET {assignments}, updated_at = ? WHERE id = ?",
                (*fields.values(), _now(), document_id),
            )
            self._conn.commit()

    def get(self, document_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return _to_dict(row)

    def list(self, workspace_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM documents WHERE workspace_id = ? ORDER BY created_at", (workspace_id,)
            ).fetchall()
        return [_to_dict(r) for r in rows]

    def delete(self, document_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            self._conn.commit()

    def fail_interrupted(self) -> int:
        """Called on startup: jobs that were running when the server stopped can't resume."""
        placeholders = ", ".join("?" for _ in _UNFINISHED)
        with self._lock:
            cursor = self._conn.execute(
                f"UPDATE documents SET status = 'error', progress = 'Failed', "
                f"error = 'Processing was interrupted by a server restart. Please upload again.', "
                f"updated_at = ? WHERE status IN ({placeholders})",
                (_now(), *_UNFINISHED),
            )
            self._conn.commit()
            return cursor.rowcount

    def set_research(self, workspace_id: str, topic: str, description: str, breakdown: str) -> dict:
        with self._lock:
            self._conn.execute(
                "INSERT INTO research (workspace_id, topic, description, breakdown, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(workspace_id) DO UPDATE SET "
                "topic = excluded.topic, description = excluded.description, "
                "breakdown = excluded.breakdown, updated_at = excluded.updated_at",
                (workspace_id, topic, description, breakdown, _now()),
            )
            self._conn.commit()
        return self.get_research(workspace_id)

    def get_research(self, workspace_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM research WHERE workspace_id = ?", (workspace_id,)).fetchone()
        return dict(row) if row else None
