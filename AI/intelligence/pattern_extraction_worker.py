#!/usr/bin/env python3
"""Pattern Extraction Worker for Master AI Dashboard."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class PatternSummary:
    total_patterns: int
    last_seen: Optional[str]
    total_sessions: int


class PatternExtractionWorker:
    """Converts raw workflow pattern events into aggregated storage."""

    def __init__(self, installation_dir: Optional[Path] = None, interval_seconds: int = 120, batch_size: int = 200):
        installation_dir = Path(installation_dir) if installation_dir else Path(__file__).parent.parent
        self.installation_dir = installation_dir
        self.interval_seconds = max(10, interval_seconds)
        self.batch_size = max(10, batch_size)

        self.browser_db = self._locate_browser_db()
        self.pattern_db = self.installation_dir / "AI" / "intelligence" / "workflow_patterns.db"

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._ensure_pattern_store()

    def _locate_browser_db(self) -> Path:
        candidates = [
            self.installation_dir / "_secure_data" / "browser_activity.db",
            self.installation_dir / "AI" / "monitoring" / "browser_activity.db",
        ]
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    def _connect(self, path: Path) -> sqlite3.Connection:
        return sqlite3.connect(path, timeout=30)

    def _ensure_pattern_store(self) -> None:
        self.pattern_db.parent.mkdir(exist_ok=True)
        with self._connect(self.pattern_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS aggregated_patterns (
                    pattern_hash TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    frequency INTEGER DEFAULT 0,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    sample_pattern TEXT,
                    compressed_pattern BLOB,
                    total_sessions INTEGER DEFAULT 0,
                    last_source_id INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pattern_processing_state (
                    source_table TEXT PRIMARY KEY,
                    last_id INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _get_last_processed_id(self, table_name: str) -> int:
        with self._connect(self.pattern_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_id FROM pattern_processing_state WHERE source_table = ?", (table_name,))
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def _update_last_processed_id(self, table_name: str, last_id: int) -> None:
        with self._connect(self.pattern_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pattern_processing_state (source_table, last_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(source_table) DO UPDATE SET
                    last_id = excluded.last_id,
                    updated_at = excluded.updated_at
                """,
                (table_name, last_id, datetime.now().isoformat()),
            )
            conn.commit()

    def run_once(self) -> int:
        if not self.browser_db.exists():
            return 0

        last_id = self._get_last_processed_id("workflow_patterns")
        with self._connect(self.browser_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, pattern_hash, pattern_type, pattern_data, frequency, first_seen, last_seen
                FROM workflow_patterns
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (last_id, self.batch_size),
            )
            rows = cursor.fetchall()

        if not rows:
            return 0

        max_id = last_id
        with self._connect(self.pattern_db) as conn:
            cursor = conn.cursor()
            for row in rows:
                max_id = max(max_id, row["id"])
                pattern_hash = row["pattern_hash"]
                pattern_type = row["pattern_type"]
                pattern_data = json.loads(row["pattern_data"]) if row["pattern_data"] else {}
                frequency = int(row["frequency"] or 1)
                first_seen = row["first_seen"] or datetime.now().isoformat()
                last_seen = row["last_seen"] or first_seen
                compressed = zlib.compress(json.dumps(pattern_data, sort_keys=True).encode("utf-8"))

                cursor.execute(
                    """
                    INSERT INTO aggregated_patterns
                        (pattern_hash, pattern_type, frequency, first_seen, last_seen,
                         sample_pattern, compressed_pattern, total_sessions, last_source_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pattern_hash) DO UPDATE SET
                        frequency = aggregated_patterns.frequency + excluded.frequency,
                        last_seen = excluded.last_seen,
                        total_sessions = aggregated_patterns.total_sessions + 1,
                        compressed_pattern = CASE
                            WHEN excluded.frequency > aggregated_patterns.frequency THEN excluded.compressed_pattern
                            ELSE aggregated_patterns.compressed_pattern
                        END,
                        sample_pattern = CASE
                            WHEN aggregated_patterns.sample_pattern IS NULL THEN excluded.sample_pattern
                            ELSE aggregated_patterns.sample_pattern
                        END,
                        last_source_id = MAX(aggregated_patterns.last_source_id, excluded.last_source_id)
                    """,
                    (
                        pattern_hash,
                        pattern_type,
                        frequency,
                        first_seen,
                        last_seen,
                        json.dumps(pattern_data),
                        compressed,
                        1,
                        row["id"],
                    ),
                )

            conn.commit()

        self._update_last_processed_id("workflow_patterns", max_id)
        return len(rows)

    def start(self, background: bool = True) -> None:
        """Start the worker either in the background or run once synchronously."""
        if not background:
            self.run_once()
            return

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = self.run_once()
                sleep_time = self.interval_seconds if processed == 0 else 5
            except sqlite3.Error:
                sleep_time = self.interval_seconds
            except Exception:
                sleep_time = self.interval_seconds
            self._stop_event.wait(sleep_time)

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------
    def get_summary(self) -> PatternSummary:
        with self._connect(self.pattern_db) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total, MAX(last_seen) as last_seen, SUM(total_sessions) as sessions FROM aggregated_patterns"
            )
            row = cursor.fetchone()
            return PatternSummary(
                total_patterns=int(row["total"] or 0),
                last_seen=row["last_seen"],
                total_sessions=int(row["sessions"] or 0) if row["sessions"] is not None else 0,
            )


_global_worker: Optional[PatternExtractionWorker] = None
_lock = threading.Lock()


def get_pattern_worker(installation_dir: Optional[Path] = None) -> PatternExtractionWorker:
    global _global_worker
    with _lock:
        if _global_worker is None:
            _global_worker = PatternExtractionWorker(installation_dir=installation_dir)
        return _global_worker


def start_pattern_worker(installation_dir: Optional[Path] = None) -> PatternExtractionWorker:
    worker = get_pattern_worker(installation_dir)
    worker.start(background=True)
    return worker
