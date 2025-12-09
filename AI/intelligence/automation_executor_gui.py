#!/usr/bin/env python3
"""Automation Executor Manager GUI."""

from __future__ import annotations

import sys
import subprocess
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import json

CURRENT_DIR = Path(__file__).resolve().parent
AI_ROOT = CURRENT_DIR.parent
INSTALLATION_DIR = AI_ROOT.parent

for candidate in (INSTALLATION_DIR, AI_ROOT, CURRENT_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from automation_execution_repository import AutomationExecutionRepository
from automation_prototype_generator import AutomationPrototypeGenerator


class AutomationExecutorGUI:
    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.repo = AutomationExecutionRepository(self.installation_dir)
        self.prototype_generator = AutomationPrototypeGenerator(self.installation_dir)
        self.prototype_cache: Dict[str, Dict] = {}

        self.root = tk.Tk()
        self.root.title("Automation Executor Manager")
        self.root.geometry("1200x760")
        self.root.minsize(960, 600)

        self._build_ui()
        self._load_prototypes()
        self._load_runs()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        header = ttk.Label(
            main_frame,
            text="Automation Executor",
            font=("Arial", 18, "bold"),
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w")

        controls = ttk.Frame(main_frame)
        controls.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(3, weight=1)

        ttk.Label(controls, text="Automation Prototypes", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.prototype_tree = ttk.Treeview(
            controls,
            columns=("Name", "Pattern", "Frequency", "LastSeen"),
            show="headings",
            height=15,
        )
        self.prototype_tree.grid(row=1, column=0, sticky="nsew")
        column_defs = (
            ("Name", 260),
            ("Pattern", 200),
            ("Frequency", 90),
            ("LastSeen", 160),
        )
        for col, width in column_defs:
            self.prototype_tree.heading(col, text=col)
            self.prototype_tree.column(col, stretch=True, width=width)
        proto_scroll = ttk.Scrollbar(controls, orient=tk.VERTICAL, command=self.prototype_tree.yview)
        self.prototype_tree.configure(yscrollcommand=proto_scroll.set)
        proto_scroll.grid(row=1, column=1, sticky="ns")

        ttk.Label(controls, text="Prototype Summary", font=("Arial", 11, "bold")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.prototype_details = scrolledtext.ScrolledText(controls, height=14, wrap=tk.WORD)
        self.prototype_details.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        button_frame = ttk.Frame(controls)
        button_frame.grid(row=4, column=0, sticky="ew")
        button_frame.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(button_frame, text="Generate New Prototypes", command=self._handle_generate).grid(row=0, column=0, padx=4)
        ttk.Button(button_frame, text="Run Selected Prototype", command=self._handle_run_selected).grid(row=0, column=1, padx=4)
        ttk.Button(button_frame, text="Open Prototype Folder", command=self._handle_open_folder).grid(row=0, column=2, padx=4)

        history_frame = ttk.Frame(main_frame)
        history_frame.grid(row=1, column=1, sticky="nsew")
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(3, weight=1)

        ttk.Label(history_frame, text="Recent Runs", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.run_tree = ttk.Treeview(
            history_frame,
            columns=("ID", "Pattern", "Status", "Duration", "Completed"),
            show="headings",
            height=12,
        )
        self.run_tree.grid(row=1, column=0, sticky="nsew")
        for col, width in (("ID", 80), ("Pattern", 220), ("Status", 120), ("Duration", 90), ("Completed", 160)):
            self.run_tree.heading(col, text=col)
            self.run_tree.column(col, stretch=True, width=width)
        run_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.run_tree.yview)
        self.run_tree.configure(yscrollcommand=run_scroll.set)
        run_scroll.grid(row=1, column=1, sticky="ns")

        ttk.Label(history_frame, text="Run Details", font=("Arial", 11, "bold")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.log_text = scrolledtext.ScrolledText(history_frame, height=12, wrap=tk.WORD)
        self.log_text.grid(row=3, column=0, columnspan=2, sticky="nsew")

        self.prototype_tree.bind("<<TreeviewSelect>>", self._on_prototype_select)
        self.run_tree.bind("<<TreeviewSelect>>", self._on_run_select)

    def _load_prototypes(self):
        self.prototype_tree.delete(*self.prototype_tree.get_children())
        self.prototype_cache = self.prototype_generator.list_prototypes()
        for key, data in self.prototype_cache.items():
            display_name = data.get("display_name") or data.get("pattern_hash") or key
            self.prototype_tree.insert(
                "",
                tk.END,
                iid=key,
                values=(
                    display_name,
                    data.get("pattern_hash"),
                    data.get("frequency"),
                    data.get("last_seen"),
                ),
            )
        if self.prototype_cache:
            first = next(iter(self.prototype_cache))
            self.prototype_tree.selection_set(first)
            self._show_prototype_details(first)
        else:
            self.prototype_details.delete(1.0, tk.END)
            self.prototype_details.insert(tk.END, "No automation prototypes generated yet.")

    def _load_runs(self):
        self.run_tree.delete(*self.run_tree.get_children())
        runs = self.repo.list_recent_runs()
        for run_id, record in runs.items():
            self.run_tree.insert(
                "",
                tk.END,
                iid=str(run_id),
                values=(
                    run_id,
                    record.pattern_hash,
                    record.status,
                    f"{record.duration_seconds:.1f}s",
                    record.completed_at.strftime("%Y-%m-%d %H:%M"),
                ),
            )

    def _handle_generate(self):
        def worker():
            try:
                result = self.prototype_generator.generate_for_top_patterns()
                self.root.after(0, self._load_prototypes)
                message = f"Generated {len(result)} prototype bundle(s)." if result else "No new prototypes created."
                messagebox.showinfo("Generation Complete", message)
            except Exception as exc:
                traceback.print_exc()
                messagebox.showerror("Error", f"Could not generate prototypes:\n{exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _handle_run_selected(self):
        selection = self.prototype_tree.selection()
        if not selection:
            messagebox.showinfo("Select Prototype", "Please select a prototype to run.")
            return
        cache_key = selection[0]
        data = self.prototype_cache.get(cache_key, {})
        path = data.get("path")
        pattern_hash = data.get("pattern_hash") or cache_key
        if not path:
            messagebox.showerror("Error", "Prototype path missing.")
            return
        self._run_prototype_async(cache_key, pattern_hash, Path(path))

    def _handle_open_folder(self):
        selection = self.prototype_tree.selection()
        if not selection:
            messagebox.showinfo("Select Prototype", "Please select a prototype.")
            return
        data = self.prototype_cache.get(selection[0], {})
        path = data.get("path")
        if not path:
            messagebox.showerror("Error", "Prototype path missing.")
            return
        subprocess.Popen(["explorer", path])

    def _run_prototype_async(self, cache_key: str, pattern_hash: str, prototype_dir: Path):
        threading.Thread(
            target=self._run_prototype,
            args=(cache_key, pattern_hash, prototype_dir),
            daemon=True,
        ).start()

    def _run_prototype(self, cache_key: str, pattern_hash: str, prototype_dir: Path):
        script_path = prototype_dir / "prototype.py"
        logs_path = prototype_dir / f"run_{int(time.time())}.log"
        if not script_path.exists():
            messagebox.showerror("Missing script", f"Prototype script not found at {script_path}")
            return

        start = datetime.now()
        status = "success"
        error_message = None
        metadata: Dict[str, Optional[str]] = {}

        try:
            with open(logs_path, "w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(prototype_dir),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
                retcode = process.wait()
                metadata["return_code"] = retcode
                if retcode != 0:
                    status = "failed"
                    error_message = f"Process exited with code {retcode}"
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            traceback.print_exc()

        completed = datetime.now()
        data = self.prototype_cache.get(cache_key) or {}
        run_id = self.repo.log_run(
            pattern_hash=pattern_hash,
            prototype_path=prototype_dir,
            started_at=start,
            completed_at=completed,
            status=status,
            logs_path=logs_path,
            error_message=error_message,
            metadata=metadata,
        )

        description = data.get("display_name")
        self.repo.register_prototype(pattern_hash, prototype_dir, description=description)
        self.root.after(0, self._load_runs)

        if status == "success":
            messagebox.showinfo("Run Complete", f"Automation run {run_id} completed successfully.")
        else:
            messagebox.showwarning("Run Failed", f"Automation run {run_id} failed: {error_message}")

    def _show_prototype_details(self, iid: str):
        data = self.prototype_cache.get(iid, {})
        self.prototype_details.delete(1.0, tk.END)
        if not data:
            self.prototype_details.insert(tk.END, "No details available.")
            return

        lines = []
        lines.append(f"Name: {data.get('display_name') or data.get('pattern_hash')}")
        lines.append(f"Pattern Hash: {data.get('pattern_hash')}")
        lines.append(f"Frequency: {data.get('frequency')}")
        lines.append(f"Last Seen: {data.get('last_seen')}")
        lines.append(f"Bundle Path: {data.get('path')}")

        summary_json = data.get("summary_data") or {}
        steps = summary_json.get("steps") or []
        if steps:
            lines.append("\nKey Steps:")
            for step in steps[:6]:
                action = step.get("action_type") or step.get("action") or "action"
                url = step.get("page_url") or step.get("url") or ""
                lines.append(f" • {action} {url}")
            if len(steps) > 6:
                lines.append(f" • ... and {len(steps) - 6} more steps")

        gpt_path = data.get("gpt_report")
        if gpt_path and Path(gpt_path).exists():
            try:
                report = Path(gpt_path).read_text(encoding="utf-8").strip()
                if report:
                    lines.append("\nGPT Insight:")
                    for line in report.splitlines()[:14]:
                        lines.append(line)
                    if len(report.splitlines()) > 14:
                        lines.append("...")
            except Exception:
                pass

        self.prototype_details.insert(tk.END, "\n".join(lines))
        self.prototype_details.see(tk.END)

    def _on_prototype_select(self, _event):
        selection = self.prototype_tree.selection()
        if not selection:
            return
        self._show_prototype_details(selection[0])

    def _on_run_select(self, _event):
        selection = self.run_tree.selection()
        if not selection:
            return
        record = self.repo.list_recent_runs(limit=100).get(int(selection[0]))
        if not record:
            return
        lines = [
            f"Run ID: {record.run_id}",
            f"Pattern: {record.pattern_hash}",
            f"Status: {record.status}",
            f"Started: {record.started_at}",
            f"Completed: {record.completed_at}",
            f"Duration: {record.duration_seconds:.1f}s",
        ]
        if record.error_message:
            lines.append(f"Error: {record.error_message}")
        if record.logs_path:
            lines.append(f"Logs: {record.logs_path}")
        lines.append("Metadata:")
        lines.append(json.dumps(record.metadata, indent=2))

        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, "\n".join(lines))
        self.log_text.see(tk.END)

    def run(self):
        self.root.mainloop()


def launch_automation_executor(installation_dir: Path):
    gui = AutomationExecutorGUI(installation_dir)
    gui.run()


if __name__ == "__main__":
    launch_automation_executor(INSTALLATION_DIR)
