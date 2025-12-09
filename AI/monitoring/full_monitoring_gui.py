#!/usr/bin/env python3
"""
Full System Monitoring GUI
Control interface for full system monitoring.
For personal use with explicit consent.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from pathlib import Path
from datetime import datetime
import sys
import subprocess

# Ensure dependencies are installed before importing
def ensure_dependencies():
    """Ensure all dependencies are installed"""
    try:
        import mss
        import pynput
        import psutil
        import watchdog
        return True
    except ImportError:
        # Try to install missing dependencies
        try:
            print("Installing missing dependencies...")
            # Use --no-warn-script-location to suppress PATH warnings
            # Use --only-binary :all: to avoid building from source (which requires C compiler)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", 
                                  "--no-warn-script-location", "--only-binary", ":all:", 
                                  "mss", "pynput", "psutil", "watchdog"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Try importing again
            import mss
            import pynput
            import psutil
            import watchdog
            print("Dependencies installed successfully!")
            return True
        except Exception as e:
            print(f"Failed to install dependencies: {e}")
            print(f"Python executable: {sys.executable}")
            print("Please run: install_all_dependencies.bat to install dependencies manually")
            return False

# Check dependencies before proceeding
if not ensure_dependencies():
    print("WARNING: Some dependencies may not be installed. The GUI may not work correctly.")

# Import full system monitor
try:
    from full_system_monitor import start_full_monitoring, stop_full_monitoring, get_full_monitor
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False
    start_full_monitoring = None
    stop_full_monitoring = None
    get_full_monitor = None

# Import AI training integration
try:
    from ai_training_integration import start_ai_training, stop_ai_training, get_ai_training_integration
    AI_TRAINING_AVAILABLE = True
except ImportError:
    AI_TRAINING_AVAILABLE = False
    start_ai_training = None
    stop_ai_training = None
    get_ai_training_integration = None


class FullMonitoringGUI(tk.Tk):
    """GUI for full system monitoring control"""
    
    def __init__(self):
        super().__init__()
        self.title("Full System Monitor - Personal Use")
        self.geometry("800x600")
        self.configure(bg="#f0f0f0")
        
        # Get installation directory
        installation_dir = Path(__file__).parent.parent
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor = None
        self.installation_dir = installation_dir
        
        # AI training integration
        self.ai_training_active = False
        self.ai_integration = None
        
        # Setup GUI
        self._setup_gui()
        
        # Update thread
        self.update_thread = None
        self._start_update_thread()
    
    def _setup_gui(self):
        """Setup GUI components"""
        # Header
        header = tk.Frame(self, bg="#2c3e50", height=60)
        header.pack(fill=tk.X)
        
        title = tk.Label(header, text="Full System Monitor", 
                        font=("Arial", 18, "bold"), 
                        bg="#2c3e50", fg="white")
        title.pack(pady=15)
        
        # Consent notice
        consent_frame = tk.Frame(self, bg="#fff3cd", padx=10, pady=10)
        consent_frame.pack(fill=tk.X, padx=10, pady=10)
        
        consent_label = tk.Label(consent_frame, 
                                text="⚠️ PERSONAL USE ONLY - You have given explicit consent for full system monitoring.",
                                font=("Arial", 10, "bold"),
                                bg="#fff3cd", fg="#856404",
                                wraplength=750, justify=tk.LEFT)
        consent_label.pack()
        
        # Control panel
        control_frame = tk.LabelFrame(self, text="Monitoring Control", 
                                      font=("Arial", 12, "bold"),
                                      bg="#f0f0f0", padx=10, pady=10)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Monitoring options
        options_frame = tk.Frame(control_frame, bg="#f0f0f0")
        options_frame.pack(fill=tk.X, pady=5)
        
        self.record_screen_var = tk.BooleanVar(value=True)
        self.record_keyboard_var = tk.BooleanVar(value=True)
        self.record_mouse_var = tk.BooleanVar(value=True)
        self.record_apps_var = tk.BooleanVar(value=True)
        self.record_files_var = tk.BooleanVar(value=True)
        
        tk.Checkbutton(options_frame, text="Record Screen", 
                      variable=self.record_screen_var,
                      bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(options_frame, text="Record Keyboard", 
                      variable=self.record_keyboard_var,
                      bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(options_frame, text="Record Mouse", 
                      variable=self.record_mouse_var,
                      bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(options_frame, text="Record Applications", 
                      variable=self.record_apps_var,
                      bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(options_frame, text="Record Files", 
                      variable=self.record_files_var,
                      bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        # Control buttons
        button_frame = tk.Frame(control_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = tk.Button(button_frame, text="Start Monitoring", 
                                      command=self._start_monitoring,
                                      bg="#27ae60", fg="white",
                                      font=("Arial", 12, "bold"),
                                      padx=20, pady=10)
        self.start_button.pack(side=tk.LEFT, padx=10)
        
        self.stop_button = tk.Button(button_frame, text="Stop Monitoring", 
                                     command=self._stop_monitoring,
                                     bg="#e74c3c", fg="white",
                                     font=("Arial", 12, "bold"),
                                     padx=20, pady=10,
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        # Status panel
        status_frame = tk.LabelFrame(self, text="Monitoring Status", 
                                     font=("Arial", 12, "bold"),
                                     bg="#f0f0f0", padx=10, pady=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status text
        self.status_text = scrolledtext.ScrolledText(status_frame, 
                                                     height=15,
                                                     font=("Courier", 9),
                                                     bg="#2c3e50", fg="#ecf0f1",
                                                     wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Metrics display
        metrics_frame = tk.Frame(self, bg="#f0f0f0", padx=10, pady=10)
        metrics_frame.pack(fill=tk.X)
        
        self.metrics_label = tk.Label(metrics_frame, 
                                      text="Metrics: Not started",
                                      font=("Arial", 10),
                                      bg="#f0f0f0", fg="#2c3e50",
                                      justify=tk.LEFT)
        self.metrics_label.pack(anchor=tk.W)
    
    def _start_monitoring(self):
        """Start full system monitoring"""
        if not MONITOR_AVAILABLE:
            messagebox.showerror("Error", "Full system monitor not available. Install required dependencies.")
            return
        
        # Confirm consent
        consent = messagebox.askyesno(
            "Consent Required",
            "You are about to start FULL SYSTEM MONITORING.\n\n"
            "This will record:\n"
            "- Screen activity\n"
            "- Keyboard input\n"
            "- Mouse movements\n"
            "- Application usage\n"
            "- File system activity\n\n"
            "All data will be encrypted and stored locally.\n\n"
            "Do you give explicit consent to start monitoring?"
        )
        
        if not consent:
            return
        
        try:
            # Import and start monitoring
            from full_system_monitor import FullSystemMonitor
            
            self.monitor = FullSystemMonitor(
                installation_dir=self.installation_dir,
                user_consent=True,
                record_screen=self.record_screen_var.get(),
                record_keyboard=self.record_keyboard_var.get(),
                record_mouse=self.record_mouse_var.get(),
                record_apps=self.record_apps_var.get(),
                record_files=self.record_files_var.get()
            )
            
            self.monitor.start_monitoring()
            self.monitoring_active = True
            
            # Start AI training integration
            if AI_TRAINING_AVAILABLE:
                try:
                    self.ai_integration = start_ai_training(self.installation_dir)
                    self.ai_training_active = True
                    self._log("✅ AI training integration started")
                    self._log("   - Automatically analyzing recorded data")
                    self._log("   - Extracting patterns and workflows")
                    self._log("   - Training AI models for employee model training")
                except Exception as e:
                    self._log(f"⚠️ AI training integration warning: {e}")
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            self._log("✅ Full system monitoring started")
            self._log(f"Session ID: {self.monitor.session_id}")
            self._log(f"Recording: Screen={self.record_screen_var.get()}, "
                     f"Keyboard={self.record_keyboard_var.get()}, "
                     f"Mouse={self.record_mouse_var.get()}, "
                     f"Apps={self.record_apps_var.get()}, "
                     f"Files={self.record_files_var.get()}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start monitoring: {e}")
            self._log(f"❌ Error starting monitoring: {e}")
    
    def _stop_monitoring(self):
        """Stop full system monitoring"""
        if not self.monitor:
            return
        
        try:
            # Stop AI training integration
            if self.ai_training_active and AI_TRAINING_AVAILABLE:
                try:
                    stop_ai_training()
                    self.ai_training_active = False
                    self._log("✅ AI training integration stopped")
                except Exception as e:
                    self._log(f"⚠️ Error stopping AI training: {e}")
            
            self.monitor.stop_monitoring()
            self.monitoring_active = False
            
            # Update UI
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Get final metrics
            metrics = self.monitor.get_metrics()
            self._log("✅ Full system monitoring stopped")
            self._log(f"Total screens recorded: {metrics.get('screens_recorded', 0)}")
            self._log(f"Total keystrokes recorded: {metrics.get('keystrokes_recorded', 0)}")
            self._log(f"Total mouse events recorded: {metrics.get('mouse_events_recorded', 0)}")
            self._log(f"Total app switches recorded: {metrics.get('app_switches_recorded', 0)}")
            self._log(f"Total file events recorded: {metrics.get('file_events_recorded', 0)}")
            
            self.monitor = None
            self.ai_integration = None
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop monitoring: {e}")
            self._log(f"❌ Error stopping monitoring: {e}")
    
    def _log(self, message: str):
        """Log message to status text"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
    
    def _start_update_thread(self):
        """Start update thread for metrics"""
        def update_metrics():
            while True:
                try:
                    if self.monitoring_active and self.monitor:
                        metrics = self.monitor.get_metrics()
                        
                        metrics_text = (
                            f"Screens: {metrics.get('screens_recorded', 0)} | "
                            f"Keystrokes: {metrics.get('keystrokes_recorded', 0)} | "
                            f"Mouse Events: {metrics.get('mouse_events_recorded', 0)} | "
                            f"App Switches: {metrics.get('app_switches_recorded', 0)} | "
                            f"File Events: {metrics.get('file_events_recorded', 0)}"
                        )
                        
                        self.metrics_label.config(text=f"Metrics: {metrics_text}")
                    
                    time.sleep(2)  # Update every 2 seconds
                    
                except Exception as e:
                    time.sleep(5)
        
        self.update_thread = threading.Thread(target=update_metrics, daemon=True)
        self.update_thread.start()
    
    def on_closing(self):
        """Handle window closing"""
        if self.monitoring_active and self.monitor:
            stop = messagebox.askyesno("Stop Monitoring?", 
                                      "Monitoring is active. Stop monitoring before closing?")
            if stop:
                self._stop_monitoring()
        
        self.destroy()


if __name__ == "__main__":
    app = FullMonitoringGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

