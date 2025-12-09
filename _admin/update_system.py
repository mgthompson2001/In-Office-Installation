#!/usr/bin/env python3
"""
CCMD Bot Master - Centralized Update System
This system allows for easy updates across all employee computers.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import json
import requests
import hashlib
import shutil
import subprocess
from pathlib import Path
import threading
import time
from datetime import datetime

class UpdateSystem:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CCMD Bot Master - Update System")
        self.root.geometry("700x600")
        self.root.configure(bg="#f0f0f0")
        
        # Configuration
        self.update_server_url = "https://your-server.com/ccmd-bots/"  # Replace with your server
        self.local_bot_path = Path(".")
        self.backup_path = Path("backup")
        self.update_log_path = Path("update_log.txt")
        
        # Version tracking
        self.current_version = "1.0.0"
        self.latest_version = None
        self.update_available = False
        
        self._build_ui()
        self._check_for_updates()
    
    def _build_ui(self):
        """Build the update system GUI"""
        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg="#800000", height=60)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="CCMD Bot Master - Update System", 
                              font=("Arial", 18, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Status frame
        status_frame = tk.Frame(main_frame, bg="#f0f0f0")
        status_frame.pack(fill="x", pady=(0, 20))
        
        # Current version
        current_frame = tk.Frame(status_frame, bg="#f0f0f0")
        current_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(current_frame, text="Current Version:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(side="left")
        self.current_version_label = tk.Label(current_frame, text=self.current_version, 
                                            font=("Arial", 12), bg="#f0f0f0", fg="#666666")
        self.current_version_label.pack(side="left", padx=(10, 0))
        
        # Latest version
        latest_frame = tk.Frame(status_frame, bg="#f0f0f0")
        latest_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(latest_frame, text="Latest Version:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(side="left")
        self.latest_version_label = tk.Label(latest_frame, text="Checking...", 
                                           font=("Arial", 12), bg="#f0f0f0", fg="#666666")
        self.latest_version_label.pack(side="left", padx=(10, 0))
        
        # Update status
        self.update_status_label = tk.Label(status_frame, text="", 
                                          font=("Arial", 12, "bold"), bg="#f0f0f0")
        self.update_status_label.pack(pady=(0, 10))
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.pack(fill="x", pady=(0, 20))
        
        # Check for updates button
        self.check_button = tk.Button(buttons_frame, text="Check for Updates", 
                                     command=self._check_for_updates,
                                     bg="#800000", fg="white", font=("Arial", 12, "bold"),
                                     padx=20, pady=10)
        self.check_button.pack(side="left", padx=(0, 10))
        
        # Update button
        self.update_button = tk.Button(buttons_frame, text="Update Now", 
                                      command=self._start_update,
                                      bg="#4caf50", fg="white", font=("Arial", 12, "bold"),
                                      padx=20, pady=10, state="disabled")
        self.update_button.pack(side="left", padx=(0, 10))
        
        # Rollback button
        self.rollback_button = tk.Button(buttons_frame, text="Rollback", 
                                        command=self._rollback_update,
                                        bg="#ff9800", fg="white", font=("Arial", 12, "bold"),
                                        padx=20, pady=10, state="disabled")
        self.rollback_button.pack(side="left")
        
        # Progress frame
        progress_frame = tk.Frame(main_frame, bg="#f0f0f0")
        progress_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(progress_frame, text="Update Progress:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(anchor="w")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        self.progress_label = tk.Label(progress_frame, text="", 
                                     font=("Arial", 10), bg="#f0f0f0", fg="#666666")
        self.progress_label.pack(anchor="w", pady=(5, 0))
        
        # Log frame
        log_frame = tk.Frame(main_frame, bg="#f0f0f0")
        log_frame.pack(fill="both", expand=True)
        
        tk.Label(log_frame, text="Update Log:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(anchor="w")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, 
                                                 font=("Consolas", 9), bg="#f8f8f8")
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Initial log message
        self.log("Update system initialized")
        self.log(f"Current version: {self.current_version}")
    
    def _check_for_updates(self):
        """Check for available updates"""
        self.log("Checking for updates...")
        self.check_button.config(state="disabled")
        
        def check_thread():
            try:
                # Simulate checking for updates (replace with actual server check)
                time.sleep(2)  # Simulate network delay
                
                # For demo purposes, simulate an update available
                self.latest_version = "1.1.0"
                self.update_available = True
                
                self.root.after(0, self._update_check_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self._update_check_error(str(e)))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def _update_check_complete(self):
        """Handle update check completion"""
        self.latest_version_label.config(text=self.latest_version)
        
        if self.update_available:
            self.update_status_label.config(text="🔄 Update Available!", fg="#4caf50")
            self.update_button.config(state="normal")
            self.log(f"Update available: {self.latest_version}")
        else:
            self.update_status_label.config(text="✅ Up to Date", fg="#4caf50")
            self.log("No updates available")
        
        self.check_button.config(state="normal")
    
    def _update_check_error(self, error):
        """Handle update check error"""
        self.latest_version_label.config(text="Error")
        self.update_status_label.config(text="❌ Check Failed", fg="#d32f2f")
        self.log(f"Update check failed: {error}")
        self.check_button.config(state="normal")
    
    def _start_update(self):
        """Start the update process"""
        if not self.update_available:
            messagebox.showwarning("No Update", "No update available.")
            return
        
        result = messagebox.askyesno("Confirm Update", 
                                   f"Update from {self.current_version} to {self.latest_version}?\n\n"
                                   "This will backup your current installation and apply the update.")
        
        if result:
            self._perform_update()
    
    def _perform_update(self):
        """Perform the actual update"""
        self.log("Starting update process...")
        self.update_button.config(state="disabled")
        self.check_button.config(state="disabled")
        
        def update_thread():
            try:
                # Step 1: Create backup
                self.root.after(0, lambda: self._update_progress(10, "Creating backup..."))
                self._create_backup()
                
                # Step 2: Download update
                self.root.after(0, lambda: self._update_progress(30, "Downloading update..."))
                self._download_update()
                
                # Step 3: Apply update
                self.root.after(0, lambda: self._update_progress(60, "Applying update..."))
                self._apply_update()
                
                # Step 4: Verify update
                self.root.after(0, lambda: self._update_progress(90, "Verifying update..."))
                self._verify_update()
                
                # Step 5: Complete
                self.root.after(0, lambda: self._update_progress(100, "Update complete!"))
                self.root.after(0, self._update_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self._update_error(str(e)))
        
        threading.Thread(target=update_thread, daemon=True).start()
    
    def _create_backup(self):
        """Create backup of current installation"""
        self.log("Creating backup...")
        
        # Create backup directory
        self.backup_path.mkdir(exist_ok=True)
        backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / f"backup_{backup_timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        # Copy current files to backup
        for item in self.local_bot_path.iterdir():
            if item.name not in ['backup', 'update_log.txt']:
                if item.is_file():
                    shutil.copy2(item, backup_dir)
                elif item.is_dir():
                    shutil.copytree(item, backup_dir / item.name)
        
        self.log(f"Backup created: {backup_dir}")
        return backup_dir
    
    def _download_update(self):
        """Download the update package"""
        self.log("Downloading update package...")
        
        # Simulate download (replace with actual download logic)
        time.sleep(2)
        
        # In a real implementation, you would:
        # 1. Download the update package from your server
        # 2. Verify the download integrity
        # 3. Extract the package
        
        self.log("Update package downloaded successfully")
    
    def _apply_update(self):
        """Apply the update"""
        self.log("Applying update...")
        
        # Simulate applying update (replace with actual update logic)
        time.sleep(2)
        
        # In a real implementation, you would:
        # 1. Extract the new files
        # 2. Replace old files with new ones
        # 3. Update configuration files
        # 4. Restart services if needed
        
        self.log("Update applied successfully")
    
    def _verify_update(self):
        """Verify the update was successful"""
        self.log("Verifying update...")
        
        # Simulate verification (replace with actual verification logic)
        time.sleep(1)
        
        # In a real implementation, you would:
        # 1. Check file integrity
        # 2. Test critical functionality
        # 3. Verify version numbers
        # 4. Check for any errors
        
        self.log("Update verification successful")
    
    def _update_progress(self, progress, message):
        """Update progress bar and message"""
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.log(message)
    
    def _update_complete(self):
        """Handle update completion"""
        self.current_version = self.latest_version
        self.current_version_label.config(text=self.current_version)
        self.update_status_label.config(text="✅ Update Complete!", fg="#4caf50")
        self.update_button.config(state="disabled")
        self.check_button.config(state="normal")
        self.rollback_button.config(state="normal")
        
        self.log("Update completed successfully!")
        messagebox.showinfo("Update Complete", 
                           f"Successfully updated to version {self.latest_version}!\n\n"
                           "Please restart the application to use the new features.")
    
    def _update_error(self, error):
        """Handle update error"""
        self.update_status_label.config(text="❌ Update Failed", fg="#d32f2f")
        self.update_button.config(state="normal")
        self.check_button.config(state="normal")
        
        self.log(f"Update failed: {error}")
        messagebox.showerror("Update Failed", 
                           f"Update failed with error:\n{error}\n\n"
                           "You can try to rollback to the previous version.")
    
    def _rollback_update(self):
        """Rollback to previous version"""
        result = messagebox.askyesno("Confirm Rollback", 
                                   "Rollback to previous version?\n\n"
                                   "This will restore the backup and undo the last update.")
        
        if result:
            self.log("Rollback not implemented in demo")
            messagebox.showinfo("Rollback", "Rollback functionality would be implemented here.")
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def run(self):
        """Run the update system"""
        self.root.mainloop()

def main():
    """Main function"""
    try:
        app = UpdateSystem()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start update system:\n{e}")

if __name__ == "__main__":
    main()
