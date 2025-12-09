# Billing Department Launcher
# Sub-launcher for Billing Department bots

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys

class BillingDepartmentLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Billing Department - Bot Launcher - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("750x800")
        self._setup_bot_configs()
        self._build_ui()

    def _setup_bot_configs(self):
        """Configure all bots in the Billing Department"""
        from pathlib import Path
        
        # Get base installation directory (go up from _bots/Billing Department to In-Office Installation)
        installation_dir = Path(__file__).parent.parent.parent
        
        self.bots = {
            "Medicare Refiling Bot": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "Medicare Refiling Bot" / "medicare_refiling_bot.py"),
                "description": "Session medium audit bot for TherapyNotes Medicare claims. Compares documented session medium against claim modifiers and prepares audit outputs."
            },
            "TN Refiling Bot": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "TN Refiling Bot" / "tn_refiling_bot.py"),
                "description": "Automated refiling bot for Therapy Notes. Reads client data from Excel/CSV files, extracts claim numbers from scanned PDFs using OCR, and searches for clients using DOB, name, and date of service."
            },
            "Medisoft/Penelope Data Synthesizer": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "Medisoft Penelope Data Synthesizer" / "medisoft_penelope_data_synthesizer.py"),
                "description": "Synthesizes data from a PDF report and Excel spreadsheet. Matches records based on Chart column (PDF) and PT code Column E (Excel), combining Date of Service, Penelope ID, DOB, modifiers, counselor names, supervisor, and all other relevant information."
            },
            "Medicare Modifier Comparison Bot": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "Medicare Modifier Comparison Bot" / "medicare_modifier_comparison_bot.py"),
                "description": "Compares two Excel files to identify modifier mismatches. Matches records by Name, DOB, and Date of Service, then compares Session Medium (File 1, Column F) with Modifier (File 2, Column G) to determine which claims need refiling."
            }
        }

    def _build_ui(self):
        """Build the department launcher UI"""
        # Header
        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text="Billing Department", bg="#660000", fg="white",
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
        
        tk.Label(desc_frame, text=bot_info["description"],
                font=("Segoe UI", 9), fg="gray", bg="white",
                wraplength=600, justify="left", anchor="w").pack(anchor="w")

    def _launch_bot(self, bot_name):
        """Launch the selected bot"""
        if bot_name not in self.bots:
            messagebox.showerror("Error", "Invalid bot selection.")
            return

        bot_info = self.bots[bot_name]
        bot_path = bot_info["path"]

        self.status_label.config(text=f"Launching {bot_name}...", fg="blue")
        self.update()

        try:
            if bot_info.get("is_folder", False):
                self._launch_folder_bot(bot_path, bot_name)
            else:
                self._launch_file_bot(bot_path, bot_name)
            
            self.status_label.config(text=f"✓ {bot_name} launched successfully!", fg="green")
        except Exception as e:
            self.status_label.config(text=f"✗ Failed to launch {bot_name}", fg="red")
            messagebox.showerror("Launch Error", f"Failed to launch {bot_name}:\n{str(e)}")

    def _launch_file_bot(self, file_path, bot_name):
        """Launch a single file bot"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        subprocess.Popen([sys.executable, file_path])
        print(f"[LAUNCH] {bot_name} - {file_path}")

    def _launch_folder_bot(self, folder_path, bot_name):
        """Launch a folder-based bot"""
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        # Look for common entry point files
        entry_points = ["main.py", "launcher.py", "app.py", "bot.py", "run.py"]
        
        for entry_point in entry_points:
            full_path = os.path.join(folder_path, entry_point)
            if os.path.exists(full_path):
                subprocess.Popen([sys.executable, full_path])
                print(f"[LAUNCH] {bot_name} - {full_path}")
                return
        
        # If no entry point found, open the folder
        if sys.platform == "win32":
            os.startfile(folder_path)
        else:
            subprocess.Popen(["xdg-open", folder_path])
        
        messagebox.showinfo("Manual Launch Required", 
                          f"Bot folder opened: {folder_path}\n\nPlease launch the bot manually from this folder.")

if __name__ == "__main__":
    app = BillingDepartmentLauncher()
    app.mainloop()

