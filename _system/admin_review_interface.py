#!/usr/bin/env python3
"""
Admin Review Interface - Password-Protected Admin Section
Admin-only interface for reviewing AI optimization recommendations.
Requires admin password to access.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# Import optimization analyzer
try:
    from ai_optimization_analyzer import AIOptimizationAnalyzer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    AIOptimizationAnalyzer = None

# Import admin storage
try:
    from admin_secure_storage import AdminSecureStorage
    ADMIN_STORAGE_AVAILABLE = True
except ImportError:
    ADMIN_STORAGE_AVAILABLE = False
    AdminSecureStorage = None


class AdminReviewInterface:
    """
    Password-protected admin interface for reviewing AI recommendations.
    Requires admin password to access.
    """
    
    def __init__(self, parent_window, installation_dir: Optional[Path] = None):
        """Initialize admin review interface"""
        self.parent = parent_window
        self.installation_dir = installation_dir or Path(__file__).parent.parent
        
        # Initialize components
        self.optimization_analyzer = None
        self.admin_storage = None
        
        if OPTIMIZATION_AVAILABLE:
            self.optimization_analyzer = AIOptimizationAnalyzer(self.installation_dir)
        
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
        password_entry.pack(pady=(5, 20))
        password_entry.focus()
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")
        
        def verify_admin_password():
            password = password_var.get().strip()
            
            if not password:
                messagebox.showwarning("Missing Password", "Please enter admin password.")
                return
            
            # Authenticate
            if self.admin_storage:
                if self.admin_storage.authenticate(password):
                    self.authenticated = True
                    dialog.destroy()
                    self._open_admin_interface()
                else:
                    messagebox.showerror("Access Denied", "Incorrect admin password.")
                    password_var.set("")
                    password_entry.focus()
            else:
                # Fallback: Use default password
                DEFAULT_PASSWORD = "Integritycode2001@"
                if password == DEFAULT_PASSWORD:
                    self.authenticated = True
                    dialog.destroy()
                    self._open_admin_interface()
                else:
                    messagebox.showerror("Access Denied", "Incorrect admin password.")
                    password_var.set("")
                    password_entry.focus()
        
        def cancel_access():
            dialog.destroy()
        
        verify_button = tk.Button(button_frame, text="Grant Access", 
                                 command=verify_admin_password,
                                 bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                 padx=15, pady=5)
        verify_button.pack(side="left", padx=(0, 10))
        
        cancel_button = tk.Button(button_frame, text="Cancel", 
                                 command=cancel_access,
                                 bg="#666666", fg="white", font=("Arial", 10),
                                 padx=15, pady=5)
        cancel_button.pack(side="right")
        
        # Bind Enter key
        password_entry.bind("<Return>", lambda e: verify_admin_password())
    
    def _open_admin_interface(self):
        """Open admin review interface"""
        if not self.authenticated:
            return
        
        # Create admin window
        admin_window = tk.Toplevel(self.parent)
        admin_window.title("🔒 Admin Review - AI Optimization Recommendations")
        admin_window.geometry("1000x700")
        admin_window.configure(bg="#f0f0f0")
        
        # Header
        header_frame = tk.Frame(admin_window, bg="#d32f2f", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔒 Admin Review - AI Optimization Recommendations", 
                              font=("Arial", 18, "bold"), bg="#d32f2f", fg="white")
        title_label.pack(expand=True, pady=10)
        
        subtitle_label = tk.Label(header_frame, text="Review and approve AI-generated software optimization recommendations", 
                                 font=("Arial", 11), bg="#d32f2f", fg="#cccccc")
        subtitle_label.pack()
        
        # Main content
        main_frame = tk.Frame(admin_window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Info frame
        info_frame = tk.Frame(main_frame, bg="#fff3cd", relief="raised", bd=2)
        info_frame.pack(fill="x", pady=(0, 20))
        
        info_text = """⚠️ ADMIN ONLY: This section displays AI-generated optimization recommendations.
        
