#!/usr/bin/env python3
"""Lightweight screen recorder for workflow training sessions."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import mss  # type: ignore
    from PIL import Image  # pillow is a transitive dependency of mss on Windows
    MSS_AVAILABLE = True
except Exception:
    mss = None  # type: ignore
    Image = None  # type: ignore
    MSS_AVAILABLE = False


class ScreenRecorder:
    """Capture periodic screenshots for a training session."""

    def __init__(self, installation_dir: Path, *, interval_seconds: float = 1.0) -> None:
        self.installation_dir = Path(installation_dir)
        self.interval_seconds = interval_seconds
        self.output_root = self.installation_dir / "_secure_data" / "session_media"
        self.output_root.mkdir(parents=True, exist_ok=True)

        self._session_id: Optional[str] = None
        self._capture_dir: Optional[Path] = None
        self._frames: list[str] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, session_id: str) -> Optional[Path]:
        """Begin capturing screenshots for the given session."""
        if not MSS_AVAILABLE:
            return None

        if self._session_id is not None:
            # Already recording; ignore duplicate start call
            return self._capture_dir

        self._session_id = session_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._capture_dir = self.output_root / f"{session_id}_{timestamp}"
        self._capture_dir.mkdir(exist_ok=True)
        self._frames = []
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_capture_loop, daemon=True)
        self._thread.start()
        return self._capture_dir

    def stop(self) -> Optional[Dict[str, Any]]:
        """Stop capturing and return a manifest describing captured files."""
        if self._session_id is None:
            return None

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        manifest = {
            "session_id": self._session_id,
            "capture_dir": str(self._capture_dir) if self._capture_dir else None,
            "frames": list(self._frames),
            "interval_seconds": self.interval_seconds,
            "recorded_at": datetime.now().isoformat(),
            "mss_available": MSS_AVAILABLE,
        }

        # Reset state
        self._session_id = None
        self._capture_dir = None
        self._frames = []
        self._thread = None
        self._stop_event.clear()

        return manifest

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_capture_loop(self) -> None:
        if not MSS_AVAILABLE or self._capture_dir is None or mss is None:
            return

        with mss.mss() as sct:  # type: ignore[attr-defined]
            monitor = sct.monitors[0]
            frame_index = 0
            while not self._stop_event.is_set():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                image = sct.grab(monitor)
                frame_path = self._capture_dir / f"frame_{frame_index:06d}_{timestamp}.png"
                try:
                    img = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX")  # type: ignore[arg-type]
                    img.save(frame_path, format="PNG")
                    self._frames.append(str(frame_path))
                except Exception:
                    # Ignore individual frame failures
                    pass

                frame_index += 1
                time.sleep(self.interval_seconds)


def create_screen_recorder(installation_dir: Path, *, interval_seconds: float = 1.0) -> ScreenRecorder:
    """Factory helper that returns a ScreenRecorder instance."""
    return ScreenRecorder(installation_dir, interval_seconds=interval_seconds)
