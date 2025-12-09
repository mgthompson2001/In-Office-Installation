#!/usr/bin/env python3
"""
Medical Records Department Launcher
-----------------------------------

Provides a lightweight GUI to launch Medical Records automation bots.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from pathlib import Path


class MedicalRecordsDepartmentLauncher(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Medical Records Department - Bot Launcher - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("700x400")
        self.resizable(True, True)
        self._configure_paths()
        self._build_ui()

    def _configure_paths(self) -> None:
        """Resolve absolute paths for Medical Records bots."""
        installation_dir = Path(__file__).parent.parent.parent

        self.bots = {
            "Medical Records Bot": {
                "path": str(
                    installation_dir
                    / "_bots"
                    / "Med Rec"
                    / "Finished Product, Launch Ready"
                    / "Bot and extender"
                    / "integrity_medical_records_bot_v3g_batchclicks.py"
                ),
                "description": "Legacy medical records management workflow."
            },
            "Medical Records Billing Log Bot": {
                "path": str(
                    installation_dir
                    / "_bots"
                    / "Med Rec"
                    / "therapy_notes_records_bot.py"
                ),
                "description": "Generates TherapyNotes date-of-service logs from insurer documents."
            }
        }

    def _build_ui(self) -> None:
        """Construct the launcher interface."""
        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(
            header,
            text="Medical Records Department",
            bg="#660000",
            fg="white",
            font=("Segoe UI", 14, "bold"),
            pady=8
        ).pack(side="left", padx=12)

        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)

        tk.Label(
            main_frame,
            text="Select a bot to launch:",
            font=("Segoe UI", 10),
            wraplength=640
        ).pack(pady=(0, 15), anchor="w")

        for bot_name, bot_info in self.bots.items():
            self._create_bot_card(main_frame, bot_name, bot_info)

        status_frame = tk.LabelFrame(main_frame, text="Status", font=("Segoe UI", 9, "bold"))
        status_frame.pack(fill="x", pady=(20, 0))

        self.status_label = tk.Label(
            status_frame,
            text="Ready. Select a bot to launch.",
            font=("Segoe UI", 9),
            fg="gray"
        )
        self.status_label.pack(padx=10, pady=8)

    def _create_bot_card(self, parent: tk.Widget, bot_name: str, bot_info: dict) -> None:
        """Render a simple card with launch button and description."""
        card = tk.Frame(parent, relief="ridge", bd=2, bg="white")
        card.pack(fill="x", pady=8)

        header_frame = tk.Frame(card, bg="white")
        header_frame.pack(fill="x", padx=15, pady=12)

        tk.Label(
            header_frame,
            text=bot_name,
            font=("Segoe UI", 11, "bold"),
            bg="white"
        ).pack(side="left", fill="x", expand=True)

        launch_btn = tk.Button(
            header_frame,
            text="Launch",
            command=lambda name=bot_name: self._launch_bot(name),
            bg="#660000",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=15,
            pady=5,
            cursor="hand2",
            relief="raised"
        )
        launch_btn.pack(side="right")

        desc_frame = tk.Frame(card, bg="white")
        desc_frame.pack(fill="x", padx=15, pady=(0, 12))

        tk.Label(
            desc_frame,
            text=bot_info["description"],
            font=("Segoe UI", 9),
            fg="gray",
            bg="white",
            wraplength=600,
            justify="left"
        ).pack(anchor="w")

    def _launch_bot(self, bot_name: str) -> None:
        """Launch the selected bot via subprocess."""
        bot_info = self.bots.get(bot_name)
        if not bot_info:
            messagebox.showerror("Error", f"Invalid selection: {bot_name}")
            return

        bot_path = bot_info["path"]
        if not os.path.exists(bot_path):
            messagebox.showerror("File Not Found", f"The bot file was not found:\n{bot_path}")
            self.status_label.config(text=f"✗ Missing file for {bot_name}", fg="red")
            return

        self.status_label.config(text=f"Launching {bot_name}...", fg="blue")
        self.update()

        try:
            process = subprocess.Popen(
                [sys.executable, bot_path],
                cwd=os.path.dirname(bot_path)
            )
            self.status_label.config(
                text=f"✓ {bot_name} launched (PID: {process.pid})",
                fg="green"
            )
        except Exception as exc:  # noqa: BLE001
            self.status_label.config(text=f"✗ Failed to launch {bot_name}", fg="red")
            messagebox.showerror("Launch Error", f"Failed to launch {bot_name}:\n{exc}")


def main() -> None:
    app = MedicalRecordsDepartmentLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()

