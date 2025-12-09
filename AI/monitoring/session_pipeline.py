#!/usr/bin/env python3
"""Session pipeline orchestrating export, ingestion, and cleanup for monitoring data."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from .export_monitoring_data import ExportResult, MonitoringDataExporter
from .monitoring_retention import MonitoringRetentionManager

LOGGER = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    session_id: str
    export_path: Path
    summary_path: Path
    events_path: Optional[Path]
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]

class MonitoringSessionPipeline:
    """High-level orchestration for handling monitoring sessions post-capture."""

    def __init__(
        self,
        installation_dir: Path,
        *,
        retention_days: int = 7,
        max_database_gb: float = 2.0,
        event_limit: int = 5000,
    ) -> None:
        self.installation_dir = Path(installation_dir)
        config = self._load_config()
        if config:
            retention_days = int(config.get("retention_days", retention_days) or retention_days)
            max_database_gb = float(config.get("max_database_gb", max_database_gb) or max_database_gb)
            event_limit = int(config.get("export_event_limit", config.get("event_limit", event_limit)) or event_limit)
        self.exporter = MonitoringDataExporter(self.installation_dir, event_limit=event_limit)
        self.retention = MonitoringRetentionManager(
            self.installation_dir,
            retention_days=retention_days,
            max_database_gb=max_database_gb,
        )
        self.training_db = self.installation_dir / "AI" / "intelligence" / "training_metrics.db"
        self._ensure_metadata_table()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_session(
        self,
        session_id: str,
        *,
        workflow_title: Optional[str] = None,
        cleanup: bool = True,
    ) -> Optional[PipelineResult]:
        LOGGER.info("Exporting monitoring session %s", session_id)
        export_result = self.exporter.export_session(session_id)
        if not export_result:
            LOGGER.warning("Session %s not found in monitoring database", session_id)
            return None

        self._record_export_metadata(export_result, workflow_title)

        if cleanup:
            LOGGER.info("Applying retention policies after export")
            self.retention.purge_session(session_id)
            self.retention.enforce()

        return PipelineResult(
            session_id=session_id,
            export_path=export_result.export_root,
            summary_path=export_result.summary_file,
            events_path=export_result.events_file if export_result.events_file.exists() else None,
            start_timestamp=export_result.start_timestamp,
            end_timestamp=export_result.end_timestamp,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_metadata_table(self) -> None:
        if not self.training_db.exists():
            LOGGER.warning("Training metrics database missing at %s", self.training_db)
        with sqlite3.connect(self.training_db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    workflow_title TEXT,
                    exported_at TEXT NOT NULL,
                    summary_path TEXT NOT NULL,
                    events_path TEXT,
                    counts_json TEXT,
                    start_timestamp TEXT,
                    end_timestamp TEXT
                )
                """,
            )
            conn.commit()

    def _load_config(self) -> Dict[str, Any]:
        config_path = self.installation_dir / "AI" / "monitoring" / "full_monitoring_config.json"
        try:
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _record_export_metadata(self, result: ExportResult, workflow_title: Optional[str]) -> None:
        counts_json = json.dumps(result.counts)
        exported_at = datetime.utcnow().isoformat()
        with sqlite3.connect(self.training_db) as conn:
            conn.execute(
                """
                INSERT INTO session_exports (
                    session_id, workflow_title, exported_at, summary_path, events_path,
                    counts_json, start_timestamp, end_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    workflow_title = excluded.workflow_title,
                    exported_at = excluded.exported_at,
                    summary_path = excluded.summary_path,
                    events_path = excluded.events_path,
                    counts_json = excluded.counts_json,
                    start_timestamp = excluded.start_timestamp,
                    end_timestamp = excluded.end_timestamp
                """,
                (
                    result.session_id,
                    workflow_title,
                    exported_at,
                    str(result.summary_file),
                    str(result.events_file) if result.events_file.exists() else None,
                    counts_json,
                    result.start_timestamp,
                    result.end_timestamp,
                ),
            )
            conn.commit()


__all__ = ["MonitoringSessionPipeline", "PipelineResult"]
