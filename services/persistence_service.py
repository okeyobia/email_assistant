from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessedEmail:
    account: str
    message_id: str
    processed_at: datetime


class ProcessedStore:
    """SQLite-backed store of processed Gmail message ids."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    account TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    PRIMARY KEY (account, message_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processed_account
                ON processed_emails(account)
                """
            )

    def is_processed(self, account: str, message_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_emails WHERE account=? AND message_id=?",
                (account, message_id),
            ).fetchone()
        return row is not None

    def mark_processed(self, account: str, message_id: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_emails(account, message_id, processed_at)
                VALUES (?, ?, ?)
                """,
                (account, message_id, timestamp),
            )
        LOGGER.debug("Recorded %s for account %s", message_id, account)

    def recent_entries(self, limit: int = 10) -> list[ProcessedEmail]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT account, message_id, processed_at FROM processed_emails ORDER BY processed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ProcessedEmail(row[0], row[1], datetime.fromisoformat(row[2])) for row in rows]
