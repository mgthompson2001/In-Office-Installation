#!/usr/bin/env python3
"""
AI Optimization Analyzer - Passive Monitoring & Software Optimization
Analyzes software usage patterns and recommends optimizations.
All recommendations require admin approval before implementation.
"""

import os
import json
import sqlite3
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from collections import Counter, defaultdict

# Secure data collection
try:
    from secure_data_collector import SecureDataCollector
    COLLECTOR_AVAILABLE = True
except ImportError:
    COLLECTOR_AVAILABLE = False
    SecureDataCollector = None

# Admin storage
try:
    from admin_secure_storage import AdminSecureStorage
    ADMIN_STORAGE_AVAILABLE = True
except ImportError:
    ADMIN_STORAGE_AVAILABLE = False
    AdminSecureStorage = None


class AIOptimizationAnalyzer:
    """
    AI-powered software optimization analyzer.
    Passively monitors usage and recommends improvements.
    All recommendations require admin approval.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize AI optimization analyzer"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        self.intelligence_dir = ai_dir / "intelligence"
        self.intelligence_dir.mkdir(exist_ok=True, mode=0o700)
        self.analysis_reports_dir = ai_dir / "AI Analysis reports"
        self.analysis_reports_dir.mkdir(exist_ok=True, parents=True, mode=0o700)
        
        # Recommendations database
        self.recommendations_db = self.intelligence_dir / "optimization_recommendations.db"
        self._init_recommendations_database()
        
        # Setup logging
        self.log_file = self.intelligence_dir / "optimization_analyzer.log"
        self._setup_logging()
        
        # Analysis interval
        self.analysis_interval_hours = 24  # Analyze daily
        self.analysis_active = True
    
    def _init_recommendations_database(self):
        """Initialize recommendations database"""
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        # Optimization recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                current_state TEXT,
                proposed_change TEXT,
                expected_benefit TEXT,
                implementation_complexity TEXT,
                confidence_score REAL,
                data_evidence TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                reviewed_at TEXT,
                approved_at TEXT,
                rejected_at TEXT,
                implemented_at TEXT
            )
        """)
        
        # Analysis history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT NOT NULL,
                findings TEXT,
                recommendations_count INTEGER,
                analyzed_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def analyze_software_usage(self) -> Dict:
        """Analyze software usage patterns and generate recommendations"""
        self.logger.info("Starting software usage analysis...")
        
        if not COLLECTOR_AVAILABLE:
            self.logger.warning("Secure data collector not available")
            return {}
        
        collector = SecureDataCollector(self.installation_dir)
        
        # Get workflow history
        history = collector.get_workflow_history(days=30)
        
        # Analyze patterns
        findings = self._analyze_patterns(history)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings)
        
        # Store recommendations
        for recommendation in recommendations:
            self._store_recommendation(recommendation)
        
        # Build and store analysis report
        report_text, report_path = self._create_analysis_report(findings, recommendations)

        # Store analysis history
        self._store_analysis_history(findings, len(recommendations), report_path)
        
        self.logger.info(f"Analysis complete: {len(recommendations)} recommendations generated")
        
        return {
            "findings": findings,
            "recommendations": recommendations,
            "analyzed_at": datetime.now().isoformat(),
            "report_path": str(report_path) if report_path else None,
            "report_text": report_text
        }
    
    def _analyze_patterns(self, history: List[Dict]) -> Dict:
        """Analyze usage patterns"""
        findings = {
            "bot_usage_patterns": {},
            "performance_issues": [],
            "optimization_opportunities": [],
            "user_behavior_patterns": {},
            "error_patterns": {}
        }
        
        if not history:
            return findings
        
        # Bot usage analysis
        bot_usage = Counter()
        bot_success_rates = defaultdict(lambda: {"successes": 0, "total": 0})
        bot_execution_times = defaultdict(list)
        
        for record in history:
            bot_name = record.get("bot_name")
            if bot_name:
                bot_usage[bot_name] += 1
                bot_success_rates[bot_name]["total"] += 1
                if record.get("success"):
                    bot_success_rates[bot_name]["successes"] += 1
                if record.get("execution_time"):
                    bot_execution_times[bot_name].append(record["execution_time"])
        
        findings["bot_usage_patterns"] = {
            "most_used": dict(bot_usage.most_common(10)),
            "success_rates": {
                bot: data["successes"] / data["total"] 
                for bot, data in bot_success_rates.items()
            },
            "average_execution_times": {
                bot: sum(times) / len(times) if times else 0
                for bot, times in bot_execution_times.items()
            }
        }
        
        # Performance issues
        for bot, times in bot_execution_times.items():
            avg_time = sum(times) / len(times) if times else 0
            if avg_time > 300:  # More than 5 minutes
                findings["performance_issues"].append({
                    "bot": bot,
                    "average_time": avg_time,
                    "issue": "Slow execution time"
                })
        
        # Success rate issues
        for bot, success_rate in findings["bot_usage_patterns"]["success_rates"].items():
            if success_rate < 0.7:  # Less than 70% success
                findings["performance_issues"].append({
                    "bot": bot,
                    "success_rate": success_rate,
                    "issue": "Low success rate"
                })
        
        # Optimization opportunities
        # Find bots that are rarely used but could be optimized
        total_executions = len(history)
        for bot, count in bot_usage.items():
            usage_percentage = count / total_executions if total_executions > 0 else 0
            if usage_percentage < 0.05:  # Less than 5% usage
                findings["optimization_opportunities"].append({
                    "bot": bot,
                    "usage_percentage": usage_percentage,
                    "opportunity": "Low usage - consider deprecation or optimization"
                })
        
        return findings
    
    def _generate_recommendations(self, findings: Dict) -> List[Dict]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Performance recommendations
        for issue in findings.get("performance_issues", []):
            if issue["issue"] == "Slow execution time":
                recommendations.append({
                    "recommendation_type": "performance",
                    "title": f"Optimize {issue['bot']} Execution Time",
                    "description": f"{issue['bot']} has average execution time of {issue['average_time']:.2f}s",
                    "current_state": f"Average execution time: {issue['average_time']:.2f}s",
                    "proposed_change": "Optimize bot workflow to reduce execution time",
                    "expected_benefit": f"Reduce execution time by ~30-50%",
                    "implementation_complexity": "Medium",
                    "confidence_score": 0.85,
                    "data_evidence": json.dumps(issue),
                    "status": "pending"
                })
            
            elif issue["issue"] == "Low success rate":
                recommendations.append({
                    "recommendation_type": "reliability",
                    "title": f"Improve {issue['bot']} Success Rate",
                    "description": f"{issue['bot']} has success rate of {issue['success_rate']:.2%}",
                    "current_state": f"Success rate: {issue['success_rate']:.2%}",
                    "proposed_change": "Review and fix common failure points in bot",
                    "expected_benefit": f"Increase success rate to >85%",
                    "implementation_complexity": "High",
                    "confidence_score": 0.80,
                    "data_evidence": json.dumps(issue),
                    "status": "pending"
                })
        
        # Optimization opportunities
        for opportunity in findings.get("optimization_opportunities", []):
            recommendations.append({
                "recommendation_type": "optimization",
                "title": f"Review {opportunity['bot']} Usage",
                "description": f"{opportunity['bot']} is used only {opportunity['usage_percentage']:.2%} of the time",
                "current_state": f"Usage: {opportunity['usage_percentage']:.2%}",
                "proposed_change": "Consider deprecation or merging with other bots",
                "expected_benefit": "Reduce maintenance overhead",
                "implementation_complexity": "Low",
                "confidence_score": 0.70,
                "data_evidence": json.dumps(opportunity),
                "status": "pending"
            })
        
        # Usage pattern recommendations
        bot_usage = findings.get("bot_usage_patterns", {}).get("most_used", {})
        if bot_usage:
            most_used = max(bot_usage.items(), key=lambda x: x[1])
            recommendations.append({
                "recommendation_type": "feature",
                "title": f"Enhance {most_used[0]} Functionality",
                "description": f"{most_used[0]} is the most used bot ({most_used[1]} times)",
                "current_state": f"Most used bot: {most_used[1]} executions",
                "proposed_change": "Add advanced features or optimizations to most-used bot",
                "expected_benefit": "Improve user experience for most common workflow",
                "implementation_complexity": "Medium",
                "confidence_score": 0.90,
                "data_evidence": json.dumps({"bot": most_used[0], "usage_count": most_used[1]}),
                "status": "pending"
            })
        
        return recommendations
    
    def _store_recommendation(self, recommendation: Dict):
        """Store recommendation in database"""
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_recommendations
            (recommendation_type, title, description, current_state, proposed_change,
             expected_benefit, implementation_complexity, confidence_score, data_evidence,
             status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation["recommendation_type"],
            recommendation["title"],
            recommendation["description"],
            recommendation["current_state"],
            recommendation["proposed_change"],
            recommendation["expected_benefit"],
            recommendation["implementation_complexity"],
            recommendation["confidence_score"],
            recommendation["data_evidence"],
            recommendation["status"],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _create_analysis_report(self, findings: Dict, recommendations: List[Dict]) -> (str, Optional[Path]):
        """Create a human-readable analysis report and save it."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.analysis_reports_dir / f"optimization_analysis_{timestamp}.txt"

        lines = []
        lines.append("AI OPTIMIZATION ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")

        bot_usage = findings.get("bot_usage_patterns", {})
        lines.append("BOT USAGE PATTERNS")
        lines.append("-" * 80)
        most_used = bot_usage.get("most_used", {})
        if most_used:
            lines.append("Most frequently used bots:")
            for bot, count in most_used.items():
                lines.append(f"  • {bot}: {count} runs")
        else:
            lines.append("No bot usage data available.")
        lines.append("")

        success_rates = bot_usage.get("success_rates", {})
        if success_rates:
            lines.append("Success rates:")
            for bot, rate in success_rates.items():
                lines.append(f"  • {bot}: {rate:.2%}")
            lines.append("")

        perf_issues = findings.get("performance_issues", [])
        lines.append("PERFORMANCE ISSUES")
        lines.append("-" * 80)
        if perf_issues:
            for issue in perf_issues:
                lines.append(f"  • {issue.get('bot')}: {issue.get('issue')} (avg time {issue.get('average_time', 0):.1f}s)")
        else:
            lines.append("  • None detected")
        lines.append("")

        lines.append("OPTIMIZATION OPPORTUNITIES")
        lines.append("-" * 80)
        opportunities = findings.get("optimization_opportunities", [])
        if opportunities:
            for opp in opportunities:
                lines.append(f"  • {opp.get('issue')}: {opp.get('description')}")
        else:
            lines.append("  • No additional opportunities detected")
        lines.append("")

        lines.append("RECOMMENDATIONS GENERATED")
        lines.append("-" * 80)
        if recommendations:
            for idx, rec in enumerate(recommendations, 1):
                lines.append(f"{idx}. {rec.get('title')}")
                lines.append(f"   Type: {rec.get('recommendation_type')} | Confidence: {rec.get('confidence_score', 0):.2f}")
                lines.append(f"   Expected Benefit: {rec.get('expected_benefit')}")
                lines.append(f"   Proposed Change: {rec.get('proposed_change')}")
                lines.append("")
        else:
            lines.append("No new recommendations generated.")
            lines.append("")

        lines.append("This report is automatically generated and stored for audit/review.")
        report_text = "\n".join(lines)

        try:
            with report_path.open("w", encoding="utf-8") as fh:
                fh.write(report_text)
        except Exception as e:
            self.logger.error(f"Failed to write analysis report: {e}")
            return report_text, None

        return report_text, report_path

    def _store_analysis_history(self, findings: Dict, recommendations_count: int, report_path: Optional[Path]):
        """Store analysis history"""
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        findings_copy = dict(findings)
        if report_path:
            findings_copy["report_path"] = str(report_path)

        cursor.execute("""
            INSERT INTO analysis_history
            (analysis_type, findings, recommendations_count, analyzed_at)
            VALUES (?, ?, ?, ?)
        """, (
            "software_usage_analysis",
            json.dumps(findings_copy),
            recommendations_count,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_pending_recommendations(self) -> List[Dict]:
        """Get all pending recommendations"""
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM optimization_recommendations
            WHERE status = 'pending'
            ORDER BY confidence_score DESC, created_at DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        recommendations = []
        for row in cursor.fetchall():
            rec = dict(zip(columns, row))
            if rec.get("data_evidence"):
                rec["data_evidence"] = json.loads(rec["data_evidence"])
            recommendations.append(rec)
        
        conn.close()
        return recommendations
    
    def approve_recommendation(self, recommendation_id: int, admin_password: str) -> bool:
        """Approve a recommendation (admin only)"""
        # Verify admin access
        if ADMIN_STORAGE_AVAILABLE:
            admin_storage = AdminSecureStorage(self.installation_dir)
            if not admin_storage.authenticate(admin_password):
                return False
        
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE optimization_recommendations
            SET status = 'approved', approved_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), recommendation_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Recommendation {recommendation_id} approved by admin")
        return True
    
    def reject_recommendation(self, recommendation_id: int, admin_password: str) -> bool:
        """Reject a recommendation (admin only)"""
        # Verify admin access
        if ADMIN_STORAGE_AVAILABLE:
            admin_storage = AdminSecureStorage(self.installation_dir)
            if not admin_storage.authenticate(admin_password):
                return False
        
        conn = sqlite3.connect(self.recommendations_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE optimization_recommendations
            SET status = 'rejected', rejected_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), recommendation_id))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Recommendation {recommendation_id} rejected by admin")
        return True
    
    def start_continuous_analysis(self):
        """Start continuous analysis (runs daily)"""
        import threading
        
        def analysis_loop():
            while self.analysis_active:
                try:
                    self.analyze_software_usage()
                    time.sleep(self.analysis_interval_hours * 3600)  # Wait for interval
                except Exception as e:
                    self.logger.error(f"Error in continuous analysis: {e}")
                    time.sleep(3600)  # Retry in 1 hour
        
        thread = threading.Thread(target=analysis_loop, daemon=True)
        thread.start()
        self.logger.info(f"Continuous analysis started (interval: {self.analysis_interval_hours} hours)")

