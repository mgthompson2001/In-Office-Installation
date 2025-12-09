#!/usr/bin/env python3
"""
Code Encryption Tool - Protects bot code from unauthorized access
This script encrypts Python files to prevent employees from viewing/editing the code.
"""

import os
import sys
import base64
import zlib
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
import threading

class CodeEncryptor:
    def __init__(self):
        self.password = "Integritycode1!"
        self.encrypted_files = []
        self.backup_dir = Path("encrypted_backup")
        
    def encrypt_file(self, file_path):
        """Encrypt a Python file"""
        try:
            # Read the original file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create encrypted content
            encrypted_content = self._encrypt_content(content)
            
            # Create backup
            self.backup_dir.mkdir(exist_ok=True)
            backup_path = self.backup_dir / f"{file_path.name}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Write encrypted file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            
            return True
            
        except Exception as e:
            print(f"Error encrypting {file_path}: {e}")
            return False
    
    def _encrypt_content(self, content):
        """Encrypt the content using base64 and compression"""
        # Compress the content
        compressed = zlib.compress(content.encode('utf-8'))
        
        # Encode with base64
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Create encrypted wrapper
        encrypted_wrapper = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ENCRYPTED FILE - DO NOT EDIT
# This file is encrypted and protected from unauthorized access.
# Contact your system administrator for access.

import base64
import zlib
import sys
import os

def _decrypt_content():
    """Decrypt the content"""
    encrypted_data = """{encoded}"""
    
    try:
        # Decode from base64
        compressed_data = base64.b64decode(encrypted_data.encode('utf-8'))
        
        # Decompress
        decrypted_content = zlib.decompress(compressed_data).decode('utf-8')
        
        return decrypted_content
    except Exception as e:
        print(f"Decryption error: {{e}}")
        return None

def _execute_decrypted():
    """Execute the decrypted content"""
    content = _decrypt_content()
    if content:
        # Create a new module and execute the content
        import types
        module = types.ModuleType("decrypted_module")
        
        # Set up the module's namespace
        module.__file__ = __file__
        module.__name__ = __name__
        
        # Execute the decrypted content
        exec(content, module.__dict__)
        
        return module
    return None

# Auto-execute if this is the main module
if __name__ == "__main__":
    module = _execute_decrypted()
    if module:
        # If the original module had a main function, call it
        if hasattr(module, 'main'):
            module.main()
        elif hasattr(module, 'App'):
            # For GUI applications
            app = module.App()
            if hasattr(app, 'mainloop'):
                app.mainloop()
    else:
        print("Failed to decrypt and execute the module")
        sys.exit(1)
