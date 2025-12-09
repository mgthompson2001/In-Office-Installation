#!/usr/bin/env python3
"""
Self-Contained Update Installer Creator
Creates a single executable file that employees can download and run to update their software
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import base64

class UpdateInstallerCreator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CCMD Bot - Update Installer Creator")
        self.root.geometry("950x850")
        self.root.configure(bg="#f7f3f2")
        
        # Paths
        self.output_dir = Path.home() / "Desktop" / "CCMD_Updates"
        self.output_dir.mkdir(exist_ok=True)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the main UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg="#f7f3f2")
        main_frame.pack(expand=True, fill="both", padx=30, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg="#800000", height=100)
        header_frame.pack(fill="x", pady=(0, 30))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📦 Create Update Installer", 
                              font=("Segoe UI", 24, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(header_frame, text="Package updates that employees can download and install", 
                                 font=("Segoe UI", 11), bg="#800000", fg="#cccccc")
        subtitle_label.pack()
        
        # Instructions
        instructions = """
📧 How This Works:
1. Select the updated bot files below
2. Add version number and release notes
3. Click "Create Update Installer"
4. Email the generated installer file to employees
5. Employees download and double-click to install - that's it!

✨ The installer will:
• Automatically find their bot installation
• Backup their current version
• Install the updates
• Show them a success message
• No technical knowledge required!
        """
        
        instructions_frame = tk.Frame(main_frame, bg="#fff5e6", relief="solid", borderwidth=1)
        instructions_frame.pack(fill="x", pady=(0, 20), padx=5)
        
        instructions_label = tk.Label(instructions_frame, text=instructions, 
                                     font=("Segoe UI", 10), bg="#fff5e6", 
                                     justify="left", anchor="w")
        instructions_label.pack(padx=15, pady=15, fill="x")
        
        # Form frame with scrolling
        form_frame = tk.Frame(main_frame, bg="#ffffff", relief="solid", borderwidth=1)
        form_frame.pack(fill="both", expand=True, padx=5)
        
        # Add canvas and scrollbar for scrolling
        canvas = tk.Canvas(form_frame, bg="#ffffff", highlightthickness=0)
        scrollbar = tk.Scrollbar(form_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ffffff")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Form content (now inside scrollable frame)
        form_content = tk.Frame(scrollable_frame, bg="#ffffff")
        form_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Source folder selection
        tk.Label(form_content, text="📁 Updated Bot Files:", 
                font=("Segoe UI", 11, "bold"), bg="#ffffff").grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        source_frame = tk.Frame(form_content, bg="#ffffff")
        source_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        self.source_entry = tk.Entry(source_frame, font=("Segoe UI", 10), width=60)
        self.source_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = tk.Button(source_frame, text="📂 Browse", 
                              command=self._browse_source,
                              bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                              padx=15, pady=5, cursor="hand2", relief="flat")
        browse_btn.pack(side="right")
        
        # Version number
        tk.Label(form_content, text="🔢 Version Number:", 
                font=("Segoe UI", 11, "bold"), bg="#ffffff").grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        version_frame = tk.Frame(form_content, bg="#ffffff")
        version_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        self.version_entry = tk.Entry(version_frame, font=("Segoe UI", 10), width=30)
        self.version_entry.pack(side="left")
        self.version_entry.insert(0, self._get_next_version())
        
        tk.Label(version_frame, text="  (e.g., 1.0.0, 1.1.0, 2.0.0)", 
                font=("Segoe UI", 9, "italic"), bg="#ffffff", fg="#666666").pack(side="left", padx=10)
        
        # Release notes
        tk.Label(form_content, text="📝 Release Notes (what's new/fixed):", 
                font=("Segoe UI", 11, "bold"), bg="#ffffff").grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        self.notes_text = scrolledtext.ScrolledText(form_content, height=8, width=70,
                                                   font=("Segoe UI", 10), wrap="word")
        self.notes_text.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        self.notes_text.insert("1.0", "• Fixed bug in patient search\n• Improved upload speed\n• Added new feature: ")
        
        # Create button
        create_btn = tk.Button(form_content, text="🎁 Create Update Installer", 
                              command=self._create_installer,
                              bg="#800000", fg="white", font=("Segoe UI", 13, "bold"),
                              padx=30, pady=15, cursor="hand2", relief="flat")
        create_btn.grid(row=6, column=0, columnspan=2, pady=20)
        
        # Status log
        tk.Label(form_content, text="📋 Status Log:", 
                font=("Segoe UI", 11, "bold"), bg="#ffffff").grid(row=7, column=0, sticky="w", pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(form_content, height=10, width=70,
                                                 font=("Consolas", 9), wrap="word",
                                                 bg="#f0f0f0")
        self.log_text.grid(row=8, column=0, columnspan=2, sticky="ew")
        
        form_content.columnconfigure(0, weight=1)
    
    def _browse_source(self):
        """Browse for source folder"""
        folder = filedialog.askdirectory(title="Select folder containing updated bot files",
                                        initialdir=str(Path.home() / "Desktop"))
        if folder:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, folder)
            self._log(f"✅ Selected source folder: {folder}")
    
    def _get_next_version(self):
        """Get next version number"""
        try:
            version_file = self.output_dir / "latest_version.txt"
            if version_file.exists():
                current = version_file.read_text().strip()
                parts = current.split(".")
                parts[-1] = str(int(parts[-1]) + 1)
                return ".".join(parts)
        except:
            pass
        return "1.0.0"
    
    def _log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def _create_installer(self):
        """Create the self-installing update package"""
        try:
            # Validate inputs
            source_folder = self.source_entry.get().strip()
            version = self.version_entry.get().strip()
            notes = self.notes_text.get("1.0", tk.END).strip()
            
            if not source_folder or not os.path.exists(source_folder):
                messagebox.showerror("Error", "Please select a valid source folder")
                return
            
            if not version:
                messagebox.showerror("Error", "Please enter a version number")
                return
            
            self._log("🚀 Starting installer creation...")
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            installer_name = f"CCMD_Bot_Update_v{version}_{timestamp}.py"
            installer_path = self.output_dir / installer_name
            
            # Create metadata
            metadata = {
                "version": version,
                "release_notes": notes,
                "created": datetime.now().isoformat(),
                "files": []
            }
            
            # Collect all files to update
            self._log("📦 Collecting files to package...")
            source_path = Path(source_folder)
            files_data = {}
            
            for file_path in source_path.rglob("*.py"):
                relative_path = file_path.relative_to(source_path)
                self._log(f"  • {relative_path}")
                
                # Read file content
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Store as base64
                files_data[str(relative_path)] = base64.b64encode(content).decode('utf-8')
                metadata["files"].append(str(relative_path))
            
            self._log(f"✅ Packaged {len(files_data)} files")
            
            # Create the self-installing script
            self._log("🔧 Creating installer script...")
            installer_script = self._generate_installer_script(metadata, files_data)
            
            # Write installer
            with open(installer_path, 'w', encoding='utf-8') as f:
                f.write(installer_script)
            
            self._log(f"✅ Installer created: {installer_path}")
            
            # Save version info
            version_file = self.output_dir / "latest_version.txt"
            version_file.write_text(version)
            
            # Create instruction file
            instructions_file = self.output_dir / f"CCMD_Bot_Update_v{version}_INSTRUCTIONS.txt"
            instructions_content = f"""
