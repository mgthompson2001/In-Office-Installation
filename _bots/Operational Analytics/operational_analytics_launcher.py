# Operational Analytics Launcher
# Sub-launcher for Operational Analytics bots

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys

class OperationalAnalyticsLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Operational Analytics - Bot Launcher - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("750x500")
        self._setup_bot_configs()
        self._build_ui()

    def _setup_bot_configs(self):
        """Configure all bots in the Operational Analytics department"""
        from pathlib import Path
        
        # Get base installation directory (go up from _bots/Operational Analytics to In-Office Installation)
        installation_dir = Path(__file__).parent.parent.parent
        
        self.bots = {
            "Missed Appointments Tracker Bot": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "Medisoft Billing" / "Missed Appointments Tracker Bot" / "missed_appointments_tracker_bot.py"),
                "description": "Tracks missed appointments across 330+ counselors and thousands of clients. Synthesizes data from Excel spreadsheets and Therapy Notes to identify potential missed appointments based on session frequency analysis."
            }
        }

    def _build_ui(self):
        """Build the department launcher UI"""
        # Header
        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text="Operational Analytics", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=8).pack(side="left", padx=12)
        
        # Back button in header
        back_btn = tk.Button(header, text="← Back to Main Menu", command=self.destroy,
                           bg="#800000", fg="white", font=("Segoe UI", 9),
                           relief="flat", padx=10, pady=4, cursor="hand2")
        back_btn.pack(side="right", padx=12)

        # Main container
        main_container = tk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=0, pady=0)

        # Instructions (fixed at top)
        instructions_frame = tk.Frame(main_container)
        instructions_frame.pack(fill="x", padx=25, pady=(25, 10))
        
        instructions = tk.Label(instructions_frame, 
                               text="Select a bot from the list below to launch it:",
                               font=("Segoe UI", 10),
                               wraplength=640)
        instructions.pack()

        # Create scrollable frame for bot cards
        # Canvas and scrollbar container
        canvas_frame = tk.Frame(main_container)
        canvas_frame.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # Create canvas with scrollbar
        canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        # Configure scrollable frame
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Create window in canvas for scrollable frame
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configure canvas scrolling
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Update canvas width when window is resized
        def configure_canvas_width(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind("<Configure>", configure_canvas_width)

        # Mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Bot cards in scrollable frame
        for bot_name, bot_info in self.bots.items():
            self._create_bot_card(scrollable_frame, bot_name, bot_info)

        # Status area (fixed at bottom)
        status_frame = tk.LabelFrame(main_container, text="Status", font=("Segoe UI", 9, "bold"))
        status_frame.pack(fill="x", padx=25, pady=(10, 25))
        
        self.status_label = tk.Label(status_frame, text="Ready. Select a bot to launch.", 
                                     font=("Segoe UI", 9), fg="gray")
        self.status_label.pack(padx=10, pady=8)

    def _create_bot_card(self, parent, bot_name, bot_info):
        """Create a card UI for each bot"""
        card = tk.Frame(parent, relief="ridge", bd=2, bg="white")
        card.pack(fill="x", pady=8)

        # Bot name and launch button on same row
        header_frame = tk.Frame(card, bg="white")
        header_frame.pack(fill="x", padx=15, pady=12)

        tk.Label(header_frame, text=bot_name, font=("Segoe UI", 11, "bold"),
                bg="white", anchor="w").pack(side="left", fill="x", expand=True)

        launch_btn = tk.Button(header_frame, text="Launch",
                              command=lambda: self._launch_bot(bot_name),
                              bg="#660000", fg="white", font=("Segoe UI", 9, "bold"),
                              padx=15, pady=5, cursor="hand2", relief="raised")
        launch_btn.pack(side="right")

        # Description
        desc_frame = tk.Frame(card, bg="white")
        desc_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        description = bot_info.get("description", "No description available.")
        tk.Label(desc_frame, text=description, font=("Segoe UI", 9),
                bg="white", wraplength=650, justify="left", anchor="w").pack(anchor="w")

    def _launch_bot(self, bot_name):
        """Launch the selected bot"""
        bot_config = self.bots.get(bot_name)
        
        if not bot_config:
            messagebox.showerror("Error", f"Bot configuration not found: {bot_name}")
            return
        
        bot_path = bot_config["path"]
        
        if not os.path.exists(bot_path):
            messagebox.showerror("File Not Found", 
                               f"Bot file not found:\n{bot_path}\n\n"
                               "Please check that the bot is installed correctly.")
            self.status_label.config(text=f"Error: {bot_name} file not found", fg="red")
            return
        
        try:
            self.status_label.config(text=f"Launching {bot_name}...", fg="blue")
            self.update()
            
            # Verify the path exists (double-check)
            if not os.path.exists(bot_path):
                error_msg = f"Bot file not found:\n{bot_path}\n\nPlease verify the file exists."
                messagebox.showerror("File Not Found", error_msg)
                self.status_label.config(text=f"Error: {bot_name} file not found", fg="red")
                return
            
            # Launch the bot in a new process (simple launch - let Python handle GUI)
            process = subprocess.Popen([sys.executable, bot_path])
            
            # Give it a brief moment to start
            import time
            time.sleep(0.2)
            
            # Check if process is still running (didn't crash immediately)
            if process.poll() is None:
                # Process is running - success!
                self.status_label.config(text=f"✅ {bot_name} launched successfully", fg="green")
            else:
                # Process exited immediately - there was an error
                return_code = process.returncode
                error_msg = (f"Bot exited immediately with return code {return_code}.\n\n"
                           f"This usually means there's an error in the bot code.\n"
                           f"Please try running the bot directly to see error messages:\n\n"
                           f"python \"{bot_path}\"")
                messagebox.showerror("Launch Error", error_msg)
                self.status_label.config(text=f"Error: {bot_name} exited immediately", fg="red")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            error_msg = (f"Failed to launch {bot_name}:\n\n{str(e)}\n\n"
                        f"Path: {bot_path}\n\n"
                        f"Please verify the path is correct.")
            messagebox.showerror("Launch Error", error_msg)
            self.status_label.config(text=f"Error launching {bot_name}", fg="red")

if __name__ == "__main__":
    app = OperationalAnalyticsLauncher()
    app.mainloop()