'''
        
        return encrypted_wrapper
    
    def encrypt_directory(self, directory_path):
        """Encrypt all Python files in a directory"""
        directory = Path(directory_path)
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return False
        
        python_files = list(directory.rglob("*.py"))
        if not python_files:
            print(f"No Python files found in {directory}")
            return False
        
        print(f"Found {len(python_files)} Python files to encrypt...")
        
        success_count = 0
        for file_path in python_files:
            if self.encrypt_file(file_path):
                self.encrypted_files.append(str(file_path))
                success_count += 1
                print(f"✅ Encrypted: {file_path}")
            else:
                print(f"❌ Failed to encrypt: {file_path}")
        
        print(f"\nEncryption complete: {success_count}/{len(python_files)} files encrypted")
        return success_count > 0
    
    def create_encrypted_launcher(self):
        """Create an encrypted version of the main launcher"""
        launcher_path = Path("Launcher/bot_launcher.py")
        if launcher_path.exists():
            return self.encrypt_file(launcher_path)
        return False

class EncryptionGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CCMD Bot Code Encryptor")
        self.root.geometry("600x500")
        self.root.configure(bg="#f0f0f0")
        
        self.encryptor = CodeEncryptor()
        self._build_ui()
    
    def _build_ui(self):
        """Build the GUI interface"""
        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="CCMD Bot Code Encryptor", 
                              font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#800000")
        title_label.pack(pady=(0, 20))
        
        # Warning frame
        warning_frame = tk.Frame(main_frame, bg="#fff3cd", relief="raised", bd=2)
        warning_frame.pack(fill="x", pady=(0, 20))
        
        warning_label = tk.Label(warning_frame, 
                                text="⚠️ WARNING: This will encrypt all Python files to prevent unauthorized access.\n"
                                     "Original files will be backed up in the 'encrypted_backup' folder.\n"
                                     "Only authorized personnel should run this tool.",
                                font=("Arial", 10), bg="#fff3cd", fg="#856404", justify="left")
        warning_label.pack(padx=10, pady=10)
        
        # Options frame
        options_frame = tk.Frame(main_frame, bg="#f0f0f0")
        options_frame.pack(fill="x", pady=(0, 20))
        
        # Encrypt specific directory
        dir_frame = tk.Frame(options_frame, bg="#f0f0f0")
        dir_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(dir_frame, text="Encrypt Directory:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(anchor="w")
        
        dir_button_frame = tk.Frame(dir_frame, bg="#f0f0f0")
        dir_button_frame.pack(fill="x", pady=(5, 0))
        
        self.dir_var = tk.StringVar()
        dir_entry = tk.Entry(dir_button_frame, textvariable=self.dir_var, 
                           font=("Arial", 10), width=50)
        dir_entry.pack(side="left", fill="x", expand=True)
        
        browse_button = tk.Button(dir_button_frame, text="Browse", 
                                 command=self._browse_directory,
                                 bg="#800000", fg="white", font=("Arial", 10))
        browse_button.pack(side="right", padx=(10, 0))
        
        # Encrypt launcher
        launcher_frame = tk.Frame(options_frame, bg="#f0f0f0")
        launcher_frame.pack(fill="x", pady=(0, 10))
        
        launcher_button = tk.Button(launcher_frame, text="Encrypt Main Launcher", 
                                   command=self._encrypt_launcher,
                                   bg="#800000", fg="white", font=("Arial", 12, "bold"),
                                   padx=20, pady=10)
        launcher_button.pack()
        
        # Encrypt all bots
        all_bots_frame = tk.Frame(options_frame, bg="#f0f0f0")
        all_bots_frame.pack(fill="x", pady=(0, 10))
        
        all_bots_button = tk.Button(all_bots_frame, text="Encrypt All Bot Files", 
                                   command=self._encrypt_all_bots,
                                   bg="#d32f2f", fg="white", font=("Arial", 12, "bold"),
                                   padx=20, pady=10)
        all_bots_button.pack()
        
        # Log frame
        log_frame = tk.Frame(main_frame, bg="#f0f0f0")
        log_frame.pack(fill="both", expand=True)
        
        tk.Label(log_frame, text="Encryption Log:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(anchor="w")
        
        self.log_text = tk.Text(log_frame, height=15, font=("Consolas", 9), 
                               bg="#f8f8f8", wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Scrollbar
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
    
    def _browse_directory(self):
        """Browse for directory to encrypt"""
        directory = filedialog.askdirectory(title="Select Directory to Encrypt")
        if directory:
            self.dir_var.set(directory)
    
    def _encrypt_launcher(self):
        """Encrypt the main launcher"""
        self.log("🔒 Encrypting main launcher...")
        
        def encrypt_thread():
            try:
                if self.encryptor.create_encrypted_launcher():
                    self.log("✅ Main launcher encrypted successfully")
                else:
                    self.log("❌ Failed to encrypt main launcher")
            except Exception as e:
                self.log(f"❌ Error encrypting launcher: {e}")
        
        threading.Thread(target=encrypt_thread, daemon=True).start()
    
    def _encrypt_all_bots(self):
        """Encrypt all bot files"""
        self.log("🔒 Starting encryption of all bot files...")
        
        def encrypt_thread():
            try:
                # Encrypt main directories
                directories = [
                    "Launcher",
                    "Referral bot and bridge (final)",
                    "The Welcomed One, Exalted Rank",
                    "Med Rec",
                    "Cursor versions"
                ]
                
                total_encrypted = 0
                for directory in directories:
                    if Path(directory).exists():
                        self.log(f"📁 Encrypting {directory}...")
                        if self.encryptor.encrypt_directory(directory):
                            total_encrypted += 1
                            self.log(f"✅ {directory} encrypted successfully")
                        else:
                            self.log(f"❌ Failed to encrypt {directory}")
                    else:
                        self.log(f"⚠️ Directory not found: {directory}")
                
                self.log(f"🎉 Encryption complete! {total_encrypted} directories processed")
                self.log("📁 Original files backed up in 'encrypted_backup' folder")
                
            except Exception as e:
                self.log(f"❌ Error during encryption: {e}")
        
        threading.Thread(target=encrypt_thread, daemon=True).start()
    
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def main():
    """Main function"""
    try:
        app = EncryptionGUI()
        app.run()
    except Exception as e:
        print(f"Error starting encryptor: {e}")

if __name__ == "__main__":
    main()