The AI passively monitors software usage and generates recommendations for improvements.
All recommendations require your approval before implementation.
AI Task Assistant training updates autonomously - this section is only for software changes."""
        
        info_label = tk.Label(info_frame, text=info_text, 
                             font=("Arial", 10), bg="#fff3cd", fg="#856404", 
                             justify="left", wraplength=950)
        info_label.pack(padx=15, pady=15)
        
        # Recommendations frame
        rec_frame = tk.LabelFrame(main_frame, text="Pending Recommendations", 
                                 font=("Arial", 12, "bold"), bg="#f0f0f0")
        rec_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Treeview for recommendations
        tree_frame = tk.Frame(rec_frame, bg="#f0f0f0")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        tree = ttk.Treeview(tree_frame, columns=("Type", "Title", "Complexity", "Confidence", "Status"),
                           show="tree headings", yscrollcommand=tree_scroll_y.set,
                           xscrollcommand=tree_scroll_x.set)
        
        tree.heading("#0", text="ID")
        tree.heading("Type", text="Type")
        tree.heading("Title", text="Title")
        tree.heading("Complexity", text="Complexity")
        tree.heading("Confidence", text="Confidence")
        tree.heading("Status", text="Status")
        
        tree.column("#0", width=50)
        tree.column("Type", width=120)
        tree.column("Title", width=300)
        tree.column("Complexity", width=100)
        tree.column("Confidence", width=100)
        tree.column("Status", width=100)
        
        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)
        
        tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Details frame
        details_frame = tk.LabelFrame(main_frame, text="Recommendation Details", 
                                     font=("Arial", 11, "bold"), bg="#f0f0f0")
        details_frame.pack(fill="x", pady=(0, 20))
        
        details_text = scrolledtext.ScrolledText(details_frame, height=8, 
                                                font=("Consolas", 10), wrap="word")
        details_text.pack(fill="x", padx=10, pady=10)
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.pack(fill="x")
        
        def refresh_recommendations():
            """Refresh recommendations list"""
            # Clear tree
            for item in tree.get_children():
                tree.delete(item)
            
            # Load recommendations
            if self.optimization_analyzer:
                try:
                    recommendations = self.optimization_analyzer.get_pending_recommendations()
                    
                    if recommendations:
                        for rec in recommendations:
                            tree.insert("", "end", 
                                       text=str(rec.get("id", "")),
                                       values=(
                                           rec.get("recommendation_type", ""),
                                           rec.get("title", ""),
                                           rec.get("implementation_complexity", ""),
                                           f"{rec.get('confidence_score', 0):.2%}",
                                           rec.get("status", "pending")
                                       ),
                                       tags=(str(rec.get("id")),))
                    else:
                        tree.insert("", "end", text="No recommendations", 
                                   values=("", "No pending recommendations", "", "", ""))
                except Exception as e:
                    tree.insert("", "end", text="Error", 
                               values=("", f"Error loading recommendations: {e}", "", "", ""))
        
        def show_details(event):
            """Show recommendation details"""
            selection = tree.selection()
            if not selection:
                return
            
            item = tree.item(selection[0])
            rec_id = int(item["text"])
            
            # Get recommendation details
            if self.optimization_analyzer:
                try:
                    recommendations = self.optimization_analyzer.get_pending_recommendations()
                    rec = next((r for r in recommendations if str(r.get("id")) == str(rec_id)), None)
                except Exception as e:
                    rec = None
                    details_text.delete("1.0", tk.END)
                    details_text.insert("1.0", f"Error loading recommendation: {e}")
                
                if rec:
                    details = f"""
RECOMMENDATION ID: {rec.get('id')}
TYPE: {rec.get('recommendation_type', '').upper()}
TITLE: {rec.get('title', '')}

DESCRIPTION:
{rec.get('description', '')}

CURRENT STATE:
{rec.get('current_state', '')}

PROPOSED CHANGE:
{rec.get('proposed_change', '')}

EXPECTED BENEFIT:
{rec.get('expected_benefit', '')}

IMPLEMENTATION COMPLEXITY: {rec.get('implementation_complexity', '')}
CONFIDENCE SCORE: {rec.get('confidence_score', 0):.2%}

DATA EVIDENCE:
{json.dumps(rec.get('data_evidence', {}), indent=2)}

