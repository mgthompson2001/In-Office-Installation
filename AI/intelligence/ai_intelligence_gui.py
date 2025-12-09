#!/usr/bin/env python3
"""
AI Intelligence Dashboard GUI
Real-time visualization of AI learning progress and generative intelligence metrics
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from verify_ai_intelligence import AIIntelligenceDashboard


class AIIntelligenceGUI:
    """GUI dashboard for AI intelligence metrics"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Intelligence Dashboard - Generative Intelligence System")
        self.root.geometry("900x700")
        
        self.dashboard = AIIntelligenceDashboard()
        self.refresh_interval = 5  # seconds
        
        self._create_widgets()
        self._start_refresh_loop()
    
    def _create_widgets(self):
        """Create GUI widgets"""
        # Header
        header = tk.Label(
            self.root,
            text="AI INTELLIGENCE DASHBOARD",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white",
            pady=10
        )
        header.pack(fill=tk.X)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Checking system status...",
            font=("Arial", 10),
            fg="blue"
        )
        self.status_label.pack()
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(self.root, text="Data Collection Metrics", padding=10)
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(metrics_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Data Collection Tab
        data_tab = ttk.Frame(notebook)
        notebook.add(data_tab, text="Data Collection")
        
        self.data_text = scrolledtext.ScrolledText(data_tab, height=15, wrap=tk.WORD)
        self.data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # AI Learning Tab
        learning_tab = ttk.Frame(notebook)
        notebook.add(learning_tab, text="AI Learning")
        
        self.learning_text = scrolledtext.ScrolledText(learning_tab, height=15, wrap=tk.WORD)
        self.learning_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Intelligence Tab
        intelligence_tab = ttk.Frame(notebook)
        notebook.add(intelligence_tab, text="Generative Intelligence")
        
        self.intelligence_text = scrolledtext.ScrolledText(intelligence_tab, height=15, wrap=tk.WORD)
        self.intelligence_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        refresh_btn = ttk.Button(control_frame, text="Refresh Now", command=self._refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        export_btn = ttk.Button(control_frame, text="Export Report", command=self._export_report)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = ttk.Checkbutton(
            control_frame,
            text="Auto-refresh (5s)",
            variable=self.auto_refresh_var
        )
        auto_refresh_check.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            control_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
        
        self.progress_label = tk.Label(control_frame, text="0%")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
    
    def _refresh_data(self):
        """Refresh all data"""
        try:
            # Status
            status = self.dashboard.get_monitoring_status()
            if status["monitoring_active"]:
                self.status_label.config(text="[OK] Monitoring Active - System Learning", fg="green")
            elif status["data_collected"]:
                self.status_label.config(text="[PAUSED] Data Collected - Ready for Analysis", fg="orange")
            else:
                self.status_label.config(text="[INACTIVE] No Data Collected", fg="red")
            
            # Data Collection Metrics
            metrics = self.dashboard.get_data_collection_metrics()
            data_lines = []
            data_lines.append("DATA COLLECTION METRICS")
            data_lines.append("=" * 60)
            data_lines.append(f"Total Data Points: {metrics['total_data_points']:,}")
            data_lines.append(f"  - Screen Recordings: {metrics['total_screens']:,}")
            data_lines.append(f"  - Keyboard Input: {metrics['total_keyboard']:,}")
            data_lines.append(f"  - Mouse Activity: {metrics['total_mouse']:,}")
            data_lines.append(f"  - Application Usage: {metrics['total_apps']:,}")
            data_lines.append(f"  - File Activity: {metrics['total_files']:,}")
            data_lines.append("")
            data_lines.append(f"Sessions Recorded: {metrics['sessions_count']}")
            data_lines.append(f"Data Size: {metrics['data_size_mb']} MB")
            data_lines.append(f"Time Span: {metrics['time_span_days']} days")
            if metrics['collection_rate_per_hour'] > 0:
                data_lines.append(f"Collection Rate: {metrics['collection_rate_per_hour']:.1f} data points/hour")
            
            self.data_text.delete(1.0, tk.END)
            self.data_text.insert(1.0, "\n".join(data_lines))
            
            # AI Learning Metrics
            learning = self.dashboard.get_ai_learning_metrics()
            learning_lines = []
            learning_lines.append("AI LEARNING METRICS")
            learning_lines.append("=" * 60)
            learning_lines.append(f"Patterns Extracted: {learning['patterns_extracted']:,}")
            learning_lines.append(f"Workflows Identified: {learning['workflows_identified']:,}")
            learning_lines.append(f"Sequences Learned: {learning['sequences_learned']:,}")
            learning_lines.append(f"Models Trained: {learning['models_trained']}")
            learning_lines.append(f"Learning Progress: {learning['learning_progress']}%")
            learning_lines.append("")
            if learning.get("last_analysis"):
                learning_lines.append(f"Last Analysis: {learning['last_analysis']}")
            if learning.get("last_training"):
                learning_lines.append(f"Last Training: {learning['last_training']}")
            
            self.learning_text.delete(1.0, tk.END)
            self.learning_text.insert(1.0, "\n".join(learning_lines))
            
            # Update progress bar
            self.progress_var.set(learning['learning_progress'])
            self.progress_label.config(text=f"{learning['learning_progress']}%")
            
            # Generative Intelligence
            insights = self.dashboard.get_operational_insights()
            intel_lines = []
            intel_lines.append("GENERATIVE INTELLIGENCE STATUS")
            intel_lines.append("=" * 60)
            intel_lines.append(f"Learning Velocity: {insights['learning_velocity']}")
            intel_lines.append("")
            intel_lines.append("Most Used Applications:")
            for app in insights["most_used_apps"][:5]:
                intel_lines.append(f"  - {app['app']}: {app['usage_count']:,} uses")
            intel_lines.append("")
            intel_lines.append("CONTRIBUTION TO REVOLUTIONIZING OPERATIONS:")
            intel_lines.append("")
            
            # Calculate contribution
            contribution_score = 0
            if metrics['total_data_points'] > 10000:
                contribution_score += 30
                intel_lines.append("[OK] High data volume - System learning effectively")
            elif metrics['total_data_points'] > 1000:
                contribution_score += 15
                intel_lines.append("[OK] Moderate data volume - Building knowledge base")
            
            if learning['patterns_extracted'] > 100:
                contribution_score += 25
                intel_lines.append("[OK] Significant patterns extracted - AI understanding workflows")
            elif learning['patterns_extracted'] > 10:
                contribution_score += 10
                intel_lines.append("[OK] Patterns being identified - Learning in progress")
            
            if learning['workflows_identified'] > 10:
                contribution_score += 25
                intel_lines.append("[OK] Workflows being learned - Automation opportunities identified")
            elif learning['workflows_identified'] > 0:
                contribution_score += 10
                intel_lines.append("[OK] Workflow identification started")
            
            if learning['models_trained'] > 0:
                contribution_score += 20
                intel_lines.append("[OK] AI models actively training - Generative intelligence building")
            
            intel_lines.append("")
            intel_lines.append(f"Contribution Score: {contribution_score}/100")
            intel_lines.append("")
            intel_lines.append("SYSTEM STATUS: Building Generative Intelligence")
            intel_lines.append("The monitoring system is actively learning your workflows,")
            intel_lines.append("patterns, and behaviors to create an autonomous AI that")
            intel_lines.append("will revolutionize company operations through intelligent automation.")
            
            self.intelligence_text.delete(1.0, tk.END)
            self.intelligence_text.insert(1.0, "\n".join(intel_lines))
            
        except Exception as e:
            self.status_label.config(text=f"[ERROR] {str(e)}", fg="red")
    
    def _export_report(self):
        """Export full report"""
        try:
            from datetime import datetime
            report = self.dashboard.generate_report()
            
            # Save to AI Analysis reports folder
            ai_dir = Path(__file__).parent.parent
            analysis_reports_dir = ai_dir / "AI Analysis reports"
            analysis_reports_dir.mkdir(exist_ok=True, parents=True, mode=0o700)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = analysis_reports_dir / f"ai_intelligence_report_{timestamp}.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            from tkinter import messagebox
            messagebox.showinfo("Report Exported", f"Report saved to:\n{report_file}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to export report: {e}")
    
    def _start_refresh_loop(self):
        """Start auto-refresh loop"""
        def refresh_loop():
            while True:
                if self.auto_refresh_var.get():
                    self._refresh_data()
                time.sleep(self.refresh_interval)
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        
        # Initial refresh
        self._refresh_data()
    
    def run(self):
        """Run GUI"""
        self.root.mainloop()


def main():
    """Main function"""
    app = AIIntelligenceGUI()
    app.run()


if __name__ == "__main__":
    main()

