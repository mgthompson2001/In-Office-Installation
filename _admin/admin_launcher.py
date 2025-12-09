#!/usr/bin/env python3
"""
CCMD Bot - Admin Control Panel
Unified launcher for all administrative tools
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from pathlib import Path
import hashlib
import time

class AdminLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CCMD Bot - Admin Control Panel")
        self.geometry("1100x900")
        self.configure(bg="#f7f3f2")
        
        # Security
        self.correct_password = "Integritycode1!"
        self.max_attempts = 3
        self.attempts = 0
        self.access_granted = False
        
        # Check access first
        self._check_access()
        
        if self.access_granted:
            self._build_ui()
    
    def _check_access(self):
        """Check password before granting access"""
        # Create password dialog
        dialog = tk.Toplevel(self)
        dialog.title("Authentication Required")
        dialog.geometry("500x320")
        dialog.configure(bg="#f0f0f0")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (320 // 2)
        dialog.geometry(f"500x320+{x}+{y}")
        
        # Header
        header = tk.Frame(dialog, bg="#800000", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="🔒 Admin Access Required", 
                font=("Segoe UI", 16, "bold"), bg="#800000", fg="white").pack(expand=True)
        
        # Content
        content = tk.Frame(dialog, bg="#f0f0f0")
        content.pack(expand=True, fill="both", padx=30, pady=20)
        
        tk.Label(content, text="Enter administrator password:", 
                font=("Segoe UI", 11), bg="#f0f0f0").pack(pady=(0, 10))
        
        password_var = tk.StringVar()
        password_entry = tk.Entry(content, textvariable=password_var, show="●", 
                                 font=("Segoe UI", 12), width=25)
        password_entry.pack(pady=10)
        password_entry.focus()
        
        error_label = tk.Label(content, text="", font=("Segoe UI", 9), 
                              bg="#f0f0f0", fg="red")
        error_label.pack(pady=5)
        
        def check_password():
            if password_var.get() == self.correct_password:
                self.access_granted = True
                dialog.destroy()
            else:
                self.attempts += 1
                remaining = self.max_attempts - self.attempts
                if remaining > 0:
                    error_label.config(text=f"❌ Incorrect password. {remaining} attempts remaining.")
                    password_entry.delete(0, tk.END)
                    password_entry.focus()
                else:
                    messagebox.showerror("Access Denied", 
                                       "Maximum attempts exceeded.\nAccess denied.")
                    dialog.destroy()
                    self.destroy()
                    sys.exit(0)
        
        def on_enter(event):
            check_password()
        
        password_entry.bind("<Return>", on_enter)
        
        btn_frame = tk.Frame(content, bg="#f0f0f0")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="Login", command=check_password,
                 bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2", relief="flat").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Cancel", command=lambda: [dialog.destroy(), self.destroy(), sys.exit(0)],
                 bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2", relief="flat").pack(side="left", padx=5)
        
        # Wait for dialog to close
        self.wait_window(dialog)
    
    def _build_ui(self):
        """Build the main admin interface"""
        # Main container
        main_frame = tk.Frame(self, bg="#f7f3f2")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg="#800000", height=120)
        header_frame.pack(fill="x", pady=(0, 30))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="🛠️ CCMD Bot Admin Control Panel", 
                font=("Segoe UI", 26, "bold"), bg="#800000", fg="white").pack(expand=True)
        
        tk.Label(header_frame, text="Choose an administrative tool below", 
                font=("Segoe UI", 12), bg="#800000", fg="#cccccc").pack()
        
        # Tools grid
        tools_frame = tk.Frame(main_frame, bg="#f7f3f2")
        tools_frame.pack(expand=True, fill="both")
        
        # Configure grid
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.columnconfigure(1, weight=1)
        
        # Tool cards
        tools = [
            {
                "title": "📧 Email Update Creator",
                "subtitle": "RECOMMENDED - Easiest Method",
                "description": "Create update installers that employees can download and install via email.\n\n✓ No network setup needed\n✓ Works anywhere\n✓ One-click install for users",
                "script": "create_update_installer.py",
                "color": "#4CAF50",
                "row": 0,
                "col": 0
            },
            {
                "title": "🌐 Network Update Manager",
                "subtitle": "For Advanced Users",
                "description": "Centralized update system using shared network drives.\n\n✓ Push updates to all computers\n✓ Real-time monitoring\n✓ Requires network setup",
                "script": "easy_update_manager.py",
                "color": "#2196F3",
                "row": 0,
                "col": 1
            },
            {
                "title": "🚀 Bot Launcher",
                "subtitle": "For Testing",
                "description": "Launch bots directly from this computer for testing.\n\n✓ Test before deploying\n✓ Quick access\n✓ Development mode",
                "script": "secure_launcher.py",
                "color": "#FF9800",
                "row": 1,
                "col": 0
            },
            {
                "title": "📚 Documentation",
                "subtitle": "Help & Guides",
                "description": "View comprehensive guides and documentation.\n\n✓ Step-by-step instructions\n✓ Troubleshooting\n✓ Best practices",
                "script": None,
                "color": "#9C27B0",
                "row": 1,
                "col": 1
            }
        ]
        
        for tool in tools:
            self._create_tool_card(tools_frame, tool)
        
        # Footer
        footer_frame = tk.Frame(main_frame, bg="#f7f3f2")
        footer_frame.pack(fill="x", pady=(20, 0))
        
        tk.Label(footer_frame, text="💡 Tip: Start with the Email Update Creator - it's the easiest way to distribute updates!", 
                font=("Segoe UI", 10, "italic"), bg="#fff5e6", fg="#856404",
                relief="solid", borderwidth=1, padx=15, pady=10).pack(fill="x")
        
        # Exit button
        tk.Button(footer_frame, text="❌ Exit", command=self.quit,
                 bg="#f44336", fg="white", font=("Segoe UI", 11, "bold"),
                 padx=25, pady=10, cursor="hand2", relief="flat").pack(pady=15)
    
    def _create_tool_card(self, parent, tool):
        """Create a tool card"""
        card = tk.Frame(parent, bg="white", relief="solid", borderwidth=1)
        card.grid(row=tool["row"], column=tool["col"], padx=10, pady=10, sticky="nsew")
        
        # Header bar
        header = tk.Frame(card, bg=tool["color"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text=tool["title"], 
                font=("Segoe UI", 14, "bold"), bg=tool["color"], fg="white").pack(expand=True)
        
        # Subtitle
        subtitle_frame = tk.Frame(card, bg="#f0f0f0")
        subtitle_frame.pack(fill="x")
        
        tk.Label(subtitle_frame, text=tool["subtitle"], 
                font=("Segoe UI", 9, "italic"), bg="#f0f0f0", fg="#666666").pack(pady=5)
        
        # Content
        content = tk.Frame(card, bg="white")
        content.pack(expand=True, fill="both", padx=15, pady=15)
        
        tk.Label(content, text=tool["description"], 
                font=("Segoe UI", 10), bg="white", fg="#333333",
                justify="left", wraplength=350).pack(anchor="w")
        
        # Button
        button_frame = tk.Frame(card, bg="white")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        if tool["script"]:
            btn = tk.Button(button_frame, text="🚀 Launch", 
                          command=lambda s=tool["script"]: self._launch_tool(s),
                          bg=tool["color"], fg="white", font=("Segoe UI", 11, "bold"),
                          padx=30, pady=10, cursor="hand2", relief="flat")
        else:
            btn = tk.Button(button_frame, text="📖 View Guides", 
                          command=self._show_documentation,
                          bg=tool["color"], fg="white", font=("Segoe UI", 11, "bold"),
                          padx=30, pady=10, cursor="hand2", relief="flat")
        
        btn.pack()
    
    def _launch_tool(self, script_name):
        """Launch an administrative tool"""
        try:
            script_path = Path(__file__).parent / script_name
            
            if not script_path.exists():
                messagebox.showerror("Error", f"Tool not found:\n{script_path}")
                return
            
            # Launch the tool
            if sys.platform == "win32":
                os.startfile(script_path)
            else:
                subprocess.Popen([sys.executable, str(script_path)])
            
            # Minimize this window
            self.iconify()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch tool:\n{e}")
    
    def _show_documentation(self):
        """Show documentation menu"""
        # Create documentation dialog
        dialog = tk.Toplevel(self)
        dialog.title("📚 Documentation & Guides")
        dialog.geometry("600x500")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        
        # Header
        header = tk.Frame(dialog, bg="#9C27B0", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="📚 Documentation & Guides", 
                font=("Segoe UI", 16, "bold"), bg="#9C27B0", fg="white").pack(expand=True)
        
        # Content
        content = tk.Frame(dialog, bg="#f0f0f0")
        content.pack(expand=True, fill="both", padx=20, pady=20)
        
        docs = [
            {
                "title": "📧 Email Update System Guide",
                "file": "EMAIL_UPDATE_GUIDE.md",
                "description": "How to create and send updates via email"
            },
            {
                "title": "🎯 Non-Technical User Guide",
                "file": "NON_TECHNICAL_GUIDE.md",
                "description": "Simple guide for people who don't code"
            },
            {
                "title": "📖 Main README",
                "file": "README.md",
                "description": "Overview of the entire system"
            },
            {
                "title": "🚀 Quick Deployment Guide",
                "file": "QUICK_DEPLOYMENT_GUIDE.md",
                "description": "Fast setup instructions"
            }
        ]
        
        for doc in docs:
            doc_frame = tk.Frame(content, bg="white", relief="solid", borderwidth=1)
            doc_frame.pack(fill="x", pady=5)
            
            info_frame = tk.Frame(doc_frame, bg="white")
            info_frame.pack(side="left", expand=True, fill="both", padx=15, pady=10)
            
            tk.Label(info_frame, text=doc["title"], 
                    font=("Segoe UI", 11, "bold"), bg="white", anchor="w").pack(anchor="w")
            
            tk.Label(info_frame, text=doc["description"], 
                    font=("Segoe UI", 9), bg="white", fg="#666666", anchor="w").pack(anchor="w")
            
            btn_frame = tk.Frame(doc_frame, bg="white")
            btn_frame.pack(side="right", padx=10)
            
            file_path = Path(__file__).parent / doc["file"]
            if file_path.exists():
                tk.Button(btn_frame, text="📖 Open", 
                         command=lambda f=file_path: self._open_file(f),
                         bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"),
                         padx=15, pady=5, cursor="hand2", relief="flat").pack()
            else:
                tk.Label(btn_frame, text="Not found", 
                        font=("Segoe UI", 9), fg="#999999").pack()
        
        # Close button
        tk.Button(content, text="Close", command=dialog.destroy,
                 bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, cursor="hand2", relief="flat").pack(pady=20)
    
    def _open_file(self, file_path):
        """Open a file with default application"""
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(file_path)])
            else:
                subprocess.Popen(["xdg-open", str(file_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")

if __name__ == "__main__":
    app = AdminLauncher()
    app.mainloop()

