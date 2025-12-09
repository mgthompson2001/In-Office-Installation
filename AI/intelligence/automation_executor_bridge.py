#!/usr/bin/env python3
"""Bridge script to launch the Automation Executor GUI from the dashboard."""

from pathlib import Path

from automation_executor_gui import launch_automation_executor


def main():
    installation_dir = Path(__file__).parent.parent.parent
    launch_automation_executor(installation_dir)


if __name__ == "__main__":
    main()
