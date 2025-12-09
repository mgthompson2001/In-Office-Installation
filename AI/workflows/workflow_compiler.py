#!/usr/bin/env python3
"""
Workflow Compiler
-----------------
Transforms stored workflow_understanding records from the context
engine into executable graph definitions that can be inspected or
simulated from the Master AI Dashboard.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from collections import Counter


@dataclass
class WorkflowStep:
    step_number: int
    action_id: str
    intent_category: str = "unknown"
    intent_description: str = "Intent unclear"
    intent_confidence: float = 0.0
    contexts: Dict[str, str] = field(default_factory=dict)
    source_session: str = ""


@dataclass
class CompiledWorkflow:
    workflow_key: str
    session_id: str
    workflow_id: str
    workflow_type: str
    description: str
    goal: str
    confidence: float
    timestamp: str
    steps: List[WorkflowStep] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "workflow_key": self.workflow_key,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "description": self.description,
            "goal": self.goal,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "summary": getattr(self, "summary", []),
            "steps": [
                {
                    "step_number": step.step_number,
                    "action_id": step.action_id,
                    "intent_category": step.intent_category,
                    "intent_description": step.intent_description,
                    "intent_confidence": step.intent_confidence,
                    "contexts": step.contexts,
                    "source_session": step.source_session,
                }
                for step in self.steps
            ],
        }


class WorkflowCompiler:
    """Compile workflow-understanding records into graph definitions."""

    def __init__(self, installation_dir: Optional[Path] = None):
        if installation_dir is None:
            installation_dir = Path(__file__).resolve().parent.parent

        self.installation_dir = Path(installation_dir)
        self.ai_dir = self.installation_dir / "AI"
        self.intelligence_dir = self.ai_dir / "intelligence"
        self.workflows_dir = self.ai_dir / "workflows"
        self.compiled_dir = self.workflows_dir / "compiled"

        self.context_db = self.intelligence_dir / "context_understanding.db"

        self.workflows_dir.mkdir(exist_ok=True, parents=True)
        self.compiled_dir.mkdir(exist_ok=True, parents=True)

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------
    def compile_workflows(self) -> List[CompiledWorkflow]:
        """Compile all stored workflows from the context DB."""
        if not self.context_db.exists():
            return []

        compiled: List[CompiledWorkflow] = []

        with sqlite3.connect(self.context_db) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                """
                SELECT id, session_id, workflow_id, workflow_type,
                       workflow_description, workflow_steps,
                       workflow_goal, workflow_context,
                       confidence_score, timestamp
                FROM workflow_understanding
                ORDER BY timestamp DESC
                LIMIT 200
                """
            )

            rows = cur.fetchall()
            for row in rows:
                workflow = self._build_workflow(cur, row)
                if workflow is None:
                    continue
                compiled.append(workflow)
                self._persist_workflow(workflow)

        return compiled

    def _build_workflow(self, cur: sqlite3.Cursor, row: sqlite3.Row) -> Optional[CompiledWorkflow]:
        workflow_steps_raw = row["workflow_steps"] or "[]"
        try:
            action_ids = json.loads(workflow_steps_raw)
        except json.JSONDecodeError:
            action_ids = []

        workflow_id = row["workflow_id"] or f"wf_{row['id']}"
        workflow_key = f"{row['session_id']}::{workflow_id}"

        compiled = CompiledWorkflow(
            workflow_key=workflow_key,
            session_id=row["session_id"],
            workflow_id=workflow_id,
            workflow_type=row["workflow_type"] or "unknown",
            description=row["workflow_description"] or "",
            goal=row["workflow_goal"] or "",
            confidence=row["confidence_score"] or 0.0,
            timestamp=row["timestamp"] or datetime.now().isoformat(),
        )

        if not action_ids:
            return compiled

        for idx, action_id in enumerate(action_ids, start=1):
            step = self._build_step(cur, row["session_id"], action_id, idx)
            compiled.steps.append(step)

        compiled.summary = self._generate_summary(compiled)

        return compiled

    def _build_step(
        self,
        cur: sqlite3.Cursor,
        session_id: str,
        action_id: str,
        step_number: int,
    ) -> WorkflowStep:
        step = WorkflowStep(step_number=step_number, action_id=action_id)

        cur.execute(
            """
            SELECT intent_category, intent_description, confidence_score
            FROM intent_understanding
            WHERE session_id = ? AND action_id = ?
            ORDER BY confidence_score DESC
            LIMIT 1
            """,
            (session_id, action_id),
        )
        intent_row = cur.fetchone()
        if intent_row:
            step.intent_category = intent_row["intent_category"] or "unknown"
            step.intent_description = intent_row["intent_description"] or "Intent unclear"
            step.intent_confidence = intent_row["confidence_score"] or 0.0

        cur.execute(
            """
            SELECT context_type, context_value
            FROM context_understanding
            WHERE session_id = ? AND action_id = ?
            ORDER BY context_type
            """,
            (session_id, action_id),
        )
        contexts = {r["context_type"]: r["context_value"] for r in cur.fetchall()}
        step.contexts = contexts

        step.source_session = session_id
        return step

    def _persist_workflow(self, workflow: CompiledWorkflow) -> None:
        output_file = self.compiled_dir / f"{workflow.workflow_key.replace('::', '__')}.json"
        with output_file.open("w", encoding="utf-8") as fh:
            json.dump(workflow.to_dict(), fh, ensure_ascii=False, indent=2)

    def _generate_summary(self, workflow: CompiledWorkflow) -> List[str]:
        lines: List[str] = []
        total_steps = len(workflow.steps)
        business_steps = [
            step for step in workflow.steps
            if step.intent_category not in {"development_activity"}
        ]

        lines.append(f"Workflow captured from session {workflow.session_id} ({workflow.workflow_type}).")
        if business_steps and total_steps != len(business_steps):
            lines.append(
                f"Contains {len(business_steps)} business-relevant actions (out of {total_steps} recorded) with goal: {workflow.goal or 'Unspecified'}."
            )
        else:
            lines.append(f"Contains {total_steps} recorded actions with goal: {workflow.goal or 'Unspecified'}.")

        if not workflow.steps:
            return lines

        analysis_steps = business_steps or workflow.steps

        intent_counts = Counter(step.intent_category for step in analysis_steps)
        context_app = Counter(
            step.contexts.get("application") for step in analysis_steps if step.contexts.get("application")
        )
        context_page = Counter(
            step.contexts.get("page") for step in analysis_steps if step.contexts.get("page")
        )

        intent_friendly = {
            "penelope_queue_management": "Penelope Queue Management",
            "penelope_portal_navigation": "Penelope Portal Navigation",
            "automation_control": "Automation Control",
            "remove_counselor": "Counselor Removal",
            "therapy_notes_management": "TherapyNotes Management",
            "process_billing": "Billing Workflow",
            "web_form_completion": "Web Form Completion",
            "development_activity": "Development / IDE Activity",
        }

        if intent_counts:
            lines.append("Top intents detected:")
            for intent, count in intent_counts.most_common(3):
                label = intent_friendly.get(intent, intent.replace('_', ' ').title())
                lines.append(f"  • {label} ({count} steps)")

        if context_app:
            lines.append("Primary applications involved:")
            for app, count in context_app.most_common(3):
                lines.append(f"  • {app} ({count} steps)")

        if context_page:
            lines.append("Common screens/pages:")
            for page, count in context_page.most_common(3):
                lines.append(f"  • {page} ({count} steps)")

        lines.append("Suggested interpretation:")
        top_intent = intent_counts.most_common(1)[0][0] if intent_counts else "unknown"
        if top_intent == "automation_control":
            lines.append("  This appears to be a session controlling automation tools (launching bots, monitoring).")
        elif top_intent in {"remove_counselor", "therapy_notes_management"}:
            lines.append("  This captures a TherapyNotes counselor removal workflow.")
        elif top_intent == "penelope_queue_management":
            lines.append("  This session is managing the Penelope/Athena task queue and counselor assignments.")
        elif top_intent == "penelope_portal_navigation":
            lines.append("  This session is navigating within the Penelope portal.")
        elif top_intent == "web_form_completion":
            lines.append("  This workflow completes a web form or filters data on a webpage.")
        elif top_intent == "development_activity":
            lines.append("  Activity recorded inside the development environment (likely code editing).")
        else:
            lines.append("  Mixed activity detected; review simulation output for step-by-step context.")

        return lines

    # ------------------------------------------------------------------
    # Queries for UI
    # ------------------------------------------------------------------
    def get_compiled_workflows(self) -> List[Dict]:
        workflows = []
        for json_path in sorted(self.compiled_dir.glob("*.json")):
            try:
                with json_path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    workflows.append(data)
            except Exception:
                continue
        return workflows

    def simulate_workflow(self, workflow_key: str) -> Optional[Dict]:
        file_path = self.compiled_dir / f"{workflow_key.replace('::', '__')}.json"
        if not file_path.exists():
            return None

        with file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        simulation = {
            "workflow_key": data.get("workflow_key"),
            "summary": self._build_summary(data),
            "steps": [
                {
                    "step_number": step.get("step_number"),
                    "action_id": step.get("action_id"),
                    "intent": f"{step.get('intent_category')} ({step.get('intent_confidence'):.2f})",
                    "intent_description": step.get("intent_description"),
                    "contexts": step.get("contexts", {}),
                }
                for step in data.get("steps", [])
            ],
        }
        return simulation

    def _build_summary(self, data: Dict) -> List[str]:
        summary = []
        summary_lines = data.get("summary")
        if summary_lines:
            summary.extend(summary_lines)
        else:
            summary.extend([
                f"Workflow ID: {data.get('workflow_id')} ({data.get('workflow_type')})",
                f"Session: {data.get('session_id')}",
                f"Confidence: {data.get('confidence'):.2f}",
            ])
        goal = data.get("goal")
        if goal:
            summary.append(f"Goal: {goal}")
        description = data.get("description")
        if description:
            summary.append("")
            summary.append("Description:")
            summary.append(description)
        summary.append("")
        summary.append(f"Total steps: {len(data.get('steps', []))}")
        return summary

