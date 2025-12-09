#!/usr/bin/env python3
"""
AI Intelligence Verification Dashboard
Shows how the monitoring system is contributing to building a generatively intelligent system
that learns and revolutionizes company operations.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys

# Background services
try:
    from pattern_extraction_worker import start_pattern_worker, get_pattern_worker
except ImportError:  # pragma: no cover - optional dependency
    start_pattern_worker = None  # type: ignore
    get_pattern_worker = None  # type: ignore

try:
    from training_scheduler import start_training_scheduler, get_training_scheduler
except ImportError:  # pragma: no cover - optional dependency
    start_training_scheduler = None  # type: ignore
    get_training_scheduler = None  # type: ignore

try:
    from automation_prototype_generator import AutomationPrototypeGenerator
except ImportError:  # pragma: no cover - optional dependency
    AutomationPrototypeGenerator = None  # type: ignore

# Add AI subdirectories to path
ai_dir = Path(__file__).parent.parent
sys.path.insert(0, str(ai_dir / "training"))
sys.path.insert(0, str(ai_dir / "intelligence"))

try:
    from ai_training_integration import get_ai_training_integration
    from ai_activity_analyzer import AIActivityAnalyzer
    from local_ai_trainer import LocalAITrainer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class AIIntelligenceDashboard:
    """Dashboard showing AI learning progress and intelligence metrics"""
    
    def __init__(self, installation_dir: Optional[Path] = None):
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent.parent
        
        installation_dir = Path(installation_dir)
        self.installation_dir = installation_dir
        ai_dir = installation_dir / "AI"
        secure_data_dir = self.installation_dir / "_secure_data" / "full_monitoring"
        legacy_data_dir = ai_dir / "data" / "full_monitoring"
        self.data_dir = secure_data_dir if (secure_data_dir / "full_monitoring.db").exists() else legacy_data_dir
        self.models_dir = ai_dir / "models"
        self.db_path = self.data_dir / "full_monitoring.db"
        self.pattern_store = ai_dir / "intelligence" / "workflow_patterns.db"
        self.training_metrics_db = ai_dir / "intelligence" / "training_metrics.db"
        self.pattern_worker = None
        self.training_scheduler = None
        self.prototype_generator = None
        
        # Initialize AI components
        self.analyzer = None
        self.trainer = None
        self.integration = None
        
        if AI_AVAILABLE:
            try:
                # Pass installation_dir (parent of AI folder) to components
                self.analyzer = AIActivityAnalyzer(self.installation_dir)
                self.trainer = LocalAITrainer(self.installation_dir)
                self.integration = get_ai_training_integration(self.installation_dir)
            except Exception as e:
                print(f"Warning: Could not initialize AI components: {e}")
                pass

        self._start_background_services()

    def _start_background_services(self) -> None:
        """Ensure pattern extraction and training scheduler are running."""
        if start_pattern_worker and self.pattern_worker is None:
            try:
                self.pattern_worker = start_pattern_worker(self.installation_dir)
            except Exception as exc:
                print(f"Warning: Could not start pattern worker: {exc}")

        if start_training_scheduler and self.training_scheduler is None:
            try:
                self.training_scheduler = start_training_scheduler(self.installation_dir)
            except Exception as exc:
                print(f"Warning: Could not start training scheduler: {exc}")

        if AutomationPrototypeGenerator and self.prototype_generator is None:
            try:
                self.prototype_generator = AutomationPrototypeGenerator(self.installation_dir)
            except Exception as exc:
                print(f"Warning: Could not initialize automation prototype generator: {exc}")
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring status"""
        status = {
            "monitoring_active": False,
            "database_exists": self.db_path.exists(),
            "data_collected": False,
            "last_activity": None
        }
        
        if not self.db_path.exists():
            return status
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for recent activity (last 5 minutes - more accurate for "currently active")
            cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
            
            cursor.execute("""
                SELECT MAX(timestamp) FROM (
                    SELECT timestamp FROM screen_recordings WHERE timestamp > ?
                    UNION ALL
                    SELECT timestamp FROM keyboard_input WHERE timestamp > ?
                    UNION ALL
                    SELECT timestamp FROM mouse_activity WHERE timestamp > ?
                    UNION ALL
                    SELECT timestamp FROM application_usage WHERE timestamp > ?
                    UNION ALL
                    SELECT timestamp FROM file_activity WHERE timestamp > ?
                )
            """, (cutoff, cutoff, cutoff, cutoff, cutoff))
            
            result = cursor.fetchone()
            if result and result[0]:
                status["last_activity"] = result[0]
                last_activity_time = datetime.fromisoformat(result[0])
                # Only show as active if data was recorded in the last 5 minutes
                status["monitoring_active"] = (datetime.now() - last_activity_time).total_seconds() < 300
                status["data_collected"] = True
            else:
                # Check for any data at all (for "data_collected" status)
                cursor.execute("""
                    SELECT MAX(timestamp) FROM (
                        SELECT timestamp FROM screen_recordings
                        UNION ALL
                        SELECT timestamp FROM keyboard_input
                        UNION ALL
                        SELECT timestamp FROM mouse_activity
                        UNION ALL
                        SELECT timestamp FROM application_usage
                        UNION ALL
                        SELECT timestamp FROM file_activity
                    )
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    status["last_activity"] = result[0]
                    status["data_collected"] = True
            
            conn.close()
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def get_data_collection_metrics(self) -> Dict:
        """Get data collection metrics"""
        metrics = {
            "total_screens": 0,
            "total_keyboard": 0,
            "total_mouse": 0,
            "total_apps": 0,
            "total_files": 0,
            "total_data_points": 0,
            "sessions_count": 0,
            "data_size_mb": 0,
            "collection_rate_per_hour": 0,
            "time_span_days": 0
        }
        
        if not self.db_path.exists():
            return metrics
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM screen_recordings")
            metrics["total_screens"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM keyboard_input")
            metrics["total_keyboard"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mouse_activity")
            metrics["total_mouse"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM application_usage")
            metrics["total_apps"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_activity")
            metrics["total_files"] = cursor.fetchone()[0]
            
            metrics["total_data_points"] = (
                metrics["total_screens"] +
                metrics["total_keyboard"] +
                metrics["total_mouse"] +
                metrics["total_apps"] +
                metrics["total_files"]
            )
            
            # Count sessions
            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM screen_recordings")
            metrics["sessions_count"] = cursor.fetchone()[0]
            
            # Get time span
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM screen_recordings")
            result = cursor.fetchone()
            if result and result[0] and result[1]:
                start = datetime.fromisoformat(result[0])
                end = datetime.fromisoformat(result[1])
                metrics["time_span_days"] = (end - start).days + 1
                
                # Calculate collection rate
                hours = (end - start).total_seconds() / 3600
                if hours > 0:
                    metrics["collection_rate_per_hour"] = metrics["total_data_points"] / hours
            
            # Estimate data size
            db_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
            metrics["data_size_mb"] = round(db_size, 2)
            
            conn.close()
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics
    
    def get_ai_learning_metrics(self) -> Dict:
        """Get AI learning and pattern extraction metrics"""
        metrics = {
            "patterns_extracted": 0,
            "workflows_identified": 0,
            "sequences_learned": 0,
            "models_trained": 0,
            "training_data_points": 0,
            "last_analysis": None,
            "last_training": None,
            "learning_progress": 0,
            "pattern_count": 0,
            "last_pattern_seen": None,
            "training_accuracy": None,
            "training_precision": None,
            "training_recall": None
        }
        
        if not self.analyzer:
            return metrics
        
        try:
            # Check for analysis files
            analysis_files = list(self.models_dir.glob("analysis_*.json"))
            metrics["patterns_extracted"] = len(analysis_files)
            
            # Count patterns in analysis files
            total_patterns = 0
            total_workflows = 0
            total_sequences = 0
            
            for analysis_file in analysis_files:
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                        total_patterns += len(analysis.get("patterns", []))
                        total_workflows += len(analysis.get("workflows", []))
                        total_sequences += len(analysis.get("sequences", []))
                except:
                    pass
            
            metrics["patterns_extracted"] = total_patterns
            metrics["workflows_identified"] = total_workflows
            metrics["sequences_learned"] = total_sequences
            
            # Check for trained models
            model_files = list(self.models_dir.glob("*.pkl")) + list(self.models_dir.glob("*.h5")) + list(self.models_dir.glob("*.pt"))
            metrics["models_trained"] = len(model_files)
            
            # Get training status
            if self.integration:
                status = self.integration.get_training_status()
                metrics["last_analysis"] = status.get("last_analysis_time")
                metrics["last_training"] = status.get("last_training_time")
                metrics["training_data_points"] = status.get("has_enough_data", False)
            
            # Calculate learning progress (0-100%)
            data_metrics = self.get_data_collection_metrics()
            if data_metrics["total_data_points"] > 0:
                # Progress based on data collection and analysis
                analysis_progress = min(100, (metrics["patterns_extracted"] / max(1, data_metrics["total_data_points"] / 100)) * 100)
                training_progress = min(100, metrics["models_trained"] * 10)  # 10% per model
                metrics["learning_progress"] = round((analysis_progress + training_progress) / 2, 1)

            # Pattern extraction summary
            pattern_summary = self.get_pattern_summary()
            metrics["pattern_count"] = pattern_summary.get("total_patterns", 0)
            metrics["last_pattern_seen"] = pattern_summary.get("last_seen")

            # Training metrics summary
            recent_training = self.get_recent_training_runs(limit=1)
            if recent_training:
                run = recent_training[0]
                metrics["training_accuracy"] = run.get("accuracy")
                metrics["training_precision"] = run.get("precision")
                metrics["training_recall"] = run.get("recall")
                metrics["last_training"] = metrics["last_training"] or run.get("completed_at")
 
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics

    def get_pattern_summary(self) -> Dict[str, Optional[int]]:
        """Return aggregated pattern statistics from the pattern store."""
        try:
            if get_pattern_worker:
                worker = get_pattern_worker(self.installation_dir)
                summary = worker.get_summary()
                return {
                    "total_patterns": summary.total_patterns,
                    "last_seen": summary.last_seen,
                    "total_sessions": summary.total_sessions,
                }
        except Exception as exc:
            return {"error": str(exc)}

        # Fallback: direct query if worker not available
        if not self.pattern_store.exists():
            return {"total_patterns": 0, "last_seen": None, "total_sessions": 0}

        try:
            conn = sqlite3.connect(self.pattern_store)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), MAX(last_seen), SUM(total_sessions) FROM aggregated_patterns")
            total, last_seen, sessions = cursor.fetchone()
            conn.close()
            return {
                "total_patterns": int(total or 0),
                "last_seen": last_seen,
                "total_sessions": int(sessions or 0),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_recent_training_runs(self, limit: int = 3) -> List[Dict[str, Optional[float]]]:
        """Return recent incremental training metrics."""
        if get_training_scheduler:
            try:
                scheduler = get_training_scheduler(self.installation_dir)
                runs = scheduler.get_recent_runs(limit)
                return [run.__dict__ for run in runs]
            except Exception:
                pass

        if not self.training_metrics_db.exists():
            return []

        try:
            conn = sqlite3.connect(self.training_metrics_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT started_at, completed_at, duration_seconds, patterns_processed,
                       new_patterns, accuracy, precision, recall, notes
                FROM training_runs
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def list_automation_prototypes(self) -> List[Dict[str, Optional[str]]]:
        """Return metadata about generated automation prototypes."""
        if self.prototype_generator:
            try:
                data = self.prototype_generator.list_prototypes()
                return [dict(item) for item in data.values()]
            except Exception:
                pass
        return []
    
    def get_operational_insights(self) -> Dict:
        """Get insights on how AI is learning to revolutionize operations"""
        insights = {
            "most_used_apps": [],
            "common_workflows": [],
            "efficiency_patterns": [],
            "automation_opportunities": [],
            "learning_velocity": "Low"
        }
        
        if not self.db_path.exists():
            return insights
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Most used apps
            cursor.execute("""
                SELECT active_app, COUNT(*) as count
                FROM application_usage
                GROUP BY active_app
                ORDER BY count DESC
                LIMIT 10
            """)
            
            insights["most_used_apps"] = [
                {"app": row[0] or "Unknown", "usage_count": row[1]}
                for row in cursor.fetchall()
            ]
            
            # Get learning velocity
            cursor.execute("""
                SELECT COUNT(*) FROM screen_recordings
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            recent_activity = cursor.fetchone()[0]
            
            if recent_activity > 1000:
                insights["learning_velocity"] = "Very High"
            elif recent_activity > 500:
                insights["learning_velocity"] = "High"
            elif recent_activity > 100:
                insights["learning_velocity"] = "Medium"
            else:
                insights["learning_velocity"] = "Low"
            
            conn.close()
            
            # Get workflows from analysis
            if self.analyzer:
                analysis_files = list(self.models_dir.glob("analysis_*.json"))
                workflows = []
                
                for analysis_file in analysis_files[:5]:  # Latest 5
                    try:
                        with open(analysis_file, 'r', encoding='utf-8') as f:
                            analysis = json.load(f)
                            workflows.extend(analysis.get("workflows", [])[:3])  # Top 3 per file
                    except:
                        pass
                
                insights["common_workflows"] = workflows[:10]  # Top 10
            
        except Exception as e:
            insights["error"] = str(e)
        
        return insights
    
    def generate_report(self) -> str:
        """Generate comprehensive intelligence report"""
        report_lines = []
        
        report_lines.append("=" * 80)
        report_lines.append("AI INTELLIGENCE VERIFICATION DASHBOARD")
        report_lines.append("Generative Intelligence System - Learning Progress Report")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Monitoring Status
        report_lines.append("MONITORING STATUS")
        report_lines.append("-" * 80)
        status = self.get_monitoring_status()
        report_lines.append(f"Monitoring Active: {'[OK]' if status['monitoring_active'] else '[INACTIVE]'}")
        report_lines.append(f"Database Exists: {'[OK]' if status['database_exists'] else '[MISSING]'}")
        report_lines.append(f"Data Collected: {'[OK]' if status['data_collected'] else '[NO DATA]'}")
        if status.get("last_activity"):
            report_lines.append(f"Last Activity: {status['last_activity']}")
        report_lines.append("")
        
        # Data Collection Metrics
        report_lines.append("DATA COLLECTION METRICS")
        report_lines.append("-" * 80)
        metrics = self.get_data_collection_metrics()
        report_lines.append(f"Total Data Points: {metrics['total_data_points']:,}")
        report_lines.append(f"  - Screen Recordings: {metrics['total_screens']:,}")
        report_lines.append(f"  - Keyboard Input: {metrics['total_keyboard']:,}")
        report_lines.append(f"  - Mouse Activity: {metrics['total_mouse']:,}")
        report_lines.append(f"  - Application Usage: {metrics['total_apps']:,}")
        report_lines.append(f"  - File Activity: {metrics['total_files']:,}")
        report_lines.append(f"Sessions Recorded: {metrics['sessions_count']}")
        report_lines.append(f"Data Size: {metrics['data_size_mb']} MB")
        report_lines.append(f"Time Span: {metrics['time_span_days']} days")
        if metrics['collection_rate_per_hour'] > 0:
            report_lines.append(f"Collection Rate: {metrics['collection_rate_per_hour']:.1f} data points/hour")
        report_lines.append("")
        
        # AI Learning Metrics
        report_lines.append("AI LEARNING METRICS")
        report_lines.append("-" * 80)
        learning = self.get_ai_learning_metrics()
        report_lines.append(f"Patterns Extracted: {learning['patterns_extracted']:,}")
        report_lines.append(f"Workflows Identified: {learning['workflows_identified']:,}")
        report_lines.append(f"Sequences Learned: {learning['sequences_learned']:,}")
        report_lines.append(f"Models Trained: {learning['models_trained']}")
        report_lines.append(f"Learning Progress: {learning['learning_progress']}%")
        if learning.get("last_analysis"):
            report_lines.append(f"Last Analysis: {learning['last_analysis']}")
        if learning.get("last_training"):
            report_lines.append(f"Last Training: {learning['last_training']}")
        report_lines.append("")
        
        # Operational Insights
        report_lines.append("OPERATIONAL INSIGHTS")
        report_lines.append("-" * 80)
        insights = self.get_operational_insights()
        report_lines.append(f"Learning Velocity: {insights['learning_velocity']}")
        report_lines.append("")
        report_lines.append("Most Used Applications:")
        for app in insights["most_used_apps"][:5]:
            report_lines.append(f"  - {app['app']}: {app['usage_count']:,} uses")
        report_lines.append("")
        
        # Contribution to Telos
        report_lines.append("CONTRIBUTION TO GENERATIVE INTELLIGENCE")
        report_lines.append("-" * 80)
        
        # Calculate contribution score
        contribution_score = 0
        contribution_factors = []
        
        if metrics['total_data_points'] > 10000:
            contribution_score += 30
            contribution_factors.append("High data volume collected")
        elif metrics['total_data_points'] > 1000:
            contribution_score += 15
            contribution_factors.append("Moderate data volume collected")
        
        if learning['patterns_extracted'] > 100:
            contribution_score += 25
            contribution_factors.append("Significant patterns extracted")
        elif learning['patterns_extracted'] > 10:
            contribution_score += 10
            contribution_factors.append("Patterns being identified")
        
        if learning['workflows_identified'] > 10:
            contribution_score += 25
            contribution_factors.append("Workflows being learned")
        elif learning['workflows_identified'] > 0:
            contribution_score += 10
            contribution_factors.append("Workflow identification started")
        
        if learning['models_trained'] > 0:
            contribution_score += 20
            contribution_factors.append("AI models actively training")
        
        report_lines.append(f"Contribution Score: {contribution_score}/100")
        report_lines.append("")
        report_lines.append("Active Learning Factors:")
        for factor in contribution_factors:
            report_lines.append(f"  [OK] {factor}")
        
        if contribution_score < 50:
            report_lines.append("")
            report_lines.append("RECOMMENDATION: Continue monitoring to build sufficient data for")
            report_lines.append("generative intelligence. The system needs more data to learn effectively.")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("SYSTEM STATUS: Building Generative Intelligence")
        report_lines.append("The monitoring system is actively learning your workflows, patterns,")
        report_lines.append("and behaviors to create an autonomous AI that will revolutionize")
        report_lines.append("company operations through intelligent automation.")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    """Main function"""
    print("Generating AI Intelligence Verification Report...")
    print("")
    
    dashboard = AIIntelligenceDashboard()
    report = dashboard.generate_report()
    
    print(report)
    print("")
    
    # Save report to AI Analysis reports folder
    ai_dir = Path(__file__).parent.parent
    analysis_reports_dir = ai_dir / "AI Analysis reports"
    analysis_reports_dir.mkdir(exist_ok=True, parents=True, mode=0o700)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = analysis_reports_dir / f"ai_intelligence_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to: {report_file}")
    print("")
    print("Press Enter to exit...")
    input()


if __name__ == "__main__":
    main()

