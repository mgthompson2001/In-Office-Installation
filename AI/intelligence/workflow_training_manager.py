#!/usr/bin/env python3
"""Workflow training session manager."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sys

try:
    from monitoring.full_system_monitor import (
        get_full_monitor,
        start_full_monitoring,
        stop_full_monitoring,
    )
except ImportError:
    ai_root = Path(__file__).resolve().parents[1]
    monitoring_dir = ai_root / "monitoring"
    if str(monitoring_dir) not in sys.path:
        sys.path.insert(0, str(monitoring_dir))
    from full_system_monitor import get_full_monitor, start_full_monitoring, stop_full_monitoring

try:
    from monitoring.screen_recorder import create_screen_recorder, ScreenRecorder
except ImportError:
    ai_root = Path(__file__).resolve().parents[1]
    monitoring_dir = ai_root / "monitoring"
    if str(monitoring_dir) not in sys.path:
        sys.path.insert(0, str(monitoring_dir))
    try:
        from screen_recorder import create_screen_recorder, ScreenRecorder
    except Exception:
        create_screen_recorder = None  # type: ignore
        ScreenRecorder = None  # type: ignore

from automation_prototype_generator import AutomationPrototypeGenerator
try:
    from monitoring.session_pipeline import MonitoringSessionPipeline
except ImportError:
    ai_root = Path(__file__).resolve().parents[1]
    monitoring_dir = ai_root / 'monitoring'
    if str(monitoring_dir) not in sys.path:
        sys.path.insert(0, str(monitoring_dir))
    try:
        from session_pipeline import MonitoringSessionPipeline
    except Exception:
        MonitoringSessionPipeline = None  # type: ignore


@dataclass
class TrainingSessionMetadata:
    title: str
    session_id: str
    started_at: datetime
    generation_mode: str = "both"
    cursor_notes: Optional[str] = None
    screen_capture_dir: Optional[Path] = None
    screen_manifest: Optional[Dict[str, Any]] = None


class WorkflowTrainingManager:
    """Coordinates single-workflow training captures."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.generator = AutomationPrototypeGenerator(self.installation_dir)
        self.logger = logging.getLogger(__name__)
        self.session_pipeline = None
        try:
            if 'MonitoringSessionPipeline' in globals() and MonitoringSessionPipeline is not None:
                self.session_pipeline = MonitoringSessionPipeline(self.installation_dir, retention_days=3, max_database_gb=1.5, event_limit=2000)
        except Exception:
            self.logger.warning('Monitoring session pipeline unavailable.', exc_info=True)
        self.screen_recorder: Optional[ScreenRecorder] = None
        if create_screen_recorder:
            try:
                self.screen_recorder = create_screen_recorder(self.installation_dir)
            except Exception:
                self.screen_recorder = None

    def start_training(
        self,
        title: str,
        *,
        generation_mode: str = "both",
        cursor_notes: Optional[str] = None,
    ) -> TrainingSessionMetadata:
        # Check if monitoring is already running from a different source
        monitor = get_full_monitor(self.installation_dir, user_consent=True)
        if monitor and getattr(monitor, "monitoring_active", False):
            # If monitoring is already active, use the existing session
            print(f"[DEBUG] Using existing active monitoring session: {monitor.session_id}")
            session_id = getattr(monitor, "session_id", datetime.now().strftime("session_%Y%m%d_%H%M%S"))
        else:
            # Start fresh monitoring - clicking "Start Training" IS the consent
            print(f"[DEBUG] Starting new monitoring session for training...")
            try:
                monitor_instance = start_full_monitoring(self.installation_dir, user_consent=True)
                print(f"[DEBUG] start_full_monitoring returned: {monitor_instance}")
                print(f"[DEBUG] Monitor monitoring_active: {getattr(monitor_instance, 'monitoring_active', 'N/A')}")
                print(f"[DEBUG] Monitor session_id: {getattr(monitor_instance, 'session_id', 'N/A')}")
            except Exception as e:
                import traceback
                print(f"[ERROR] Failed to start monitoring: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Failed to start monitoring: {e}")

            # Give monitor a moment to initialise
            print(f"[DEBUG] Waiting for monitoring to initialize...")
            time.sleep(3)  # Increased wait time to ensure monitoring starts
            monitor = get_full_monitor(self.installation_dir, user_consent=True)
            
            # CRITICAL: Verify that monitoring actually started
            if not monitor:
                raise RuntimeError("Monitoring system failed to initialize. Please check system requirements.")
            
            monitoring_active = getattr(monitor, "monitoring_active", False)
            print(f"[DEBUG] After wait, monitoring_active: {monitoring_active}")
            
            if not monitoring_active:
                # Try one more time after a longer wait
                print(f"[DEBUG] Monitoring not active, waiting longer...")
                time.sleep(2)
                monitor = get_full_monitor(self.installation_dir, user_consent=True)
                monitoring_active = getattr(monitor, "monitoring_active", False)
                print(f"[DEBUG] After second wait, monitoring_active: {monitoring_active}")
                
                if not monitoring_active:
                    # Check if there's an error in the log
                    log_path = self.installation_dir / "_secure_data" / "full_monitoring" / "monitoring.log"
                    last_log_lines = []
                    if log_path.exists():
                        try:
                            with open(log_path, 'r') as f:
                                lines = f.readlines()
                                last_log_lines = lines[-10:] if len(lines) > 10 else lines
                        except:
                            pass
                    
                    error_msg = (
                        "Monitoring failed to start. Training cannot proceed without active monitoring.\n\n"
                        "Please check:\n"
                        "- System permissions\n"
                        "- No other monitoring processes running\n"
                        "- Try restarting the application\n\n"
                    )
                    if last_log_lines:
                        error_msg += "Last log entries:\n" + "".join(last_log_lines[-5:])
                    
                    raise RuntimeError(error_msg)
            
            # CRITICAL: Use the monitor's session_id to ensure they match
            monitor_session_id = getattr(monitor, "session_id", None)
            if monitor_session_id:
                session_id = monitor_session_id
                print(f"[DEBUG] Using monitor's session_id: {session_id}")
            else:
                # Fallback: create a new session_id and update the monitor
                session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
                print(f"[DEBUG] Monitor has no session_id, creating new one: {session_id}")
                # Update monitor's session_id to match
                if hasattr(monitor, 'session_id'):
                    monitor.session_id = session_id
                    print(f"[DEBUG] Updated monitor's session_id to match training session")
            
            print(f"[DEBUG] Training started with session_id: {session_id}, monitoring_active: {monitor.monitoring_active}")
            print(f"[DEBUG] Monitor's session_id: {getattr(monitor, 'session_id', 'N/A')}")
            
            # Verify database was created
            db_path = monitor.db_path if hasattr(monitor, 'db_path') else None
            if db_path:
                print(f"[DEBUG] Database path: {db_path}")
                print(f"[DEBUG] Database exists: {db_path.exists() if db_path else False}")

        mode = (generation_mode or "both").lower()
        if mode not in {"cursor", "gpt", "both"}:
            mode = "both"

        screen_dir: Optional[Path] = None
        if self.screen_recorder:
            try:
                screen_dir = self.screen_recorder.start(session_id)
            except Exception:
                screen_dir = None

        return TrainingSessionMetadata(
            title=title,
            session_id=session_id,
            started_at=datetime.now(),
            generation_mode=mode,
            cursor_notes=cursor_notes,
            screen_capture_dir=screen_dir,
        )

    def end_training(
        self,
        metadata: TrainingSessionMetadata,
        *,
        generation_mode: Optional[str] = None,
        cursor_notes: Optional[str] = None,
    ) -> Optional[Path]:
        print(f"[DEBUG] end_training called for session: {metadata.session_id}")
        
        # Get monitor before stopping to check metrics
        monitor = get_full_monitor(self.installation_dir, user_consent=True)
        if monitor:
            metrics = monitor.get_metrics()
            print(f"[DEBUG] Metrics before stopping:")
            print(f"  - Screens recorded: {metrics.get('screens_recorded', 0)}")
            print(f"  - Keystrokes recorded: {metrics.get('keystrokes_recorded', 0)}")
            print(f"  - Mouse events recorded: {metrics.get('mouse_events_recorded', 0)}")
            print(f"  - Browser events recorded: {metrics.get('browser_events_recorded', 0)}")
            print(f"  - Excel events recorded: {metrics.get('excel_events_recorded', 0)}")
            print(f"  - Monitoring active: {monitor.monitoring_active}")
            print(f"  - Monitor Session ID: {monitor.session_id}")
            print(f"  - Training Session ID: {metadata.session_id}")
            
            # CRITICAL: If session IDs don't match, update monitor's session_id to match training
            if monitor.session_id != metadata.session_id:
                print(f"[WARNING] Session ID mismatch detected!")
                print(f"  Monitor has: {monitor.session_id}")
                print(f"  Training expects: {metadata.session_id}")
                print(f"[DEBUG] Updating monitor's session_id to match training session...")
                # Update all pending records in the queue to use the correct session_id
                # This is a workaround - ideally we'd prevent the mismatch in the first place
                monitor.session_id = metadata.session_id
                print(f"[DEBUG] Monitor session_id updated to: {monitor.session_id}")
        
        stop_full_monitoring()
        print(f"[DEBUG] Monitoring stopped")

        # wait longer for data flush - buffers need time to write
        print(f"[DEBUG] Waiting for data buffers to flush to database...")
        time.sleep(5)  # Increased to 5 seconds to ensure all data is flushed
        print(f"[DEBUG] Data flush wait complete")
        
        # Verify events are in database before proceeding
        print(f"[DEBUG] Verifying events in database for session: {metadata.session_id}")
        full_monitoring_db = self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db"
        if full_monitoring_db.exists():
            import sqlite3
            with sqlite3.connect(full_monitoring_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM browser_activity WHERE session_id = ?", (metadata.session_id,))
                browser_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM mouse_activity WHERE session_id = ?", (metadata.session_id,))
                mouse_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM keyboard_input WHERE session_id = ?", (metadata.session_id,))
                key_count = cursor.fetchone()[0]
                total_db_events = browser_count + mouse_count + key_count
                print(f"[DEBUG] Database event counts for session {metadata.session_id}:")
                print(f"  - Browser: {browser_count}")
                print(f"  - Mouse: {mouse_count}")
                print(f"  - Keyboard: {key_count}")
                print(f"  - Total: {total_db_events}")
                
                # If no events found, check what session IDs exist
                if total_db_events == 0:
                    cursor.execute("SELECT DISTINCT session_id FROM browser_activity ORDER BY session_id DESC LIMIT 5")
                    other_sessions = [row[0] for row in cursor.fetchall()]
                    if other_sessions:
                        print(f"[WARNING] No events found for session {metadata.session_id}")
                        print(f"[WARNING] Found events with other session IDs: {other_sessions}")
                        print(f"[WARNING] This suggests a session ID mismatch - events may be under a different session ID")
        mode = (generation_mode or metadata.generation_mode or "both")
        notes = cursor_notes if cursor_notes is not None else metadata.cursor_notes
        print(f"[DEBUG] Generation mode: {mode}, notes: {bool(notes)}")
        
        screen_manifest: Optional[Dict[str, Any]] = None
        if self.screen_recorder:
            try:
                screen_manifest = self.screen_recorder.stop()
                if screen_manifest:
                    metadata.screen_manifest = screen_manifest
            except Exception:
                screen_manifest = None
        print(f"[DEBUG] Calling generator.generate_from_session with session_id: {metadata.session_id}")
        try:
            bundle_path = self.generator.generate_from_session(
                metadata.session_id,
                metadata.title,
                generation_mode=mode,
                cursor_notes=notes,
                screen_manifest=screen_manifest,
            )
            print(f"[DEBUG] generator.generate_from_session returned: {bundle_path}")
        except Exception as e:
            import traceback
            print(f"[ERROR] Error in generate_from_session: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise

        if self.session_pipeline:
            try:
                self.session_pipeline.process_session(
                    metadata.session_id,
                    workflow_title=metadata.title,
                    cleanup=True,
                )
            except Exception:
                self.logger.warning('Failed to run monitoring session pipeline for %s', metadata.session_id, exc_info=True)

        return bundle_path
