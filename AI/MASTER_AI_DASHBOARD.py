#!/usr/bin/env python3
"""
Master AI Dashboard - Centralized AI Development & Monitoring Hub
A simple, user-friendly interface to oversee all AI development and data
in the In-Office Installation folder.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import time
from pathlib import Path
import sys
import sqlite3
import json
import subprocess
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List

# Add AI directories to path for imports (package root + subdirectories)
ai_dir = Path(__file__).parent
sys.path.insert(0, str(ai_dir))
sys.path.insert(0, str(ai_dir / "monitoring"))
sys.path.insert(0, str(ai_dir / "training"))
sys.path.insert(0, str(ai_dir / "intelligence"))
sys.path.insert(0, str(ai_dir / "workflows"))
sys.path.insert(0, str(ai_dir / "scripts"))
# Also add _system for any remaining dependencies
sys.path.insert(0, str(Path(__file__).parent.parent / "_system"))

# Ensure browser monitoring bootstrap is activated (safe no-op if unavailable)
try:
    import auto_enable_browser_monitoring  # noqa: F401
except ImportError:
    pass

# Try to import AI components
try:
    from verify_ai_intelligence import AIIntelligenceDashboard
    AI_INTELLIGENCE_AVAILABLE = True
except ImportError:
    AI_INTELLIGENCE_AVAILABLE = False
    AIIntelligenceDashboard = None

try:
    from full_system_monitor import FullSystemMonitor, get_full_monitor, start_full_monitoring, stop_full_monitoring
    FULL_MONITOR_AVAILABLE = True
except ImportError:
    FULL_MONITOR_AVAILABLE = False
    FullSystemMonitor = None
    get_full_monitor = None

try:
    from browser_activity_monitor import get_browser_monitor
    BROWSER_MONITOR_AVAILABLE = True
except ImportError:
    BROWSER_MONITOR_AVAILABLE = False
    get_browser_monitor = None

try:
    from ai_training_integration import get_ai_training_integration
    AI_TRAINING_AVAILABLE = True
except ImportError:
    AI_TRAINING_AVAILABLE = False
    get_ai_training_integration = None

# Import Context Understanding Engine
try:
    from context_understanding_engine import ContextUnderstandingEngine
    CONTEXT_ENGINE_AVAILABLE = True
except ImportError:
    CONTEXT_ENGINE_AVAILABLE = False
    ContextUnderstandingEngine = None

# Import admin review and optimization analyzer
try:
    from admin_review_interface import AdminReviewInterface
    from ai_optimization_analyzer import AIOptimizationAnalyzer
    ADMIN_REVIEW_AVAILABLE = True
except ImportError:
    ADMIN_REVIEW_AVAILABLE = False
    AdminReviewInterface = None
    AIOptimizationAnalyzer = None

try:
    from workflow_compiler import WorkflowCompiler
    WORKFLOW_COMPILER_AVAILABLE = True
except ImportError:
    WORKFLOW_COMPILER_AVAILABLE = False
    WorkflowCompiler = None

LLM_SERVICE_AVAILABLE = False
LLMService = None
try:
    from llm.llm_service import LLMService  # Prefer package import to support relative imports
    LLM_SERVICE_AVAILABLE = True
except ImportError:
    try:
        from llm_service import LLMService  # Fallback for legacy environments
        LLM_SERVICE_AVAILABLE = True
    except ImportError:
        LLMService = None

# Full system monitoring functions are imported above
FULL_MONITORING_AVAILABLE = FULL_MONITOR_AVAILABLE

try:
    from workflow_training_manager import WorkflowTrainingManager, TrainingSessionMetadata
    WORKFLOW_TRAINING_AVAILABLE = True
except ImportError:
    WORKFLOW_TRAINING_AVAILABLE = False
    WorkflowTrainingManager = None  # type: ignore
    TrainingSessionMetadata = None  # type: ignore


class MasterAIDashboard:
    """Master AI Dashboard - Centralized AI Development & Monitoring"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Master AI Dashboard - AI Development & Monitoring Hub")
        # Increased window size to ensure all buttons are visible
        # Get screen dimensions and set window to 90% of screen size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(1400, 900)
        self.root.configure(bg="#f0f0f0")
        
        # Installation directory (parent of AI folder)
        self.installation_dir = Path(__file__).parent.parent
        
        # AI directory
        self.ai_dir = Path(__file__).parent
        
        # Data directories (updated paths)
        self.data_dir = self.ai_dir / "data"
        self.ai_intelligence_dir = self.ai_dir / "intelligence"
        self.ai_models_dir = self.ai_dir / "models"
        self.ai_analysis_reports_dir = self.ai_dir / "AI Analysis reports"
        self.ai_analysis_reports_dir.mkdir(exist_ok=True, mode=0o700)
        self.user_dir = self.installation_dir / "_user_directory"
        
        # Full system monitoring state
        self.full_monitor = None
        self.monitoring_active = False
        
        # Context Understanding Engine state
        self.context_engine = None
        
        # Initialize components
        self.ai_dashboard = None
        if AI_INTELLIGENCE_AVAILABLE:
            try:
                self.ai_dashboard = AIIntelligenceDashboard(self.installation_dir)
                if self.ai_dashboard:
                    secure_db = self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db"
                    if secure_db.exists():
                        self.ai_dashboard.data_dir = secure_db.parent
                        self.ai_dashboard.db_path = secure_db
            except Exception as exc:
                if hasattr(self, "logger") and self.logger:
                    self.logger.error(f"Unable to initialize AI dashboard: {exc}")
                self.ai_dashboard = None

        self.workflow_compiler = None
        if WORKFLOW_COMPILER_AVAILABLE:
            try:
                self.workflow_compiler = WorkflowCompiler(self.installation_dir)
            except Exception as e:
                print(f"Warning: unable to initialize workflow compiler: {e}")
                self.workflow_compiler = None

        self.llm_service = None
        self._llm_api_key_cache = None
        if LLM_SERVICE_AVAILABLE:
            try:
                self.llm_service = LLMService(self.installation_dir)
                self._llm_api_key_cache = self.llm_service.get_config().api_key
            except Exception as e:
                print(f"Warning: unable to initialize LLM service: {e}")
                self.llm_service = None
        self._latest_insight_cache = None

        self.optimization_analyzer = None
        if ADMIN_REVIEW_AVAILABLE and AIOptimizationAnalyzer:
            try:
                self.optimization_analyzer = AIOptimizationAnalyzer(self.installation_dir)
            except Exception as e:
                print(f"Warning: unable to initialize optimization analyzer: {e}")
                self.optimization_analyzer = None
        
        self.prototype_generation_available = False
        try:
            from automation_prototype_generator import AutomationPrototypeGenerator  # noqa: F401
            self.prototype_generation_available = True
        except ImportError:
            self.prototype_generation_available = False
        self.workflow_training_manager = None
        if WORKFLOW_TRAINING_AVAILABLE and WorkflowTrainingManager is not None:
            try:
                self.workflow_training_manager = WorkflowTrainingManager(self.installation_dir)
            except Exception as exc:
                print(f"Warning: unable to initialize workflow training manager: {exc}")
                self.workflow_training_manager = None
        self.training_session_metadata: Optional[TrainingSessionMetadata] = None
        
        # Refresh interval
        self.refresh_interval = 5  # seconds
        self.auto_refresh = True
        
        # Create GUI
        self._create_widgets()
        self._start_refresh_loop()
    
    def _create_widgets(self):
        """Create GUI widgets"""
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=80)
        header.pack(fill=tk.X)
        
        title = tk.Label(
            header,
            text="MASTER AI DASHBOARD",
            font=("Arial", 24, "bold"),
            bg="#2c3e50",
            fg="white",
            pady=20
        )
        title.pack()
        
        subtitle = tk.Label(
            header,
            text="Centralized AI Development & Monitoring Hub",
            font=("Arial", 12),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        subtitle.pack()
        
        # Main container
        main_container = tk.Frame(self.root, bg="#f0f0f0")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Status & Quick Stats (with scrolling if needed)
        left_panel_container = tk.Frame(main_container, bg="#f0f0f0")
        left_panel_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), expand=False)
        left_panel_container.config(width=350)
        
        # Create scrollable canvas for left panel
        left_canvas = tk.Canvas(left_panel_container, bg="#ffffff", highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_panel_container, orient="vertical", command=left_canvas.yview)
        left_panel = tk.Frame(left_canvas, bg="#ffffff", relief=tk.RAISED, bd=2)
        
        left_panel.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        left_panel.config(width=350)
        
        # System Status
        status_frame = ttk.LabelFrame(left_panel, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Checking system status...",
            font=("Arial", 11, "bold"),
            fg="blue",
            wraplength=320,
            justify=tk.LEFT
        )
        self.status_label.pack()
        
        # Quick Stats
        stats_frame = ttk.LabelFrame(left_panel, text="Quick Stats", padding=10)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(
            stats_frame,
            height=12,  # Reduced height to make room for buttons at bottom
            width=35,
            wrap=tk.WORD,
            font=("Arial", 9)
        )
        self.stats_text.pack(fill=tk.BOTH, expand=False)  # Changed to expand=False
        
        # Control buttons
        control_frame = tk.Frame(left_panel, bg="#ffffff")
        control_frame.pack(fill=tk.X, pady=10)
        
        refresh_btn = tk.Button(
            control_frame,
            text="Refresh Now",
            command=self._refresh_all,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2"
        )
        refresh_btn.pack(fill=tk.X, pady=2)
        
        export_btn = tk.Button(
            control_frame,
            text="Export Report",
            command=self._export_report,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2"
        )
        export_btn.pack(fill=tk.X, pady=2)
        
        auto_proto_btn = tk.Button(
            control_frame,
            text="Generate Automation Prototypes",
            command=self._generate_automation_prototypes,
            bg="#8e44ad",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        if not self.prototype_generation_available:
            auto_proto_btn.config(state=tk.DISABLED)
        auto_proto_btn.pack(fill=tk.X, pady=2)
        
        # Full System Monitoring Controls
        monitoring_control_frame = tk.LabelFrame(control_frame, text="System Monitoring", 
                                                font=("Arial", 10, "bold"), bg="#ffffff")
        monitoring_control_frame.pack(fill=tk.X, pady=5)
        
        # Start/Stop Monitoring button
        self.monitor_btn = tk.Button(
            monitoring_control_frame,
            text="Start Monitoring",
            command=self._toggle_monitoring,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.monitor_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Verify Monitoring Data button
        verify_btn = tk.Button(
            monitoring_control_frame,
            text="Verify Monitoring Data",
            command=self._verify_monitoring_data,
            bg="#3498db",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=5,
            pady=3,
            cursor="hand2"
        )
        verify_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Context Understanding Engine Controls
        context_control_frame = tk.LabelFrame(control_frame, text="Context Understanding", 
                                             font=("Arial", 10, "bold"), bg="#ffffff")
        context_control_frame.pack(fill=tk.X, pady=5)
        
        # Test Context Engine button
        test_context_btn = tk.Button(
            context_control_frame,
            text="Test Context Engine",
            command=self._test_context_engine,
            bg="#e67e22",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=5,
            pady=3,
            cursor="hand2"
        )
        test_context_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # AI Recommendations button
        ai_recs_btn = tk.Button(
            control_frame,
            text="📊 AI Recommendations",
            command=self._open_ai_recommendations,
            bg="#9b59b6",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2"
        )
        ai_recs_btn.pack(fill=tk.X, pady=2)
        
        train_btn = tk.Button(
            control_frame,
            text="🎬 Train New Workflow",
            command=self._start_workflow_training,
            bg="#16a085",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        train_btn.pack(fill=tk.X, pady=2)

        end_train_btn = tk.Button(
            control_frame,
            text="⛔ End Workflow Training",
            command=self._end_workflow_training,
            bg="#c0392b",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        end_train_btn.pack(fill=tk.X, pady=2)
        
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_check = tk.Checkbutton(
            control_frame,
            text="Auto-refresh (5s)",
            variable=self.auto_refresh_var,
            bg="#ffffff",
            font=("Arial", 9)
        )
        auto_refresh_check.pack(pady=5)
        
        # Right panel - Main content with tabs
        right_panel = tk.Frame(main_container, bg="#ffffff", relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipadx=10, ipady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Overview
        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="📊 Overview")
        
        self.overview_text = scrolledtext.ScrolledText(
            overview_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.overview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 2: Data Collection
        data_tab = ttk.Frame(notebook)
        notebook.add(data_tab, text="📥 Data Collection")
        
        self.data_text = scrolledtext.ScrolledText(
            data_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 3: AI Learning
        learning_tab = ttk.Frame(notebook)
        notebook.add(learning_tab, text="🧠 AI Learning")
        
        self.learning_text = scrolledtext.ScrolledText(
            learning_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.learning_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 4: Training Lab
        training_tab = ttk.Frame(notebook)
        notebook.add(training_tab, text="🧪 Training Lab")

        self.training_text = scrolledtext.ScrolledText(
            training_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.training_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 5: Monitoring
        monitoring_tab = ttk.Frame(notebook)
        notebook.add(monitoring_tab, text="👁️ Monitoring")
        
        self.monitoring_text = scrolledtext.ScrolledText(
            monitoring_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.monitoring_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 6: Intelligence
        intelligence_tab = ttk.Frame(notebook)
        notebook.add(intelligence_tab, text="🎯 Intelligence")
        
        self.intelligence_text = scrolledtext.ScrolledText(
            intelligence_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.intelligence_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 7: AI Recommendations
        ai_recs_tab = ttk.Frame(notebook)
        notebook.add(ai_recs_tab, text="📊 AI Recommendations")
        
        self.ai_recs_text = scrolledtext.ScrolledText(
            ai_recs_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.ai_recs_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 8: Users & Bots
        users_tab = ttk.Frame(notebook)
        notebook.add(users_tab, text="👥 Users & Bots")

        self.users_text = scrolledtext.ScrolledText(
            users_tab,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.users_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 9: Automation Executor
        automation_tab = ttk.Frame(notebook)
        notebook.add(automation_tab, text="🤖 Automation Executor")
        self._build_automation_tab(automation_tab)

        # Tab 10: Workflow Library (only if compiler available)
        workflows_tab = ttk.Frame(notebook)
        notebook.add(workflows_tab, text="🧠 Workflow Library")
        self._build_workflow_tab(workflows_tab)

        # Initial load
        self._update_workflow_library()

        llm_tab = ttk.Frame(notebook)
        notebook.add(llm_tab, text="🤖 LLM Assistant")
        self._build_llm_tab(llm_tab)
        self._refresh_llm_settings_ui()
    
    def _refresh_all(self):
        """Refresh all data"""
        try:
            # Update status
            self._update_status()
            
            # Update overview
            self._update_overview()
            
            # Update data collection
            self._update_data_collection()
            
            # Update AI learning
            self._update_ai_learning()

            # Update training lab
            self._update_training_lab()

            # Update monitoring
            self._update_monitoring()
            
            # Update intelligence
            self._update_intelligence()
            
            # Update AI recommendations
            self._update_ai_recommendations()
            
            # Update users & bots
            self._update_users_bots()

            # Update workflow library list (without recompiling)
            self._update_workflow_library(refresh_only=True)
            
        except Exception as e:
            self.status_label.config(
                text=f"[ERROR] {str(e)}",
                fg="red"
            )
    
    def _update_status(self):
        """Update system status"""
        try:
            status_lines = []
            status_lines.append("SYSTEM STATUS")
            status_lines.append("=" * 40)
            status_lines.append("")

            monitoring_flag = False
            data_collected = False
            last_activity = "N/A"

            # Check monitoring status
            if self.ai_dashboard:
                status = self.ai_dashboard.get_monitoring_status()
                if isinstance(status, dict):
                    monitoring_flag = status.get("monitoring_active", False)
                    data_collected = status.get("data_collected", False)
                    last_activity = status.get("last_activity") or "N/A"
            else:
                status_lines.append("⚠️ AI Dashboard: Not Available")

            # If monitoring was just started from this dashboard, reflect that immediately
            if self.monitoring_active and not monitoring_flag:
                monitoring_flag = True
                status_lines.append("✅ Monitoring: ACTIVE (Starting via dashboard)")
                status_lines.append("   Last Activity: Initializing...")
            elif monitoring_flag:
                status_lines.append("✅ Monitoring: ACTIVE")
                status_lines.append(f"   Last Activity: {last_activity}")
            else:
                status_lines.append("⚠️ Monitoring: INACTIVE")

            # Data collection indicator
            if data_collected or monitoring_flag:
                status_lines.append("✅ Data Collection: ACTIVE")
            else:
                status_lines.append("❌ Data Collection: NO DATA")

            status_lines.append("")

            # Check components
            status_lines.append("COMPONENTS:")
            if AI_INTELLIGENCE_AVAILABLE:
                status_lines.append("✅ AI Intelligence Dashboard")
            else:
                status_lines.append("❌ AI Intelligence Dashboard")

            if FULL_MONITOR_AVAILABLE:
                status_lines.append("✅ Full System Monitor")
            else:
                status_lines.append("❌ Full System Monitor")

            if BROWSER_MONITOR_AVAILABLE:
                status_lines.append("✅ Browser Activity Monitor")
            else:
                status_lines.append("❌ Browser Activity Monitor")

            if AI_TRAINING_AVAILABLE:
                status_lines.append("✅ AI Training Integration")
            else:
                status_lines.append("❌ AI Training Integration")

            # Determine label colour based on monitoring state
            label_colour = "green" if monitoring_flag else "orange"

            self.status_label.config(
                text="\n".join(status_lines[:10]),  # Show first 10 lines
                fg=label_colour
            )

        except Exception as e:
            self.status_label.config(
                text=f"[ERROR] {str(e)}",
                fg="red"
            )
    
    def _update_overview(self):
        """Update overview tab"""
        try:
            lines = []
            lines.append("MASTER AI DASHBOARD - OVERVIEW")
            lines.append("=" * 60)
            lines.append("")
            lines.append("Welcome to the Master AI Dashboard!")
            lines.append("This dashboard provides a centralized view of all AI")
            lines.append("development and monitoring activities in your system.")
            lines.append("")
            lines.append("=" * 60)
            lines.append("")
            
            # Get quick stats
            if self.ai_dashboard:
                metrics = self.ai_dashboard.get_data_collection_metrics()
                learning = self.ai_dashboard.get_ai_learning_metrics()
                
                lines.append("QUICK SUMMARY:")
                lines.append(f"  • Total Data Points: {metrics.get('total_data_points', 0):,}")
                lines.append(f"  • Patterns Extracted: {learning.get('patterns_extracted', 0):,}")
                lines.append(f"  • Workflows Identified: {learning.get('workflows_identified', 0):,}")
                lines.append(f"  • Learning Progress: {learning.get('learning_progress', 0)}%")
                lines.append("")
                
                insights = self.ai_dashboard.get_operational_insights()
                lines.append(f"  • Learning Velocity: {insights.get('learning_velocity', 'Unknown')}")
                lines.append("")
            
            lines.append("=" * 60)
            lines.append("")
            lines.append("TABS EXPLANATION:")
            lines.append("")
            lines.append("📥 Data Collection:")
            lines.append("   Shows what data is being collected from your activities")
            lines.append("")
            lines.append("🧠 AI Learning:")
            lines.append("   Shows how the AI is learning from your data")
            lines.append("")
            lines.append("👁️ Monitoring:")
            lines.append("   Shows monitoring system status and activity")
            lines.append("")
            lines.append("🎯 Intelligence:")
            lines.append("   Shows AI intelligence metrics and contributions")
            lines.append("")
            lines.append("👥 Users & Bots:")
            lines.append("   Shows registered users and bot activity")
            lines.append("")
            
            self.overview_text.delete(1.0, tk.END)
            self.overview_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.overview_text.delete(1.0, tk.END)
            self.overview_text.insert(1.0, f"Error loading overview: {e}")
    
    # ------------------------------------------------------------------
    # Monitoring datastore utilities
    # ------------------------------------------------------------------
    def _locate_full_monitor_database(self) -> Optional[Path]:
        """Return the most up-to-date full monitoring database."""
        candidates = [
            self.installation_dir / "_secure_data" / "full_monitoring" / "full_monitoring.db",
            self.data_dir / "full_monitoring" / "full_monitoring.db",
            self.installation_dir / "AI" / "data" / "full_monitoring" / "full_monitoring.db",
        ]

        best_path: Optional[Path] = None
        best_score = -1
        for path in candidates:
            if not path.exists():
                continue
            try:
                score = path.stat().st_size
            except OSError:
                score = 0
            if score > best_score:
                best_path = path
                best_score = score
        return best_path

    # ------------------------------------------------------------------
    # Browser telemetry utilities
    # ------------------------------------------------------------------
    def _locate_browser_database(self) -> Optional[Path]:
        """Return the first available browser activity database."""
        candidates = [
            self.data_dir / "browser_activity.db",
            self.installation_dir / "_secure_data" / "browser_activity.db",
            self.installation_dir / "AI" / "data" / "browser_activity.db",
        ]

        seen: set = set()
        for path in candidates:
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            if resolved in seen:
                continue
            seen.add(resolved)
            if path.exists():
                return path
        return None

    def _summarize_browser_activity(self, browser_db: Path) -> Tuple[int, Dict[str, int]]:
        """Return total events and per-table counts for the browser activity database."""
        counts: Dict[str, int] = {
            "page_navigations": 0,
            "element_interactions": 0,
            "form_field_interactions": 0,
        }

        try:
            with sqlite3.connect(browser_db) as conn:
                cursor = conn.cursor()
                for table in counts:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        value = cursor.fetchone()
                        counts[table] = int(value[0]) if value and value[0] is not None else 0
                    except sqlite3.Error:
                        counts[table] = 0
        except Exception as exc:
            if hasattr(self, "logger"):
                self.logger.error(f"Browser activity summary error: {exc}")
            counts = {k: 0 for k in counts}

        total_events = sum(counts.values())
        return total_events, counts

    def _update_data_collection(self):
        """Update data collection tab"""
        try:
            lines = []
            lines.append("DATA COLLECTION METRICS")
            lines.append("=" * 60)
            lines.append("")
            
            if self.ai_dashboard:
                metrics = self.ai_dashboard.get_data_collection_metrics()
                
                lines.append("TOTAL DATA POINTS:")
                lines.append(f"  {metrics.get('total_data_points', 0):,} total records")
                if getattr(self.ai_dashboard, 'db_path', None):
                    lines.append(f"  Database: {self.ai_dashboard.db_path}")
                lines.append("")
                lines.append("BREAKDOWN BY TYPE:")
                lines.append(f"  • Screen Recordings: {metrics.get('total_screens', 0):,}")
                lines.append(f"  • Keyboard Input: {metrics.get('total_keyboard', 0):,}")
                lines.append(f"  • Mouse Activity: {metrics.get('total_mouse', 0):,}")
                lines.append(f"  • Application Usage: {metrics.get('total_apps', 0):,}")
                lines.append(f"  • File Activity: {metrics.get('total_files', 0):,}")
                lines.append("")
                lines.append("COLLECTION STATISTICS:")
                lines.append(f"  • Sessions Recorded: {metrics.get('sessions_count', 0)}")
                lines.append(f"  • Data Size: {metrics.get('data_size_mb', 0)} MB")
                lines.append(f"  • Time Span: {metrics.get('time_span_days', 0)} days")
                if metrics.get('collection_rate_per_hour', 0) > 0:
                    lines.append(f"  • Collection Rate: {metrics.get('collection_rate_per_hour', 0):.1f} data points/hour")
                lines.append("")
            else:
                lines.append("AI Dashboard not available")
                lines.append("")
            
            # Check browser activity
            browser_db = self._locate_browser_database()
            if browser_db:
                total_events, breakdown = self._summarize_browser_activity(browser_db)
                lines.append("BROWSER ACTIVITY:")
                lines.append(f"  • Database Path: {browser_db}")
                lines.append(f"  • Total Browser Events: {total_events:,}")
                if total_events == 0:
                    lines.append("    (No browser telemetry recorded yet)")
                else:
                    if breakdown.get("page_navigations"):
                        lines.append(f"    - Page Navigations: {breakdown['page_navigations']:,}")
                    if breakdown.get("element_interactions"):
                        lines.append(f"    - Element Interactions: {breakdown['element_interactions']:,}")
                    if breakdown.get("form_field_interactions"):
                        lines.append(f"    - Form Field Interactions: {breakdown['form_field_interactions']:,}")
                lines.append("")
            else:
                lines.append("BROWSER ACTIVITY:")
                lines.append("  • No browser activity database detected.")
                lines.append("  • Launch bots from the Secure Launcher to start passive browser capture.")
                lines.append("")
            
            self.data_text.delete(1.0, tk.END)
            self.data_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.data_text.delete(1.0, tk.END)
            self.data_text.insert(1.0, f"Error loading data collection: {e}")
    
    def _update_ai_learning(self):
        """Update AI learning tab"""
        try:
            lines = []
            lines.append("AI LEARNING METRICS")
            lines.append("=" * 60)
            lines.append("")
            
            if self.ai_dashboard:
                learning = self.ai_dashboard.get_ai_learning_metrics()
                
                lines.append("LEARNING PROGRESS:")
                lines.append(f"  • Patterns Extracted: {learning.get('patterns_extracted', 0):,}")
                lines.append(f"  • Workflows Identified: {learning.get('workflows_identified', 0):,}")
                lines.append(f"  • Sequences Learned: {learning.get('sequences_learned', 0):,}")
                lines.append(f"  • Aggregated Patterns: {learning.get('pattern_count', 0):,}")
                if learning.get("last_pattern_seen"):
                    lines.append(f"  • Last Pattern Seen: {learning.get('last_pattern_seen')}")
                lines.append(f"  • Models Trained: {learning.get('models_trained', 0)}")
                lines.append(f"  • Learning Progress: {learning.get('learning_progress', 0)}%")
                lines.append("")
                
                if learning.get("last_analysis"):
                    lines.append(f"  • Last Analysis: {learning.get('last_analysis')}")
                if learning.get("last_training"):
                    lines.append(f"  • Last Training: {learning.get('last_training')}")
                if learning.get("training_accuracy") is not None:
                    lines.append(
                        "  • Training Quality: "
                        f"Accuracy {learning.get('training_accuracy'):.2%}, "
                        f"Precision {learning.get('training_precision'):.2%}, "
                        f"Recall {learning.get('training_recall'):.2%}"
                    )
                lines.append("")
                
                lines.append("WHAT THIS MEANS:")
                lines.append("  The AI is learning from your activities to understand")
                lines.append("  your workflows and patterns. This will enable the AI")
                lines.append("  to automate tasks and revolutionize operations.")
                lines.append("")
            else:
                lines.append("AI Dashboard not available")
                lines.append("")
            
            self.learning_text.delete(1.0, tk.END)
            self.learning_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.learning_text.delete(1.0, tk.END)
            self.learning_text.insert(1.0, f"Error loading AI learning: {e}")
    
    def _update_training_lab(self):
        """Update training lab tab with recent session summaries."""
        if not hasattr(self, "training_text"):
            return

        try:
            lines: List[str] = []
            lines.append("TRAINING LAB")
            lines.append("=" * 60)
            lines.append("")

            context_db = self.ai_intelligence_dir / "context_understanding.db"
            if not context_db.exists():
                lines.append("Context understanding database not found.")
                lines.append("Run monitoring + context engine to generate training data.")
                self.training_text.delete(1.0, tk.END)
                self.training_text.insert(1.0, "\n".join(lines))
                return

            with sqlite3.connect(context_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT session_id, MAX(timestamp) AS last_ts
                    FROM intent_understanding
                    GROUP BY session_id
                    ORDER BY last_ts DESC
                    LIMIT 5
                    """
                )
                sessions = cursor.fetchall()

                if not sessions:
                    lines.append("No processed sessions yet. Run bots or user sessions to collect data.")
                else:
                    lines.append("RECENT SESSIONS (latest first):")
                    for row in sessions:
                        session_id = row["session_id"] or "unknown"
                        last_ts = row["last_ts"] or "unknown"

                        cursor.execute(
                            "SELECT COUNT(*) FROM intent_understanding WHERE session_id = ?",
                            (session_id,),
                        )
                        intents = cursor.fetchone()[0]

                        cursor.execute(
                            "SELECT COUNT(*) FROM context_understanding WHERE session_id = ?",
                            (session_id,),
                        )
                        contexts = cursor.fetchone()[0]

                        cursor.execute(
                            "SELECT COUNT(*) FROM dependency_mapping WHERE session_id = ?",
                            (session_id,),
                        )
                        dependencies = cursor.fetchone()[0]

                        cursor.execute(
                            "SELECT COUNT(*) FROM goal_understanding WHERE session_id = ?",
                            (session_id,),
                        )
                        goals = cursor.fetchone()[0]

                        cursor.execute(
                            """
                            SELECT COUNT(*)
                            FROM context_understanding
                            WHERE session_id = ? AND context_type = 'state' AND context_value = 'logging'
                            """,
                            (session_id,),
                        )
                        bot_logs = cursor.fetchone()[0]

                        lines.append(f"• Session: {session_id}")
                        lines.append(f"  Last Activity: {last_ts}")
                        lines.append(
                            f"  Intents: {intents:,} | Contexts: {contexts:,} | Dependencies: {dependencies:,} | Goals: {goals:,}"
                        )
                        lines.append(f"  Bot Log Events Linked: {bot_logs:,}")
                        lines.append("")

            lines.append("NEXT STEPS:")
            lines.append("  1. Review session summaries above.")
            lines.append("  2. Mark intent/goal corrections in context DB (coming soon).")
            lines.append("  3. Use Workflow Library to simulate or replay captured runs.")

            # Pattern and training summaries
            if self.ai_dashboard:
                pattern_summary = self.ai_dashboard.get_pattern_summary()
                if pattern_summary:
                    lines.append("PATTERN STORE SUMMARY")
                    lines.append("-" * 60)
                    if pattern_summary.get("error"):
                        lines.append(f"  Error: {pattern_summary['error']}")
                    else:
                        lines.append(f"  • Aggregated Patterns: {pattern_summary.get('total_patterns', 0):,}")
                        lines.append(f"  • Sessions Represented: {pattern_summary.get('total_sessions', 0):,}")
                        if pattern_summary.get("last_seen"):
                            lines.append(f"  • Last Pattern Update: {pattern_summary['last_seen']}")
                    lines.append("")

                training_runs = self.ai_dashboard.get_recent_training_runs(limit=3)
                if training_runs:
                    lines.append("RECENT TRAINING RUNS")
                    lines.append("-" * 60)
                    for run in training_runs:
                        lines.append(f"• Completed: {run.get('completed_at')}")
                        lines.append(
                            f"  Patterns: {run.get('patterns_processed', 0):,} (+{run.get('new_patterns', 0):,} new)"
                        )
                        lines.append(
                            "  Metrics: "
                            f"Accuracy {run.get('accuracy', 0.0):.2%}, "
                            f"Precision {run.get('precision', 0.0):.2%}, "
                            f"Recall {run.get('recall', 0.0):.2%}"
                        )
                        if run.get("notes"):
                            lines.append(f"  Notes: {run['notes']}")
                        lines.append("")

            self.training_text.delete(1.0, tk.END)
            self.training_text.insert(1.0, "\n".join(lines))

        except Exception as e:
            self.training_text.delete(1.0, tk.END)
            self.training_text.insert(1.0, f"Error loading training lab: {e}")
    
    def _update_monitoring(self):
        """Update monitoring tab"""
        try:
            lines = []
            lines.append("MONITORING SYSTEM STATUS")
            lines.append("=" * 60)
            lines.append("")
            
            # Check actual monitor instance state (most reliable)
            # ALWAYS check global instance first (most reliable source of truth)
            actual_monitor_active = False
            monitor_instance = None
            
            # Check global instance first (most reliable - this is the actual running instance)
            if get_full_monitor:
                try:
                    monitor_instance = get_full_monitor(self.installation_dir, user_consent=True)
                    if monitor_instance:
                        actual_monitor_active = monitor_instance.monitoring_active
                        # Update our stored instance to match
                        self.full_monitor = monitor_instance
                        if actual_monitor_active:
                            lines.append(f"   • Monitor Instance: Found (global) - ACTIVE")
                except Exception as e:
                    self.logger.error(f"Error getting global monitor: {e}")
            
            # Fallback to stored instance if global check failed
            if not monitor_instance and self.full_monitor:
                try:
                    actual_monitor_active = self.full_monitor.monitoring_active
                    monitor_instance = self.full_monitor
                    if actual_monitor_active:
                        lines.append(f"   • Monitor Instance: Found (stored) - ACTIVE")
                except Exception as e:
                    self.logger.error(f"Error checking stored monitor: {e}")
            
            # Also check button state
            is_button_active = self.monitoring_active
            
            # Full system monitoring - locate the most current database
            full_monitor_db = self._locate_full_monitor_database()
            if full_monitor_db and full_monitor_db.exists():
                try:
                    conn = sqlite3.connect(full_monitor_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM screen_recordings")
                    screen_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM keyboard_input")
                    keyboard_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM mouse_activity")
                    mouse_count = cursor.fetchone()[0]
                    
                    # Check if monitoring is currently active (data in last 2 minutes - more accurate)
                    cutoff = (datetime.now() - timedelta(minutes=2)).isoformat()
                    cursor.execute("""
                        SELECT COUNT(*) FROM screen_recordings WHERE timestamp > ?
                    """, (cutoff,))
                    recent_count = cursor.fetchone()[0]
                    
                    # Also check for very recent data (last 30 seconds) as stronger indicator
                    very_recent_cutoff = (datetime.now() - timedelta(seconds=30)).isoformat()
                    cursor.execute("""
                        SELECT COUNT(*) FROM screen_recordings WHERE timestamp > ?
                    """, (very_recent_cutoff,))
                    very_recent_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    # Determine status: check actual monitor state FIRST, then recent data, then button state
                    # Use recent data as strong indicator even if instance check fails
                    if actual_monitor_active or very_recent_count > 0 or (recent_count > 0 and is_button_active):
                        lines.append("✅ Full System Monitoring: ACTIVE (Currently Recording)")
                        if actual_monitor_active:
                            lines.append("   • Status: Monitor instance is active")
                        elif very_recent_count > 0:
                            lines.append(f"   • Status: Very recent data detected ({very_recent_count:,} screens in last 30 sec)")
                        elif recent_count > 0:
                            lines.append(f"   • Status: Recent data detected ({recent_count:,} screens in last 2 min)")
                        if is_button_active:
                            lines.append("   • Started from: Master AI Dashboard")
                        if monitor_instance:
                            lines.append(f"   • Session ID: {monitor_instance.session_id}")
                    elif is_button_active:
                        # Button is active but monitor state not detected - show as starting
                        lines.append("⚠️ Full System Monitoring: STARTING (Button active, waiting for data...)")
                        lines.append("   • Status: Monitoring started but no data recorded yet")
                        lines.append("   • This is normal if monitoring just started")
                        if self.full_monitor:
                            lines.append(f"   • Monitor Instance: {type(self.full_monitor).__name__}")
                            lines.append(f"   • Monitor State: monitoring_active = {self.full_monitor.monitoring_active}")
                            if hasattr(self.full_monitor, 'session_id'):
                                lines.append(f"   • Session ID: {self.full_monitor.session_id}")
                    elif recent_count > 0:
                        lines.append("✅ Full System Monitoring: ACTIVE (Currently Recording)")
                        lines.append(f"   • Status: Recent data detected ({recent_count:,} screens in last 2 min)")
                    else:
                        lines.append("⚠️ Full System Monitoring: INACTIVE (Data exists but not currently recording)")
                    
                    lines.append(f"   • Total Screens: {screen_count:,}")
                    lines.append(f"   • Total Keyboard: {keyboard_count:,}")
                    lines.append(f"   • Total Mouse: {mouse_count:,}")
                    lines.append(f"   • Database: {full_monitor_db}")
                    lines.append(f"   • Recent Activity (last 2 min): {recent_count:,} screens")
                    lines.append("")
                    lines.append("   Note: Use 'Start Monitoring' button in left panel to start/stop recording")
                except Exception as e:
                    lines.append(f"⚠️ Full System Monitoring: Error checking status ({e})")
            else:
                # No database - check if monitoring is supposed to be active
                if actual_monitor_active or is_button_active:
                    lines.append("⚠️ Full System Monitoring: STARTING (No database yet)")
                    lines.append("   • Status: Monitoring started but database not created yet")
                    lines.append("   • This is normal if monitoring just started")
                else:
                    lines.append("❌ Full System Monitoring: NOT ACTIVE (No database found)")
            lines.append("")
            
            # Browser monitoring
            browser_db = self._locate_browser_database()
            if browser_db:
                total_events, breakdown = self._summarize_browser_activity(browser_db)
                status_icon = "✅" if total_events > 0 else "⚠️"
                status_label = "ACTIVE" if total_events > 0 else "NO RECENT EVENTS"
                lines.append(f"{status_icon} Browser Activity Monitoring: {status_label}")
                lines.append(f"   • Database Path: {browser_db}")
                lines.append(f"   • Total Browser Events: {total_events:,}")
                if total_events > 0:
                    if breakdown.get("page_navigations"):
                        lines.append(f"   • Page Navigations: {breakdown['page_navigations']:,}")
                    if breakdown.get("element_interactions"):
                        lines.append(f"   • Element Interactions: {breakdown['element_interactions']:,}")
                    if breakdown.get("form_field_interactions"):
                        lines.append(f"   • Form Field Interactions: {breakdown['form_field_interactions']:,}")
                else:
                    lines.append("   • No browser telemetry recorded in the last runs.")
                    lines.append("   • Ensure bots launch from the Secure Launcher to attach the browser monitor.")
            else:
                lines.append("❌ Browser Activity Monitoring: NOT ACTIVE (database not found)")
                lines.append("   • Launch bots via the Secure Launcher to initialize passive browser capture.")
            lines.append("")
            
            self.monitoring_text.delete(1.0, tk.END)
            self.monitoring_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.monitoring_text.delete(1.0, tk.END)
            self.monitoring_text.insert(1.0, f"Error loading monitoring: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_intelligence(self):
        """Update intelligence tab"""
        try:
            lines = []
            lines.append("AI INTELLIGENCE STATUS")
            lines.append("=" * 60)
            lines.append("")
            
            # Context Understanding Engine Status (NEW)
            lines.append("CONTEXT UNDERSTANDING ENGINE")
            lines.append("-" * 60)
            lines.append("")
            
            if CONTEXT_ENGINE_AVAILABLE:
                try:
                    # Initialize engine if not already done
                    if not self.context_engine:
                        self.context_engine = ContextUnderstandingEngine(self.installation_dir)
                    
                    # Check database
                    context_db = self.ai_intelligence_dir / "context_understanding.db"
                    if context_db.exists():
                        try:
                            conn = sqlite3.connect(context_db)
                            cursor = conn.cursor()
                            
                            # Check intent understanding
                            cursor.execute("SELECT COUNT(*) FROM intent_understanding")
                            intent_count = cursor.fetchone()[0]
                            
                            # Check context understanding
                            cursor.execute("SELECT COUNT(*) FROM context_understanding")
                            context_count = cursor.fetchone()[0]
                            
                            # Check dependency mapping
                            cursor.execute("SELECT COUNT(*) FROM dependency_mapping")
                            dependency_count = cursor.fetchone()[0]
                            
                            # Check goal understanding
                            cursor.execute("SELECT COUNT(*) FROM goal_understanding")
                            goal_count = cursor.fetchone()[0]
                            
                            # Check workflow understanding
                            cursor.execute("SELECT COUNT(*) FROM workflow_understanding")
                            workflow_count = cursor.fetchone()[0]
                            
                            # Check recent processing (last 24 hours)
                            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                            cursor.execute("""
                                SELECT COUNT(DISTINCT session_id) FROM intent_understanding 
                                WHERE timestamp > ?
                            """, (cutoff,))
                            recent_sessions = cursor.fetchone()[0]
                            
                            conn.close()
                            
                            # Determine status
                            if recent_sessions > 0:
                                lines.append("✅ Context Understanding Engine: OPERATIONAL")
                                lines.append(f"   • Status: Processing sessions actively")
                                lines.append(f"   • Recent Sessions (last 24h): {recent_sessions}")
                            elif intent_count > 0 or context_count > 0 or dependency_count > 0:
                                lines.append("⚠️ Context Understanding Engine: IDLE")
                                lines.append("   • Status: Has processed data but not recently")
                                lines.append("   • Last processing: More than 24 hours ago")
                            else:
                                lines.append("⚠️ Context Understanding Engine: READY (No data yet)")
                                lines.append("   • Status: Waiting for monitoring data")
                                lines.append("   • Will process sessions automatically when monitoring is active")
                            
                            lines.append("")
                            lines.append("   Understanding Statistics:")
                            lines.append(f"   • Intent Classifications: {intent_count:,}")
                            lines.append(f"   • Context Extractions: {context_count:,}")
                            lines.append(f"   • Dependency Mappings: {dependency_count:,}")
                            lines.append(f"   • Goal Identifications: {goal_count:,}")
                            lines.append(f"   • Workflow Understandings: {workflow_count:,}")
                            
                        except Exception as e:
                            lines.append(f"⚠️ Context Understanding Engine: ERROR")
                            lines.append(f"   • Error checking database: {e}")
                    else:
                        lines.append("⚠️ Context Understanding Engine: READY (No database yet)")
                        lines.append("   • Status: Waiting for first session to process")
                        lines.append("   • Database will be created automatically")
                    
                    lines.append("")
                    lines.append("   Test File Location:")
                    lines.append("   • AI/intelligence/test_context_understanding.py")
                    lines.append("")
                    
                except Exception as e:
                    lines.append(f"⚠️ Context Understanding Engine: ERROR")
                    lines.append(f"   • Error initializing: {e}")
                    lines.append("")
            else:
                lines.append("❌ Context Understanding Engine: NOT AVAILABLE")
                lines.append("   • Module not found or not importable")
                lines.append("")
            
            lines.append("=" * 60)
            lines.append("")
            
            if self.ai_dashboard:
                insights = self.ai_dashboard.get_operational_insights()
                learning = self.ai_dashboard.get_ai_learning_metrics()
                metrics = self.ai_dashboard.get_data_collection_metrics()
                
                lines.append(f"LEARNING VELOCITY: {insights.get('learning_velocity', 'Unknown')}")
                lines.append("")
                
                # Calculate contribution score
                contribution_score = 0
                contribution_factors = []
                
                if metrics.get('total_data_points', 0) > 10000:
                    contribution_score += 30
                    contribution_factors.append("✅ High data volume collected")
                elif metrics.get('total_data_points', 0) > 1000:
                    contribution_score += 15
                    contribution_factors.append("✅ Moderate data volume collected")
                
                if learning.get('patterns_extracted', 0) > 100:
                    contribution_score += 25
                    contribution_factors.append("✅ Significant patterns extracted")
                elif learning.get('patterns_extracted', 0) > 10:
                    contribution_score += 10
                    contribution_factors.append("✅ Patterns being identified")
                
                if learning.get('workflows_identified', 0) > 10:
                    contribution_score += 25
                    contribution_factors.append("✅ Workflows being learned")
                elif learning.get('workflows_identified', 0) > 0:
                    contribution_score += 10
                    contribution_factors.append("✅ Workflow identification started")
                
                if learning.get('models_trained', 0) > 0:
                    contribution_score += 20
                    contribution_factors.append("✅ AI models actively training")
                
                # Add Context Engine to contribution score
                if CONTEXT_ENGINE_AVAILABLE and self.context_engine:
                    context_db = self.ai_intelligence_dir / "context_understanding.db"
                    if context_db.exists():
                        try:
                            conn = sqlite3.connect(context_db)
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM intent_understanding")
                            intent_count = cursor.fetchone()[0]
                            conn.close()
                            
                            if intent_count > 1000:
                                contribution_score += 15
                                contribution_factors.append("✅ Context Understanding Engine processing actively")
                            elif intent_count > 100:
                                contribution_score += 10
                                contribution_factors.append("✅ Context Understanding Engine operational")
                        except:
                            pass
                
                lines.append(f"CONTRIBUTION SCORE: {contribution_score}/100")
                lines.append("")
                lines.append("ACTIVE LEARNING FACTORS:")
                for factor in contribution_factors:
                    lines.append(f"  {factor}")
                lines.append("")
                
                lines.append("MOST USED APPLICATIONS:")
                for app in insights.get("most_used_apps", [])[:5]:
                    lines.append(f"  • {app.get('app', 'Unknown')}: {app.get('usage_count', 0):,} uses")
                lines.append("")
                
                lines.append("SYSTEM STATUS:")
                lines.append("  Building Generative Intelligence")
                lines.append("  The system is learning your workflows to create")
                lines.append("  an autonomous AI that will revolutionize operations.")
                lines.append("")
            else:
                lines.append("AI Dashboard not available")
                lines.append("")
            
            self.intelligence_text.delete(1.0, tk.END)
            self.intelligence_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.intelligence_text.delete(1.0, tk.END)
            self.intelligence_text.insert(1.0, f"Error loading intelligence: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_users_bots(self):
        """Update users & bots tab"""
        try:
            lines = []
            lines.append("USERS & BOTS")
            lines.append("=" * 60)
            lines.append("")
            
            # Check user directory
            user_db = self.user_dir / "user_directory.db"
            if user_db.exists():
                try:
                    conn = sqlite3.connect(user_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, computer_name, registration_date FROM users")
                    users = cursor.fetchall()
                    conn.close()
                    
                    lines.append(f"REGISTERED USERS: {len(users)}")
                    lines.append("")
                    for name, computer, date in users:
                        lines.append(f"  • {name} ({computer})")
                        lines.append(f"    Registered: {date}")
                        lines.append("")
                except:
                    lines.append("Could not load user data")
                    lines.append("")
            else:
                lines.append("No user directory found")
                lines.append("")
            
            # Check bot activity (simplified)
            lines.append("BOT ACTIVITY:")
            lines.append("  Check individual bot logs for detailed activity")
            lines.append("")
            
            self.users_text.delete(1.0, tk.END)
            self.users_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.users_text.delete(1.0, tk.END)
            self.users_text.insert(1.0, f"Error loading users & bots: {e}")
    
    def _update_quick_stats(self):
        """Update quick stats in left panel"""
        try:
            lines = []
            
            if self.ai_dashboard:
                metrics = self.ai_dashboard.get_data_collection_metrics()
                learning = self.ai_dashboard.get_ai_learning_metrics()
                
                lines.append("QUICK STATS")
                lines.append("=" * 30)
                lines.append("")
                lines.append(f"Data Points:")
                lines.append(f"  {metrics.get('total_data_points', 0):,}")
                lines.append("")
                lines.append(f"Patterns:")
                lines.append(f"  {learning.get('patterns_extracted', 0):,}")
                lines.append("")
                lines.append(f"Workflows:")
                lines.append(f"  {learning.get('workflows_identified', 0):,}")
                lines.append("")
                lines.append(f"Progress:")
                lines.append(f"  {learning.get('learning_progress', 0)}%")
                lines.append("")
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, "\n".join(lines))
            
        except Exception as e:
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, f"Error: {e}")
    
    def _export_report(self):
        """Export full report"""
        try:
            if self.ai_dashboard:
                report = self.ai_dashboard.generate_report()
                # Save to AI Analysis reports folder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = self.ai_analysis_reports_dir / f"ai_intelligence_report_{timestamp}.txt"
                report_file.parent.mkdir(exist_ok=True, parents=True)
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                messagebox.showinfo(
                    "Report Exported",
                    f"Report saved to:\n{report_file}"
                )
            else:
                messagebox.showwarning(
                    "Export Unavailable",
                    "AI Dashboard not available. Cannot generate report."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export report: {e}")
    
    def _launch_full_monitoring(self):
        """Launch full system monitoring GUI"""
        try:
            # Check if full monitoring system exists (now in AI/monitoring)
            monitoring_dir = self.ai_dir / "monitoring"
            full_monitoring_bat = monitoring_dir / "launch_full_monitoring.bat"
            full_monitoring_py = monitoring_dir / "full_monitoring_gui.py"
            
            if full_monitoring_bat.exists():
                # Launch via batch file (recommended)
                subprocess.Popen(
                    [str(full_monitoring_bat)],
                    cwd=str(monitoring_dir),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                messagebox.showinfo(
                    "Full System Monitoring",
                    "Full System Monitoring GUI is launching...\n\n"
                    "This will open a separate window where you can:\n"
                    "• Start/Stop monitoring\n"
                    "• Configure recording options\n"
                    "• View real-time metrics"
                )
            elif full_monitoring_py.exists():
                # Launch via Python script directly
                python_exe = sys.executable
                subprocess.Popen(
                    [python_exe, str(full_monitoring_py)],
                    cwd=str(monitoring_dir),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                messagebox.showinfo(
                    "Full System Monitoring",
                    "Full System Monitoring GUI is launching...\n\n"
                    "This will open a separate window where you can:\n"
                    "• Start/Stop monitoring\n"
                    "• Configure recording options\n"
                    "• View real-time metrics"
                )
            else:
                messagebox.showerror(
                    "Not Found",
                    "Full System Monitoring system not found.\n\n"
                    f"Expected location: {full_monitoring_bat}\n"
                    f"or: {full_monitoring_py}\n\n"
                    "Please ensure the full monitoring system is installed."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to launch Full System Monitoring:\n{e}"
            )
    
    def _verify_monitoring_data(self):
        """Launch monitoring data verification tool"""
        try:
            monitoring_dir = self.ai_dir / "monitoring"
            verify_script = monitoring_dir / "verify_monitoring_data.py"
            verify_bat = monitoring_dir / "VERIFY_MONITORING.bat"
            
            if verify_bat.exists():
                # Launch via batch file (recommended)
                subprocess.Popen(
                    [str(verify_bat)],
                    cwd=str(monitoring_dir),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                messagebox.showinfo(
                    "Verify Monitoring Data",
                    "Monitoring verification tool is launching...\n\n"
                    "This will check:\n"
                    "• If monitoring database exists\n"
                    "• If data is being recorded\n"
                    "• Recent activity (last 5 minutes)\n"
                    "• Dependencies status"
                )
            elif verify_script.exists():
                # Launch via Python script directly
                python_exe = sys.executable
                subprocess.Popen(
                    [python_exe, str(verify_script)],
                    cwd=str(monitoring_dir),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                messagebox.showinfo(
                    "Verify Monitoring Data",
                    "Monitoring verification tool is launching...\n\n"
                    "This will check:\n"
                    "• If monitoring database exists\n"
                    "• If data is being recorded\n"
                    "• Recent activity (last 5 minutes)\n"
                    "• Dependencies status"
                )
            else:
                messagebox.showerror(
                    "Not Found",
                    "Monitoring verification tool not found.\n\n"
                    f"Expected location: {verify_script}\n\n"
                    "Please ensure the verification tool is installed."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to launch verification tool:\n{e}"
            )
    
    def _test_context_engine(self):
        """Launch Context Understanding Engine test"""
        try:
            intelligence_dir = self.ai_dir / "intelligence"
            # Try GUI version first, fallback to console version
            test_script_gui = intelligence_dir / "test_context_understanding_gui.py"
            test_script = intelligence_dir / "test_context_understanding.py"
            
            python_exe = sys.executable
            
            if test_script_gui.exists():
                # Launch GUI version (shows results in window)
                subprocess.Popen(
                    [python_exe, str(test_script_gui)],
                    cwd=str(intelligence_dir)
                )
                messagebox.showinfo(
                    "Test Context Engine",
                    "Context Understanding Engine test is launching...\n\n"
                    "A window will appear showing test results.\n\n"
                    "This will check:\n"
                    "• If Context Engine is initialized\n"
                    "• If database exists\n"
                    "• If sessions are being processed\n"
                    "• Understanding statistics\n"
                    "• Recent processing activity"
                )
            elif test_script.exists():
                # Fallback to console version (but show window)
                subprocess.Popen(
                    [python_exe, str(test_script)],
                    cwd=str(intelligence_dir)
                    # Note: No CREATE_NO_WINDOW flag so console window will appear
                )
                messagebox.showinfo(
                    "Test Context Engine",
                    "Context Understanding Engine test is launching...\n\n"
                    "A console window will appear showing test results.\n\n"
                    "This will check:\n"
                    "• If Context Engine is initialized\n"
                    "• If database exists\n"
                    "• If sessions are being processed\n"
                    "• Understanding statistics\n"
                    "• Recent processing activity"
                )
            else:
                messagebox.showerror(
                    "Not Found",
                    "Context Engine test file not found.\n\n"
                    f"Expected location: {test_script_gui} or {test_script}\n\n"
                    "Please ensure the test file is installed."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to launch Context Engine test:\n{e}"
            )
    
    def _toggle_monitoring(self):
        """Toggle full system monitoring on/off"""
        try:
            if not FULL_MONITORING_AVAILABLE:
                messagebox.showerror(
                    "Not Available",
                    "Full system monitoring is not available.\n\n"
                    "Please ensure all dependencies are installed."
                )
                return
            
            # Get current monitor instance to check actual state
            current_monitor = None
            if get_full_monitor:
                try:
                    current_monitor = get_full_monitor(self.installation_dir, user_consent=True)
                except:
                    pass
            
            # Check actual monitor state (not just our internal flag)
            is_actually_active = current_monitor and current_monitor.monitoring_active if current_monitor else False
            
            if is_actually_active or self.monitoring_active:
                self.monitor_btn.config(text="Stopping...", state=tk.DISABLED)

                def do_stop():
                    try:
                        if stop_full_monitoring:
                            stop_full_monitoring()
                    finally:
                        self.full_monitor = None
                        self.monitoring_active = False
                        self.root.after(0, self._on_monitoring_stopped)

                threading.Thread(target=do_stop, daemon=True).start()
            else:
                # Start monitoring
                if start_full_monitoring:
                    # Get monitor instance first to configure it
                    if get_full_monitor:
                        self.full_monitor = get_full_monitor(self.installation_dir, user_consent=True)
                        if self.full_monitor:
                            # Configure what to record (before starting)
                            self.full_monitor.record_screen = True
                            self.full_monitor.record_keyboard = True
                            self.full_monitor.record_mouse = True
                            self.full_monitor.record_apps = True
                            self.full_monitor.record_files = True
                            # Start monitoring
                            self.full_monitor.start_monitoring()
                            
                            # Verify it actually started
                            if self.full_monitor.monitoring_active:
                                self.monitoring_active = True
                                self.monitor_btn.config(text="Stop Monitoring", bg="#e74c3c", state=tk.NORMAL)
                                messagebox.showinfo("Monitoring Started", "Full system monitoring has been started.")
                                # Force refresh of monitoring tab immediately (multiple times to ensure update)
                                self.root.after(100, self._update_monitoring)  # After 100ms
                                self.root.after(500, self._update_monitoring)  # After 500ms
                                self.root.after(2000, self._update_monitoring)  # After 2 seconds
                                self._update_monitoring()  # Immediate
                            else:
                                messagebox.showerror("Error", "Monitoring failed to start. Check dependencies.")
                                return
                    else:
                        # Fallback: use start_full_monitoring directly
                        self.full_monitor = start_full_monitoring(
                            installation_dir=self.installation_dir,
                            user_consent=True
                        )
                        if self.full_monitor and self.full_monitor.monitoring_active:
                            self.monitoring_active = True
                            self.monitor_btn.config(text="Stop Monitoring", bg="#e74c3c", state=tk.NORMAL)
                            messagebox.showinfo("Monitoring Started", "Full system monitoring has been started.")
                            # Force refresh of monitoring tab immediately (multiple times to ensure update)
                            self.root.after(100, self._update_monitoring)  # After 100ms
                            self.root.after(500, self._update_monitoring)  # After 500ms
                            self.root.after(2000, self._update_monitoring)  # After 2 seconds
                            self._update_monitoring()  # Immediate
                        else:
                            messagebox.showerror("Error", "Monitoring failed to start. Check dependencies.")
                            return
                else:
                    messagebox.showerror("Error", "Monitoring functions not available.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle monitoring:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _on_monitoring_stopped(self):
        try:
            self.monitor_btn.config(text="Start Monitoring", bg="#27ae60", state=tk.NORMAL)
            messagebox.showinfo("Monitoring Stopped", "Full system monitoring has been stopped.")
            self._update_monitoring()
            self._update_workflow_library(refresh_only=True)
        except Exception:
            pass

    def _open_ai_recommendations(self):
        """Open AI recommendations interface"""
        try:
            if ADMIN_REVIEW_AVAILABLE and AdminReviewInterface:
                AdminReviewInterface(self.root, self.installation_dir)
            else:
                messagebox.showerror(
                    "Not Available",
                    "AI Recommendations interface is not available.\n\n"
                    "Please ensure admin_review_interface.py is installed."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open AI recommendations:\n{e}")
    
    def _update_ai_recommendations(self):
        """Update AI recommendations tab"""
        try:
            lines = []
            lines.append("AI OPTIMIZATION RECOMMENDATIONS")
            lines.append("=" * 60)
            lines.append("")
            
            if self.optimization_analyzer:
                try:
                    recommendations = self.optimization_analyzer.get_pending_recommendations()
                    
                    if recommendations:
                        lines.append(f"PENDING RECOMMENDATIONS: {len(recommendations)}")
                        lines.append("")
                        
                        for i, rec in enumerate(recommendations[:10], 1):  # Show first 10
                            lines.append(f"{i}. {rec.get('title', 'Untitled')}")
                            lines.append(f"   Type: {rec.get('recommendation_type', 'Unknown')}")
                            lines.append(f"   Complexity: {rec.get('implementation_complexity', 'Unknown')}")
                            lines.append(f"   Confidence: {rec.get('confidence_score', 0):.2%}")
                            lines.append(f"   Status: {rec.get('status', 'pending')}")
                            if rec.get('description'):
                                desc = rec.get('description', '')[:100]
                                lines.append(f"   Description: {desc}...")
                            lines.append("")
                        
                        if len(recommendations) > 10:
                            lines.append(f"... and {len(recommendations) - 10} more recommendations")
                            lines.append("")
                        
                        lines.append("Click '📊 AI Recommendations' button to view and manage all recommendations")
                    else:
                        lines.append("No pending recommendations at this time.")
                        lines.append("")
                        lines.append("The AI will generate recommendations as it learns from usage patterns.")
                except Exception as e:
                    lines.append(f"Error loading recommendations: {e}")
            else:
                lines.append("AI Optimization Analyzer not available.")
                lines.append("")
                lines.append("Recommendations will appear here once the analyzer is active.")
            
            lines.append("")
            lines.append("GPT INSIGHTS")
            lines.append("-" * 60)

            if self.llm_service and self.llm_service.is_configured():
                insight = self._get_llm_insight()
                if insight and insight.get("summary"):
                    summary_lines = insight["summary"].splitlines()
                    if insight.get("generated_at"):
                        lines.append(f"Generated: {insight['generated_at']}")
                    if insight.get("model"):
                        lines.append(f"Model: {insight['model']}")
                    lines.append("")
                    lines.extend(summary_lines)
                else:
                    lines.append("No GPT insight available yet. Run monitoring for more data.")
            else:
                lines.append("LLM service not configured. Open the LLM Assistant tab to add your API key.")
            
            lines.append("")
            lines.append("AUTOMATION PROTOTYPES")
            lines.append("-" * 60)
            if self.ai_dashboard:
                prototypes = self.ai_dashboard.list_automation_prototypes()
                if prototypes:
                    for proto in prototypes[:10]:
                        lines.append(f"• Pattern: {proto.get('pattern_hash')}")
                        lines.append(f"  Type: {proto.get('pattern_type', 'unknown')}")
                        freq = proto.get('frequency')
                        if freq is not None:
                            lines.append(f"  Frequency: {freq}")
                        if proto.get('last_seen'):
                            lines.append(f"  Last Seen: {proto['last_seen']}")
                        if proto.get('path'):
                            lines.append(f"  Bundle: {proto['path']}")
                        if proto.get('gpt_report'):
                            lines.append(f"  GPT Report: {proto['gpt_report']}")
                        lines.append("")
                    if len(prototypes) > 10:
                        lines.append(f"... and {len(prototypes) - 10} more prototypes")
                        lines.append("")
                else:
                    lines.append("No prototypes generated yet. Click 'Generate Automation Prototypes' to create them once patterns are ready.")
            else:
                lines.append("Automation prototypes unavailable until AI intelligence dashboard initializes.")
            
            self.ai_recs_text.delete(1.0, tk.END)
            self.ai_recs_text.insert(1.0, "\n".join(lines))
        except Exception as e:
            self.ai_recs_text.delete(1.0, tk.END)
            self.ai_recs_text.insert(1.0, f"Error loading AI recommendations: {e}")
    
    # ------------------------------------------------------------------
    # Workflow Library
    # ------------------------------------------------------------------
    def _build_workflow_tab(self, tab):
        tab.columnconfigure(0, weight=1, minsize=280)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        left_frame = tk.Frame(tab, bg="#ffffff", bd=1, relief=tk.SUNKEN)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=5)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        header = tk.Label(left_frame, text="Compiled Workflows", font=("Arial", 12, "bold"), bg="#ffffff")
        header.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        self.workflow_listbox = tk.Listbox(left_frame, exportselection=False, height=20)
        self.workflow_listbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.workflow_listbox.bind("<<ListboxSelect>>", self._on_workflow_select)

        button_frame = tk.Frame(left_frame, bg="#ffffff")
        button_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        button_frame.columnconfigure((0, 1), weight=1)

        compile_btn = tk.Button(
            button_frame,
            text="Compile Workflows",
            command=self._compile_workflows,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=6,
            pady=4,
            cursor="hand2"
        )
        compile_btn.grid(row=0, column=0, padx=4, pady=2, sticky="ew")

        simulate_btn = tk.Button(
            button_frame,
            text="Simulate Workflow",
            command=self._simulate_selected_workflow,
            bg="#27ae60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=6,
            pady=4,
            cursor="hand2"
        )
        simulate_btn.grid(row=0, column=1, padx=4, pady=2, sticky="ew")

        refresh_btn = tk.Button(
            button_frame,
            text="Refresh List",
            command=self._update_workflow_library,
            bg="#95a5a6",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=6,
            pady=4,
            cursor="hand2"
        )
        refresh_btn.grid(row=1, column=0, columnspan=2, padx=4, pady=(4, 2), sticky="ew")

        right_frame = tk.Frame(tab, bg="#ffffff", bd=1, relief=tk.SUNKEN)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 5), pady=5)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        right_frame.rowconfigure(3, weight=1)

        details_label = tk.Label(right_frame, text="Workflow Details", font=("Arial", 12, "bold"), bg="#ffffff")
        details_label.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        self.workflow_details = scrolledtext.ScrolledText(
            right_frame,
            height=10,
            font=("Courier New", 10),
            wrap=tk.WORD
        )
        self.workflow_details.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        simulation_label = tk.Label(right_frame, text="Simulation Output", font=("Arial", 12, "bold"), bg="#ffffff")
        simulation_label.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 4))

        self.workflow_simulation = scrolledtext.ScrolledText(
            right_frame,
            height=12,
            font=("Courier New", 10),
            wrap=tk.WORD
        )
        self.workflow_simulation.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))

        if not WORKFLOW_COMPILER_AVAILABLE or self.workflow_compiler is None:
            self.workflow_details.insert(1.0, "Workflow compiler module not available.")
            compile_btn.config(state=tk.DISABLED)
            simulate_btn.config(state=tk.DISABLED)
            refresh_btn.config(state=tk.DISABLED)

    def _build_llm_tab(self, tab):
        for col in range(2):
            tab.columnconfigure(col, weight=1)
        tab.rowconfigure(0, weight=1)

        # Ensure variables exist once
        if not hasattr(self, "llm_api_key_var"):
            self.llm_api_key_var = tk.StringVar()
        self.llm_model_var = tk.StringVar(value="gpt-5-mini")
        self.llm_temperature_var = tk.DoubleVar(value=0.2)
        self.llm_query_var = tk.StringVar()

        settings_frame = tk.LabelFrame(tab, text="LLM Configuration", font=("Arial", 12, "bold"), bg="#f0f0f0")
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        settings_frame.columnconfigure(1, weight=1)

        tk.Label(settings_frame, text="Provider:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=0, column=0, sticky="w", padx=10, pady=(12, 4))
        tk.Label(settings_frame, text="OpenAI", font=("Arial", 10), bg="#f0f0f0").grid(row=0, column=1, sticky="w", padx=10, pady=(12, 4))

        tk.Label(settings_frame, text="API Key:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.llm_api_key_entry = tk.Entry(settings_frame, textvariable=self.llm_api_key_var, show="*", font=("Arial", 10))
        self.llm_api_key_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        tk.Label(settings_frame, text="(enter new key to update — existing key stays if left as ****)", font=("Arial", 9), bg="#f0f0f0", fg="#555555").grid(row=2, column=1, sticky="w", padx=10, pady=(0, 8))

        tk.Label(settings_frame, text="Model:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=3, column=0, sticky="w", padx=10, pady=4)
        self.llm_model_entry = ttk.Combobox(
            settings_frame,
            textvariable=self.llm_model_var,
            state="readonly",
            values=[
                "gpt-5-mini",
                "gpt-5-nano",
                "gpt-5",
                "gpt-4o",
                "gpt-4o-mini",
            ]
        )
        self.llm_model_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=4)

        tk.Label(settings_frame, text="Temperature:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=4, column=0, sticky="w", padx=10, pady=4)
        temp_scale = tk.Scale(settings_frame, variable=self.llm_temperature_var, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL)
        temp_scale.grid(row=4, column=1, sticky="ew", padx=10, pady=4)
        self.llm_temp_scale = temp_scale

        button_row = tk.Frame(settings_frame, bg="#f0f0f0")
        button_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 8))
        button_row.columnconfigure((0, 1), weight=1)

        tk.Button(button_row, text="Save Settings", command=self._save_llm_settings, bg="#27ae60", fg="white", font=("Arial", 10, "bold"), padx=10, pady=6).grid(row=0, column=0, padx=(0, 6), sticky="ew")
        tk.Button(button_row, text="Test Connection", command=self._test_llm_connection, bg="#2980b9", fg="white", font=("Arial", 10, "bold"), padx=10, pady=6).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.llm_status_label = tk.Label(settings_frame, text="LLM not configured.", font=("Arial", 10), bg="#f0f0f0", fg="#c0392b")
        self.llm_status_label.grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4))

        chat_frame = tk.LabelFrame(tab, text="AI Assistant", font=("Arial", 12, "bold"), bg="#f0f0f0")
        chat_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.llm_chat_text = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 10))
        self.llm_chat_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))

        input_frame = tk.Frame(chat_frame, bg="#f0f0f0")
        input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 10))
        input_frame.columnconfigure(0, weight=1)

        self.llm_query_entry = tk.Entry(input_frame, textvariable=self.llm_query_var, font=("Arial", 10))
        self.llm_query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.llm_query_entry.bind("<Return>", lambda e: self._run_llm_query())

        tk.Button(input_frame, text="Send", command=self._run_llm_query, bg="#8e44ad", fg="white", font=("Arial", 10, "bold"), padx=12, pady=4).grid(row=0, column=1)

        tk.Button(input_frame, text="Clear", command=self._clear_llm_chat, bg="#7f8c8d", fg="white", font=("Arial", 10), padx=12, pady=4).grid(row=0, column=2, padx=(6, 0))

    def _update_workflow_library(self, refresh_only: bool = False):
        if not hasattr(self, "workflow_listbox"):
            return

        if self.workflow_compiler is None:
            self.compiled_workflows = []
            self.workflow_listbox.delete(0, tk.END)
            self.workflow_details.delete(1.0, tk.END)
            self.workflow_details.insert(1.0, "Workflow compiler not available.")
            self.workflow_simulation.delete(1.0, tk.END)
            return

        try:
            if not refresh_only:
                self.compiled_workflows = self.workflow_compiler.get_compiled_workflows()
            elif not getattr(self, "compiled_workflows", None):
                self.compiled_workflows = self.workflow_compiler.get_compiled_workflows()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load workflows:\n{e}")
            self.compiled_workflows = []

        self.workflow_listbox.delete(0, tk.END)

        for workflow in self.compiled_workflows:
            display = f"{workflow.get('workflow_id', 'unknown')} | {workflow.get('workflow_type', 'unknown')}"
            self.workflow_listbox.insert(tk.END, display)

        if self.compiled_workflows:
            self.workflow_listbox.selection_set(0)
            self._display_workflow_details(self.compiled_workflows[0])
        else:
            self.workflow_details.delete(1.0, tk.END)
            self.workflow_details.insert(1.0, "No compiled workflows found. Click 'Compile Workflows' to generate.")
            self.workflow_simulation.delete(1.0, tk.END)

    def _compile_workflows(self):
        if self.workflow_compiler is None:
            messagebox.showerror("Unavailable", "Workflow compiler module is not available.")
            return

        try:
            compiled = self.workflow_compiler.compile_workflows()
            self.compiled_workflows = [wf.to_dict() if hasattr(wf, "to_dict") else wf for wf in compiled]
            self._update_workflow_library(refresh_only=True)
            messagebox.showinfo("Workflow Compilation", f"Compiled {len(compiled)} workflows from recent sessions.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to compile workflows:\n{e}")

    def _refresh_llm_settings_ui(self):
        if not hasattr(self, "llm_status_label"):
            return

        widgets = [
            getattr(self, "llm_api_key_entry", None),
            getattr(self, "llm_model_entry", None),
            getattr(self, "llm_temp_scale", None),
            getattr(self, "llm_query_entry", None),
        ]

        if not self.llm_service:
            for widget in widgets:
                if widget:
                    widget.configure(state=tk.DISABLED)
            self.llm_status_label.config(text="LLM service not available in this environment.", fg="#c0392b")
            return

        for widget in widgets:
            if widget:
                widget.configure(state=tk.NORMAL)

        cfg = self.llm_service.get_config()
        if cfg.api_key:
            self.llm_api_key_var.set("********")
        else:
            self.llm_api_key_var.set("")
        self.llm_model_var.set(cfg.model or "gpt-5-mini")
        self.llm_temperature_var.set(cfg.temperature or 0.2)

        if not self.llm_service.available():
            self.llm_status_label.config(
                text="OpenAI client not installed. Run: pip install openai",
                fg="#c0392b"
            )
        elif not cfg.api_key:
            self.llm_status_label.config(
                text="Enter your OpenAI API key to enable GPT-4o summaries.",
                fg="#e67e22"
            )
        else:
            self.llm_status_label.config(
                text=f"Connected to {cfg.provider.upper()} (model {cfg.model}).",
                fg="#27ae60"
            )

    def _save_llm_settings(self):
        if not self.llm_service:
            messagebox.showerror("Unavailable", "LLM service is not available.")
            return

        cfg = self.llm_service.get_config()
        api_key_input = self.llm_api_key_var.get().strip()
        if api_key_input and api_key_input != "********":
            api_key = api_key_input
            self._llm_api_key_cache = api_key
        else:
            api_key = self._llm_api_key_cache or cfg.api_key

        model = self.llm_model_var.get().strip() or cfg.model or "gpt-5-mini"
        temperature = self.llm_temperature_var.get()

        try:
            self.llm_service.save_config(api_key, model, provider="openai", temperature=temperature)
            self._llm_api_key_cache = api_key
            messagebox.showinfo("Saved", "LLM settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save LLM settings:\n{e}")

        self._refresh_llm_settings_ui()

    def _test_llm_connection(self):
        if not self.llm_service:
            messagebox.showerror("Unavailable", "LLM service is not available.")
            return

        if not self.llm_service.available():
            messagebox.showerror("Unavailable", "OpenAI client library not installed. Run: pip install openai")
            return

        if not self.llm_service.is_configured():
            messagebox.showwarning("Configure LLM", "Please enter and save your OpenAI API key first.")
            return

        self.llm_status_label.config(text="Testing connection...", fg="#2980b9")

        def worker():
            response = self.llm_service.generate_summary("Summarize your capabilities in one sentence.")

            def update():
                if response:
                    self.llm_status_label.config(text="Connection successful.", fg="#27ae60")
                else:
                    self.llm_status_label.config(text="LLM test failed. Check API key and network.", fg="#c0392b")

            self.root.after(0, update)

        threading.Thread(target=worker, daemon=True).start()

    def _run_llm_query(self):
        if not self.llm_service:
            messagebox.showerror("Unavailable", "LLM service is not available.")
            return
        if not self.llm_service.available():
            messagebox.showerror("Unavailable", "OpenAI client library not installed. Run: pip install openai")
            return
        if not self.llm_service.is_configured():
            messagebox.showwarning("Configure LLM", "Please enter and save your OpenAI API key first.")
            return

        prompt = self.llm_query_var.get().strip()
        if not prompt:
            return
        self.llm_query_var.set("")
        self._append_llm_chat("You", prompt)

        threading.Thread(target=self._llm_chat_worker, args=(prompt,), daemon=True).start()

    def _clear_llm_chat(self):
        if hasattr(self, "llm_chat_text"):
            self.llm_chat_text.config(state=tk.NORMAL)
            self.llm_chat_text.delete(1.0, tk.END)
            self.llm_chat_text.config(state=tk.DISABLED)

    def _append_llm_chat(self, speaker: str, message: str):
        if not hasattr(self, "llm_chat_text"):
            return
        self.llm_chat_text.config(state=tk.NORMAL)
        self.llm_chat_text.insert(tk.END, f"{speaker}: {message}\n\n")
        self.llm_chat_text.see(tk.END)
        self.llm_chat_text.config(state=tk.DISABLED)

    def _llm_chat_worker(self, prompt: str):
        response = self.llm_service.chat(prompt)

        def update():
            if response:
                self._append_llm_chat("Assistant", response)
            else:
                self._append_llm_chat("Assistant", "[LLM] Unable to generate a response. Check settings.")

        self.root.after(0, update)

    def _replay_llm_summary(self, text: str):
        if not hasattr(self, "workflow_simulation"):
            return
        self.workflow_simulation.insert(tk.END, "\n[LLM Summary]\n" + text + "\n")
        self.workflow_simulation.see(tk.END)

    def _async_workflow_summary(self, workflow: Dict):
        if not self.llm_service or not self.llm_service.available() or not self.llm_service.is_configured():
            return
        prompt = self.llm_service.redact_and_prepare_workflow(workflow)
        prompt += "\n\nProvide a concise 4-sentence business summary of this workflow."
        summary = self.llm_service.generate_summary(prompt)

        def update():
            if summary:
                self._replay_llm_summary(summary)
            else:
                self._replay_llm_summary("[LLM] Could not generate summary (check LLM configuration).")

        self.root.after(0, update)

    def _on_workflow_select(self, event=None):
        if not getattr(self, "compiled_workflows", None):
            return
        selection = self.workflow_listbox.curselection()
        if not selection:
            return
        workflow = self.compiled_workflows[selection[0]]
        self._display_workflow_details(workflow)

    def _display_workflow_details(self, workflow: Dict):
        details = [
            f"Workflow ID : {workflow.get('workflow_id')}",
            f"Type        : {workflow.get('workflow_type')}",
            f"Session     : {workflow.get('session_id')}",
            f"Confidence  : {workflow.get('confidence', 0.0):.2f}",
            f"Timestamp   : {workflow.get('timestamp')}",
        ]
        goal = workflow.get("goal")
        if goal:
            details.append(f"Goal        : {goal}")
        description = workflow.get("description")
        if description:
            details.append("")
            details.append("Description:")
            details.append(description)
        details.append("")
        details.append(f"Steps       : {len(workflow.get('steps', []))}")

        summary = workflow.get("summary")
        if summary:
            details.append("")
            details.append("Summary:")
            for line in summary:
                details.append(f"  {line}")

        self.workflow_details.delete(1.0, tk.END)
        self.workflow_details.insert(1.0, "\n".join(details))
        self.workflow_simulation.delete(1.0, tk.END)

    def _simulate_selected_workflow(self):
        if self.workflow_compiler is None:
            messagebox.showerror("Unavailable", "Workflow compiler module is not available.")
            return

        selection = self.workflow_listbox.curselection()
        if not selection:
            messagebox.showwarning("Select Workflow", "Please select a workflow to simulate.")
            return

        workflow = self.compiled_workflows[selection[0]]
        workflow_key = workflow.get("workflow_key")
        try:
            simulation = self.workflow_compiler.simulate_workflow(workflow_key)
        except Exception as e:
            messagebox.showerror("Error", f"Simulation failed:\n{e}")
            return

        if not simulation:
            messagebox.showerror("Simulation Failed", "Could not simulate the selected workflow.")
            return

        lines = simulation.get("summary", [])
        if lines and lines[-1] != "":
            lines.append("")
        lines.append("Steps:")
        for step in simulation.get("steps", []):
            lines.append(f"Step {step['step_number']:>2}: {step['intent']} - {step['intent_description']}")
            contexts = step.get("contexts", {})
            if contexts:
                ctx = ", ".join(f"{k}={v}" for k, v in contexts.items())
                lines.append(f"    Contexts: {ctx}")

        self.workflow_simulation.delete(1.0, tk.END)
        self.workflow_simulation.insert(1.0, "\n".join(lines))

        if self.llm_service and self.llm_service.available() and self.llm_service.is_configured():
            self.workflow_simulation.insert(tk.END, "\n[LLM] Generating natural language summary...\n")
            self.workflow_simulation.see(tk.END)
            threading.Thread(target=self._async_workflow_summary, args=(workflow,), daemon=True).start()

    def _start_refresh_loop(self):
        """Start auto-refresh loop"""
        def refresh_loop():
            while True:
                if self.auto_refresh_var.get():
                    try:
                        self._refresh_all()
                        self._update_quick_stats()
                    except:
                        pass
                time.sleep(self.refresh_interval)
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
        
        # Initial refresh after a short delay
        self.root.after(500, self._refresh_all)
        self.root.after(500, self._update_quick_stats)
    
    def run(self):
        """Run dashboard"""
        self.root.mainloop()

    def _log_error(self, message: str):
        """Log error"""
        self.logger.error(message)

    def _is_insight_stale(self, insight: Dict, max_age_hours: int = 6) -> bool:
        timestamp = insight.get("generated_at")
        if not timestamp:
            return True
        try:
            generated = datetime.fromisoformat(timestamp)
        except ValueError:
            return True
        return (datetime.now() - generated) > timedelta(hours=max_age_hours)

    def _get_llm_insight(self, force: bool = False) -> Optional[Dict]:
        if not self.llm_service or not self.llm_service.is_configured():
            return None

        try:
            from intelligence.llm_insight_service import load_latest_insight, generate_insight
        except Exception as exc:
            if hasattr(self, "logger") and self.logger:
                self.logger.warning(f"LLM insight service unavailable: {exc}")
            return None

        if not force and self._latest_insight_cache:
            if not self._is_insight_stale(self._latest_insight_cache):
                return self._latest_insight_cache

        try:
            insight = load_latest_insight(self.installation_dir)
            if force or not insight or self._is_insight_stale(insight):
                insight = generate_insight(self.installation_dir)
            self._latest_insight_cache = insight
            return insight
        except Exception as exc:
            if hasattr(self, "logger") and self.logger:
                self.logger.warning(f"Unable to generate LLM insight: {exc}")
            return None

    def _generate_automation_prototypes(self):
        if not self.prototype_generation_available or not self.ai_dashboard:
            messagebox.showwarning("Unavailable", "Automation prototype generator is not available.")
            return

        generator = getattr(self.ai_dashboard, "prototype_generator", None)
        if not generator:
            messagebox.showwarning("Unavailable", "Automation prototype generator has not been initialized yet.")
            return

        if getattr(self, "_prototype_generation_running", False):
            messagebox.showinfo("In Progress", "Prototype generation is already running. Please wait.")
            return

        self._prototype_generation_running = True

        def worker():
            try:
                results = generator.generate_for_top_patterns()

                def on_success():
                    self._latest_insight_cache = None
                    self._update_ai_recommendations()
                    if results:
                        messagebox.showinfo(
                            "Automation Prototypes Created",
                            f"Generated {len(results)} prototype bundle(s). Check 'AI/automation_prototypes/'.",
                        )
                    else:
                        messagebox.showinfo(
                            "No Candidates",
                            "No eligible patterns met the thresholds yet. Collect more monitoring data.",
                        )

                self.root.after(0, on_success)
            except Exception as exc:

                def on_error():
                    messagebox.showerror("Generation Failed", f"Could not generate prototypes:\n{exc}")

                self.root.after(0, on_error)
            finally:
                self.root.after(0, lambda: setattr(self, "_prototype_generation_running", False))

        threading.Thread(target=worker, daemon=True).start()

    def _build_automation_tab(self, tab):
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        frame = ttk.Frame(tab, padding=20)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        header = ttk.Label(
            frame,
            text="Automation Executor",
            font=("Arial", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        description = ttk.Label(
            frame,
            text=(
                "Launch the Automation Executor Manager to review AI-generated "
                "prototype bundles, run them end-to-end, and capture feedback."
            ),
            wraplength=600,
            justify=tk.LEFT,
        )
        description.grid(row=1, column=0, sticky="w", pady=(10, 20))

        launch_btn = ttk.Button(
            frame,
            text="Open Automation Executor",
            command=self._launch_automation_executor,
        )
        launch_btn.grid(row=2, column=0, sticky="w", pady=(0, 12))

        info = ttk.Label(
            frame,
            text="Prototype bundles live under AI/automation_prototypes/",
            foreground="#555555",
        )
        info.grid(row=3, column=0, sticky="w")

    def _launch_automation_executor(self):
        bridge_path = self.installation_dir / "AI" / "intelligence" / "automation_executor_gui.py"
        if not bridge_path.exists():
            messagebox.showerror("Not Available", "Automation executor GUI not found at expected path.")
            return
        try:
            subprocess.Popen([sys.executable, str(bridge_path)])
        except Exception as exc:
            messagebox.showerror("Launch Failed", f"Could not launch automation executor:\n{exc}")

    def _start_workflow_training(self):
        if not self.workflow_training_manager:
            messagebox.showwarning(
                "Not Available",
                "Workflow training manager is unavailable. Ensure training modules are installed.",
            )
            return

        if self.training_session_metadata is not None:
            messagebox.showinfo("Training In Progress", "A workflow training session is already active.")
            return

        title = simpledialog.askstring("Train New Workflow", "Enter a name for this workflow:", parent=self.root)
        if not title:
            return

        try:
            metadata = self.workflow_training_manager.start_training(title)
            self.training_session_metadata = metadata
            messagebox.showinfo(
                "Training Started",
                f"Recording workflow '{title}'. Use 'End Workflow Training' when finished.",
            )
        except RuntimeError as exc:
            messagebox.showwarning("Monitoring Active", str(exc))
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to start training:\n{exc}")

    def _end_workflow_training(self):
        if not self.workflow_training_manager:
            messagebox.showwarning(
                "Not Available",
                "Workflow training manager is unavailable. Ensure training modules are installed.",
            )
            return

        if not self.training_session_metadata:
            messagebox.showinfo("No Training Session", "No workflow training session is currently active.")
            return

        metadata = self.training_session_metadata
        self.training_session_metadata = None
        try:
            bundle = self.workflow_training_manager.end_training(metadata)
            self._latest_insight_cache = None
            self._update_ai_recommendations()
            if bundle:
                messagebox.showinfo(
                    "Training Complete",
                    f"Prototype generated for '{metadata.title}'.\nBundle: {bundle}",
                )
            else:
                messagebox.showwarning(
                    "Training Complete",
                    "Workflow recorded, but no browser activity was detected. No prototype generated.",
                )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to complete training:\n{exc}")


def main():
    """Main function"""
    app = MasterAIDashboard()
    app.run()


if __name__ == "__main__":
    main()
