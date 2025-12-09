#!/usr/bin/env python3
"""Launch a lightweight browser window for workflow training sessions."""

from __future__ import annotations

import sys
import subprocess
import time
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from browser_activity_monitor import wrap_webdriver_for_monitoring
except ImportError:
    wrap_webdriver_for_monitoring = None


def _launch_chrome_browser():
    options = Options()
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    if wrap_webdriver_for_monitoring:
        try:
            driver = wrap_webdriver_for_monitoring(driver, bot_name="Workflow Trainer Browser")
        except Exception:
            pass
    driver.get("about:blank")
    try:
        while driver.window_handles:
            time.sleep(0.5)
    except Exception:
        pass


def _launch_system_browser(url: str):
    if sys.platform.startswith("win"):
        subprocess.Popen(["start", url], shell=True)
    elif sys.platform.startswith("darwin"):
        subprocess.Popen(["open", url])
    else:
        subprocess.Popen(["xdg-open", url])


def main():
    default_url = "about:blank"
    if SELENIUM_AVAILABLE:
        try:
            _launch_chrome_browser()
            return
        except Exception:
            pass
    _launch_system_browser(default_url)


if __name__ == "__main__":
    main()