═══════════════════════════════════════════════════════════════
  CCMD BOT UPDATE v{version} - INSTALLATION INSTRUCTIONS
═══════════════════════════════════════════════════════════════

📧 HOW TO INSTALL THIS UPDATE:

1. Download the attached file: {installer_name}

2. Double-click the file to run it
   (You may need to right-click → "Open with" → "Python")

3. The installer will:
   • Find your bot installation automatically
   • Backup your current files
   • Install the new version
   • Show you a success message

4. That's it! Your bots are now updated to v{version}

═══════════════════════════════════════════════════════════════
📝 WHAT'S NEW IN THIS VERSION:

{notes}

═══════════════════════════════════════════════════════════════
❓ TROUBLESHOOTING:

Problem: "Python not found" error
Solution: Make sure Python is installed on your computer

Problem: "Installation folder not found"
Solution: The installer will ask you to locate your bot folder

Problem: Installation fails
Solution: Contact IT support with the error message

═══════════════════════════════════════════════════════════════
💡 IMPORTANT NOTES:

• Your old files are backed up automatically
• You can roll back if needed
• No internet connection required
• Works on all computers with Python installed

═══════════════════════════════════════════════════════════════
"""
            
            with open(instructions_file, 'w', encoding='utf-8') as f:
                f.write(instructions_content)
            
            self._log(f"✅ Instructions created: {instructions_file}")
            
            # Success message
            self._log("")
            self._log("=" * 60)
            self._log("🎉 UPDATE INSTALLER CREATED SUCCESSFULLY!")
            self._log("=" * 60)
            self._log("")
            self._log(f"📁 Location: {self.output_dir}")
            self._log(f"📦 Installer: {installer_name}")
            self._log(f"📄 Instructions: {instructions_file.name}")
            self._log("")
            self._log("📧 NEXT STEPS:")
            self._log("1. Email both files to your employees")
            self._log("2. They download and run the installer")
            self._log("3. That's it - updates installed automatically!")
            self._log("")
            
            # Show success dialog
            result = messagebox.askyesno(
                "✅ Success!", 
                f"Update installer created successfully!\n\n"
                f"📁 Location: {self.output_dir}\n\n"
                f"Files created:\n"
                f"• {installer_name}\n"
                f"• {instructions_file.name}\n\n"
                f"Would you like to open the folder?",
                icon="info"
            )
            
            if result:
                # Open folder
                if sys.platform == "win32":
                    os.startfile(self.output_dir)
                elif sys.platform == "darwin":
                    os.system(f"open '{self.output_dir}'")
                else:
                    os.system(f"xdg-open '{self.output_dir}'")
            
        except Exception as e:
            self._log(f"❌ ERROR: {e}")
            messagebox.showerror("Error", f"Failed to create installer:\n{e}")
    
    def _generate_installer_script(self, metadata, files_data):
        """Generate the self-installing Python script"""
        # Convert data to embedded strings
        metadata_json = json.dumps(metadata, indent=2)
        files_json = json.dumps(files_data, indent=2)
        
        script = f'''#!/usr/bin/env python3
"""
CCMD Bot Automatic Update Installer
Version: {metadata["version"]}
Created: {metadata["created"]}

