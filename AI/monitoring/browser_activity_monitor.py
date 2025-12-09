#!/usr/bin/env python3
"""Browser activity monitoring utilities."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from selenium.webdriver.support.events import (
        AbstractEventListener,
        EventFiringWebDriver,
    )
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:  # pragma: no cover
    AbstractEventListener = object  # type: ignore
    EventFiringWebDriver = None  # type: ignore
    WebDriverException = Exception
    SELENIUM_AVAILABLE = False

__all__ = [
    "get_browser_monitor",
    "wrap_webdriver_for_monitoring",
    "BrowserActivityMonitor",
]


_LOGGER = logging.getLogger("browser_monitor")


@dataclass
class BrowserEvent:
    timestamp: str
    session_id: str
    page_title: Optional[str] = None
    url: Optional[str] = None
    anonymized_url: Optional[str] = None
    action_type: Optional[str] = None
    element_tag: Optional[str] = None
    element_id: Optional[str] = None
    element_name: Optional[str] = None
    element_type: Optional[str] = None
    element_value: Optional[str] = None


class BrowserActivityMonitor:
    """Lightweight browser telemetry sink that stores activity in SQLite."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.secure_dir = self.installation_dir / "_secure_data"
        self.secure_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.secure_dir / "browser_activity.db"
        self.salt_path = self.secure_dir / ".browser_monitor_salt"

        self.collection_active = False
        self._current_session_id: Optional[str] = None
        self._lock = threading.RLock()

        self._init_database()
        self._salt = self._load_salt()

    # ------------------------------------------------------------------
    # Database initialisation
    # ------------------------------------------------------------------
    def _init_database(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS page_navigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                page_title TEXT,
                url TEXT,
                anonymized_url TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS element_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                action_type TEXT,
                element_tag TEXT,
                element_id TEXT,
                element_name TEXT,
                element_type TEXT,
                element_value TEXT,
                anonymized_page_url TEXT
            )
            """
        )
        # Migration: Add element_value column if it doesn't exist
        try:
            cursor.execute("PRAGMA table_info(element_interactions)")
            columns = [row[1] for row in cursor.fetchall()]
            if "element_value" not in columns:
                cursor.execute("ALTER TABLE element_interactions ADD COLUMN element_value TEXT")
        except Exception as e:
            # If migration fails, log but don't crash
            logging.warning(f"Failed to migrate element_interactions table: {e}")
        
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_nav_session ON page_navigations(session_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_element_session ON element_interactions(session_id)
            """
        )
        conn.commit()
        conn.close()

    def _load_salt(self) -> bytes:
        if self.salt_path.exists():
            return self.salt_path.read_bytes()
        salt = os.urandom(32)
        self.salt_path.write_bytes(salt)
        os.chmod(self.salt_path, 0o600)
        return salt

    # ------------------------------------------------------------------
    # Session / collection control
    # ------------------------------------------------------------------
    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id

    def _generate_session_id(self) -> str:
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def start_collection(self, session_id: Optional[str] = None) -> str:
        with self._lock:
            if session_id is None:
                session_id = self._generate_session_id()
            self._current_session_id = session_id
            self.collection_active = True
            return session_id

    def stop_collection(self) -> None:
        with self._lock:
            self.collection_active = False
            self._current_session_id = None

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    def _hash_value(self, value: str) -> str:
        if not value:
            return ""
        digest = hmac.new(self._salt, value.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def _record_navigation(self, event: BrowserEvent) -> None:
        with self._lock:
            if not self.collection_active:
                return
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO page_navigations (session_id, timestamp, page_title, url, anonymized_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.timestamp,
                    event.page_title,
                    event.url,
                    event.anonymized_url,
                ),
            )
            conn.commit()
            conn.close()

    def _record_interaction(self, event: BrowserEvent) -> None:
        with self._lock:
            if not self.collection_active:
                return
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO element_interactions (
                        session_id,
                        timestamp,
                        action_type,
                        element_tag,
                        element_id,
                        element_name,
                        element_type,
                        element_value,
                        anonymized_page_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.session_id,
                        event.timestamp,
                        event.action_type,
                        event.element_tag,
                        event.element_id,
                        event.element_name,
                        event.element_type,
                        event.element_value,
                        event.anonymized_url,
                    ),
                )
                conn.commit()
            except sqlite3.OperationalError as e:
                if "element_value" in str(e):
                    # Fallback: try without element_value column
                    try:
                        cursor.execute(
                            """
                            INSERT INTO element_interactions (
                                session_id,
                                timestamp,
                                action_type,
                                element_tag,
                                element_id,
                                element_name,
                                element_type,
                                anonymized_page_url
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                event.session_id,
                                event.timestamp,
                                event.action_type,
                                event.element_tag,
                                event.element_id,
                                event.element_name,
                                event.element_type,
                                event.anonymized_url,
                            ),
                        )
                        conn.commit()
                    except Exception as fallback_error:
                        logging.warning(f"Failed to record interaction (fallback): {fallback_error}")
                else:
                    logging.warning(f"Failed to record interaction: {e}")
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def record_navigation(self, url: str, title: Optional[str], session_id: Optional[str] = None) -> None:
        try:
            if not self.collection_active:
                return
            session = session_id or self._current_session_id
            if not session:
                session = self.start_collection()
            event = BrowserEvent(
                timestamp=datetime.now().isoformat(),
                session_id=session,
                page_title=title,
                url=url,
                anonymized_url=self._hash_value(url),
            )
            self._record_navigation(event)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record navigation event: {e}")

    def record_interaction(
        self,
        action_type: str,
        driver,
        element=None,
        session_id: Optional[str] = None,
    ) -> None:
        try:
            if not self.collection_active:
                return
            session = session_id or self._current_session_id
            if not session:
                session = self.start_collection()

            page_url = ""
            try:
                page_url = driver.current_url if driver else ""
            except Exception:
                page_url = ""

            tag = element.tag_name if element is not None else None
            elem_id = element.get_attribute("id") if element is not None else None
            elem_name = element.get_attribute("name") if element is not None else None
            elem_type = element.get_attribute("type") if element is not None else None
            elem_value = None
            if action_type in {"change", "value_change"} and element is not None:
                try:
                    elem_value = element.get_attribute("value")
                except Exception:
                    elem_value = None

            event = BrowserEvent(
                timestamp=datetime.now().isoformat(),
                session_id=session,
                action_type=action_type,
                element_tag=tag,
                element_id=elem_id,
                element_name=elem_name,
                element_type=elem_type,
                element_value=elem_value,
                anonymized_url=self._hash_value(page_url or ""),
            )
            self._record_interaction(event)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record interaction event: {e}")
    
    # ------------------------------------------------------------------
    # Data cleanup / recycling
    # ------------------------------------------------------------------
    def cleanup_old_records(self, retention_days: int = 30) -> int:
        """Remove old records from the database to free up space.
        
        Args:
            retention_days: Number of days of data to keep (default: 30)
            
        Returns:
            Number of records deleted
        """
        if not self.db_path.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.isoformat()
        
        total_deleted = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old page navigations
            cursor.execute(
                "DELETE FROM page_navigations WHERE timestamp < ?",
                (cutoff_str,)
            )
            nav_deleted = cursor.rowcount
            
            # Delete old element interactions
            cursor.execute(
                "DELETE FROM element_interactions WHERE timestamp < ?",
                (cutoff_str,)
            )
            elem_deleted = cursor.rowcount
            
            total_deleted = nav_deleted + elem_deleted
            
            if total_deleted > 0:
                conn.commit()
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                conn.commit()
                _LOGGER.info(f"Cleaned {total_deleted} old records from browser activity database")
            
            conn.close()
        except Exception as e:
            _LOGGER.warning(f"Error during database cleanup: {e}")
        
        return total_deleted


class _MonitoringEventListener(AbstractEventListener):
    def __init__(self, monitor: BrowserActivityMonitor, session_id: str):
        self.monitor = monitor
        self.session_id = session_id

    # Navigation events -------------------------------------------------
    def after_navigate_to(self, url, driver):  # type: ignore[override]
        try:
            try:
                current_url = driver.current_url if driver else url
                title = driver.title if driver else None
            except Exception:
                current_url = url if url else ""
                title = None
            self.monitor.record_navigation(current_url, title, session_id=self.session_id)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record navigation: {e}")

    def after_navigate_back(self, driver):  # type: ignore[override]
        try:
            try:
                url = driver.current_url
                title = driver.title
            except Exception:
                url = ""
                title = None
            self.monitor.record_navigation(url, title, session_id=self.session_id)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record back navigation: {e}")

    def after_navigate_forward(self, driver):  # type: ignore[override]
        try:
            try:
                url = driver.current_url
                title = driver.title
            except Exception:
                url = ""
                title = None
            self.monitor.record_navigation(url, title, session_id=self.session_id)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record forward navigation: {e}")

    # Interaction events -----------------------------------------------
    def after_click(self, element, driver):  # type: ignore[override]
        try:
            self.monitor.record_interaction("click", driver, element, session_id=self.session_id)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record click interaction: {e}")

    def after_change_value_of(self, element, driver):  # type: ignore[override]
        try:
            self.monitor.record_interaction("change", driver, element, session_id=self.session_id)
        except Exception as e:
            # Never crash the bot - monitoring failures should be silent
            logging.debug(f"Monitoring: Failed to record change interaction: {e}")


_global_monitor: Optional[BrowserActivityMonitor] = None
_global_lock = threading.Lock()


def get_browser_monitor(installation_dir: Optional[Path] = None) -> Optional[BrowserActivityMonitor]:
    """Get browser monitor instance, returning None if initialization fails."""
    global _global_monitor
    try:
        with _global_lock:
            if _global_monitor is None:
                if installation_dir is None:
                    # Auto-detect: if we're in AI/monitoring/browser_activity_monitor.py, go up 2 levels
                    current_file = Path(__file__).resolve()
                    if current_file.parent.name == "monitoring" and current_file.parent.parent.name == "AI":
                        installation_dir = current_file.parent.parent.parent
                    else:
                        installation_dir = current_file.parent.parent.parent
                _global_monitor = BrowserActivityMonitor(Path(installation_dir))
            return _global_monitor
    except Exception as e:
        # Never crash the bot - if monitoring can't be initialized, return None
        logging.debug(f"Monitoring: Failed to initialize browser monitor: {e}")
        return None


def wrap_webdriver_for_monitoring(
    driver,
    session_id: Optional[str] = None,
    bot_name: Optional[str] = None,
    installation_dir: Optional[Path] = None,
):
    """Return an EventFiringWebDriver that records telemetry. Returns original driver if monitoring fails."""
    if not SELENIUM_AVAILABLE:
        return driver

    try:
        monitor = get_browser_monitor(installation_dir)
        if monitor is None:
            # Monitoring unavailable - return original driver
            return driver
        
        session = monitor.start_collection(session_id)
        listener = _MonitoringEventListener(monitor, session)

        try:
            wrapped = EventFiringWebDriver(driver, listener)
        except Exception as exc:  # pragma: no cover - fallback if wrapping fails
            logging.debug(f"Could not wrap webdriver for monitoring: {exc}")
            return driver

        # Store reference so we can detect quit
        setattr(wrapped, "__monitor_session_id__", session)
        return wrapped
    except Exception as e:
        # Never crash the bot - if monitoring fails, return original driver
        logging.debug(f"Monitoring: Failed to wrap webdriver: {e}")
        return driver
