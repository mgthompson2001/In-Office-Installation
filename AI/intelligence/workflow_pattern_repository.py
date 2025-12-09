#!/usr/bin/env python3
"""Workflow pattern repository utilities."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowStep:
    """Single step within a workflow pattern."""

    page_url: Optional[str]
    action_type: Optional[str]
    selector: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class WorkflowPattern:
    """Normalized workflow pattern ready for automation generation."""

    pattern_hash: str
    pattern_type: str
    frequency: int
    total_sessions: int
    first_seen: datetime
    last_seen: datetime
    steps: List[WorkflowStep]
    raw_data: Dict[str, Any]


class WorkflowPatternRepository:
    """Reads workflow patterns from the aggregated pattern store."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.pattern_db = self.installation_dir / "AI" / "intelligence" / "workflow_patterns.db"

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.pattern_db, timeout=30)

    def list_patterns(self, limit: int = 50, min_frequency: int = 5) -> List[WorkflowPattern]:
        if not self.pattern_db.exists():
            return []

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT pattern_hash, pattern_type, frequency, total_sessions,
                       first_seen, last_seen, sample_pattern
                FROM aggregated_patterns
                WHERE frequency >= ?
                ORDER BY frequency DESC, last_seen DESC
                LIMIT ?
                """,
                (min_frequency, limit),
            )
            rows = cursor.fetchall()

        patterns: List[WorkflowPattern] = []
        for row in rows:
            raw_data = {}
            try:
                raw_data = json.loads(row["sample_pattern"] or "{}")
            except Exception:
                raw_data = {}

            steps_json = raw_data.get("action_sequence") or raw_data.get("steps") or []
            steps: List[WorkflowStep] = []
            for entry in steps_json:
                if isinstance(entry, dict):
                    steps.append(
                        WorkflowStep(
                            page_url=entry.get("page_url") or entry.get("url"),
                            action_type=entry.get("action") or entry.get("type"),
                            selector=entry.get("selector") or entry.get("element") or entry.get("by"),
                            metadata={
                                key: value
                                for key, value in entry.items()
                                if key not in {"page_url", "url", "action", "type", "selector", "element", "by"}
                            },
                        )
                    )

            try:
                first_seen = datetime.fromisoformat(row["first_seen"])
            except Exception:
                first_seen = datetime.min

            try:
                last_seen = datetime.fromisoformat(row["last_seen"])
            except Exception:
                last_seen = datetime.min

            patterns.append(
                WorkflowPattern(
                    pattern_hash=row["pattern_hash"],
                    pattern_type=row["pattern_type"],
                    frequency=int(row["frequency"] or 0),
                    total_sessions=int(row["total_sessions"] or 0),
                    first_seen=first_seen,
                    last_seen=last_seen,
                    steps=steps,
                    raw_data=raw_data,
                )
            )

        return patterns

    def get_pattern(self, pattern_hash: str) -> Optional[WorkflowPattern]:
        matches = self.list_patterns(limit=1_000, min_frequency=1)
        for pattern in matches:
            if pattern.pattern_hash == pattern_hash:
                return pattern
        return None
