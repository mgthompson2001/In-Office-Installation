# Intake & Referral Department Launcher
# Sub-launcher for Intake & Referral Department bots

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys

class IntakeReferralLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Intake & Referral Department - Bot Launcher - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("700x600")
        self._setup_bot_configs()
        self._build_ui()
        self._setup_scrolling()

    def _setup_bot_configs(self):
        """Configure all bots in the Intake & Referral Department"""
        from pathlib import Path
        
        # Get base installation directory (go up from _bots/Launcher to In-Office Installation)
        installation_dir = Path(__file__).parent.parent.parent
        
        self.bots = {
            "Remove Counselor Bot": {
                "path": str(installation_dir / "_bots" / "Cursor versions" / "Goose" / "isws_remove_counselor_botcursor3.py"),
                "description": "Remove counselor assignments from client records in Therapy Notes. Processes CSV files with client data and removes specified counselors from the Clinicians tab."
            },
            "Referral Form/Upload Bot": {
                "path": str(installation_dir / "_bots" / "Referral bot and bridge (final)" / "isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py"),
                "description": "Create and upload referral forms. Generates PDFs from CSV data and includes 'Launch Uploader' button for dual-tab Base/IPS uploader."
            },
            "Counselor Assignment Bot": {
                "path": str(installation_dir / "_bots" / "Referral bot and bridge (final)" / "counselor_assignment_bot.py"),
                "description": "Assign counselors to clients based on CSV data. Automates counselor assignment process in the Penelope system."
            },
            "Existing Client Referral Form Bot": {
                "path": str(installation_dir / "_bots" / "Referral bot and bridge (final)" / "existing_client_referral_form_bot.py"),
                "description": "Navigate to existing client profiles, extract counselor assignment notes, and navigate to Pre-Enrollment Waiting for Allocation. Includes uploader integration for referral form uploads."
            },
            "Referral Document Cleanup Bot": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "Medisoft Billing" / "Referral Document Cleanup Bot" / "referral_document_cleanup_bot.py"),
                "description": "Clean up old documents (30+ days) from Therapy Notes 'New Referrals' patient groups. Reads counselors from Excel and removes documents based on filters (All, IA Only, Reassignment)."
            }
        }

    def _build_ui(self):
        """Build the department launcher UI"""
        # Header
        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text="Intake & Referral Department", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=8).pack(side="left", padx=12)
        
        # Back button in header
        back_btn = tk.Button(header, text="← Back to Main Menu", command=self.destroy,
                           bg="#800000", fg="white", font=("Segoe UI", 9),
                           relief="flat", padx=10, pady=4, cursor="hand2")
        back_btn.pack(side="right", padx=12)

        # Create scrollable canvas
        canvas = tk.Canvas(self, bg="white")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="white")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for scrolling
        self.canvas = canvas
        
        # Main content (inside scrollable frame)
        main_frame = tk.Frame(self.scrollable_frame)
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)

        # Instructions
        instructions = tk.Label(main_frame, 
                               text="Select a bot from the list below to launch it:",
                               font=("Segoe UI", 10),
                               wraplength=640)
        instructions.pack(pady=(0, 20))

        # Bot cards
        for bot_name, bot_info in self.bots.items():
            self._create_bot_card(main_frame, bot_name, bot_info)

        # Status area
        status_frame = tk.LabelFrame(main_frame, text="Status", font=("Segoe UI", 9, "bold"))
        status_frame.pack(fill="x", pady=(15, 0))
        
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
    
    def _setup_scrolling(self):
        """Setup mouse wheel scrolling for the entire window"""
        def _on_mousewheel(event):
            """Handle mouse wheel scrolling"""
            # Scroll the canvas
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _bind_to_mousewheel(event):
            """Bind mouse wheel to canvas when mouse enters"""
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            """Unbind mouse wheel when mouse leaves"""
            self.canvas.unbind_all("<MouseWheel>")
        
        # Bind mouse wheel to canvas
        self.canvas.bind("<Enter>", _bind_to_mousewheel)
        self.canvas.bind("<Leave>", _unbind_from_mousewheel)
        
        # Also bind to the scrollable frame and all child widgets
        def bind_recursive(widget):
            """Recursively bind mouse wheel to all widgets"""
            widget.bind("<Enter>", _bind_to_mousewheel)
            widget.bind("<Leave>", _unbind_from_mousewheel)
            for child in widget.winfo_children():
                bind_recursive(child)
        
        bind_recursive(self.scrollable_frame)
        
        # Bind mouse wheel to the main window as well
        self.bind("<Enter>", _bind_to_mousewheel)
        self.bind("<Leave>", _unbind_from_mousewheel)

if __name__ == "__main__":
    app = IntakeReferralLauncher()
    app.mainloop()

