#!/usr/bin/env python3
"""Automation prototype generator utilities."""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
AI_ROOT = CURRENT_DIR.parent
INSTALLATION_DIR = AI_ROOT.parent

for candidate in [INSTALLATION_DIR, AI_ROOT, CURRENT_DIR]:
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import json
import sqlite3
import zlib
import re
from datetime import datetime
from typing import Dict, Optional, Any

from llm.llm_service import LLMService

try:  # Allow import when executed as package or standalone script
    from .workflow_pattern_repository import WorkflowPattern, WorkflowPatternRepository
    from .automation_execution_repository import AutomationExecutionRepository
except ImportError:  # pragma: no cover
    from workflow_pattern_repository import WorkflowPattern, WorkflowPatternRepository
    from automation_execution_repository import AutomationExecutionRepository


SCRIPT_TEMPLATE = """# Auto-generated prototype for workflow {pattern_hash}
# Generated on {generated_at}

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def run_workflow(driver: webdriver.Chrome):
    wait = WebDriverWait(driver, 15)

{body}


if __name__ == "__main__":
    driver = webdriver.Chrome()
    try:
        run_workflow(driver)
    finally:
        driver.quit()
"""

STEP_TEMPLATE = """    # Step {index}: {description}
    driver.get("{url}")
"""


