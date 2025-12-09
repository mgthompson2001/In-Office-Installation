#!/usr/bin/env python3
"""Utilities to export full monitoring telemetry into compact training datasets."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_EVENT_LIMIT = 5000
DEFAULT_EXPORT_SUBDIR = Path("AI") / "training" / "exports"


@dataclass
class ExportResult:
    """Metadata describing an exported monitoring session."""

    session_id: str
    export_root: Path
    summary_file: Path
    events_file: Path
    counts: Dict[str, int]
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]


class MonitoringDataExporter:
    """Convert raw monitoring telemetry into lightweight artefacts for training."""

    TABLE_SPECS: Dict[str, Sequence[str]] = {
        "screen_recordings": ("timestamp", "session_id", "window_title", "active_app"),
        "keyboard_input": (
            "timestamp",
            "session_id",
            "key_pressed",
            "key_name",
            "is_special_key",
            "active_app",
            "window_title",
        ),
        "mouse_activity": (
            "timestamp",
            "session_id",
            "event_type",
            "x_position",
            "y_position",
            "button",
            "scroll_delta",
            "movement_count",
            "active_app",
            "window_title",
        ),
        "application_usage": (
            "timestamp",
            "session_id",
            "app_name",
            "app_path",
            "window_title",
            "is_active",
            "duration_seconds",
        ),
        "file_activity": (
            "timestamp",
            "session_id",
            "event_type",
            "file_path",
            "file_size",
            "file_type",
            "app_name",
        ),
    }

    def __init__(self, installation_dir: Path, *, event_limit: int = DEFAULT_EVENT_LIMIT) -> None:
        self.installation_dir = Path(installation_dir)
        self.data_dir = self.installation_dir / "_secure_data" / "full_monitoring"
        self.db_path = self.data_dir / "full_monitoring.db"
        self.event_limit = max(100, event_limit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def export_session(
        self,
        session_id: str,
        export_root: Optional[Path] = None,
        *,
        include_events: bool = True,
    ) -> Optional[ExportResult]:
        if not self.db_path.exists():
            return None

        export_root = (export_root or (self.installation_dir / DEFAULT_EXPORT_SUBDIR)).resolve()
        export_root.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            available = self._session_exists(conn, session_id)
            if not available:
                return None

            counts = self._collect_counts(conn, session_id)
            time_bounds = self._collect_time_bounds(conn, session_id)

            session_dir = export_root / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            summary_path = session_dir / "summary.json"
            events_path = session_dir / "events.jsonl"

            summary_payload: Dict[str, Any] = {
                "session_id": session_id,
                "generated_at": datetime.utcnow().strftime(ISO_FORMAT),
                "counts": counts,
                "time_range": time_bounds,
                "source_db": str(self.db_path),
            }

            summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

            if include_events:
                self._write_event_stream(conn, session_id, events_path)
            else:
                if events_path.exists():
                    events_path.unlink()

            return ExportResult(
                session_id=session_id,
                export_root=session_dir,
                summary_file=summary_path,
                events_file=events_path if include_events else summary_path,
                counts=counts,
                start_timestamp=time_bounds.get("start"),
                end_timestamp=time_bounds.get("end"),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _session_exists(self, conn: sqlite3.Connection, session_id: str) -> bool:
        cursor = conn.execute(
            """
            SELECT 1
            FROM (
                SELECT session_id FROM screen_recordings WHERE session_id = ?
                UNION ALL
                SELECT session_id FROM keyboard_input WHERE session_id = ?
                UNION ALL
                SELECT session_id FROM mouse_activity WHERE session_id = ?
                UNION ALL
                SELECT session_id FROM application_usage WHERE session_id = ?
                UNION ALL
                SELECT session_id FROM file_activity WHERE session_id = ?
            )
            LIMIT 1
            """,
            (session_id,) * 5,
        )
        return cursor.fetchone() is not None

    def _collect_counts(self, conn: sqlite3.Connection, session_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for table in self.TABLE_SPECS:
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
                (session_id,),
            )
            counts[table] = int(cursor.fetchone()[0])
        return counts

    def _collect_time_bounds(self, conn: sqlite3.Connection, session_id: str) -> Dict[str, Optional[str]]:
        bounds = {"start": None, "end": None}
        timestamps: List[str] = []
        for table, columns in self.TABLE_SPECS.items():
            if "timestamp" not in columns:
                continue
            cursor = conn.execute(
                f"SELECT MIN(timestamp), MAX(timestamp) FROM {table} WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                continue
            start, end = row
            if start:
                timestamps.append(start)
            if end:
                timestamps.append(end)
        if timestamps:
            bounds["start"] = min(timestamps)
            bounds["end"] = max(timestamps)
        return bounds

    def _write_event_stream(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        output_file: Path,
    ) -> None:
        rows_emitted = 0
        with output_file.open("w", encoding="utf-8") as handle:
            for table, columns in self.TABLE_SPECS.items():
                projection = ", ".join(columns)
                cursor = conn.execute(
                    f"SELECT {projection} FROM {table} WHERE session_id = ? ORDER BY timestamp LIMIT ?",
                    (session_id, self.event_limit),
                )
                col_names = [description[0] for description in cursor.description]
                for db_row in cursor:
                    payload = {name: db_row[idx] for idx, name in enumerate(col_names)}
                    payload["source_table"] = table
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    rows_emitted += 1
        # If nothing was written, remove placeholder file
        if rows_emitted == 0:
            output_file.unlink(missing_ok=True)


def export_latest_sessions(
    installation_dir: Path,
    *,
    limit: int = 5,
    event_limit: int = DEFAULT_EVENT_LIMIT,
) -> List[ExportResult]:
    exporter = MonitoringDataExporter(installation_dir, event_limit=event_limit)
    if not exporter.db_path.exists():
        return []

    results: List[ExportResult] = []
    with sqlite3.connect(exporter.db_path) as conn:
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
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        )
        session_ids = [row["session_id"] for row in cursor.fetchall() if row["session_id"]]

    for session_id in session_ids:
        result = exporter.export_session(session_id)
        if result:
            results.append(result)
    return results


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Export monitoring sessions to training artefacts")
    parser.add_argument(
        "installation",
        type=Path,
        help="Path to the In-Office Installation directory",
    )
    parser.add_argument(
        "--session",
        dest="session_id",
        help="Specific session identifier to export. If omitted the most recent sessions are exported.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of recent sessions to export when --session is not provided.",
    )
    parser.add_argument(
        "--events",
        dest="event_limit",
        type=int,
        default=DEFAULT_EVENT_LIMIT,
        help="Maximum number of events per table to include in the JSONL output.",
    )

    args = parser.parse_args()
    if args.session_id:
        exporter = MonitoringDataExporter(args.installation, event_limit=args.event_limit)
        result = exporter.export_session(args.session_id)
        if result:
            print(f"Exported session {result.session_id} to {result.export_root}")
        else:
            print("No data exported (session not found).")
    else:
        results = export_latest_sessions(args.installation, limit=args.limit, event_limit=args.event_limit)
        if not results:
            print("No monitoring sessions were exported.")
        for result in results:
            print(f"Exported session {result.session_id} to {result.export_root}")


if __name__ == "__main__":
    _cli()
