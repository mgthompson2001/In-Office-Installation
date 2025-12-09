#!/usr/bin/env python3
"""Retention helpers for full monitoring datasets."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

LOGGER = logging.getLogger(__name__)


class MonitoringRetentionManager:
    """Apply retention policies to the full monitoring store."""

    TABLES = (
        "screen_recordings",
        "keyboard_input",
        "mouse_activity",
        "application_usage",
        "file_activity",
    )

    def __init__(
        self,
        installation_dir: Path,
        *,
        retention_days: int = 7,
        max_database_gb: float = 2.0,
    ) -> None:
        self.installation_dir = Path(installation_dir)
        self.data_dir = self.installation_dir / "_secure_data" / "full_monitoring"
        self.session_media_dir = self.installation_dir / "_secure_data" / "session_media"
        self.db_path = self.data_dir / "full_monitoring.db"
        self.retention_days = max(1, retention_days)
        self.max_database_bytes = max_database_gb * (1024 ** 3)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def purge_session(self, session_id: str) -> None:
        if not self.db_path.exists():
            return
        LOGGER.info("Purging telemetry for session %s", session_id)
        with sqlite3.connect(self.db_path) as conn:
            for table in self.TABLES:
                conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.execute("VACUUM")

        session_media = self.session_media_dir / session_id
        if session_media.exists():
            shutil.rmtree(session_media, ignore_errors=True)

    def enforce(self) -> None:
        if not self.db_path.exists():
            return
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        stale_sessions = self._sessions_older_than(cutoff)
        for session_id in stale_sessions:
            self.purge_session(session_id)
        self._enforce_size_limit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _sessions_older_than(self, cutoff: datetime) -> Iterable[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, MAX(timestamp) AS last_seen
                FROM (
                    SELECT session_id, timestamp FROM screen_recordings
                    UNION ALL
                    SELECT session_id, timestamp FROM keyboard_input
                    UNION ALL
                    SELECT session_id, timestamp FROM mouse_activity
                    UNION ALL
                    SELECT session_id, timestamp FROM application_usage
                    UNION ALL
                    SELECT session_id, timestamp FROM file_activity
                )
                WHERE session_id IS NOT NULL
                GROUP BY session_id
                HAVING datetime(last_seen) < datetime(?)
                """,
                (cutoff.isoformat(),),
            )
            return [row[0] for row in cursor.fetchall() if row[0]]

    def _enforce_size_limit(self) -> None:
        if not self.db_path.exists():
            return
        if self.db_path.stat().st_size <= self.max_database_bytes:
            return
        LOGGER.warning(
            "Monitoring database exceeds size limit (%.2f GB). Purging oldest sessions until under limit.",
            self.db_path.stat().st_size / (1024 ** 3),
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT session_id, MAX(timestamp) AS last_seen
                FROM (
                    SELECT session_id, timestamp FROM screen_recordings
                    UNION ALL
                    SELECT session_id, timestamp FROM keyboard_input
                    UNION ALL
                    SELECT session_id, timestamp FROM mouse_activity
                    UNION ALL
                    SELECT session_id, timestamp FROM application_usage
                    UNION ALL
                    SELECT session_id, timestamp FROM file_activity
                )
                WHERE session_id IS NOT NULL
                GROUP BY session_id
                ORDER BY last_seen ASC
                """,
            )
            sessions = [row["session_id"] for row in cursor.fetchall() if row["session_id"]]

        for session_id in sessions:
            if self.db_path.stat().st_size <= self.max_database_bytes:
                break
            LOGGER.info("Purging session %s to enforce database size limit", session_id)
            self.purge_session(session_id)


__all__ = ["MonitoringRetentionManager"]
