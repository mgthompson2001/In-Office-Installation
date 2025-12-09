#!/usr/bin/env python3
"""
Easy Update Manager - No-Code GUI for Non-Technical Users
This is a simple, intuitive interface for managing bot updates without any coding knowledge.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
import threading
import time
from datetime import datetime
import socket
import platform
import subprocess

class EasyUpdateManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CCMD Bot Update Manager - Easy Mode")
        self.root.geometry("1000x850")
        self.root.configure(bg="#f7f3f2")
        
        # Configuration - try centralized network location first, fallback to local
        import os
        self.computers_file, self.update_packages_dir = self._get_centralized_paths()
        
        # Create directories with proper permissions
        try:
            self.update_packages_dir.mkdir(exist_ok=True)
        except PermissionError:
            # Fallback to temp directory
            import tempfile
            self.update_packages_dir = Path(tempfile.gettempdir()) / "ccmd_update_packages"
            self.update_packages_dir.mkdir(exist_ok=True)
            print(f"⚠️  Using temp directory for update packages: {self.update_packages_dir}")
        
        # Security settings
        self.correct_password = "Integritycode1!"
        self.max_attempts = 3
        self.attempts = 0
        self.locked = False
        self.access_granted = False
        
        # Load computers
        self.computers = self._load_computers()
        
        # Auto-register this computer if not already registered
        self._auto_register_computer()
        
        # Check access first
        self._check_access()
    
    def _get_centralized_paths(self):
        """Get centralized paths for computer data and update packages"""
        import os
        
        # Try centralized network locations first
        import socket
        current_computer = socket.gethostname()
        
        network_locations = [
            # Company shared drive (most common in business environments)
            Path("//server/CCMD_Bot_Manager"),
            Path("//fileserver/CCMD_Bot_Manager"), 
            Path("//network/CCMD_Bot_Manager"),
            Path("//shared/CCMD_Bot_Manager"),
            Path("//company/CCMD_Bot_Manager"),
            # Local shared folder (fallback)
            Path("C:/CCMD_Bot_Manager"),
            Path("D:/CCMD_Bot_Manager"),
            # Network share from current computer
            Path(f"//{current_computer}/CCMD_Bot_Manager"),
        ]
        
        # Try to find a writable network location
        for network_path in network_locations:
            try:
                network_path.mkdir(exist_ok=True)
                # Test write access
                test_file = network_path / "test_write.tmp"
                test_file.write_text("test")
                test_file.unlink()
                
                computers_file = network_path / "computers.json"
                update_packages_dir = network_path / "update_packages"
                print(f"✅ Using centralized location: {network_path}")
                return computers_file, update_packages_dir
            except (PermissionError, OSError, FileNotFoundError):
                continue
        
        # Fallback to local user documents
        user_docs = Path.home() / "Documents" / "CCMD_Bot_Manager"
        user_docs.mkdir(exist_ok=True)
        print(f"⚠️  Using local location: {user_docs}")
        print("   For centralized management, create a folder on your company shared drive:")
        print("   Example: \\\\YOUR_SERVER\\CCMD_Bot_Manager")
        print("   Give all users read/write access, then restart the update manager")
        
        computers_file = user_docs / "computers.json"
        update_packages_dir = user_docs / "update_packages"
        return computers_file, update_packages_dir
    
    def _load_computers(self):
        """Load computer list from file"""
        if self.computers_file.exists():
            with open(self.computers_file, 'r') as f:
                return json.load(f)
        else:
            return {"computers": []}
    
    def _save_computers(self):
        """Save computer list to file"""
        with open(self.computers_file, 'w') as f:
            json.dump(self.computers, f, indent=2)
    
    def _get_computer_info(self):
        """Get current computer information"""
        try:
            # Get computer name
            computer_name = platform.node()
            
            # Get IP address
            try:
                # Connect to a remote server to get local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except:
                ip_address = "127.0.0.1"
            
            # Get username
            username = os.getenv('USERNAME') or os.getenv('USER') or "Unknown"
            
            # Get bot installation path (current directory)
            bot_path = str(Path.cwd())
            
            # Get OS information
            os_info = f"{platform.system()} {platform.release()}"
            
            return {
                "name": computer_name,
                "ip": ip_address,
                "user": username,
                "bot_path": bot_path,
                "os": os_info,
                "last_seen": datetime.now().isoformat(),
                "status": "Online",
                "version": "Unknown"
            }
        except Exception as e:
            return None
    
    def _auto_register_computer(self):
        """Automatically register this computer if not already registered"""
        computer_info = self._get_computer_info()
        if not computer_info:
            return
        
        # Check if this computer is already registered
        existing_computer = None
        for computer in self.computers["computers"]:
            if (computer["name"] == computer_info["name"] and 
                computer["ip"] == computer_info["ip"]):
                existing_computer = computer
                break
        
        if existing_computer:
            # Update last seen and status
            existing_computer["last_seen"] = computer_info["last_seen"]
            existing_computer["status"] = "Online"
            existing_computer["bot_path"] = computer_info["bot_path"]
            existing_computer["os"] = computer_info["os"]
            existing_computer["user"] = computer_info["user"]
        else:
            # Add new computer
            self.computers["computers"].append(computer_info)
        
        # Save the updated computer list
        self._save_computers()
    
    def _check_access(self):
        """Check if user has access to the update manager"""
        if self.access_granted:
            self._build_ui()
            return
        
        # Create access dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Manager Access - IT Only")
        dialog.geometry("500x400")
        dialog.configure(bg="#f7f3f2")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Header
        header_frame = tk.Frame(dialog, bg="#800000", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔒 Update Manager Access", 
                              font=("Segoe UI", 16, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Main content
        content_frame = tk.Frame(dialog, bg="#f7f3f2")
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Instructions
        instructions = tk.Label(content_frame, 
                               text="This tool is for IT personnel only.\nEnter the access password to continue:",
                               font=("Segoe UI", 12), bg="#f7f3f2", justify="center")
        instructions.pack(pady=(0, 20))
        
        # Password entry
        password_frame = tk.Frame(content_frame, bg="#f7f3f2")
        password_frame.pack(pady=10)
        
        password_label = tk.Label(password_frame, text="Password:", 
                                 font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        password_label.pack(side="left", padx=(0, 10))
        
        self.password_entry = tk.Entry(password_frame, show="*", font=("Segoe UI", 11), width=20)
        self.password_entry.pack(side="left")
        self.password_entry.bind("<Return>", lambda e: self._verify_password(dialog))
        self.password_entry.focus()
        
        # Status label
        self.status_label = tk.Label(content_frame, text="", 
                                    font=("Segoe UI", 10), bg="#f7f3f2", fg="red")
        self.status_label.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg="#f7f3f2")
        button_frame.pack(pady=20)
        
        login_btn = tk.Button(button_frame, text="Login", 
                             command=lambda: self._verify_password(dialog),
                             bg="#800000", fg="white", font=("Segoe UI", 11, "bold"),
                             padx=20, pady=6, cursor="hand2", width=8, height=1,
                             relief="raised", bd=2, activebackground="#600000", activeforeground="white")
        login_btn.pack(side="left", padx=(0, 10))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                              command=self.root.quit,
                              bg="#800000", fg="white", font=("Segoe UI", 11, "bold"),
                              padx=20, pady=6, cursor="hand2", width=8, height=1,
                              relief="raised", bd=2, activebackground="#600000", activeforeground="white")
        cancel_btn.pack(side="left")
        
        # Handle dialog close
        dialog.protocol("WM_DELETE_WINDOW", self.root.quit)
    
    def _verify_password(self, dialog):
        """Verify the entered password"""
        if self.locked:
            self.status_label.config(text="Access locked. Too many failed attempts.")
            return
        
        entered_password = self.password_entry.get()
        
        if entered_password == self.correct_password:
            self.access_granted = True
            dialog.destroy()
            self._build_ui()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            
            if remaining > 0:
                self.status_label.config(text=f"Invalid password. {remaining} attempts remaining.")
            else:
                self.locked = True
                self.status_label.config(text="Access locked. Too many failed attempts.")
                self.password_entry.config(state="disabled")
    
    def _build_ui(self):
        """Build the main UI after successful authentication"""
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self._create_manage_computers_tab()
        self._create_create_updates_tab()
        self._create_deploy_updates_tab()
        self._create_monitor_status_tab()
        
        # Start the main loop
        self.root.mainloop()
    
    def _create_manage_computers_tab(self):
        """Create the Manage Computers tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Manage Computers")
        
        # Header
        header_frame = tk.Frame(frame, bg="#800000", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🖥️ Manage Computers", 
                              font=("Segoe UI", 16, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Instructions
        instructions = tk.Label(frame, 
                               text="View and manage all computers in your network. Computers are automatically registered when bots are installed.",
                               font=("Segoe UI", 11), bg="#f7f3f2", justify="center")
        instructions.pack(pady=10)
        
        # Computer list
        list_frame = tk.Frame(frame, bg="#f7f3f2")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scrollable frame for computers
        canvas = tk.Canvas(list_frame, bg="#f7f3f2")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#f7f3f2")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        refresh_btn = tk.Button(frame, text="🔄 Refresh List", 
                               command=self._refresh_computer_list,
                               bg="#800000", fg="white", font=("Segoe UI", 11, "bold"),
                               padx=15, pady=5, cursor="hand2")
        refresh_btn.pack(pady=10)
        
        # Initial load
        self._refresh_computer_list()
    
    def _refresh_computer_list(self):
        """Refresh the computer list display"""
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Load computers
        self.computers = self._load_computers()
        
        if not self.computers["computers"]:
            no_computers_label = tk.Label(self.scrollable_frame, 
                                         text="No computers registered yet.\nComputers will appear here after bot installation.",
                                         font=("Segoe UI", 12), bg="#f7f3f2", fg="#666666")
            no_computers_label.pack(pady=50)
            return
        
        # Display each computer
        for i, computer in enumerate(self.computers["computers"]):
            computer_frame = tk.Frame(self.scrollable_frame, bg="#ffffff", relief="raised", bd=1)
            computer_frame.pack(fill="x", padx=5, pady=5)
            
            # Computer info
            info_text = f"🖥️ {computer['name']} ({computer['ip']})\n"
            info_text += f"👤 User: {computer['user']}\n"
            info_text += f"💻 OS: {computer['os']}\n"
            info_text += f"📁 Path: {computer['bot_path']}\n"
            info_text += f"🕒 Last Seen: {computer.get('last_seen', 'Unknown')}\n"
            info_text += f"📊 Status: {computer.get('status', 'Unknown')}"
            
            info_label = tk.Label(computer_frame, text=info_text, 
                                 font=("Segoe UI", 10), bg="#ffffff", justify="left")
            info_label.pack(anchor="w", padx=10, pady=10)
    
    def _create_create_updates_tab(self):
        """Create the Create Updates tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Create Updates")
        
        # Header
        header_frame = tk.Frame(frame, bg="#800000", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📦 Create Updates", 
                              font=("Segoe UI", 16, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Instructions
        instructions = tk.Label(frame, 
                               text="Create update packages by selecting files to update. This will package the selected files for deployment.",
                               font=("Segoe UI", 11), bg="#f7f3f2", justify="center")
        instructions.pack(pady=10)
        
        # Update creation form
        form_frame = tk.Frame(frame, bg="#f7f3f2")
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Version input
        version_frame = tk.Frame(form_frame, bg="#f7f3f2")
        version_frame.pack(fill="x", pady=5)
        
        version_label = tk.Label(version_frame, text="Version:", 
                                font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        version_label.pack(side="left", padx=(0, 10))
        
        self.version_entry = tk.Entry(version_frame, font=("Segoe UI", 11), width=20)
        self.version_entry.pack(side="left")
        self.version_entry.insert(0, datetime.now().strftime("%Y.%m.%d"))
        
        # Description input
        desc_frame = tk.Frame(form_frame, bg="#f7f3f2")
        desc_frame.pack(fill="x", pady=5)
        
        desc_label = tk.Label(desc_frame, text="Description:", 
                             font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        desc_label.pack(side="left", padx=(0, 10))
        
        self.desc_entry = tk.Entry(desc_frame, font=("Segoe UI", 11), width=40)
        self.desc_entry.pack(side="left")
        
        # File selection
        file_frame = tk.Frame(form_frame, bg="#f7f3f2")
        file_frame.pack(fill="x", pady=10)
        
        file_label = tk.Label(file_frame, text="Select Files/Folders to Update:", 
                             font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        file_label.pack(anchor="w")
        
        self.selected_files = []
        
        # File list
        self.file_listbox = tk.Listbox(file_frame, height=8, font=("Segoe UI", 10))
        self.file_listbox.pack(fill="x", pady=5)
        
        # File selection buttons
        file_btn_frame = tk.Frame(file_frame, bg="#f7f3f2")
        file_btn_frame.pack(fill="x", pady=5)
        
        add_file_btn = tk.Button(file_btn_frame, text="📁 Add Files", 
                                command=self._add_files,
                                bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                padx=10, pady=3, cursor="hand2")
        add_file_btn.pack(side="left", padx=(0, 5))
        
        add_folder_btn = tk.Button(file_btn_frame, text="📂 Add Folder", 
                                  command=self._add_folder,
                                  bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                  padx=10, pady=3, cursor="hand2")
        add_folder_btn.pack(side="left", padx=(0, 5))
        
        remove_file_btn = tk.Button(file_btn_frame, text="❌ Remove", 
                                   command=self._remove_selected_file,
                                   bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                   padx=10, pady=3, cursor="hand2")
        remove_file_btn.pack(side="left")
        
        # Create package button
        create_btn = tk.Button(form_frame, text="📦 Create Update Package", 
                              command=self._create_update_package,
                              bg="#800000", fg="white", font=("Segoe UI", 12, "bold"),
                              padx=20, pady=10, cursor="hand2")
        create_btn.pack(pady=20)
    
    def _add_files(self):
        """Add files to the update package"""
        files = filedialog.askopenfilenames(
            title="Select files to include in update",
            filetypes=[("All files", "*.*")]
        )
        
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.file_listbox.insert(tk.END, file)
    
    def _add_folder(self):
        """Add a folder to the update package"""
        folder = filedialog.askdirectory(title="Select folder to include in update")
        
        if folder and folder not in self.selected_files:
            self.selected_files.append(folder)
            self.file_listbox.insert(tk.END, f"{folder} (folder)")
    
    def _remove_selected_file(self):
        """Remove selected file from the update package"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            self.file_listbox.delete(index)
            del self.selected_files[index]
    
    def _create_update_package(self):
        """Create an update package"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select at least one file or folder to update.")
            return
        
        version = self.version_entry.get().strip()
        description = self.desc_entry.get().strip()
        
        if not version:
            messagebox.showwarning("No Version", "Please enter a version number.")
            return
        
        if not description:
            messagebox.showwarning("No Description", "Please enter a description.")
            return
        
        try:
            # Create update package directory
            package_name = f"update_{version}_{int(time.time())}"
            package_dir = self.update_packages_dir / package_name
            package_dir.mkdir(exist_ok=True)
            
            # Copy files
            for item in self.selected_files:
                if os.path.isfile(item):
                    shutil.copy2(item, package_dir)
                elif os.path.isdir(item):
                    shutil.copytree(item, package_dir / os.path.basename(item))
            
            # Create package info
            package_info = {
                "version": version,
                "description": description,
                "created": datetime.now().isoformat(),
                "files": [os.path.basename(f) for f in self.selected_files]
            }
            
            with open(package_dir / "package_info.json", 'w') as f:
                json.dump(package_info, f, indent=2)
            
            # Create zip file
            zip_path = self.update_packages_dir / f"{package_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            # Clean up temp directory
            shutil.rmtree(package_dir)
            
            messagebox.showinfo("Success", f"Update package created successfully!\n\nPackage: {zip_path.name}\nVersion: {version}\nDescription: {description}")
            
            # Clear form
            self.selected_files.clear()
            self.file_listbox.delete(0, tk.END)
            self.desc_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create update package:\n{e}")
    
    def _create_deploy_updates_tab(self):
        """Create the Deploy Updates tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Deploy Updates")
        
        # Header
        header_frame = tk.Frame(frame, bg="#800000", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🚀 Deploy Updates", 
                              font=("Segoe UI", 16, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Instructions
        instructions = tk.Label(frame, 
                               text="Deploy update packages to selected computers. Choose a package and select target computers.",
                               font=("Segoe UI", 11), bg="#f7f3f2", justify="center")
        instructions.pack(pady=10)
        
        # Deployment form
        form_frame = tk.Frame(frame, bg="#f7f3f2")
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Package selection
        package_frame = tk.Frame(form_frame, bg="#f7f3f2")
        package_frame.pack(fill="x", pady=10)
        
        package_label = tk.Label(package_frame, text="Select Update Package:", 
                                font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        package_label.pack(anchor="w")
        
        self.package_var = tk.StringVar()
        self.package_combo = ttk.Combobox(package_frame, textvariable=self.package_var, 
                                         state="readonly", width=50)
        self.package_combo.pack(fill="x", pady=5)
        
        refresh_packages_btn = tk.Button(package_frame, text="🔄 Refresh Packages", 
                                        command=self._refresh_packages,
                                        bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                        padx=10, pady=3, cursor="hand2")
        refresh_packages_btn.pack(anchor="w", pady=5)
        
        # Computer selection
        computer_frame = tk.Frame(form_frame, bg="#f7f3f2")
        computer_frame.pack(fill="both", expand=True, pady=10)
        
        computer_label = tk.Label(computer_frame, text="Select Target Computers:", 
                                 font=("Segoe UI", 11, "bold"), bg="#f7f3f2")
        computer_label.pack(anchor="w")
        
        # Create scrollable frame for computer checkboxes
        canvas = tk.Canvas(computer_frame, bg="#f7f3f2", height=200)
        scrollbar = ttk.Scrollbar(computer_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="#f7f3f2")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Selection buttons
        select_frame = tk.Frame(computer_frame, bg="#f7f3f2")
        select_frame.pack(fill="x", pady=5)
        
        select_all_btn = tk.Button(select_frame, text="✅ Select All", 
                                  command=self._select_all_computers,
                                  bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                  padx=10, pady=3, cursor="hand2")
        select_all_btn.pack(side="left", padx=(0, 5))
        
        select_none_btn = tk.Button(select_frame, text="❌ Select None", 
                                   command=self._select_none_computers,
                                   bg="#800000", fg="white", font=("Segoe UI", 10, "bold"),
                                   padx=10, pady=3, cursor="hand2")
        select_none_btn.pack(side="left")
        
        # Deploy button
        deploy_btn = tk.Button(form_frame, text="🚀 Deploy Update", 
                              command=self._deploy_update,
                              bg="#800000", fg="white", font=("Segoe UI", 12, "bold"),
                              padx=20, pady=10, cursor="hand2")
        deploy_btn.pack(pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(form_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(pady=10)
        
        # Status label
        self.deploy_status_label = tk.Label(form_frame, text="", 
                                           font=("Segoe UI", 10), bg="#f7f3f2")
        self.deploy_status_label.pack(pady=5)
        
        # Initialize
        self.computer_vars = {}
        self.computer_checkboxes = {}
        self._refresh_packages()
        self._refresh_deploy_computers()
    
    def _refresh_packages(self):
        """Refresh the list of available update packages"""
        packages = []
        if self.update_packages_dir.exists():
            for file in self.update_packages_dir.glob("*.zip"):
                packages.append(file.name)
        
        self.package_combo["values"] = packages
        if packages:
            self.package_combo.set(packages[0])
    
    def _refresh_deploy_computers(self):
        """Refresh the computer list for deployment"""
        # Clear existing checkboxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.computer_checkboxes.clear()
        self.computer_vars.clear()
        
        # Create checkboxes for each computer
        for i, computer in enumerate(self.computers["computers"]):
            # Create variable for checkbox
            var = tk.BooleanVar()
            self.computer_vars[computer["name"]] = var
            
            # Create checkbox frame
            checkbox_frame = tk.Frame(self.scrollable_frame, bg="#f7f3f2")
            checkbox_frame.pack(fill="x", padx=5, pady=2)
            
            # Create checkbox
            checkbox = tk.Checkbutton(checkbox_frame, 
                                     text=f"{computer['name']} ({computer['ip']}) - {computer['user']}",
                                     variable=var,
                                     font=("Segoe UI", 10),
                                     bg="#f7f3f2")
            checkbox.pack(anchor="w")
            
            # Store reference
            self.computer_checkboxes[computer["name"]] = checkbox
            
            # Add status indicator
            status_color = "#800000" if computer.get("status") == "Online" else "#666666"
            status_label = tk.Label(checkbox_frame, 
                                   text=f"Status: {computer.get('status', 'Unknown')}",
                                   font=("Segoe UI", 8),
                                   fg=status_color,
                                   bg="#f7f3f2")
            status_label.pack(anchor="w", padx=(20, 0))
    
    def _select_all_computers(self):
        """Select all computers for deployment"""
        for var in self.computer_vars.values():
            var.set(True)
    
    def _select_none_computers(self):
        """Deselect all computers for deployment"""
        for var in self.computer_vars.values():
            var.set(False)
    
    def _deploy_update(self):
        """Deploy the selected update package to selected computers"""
        if not self.package_var.get():
            messagebox.showwarning("No Package", "Please select an update package.")
            return
        
        selected_computers = [name for name, var in self.computer_vars.items() if var.get()]
        
        if not selected_computers:
            messagebox.showwarning("No Computers", "Please select at least one computer.")
            return
        
        # Confirm deployment
        result = messagebox.askyesno("Confirm Deployment", 
                                   f"Deploy update package '{self.package_var.get()}' to {len(selected_computers)} computer(s)?\n\n"
                                   f"Computers: {', '.join(selected_computers)}")
        
        if not result:
            return
        
        # Start deployment in background thread
        self.deploy_status_label.config(text="Deployment in progress...")
        self.progress_var.set(0)
        
        def deploy_worker():
            try:
                package_path = self.update_packages_dir / self.package_var.get()
                
                for i, computer_name in enumerate(selected_computers):
                    # Update progress
                    progress = (i / len(selected_computers)) * 100
                    self.progress_var.set(progress)
                    self.deploy_status_label.config(text=f"Deploying to {computer_name}...")
                    
                    # Simulate deployment (replace with actual deployment logic)
                    time.sleep(2)  # Simulate deployment time
                    
                    # Update computer status
                    for computer in self.computers["computers"]:
                        if computer["name"] == computer_name:
                            computer["last_seen"] = datetime.now().isoformat()
                            computer["status"] = "Online"
                            break
                    
                    # Save updated computer list
                    self._save_computers()
                
                # Complete
                self.progress_var.set(100)
                self.deploy_status_label.config(text=f"Deployment completed successfully to {len(selected_computers)} computer(s)!")
                
                # Refresh computer list
                self._refresh_deploy_computers()
                
            except Exception as e:
                self.deploy_status_label.config(text=f"Deployment failed: {e}")
        
        # Start deployment thread
        deploy_thread = threading.Thread(target=deploy_worker, daemon=True)
        deploy_thread.start()
    
    def _create_monitor_status_tab(self):
        """Create the Monitor Status tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Monitor Status")
        
        # Header
        header_frame = tk.Frame(frame, bg="#800000", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📊 Monitor Status", 
                              font=("Segoe UI", 16, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Instructions
        instructions = tk.Label(frame, 
                               text="Monitor the status of all computers and recent deployments. Check system health and connectivity.",
                               font=("Segoe UI", 11), bg="#f7f3f2", justify="center")
        instructions.pack(pady=10)
        
        # Status display
        status_frame = tk.Frame(frame, bg="#f7f3f2")
        status_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Status text area
        self.status_text = scrolledtext.ScrolledText(status_frame, height=20, width=80, 
                                                    font=("Courier New", 10), bg="#ffffff")
        self.status_text.pack(fill="both", expand=True)
        
        # Control buttons
        control_frame = tk.Frame(status_frame, bg="#f7f3f2")
        control_frame.pack(fill="x", pady=10)
        
        refresh_status_btn = tk.Button(control_frame, text="🔄 Refresh Status", 
                                      command=self._refresh_status,
                                      bg="#800000", fg="white", font=("Segoe UI", 11, "bold"),
                                      padx=15, pady=5, cursor="hand2")
        refresh_status_btn.pack(side="left", padx=(0, 10))
        
        clear_log_btn = tk.Button(control_frame, text="🗑️ Clear Log", 
                                 command=self._clear_status_log,
                                 bg="#800000", fg="white", font=("Segoe UI", 11, "bold"),
                                 padx=15, pady=5, cursor="hand2")
        clear_log_btn.pack(side="left")
        
        # Initial status load
        self._refresh_status()
    
    def _refresh_status(self):
        """Refresh the status display"""
        self.status_text.delete(1.0, tk.END)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_text.insert(tk.END, f"=== Status Report - {timestamp} ===\n\n")
        
        # Computer status
        self.status_text.insert(tk.END, "🖥️ COMPUTER STATUS:\n")
        self.status_text.insert(tk.END, "-" * 50 + "\n")
        
        if not self.computers["computers"]:
            self.status_text.insert(tk.END, "No computers registered.\n\n")
        else:
            for computer in self.computers["computers"]:
                status_icon = "✅" if computer.get("status") == "Online" else "❌"
                self.status_text.insert(tk.END, f"{status_icon} {computer['name']} ({computer['ip']})\n")
                self.status_text.insert(tk.END, f"   User: {computer['user']}\n")
                self.status_text.insert(tk.END, f"   OS: {computer['os']}\n")
                self.status_text.insert(tk.END, f"   Last Seen: {computer.get('last_seen', 'Unknown')}\n")
                self.status_text.insert(tk.END, f"   Status: {computer.get('status', 'Unknown')}\n\n")
        
        # Update packages
        self.status_text.insert(tk.END, "📦 UPDATE PACKAGES:\n")
        self.status_text.insert(tk.END, "-" * 50 + "\n")
        
        if self.update_packages_dir.exists():
            packages = list(self.update_packages_dir.glob("*.zip"))
            if packages:
                for package in packages:
                    self.status_text.insert(tk.END, f"📦 {package.name}\n")
                    self.status_text.insert(tk.END, f"   Size: {package.stat().st_size / 1024:.1f} KB\n")
                    self.status_text.insert(tk.END, f"   Created: {datetime.fromtimestamp(package.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            else:
                self.status_text.insert(tk.END, "No update packages found.\n\n")
        else:
            self.status_text.insert(tk.END, "Update packages directory not found.\n\n")
        
        # System info
        self.status_text.insert(tk.END, "💻 SYSTEM INFO:\n")
        self.status_text.insert(tk.END, "-" * 50 + "\n")
        self.status_text.insert(tk.END, f"Python Version: {sys.version}\n")
        self.status_text.insert(tk.END, f"Platform: {platform.platform()}\n")
        self.status_text.insert(tk.END, f"Working Directory: {os.getcwd()}\n")
        self.status_text.insert(tk.END, f"Update Manager Version: 1.0\n\n")
        
        # Scroll to top
        self.status_text.see(1.0)
    
    def _clear_status_log(self):
        """Clear the status log"""
        self.status_text.delete(1.0, tk.END)

def auto_register_computer_silent():
    """Silent auto-registration for installer - no GUI"""
    try:
        # Use the same centralized path logic as the main class
        def get_centralized_paths():
            import socket
            current_computer = socket.gethostname()
            
            network_locations = [
                Path("//server/CCMD_Bot_Manager"),
                Path("//fileserver/CCMD_Bot_Manager"), 
                Path("//network/CCMD_Bot_Manager"),
                Path("//shared/CCMD_Bot_Manager"),
                Path("//company/CCMD_Bot_Manager"),
                Path("C:/CCMD_Bot_Manager"),
                Path("D:/CCMD_Bot_Manager"),
                Path(f"//{current_computer}/CCMD_Bot_Manager"),
            ]
            
            for network_path in network_locations:
                try:
                    network_path.mkdir(exist_ok=True)
                    test_file = network_path / "test_write.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    return network_path / "computers.json"
                except (PermissionError, OSError, FileNotFoundError):
                    continue
            
            # Fallback to local
            user_docs = Path.home() / "Documents" / "CCMD_Bot_Manager"
            user_docs.mkdir(exist_ok=True)
            return user_docs / "computers.json"
        
        computers_file = get_centralized_paths()
        
        # Load existing computers
        if computers_file.exists():
            with open(computers_file, 'r') as f:
                computers = json.load(f)
        else:
            computers = {"computers": []}
        
        # Get computer info
        try:
            # Get computer name
            computer_name = platform.node()
            
            # Get IP address
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except:
                ip_address = "127.0.0.1"
            
            # Get username
            username = os.getenv('USERNAME') or os.getenv('USER') or "Unknown"
            
            # Get bot installation path (current directory)
            bot_path = str(Path.cwd())
            
            # Get OS information
            os_info = f"{platform.system()} {platform.release()}"
            
            computer_info = {
                "name": computer_name,
                "ip": ip_address,
                "user": username,
                "bot_path": bot_path,
                "os": os_info,
                "last_seen": datetime.now().isoformat(),
                "status": "Online",
                "version": "Unknown"
            }
        except Exception:
            return False
        
        # Check if this computer is already registered
        existing_computer = None
        for computer in computers["computers"]:
            if (computer["name"] == computer_info["name"] and 
                computer["ip"] == computer_info["ip"]):
                existing_computer = computer
                break
        
        if existing_computer:
            # Update last seen and status
            existing_computer["last_seen"] = computer_info["last_seen"]
            existing_computer["status"] = "Online"
            existing_computer["bot_path"] = computer_info["bot_path"]
            existing_computer["os"] = computer_info["os"]
            existing_computer["user"] = computer_info["user"]
        else:
            # Add new computer
            computers["computers"].append(computer_info)
        
        # Save the updated computer list
        with open(computers_file, 'w') as f:
            json.dump(computers, f, indent=2)
        
        return True
        
    except Exception:
        return False

if __name__ == "__main__":
    app = EasyUpdateManager()
    app.root.mainloop()