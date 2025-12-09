#!/usr/bin/env python3
"""Automation execution data access layer."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class AutomationPrototypeRecord:
    pattern_hash: str
    prototype_path: str
    created_at: datetime
    description: Optional[str]


@dataclass
class AutomationRunRecord:
    run_id: int
    pattern_hash: str
    prototype_path: str
    started_at: datetime
    completed_at: datetime
    status: str
    duration_seconds: float
    logs_path: Optional[str]
    error_message: Optional[str]
    metadata: Dict


class AutomationExecutionRepository:
    """Handles persistence for automation prototypes and execution runs."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.db_path = self.installation_dir / "AI" / "intelligence" / "automation_runs.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_prototypes (
                    pattern_hash TEXT PRIMARY KEY,
                    prototype_path TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT NOT NULL,
                    prototype_path TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_seconds REAL,
                    logs_path TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Prototype records
    # ------------------------------------------------------------------
    def register_prototype(self, pattern_hash: str, prototype_path: Path, description: Optional[str] = None) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO automation_prototypes (pattern_hash, prototype_path, description, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(pattern_hash) DO UPDATE SET
                    prototype_path = excluded.prototype_path,
                    description = excluded.description,
                    created_at = excluded.created_at
                """,
                (
                    pattern_hash,
                    str(prototype_path),
                    description,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_prototype(self, pattern_hash: str) -> Optional[AutomationPrototypeRecord]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pattern_hash, prototype_path, description, created_at FROM automation_prototypes WHERE pattern_hash = ?",
                (pattern_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return AutomationPrototypeRecord(
                pattern_hash=row[0],
                prototype_path=row[1],
                description=row[2],
                created_at=datetime.fromisoformat(row[3]),
            )

    # ------------------------------------------------------------------
    # Run records
    # ------------------------------------------------------------------
    def log_run(
        self,
        *,
        pattern_hash: str,
        prototype_path: Path,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        logs_path: Optional[Path] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO automation_runs (
                    pattern_hash, prototype_path, started_at, completed_at,
                    status, duration_seconds, logs_path, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern_hash,
                    str(prototype_path),
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    status,
                    max(0.0, (completed_at - started_at).total_seconds()),
                    str(logs_path) if logs_path else None,
                    error_message,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_recent_runs(self, limit: int = 20) -> Dict[int, AutomationRunRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, pattern_hash, prototype_path, started_at, completed_at, status,
                       duration_seconds, logs_path, error_message, metadata
                FROM automation_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        records: Dict[int, AutomationRunRecord] = {}
        for row in rows:
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except Exception:
                metadata = {}
            records[row["id"]] = AutomationRunRecord(
                run_id=row["id"],
                pattern_hash=row["pattern_hash"],
                prototype_path=row["prototype_path"],
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"]),
                status=row["status"],
                duration_seconds=float(row["duration_seconds"] or 0.0),
                logs_path=row["logs_path"],
                error_message=row["error_message"],
                metadata=metadata,
            )
        return records

    def list_prototypes(self) -> Dict[str, Dict[str, Optional[str]]]:
        prototypes: Dict[str, Dict[str, Optional[str]]] = {}
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pattern_hash, prototype_path, description, created_at FROM automation_prototypes"
            )
            rows = cursor.fetchall()

        for row in rows:
            summary_path = Path(row["prototype_path"]) / "summary.json"
            gpt_path = Path(row["prototype_path"]) / "gpt_report.md"
            summary_data = None
            try:
                if summary_path.exists():
                    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                summary_data = None

            prototypes[row["pattern_hash"]] = {
                "pattern_hash": row["pattern_hash"],
                "path": str(row["prototype_path"]),
                "display_name": row["description"],
                "created_at": row["created_at"],
                "summary": str(summary_path) if summary_path.exists() else None,
                "gpt_report": str(gpt_path) if gpt_path.exists() else None,
                "summary_data": summary_data,
                "frequency": summary_data.get("frequency") if isinstance(summary_data, dict) else None,
                "last_seen": summary_data.get("last_seen") if isinstance(summary_data, dict) else None,
            }

        return prototypes