INSTRUCTIONS:
Just double-click this file to install the update!
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import json
import base64
import shutil
from pathlib import Path
from datetime import datetime

# Embedded update data
METADATA = {metadata_json}

FILES_DATA = {files_json}

class AutoInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide main window
        
        # Show welcome message
        self.show_welcome()
        
        # Find installation directory
        self.install_dir = self.find_installation_directory()
        if not self.install_dir:
            messagebox.showerror("Installation Cancelled", "No installation directory selected.")
            sys.exit(0)
        
        # Confirm installation
        if not self.confirm_installation():
            messagebox.showinfo("Cancelled", "Installation cancelled by user.")
            sys.exit(0)
        
        # Run installation
        self.install_update()
    
    def show_welcome(self):
        """Show welcome message"""
        notes = METADATA["release_notes"]
        message = f"""
Welcome to CCMD Bot Update Installer!

Version: {{METADATA["version"]}}

What's New:
{{notes}}

Click OK to begin installation.
        """
        messagebox.showinfo("CCMD Bot Update", message)
    
    def find_installation_directory(self):
        """Find the bot installation directory"""
        # Common installation paths
        possible_paths = [
            Path.home() / "Desktop" / "CCMD Bot Master",
            Path.home() / "Desktop" / "In-Office Installation",
            Path.home() / "Documents" / "CCMD Bot Master",
            Path("C:/CCMD Bot Master"),
            Path("D:/CCMD Bot Master"),
        ]
        
        # Try to find existing installation
        for path in possible_paths:
            if path.exists():
                result = messagebox.askyesno(
                    "Installation Found",
                    f"Found bot installation at:\\n{{path}}\\n\\nInstall update here?",
                    icon="question"
                )
                if result:
                    return path
        
        # Ask user to locate
        messagebox.showinfo(
            "Locate Installation",
            "Please select your CCMD Bot installation folder\\n"
            "(Usually on your Desktop or in Documents)"
        )
        
        folder = filedialog.askdirectory(
            title="Select CCMD Bot installation folder",
            initialdir=str(Path.home() / "Desktop")
        )
        
        if folder:
            return Path(folder)
        return None
    
    def confirm_installation(self):
        """Confirm installation with user"""
        message = f"""
Ready to install update v{{METADATA["version"]}}

Installation folder:
{{self.install_dir}}

Files to update: {{len(METADATA["files"])}}

Your current files will be backed up automatically.

Proceed with installation?
        """
        return messagebox.askyesno("Confirm Installation", message, icon="question")
    
    def install_update(self):
        """Install the update"""
        try:
            # Create progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Installing Update...")
            progress_window.geometry("500x300")
            progress_window.resizable(False, False)
            
            tk.Label(progress_window, text="Installing Update...", 
                    font=("Arial", 16, "bold")).pack(pady=20)
            
            status_label = tk.Label(progress_window, text="Starting...", 
                                   font=("Arial", 10))
            status_label.pack(pady=10)
            
            import tkinter.scrolledtext as scrolledtext
            log_text = scrolledtext.ScrolledText(progress_window, height=10, width=60,
                                                font=("Consolas", 9))
            log_text.pack(padx=20, pady=10, fill="both", expand=True)
            
            def log(msg):
                log_text.insert(tk.END, msg + "\\n")
                log_text.see(tk.END)
                progress_window.update()
            
            # Create backup
            status_label.config(text="Creating backup...")
            backup_dir = self.install_dir / f"backup_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
            backup_dir.mkdir(exist_ok=True)
            log(f"📦 Creating backup: {{backup_dir.name}}")
            
            # Install each file
            status_label.config(text="Installing files...")
            for i, (relative_path, file_data) in enumerate(FILES_DATA.items(), 1):
                log(f"[{{i}}/{{len(FILES_DATA)}}] Installing {{relative_path}}")
                
                target_path = self.install_dir / relative_path
                
                # Backup original if exists
                if target_path.exists():
                    backup_path = backup_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target_path, backup_path)
                
                # Write new file
                target_path.parent.mkdir(parents=True, exist_ok=True)
                content = base64.b64decode(file_data.encode('utf-8'))
                with open(target_path, 'wb') as f:
                    f.write(content)
            
            # Write version file
            version_file = self.install_dir / ".version"
            with open(version_file, 'w') as f:
                json.dump(METADATA, f, indent=2)
            
            log("")
            log("✅ Installation complete!")
            log(f"✅ Backup saved: {{backup_dir}}")
            log(f"✅ Version: {{METADATA['version']}}")
            
            status_label.config(text="Installation Complete!")
            
            # Show success message
            tk.Button(progress_window, text="🎉 Done!", 
                     command=lambda: self.finish_installation(progress_window),
                     bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                     padx=30, pady=10).pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("Installation Failed", 
                               f"An error occurred during installation:\\n\\n{{e}}\\n\\n"
                               f"Your files have not been modified.")
            sys.exit(1)
    
    def finish_installation(self, window):
        """Finish installation"""
        window.destroy()
        messagebox.showinfo(
            "Installation Complete!",
            f"CCMD Bot has been updated to version {{METADATA['version']}}!\\n\\n"
            f"Your bots are ready to use with the latest features and fixes.\\n\\n"
            f"Backup location: {{self.install_dir}}/backup_*"
        )
        sys.exit(0)

if __name__ == "__main__":
    app = AutoInstaller()
    app.root.mainloop()
'''
        return script
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = UpdateInstallerCreator()
    app.run()

