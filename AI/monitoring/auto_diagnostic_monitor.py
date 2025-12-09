#!/usr/bin/env python3
"""
Automatic Diagnostic Monitor
Runs diagnostics automatically while bots are running to ensure browser activity is being recorded.
"""

import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging


class AutoDiagnosticMonitor:
    """
    Automatic diagnostic monitor that runs in the background
    to verify browser activity recording is working.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None, check_interval: int = 30):
        """
        Initialize automatic diagnostic monitor.
        
        Args:
            installation_dir: Installation directory path
            check_interval: How often to run diagnostics (seconds)
        """
        if installation_dir is None:
            _current_file = Path(__file__).resolve()
            if "In-Office Installation" in str(_current_file):
                installation_dir = _current_file.parent.parent
            else:
                installation_dir = Path.cwd()
                if "_bots" in str(installation_dir):
                    installation_dir = installation_dir.parent
        
        self.installation_dir = installation_dir
        self.secure_data_dir = installation_dir / "_secure_data"
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread = None
        
        # Setup logging
        self.log_file = self.secure_data_dir / "diagnostic_monitor.log"
        self._setup_logging()
        
        # Track diagnostic history
        self.diagnostic_history: List[Dict] = []
        self.max_history = 100
        
    def _setup_logging(self):
        """Setup logging for diagnostic monitor"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AutoDiagnosticMonitor')
    
    def start(self):
        """Start automatic diagnostic monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Automatic diagnostic monitor started")
    
    def stop(self):
        """Stop automatic diagnostic monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Automatic diagnostic monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._run_diagnostics()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Error in diagnostic monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def _run_diagnostics(self):
        """Run diagnostic checks"""
        try:
            diagnostic_result = {
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            }
            
            # Check 1: Database exists and is accessible
            db_path = self.secure_data_dir / "browser_activity.db"
            db_accessible = db_path.exists()
            diagnostic_result["checks"]["database_accessible"] = db_accessible
            
            if not db_accessible:
                self.logger.warning("Database not accessible - browser activity may not be recorded")
                return
            
            # Check 2: Recent session activity
            recent_sessions = self._check_recent_sessions()
            diagnostic_result["checks"]["recent_sessions"] = recent_sessions
            
            # Check 3: Events being recorded
            events_recorded = self._check_events_recorded()
            diagnostic_result["checks"]["events_recorded"] = events_recorded
            
            # Check 4: Activity buffer status
            buffer_status = self._check_activity_buffer()
            diagnostic_result["checks"]["buffer_status"] = buffer_status
            
            # Check 5: Background processing thread
            thread_status = self._check_background_thread()
            diagnostic_result["checks"]["thread_status"] = thread_status
            
            # Store diagnostic result
            self.diagnostic_history.append(diagnostic_result)
            if len(self.diagnostic_history) > self.max_history:
                self.diagnostic_history.pop(0)
            
            # Log warnings if issues detected
            if not events_recorded.get("has_recent_events", False):
                self.logger.warning(
                    f"No events recorded in last {events_recorded.get('time_window', 'N/A')} seconds. "
                    f"Last event: {events_recorded.get('last_event_time', 'Never')}"
                )
            
            if buffer_status.get("buffer_size", 0) > 50:
                self.logger.warning(
                    f"Activity buffer has {buffer_status['buffer_size']} unprocessed records. "
                    "Events may not be flushed to database."
                )
            
            if not thread_status.get("thread_running", False):
                self.logger.error("Background processing thread is NOT running! Events may not be flushed.")
            
            # Log summary
            self.logger.debug(
                f"Diagnostic check: {recent_sessions.get('count', 0)} recent sessions, "
                f"{events_recorded.get('total_events', 0)} total events, "
                f"{buffer_status.get('buffer_size', 0)} buffered records"
            )
            
        except Exception as e:
            self.logger.error(f"Error running diagnostics: {e}")
    
    def _check_recent_sessions(self) -> Dict:
        """Check for recent session activity"""
        try:
            db_path = self.secure_data_dir / "browser_activity.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check sessions in last hour
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT COUNT(*), MAX(start_time)
                FROM session_summaries
                WHERE start_time > ?
            """, (one_hour_ago,))
            
            result = cursor.fetchone()
            count = result[0] if result else 0
            last_session = result[1] if result and result[1] else None
            
            conn.close()
            
            return {
                "count": count,
                "last_session": last_session,
                "has_recent_sessions": count > 0
            }
        except Exception as e:
            self.logger.error(f"Error checking recent sessions: {e}")
            return {"count": 0, "last_session": None, "has_recent_sessions": False}
    
    def _check_events_recorded(self) -> Dict:
        """Check if events are being recorded"""
        try:
            db_path = self.secure_data_dir / "browser_activity.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check events in last 5 minutes
            five_minutes_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
            
            # Check page navigations
            cursor.execute("""
                SELECT COUNT(*), MAX(timestamp)
                FROM page_navigations
                WHERE timestamp > ?
            """, (five_minutes_ago,))
            nav_result = cursor.fetchone()
            nav_count = nav_result[0] if nav_result else 0
            last_nav = nav_result[1] if nav_result and nav_result[1] else None
            
            # Check element interactions
            cursor.execute("""
                SELECT COUNT(*), MAX(timestamp)
                FROM element_interactions
                WHERE timestamp > ?
            """, (five_minutes_ago,))
            element_result = cursor.fetchone()
            element_count = element_result[0] if element_result else 0
            last_element = element_result[1] if element_result and element_result[1] else None
            
            # Get total events
            cursor.execute("SELECT COUNT(*) FROM page_navigations")
            total_navs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM element_interactions")
            total_elements = cursor.fetchone()[0]
            
            conn.close()
            
            total_recent = nav_count + element_count
            last_event_time = max(
                last_nav or "",
                last_element or ""
            ) if (last_nav or last_element) else None
            
            return {
                "has_recent_events": total_recent > 0,
                "recent_navigations": nav_count,
                "recent_interactions": element_count,
                "total_events": total_navs + total_elements,
                "last_event_time": last_event_time,
                "time_window": "5 minutes"
            }
        except Exception as e:
            self.logger.error(f"Error checking events recorded: {e}")
            return {
                "has_recent_events": False,
                "recent_navigations": 0,
                "recent_interactions": 0,
                "total_events": 0,
                "last_event_time": None,
                "time_window": "5 minutes"
            }
    
    def _check_activity_buffer(self) -> Dict:
        """Check activity buffer status"""
        try:
            from browser_activity_monitor import get_browser_monitor
            
            monitor = get_browser_monitor(self.installation_dir)
            buffer_size = len(monitor.activity_buffer) if monitor else 0
            
            return {
                "buffer_size": buffer_size,
                "has_buffered_records": buffer_size > 0,
                "buffer_healthy": buffer_size < 100
            }
        except Exception as e:
            self.logger.error(f"Error checking activity buffer: {e}")
            return {
                "buffer_size": 0,
                "has_buffered_records": False,
                "buffer_healthy": True
            }
    
    def _check_background_thread(self) -> Dict:
        """Check background processing thread status"""
        try:
            from browser_activity_monitor import get_browser_monitor
            
            monitor = get_browser_monitor(self.installation_dir)
            if monitor and monitor.processing_thread:
                thread_running = monitor.processing_thread.is_alive()
                return {
                    "thread_running": thread_running,
                    "thread_exists": True
                }
            else:
                return {
                    "thread_running": False,
                    "thread_exists": False
                }
        except Exception as e:
            self.logger.error(f"Error checking background thread: {e}")
            return {
                "thread_running": False,
                "thread_exists": False
            }
    
    def get_diagnostic_summary(self) -> Dict:
        """Get summary of recent diagnostics"""
        if not self.diagnostic_history:
            return {"status": "no_data", "message": "No diagnostic data available"}
        
        latest = self.diagnostic_history[-1]
        checks = latest.get("checks", {})
        
        # Determine overall status
        issues = []
        if not checks.get("events_recorded", {}).get("has_recent_events", False):
            issues.append("No recent events recorded")
        if checks.get("buffer_status", {}).get("buffer_size", 0) > 50:
            issues.append("Activity buffer has many unprocessed records")
        if not checks.get("thread_status", {}).get("thread_running", False):
            issues.append("Background processing thread not running")
        
        status = "healthy" if not issues else "issues_detected"
        
        return {
            "status": status,
            "timestamp": latest.get("timestamp"),
            "issues": issues,
            "checks": checks
        }
    
    def get_diagnostic_history(self, limit: int = 10) -> List[Dict]:
        """Get recent diagnostic history"""
        return self.diagnostic_history[-limit:] if self.diagnostic_history else []


# Global diagnostic monitor instance
_global_diagnostic_monitor = None


def get_diagnostic_monitor(installation_dir: Optional[Path] = None) -> AutoDiagnosticMonitor:
    """Get global diagnostic monitor instance"""
    global _global_diagnostic_monitor
    if _global_diagnostic_monitor is None:
        _global_diagnostic_monitor = AutoDiagnosticMonitor(installation_dir)
    return _global_diagnostic_monitor


def start_auto_diagnostics(installation_dir: Optional[Path] = None, check_interval: int = 30):
    """Start automatic diagnostic monitoring"""
    monitor = get_diagnostic_monitor(installation_dir)
    monitor.check_interval = check_interval
    monitor.start()
    return monitor


def stop_auto_diagnostics():
    """Stop automatic diagnostic monitoring"""
    global _global_diagnostic_monitor
    if _global_diagnostic_monitor:
        _global_diagnostic_monitor.stop()
        _global_diagnostic_monitor = None

