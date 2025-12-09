#!/usr/bin/env python3
"""
Admin Dashboard GUI - Password-Protected Admin Section
Admin-only interface for viewing employee registry and collected data.
Requires admin password to access.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# Import admin dashboard
try:
    from admin_dashboard import AdminDashboard
    ADMIN_DASHBOARD_AVAILABLE = True
except ImportError:
    ADMIN_DASHBOARD_AVAILABLE = False
    AdminDashboard = None

# Import admin storage
try:
    from admin_secure_storage import AdminSecureStorage
    ADMIN_STORAGE_AVAILABLE = True
except ImportError:
    ADMIN_STORAGE_AVAILABLE = False
    AdminSecureStorage = None


class AdminDashboardGUI:
    """
    Password-protected admin interface for viewing employee registry and data.
    Requires admin password to access.
    """
    
    def __init__(self, parent_window, installation_dir: Optional[Path] = None):
        """Initialize admin dashboard GUI"""
        self.parent = parent_window
        self.installation_dir = installation_dir or Path(__file__).parent.parent
        
        # Initialize components
        self.admin_dashboard = None
        self.admin_storage = None
        
        if ADMIN_DASHBOARD_AVAILABLE:
            self.admin_dashboard = AdminDashboard(self.installation_dir)
        
        if ADMIN_STORAGE_AVAILABLE:
            self.admin_storage = AdminSecureStorage(self.installation_dir)
        
        # Authentication
        self.authenticated = False
        
        # Create password dialog first
        self._request_admin_access()
    
    def _request_admin_access(self):
        """Request admin password access"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Admin Access Required")
        dialog.geometry("400x250")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center window
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(dialog, bg="#d32f2f", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔒 Admin Access Required", 
                              font=("Arial", 16, "bold"), bg="#d32f2f", fg="white")
        title_label.pack(expand=True)
        
        # Main content
        content_frame = tk.Frame(dialog, bg="#f0f0f0")
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Warning
        warning_label = tk.Label(content_frame, 
                                text="⚠️ WARNING: This grants access to admin-only features.\nOnly authorized administrators should proceed.",
                                font=("Arial", 10), bg="#f0f0f0", fg="#d32f2f", justify="center")
        warning_label.pack(pady=(0, 20))
        
        # Password entry
        password_label = tk.Label(content_frame, text="Enter Admin Password:", 
                                 font=("Arial", 11), bg="#f0f0f0")
        password_label.pack(anchor="w")
        
        password_var = tk.StringVar()
        password_entry = tk.Entry(content_frame, textvariable=password_var, 
                                 font=("Arial", 11), show="*", width=30)
        password_entry.pack(pady=(5, 15), fill="x")
        password_entry.focus()
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")
        
        def authenticate():
            password = password_var.get()
            
            if not self.admin_storage:
                messagebox.showerror("Error", "Admin storage not available!")
                dialog.destroy()
                return
            
            if self.admin_storage.authenticate(password):
                self.authenticated = True
                dialog.destroy()
                self._create_main_window()
            else:
                messagebox.showerror("Access Denied", "Invalid password. Access denied.")
                password_var.set("")
                password_entry.focus()
        
        def cancel():
            dialog.destroy()
        
        # Enter key binding
        password_entry.bind("<Return>", lambda e: authenticate())
        
        login_button = tk.Button(button_frame, text="Login", command=authenticate,
                                bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                padx=20, pady=5, cursor="hand2")
        login_button.pack(side="left", padx=(0, 10))
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=cancel,
                                 bg="#666666", fg="white", font=("Arial", 10),
                                 padx=20, pady=5, cursor="hand2")
        cancel_button.pack(side="left")
    
    def _create_main_window(self):
        """Create main admin dashboard window"""
        window = tk.Toplevel(self.parent)
        window.title("Admin Dashboard - Employee Registry & Data Review")
        window.geometry("1000x700")
        window.configure(bg="#f0f0f0")
        
        # Header
        header_frame = tk.Frame(window, bg="#d32f2f", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📊 Admin Dashboard", 
                              font=("Arial", 18, "bold"), bg="#d32f2f", fg="white")
        title_label.pack(expand=True, pady=10)
        
        subtitle_label = tk.Label(header_frame, text="Employee Registry & Collected Data Review", 
                                 font=("Arial", 11), bg="#d32f2f", fg="white")
        subtitle_label.pack()
        
        # Main content
        main_frame = tk.Frame(window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Top section: Employee list and summary
        top_frame = tk.Frame(main_frame, bg="#f0f0f0")
        top_frame.pack(fill="x", pady=(0, 20))
        
        # Left: Employee list
        left_frame = tk.Frame(top_frame, bg="#ffffff", relief="solid", bd=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        employees_label = tk.Label(left_frame, text="Registered Employees", 
                                  font=("Arial", 12, "bold"), bg="#ffffff")
        employees_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Employee listbox
        employees_frame = tk.Frame(left_frame, bg="#ffffff")
        employees_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        employees_listbox = tk.Listbox(employees_frame, font=("Arial", 10), 
                                       height=12, selectmode="single")
        employees_listbox.pack(fill="both", expand=True)
        
        # Scrollbar for employees
        employees_scrollbar = ttk.Scrollbar(employees_frame, orient="vertical", 
                                           command=employees_listbox.yview)
        employees_scrollbar.pack(side="right", fill="y")
        employees_listbox.config(yscrollcommand=employees_scrollbar.set)
        
        # Right: Summary statistics
        right_frame = tk.Frame(top_frame, bg="#ffffff", relief="solid", bd=1)
        right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        summary_label = tk.Label(right_frame, text="Data Summary", 
                                font=("Arial", 12, "bold"), bg="#ffffff")
        summary_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Summary text
        summary_text = scrolledtext.ScrolledText(right_frame, font=("Consolas", 9), 
                                                 height=12, bg="#f8f8f8")
        summary_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Bottom section: Employee details
        bottom_frame = tk.Frame(main_frame, bg="#ffffff", relief="solid", bd=1)
        bottom_frame.pack(fill="both", expand=True)
        
        details_label = tk.Label(bottom_frame, text="Employee Details", 
                                font=("Arial", 12, "bold"), bg="#ffffff")
        details_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Details text
        details_text = scrolledtext.ScrolledText(bottom_frame, font=("Consolas", 9), 
                                                 bg="#f8f8f8")
        details_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Buttons
        button_frame = tk.Frame(window, bg="#f0f0f0")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        def refresh_data():
            """Refresh all data"""
            employees_listbox.delete(0, tk.END)
            summary_text.delete(1.0, tk.END)
            details_text.delete(1.0, tk.END)
            
            if not self.admin_dashboard:
                details_text.insert(tk.END, "[ERROR] Admin dashboard not available!")
                return
            
            # Load employees
            employees = self.admin_dashboard.view_all_employees()
            
            if not employees:
                employees_listbox.insert(0, "No employees registered yet")
                summary_text.insert(tk.END, "[WARN] No employees registered yet.\n\n")
                summary_text.insert(tk.END, "To register employees:\n")
                summary_text.insert(tk.END, "  1. Have employees run 'install_bots.bat'\n")
                summary_text.insert(tk.END, "  2. They will enter their name\n")
                summary_text.insert(tk.END, "  3. They will appear in this registry\n")
                return
            
            # Populate employee list
            for emp in employees:
                employees_listbox.insert(tk.END, f"{emp['user_name']} - {emp['computer_name']}")
            
            # Load summary
            summary = self.admin_dashboard.view_all_data_summary()
            
            summary_text.insert(tk.END, "Aggregated Data Across All Employees:\n\n")
            summary_text.insert(tk.END, f"Bot Executions: {summary.get('bot_executions', 0)}\n")
            summary_text.insert(tk.END, f"AI Prompts: {summary.get('ai_prompts', 0)}\n")
            summary_text.insert(tk.END, f"Workflow Patterns: {summary.get('workflow_patterns', 0)}\n")
            summary_text.insert(tk.END, f"Unique Users: {summary.get('unique_users', 0)}\n")
            summary_text.insert(tk.END, f"Unique Computers: {summary.get('unique_computers', 0)}\n")
            summary_text.insert(tk.END, f"Total Records: {summary.get('total_records', 0)}\n")
            
            # Show first employee details by default
            if employees:
                show_employee_details(employees[0]['user_name'])
        
        def show_employee_details(employee_name):
            """Show detailed data for selected employee"""
            details_text.delete(1.0, tk.END)
            
            if not self.admin_dashboard:
                details_text.insert(tk.END, "[ERROR] Admin dashboard not available!")
                return
            
            employee_data = self.admin_dashboard.view_employee_data(employee_name)
            
            if not employee_data:
                details_text.insert(tk.END, f"[WARN] No data found for {employee_name}")
                return
            
            user_info = employee_data.get('user_info', {})
            stats = employee_data.get('stats', {})
            bot_executions = employee_data.get('bot_executions', [])
            ai_prompts = employee_data.get('ai_prompts', [])
            workflow_patterns = employee_data.get('workflow_patterns', [])
            
            # Employee info
            details_text.insert(tk.END, f"EMPLOYEE INFORMATION\n")
            details_text.insert(tk.END, "=" * 70 + "\n")
            details_text.insert(tk.END, f"Name: {user_info.get('user_name', 'N/A')}\n")
            details_text.insert(tk.END, f"Computer: {user_info.get('computer_name', 'N/A')}\n")
            details_text.insert(tk.END, f"Computer ID: {user_info.get('computer_id', 'N/A')}\n")
            details_text.insert(tk.END, f"Registered: {user_info.get('registered_at', 'N/A')}\n")
            details_text.insert(tk.END, f"Last Active: {user_info.get('last_active', 'Never')}\n\n")
            
            # Statistics
            details_text.insert(tk.END, f"DATA STATISTICS\n")
            details_text.insert(tk.END, "=" * 70 + "\n")
            details_text.insert(tk.END, f"Bot Executions: {stats.get('bot_executions', 0)}\n")
            details_text.insert(tk.END, f"AI Prompts: {stats.get('ai_prompts', 0)}\n")
            details_text.insert(tk.END, f"Workflow Patterns: {stats.get('workflow_patterns', 0)}\n")
            details_text.insert(tk.END, f"Total Records: {stats.get('total_records', 0)}\n\n")
            
            # Bot executions
            if bot_executions:
                details_text.insert(tk.END, f"RECENT BOT EXECUTIONS (Last {min(10, len(bot_executions))})\n")
                details_text.insert(tk.END, "=" * 70 + "\n")
                for i, exec in enumerate(bot_executions[:10], 1):
                    details_text.insert(tk.END, f"\n{i}. Bot: {exec.get('bot_name', 'N/A')}\n")
                    details_text.insert(tk.END, f"   Time: {exec.get('execution_time', 'N/A')}\n")
                    if exec.get('parameters'):
                        try:
                            params = json.loads(exec['parameters']) if isinstance(exec['parameters'], str) else exec['parameters']
                            details_text.insert(tk.END, f"   Parameters: {json.dumps(params, indent=2)}\n")
                        except:
                            details_text.insert(tk.END, f"   Parameters: {exec.get('parameters', 'N/A')}\n")
                    if exec.get('result'):
                        details_text.insert(tk.END, f"   Result: {exec.get('result', 'N/A')}\n")
                details_text.insert(tk.END, "\n")
            
            # AI prompts
            if ai_prompts:
                details_text.insert(tk.END, f"RECENT AI PROMPTS (Last {min(10, len(ai_prompts))})\n")
                details_text.insert(tk.END, "=" * 70 + "\n")
                for i, prompt in enumerate(ai_prompts[:10], 1):
                    details_text.insert(tk.END, f"\n{i}. Time: {prompt.get('execution_time', 'N/A')}\n")
                    details_text.insert(tk.END, f"   Prompt: {prompt.get('prompt', 'N/A')[:100]}...\n")
                    if prompt.get('bot_used'):
                        details_text.insert(tk.END, f"   Bot Used: {prompt.get('bot_used', 'N/A')}\n")
                details_text.insert(tk.END, "\n")
            
            # Workflow patterns
            if workflow_patterns:
                details_text.insert(tk.END, f"WORKFLOW PATTERNS (Last {min(10, len(workflow_patterns))})\n")
                details_text.insert(tk.END, "=" * 70 + "\n")
                for i, pattern in enumerate(workflow_patterns[:10], 1):
                    details_text.insert(tk.END, f"\n{i}. Pattern: {pattern.get('pattern_name', 'N/A')}\n")
                    details_text.insert(tk.END, f"   Frequency: {pattern.get('frequency', 0)}\n")
                    details_text.insert(tk.END, f"   Last Used: {pattern.get('last_used', 'N/A')}\n")
        
        def on_employee_select(event):
            """Handle employee selection"""
            selection = employees_listbox.curselection()
            if selection:
                index = selection[0]
                employees = self.admin_dashboard.view_all_employees()
                if index < len(employees):
                    employee_name = employees[index]['user_name']
                    show_employee_details(employee_name)
        
        employees_listbox.bind("<<ListboxSelect>>", on_employee_select)
        
        refresh_button = tk.Button(button_frame, text="🔄 Refresh Data", command=refresh_data,
                                  bg="#4caf50", fg="white", font=("Arial", 10, "bold"),
                                  padx=15, pady=5, cursor="hand2")
        refresh_button.pack(side="left", padx=(0, 10))
        
        close_button = tk.Button(button_frame, text="Close", command=window.destroy,
                                bg="#666666", fg="white", font=("Arial", 10),
                                padx=15, pady=5, cursor="hand2")
        close_button.pack(side="left")
        
        # Initial load
        refresh_data()


def open_admin_dashboard(parent_window, installation_dir: Optional[Path] = None):
    """
    Open admin dashboard GUI with password protection.
    
    Args:
        parent_window: Parent window (secure launcher)
        installation_dir: Installation directory path
    """
    if not ADMIN_DASHBOARD_AVAILABLE:
        messagebox.showerror("Error", 
                            "Admin dashboard not available!\n\n"
                            "Please ensure admin_dashboard.py is available.")
        return
    
    if not ADMIN_STORAGE_AVAILABLE:
        messagebox.showerror("Error", 
                            "Admin storage not available!\n\n"
                            "Please ensure admin_secure_storage.py is available.")
        return
    
    try:
        AdminDashboardGUI(parent_window, installation_dir)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open admin dashboard:\n{str(e)}")

