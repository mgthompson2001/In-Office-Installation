"""
Centralized Update Bot
This bot lives in G:/Company/Software/Updates
Employees run this to update all their bots.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import json
import shutil
import sys
from datetime import datetime
import os

# Import update_manager from same directory
sys.path.insert(0, str(Path(__file__).parent))
from update_manager import UpdateManager

class UpdateBotGUI:
    """GUI for the centralized update bot"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Software Update Manager")
        self.root.geometry("800x700")
        self.root.configure(bg="#f0f0f0")
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
        # Update source (G-Drive Updates folder root)
        self.update_source_root = Path(r"G:\Company\Software\Updates")
        # Version folder will be determined dynamically (e.g., "1.1/")
        self.update_source = None
        
        # Employee's installation folder (to be selected)
        self.installation_folder = None
        
        # Available bots
        self.available_bots = []
        
        self.create_ui()
        self.scan_for_updates()
    
    def create_ui(self):
        """Create the user interface"""
        # Header
        header_frame = tk.Frame(self.root, bg="#800000", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="Software Update Manager", 
                              font=("Arial", 20, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True, pady=(10, 0))
        
        subtitle_label = tk.Label(header_frame, text="Update all your bots to the latest version", 
                                 font=("Arial", 10), bg="#800000", fg="#cccccc")
        subtitle_label.pack()
        
        # Main content
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Installation folder selection
        folder_frame = tk.LabelFrame(main_frame, text="1. Select Your Installation Folder", 
                                    font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        folder_frame.pack(fill="x", pady=(0, 15))
        
        folder_content = tk.Frame(folder_frame, bg="#f0f0f0")
        folder_content.pack(fill="x", padx=15, pady=15)
        
        tk.Label(folder_content, text="In-Office Installation folder:", 
                font=("Arial", 10), bg="#f0f0f0").pack(anchor="w", pady=(0, 5))
        
        folder_row = tk.Frame(folder_content, bg="#f0f0f0")
        folder_row.pack(fill="x")
        
        self.folder_entry = tk.Entry(folder_row, font=("Arial", 9), width=60)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Try to auto-detect
        default_path = Path(r"C:\Users") / os.environ.get('USERNAME', '') / "OneDrive - Integrity Senior Services" / "Desktop" / "In-Office Installation"
        if default_path.exists():
            self.folder_entry.insert(0, str(default_path))
            self.installation_folder = default_path
        
        browse_button = tk.Button(folder_row, text="Browse...", 
                                 command=self.browse_folder,
                                 bg="#800020", fg="white", font=("Arial", 9),
                                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0)
        browse_button.pack(side="left")
        
        # Available updates section
        updates_frame = tk.LabelFrame(main_frame, text="2. Available Updates", 
                                     font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        updates_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        updates_content = tk.Frame(updates_frame, bg="#f0f0f0")
        updates_content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Treeview for bots
        tree_frame = tk.Frame(updates_content, bg="#f0f0f0")
        tree_frame.pack(fill="both", expand=True)
        
        # Create treeview with scrollbar
        tree_scroll = tk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")
        
        self.bot_tree = ttk.Treeview(tree_frame, columns=("Status", "Current", "Available"), 
                                     show="tree headings", height=12, yscrollcommand=tree_scroll.set)
        tree_scroll.config(command=self.bot_tree.yview)
        
        self.bot_tree.heading("#0", text="Bot Name")
        self.bot_tree.heading("Status", text="Status")
        self.bot_tree.heading("Current", text="Current Version")
        self.bot_tree.heading("Available", text="Available Version")
        
        self.bot_tree.column("#0", width=300)
        self.bot_tree.column("Status", width=150)
        self.bot_tree.column("Current", width=120)
        self.bot_tree.column("Available", width=120)
        
        self.bot_tree.pack(fill="both", expand=True)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")
        
        refresh_button = tk.Button(button_frame, text="Refresh", 
                                  command=self.scan_for_updates,
                                  bg="#6c757d", fg="white", font=("Arial", 10),
                                  padx=20, pady=8, cursor="hand2", relief="flat", bd=0)
        refresh_button.pack(side="left", padx=(0, 10))
        
        self.update_button = tk.Button(button_frame, text="Update Selected Bot", 
                                      command=self.update_selected_bot,
                                      bg="#28a745", fg="white", font=("Arial", 10, "bold"),
                                      padx=20, pady=8, cursor="hand2", relief="flat", bd=0,
                                      state="disabled")
        self.update_button.pack(side="left", padx=(0, 10))
        
        update_all_button = tk.Button(button_frame, text="Update All Bots", 
                                     command=self.update_all_bots,
                                     bg="#007bff", fg="white", font=("Arial", 10, "bold"),
                                     padx=20, pady=8, cursor="hand2", relief="flat", bd=0)
        update_all_button.pack(side="left")
        
        # Status/log area
        log_frame = tk.LabelFrame(main_frame, text="Update Log", 
                                 font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#800000")
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9),
                                                  bg="#ffffff", wrap=tk.WORD)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_text.config(state="disabled")
    
    def log(self, message):
        """Add message to log"""
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        self.root.update()
    
    def browse_folder(self):
        """Browse for installation folder"""
        folder = filedialog.askdirectory(
            title="Select In-Office Installation Folder",
            initialdir=str(Path.home() / "Desktop")
        )
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.installation_folder = Path(folder)
            self.scan_for_updates()
    
    def scan_for_updates(self):
        """Scan for available updates"""
        # Clear tree
        for item in self.bot_tree.get_children():
            self.bot_tree.delete(item)
        
        self.available_bots = []
        
        if not self.installation_folder:
            self.log("⚠️ Please select your installation folder first")
            return
        
        if not self.update_source_root.exists():
            self.log(f"❌ Update source not found: {self.update_source_root}")
            self.log("   Make sure G-Drive is accessible")
            return
        
        # Find the latest version folder (e.g., "1.1/", "1.2/", etc.)
        version_folders = []
        for item in self.update_source_root.iterdir():
            if item.is_dir():
                # Check if it looks like a version folder (e.g., "1.1", "1.0.0", "2.3.4")
                import re
                if re.match(r'^\d+\.\d+(\.\d+)?$', item.name):
                    version_folders.append(item)
        
        if not version_folders:
            self.log("❌ No version folders found in Updates directory")
            self.log("   Please push an update first using PUSH_UPDATE.bat")
            return
        
        # Use the latest version folder (sort by version number)
        def version_key(v):
            parts = v.name.split('.')
            return tuple(int(p) for p in parts)
        
        latest_version_folder = max(version_folders, key=version_key)
        self.update_source = latest_version_folder
        self.log(f"📦 Using version folder: {latest_version_folder.name}")
        
        self.log("🔍 Scanning for available updates...")
        
        # Try to load config.json from root to get user_data_files for each bot
        config_file = self.update_source_root / "config.json"
        bot_configs = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    for bot_config in config.get('bots', []):
                        bot_configs[bot_config.get('name')] = bot_config
            except:
                pass
        
        # Find all bot folders in version folder
        for bot_folder in self.update_source.iterdir():
            if not bot_folder.is_dir():
                continue
            
            bot_name = bot_folder.name.replace("_", " ")
            version_file = bot_folder / "version.json"
            
            if not version_file.exists():
                continue
            
            try:
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                
                available_version = version_data.get('version', 'Unknown')
                
                # Find corresponding bot in installation folder
                bot_path = self.find_bot_in_installation(bot_name, bot_folder.name)
                current_version = "Not found"
                status = "Not installed"
                
                if bot_path:
                    local_version_file = bot_path / "version.json"
                    if local_version_file.exists():
                        try:
                            with open(local_version_file, 'r') as f:
                                local_data = json.load(f)
                            current_version = local_data.get('version', 'Unknown')
                            
                            if current_version != available_version:
                                status = "Update available"
                            else:
                                status = "Up to date"
                        except:
                            status = "Update available"
                    else:
                        status = "Update available"
                
                # Add to tree
                item = self.bot_tree.insert("", tk.END, text=bot_name,
                                           values=(status, current_version, available_version))
                
                # Try to get user_data_files from config.json in G-Drive Updates folder
                user_data_files = ["*.json", "*.log", "*.png"]  # Default
                try:
                    config_file = self.update_source.parent / "config.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                            for bot_config in config.get('bots', []):
                                if bot_config.get('name') == bot_name:
                                    user_data_files = bot_config.get('user_data_files', user_data_files)
                                    break
                except:
                    pass
                
                self.available_bots.append({
                    'name': bot_name,
                    'folder_name': bot_folder.name,
                    'update_path': bot_folder,
                    'local_path': bot_path,
                    'current_version': current_version,
                    'available_version': available_version,
                    'status': status,
                    'tree_item': item,
                    'user_data_files': user_data_files
                })
                
            except Exception as e:
                self.log(f"⚠️ Error reading {bot_name}: {e}")
        
        self.log(f"✅ Found {len(self.available_bots)} bots")
        self.update_button.config(state="normal" if self.available_bots else "disabled")
    
    def find_bot_in_installation(self, bot_name, folder_name):
        """Find bot folder in installation directory"""
        # Search in _bots folder
        bots_folder = self.installation_folder / "_bots"
        if not bots_folder.exists():
            return None
        
        # Try exact folder name match first
        for root, dirs, files in os.walk(bots_folder):
            for dir_name in dirs:
                if dir_name == folder_name.replace("_", " "):
                    return Path(root) / dir_name
        
        # Try name matching
        for root, dirs, files in os.walk(bots_folder):
            for dir_name in dirs:
                if bot_name.lower() in dir_name.lower() or dir_name.lower() in bot_name.lower():
                    return Path(root) / dir_name
        
        return None
    
    def update_selected_bot(self):
        """Update the selected bot"""
        selection = self.bot_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a bot to update")
            return
        
        item = selection[0]
        bot_info = None
        for bot in self.available_bots:
            if bot['tree_item'] == item:
                bot_info = bot
                break
        
        if not bot_info:
            return
        
        if bot_info['status'] == "Up to date":
            messagebox.showinfo("Already Updated", f"{bot_info['name']} is already up to date!")
            return
        
        if not bot_info['local_path']:
            messagebox.showerror("Not Found", f"Could not find {bot_info['name']} in your installation folder")
            return
        
        self.update_bot(bot_info)
    
    def update_bot(self, bot_info):
        """Update a single bot"""
        bot_name = bot_info['name']
        update_path = bot_info['update_path']
        local_path = bot_info['local_path']
        
        self.log(f"📦 Updating {bot_name}...")
        
        try:
            # Get user data files from bot_info (preserve employee's saved data)
            # This includes saved logins, credentials, settings, coordinates, etc.
            user_data_files = bot_info.get('user_data_files', ["*.json", "*.log", "*.png"])
            
            self.log(f"   🔒 Preserving user data: {', '.join(user_data_files)}")
            
            # Create update manager
            manager = UpdateManager(
                bot_name=bot_name,
                current_version=bot_info['current_version'],
                update_source=str(update_path),
                bot_directory=local_path,
                user_data_files=user_data_files  # Preserve user data (logins, settings, etc.)
            )
            
            # Check for updates
            update_info = manager.check_for_updates()
            
            if not update_info:
                self.log(f"⚠️ No update available for {bot_name}")
                return
            
            # Download and install
            result = manager.update(auto_install=True)
            
            if result['updated']:
                self.log(f"✅ Successfully updated {bot_name} to version {result['new_version']}")
                
                # Update timestamp in bot files
                self.update_timestamp_in_bot(local_path)
                
                messagebox.showinfo("Update Complete", 
                                  f"{bot_name} has been updated to version {result['new_version']}!")
            else:
                self.log(f"❌ Failed to update {bot_name}: {result.get('error', 'Unknown error')}")
                messagebox.showerror("Update Failed", 
                                   f"Failed to update {bot_name}:\n{result.get('error', 'Unknown error')}")
        
        except Exception as e:
            self.log(f"❌ Error updating {bot_name}: {e}")
            messagebox.showerror("Error", f"Error updating {bot_name}:\n{e}")
        
        # Refresh
        self.scan_for_updates()
    
    def update_all_bots(self):
        """Update all bots that have updates available"""
        bots_to_update = [bot for bot in self.available_bots if bot['status'] == "Update available"]
        
        if not bots_to_update:
            messagebox.showinfo("No Updates", "All bots are up to date!")
            return
        
        response = messagebox.askyesno(
            "Update All Bots",
            f"Update {len(bots_to_update)} bot(s)?\n\n"
            f"Your settings and data will be preserved."
        )
        
        if not response:
            return
        
        self.log(f"🔄 Updating {len(bots_to_update)} bot(s)...")
        
        success_count = 0
        for bot_info in bots_to_update:
            try:
                self.update_bot(bot_info)
                success_count += 1
            except Exception as e:
                self.log(f"❌ Failed to update {bot_info['name']}: {e}")
        
        self.log(f"✅ Updated {success_count}/{len(bots_to_update)} bot(s)")
        messagebox.showinfo("Update Complete", 
                          f"Updated {success_count} out of {len(bots_to_update)} bot(s)")
        
        # Refresh
        self.scan_for_updates()
    
    def update_timestamp_in_bot(self, bot_path):
        """Update timestamp in bot's Python files"""
        # Find main bot file
        for py_file in bot_path.glob("*bot*.py"):
            if py_file.is_file():
                try:
                    # Read file
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for header/title area and add/update timestamp
                    # This is a simple approach - we'll add it to the title or header
                    timestamp = datetime.now().strftime("%m/%d/%Y")
                    timestamp_text = f"Updated, {timestamp}"
                    
                    # Try to find and update existing timestamp
                    import re
                    pattern = r'Updated,?\s*\d{1,2}/\d{1,2}/\d{4}'
                    if re.search(pattern, content):
                        content = re.sub(pattern, timestamp_text, content)
                    else:
                        # Add timestamp near title/header
                        # Look for title patterns and add after them
                        title_patterns = [
                            r'(self\.root\.title\(["\'])([^"\']+)(["\'])',
                            r'(title\s*=\s*["\'])([^"\']+)(["\'])',
                        ]
                        
                        for pattern in title_patterns:
                            if re.search(pattern, content):
                                # Add timestamp to title
                                def add_timestamp(match):
                                    return f'{match.group(1)}{match.group(2)} - {timestamp_text}{match.group(3)}'
                                content = re.sub(pattern, add_timestamp, content)
                                break
                    
                    # Write back
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.log(f"   ✅ Updated timestamp in {py_file.name}")
                    break
                except Exception as e:
                    self.log(f"   ⚠️ Could not update timestamp in {py_file.name}: {e}")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = UpdateBotGUI()
    app.run()


if __name__ == "__main__":
    main()