class AutomationPrototypeGenerator:
    """Creates automation prototype bundles from aggregated workflow patterns."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.repository = WorkflowPatternRepository(self.installation_dir)
        self.execution_repo = AutomationExecutionRepository(self.installation_dir)
        self.output_dir = self.installation_dir / "AI" / "automation_prototypes"
        self.output_dir.mkdir(exist_ok=True)
        self.llm_service = LLMService(self.installation_dir)

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return slug or "workflow"

    def list_prototypes(self) -> Dict[str, Dict[str, Optional[str]]]:
        return self.execution_repo.list_prototypes()

    def generate_for_top_patterns(self, *, limit: int = 5, min_frequency: int = 10) -> Dict[str, Path]:
        prototypes: Dict[str, Path] = {}
        for pattern in self.repository.list_patterns(limit=limit, min_frequency=min_frequency):
            bundle = self.generate_prototype(pattern)
            if bundle:
                prototypes[pattern.pattern_hash] = bundle
        return prototypes

    def generate_prototype(self, pattern: WorkflowPattern) -> Optional[Path]:
        output_path = self.output_dir / pattern.pattern_hash
        output_path.mkdir(exist_ok=True)

        script_body = []
        for idx, step in enumerate(pattern.steps, 1):
            action = step.action_type or "Action"
            url = step.page_url or "about:blank"
            script_body.append(STEP_TEMPLATE.format(index=idx, description=action, url=url))

        script_contents = SCRIPT_TEMPLATE.format(
            pattern_hash=pattern.pattern_hash,
            generated_at=pattern.last_seen.isoformat(),
            body="\n".join(script_body) if script_body else "    pass",
        )
        (output_path / "prototype.py").write_text(script_contents, encoding="utf-8")

        gpt_summary = self._generate_gpt_report(pattern)
        if gpt_summary:
            (output_path / "gpt_report.md").write_text(gpt_summary, encoding="utf-8")

        display_name = None
        if gpt_summary:
            first_line = gpt_summary.strip().splitlines()[0].strip("#* -")
            if first_line:
                display_name = first_line
        if not display_name and pattern.steps:
            first_step = pattern.steps[0]
            if first_step.action_type:
                display_name = f"{first_step.action_type.title()} workflow ({pattern.pattern_hash[:8]})"
        if not display_name:
            display_name = f"Workflow {pattern.pattern_hash[:8]}"

        summary_payload = {
            "pattern_hash": pattern.pattern_hash,
            "pattern_type": pattern.pattern_type,
            "frequency": pattern.frequency,
            "total_sessions": pattern.total_sessions,
            "first_seen": pattern.first_seen.isoformat(),
            "last_seen": pattern.last_seen.isoformat(),
            "display_name": display_name,
            "steps": [step.__dict__ for step in pattern.steps],
        }
        (output_path / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        self.execution_repo.register_prototype(
            pattern_hash=pattern.pattern_hash,
            prototype_path=output_path,
            description=display_name,
        )

        return output_path

    def _generate_gpt_report(self, pattern: WorkflowPattern) -> Optional[str]:
        if not self.llm_service.available() or not self.llm_service.is_configured():
            return None

        prompt = self._build_prompt(pattern)
        return self.llm_service.generate_summary(
            prompt,
            system_prompt=(
                "You are an automation architect. Given a workflow pattern, outline automation steps,"
                " validations, and risks. Format as Markdown."
            ),
            max_tokens=600,
        )

    def _build_prompt(self, pattern: WorkflowPattern) -> str:
        data = {
            "pattern_hash": pattern.pattern_hash,
            "pattern_type": pattern.pattern_type,
            "frequency": pattern.frequency,
            "total_sessions": pattern.total_sessions,
            "steps": [step.__dict__ for step in pattern.steps],
        }
        return (
            "Analyze the following workflow pattern and propose an automation plan."
            " Provide bullet points for required actions, validation, error handling, and streamlining opportunities.\n\n"
            f"Pattern data:\n{json.dumps(data, indent=2)}"
        )

    # ------------------------------------------------------------------
    # Single session generation
    # ------------------------------------------------------------------
    def generate_from_session(
        self,
        session_id: str,
        title: str,
        *,
        generation_mode: str = "both",
        cursor_notes: Optional[str] = None,
        screen_manifest: Optional[Dict[str, Any]] = None,
    ) -> Optional[Path]:
        print(f"[DEBUG] generate_from_session called: session_id={session_id}, title={title}, mode={generation_mode}")
        browser_db = self.installation_dir / "_secure_data" / "browser_activity.db"
        full_monitoring_db = self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db"
        
        print(f"[DEBUG] Browser DB path: {browser_db} (exists: {browser_db.exists()})")
        print(f"[DEBUG] Full monitoring DB path: {full_monitoring_db} (exists: {full_monitoring_db.exists()})")
        
        events = []
        
        # Get browser activity from browser_activity.db (Selenium-controlled browser)
        if browser_db.exists():
            with sqlite3.connect(browser_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT timestamp, url FROM page_navigations WHERE session_id = ? ORDER BY timestamp",
                    (session_id,),
                )
                nav_rows = cursor.fetchall()

                cursor.execute(
                    "SELECT timestamp, action_type, element_id, element_name, anonymized_page_url FROM element_interactions WHERE session_id = ? ORDER BY timestamp",
                    (session_id,),
                )
                interaction_rows = cursor.fetchall()
                
                for row in nav_rows:
                    events.append((row["timestamp"], "navigate", row["url"]))
                for row in interaction_rows:
                    events.append((row["timestamp"], "interaction", row))
        
        # Get Excel and browser activity from full_monitoring.db (any Excel/browser)
        if full_monitoring_db.exists():
            with sqlite3.connect(full_monitoring_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get Excel activity
                cursor.execute(
                    """SELECT timestamp, workbook_name, worksheet_name, cell_reference, cell_value, formula, action_type, window_title 
                       FROM excel_activity WHERE session_id = ? ORDER BY timestamp""",
                    (session_id,),
                )
                excel_rows = cursor.fetchall()
                for row in excel_rows:
                    events.append((row["timestamp"], "excel_activity", row))
                
                # Get browser activity from any browser
                cursor.execute(
                    """SELECT timestamp, browser_name, window_title, url, page_title, action_type, element_type, element_id, element_name, element_value, click_x, click_y, screenshot_path 
                       FROM browser_activity WHERE session_id = ? ORDER BY timestamp""",
                    (session_id,),
                )
                browser_rows = cursor.fetchall()
                for row in browser_rows:
                    events.append((row["timestamp"], "browser_activity", row))
                
                # Get PDF activity
                cursor.execute(
                    """SELECT timestamp, pdf_file_path, pdf_file_name, action_type, page_number, form_field_name, form_field_value, window_title, pdf_viewer_app 
                       FROM pdf_activity WHERE session_id = ? ORDER BY timestamp""",
                    (session_id,),
                )
                pdf_rows = cursor.fetchall()
                for row in pdf_rows:
                    events.append((row["timestamp"], "pdf_activity", row))
        
        print(f"[GENERATOR] Total events collected: {len(events)}")
        print(f"[GENERATOR] Breakdown: browser={len([e for e in events if e[1] == 'browser_activity'])}, mouse={len([e for e in events if e[1] == 'mouse_activity'])}, keyboard={len([e for e in events if e[1] == 'keyboard_input'])}, excel={len([e for e in events if e[1] == 'excel_activity'])}, pdf={len([e for e in events if e[1] == 'pdf_activity'])}")
        
        if not events:
            print("[GENERATOR] WARNING: No events found for this session. Cannot generate prototype.")
            # Check what session IDs actually exist in the database
            if full_monitoring_db.exists():
                try:
                    with sqlite3.connect(full_monitoring_db) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT DISTINCT session_id FROM browser_activity ORDER BY session_id DESC LIMIT 10")
                        existing_sessions = [row[0] for row in cursor.fetchall()]
                        print(f"[GENERATOR] Existing session IDs in browser_activity: {existing_sessions}")
                        if existing_sessions and session_id not in existing_sessions:
                            print(f"[GENERATOR] ERROR: Session ID mismatch! Looking for {session_id} but found {existing_sessions[0]}")
                except Exception as e:
                    print(f"[GENERATOR] Error checking existing sessions: {e}")
            return None

        print(f"[GENERATOR] Sorting events...")
        events.sort(key=lambda item: item[0])
        print(f"[GENERATOR] Events sorted. First event: {events[0][0] if events else 'N/A'}, Last event: {events[-1][0] if events else 'N/A'}")

        mode = (generation_mode or "both").lower()
        if mode not in {"cursor", "gpt", "both"}:
            mode = "both"
        cursor_enabled = mode in {"cursor", "both"}
        gpt_enabled = mode in {"gpt", "both"}

        body_lines = []
        for idx, (timestamp, kind, payload) in enumerate(events, 1):
            if kind == "navigate":
                url = payload or "about:blank"
                body_lines.append(f"    # Step {idx}: Navigate")
                body_lines.append(f"    driver.get(\"{url}\")")
                body_lines.append("")
            elif kind == "interaction":
                row = payload
                try:
                    row_dict = dict(row) if hasattr(row, 'keys') else row
                except (TypeError, AttributeError):
                    row_dict = row if isinstance(row, dict) else {}
                action = row_dict.get("action_type") or "interaction"
                element = row_dict.get("element_id") or row_dict.get("element_name") or "element"
                body_lines.append(f"    # Step {idx}: {action} on {element}")
                body_lines.append("    # TODO: add Selenium interaction here")
                body_lines.append("")
            elif kind == "excel_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except (TypeError, AttributeError):
                    row_dict = row if isinstance(row, dict) else {}
                workbook = row_dict.get("workbook_name", "Unknown")
                worksheet = row_dict.get("worksheet_name", "Unknown")
                cell = row_dict.get("cell_reference", "Unknown")
                action = row_dict.get("action_type", "activity")
                body_lines.append(f"    # Step {idx}: Excel {action} - {workbook}/{worksheet} cell {cell}")
                body_lines.append("    # TODO: add Excel automation (openpyxl, xlwings, or COM automation)")
                body_lines.append("")
            elif kind == "browser_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except (TypeError, AttributeError):
                    row_dict = row if isinstance(row, dict) else {}
                browser = row_dict.get("browser_name", "Browser")
                url = row_dict.get("url", "")
                page_title = row_dict.get("page_title", "")
                action = row_dict.get("action_type", "navigation")
                if url:
                    body_lines.append(f"    # Step {idx}: {browser} {action} - {url}")
                else:
                    body_lines.append(f"    # Step {idx}: {browser} {action} - {page_title}")
                body_lines.append("    # TODO: add browser automation (Selenium, Playwright, etc.)")
                body_lines.append("")
            elif kind == "pdf_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except (TypeError, AttributeError):
                    row_dict = row if isinstance(row, dict) else {}
                pdf_file = row_dict.get("pdf_file_name", "Unknown PDF")
                pdf_path = row_dict.get("pdf_file_path", "")
                action = row_dict.get("action_type", "activity")
                viewer = row_dict.get("pdf_viewer_app", "PDF Viewer")
                body_lines.append(f"    # Step {idx}: PDF {action} - {pdf_file} ({viewer})")
                if pdf_path:
                    body_lines.append(f"    # PDF Path: {pdf_path}")
                body_lines.append("    # TODO: add PDF automation (PyPDF2, pdfplumber, or Adobe Acrobat COM)")
                body_lines.append("")

        print(f"[GENERATOR] Total events collected: {len(events)}")
        
        if not events:
            print(f"[GENERATOR] ERROR: No events found for session {session_id}. Cannot generate prototype.")
            print(f"[GENERATOR] Searched in:")
            print(f"  - Browser DB: {browser_db} (exists: {browser_db.exists()})")
            print(f"  - Full Monitoring DB: {full_monitoring_db} (exists: {full_monitoring_db.exists()})")
            if full_monitoring_db.exists():
                # Check what session IDs exist in the database
                try:
                    with sqlite3.connect(full_monitoring_db) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT DISTINCT session_id FROM browser_activity LIMIT 10")
                        existing_sessions = [row[0] for row in cursor.fetchall()]
                        print(f"[GENERATOR] Existing session IDs in browser_activity: {existing_sessions}")
                        
                        # Also check other tables
                        for table in ["excel_activity", "pdf_activity", "mouse_activity", "keyboard_input"]:
                            try:
                                cursor.execute(f"SELECT DISTINCT session_id FROM {table} LIMIT 5")
                                table_sessions = [row[0] for row in cursor.fetchall()]
                                if table_sessions:
                                    print(f"[GENERATOR] Session IDs in {table}: {table_sessions}")
                            except:
                                pass
                except Exception as e:
                    print(f"[GENERATOR] Error checking database: {e}")
            return None
        
        # Create folder named "[Title] Training Session Data"
        folder_name = f"{title} Training Session Data"
        output_path = self.output_dir / folder_name
        print(f"[DEBUG] Creating output folder: {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] Output folder created: {output_path.exists()}")
        
        # Create screenshots subfolder for this session
        screenshots_session_dir = output_path / "screenshots"
        screenshots_session_dir.mkdir(exist_ok=True)

        script_contents = SCRIPT_TEMPLATE.format(
            pattern_hash=session_id,
            generated_at=datetime.now().isoformat(),
            body="\n".join(body_lines) if body_lines else "    pass",
        )
        (output_path / "prototype.py").write_text(script_contents, encoding="utf-8")

        summary_payload = {
            "pattern_hash": session_id,
            "pattern_type": "trained_session",
            "frequency": len(events),
            "total_sessions": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "display_name": title,
            "generation_mode": mode,
            "cursor_notes": cursor_notes,
            "screen_capture": screen_manifest,
            "steps": [
                {"action": kind, "data": payload if isinstance(payload, str) else dict(payload)}
                for _, kind, payload in events[:20]
            ],
        }
        (output_path / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        if screen_manifest:
            try:
                (output_path / "screen_manifest.json").write_text(
                    json.dumps(screen_manifest, indent=2),
                    encoding="utf-8",
                )
            except Exception:
                pass

        if cursor_enabled:
            cursor_prompt = self._build_cursor_prompt(title, session_id, events, cursor_notes)
            (output_path / "cursor_prompt.txt").write_text(cursor_prompt, encoding="utf-8")

        if gpt_enabled:
            gpt_report = self._generate_session_gpt_report(title, session_id, events, cursor_notes, output_path)
            if gpt_report:
                (output_path / "gpt_report.md").write_text(gpt_report, encoding="utf-8")
        
        # Copy screenshots to output folder
        screenshot_dir = self.installation_dir / "_secure_data" / "full_monitoring" / "browser_screenshots"
        screenshots_session_dir = output_path / "screenshots"
        if screenshot_dir.exists():
            import shutil
            for screenshot_file in screenshot_dir.glob(f"click_{session_id}_*.png"):
                try:
                    shutil.copy2(screenshot_file, screenshots_session_dir / screenshot_file.name)
                except Exception as e:
                    print(f"Could not copy screenshot {screenshot_file}: {e}")
        
        # Create a comprehensive README/index file for easy review
        readme_content = self._create_session_readme(title, session_id, events, output_path, screen_manifest, cursor_notes)
        (output_path / "README.md").write_text(readme_content, encoding="utf-8")
        
        # Create a quick reference file with key paths
        paths_file = {
            "session_id": session_id,
            "workflow_title": title,
            "generated_at": datetime.now().isoformat(),
            "total_events": len(events),
            "files_in_folder": {
                "gpt_report": "gpt_report.md" if gpt_enabled and (output_path / "gpt_report.md").exists() else None,
                "prototype_code": "prototype.py",
                "summary_data": "summary.json",
                "cursor_prompt": "cursor_prompt.txt" if cursor_enabled and (output_path / "cursor_prompt.txt").exists() else None,
                "screen_manifest": "screen_manifest.json" if screen_manifest and (output_path / "screen_manifest.json").exists() else None,
                "readme": "README.md"
            },
            "monitoring_data_location": str(self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db"),
            "browser_activity_location": str(self.installation_dir / "_secure_data" / "browser_activity.db")
        }
        (output_path / "session_info.json").write_text(json.dumps(paths_file, indent=2), encoding="utf-8")

        self.execution_repo.register_prototype(session_id, output_path, description=title)
        return output_path

    def _build_cursor_prompt(
        self,
        title: str,
        session_id: str,
        events: list,
        cursor_notes: Optional[str] = None,
    ) -> str:
        lines = [
            f"Workflow Title: {title}",
            f"Session ID: {session_id}",
            f"Generated At: {datetime.now().isoformat()}",
            f"Total Recorded Events: {len(events)}",
        ]
        if cursor_notes:
            lines.append(f"Team Notes: {cursor_notes.strip()}")
        lines.extend([
            "",
            "### Steps Captured During Training",
        ])

        for idx, (_, kind, payload) in enumerate(events, 1):
            if kind == "navigate":
                url = payload or "about:blank"
                lines.append(f"{idx}. Navigate to {url}")
            else:
                row = payload
                try:
                    row_dict = dict(row)
                except Exception:
                    row_dict = {}
                action = row_dict.get("action_type") or "interaction"
                target = row_dict.get("element_name") or row_dict.get("element_id") or row_dict.get("element_tag") or "page element"
                lines.append(f"{idx}. {action.title()} on {target}")

        lines.extend(
            [
                "",
                "Provide Selenium-compatible code for each step. Use `cursor_notes` above for business context.",
                "Reference automation assets under AI/automation_prototypes if needed.",
            ]
        )
        return "\n".join(lines)

    def _generate_session_gpt_report(
        self,
        title: str,
        session_id: str,
        events: list,
        cursor_notes: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[str]:
        if not self.llm_service.available() or not self.llm_service.is_configured():
            print(f"GPT report skipped: LLM service not available or not configured")
            return None
        
        print(f"Generating GPT report for session {session_id} with {len(events)} events...")

        step_descriptions = []
        for idx, (_, kind, payload) in enumerate(events, 1):
            if kind == "navigate":
                url = payload or "about:blank"
                step_descriptions.append(f"{idx}. Navigate to {url}")
            elif kind == "interaction":
                row = payload
                try:
                    row_dict = dict(row)
                except Exception:
                    row_dict = {}
                action = row_dict.get("action_type") or "interaction"
                target = row_dict.get("element_name") or row_dict.get("element_id") or row_dict.get("element_tag") or "page element"
                step_descriptions.append(f"{idx}. {action.title()} on {target}")
            elif kind == "excel_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except Exception:
                    row_dict = {}
                workbook = row_dict.get("workbook_name", "Unknown")
                worksheet = row_dict.get("worksheet_name", "Unknown")
                cell = row_dict.get("cell_reference", "Unknown")
                cell_value = row_dict.get("cell_value", "")
                formula = row_dict.get("formula", "")
                action = row_dict.get("action_type", "activity")
                desc = f"{idx}. Excel {action}: {workbook}/{worksheet} cell {cell}"
                if cell_value:
                    desc += f" (value: {cell_value[:50]})"
                if formula:
                    desc += f" (formula: {formula[:50]})"
                step_descriptions.append(desc)
            elif kind == "browser_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except Exception:
                    row_dict = {}
                browser = row_dict.get("browser_name", "Browser")
                url = row_dict.get("url", "")
                page_title = row_dict.get("page_title", "")
                action = row_dict.get("action_type", "navigation")
                if url:
                    step_descriptions.append(f"{idx}. {browser} {action}: {url}")
                else:
                    step_descriptions.append(f"{idx}. {browser} {action}: {page_title}")
            elif kind == "pdf_activity":
                row = payload
                try:
                    row_dict = dict(row)
                except Exception:
                    row_dict = {}
                pdf_file = row_dict.get("pdf_file_name", "Unknown PDF")
                action = row_dict.get("action_type", "activity")
                viewer = row_dict.get("pdf_viewer_app", "PDF Viewer")
                form_field = row_dict.get("form_field_name", "")
                if form_field:
                    step_descriptions.append(f"{idx}. PDF {action}: {pdf_file} - Form field '{form_field}' ({viewer})")
                else:
                    step_descriptions.append(f"{idx}. PDF {action}: {pdf_file} ({viewer})")

        prompt_sections = [
            f"Workflow Title: {title}",
            f"Session ID: {session_id}",
            f"Total Recorded Events: {len(events)}",
        ]
        if cursor_notes:
            prompt_sections.append(f"Team Notes: {cursor_notes.strip()}")
        prompt_sections.append("")
        prompt_sections.append("Captured Steps (chronological):")
        prompt_sections.extend(step_descriptions)

        # Collect screenshots for Vision API analysis
        screenshots_with_context = []
        screenshot_dir = self.installation_dir / "_secure_data" / "full_monitoring" / "browser_screenshots"
        
        for idx, (_, kind, payload) in enumerate(events, 1):
            if kind == "browser_activity":
                try:
                    row_dict = dict(payload) if hasattr(payload, 'keys') else payload
                    screenshot_path = row_dict.get("screenshot_path", "")
                    action = row_dict.get("action_type", "")
                    element_name = row_dict.get("element_name", "")
                    
                    if screenshot_path and action == "click":
                        full_screenshot_path = self.installation_dir / "_secure_data" / "full_monitoring" / screenshot_path
                        if full_screenshot_path.exists():
                            screenshots_with_context.append({
                                "step": idx,
                                "path": full_screenshot_path,
                                "action": action,
                                "element": element_name,
                                "description": f"Step {idx}: {action} - {element_name}"
                            })
                except:
                    pass

        prompt = "\n".join(prompt_sections)
        
        # Add screenshot references to prompt if available
        if screenshots_with_context:
            prompt += "\n\n## Screenshots Captured During Workflow\n\n"
            prompt += "The following screenshots were captured during browser interactions. "
            prompt += "These images show what was clicked when element details could not be automatically extracted:\n\n"
            for screenshot_info in screenshots_with_context:
                prompt += f"- {screenshot_info['description']}\n"
            prompt += "\nThese screenshots will be analyzed using OpenAI Vision API to identify UI elements and actions."

        system_prompt = (
            "You are an enterprise automation architect specializing in workflow automation and bot development. "
            "Your task is to analyze the recorded workflow data and provide:\n\n"
            "1. **Workflow Summary**: A clear, business-friendly description of what the workflow accomplishes\n"
            "2. **Automation Strategy**: Step-by-step automation plan with specific technical recommendations\n"
            "3. **Code Generation Guidance**: Detailed instructions for translating this workflow into executable bot code\n"
            "4. **Risk Assessment**: Potential issues, edge cases, and error handling requirements\n"
            "5. **Optimization Opportunities**: Ways to streamline or improve the workflow\n"
            "6. **Implementation Readiness**: Score (1-10) indicating how ready this workflow is for automation\n\n"
            "Format your response as Markdown with clear sections. Be specific about:\n"
            "- UI elements to interact with (buttons, forms, fields)\n"
            "- Navigation patterns and page transitions\n"
            "- Data extraction points and validation requirements\n"
            "- Error handling and retry logic\n"
            "- Dependencies and prerequisites\n\n"
            "The goal is to enable a developer to create a fully functional automation bot from your analysis."
        )

        try:
            print(f"[GPT] Calling OpenAI API with prompt length: {len(prompt)} characters...")
            print(f"[GPT] Screenshots collected: {len(screenshots_with_context)}")
            
            # Generate comprehensive workflow analysis with Vision API support
            report = None
            try:
                # If we have screenshots, use Vision API
                if screenshots_with_context:
                    print(f"[GPT] Using Vision API with {len(screenshots_with_context)} screenshots...")
                    print(f"[GPT] This may take 30-90 seconds...")
                    report = self.llm_service.generate_summary_with_images(
                        prompt, 
                        system_prompt=system_prompt, 
                        max_tokens=2000,
                        images=[s["path"] for s in screenshots_with_context]
                    )
                    print(f"[GPT] Vision API call completed")
                else:
                    print(f"[GPT] Using text-only API (no screenshots)...")
                    print(f"[GPT] This may take 30-60 seconds...")
                    report = self.llm_service.generate_summary(prompt, system_prompt=system_prompt, max_tokens=2000)
                    print(f"[GPT] Text-only API call completed")
            except Exception as api_error:
                print(f"[GPT] ERROR: OpenAI API call failed: {api_error}")
                import traceback
                print(f"[GPT] Traceback: {traceback.format_exc()}")
                # Fallback to text-only if Vision API fails
                if screenshots_with_context:
                    print(f"[GPT] Attempting fallback to text-only API...")
                    try:
                        report = self.llm_service.generate_summary(prompt, system_prompt=system_prompt, max_tokens=2000)
                        print(f"[GPT] Fallback successful")
                    except Exception as fallback_error:
                        print(f"[GPT] ERROR: Fallback also failed: {fallback_error}")
                        raise
                else:
                    raise
            
            if report:
                print(f"GPT report generated successfully ({len(report)} characters)")
                # Add metadata header
                header = f"# Workflow Analysis: {title}\n\n"
                header += f"**Session ID**: `{session_id}`\n"
                header += f"**Total Events**: {len(events)}\n"
                header += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                header += "---\n\n"
                return header + report
            else:
                print("GPT report generation returned None (empty response)")
            return None
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error generating GPT report: {e}")
            print(f"Traceback: {error_trace}")
            return None
    
    def _create_session_readme(self, title: str, session_id: str, events: list, output_path: Path, 
                               screen_manifest: Optional[Dict[str, Any]], cursor_notes: Optional[str]) -> str:
        """Create a comprehensive README file for the training session folder"""
        lines = [
            f"# {title} - Training Session Data",
            "",
            f"**Session ID**: `{session_id}`",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Events Recorded**: {len(events)}",
            "",
            "---",
            "",
            "## 📁 Contents of This Folder",
            "",
            "This folder contains all data from your workflow training session:",
            "",
            "### Core Files",
            "",
            "1. **`gpt_report.md`** - AI-generated workflow analysis and automation recommendations",
            "   - Workflow summary",
            "   - Automation strategy",
            "   - Code generation guidance",
            "   - Risk assessment",
            "   - Implementation readiness score",
            "",
            "2. **`prototype.py`** - Automation code template",
            "   - Selenium-based automation script",
            "   - Includes all captured steps as code comments",
            "   - Ready for customization and execution",
            "",
            "3. **`summary.json`** - Complete session metadata",
            "   - All recorded events in JSON format",
            "   - Timestamps, actions, and context",
            "   - Screen capture references",
            "",
            "4. **`cursor_prompt.txt`** - Manual build instructions (if enabled)",
            "   - Step-by-step workflow description",
            "   - Ready to paste into Cursor AI for code generation",
            "",
            "5. **`screen_manifest.json`** - Screen capture manifest (if available)",
            "   - References to all screenshots taken during the session",
            "   - Frame timestamps and locations",
            "",
            "6. **`session_info.json`** - Quick reference file",
            "   - Session metadata",
            "   - File locations and paths",
            "",
            "---",
            "",
            "## 📊 Session Statistics",
            "",
        ]
        
        # Count event types
        event_counts = {}
        for _, kind, _ in events:
            event_counts[kind] = event_counts.get(kind, 0) + 1
        
        lines.append("**Event Breakdown:**")
        lines.append("")
        for event_type, count in sorted(event_counts.items()):
            event_name = event_type.replace("_", " ").title()
            lines.append(f"- {event_name}: {count}")
        
        lines.extend([
            "",
            "---",
            "",
            "## 🔍 What Was Recorded",
            "",
        ])
        
        # Add summary of what was captured
        has_excel = any(kind == "excel_activity" for _, kind, _ in events)
        has_browser = any(kind in ["browser_activity", "navigate", "interaction"] for _, kind, _ in events)
        has_pdf = any(kind == "pdf_activity" for _, kind, _ in events)
        
        if has_excel:
            lines.append("✅ **Excel Activity** - Workbooks, worksheets, cells, formulas, and data entry")
        if has_browser:
            lines.append("✅ **Browser Activity** - URLs, page navigations, form interactions")
        if has_pdf:
            lines.append("✅ **PDF Activity** - PDF files opened, modified, form fields")
        
        lines.extend([
            "✅ **Screen Recordings** - Screenshots captured during the session",
            "✅ **Keyboard Input** - All keystrokes with context",
            "✅ **Mouse Activity** - Clicks, movements, and scrolls",
            "✅ **Application Usage** - All apps opened and window titles",
            "✅ **File System Activity** - Files created, modified, and saved",
            "",
            "---",
            "",
            "## 📍 Raw Data Location",
            "",
            "The raw monitoring data is stored in:",
            "",
            f"`{self.installation_dir / '_secure_data' / 'full_monitoring' / 'full_monitoring.db'}`",
            "",
            "This SQLite database contains all detailed monitoring data for this session.",
            "",
            "---",
            "",
            "## 🚀 Next Steps",
            "",
            "1. **Review the GPT Report** - Open `gpt_report.md` to see AI analysis and recommendations",
            "2. **Check the Prototype Code** - Open `prototype.py` to see the automation template",
            "3. **Review Session Summary** - Open `summary.json` to see all captured events",
            "4. **Use Cursor Prompt** - If available, use `cursor_prompt.txt` with Cursor AI for code generation",
            "",
            "---",
            "",
        ])
        
        if cursor_notes:
            lines.extend([
                "## 📝 Session Notes",
                "",
                cursor_notes,
                "",
                "---",
                "",
            ])
        
        lines.append(f"*Session completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)