CREATED: {rec.get('created_at', '')}
STATUS: {rec.get('status', 'pending').upper()}
"""
                    details_text.delete("1.0", tk.END)
                    details_text.insert("1.0", details.strip())
                    
                    # Store current selection
                    admin_window.current_rec_id = rec_id
        
        def approve_recommendation():
            """Approve selected recommendation"""
            if not hasattr(admin_window, 'current_rec_id'):
                messagebox.showwarning("No Selection", "Please select a recommendation to approve.")
                return
            
            # Request password confirmation
            password_dialog = tk.Toplevel(admin_window)
            password_dialog.title("Confirm Approval")
            password_dialog.geometry("400x200")
            password_dialog.configure(bg="#f0f0f0")
            password_dialog.transient(admin_window)
            password_dialog.grab_set()
            
            # Center window
            password_dialog.update_idletasks()
            x = (password_dialog.winfo_screenwidth() // 2) - (password_dialog.winfo_width() // 2)
            y = (password_dialog.winfo_screenheight() // 2) - (password_dialog.winfo_height() // 2)
            password_dialog.geometry(f"+{x}+{y}")
            
            tk.Label(password_dialog, text="Confirm Admin Password:", 
                    font=("Arial", 11), bg="#f0f0f0").pack(pady=20)
            
            password_var = tk.StringVar()
            password_entry = tk.Entry(password_dialog, textvariable=password_var, 
                                     font=("Arial", 11), show="*", width=30)
            password_entry.pack(pady=10)
            password_entry.focus()
            
            def confirm_approval():
                password = password_var.get().strip()
                
                if self.optimization_analyzer:
                    if self.optimization_analyzer.approve_recommendation(admin_window.current_rec_id, password):
                        messagebox.showinfo("Approved", "Recommendation approved successfully!")
                        password_dialog.destroy()
                        refresh_recommendations()
                        details_text.delete("1.0", tk.END)
                        if hasattr(admin_window, 'current_rec_id'):
                            del admin_window.current_rec_id
                    else:
                        messagebox.showerror("Error", "Failed to approve recommendation.\nCheck password or try again.")
            
            tk.Button(password_dialog, text="Approve", command=confirm_approval,
                     bg="#28a745", fg="white", font=("Arial", 10, "bold"),
                     padx=15, pady=5).pack(side="left", padx=20, pady=20)
            tk.Button(password_dialog, text="Cancel", command=password_dialog.destroy,
                     bg="#666666", fg="white", font=("Arial", 10),
                     padx=15, pady=5).pack(side="right", padx=20, pady=20)
            
            password_entry.bind("<Return>", lambda e: confirm_approval())
        
        def reject_recommendation():
            """Reject selected recommendation"""
            if not hasattr(admin_window, 'current_rec_id'):
                messagebox.showwarning("No Selection", "Please select a recommendation to reject.")
                return
            
            # Request password confirmation
            password_dialog = tk.Toplevel(admin_window)
            password_dialog.title("Confirm Rejection")
            password_dialog.geometry("400x200")
            password_dialog.configure(bg="#f0f0f0")
            password_dialog.transient(admin_window)
            password_dialog.grab_set()
            
            # Center window
            password_dialog.update_idletasks()
            x = (password_dialog.winfo_screenwidth() // 2) - (password_dialog.winfo_width() // 2)
            y = (password_dialog.winfo_screenheight() // 2) - (password_dialog.winfo_height() // 2)
            password_dialog.geometry(f"+{x}+{y}")
            
            tk.Label(password_dialog, text="Confirm Admin Password:", 
                    font=("Arial", 11), bg="#f0f0f0").pack(pady=20)
            
            password_var = tk.StringVar()
            password_entry = tk.Entry(password_dialog, textvariable=password_var, 
                                     font=("Arial", 11), show="*", width=30)
            password_entry.pack(pady=10)
            password_entry.focus()
            
            def confirm_rejection():
                password = password_var.get().strip()
                
                if self.optimization_analyzer:
                    if self.optimization_analyzer.reject_recommendation(admin_window.current_rec_id, password):
                        messagebox.showinfo("Rejected", "Recommendation rejected.")
                        password_dialog.destroy()
                        refresh_recommendations()
                        details_text.delete("1.0", tk.END)
                        if hasattr(admin_window, 'current_rec_id'):
                            del admin_window.current_rec_id
                    else:
                        messagebox.showerror("Error", "Failed to reject recommendation.\nCheck password or try again.")
            
            tk.Button(password_dialog, text="Reject", command=confirm_rejection,
                     bg="#dc3545", fg="white", font=("Arial", 10, "bold"),
                     padx=15, pady=5).pack(side="left", padx=20, pady=20)
            tk.Button(password_dialog, text="Cancel", command=password_dialog.destroy,
                     bg="#666666", fg="white", font=("Arial", 10),
                     padx=15, pady=5).pack(side="right", padx=20, pady=20)
            
            password_entry.bind("<Return>", lambda e: confirm_rejection())
        
        def run_analysis():
            """Run new analysis"""
            if self.optimization_analyzer:
                messagebox.showinfo("Analysis Started", "AI optimization analysis started.\nThis may take a few minutes.")
                result = self.optimization_analyzer.analyze_software_usage()
                messagebox.showinfo("Analysis Complete", 
                                  f"Analysis complete!\n{len(result.get('recommendations', []))} recommendations generated.")
                refresh_recommendations()
                report_text = result.get("report_text")
                report_path = result.get("report_path")
                if report_text:
                    report_window = tk.Toplevel(admin_window)
                    report_window.title("Analysis Report")
                    report_window.geometry("900x600")
                    report_window.configure(bg="#f0f0f0")

                    title = tk.Label(report_window, text="AI Optimization Analysis Report", font=("Arial", 16, "bold"), bg="#f0f0f0")
                    title.pack(pady=(15, 10))

                    info_text = f"Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    if report_path:
                        info_text += f"\nSaved to: {report_path}"
                    info_label = tk.Label(report_window, text=info_text, font=("Arial", 10), bg="#f0f0f0")
                    info_label.pack()

                    report_box = scrolledtext.ScrolledText(report_window, font=("Courier New", 10), wrap=tk.WORD)
                    report_box.pack(fill="both", expand=True, padx=15, pady=15)
                    report_box.insert("1.0", report_text)
                    report_box.config(state=tk.DISABLED)

                    close_btn = tk.Button(report_window, text="Close", command=report_window.destroy,
                                          bg="#007bff", fg="white", font=("Arial", 10, "bold"), padx=20, pady=6)
                    close_btn.pack(pady=(0, 15))
        
        # Buttons
        refresh_button = tk.Button(buttons_frame, text="🔄 Refresh", 
                                  command=refresh_recommendations,
                                  bg="#007bff", fg="white", font=("Arial", 10, "bold"),
                                  padx=15, pady=8)
        refresh_button.pack(side="left", padx=(0, 10))
        
        analyze_button = tk.Button(buttons_frame, text="🔍 Run Analysis", 
                                   command=run_analysis,
                                   bg="#17a2b8", fg="white", font=("Arial", 10, "bold"),
                                   padx=15, pady=8)
        analyze_button.pack(side="left", padx=(0, 10))
        
        approve_button = tk.Button(buttons_frame, text="✅ Approve", 
                                  command=approve_recommendation,
                                  bg="#28a745", fg="white", font=("Arial", 10, "bold"),
                                  padx=15, pady=8)
        approve_button.pack(side="left", padx=(0, 10))
        
        reject_button = tk.Button(buttons_frame, text="❌ Reject", 
                                 command=reject_recommendation,
                                 bg="#dc3545", fg="white", font=("Arial", 10, "bold"),
                                 padx=15, pady=8)
        reject_button.pack(side="right")
        
        # Bind tree selection
        tree.bind("<<TreeviewSelect>>", show_details)
        
        # Store tree and details for refresh function
        admin_window.tree = tree
        admin_window.details_text = details_text
        
        # Load initial recommendations
        refresh_recommendations()


def open_admin_review(parent_window, installation_dir: Optional[Path] = None):
    """Open admin review interface"""
    interface = AdminReviewInterface(parent_window, installation_dir)
    return interface

