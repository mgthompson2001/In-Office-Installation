#!/usr/bin/env python3
"""
Context Understanding Engine - The Intelligence Layer
Transforms collected data into actionable understanding of WHY employees do tasks.

This is the critical missing piece that transforms data collection into autonomous capability.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import logging
import re

# Import existing components
try:
    from ai_activity_analyzer import AIActivityAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    AIActivityAnalyzer = None

try:
    from pattern_extraction_engine import PatternExtractionEngine
    PATTERN_ENGINE_AVAILABLE = True
except ImportError:
    PATTERN_ENGINE_AVAILABLE = False
    PatternExtractionEngine = None


class ContextUnderstandingEngine:
    """
    Context Understanding Engine - The Intelligence Layer
    
    Understands:
    - WHY employees do tasks (intent)
    - WHAT context actions occur in (context)
    - HOW actions relate to each other (dependencies)
    - WHAT the end goal is (goals)
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize Context Understanding Engine"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        self.intelligence_dir = ai_dir / "intelligence"
        self.data_dir = ai_dir / "data"
        self.models_dir = ai_dir / "models"
        
        # Create directories
        self.intelligence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.models_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Context database
        self.context_db = self.intelligence_dir / "context_understanding.db"
        self._init_context_database()
        
        # Setup logging
        self.log_file = self.intelligence_dir / "context_understanding.log"
        self._setup_logging()
        
        # Initialize components
        self.analyzer = None
        self.pattern_engine = None
        if ANALYZER_AVAILABLE:
            self.analyzer = AIActivityAnalyzer(installation_dir)
        if PATTERN_ENGINE_AVAILABLE:
            self.pattern_engine = PatternExtractionEngine(installation_dir)
        
        # Intent classification patterns
        self.intent_patterns = self._load_intent_patterns()
        
        # Context patterns
        self.context_patterns = self._load_context_patterns()
        
        # Goal patterns
        self.goal_patterns = self._load_goal_patterns()
        
        self.logger.info("Context Understanding Engine initialized")
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _init_context_database(self):
        """Initialize context understanding database"""
        conn = sqlite3.connect(self.context_db)
        cursor = conn.cursor()
        
        # Intent understanding table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intent_understanding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                intent_category TEXT NOT NULL,
                intent_description TEXT,
                confidence_score REAL DEFAULT 0.0,
                context_data TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, action_id)
            )
        """)
        
        # Context understanding table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_understanding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                context_value TEXT NOT NULL,
                context_metadata TEXT,
                confidence_score REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, action_id, context_type)
            )
        """)
        
        # Dependency mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependency_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                source_action_id TEXT NOT NULL,
                target_action_id TEXT NOT NULL,
                dependency_type TEXT NOT NULL,
                dependency_strength REAL DEFAULT 0.0,
                dependency_metadata TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, source_action_id, target_action_id)
            )
        """)
        
        # Goal understanding table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goal_understanding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                goal_category TEXT NOT NULL,
                goal_description TEXT NOT NULL,
                goal_confidence REAL DEFAULT 0.0,
                goal_metadata TEXT,
                achieved BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, workflow_id)
            )
        """)
        
        # Workflow understanding table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_understanding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                workflow_type TEXT NOT NULL,
                workflow_description TEXT,
                workflow_steps TEXT,
                workflow_goal TEXT,
                workflow_context TEXT,
                confidence_score REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL,
                UNIQUE(session_id, workflow_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_intent_session ON intent_understanding(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_session ON context_understanding(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dependency_session ON dependency_mapping(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_session ON goal_understanding(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_session ON workflow_understanding(session_id)")
        
        conn.commit()
        conn.close()
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent classification patterns"""
        return {
            "login": [
                "login", "sign in", "authenticate", "enter credentials",
                "username", "password", "credentials"
            ],
            "penelope_queue_management": [
                "penelope", "athena", "acm_logincontrol",
                "queuedtasks", "currenttasks", "taskhandle",
                "integrityseniorservices.athena-us.com"
            ],
            "penelope_portal_navigation": [
                "penelope", "athena", "integrityseniorservices",
                "penelope portal", "penelope task"
            ],
            "search": [
                "search", "find", "lookup", "query", "filter",
                "patient search", "client search", "name search"
            ],
            "navigate": [
                "navigate", "go to", "open", "click", "select",
                "menu", "tab", "page", "section"
            ],
            "submit": [
                "submit", "save", "confirm", "apply", "execute",
                "process", "complete", "finish"
            ],
            "view": [
                "view", "display", "show", "open", "read",
                "details", "information", "report"
            ],
            "edit": [
                "edit", "modify", "change", "update", "alter",
                "modify", "adjust", "correct"
            ],
            "delete": [
                "delete", "remove", "clear", "erase", "eliminate"
            ],
            "upload": [
                "upload", "import", "add", "attach", "load"
            ],
            "download": [
                "download", "export", "save", "get", "retrieve"
            ],
            "process": [
                "process", "run", "execute", "perform", "handle",
                "automate", "batch", "bulk"
            ]
        }
    
    def _load_context_patterns(self) -> Dict[str, Any]:
        """Load context extraction patterns"""
        return {
            "application": {
                "TherapyNotes": ["therapy notes", "therapynotes", "tn"],
                "Penelope": ["penelope"],
                "Medisoft": ["medisoft"],
                "PenelopePortal": [
                    "integrityseniorservices.athena-us.com",
                    "athena-us.com",
                    "acm_logincontrol"
                ],
                "Browser": ["chrome", "firefox", "edge", "browser"],
                "Excel": ["excel"],
                "Word": ["word"],
                "Outlook": ["outlook"],
                "AutomationHub": ["automation hub", "secure launcher", "master ai dashboard"]
            },
            "page_keywords": {
                "Login Page": ["login", "sign in"],
                "Dashboard": ["dashboard", "home"],
                "Search Page": ["search", "lookup"],
                "Results Page": ["results", "list"],
                "Patient Page": ["patient", "client"],
                "Report Page": ["report", "analysis"],
                "Bot Interface": ["bot", "automation", "workflow"]
            },
            "task_keywords": {
                "Billing": ["billing", "charge", "invoice"],
                "Medical Records": ["record", "chart", "notes"],
                "Consent Management": ["consent"],
                "Welcome Letters": ["welcome letter"],
                "Intake": ["intake", "registration"],
                "Referral": ["referral"],
                "IPS Removal": ["ips", "remove counselor"],
                "Penelope Tasks": [
                    "penelope", "athena", "queuedtasks",
                    "currenttasks", "task queue"
                ],
                "Automation Oversight": ["master ai dashboard", "secure launcher", "automation hub"]
            }
        }
    
    def _load_goal_patterns(self) -> Dict[str, List[str]]:
        """Load goal identification patterns"""
        return {
            "complete_task": [
                "complete", "finish", "done", "accomplish",
                "achieve", "fulfill", "satisfy"
            ],
            "find_information": [
                "find", "locate", "discover", "identify",
                "retrieve", "obtain", "get"
            ],
            "update_record": [
                "update", "modify", "change", "edit",
                "correct", "fix", "adjust"
            ],
            "create_record": [
                "create", "add", "new", "generate",
                "make", "build", "establish"
            ],
            "process_batch": [
                "process", "batch", "bulk", "multiple",
                "all", "many", "several"
            ],
            "generate_report": [
                "report", "generate", "create report",
                "export", "download report"
            ],
            "remove_counselor": [
                "remove counselor", "remove clinician", "ips",
                "remove provider", "remove therapist"
            ],
            "automation_control": [
                "automation", "script", "python", "terminal",
                "run bot", "launch bot"
            ],
            "process_billing": [
                "billing", "invoice", "charge", "payment"
            ],
            "therapy_notes_management": [
                "therapy", "therapynotes", "client page"
            ],
            "penelope_queue_management": [
                "penelope", "athena", "acm_logincontrol",
                "queuedtasks", "currenttasks", "task queue",
                "integrityseniorservices.athena-us.com"
            ],
            "penelope_portal_navigation": [
                "penelope portal", "penelope queue", "athena portal",
                "integrityseniorservices.athena-us.com", "acm_logincontrol"
            ],
            "web_form_completion": [
                "form", "field", "input", "entry"
            ]
        }
    
    def understand_session(self, session_id: str) -> Dict:
        """
        Understand a complete session - extract intent, context, dependencies, and goals
        
        Args:
            session_id: Session ID to understand
            
        Returns:
            Dictionary with:
                - intent_understanding: List of intent classifications
                - context_understanding: List of context extractions
                - dependency_mapping: List of dependency relationships
                - goal_understanding: List of goal identifications
                - workflow_understanding: Complete workflow understanding
        """
        try:
            self.logger.info(f"Understanding session: {session_id}")
            
            # Get session data
            session_data = self._get_session_data(session_id)
            if not session_data:
                self.logger.warning(f"No data found for session: {session_id}")
                return {}
            
            # Understand intent
            intent_understanding = self._understand_intent(session_id, session_data)
            
            # Understand context
            context_understanding = self._understand_context(session_id, session_data)
            
            # Map dependencies
            dependency_mapping = self._map_dependencies(session_id, session_data)
            
            # Understand goals
            goal_understanding = self._understand_goals(session_id, session_data)
            
            # Understand workflow
            workflow_understanding = self._understand_workflow(session_id, session_data)
            
            # Store understanding
            self._store_understanding(
                session_id,
                intent_understanding,
                context_understanding,
                dependency_mapping,
                goal_understanding,
                workflow_understanding
            )
            
            return {
                "session_id": session_id,
                "intent_understanding": intent_understanding,
                "context_understanding": context_understanding,
                "dependency_mapping": dependency_mapping,
                "goal_understanding": goal_understanding,
                "workflow_understanding": workflow_understanding
            }
            
        except Exception as e:
            self.logger.error(f"Error understanding session {session_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_session_data(self, session_id: str) -> List[Dict]:
        """Get all activity data for a session"""
        try:
            activities: List[Dict] = []
            session_times: List[datetime] = []

            # Helper to capture timestamps safely
            def _remember_time(ts_str: Optional[str]):
                if not ts_str:
                    return
                try:
                    session_times.append(datetime.fromisoformat(ts_str))
                except Exception:
                    pass

            # Try full monitoring database (desktop activity)
            db_paths = [
                self.data_dir / "full_monitoring" / "full_monitoring.db",
                self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db",
            ]

            for db_path in db_paths:
                if not db_path.exists():
                    continue

                initial_count = len(activities)

                with sqlite3.connect(db_path) as conn:
                        cursor = conn.cursor()

                        cursor.execute("""
                            SELECT timestamp, window_title, active_app
                            FROM screen_recordings
                            WHERE session_id = ?
                            ORDER BY timestamp
                        """, (session_id,))
                        for row in cursor.fetchall():
                            activities.append({
                                "id": f"screen_{row[0]}",
                                "type": "screen",
                                "timestamp": row[0],
                                "window_title": row[1],
                                "active_app": row[2]
                            })
                            _remember_time(row[0])

                        cursor.execute("""
                            SELECT timestamp, key_pressed, active_app, window_title
                            FROM keyboard_input
                            WHERE session_id = ?
                            ORDER BY timestamp
                        """, (session_id,))
                        for row in cursor.fetchall():
                            activities.append({
                                "id": f"keyboard_{row[0]}",
                                "type": "keyboard",
                                "timestamp": row[0],
                                "key": row[1],
                                "active_app": row[2],
                                "window_title": row[3]
                            })
                            _remember_time(row[0])

                        cursor.execute("""
                            SELECT timestamp, event_type, x_position, y_position, active_app, window_title
                            FROM mouse_activity
                            WHERE session_id = ?
                            ORDER BY timestamp
                        """, (session_id,))
                        for row in cursor.fetchall():
                            activities.append({
                                "id": f"mouse_{row[0]}",
                                "type": "mouse",
                                "timestamp": row[0],
                                "event_type": row[1],
                                "x": row[2],
                                "y": row[3],
                                "active_app": row[4],
                                "window_title": row[5]
                            })
                            _remember_time(row[0])
                # Only stop searching if we actually found any records for this session
                if len(activities) > initial_count:
                    break

            session_start = None
            session_end = None
            if session_times:
                session_times.sort()
                session_start = session_times[0] - timedelta(seconds=5)
                session_end = session_times[-1] + timedelta(seconds=5)

            # Augment with bot log entries within session window
            bot_logs = self._get_bot_log_entries(session_start, session_end)
            activities.extend(bot_logs)

            # Helper to check whether a browser timestamp should be merged
            def _within_session(ts_str: Optional[str]) -> bool:
                if not ts_str:
                    return False
                if not session_start or not session_end:
                    return True
                try:
                    ts = datetime.fromisoformat(ts_str)
                    return session_start <= ts <= session_end
                except Exception:
                    return False

            # Try browser activity database (web automation telemetry)
            browser_db_paths = [
                self.data_dir / "browser_activity.db",
                self.installation_dir / "_secure_data" / "browser_activity.db",
            ]

            for browser_db in browser_db_paths:
                if not browser_db.exists():
                    continue

                before_browser = len(activities)

                with sqlite3.connect(browser_db) as conn:
                    cursor = conn.cursor()

                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = {row[0] for row in cursor.fetchall()}

                    # Legacy single-table schema
                    if "browser_activity" in tables:
                        cursor.execute("""
                            SELECT timestamp, event_type, url, element_type, element_text
                            FROM browser_activity
                            WHERE session_id = ?
                            ORDER BY timestamp
                        """, (session_id,))
                        rows = cursor.fetchall()
                        # If no direct matches, fall back to time window
                        if not rows and session_start and session_end:
                            cursor.execute("""
                                SELECT timestamp, event_type, url, element_type, element_text
                                FROM browser_activity
                                WHERE timestamp BETWEEN ? AND ?
                                ORDER BY timestamp
                            """, (session_start.isoformat(), session_end.isoformat()))
                            rows = cursor.fetchall()

                        for row in rows:
                            if _within_session(row[0]):
                                activities.append({
                                    "id": f"browser_{row[0]}",
                                    "type": "browser",
                                    "timestamp": row[0],
                                    "event_type": row[1],
                                    "url": row[2],
                                    "element_type": row[3],
                                    "element_text": row[4]
                                })
                                _remember_time(row[0])

                    else:
                        # Normalized schema helpers
                        def fetch_rows(query_by_session: str, query_by_time: str, columns: int):
                            rows_local = []
                            if session_id:
                                cursor.execute(query_by_session, (session_id,))
                                rows_local = cursor.fetchall()
                            if not rows_local and session_start and session_end:
                                cursor.execute(
                                    query_by_time,
                                    (session_start.isoformat(), session_end.isoformat())
                                )
                                rows_local = cursor.fetchall()
                            return rows_local

                        if "page_navigations" in tables:
                            rows = fetch_rows(
                                """
                                SELECT timestamp, navigation_type, url, page_title
                                FROM page_navigations
                                WHERE session_id = ?
                                ORDER BY timestamp
                                """,
                                """
                                SELECT timestamp, navigation_type, url, page_title
                                FROM page_navigations
                                WHERE timestamp BETWEEN ? AND ?
                                ORDER BY timestamp
                                """,
                                4
                            )
                            for row in rows:
                                if _within_session(row[0]):
                                    activities.append({
                                        "id": f"browser_nav_{row[0]}",
                                        "type": "browser-navigation",
                                        "timestamp": row[0],
                                        "event_type": row[1],
                                        "url": row[2],
                                        "page_title": row[3]
                                    })
                                    _remember_time(row[0])

                        if "element_interactions" in tables:
                            rows = fetch_rows(
                                """
                                SELECT timestamp, action_type, element_tag, element_id, element_name, page_url
                                FROM element_interactions
                                WHERE session_id = ?
                                ORDER BY timestamp
                                """,
                                """
                                SELECT timestamp, action_type, element_tag, element_id, element_name, page_url
                                FROM element_interactions
                                WHERE timestamp BETWEEN ? AND ?
                                ORDER BY timestamp
                                """,
                                6
                            )
                            for row in rows:
                                if _within_session(row[0]):
                                    activities.append({
                                        "id": f"browser_el_{row[0]}",
                                        "type": "browser-element",
                                        "timestamp": row[0],
                                        "event_type": row[1],
                                        "element_tag": row[2],
                                        "element_id": row[3],
                                        "element_name": row[4],
                                        "url": row[5]
                                    })
                                    _remember_time(row[0])

                        if "form_field_interactions" in tables:
                            rows = fetch_rows(
                                """
                                SELECT timestamp, field_name, field_type, has_value, page_url
                                FROM form_field_interactions
                                WHERE session_id = ?
                                ORDER BY timestamp
                                """,
                                """
                                SELECT timestamp, field_name, field_type, has_value, page_url
                                FROM form_field_interactions
                                WHERE timestamp BETWEEN ? AND ?
                                ORDER BY timestamp
                                """,
                                5
                            )
                            for row in rows:
                                if _within_session(row[0]):
                                    activities.append({
                                        "id": f"browser_form_{row[0]}",
                                        "type": "browser-form",
                                        "timestamp": row[0],
                                        "field_name": row[1],
                                        "field_type": row[2],
                                        "has_value": row[3],
                                        "url": row[4]
                                    })
                                    _remember_time(row[0])

                if len(activities) > before_browser:
                    break

            activities.sort(key=lambda x: x.get("timestamp", ""))
            return activities

        except Exception as e:
            self.logger.error(f"Error getting session data: {e}")
            return []

    def _get_bot_log_entries(self, session_start: Optional[datetime], session_end: Optional[datetime]) -> List[Dict]:
        """Load bot GUI log entries and map them onto the activity timeline."""
        entries: List[Dict] = []
        if not session_start or not session_end:
            return entries

        candidates: List[Path] = []

        secure_log_dir = self.installation_dir / "_secure_data" / "bot_logs"
        if secure_log_dir.exists():
            candidates.extend(secure_log_dir.glob("*.log"))

        bots_dir = self.installation_dir / "_bots"
        if bots_dir.exists():
            candidates.extend(bots_dir.rglob("*.log"))

        seen: set = set()
        for log_path in sorted(candidates):
            try:
                resolved = log_path.resolve()
            except Exception:
                resolved = log_path
            if resolved in seen or not log_path.exists():
                continue
            seen.add(resolved)

            bot_name = log_path.parent.name
            if bot_name.lower().endswith("bot"):
                bot_name = bot_name
            elif "_bots" in str(log_path):
                bot_name = log_path.stem

            try:
                with log_path.open("r", encoding="utf-8") as fh:
                    for idx, line in enumerate(fh):
                        line = line.strip()
                        if not line:
                            continue

                        timestamp_str: Optional[str] = None
                        level = "INFO"
                        message = line

                        if " | " in line:
                            parts = line.split(" | ", 2)
                            if len(parts) >= 3:
                                timestamp_str, level, message = parts[0], parts[1], parts[2]
                                try:
                                    datetime.fromisoformat(timestamp_str)
                                except ValueError:
                                    timestamp_str = None
                        else:
                            # Attempt to parse standard logging format: "YYYY-MM-DD HH:MM:SS,ms - logger - LEVEL - message"
                            try:
                                ts_part, remainder = line.split(" - ", 1)
                                parsed_ts = datetime.strptime(ts_part, "%Y-%m-%d %H:%M:%S,%f")
                                timestamp_str = parsed_ts.isoformat()
                                remainder_parts = remainder.split(" - ")
                                if len(remainder_parts) >= 2:
                                    level = remainder_parts[1].strip()
                                    message = " - ".join(remainder_parts[2:]) if len(remainder_parts) > 2 else ""
                                else:
                                    message = remainder
                            except Exception:
                                timestamp_str = None

                        if not timestamp_str:
                            continue
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            continue

                        if session_start <= timestamp <= session_end:
                            entries.append({
                                "id": f"botlog_{log_path.stem}_{idx}",
                                "type": "bot-log",
                                "timestamp": timestamp_str,
                                "level": level,
                                "message": message,
                                "bot_name": bot_name,
                                "log_file": str(log_path)
                            })
            except Exception as exc:
                self.logger.error(f"Error reading bot log {log_path}: {exc}")
        return entries
    
    def _understand_intent(self, session_id: str, session_data: List[Dict]) -> List[Dict]:
        """Understand intent behind actions"""
        intent_understanding = []
        
        for action in session_data:
            action_id = action.get("id", "")
            action_type = action.get("type", "")
            
            # Extract text from action
            text = ""
            if action_type == "keyboard":
                text = action.get("key", "")
            elif action_type == "browser":
                text = f"{action.get('url', '')} {action.get('element_text', '')}"
            elif action_type == "screen":
                text = f"{action.get('window_title', '')} {action.get('active_app', '')}"
            
            # Classify intent
            intent_category, intent_description, confidence = self._classify_intent(text, action)
            
            intent_understanding.append({
                "action_id": action_id,
                "action_type": action_type,
                "intent_category": intent_category,
                "intent_description": intent_description,
                "confidence_score": confidence,
                "context_data": json.dumps(action)
            })
        
        return intent_understanding
    
    def _classify_intent(self, text: str, action: Dict) -> Tuple[str, str, float]:
        """Classify intent from text and action"""
        text_lower = (text or "").lower()
        action_type = action.get("type", "").lower()
        active_app = (action.get("active_app") or "").lower()
        window_title = (action.get("window_title") or "").lower()
        url = (action.get("url") or "").lower()
        event_type = (action.get("event_type") or "").lower()
        element_tag = (action.get("element_tag") or "").lower()
        field_type = (action.get("field_type") or "").lower()
        element_id = (action.get("element_id") or "").lower()
        element_name = (action.get("element_name") or "").lower()

        # Filter out development/IDE windows so they do not skew business intent
        development_apps = {"cursor.exe", "code.exe", "pycharm64.exe", "pycharm.exe", "visual studio code"}
        if active_app in development_apps or ("cursor" in window_title and active_app == "cursor.exe"):
            return "development_activity", "Working in development environment", 0.2

        # High-confidence heuristics first
        key_value = (action.get("key") or "").lower()
        if action_type == "keyboard":
            if key_value in {"enter", "return"}:
                return "submit_form", "Submitting form", 0.9
            if len(key_value) == 1 or key_value.isalnum():
                return "enter_data", "Entering data", 0.75

        if action_type in {"browser-form"}:
            return "enter_data", "Updating form field", 0.85

        if action_type in {"browser-navigation", "browser", "browser-element"}:
            if event_type == "navigate" or "http" in url:
                return "navigate_page", "Navigating to web page", 0.85
            if event_type == "click" or element_tag in {"a", "button"}:
                return "interact_element", "Interacting with web element", 0.8

        penelope_triggers = [
            "integrityseniorservices.athena-us.com",
            "acm_logincontrol",
            "penelope"
        ]
        if any(trigger in url for trigger in penelope_triggers) or any(trigger in window_title for trigger in penelope_triggers):
            if any(keyword in (element_id or element_name or text_lower) for keyword in ["queuedtasks", "currenttasks", "taskhandle", "queue"]):
                return "penelope_queue_management", "Managing Penelope task queue", 0.9
            return "penelope_portal_navigation", "Navigating Penelope portal", 0.85

        if "remove counselor" in text_lower or "remove clinician" in text_lower:
            return "remove_counselor", "Removing counselor assignment", 0.9

        if "python" in active_app or "windowsterminal" in active_app or "automation" in window_title:
            return "automation_control", "Controlling automation scripts", 0.8

        if "billing" in window_title or "billing" in text_lower:
            return "process_billing", "Processing billing tasks", 0.8

        if "medisoft" in window_title or "medisoft" in active_app:
            return "medisoft_operations", "Working in Medisoft", 0.75

        if "therapynotes" in url or "therapy" in window_title:
            return "therapy_notes_navigation", "Navigating TherapyNotes", 0.8

        # Match against intent patterns as fallback
        best_match = None
        best_score = 0.0
        for intent_category, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            if score > best_score:
                best_score = score
                best_match = intent_category

        friendly_labels = {
            "penelope_queue_management": "Managing Penelope task queue",
            "penelope_portal_navigation": "Navigating Penelope portal",
            "development_activity": "Working in development environment",
        }

        if best_match:
            confidence = min(best_score / len(self.intent_patterns[best_match]), 1.0)
            description = friendly_labels.get(
                best_match,
                f"User intends to {best_match.replace('_', ' ')}"
            )
            return best_match, description, max(confidence, 0.4)

        # Default: unknown intent
        return "unknown", "Intent unclear", 0.0
    
    def _understand_context(self, session_id: str, session_data: List[Dict]) -> List[Dict]:
        """Understand context of actions"""
        context_understanding = []
        
        for action in session_data:
            action_id = action.get("id", "")
            
            # Extract context
            contexts = self._extract_context(action)
            
            for context_type, context_value in contexts.items():
                context_understanding.append({
                    "action_id": action_id,
                    "context_type": context_type,
                    "context_value": context_value,
                    "confidence_score": 0.8,  # Default confidence
                    "context_metadata": json.dumps(action)
                })
        
        return context_understanding
    
    def _extract_context(self, action: Dict) -> Dict[str, str]:
        """Extract context from action"""
        contexts = {}
        
        # Application context
        app = (action.get("active_app") or action.get("url") or "").lower()
        if app:
            app_patterns = self.context_patterns.get("application", {})
            if isinstance(app_patterns, dict):
                for label, keywords in app_patterns.items():
                    if any(keyword in app for keyword in keywords):
                        contexts["application"] = label
                        break
            if "application" not in contexts and app.strip():
                contexts["application"] = action.get("active_app") or action.get("url")
        
        # Page context
        page_text = action.get("window_title") or action.get("url") or ""
        if page_text:
            page_patterns = self.context_patterns.get("page_keywords", {})
            lower_page = page_text.lower()
            assigned_page = None
            if isinstance(page_patterns, dict):
                for label, keywords in page_patterns.items():
                    if any(keyword in lower_page for keyword in keywords):
                        assigned_page = label
                        break
            contexts["page"] = assigned_page or page_text
        
        # State context
        if action.get("type") == "keyboard":
            contexts["state"] = "typing"
        elif action.get("type") == "mouse":
            contexts["state"] = "interacting"
        elif action.get("type") == "browser":
            contexts["state"] = "browsing"
        elif action.get("type") == "screen":
            contexts["state"] = "viewing"
        elif action.get("type") == "bot-log":
            contexts["state"] = "logging"
            bot_name = action.get("bot_name") or "Bot Log"
            contexts.setdefault("application", bot_name)
            message_lower = (action.get("message") or "").lower()
            if "penelope" in message_lower or "athena" in message_lower or "queue" in message_lower:
                contexts.setdefault("task", "Penelope Tasks")
        
        # Task context
        task_patterns = self.context_patterns.get("task_keywords", {})
        combined_text = " ".join(filter(None, [action.get("window_title"), action.get("active_app"), action.get("url"), action.get("element_text")])).lower()
        if task_patterns and combined_text:
            for label, keywords in task_patterns.items():
                if any(keyword in combined_text for keyword in keywords):
                    contexts.setdefault("task", label)
                    break
        
        return contexts
    
    def _map_dependencies(self, session_id: str, session_data: List[Dict]) -> List[Dict]:
        """Map dependencies between actions"""
        dependencies = []
        
        # Analyze action sequences
        for i in range(len(session_data) - 1):
            source_action = session_data[i]
            target_action = session_data[i + 1]
            
            source_id = source_action.get("id", "")
            target_id = target_action.get("id", "")
            
            # Determine dependency type
            dependency_type, strength = self._determine_dependency(source_action, target_action)
            
            if dependency_type != "none":
                dependencies.append({
                    "source_action_id": source_id,
                    "target_action_id": target_id,
                    "dependency_type": dependency_type,
                    "dependency_strength": strength,
                    "dependency_metadata": json.dumps({
                        "source": source_action,
                        "target": target_action
                    })
                })
        
        return dependencies
    
    def _determine_dependency(self, source: Dict, target: Dict) -> Tuple[str, float]:
        """Determine dependency type and strength between actions"""
        # Time-based dependency
        source_time = source.get("timestamp", "")
        target_time = target.get("timestamp", "")
        
        try:
            source_dt = datetime.fromisoformat(source_time)
            target_dt = datetime.fromisoformat(target_time)
            time_diff = (target_dt - source_dt).total_seconds()
            
            # If actions are close in time, they're likely related
            if time_diff < 5.0:  # Within 5 seconds
                strength = 1.0 - (time_diff / 5.0)
                
                # Check if same application/page
                if source.get("active_app") == target.get("active_app"):
                    return "sequential", strength
                elif source.get("url") == target.get("url"):
                    return "sequential", strength
                else:
                    return "related", strength * 0.7
        except:
            pass
        
        return "none", 0.0
    
    def _understand_goals(self, session_id: str, session_data: List[Dict]) -> List[Dict]:
        """Understand goals of workflows"""
        goals = []
        
        # Identify workflow segments
        workflows = self._identify_workflows(session_data)
        
        for workflow_id, workflow_data in workflows.items():
            # Classify goal
            goal_category, goal_description, confidence = self._classify_goal(workflow_data)
            
            goals.append({
                "workflow_id": workflow_id,
                "goal_category": goal_category,
                "goal_description": goal_description,
                "goal_confidence": confidence,
                "goal_metadata": json.dumps(workflow_data)
            })
        
        return goals
    
    def _identify_workflows(self, session_data: List[Dict]) -> Dict[str, Dict]:
        """Identify workflow segments in session data"""
        workflows = {}
        current_workflow = None
        workflow_start = None
        
        for i, action in enumerate(session_data):
            action_type = action.get("type", "")
            app = action.get("active_app", "") or action.get("url", "")
            
            # Detect workflow boundaries (app changes, long pauses)
            if current_workflow is None:
                current_workflow = f"workflow_{i}"
                workflow_start = i
            elif i > 0:
                prev_action = session_data[i - 1]
                prev_app = prev_action.get("active_app", "") or prev_action.get("url", "")
                
                # Check for workflow boundary
                if app != prev_app:
                    # Save current workflow
                    workflows[current_workflow] = {
                        "start": workflow_start,
                        "end": i - 1,
                        "actions": session_data[workflow_start:i]
                    }
                    # Start new workflow
                    current_workflow = f"workflow_{i}"
                    workflow_start = i
        
        # Save last workflow
        if current_workflow:
            workflows[current_workflow] = {
                "start": workflow_start,
                "end": len(session_data) - 1,
                "actions": session_data[workflow_start:]
            }
        
        return workflows
    
    def _classify_goal(self, workflow_data: Dict) -> Tuple[str, str, float]:
        """Classify goal from workflow data"""
        actions = workflow_data.get("actions", [])
        
        # Extract text from workflow
        text = " ".join([
            action.get("window_title", "") or action.get("url", "") or action.get("key", "")
            for action in actions
        ]).lower()
        urls = " ".join([action.get("url", "") or "" for action in actions]).lower()
        apps = " ".join([action.get("active_app", "") or "" for action in actions]).lower()

        # Heuristic goal detection
        if "integrityseniorservices.athena-us.com" in urls or "acm_logincontrol" in urls or "penelope" in urls:
            queue_keywords = ("queuedtasks", "currenttasks", "taskhandle", "task queue")
            if any(
                any(keyword in (action.get("element_id", "") or action.get("element_name", "") or "").lower() for keyword in queue_keywords)
                for action in actions
            ) or any(keyword in text for keyword in queue_keywords):
                return "penelope_queue_management", "Managing Penelope task queue", 0.9
            return "penelope_portal_navigation", "Navigating Penelope portal", 0.85

        if "remove counselor" in text or "remove clinician" in text or "ips" in text:
            return "remove_counselor", "Removing counselor assignments", 0.9

        if "billing" in text or "billing" in apps:
            return "process_billing", "Completing billing workflow", 0.85

        if "therapy" in urls or "therapynotes" in urls or "penelope" in urls:
            return "therapy_notes_management", "Managing TherapyNotes records", 0.8

        if "python" in apps or "windowsterminal" in apps or "automation" in text:
            return "automation_control", "Executing automation scripts", 0.8

        if any(action.get("type") in {"browser-form", "browser-element"} for action in actions):
            return "web_form_completion", "Completing web form workflow", 0.75
        
        # Match against goal patterns
        best_match = None
        best_score = 0.0
        
        for goal_category, patterns in self.goal_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text)
            if score > best_score:
                best_score = score
                best_match = goal_category
        
        if best_match:
            confidence = min(best_score / len(self.goal_patterns[best_match]), 1.0)
            description = f"Goal: {best_match.replace('_', ' ')}"
            return best_match, description, confidence
        
        return "unknown", "Goal unclear", 0.0
    
    def _understand_workflow(self, session_id: str, session_data: List[Dict]) -> Dict:
        """Understand complete workflow"""
        workflows = self._identify_workflows(session_data)
        
        workflow_understanding = []
        
        for workflow_id, workflow_data in workflows.items():
            actions = workflow_data.get("actions", [])
            
            # Extract workflow information
            workflow_type = self._classify_workflow_type(actions)
            workflow_description = self._generate_workflow_description(actions)
            workflow_steps = [action.get("id", "") for action in actions]
            
            # Get goal
            goal_category, goal_description, _ = self._classify_goal(workflow_data)
            
            workflow_understanding.append({
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "workflow_description": workflow_description,
                "workflow_steps": json.dumps(workflow_steps),
                "workflow_goal": goal_description,
                "workflow_context": json.dumps(workflow_data),
                "confidence_score": 0.7  # Default confidence
            })
        
        return workflow_understanding
    
    def _classify_workflow_type(self, actions: List[Dict]) -> str:
        """Classify workflow type from actions"""
        if not actions:
            return "unknown"
        
        # Check for common workflow patterns
        action_types = [action.get("type", "") for action in actions]
        
        if "browser" in action_types:
            return "web_automation"
        elif "keyboard" in action_types and "mouse" in action_types:
            return "desktop_automation"
        elif "keyboard" in action_types:
            return "data_entry"
        else:
            return "interaction"
    
    def _generate_workflow_description(self, actions: List[Dict]) -> str:
        """Generate human-readable workflow description"""
        if not actions:
            return "Empty workflow"
        
        descriptions = []
        for action in actions[:5]:  # First 5 actions
            action_type = action.get("type", "")
            if action_type == "browser":
                url = action.get("url", "")
                if url:
                    descriptions.append(f"Navigate to {url}")
            elif action_type == "keyboard":
                key = action.get("key", "")
                if key:
                    descriptions.append(f"Type: {key}")
            elif action_type == "mouse":
                descriptions.append("Click/interact")
        
        if len(actions) > 5:
            descriptions.append(f"... and {len(actions) - 5} more actions")
        
        return " → ".join(descriptions)
    
    def _store_understanding(self, session_id: str, intent_understanding: List[Dict],
                           context_understanding: List[Dict], dependency_mapping: List[Dict],
                           goal_understanding: List[Dict], workflow_understanding: List[Dict]):
        """Store understanding in database"""
        try:
            conn = sqlite3.connect(self.context_db)
            cursor = conn.cursor()
            
            # Store intent understanding
            for intent in intent_understanding:
                cursor.execute("""
                    INSERT OR REPLACE INTO intent_understanding
                    (session_id, action_id, action_type, intent_category, intent_description,
                     confidence_score, context_data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    intent.get("action_id", ""),
                    intent.get("action_type", ""),
                    intent.get("intent_category", ""),
                    intent.get("intent_description", ""),
                    intent.get("confidence_score", 0.0),
                    intent.get("context_data", ""),
                    datetime.now().isoformat()
                ))
            
            # Store context understanding
            for context in context_understanding:
                cursor.execute("""
                    INSERT OR REPLACE INTO context_understanding
                    (session_id, action_id, context_type, context_value, context_metadata,
                     confidence_score, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    context.get("action_id", ""),
                    context.get("context_type", ""),
                    context.get("context_value", ""),
                    context.get("context_metadata", ""),
                    context.get("confidence_score", 0.0),
                    datetime.now().isoformat()
                ))
            
            # Store dependency mapping
            for dependency in dependency_mapping:
                cursor.execute("""
                    INSERT OR REPLACE INTO dependency_mapping
                    (session_id, source_action_id, target_action_id, dependency_type,
                     dependency_strength, dependency_metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    dependency.get("source_action_id", ""),
                    dependency.get("target_action_id", ""),
                    dependency.get("dependency_type", ""),
                    dependency.get("dependency_strength", 0.0),
                    dependency.get("dependency_metadata", ""),
                    datetime.now().isoformat()
                ))
            
            # Store goal understanding
            for goal in goal_understanding:
                cursor.execute("""
                    INSERT OR REPLACE INTO goal_understanding
                    (session_id, workflow_id, goal_category, goal_description, goal_confidence,
                     goal_metadata, achieved, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    goal.get("workflow_id", ""),
                    goal.get("goal_category", ""),
                    goal.get("goal_description", ""),
                    goal.get("goal_confidence", 0.0),
                    goal.get("goal_metadata", ""),
                    0,  # Not yet achieved
                    datetime.now().isoformat()
                ))
            
            # Store workflow understanding
            for workflow in workflow_understanding:
                cursor.execute("""
                    INSERT OR REPLACE INTO workflow_understanding
                    (session_id, workflow_id, workflow_type, workflow_description, workflow_steps,
                     workflow_goal, workflow_context, confidence_score, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    workflow.get("workflow_id", ""),
                    workflow.get("workflow_type", ""),
                    workflow.get("workflow_description", ""),
                    workflow.get("workflow_steps", ""),
                    workflow.get("workflow_goal", ""),
                    workflow.get("workflow_context", ""),
                    workflow.get("confidence_score", 0.0),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Stored understanding for session: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing understanding: {e}")
            import traceback
            traceback.print_exc()
    
    def process_recent_sessions(self, hours: int = 24) -> Dict:
        """Process and understand recent sessions"""
        try:
            # Get recent sessions
            recent_sessions = self._get_recent_sessions(hours)
            
            if not recent_sessions:
                self.logger.info(f"No recent sessions found in last {hours} hours")
                return {"processed": 0, "sessions": []}
            
            self.logger.info(f"Processing {len(recent_sessions)} recent sessions...")
            
            results = []
            for session_id in recent_sessions:
                try:
                    understanding = self.understand_session(session_id)
                    results.append(understanding)
                    self.logger.info(f"Processed session: {session_id}")
                except Exception as e:
                    self.logger.error(f"Error processing session {session_id}: {e}")
            
            return {
                "processed": len(results),
                "sessions": results
            }
            
        except Exception as e:
            self.logger.error(f"Error processing recent sessions: {e}")
            return {"processed": 0, "sessions": []}
    
    def _get_recent_sessions(self, hours: int = 24) -> List[str]:
        """Get recent session IDs"""
        try:
            db_paths = [
                self.data_dir / "full_monitoring" / "full_monitoring.db",
                self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db",
            ]
            
            sessions = set()
            
            for db_path in db_paths:
                if db_path.exists():
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                    
                    cursor.execute("""
                        SELECT DISTINCT session_id
                        FROM screen_recordings
                        WHERE timestamp > ?
                        ORDER BY timestamp DESC
                    """, (cutoff_time,))
                    
                    for row in cursor.fetchall():
                        sessions.add(row[0])
                    
                    conn.close()
            
            return list(sessions)
            
        except Exception as e:
            self.logger.error(f"Error getting recent sessions: {e}")
            return []

