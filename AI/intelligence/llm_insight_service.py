#!/usr/bin/env python3
"""LLM Insight generation utilities for the Master AI Dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from verify_ai_intelligence import AIIntelligenceDashboard
from llm.llm_service import LLMService


INSIGHT_PREFIX = "insight_"
INSIGHT_EXTENSION = ".json"
DEFAULT_MAX_AGE_HOURS = 6


def _analysis_dir(installation_dir: Path) -> Path:
    analysis_dir = installation_dir / "AI" / "AI Analysis reports"
    analysis_dir.mkdir(exist_ok=True)
    return analysis_dir


def _collect_metrics(installation_dir: Path) -> Dict[str, Any]:
    dashboard = AIIntelligenceDashboard(installation_dir)
    metrics: Dict[str, Any] = {
        "collected": dashboard.get_data_collection_metrics(),
        "learning": dashboard.get_ai_learning_metrics(),
        "patterns": dashboard.get_pattern_summary(),
        "training_runs": dashboard.get_recent_training_runs(limit=3),
    }
    return metrics


def _build_prompt(metrics: Dict[str, Any]) -> str:
    return (
        "You are the AI director for a healthcare automation platform. "
        "Summarize system health, learning progress, and actionable next steps. "
        "Be concise (under 6 bullet points) and highlight risks/opportunities.\n\n"
        f"Metrics:\n{json.dumps(metrics, indent=2)}"
    )


def _insight_path(analysis_dir: Path, timestamp: datetime) -> Path:
    return analysis_dir / f"{INSIGHT_PREFIX}{timestamp.strftime('%Y%m%d_%H%M%S')}{INSIGHT_EXTENSION}"


def _load_insight(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_latest_insight(installation_dir: Path) -> Optional[Dict[str, Any]]:
    analysis_dir = _analysis_dir(installation_dir)
    candidates = sorted(analysis_dir.glob(f"{INSIGHT_PREFIX}*{INSIGHT_EXTENSION}"))
    if not candidates:
        return None
    return _load_insight(candidates[-1])


def _is_stale(insight: Dict[str, Any], max_age_hours: int) -> bool:
    generated_at = insight.get("generated_at")
    if not generated_at:
        return True
    try:
        ts = datetime.fromisoformat(generated_at)
    except ValueError:
        return True
    return datetime.now() - ts > timedelta(hours=max_age_hours)


def generate_insight(
    installation_dir: Path,
    *,
    force: bool = False,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> Optional[Dict[str, Any]]:
    analysis_dir = _analysis_dir(installation_dir)
    latest = load_latest_insight(installation_dir)
    if latest and not force and not _is_stale(latest, max_age_hours):
        return latest

    metrics = _collect_metrics(installation_dir)
    prompt = _build_prompt(metrics)

    llm = LLMService(installation_dir)
    summary: Optional[str] = None
    if llm.available() and llm.is_configured():
        summary = llm.generate_summary(
            prompt,
            system_prompt=(
                "You are the executive AI analyst. Provide a brief report with headings: "
                "Overview, Key Metrics, Risks, Recommendations."
            ),
            max_tokens=600,
        )

    if not summary:
        # Fallback summary if LLM unavailable
        collected = metrics.get("collected", {})
        learning = metrics.get("learning", {})
        summary = (
            "LLM summary unavailable."
            f" Data points: {collected.get('total_data_points', 0):,}."
            f" Aggregated patterns: {learning.get('pattern_count', 0):,}."
            f" Models trained: {learning.get('models_trained', 0)}."
        )

    config = llm.get_config()
    insight = {
        "generated_at": datetime.now().isoformat(),
        "model": config.model if config else None,
        "summary": summary,
        "metrics": metrics,
    }

    path = _insight_path(analysis_dir, datetime.now())
    try:
        path.write_text(json.dumps(insight, indent=2), encoding="utf-8")
    except Exception:
        pass

    return insight
