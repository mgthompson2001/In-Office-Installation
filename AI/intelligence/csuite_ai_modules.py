#!/usr/bin/env python3
"""
C-Suite AI Modules - Revolutionary Enterprise Intelligence
Autonomous functions for finance, analytics, performance monitoring, and more.
This transforms your AI from simple automation to C-suite level intelligence.
"""

import os
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Data analysis
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Advanced analytics
try:
    from collections import Counter, defaultdict
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


class CSuiteAIModules:
    """
    C-Suite level AI modules for enterprise intelligence:
    - Finance reports and analytics
    - Data analysis and insights
    - Employee performance monitoring
    - Autonomous decision making
    - Strategic planning
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize C-Suite AI modules"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        self.intelligence_dir = ai_dir / "intelligence"
        self.intelligence_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Reports directory - use AI Analysis reports folder
        ai_dir = installation_dir / "AI"
        self.reports_dir = ai_dir / "AI Analysis reports"
        self.reports_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Analytics database
        self.analytics_db = self.intelligence_dir / "csuite_analytics.db"
        self._init_analytics_database()
        
        # Setup logging
        self.log_file = self.intelligence_dir / "csuite_modules.log"
        self._setup_logging()
    
    def _init_analytics_database(self):
        """Initialize analytics database"""
        conn = sqlite3.connect(self.analytics_db)
        cursor = conn.cursor()
        
        # Finance reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS finance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT NOT NULL,
                report_type TEXT,
                data_period TEXT,
                metrics TEXT,
                insights TEXT,
                generated_at TEXT,
                report_data TEXT
            )
        """)
        
        # Employee performance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_hash TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT,
                metrics TEXT,
                performance_score REAL,
                analyzed_at TEXT
            )
        """)
        
        # Data analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_type TEXT NOT NULL,
                data_source TEXT,
                insights TEXT,
                metrics TEXT,
                generated_at TEXT
            )
        """)
        
        # Strategic decisions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategic_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_type TEXT NOT NULL,
                decision_data TEXT,
                confidence_score REAL,
                reasoning TEXT,
                executed INTEGER DEFAULT 0,
                created_at TEXT
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
    
    # ==================== FINANCE MODULE ====================
    
    def generate_finance_report(self, period: str = "monthly") -> Dict:
        """
        Generate comprehensive finance report.
        Analyzes bot execution data to generate financial insights.
        """
        self.logger.info(f"Generating {period} finance report")
        
        # Get data from secure data collector
        from secure_data_collector import SecureDataCollector
        collector = SecureDataCollector(self.installation_dir)
        
        # Get bot execution data
        history = collector.get_workflow_history(days=30 if period == "monthly" else 7)
        
        # Calculate metrics
        metrics = self._calculate_finance_metrics(history, period)
        
        # Generate insights
        insights = self._generate_finance_insights(metrics, period)
        
        # Create report
        report = {
            "report_name": f"{period.title()} Finance Report",
            "report_type": "finance",
            "data_period": period,
            "metrics": metrics,
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "report_data": json.dumps({
                "total_executions": len(history),
                "success_rate": sum(1 for h in history if h.get("success")) / len(history) if history else 0,
                "average_execution_time": sum(h.get("execution_time", 0) for h in history) / len(history) if history else 0,
                "bots_used": len(set(h.get("bot_name") for h in history if h.get("bot_name")))
            })
        }
        
        # Store report
        self._store_finance_report(report)
        
        # Save report file
        report_file = self.reports_dir / f"finance_report_{period}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Finance report generated: {report_file}")
        return report
    
    def _calculate_finance_metrics(self, history: List[Dict], period: str) -> Dict:
        """Calculate finance metrics from bot execution history"""
        if not history:
            return {}
        
        metrics = {
            "total_executions": len(history),
            "successful_executions": sum(1 for h in history if h.get("success")),
            "failed_executions": sum(1 for h in history if not h.get("success")),
            "success_rate": sum(1 for h in history if h.get("success")) / len(history),
            "average_execution_time": sum(h.get("execution_time", 0) for h in history) / len(history),
            "total_execution_time": sum(h.get("execution_time", 0) for h in history),
            "bots_used": len(set(h.get("bot_name") for h in history if h.get("bot_name"))),
            "unique_users": len(set(h.get("user_name") for h in history if h.get("user_name")))
        }
        
        # Bot-specific metrics
        bot_metrics = {}
        for record in history:
            bot_name = record.get("bot_name")
            if bot_name:
                if bot_name not in bot_metrics:
                    bot_metrics[bot_name] = {
                        "count": 0,
                        "successes": 0,
                        "total_time": 0
                    }
                bot_metrics[bot_name]["count"] += 1
                if record.get("success"):
                    bot_metrics[bot_name]["successes"] += 1
                bot_metrics[bot_name]["total_time"] += record.get("execution_time", 0)
        
        metrics["bot_metrics"] = bot_metrics
        
        return metrics
    
    def _generate_finance_insights(self, metrics: Dict, period: str) -> List[str]:
        """Generate financial insights from metrics"""
        insights = []
        
        if metrics.get("success_rate", 0) > 0.9:
            insights.append("✅ High success rate indicates efficient automation")
        elif metrics.get("success_rate", 0) < 0.7:
            insights.append("⚠️ Low success rate may indicate need for optimization")
        
        if metrics.get("average_execution_time", 0) > 300:
            insights.append("⏱️ Average execution time is high - consider optimization")
        
        if metrics.get("bots_used", 0) > 10:
            insights.append("📊 Multiple bots in use - good automation coverage")
        
        # Bot-specific insights
        bot_metrics = metrics.get("bot_metrics", {})
        if bot_metrics:
            most_used_bot = max(bot_metrics.items(), key=lambda x: x[1]["count"])
            insights.append(f"🔝 Most used bot: {most_used_bot[0]} ({most_used_bot[1]['count']} executions)")
        
        return insights
    
    def _store_finance_report(self, report: Dict):
        """Store finance report in database"""
        conn = sqlite3.connect(self.analytics_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO finance_reports
            (report_name, report_type, data_period, metrics, insights, generated_at, report_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            report["report_name"],
            report["report_type"],
            report["data_period"],
            json.dumps(report["metrics"]),
            json.dumps(report["insights"]),
            report["generated_at"],
            report["report_data"]
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== ANALYTICS MODULE ====================
    
    def analyze_data_patterns(self) -> Dict:
        """Analyze data patterns and generate insights"""
        self.logger.info("Analyzing data patterns")
        
        from secure_data_collector import SecureDataCollector
        collector = SecureDataCollector(self.installation_dir)
        
        # Get training data
        training_data = collector.get_training_data(anonymized=True)
        
        # Analyze patterns
        patterns = self._analyze_patterns(training_data)
        
        # Generate insights
        insights = self._generate_analytics_insights(patterns)
        
        analysis = {
            "analysis_type": "data_patterns",
            "data_source": "collected_data",
            "insights": insights,
            "metrics": patterns,
            "generated_at": datetime.now().isoformat()
        }
        
        # Store analysis
        self._store_analytics(analysis)
        
        return analysis
    
    def _analyze_patterns(self, training_data: List[Dict]) -> Dict:
        """Analyze patterns in training data"""
        patterns = {
            "total_patterns": len(training_data),
            "unique_patterns": len(set(d.get("pattern_hash") for d in training_data if d.get("pattern_hash"))),
            "frequency_distribution": {},
            "confidence_distribution": {}
        }
        
        # Frequency analysis
        frequency_counter = Counter()
        confidence_values = []
        
        for data in training_data:
            if isinstance(data.get("anonymized_data"), str):
                data_dict = json.loads(data["anonymized_data"])
            else:
                data_dict = data.get("anonymized_data", {})
            
            bot = data_dict.get("bot_selected", "")
            confidence = data_dict.get("confidence", 0.0)
            
            if bot:
                frequency_counter[bot] += data.get("frequency", 1)
            
            if confidence:
                confidence_values.append(confidence)
        
        patterns["frequency_distribution"] = dict(frequency_counter)
        patterns["confidence_distribution"] = {
            "mean": np.mean(confidence_values) if confidence_values else 0,
            "std": np.std(confidence_values) if confidence_values else 0,
            "min": np.min(confidence_values) if confidence_values else 0,
            "max": np.max(confidence_values) if confidence_values else 0
        } if PANDAS_AVAILABLE and confidence_values else {}
        
        return patterns
    
    def _generate_analytics_insights(self, patterns: Dict) -> List[str]:
        """Generate analytics insights"""
        insights = []
        
        unique_patterns = patterns.get("unique_patterns", 0)
        total_patterns = patterns.get("total_patterns", 0)
        
        if unique_patterns > 50:
            insights.append(f"📊 {unique_patterns} unique patterns discovered - strong learning base")
        
        confidence_dist = patterns.get("confidence_distribution", {})
        if confidence_dist.get("mean", 0) > 0.85:
            insights.append("✅ High average confidence indicates accurate AI predictions")
        
        frequency_dist = patterns.get("frequency_distribution", {})
        if frequency_dist:
            most_common = max(frequency_dist.items(), key=lambda x: x[1])
            insights.append(f"🔝 Most common bot usage: {most_common[0]} ({most_common[1]} times)")
        
        return insights
    
    def _store_analytics(self, analysis: Dict):
        """Store analytics in database"""
        conn = sqlite3.connect(self.analytics_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO data_analytics
            (analysis_type, data_source, insights, metrics, generated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            analysis["analysis_type"],
            analysis["data_source"],
            json.dumps(analysis["insights"]),
            json.dumps(analysis["metrics"]),
            analysis["generated_at"]
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== PERFORMANCE MONITORING MODULE ====================
    
    def monitor_employee_performance(self, period_days: int = 30) -> Dict:
        """Monitor employee performance based on bot usage"""
        self.logger.info(f"Monitoring employee performance (last {period_days} days)")
        
        from secure_data_collector import SecureDataCollector
        collector = SecureDataCollector(self.installation_dir)
        
        # Get execution history
        history = collector.get_workflow_history(days=period_days)
        
        # Analyze by employee
        employee_metrics = self._calculate_employee_metrics(history)
        
        # Generate performance scores
        performance_scores = self._calculate_performance_scores(employee_metrics)
        
        # Store performance data
        for employee_hash, metrics in employee_metrics.items():
            self._store_employee_performance(employee_hash, metrics, period_days)
        
        return {
            "period_days": period_days,
            "employee_metrics": employee_metrics,
            "performance_scores": performance_scores,
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_employee_metrics(self, history: List[Dict]) -> Dict:
        """Calculate metrics per employee"""
        employee_metrics = defaultdict(lambda: {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0,
            "unique_bots_used": set(),
            "average_confidence": []
        })
        
        for record in history:
            user_hash = record.get("user_hash") or record.get("user_name", "Unknown")
            
            metrics = employee_metrics[user_hash]
            metrics["total_executions"] += 1
            
            if record.get("success"):
                metrics["successful_executions"] += 1
            else:
                metrics["failed_executions"] += 1
            
            metrics["total_execution_time"] += record.get("execution_time", 0)
            
            bot_name = record.get("bot_name")
            if bot_name:
                metrics["unique_bots_used"].add(bot_name)
            
            # Convert sets to counts for JSON serialization
            for hash_val, metrics in employee_metrics.items():
                metrics["unique_bots_used"] = len(metrics["unique_bots_used"])
        
        return dict(employee_metrics)
    
    def _calculate_performance_scores(self, employee_metrics: Dict) -> Dict:
        """Calculate performance scores for employees"""
        scores = {}
        
        for employee_hash, metrics in employee_metrics.items():
            total = metrics["total_executions"]
            if total == 0:
                continue
            
            success_rate = metrics["successful_executions"] / total
            efficiency = metrics["unique_bots_used"] / max(metrics["total_executions"], 1)
            activity_score = min(metrics["total_executions"] / 50, 1.0)  # Normalize to 1.0
            
            performance_score = (
                success_rate * 0.4 +
                efficiency * 0.3 +
                activity_score * 0.3
            )
            
            scores[employee_hash] = {
                "performance_score": performance_score,
                "success_rate": success_rate,
                "efficiency": efficiency,
                "activity_level": activity_score
            }
        
        return scores
    
    def _store_employee_performance(self, employee_hash: str, metrics: Dict, period_days: int):
        """Store employee performance data"""
        conn = sqlite3.connect(self.analytics_db)
        cursor = conn.cursor()
        
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        performance_score = (
            (metrics["successful_executions"] / max(metrics["total_executions"], 1)) * 0.4 +
            (metrics["unique_bots_used"] / max(metrics["total_executions"], 1)) * 0.3 +
            (min(metrics["total_executions"] / 50, 1.0)) * 0.3
        )
        
        cursor.execute("""
            INSERT INTO employee_performance
            (employee_hash, period_start, period_end, metrics, performance_score, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            employee_hash,
            period_start.isoformat(),
            period_end.isoformat(),
            json.dumps(metrics),
            performance_score,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== STRATEGIC DECISION MODULE ====================
    
    def make_strategic_decision(self, decision_type: str, context: Dict) -> Dict:
        """Make strategic decisions based on collected intelligence"""
        self.logger.info(f"Making strategic decision: {decision_type}")
        
        # Analyze context
        analysis = self._analyze_decision_context(decision_type, context)
        
        # Calculate confidence
        confidence = self._calculate_decision_confidence(analysis)
        
        # Generate decision
        decision = {
            "decision_type": decision_type,
            "decision_data": json.dumps(analysis),
            "confidence_score": confidence,
            "reasoning": self._generate_decision_reasoning(analysis, confidence),
            "executed": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # Store decision
        self._store_strategic_decision(decision)
        
        return decision
    
    def _analyze_decision_context(self, decision_type: str, context: Dict) -> Dict:
        """Analyze context for decision making"""
        # This would use AI to analyze context
        # For now, basic analysis
        return {
            "context": context,
            "analysis": "Basic context analysis",
            "factors": ["factor1", "factor2"]
        }
    
    def _calculate_decision_confidence(self, analysis: Dict) -> float:
        """Calculate confidence score for decision"""
        # Simple confidence calculation
        # In production, this would use ML models
        return 0.85  # Placeholder
    
    def _generate_decision_reasoning(self, analysis: Dict, confidence: float) -> str:
        """Generate reasoning for decision"""
        return f"Decision based on analysis with {confidence:.2%} confidence"
    
    def _store_strategic_decision(self, decision: Dict):
        """Store strategic decision"""
        conn = sqlite3.connect(self.analytics_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO strategic_decisions
            (decision_type, decision_data, confidence_score, reasoning, executed, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            decision["decision_type"],
            decision["decision_data"],
            decision["confidence_score"],
            decision["reasoning"],
            decision["executed"],
            decision["created_at"]
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== AUTOMATED REPORTING ====================
    
    def generate_daily_report(self) -> Dict:
        """Generate daily C-Suite report"""
        self.logger.info("Generating daily C-Suite report")
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "finance_report": self.generate_finance_report("daily"),
            "analytics": self.analyze_data_patterns(),
            "employee_performance": self.monitor_employee_performance(7),
            "generated_at": datetime.now().isoformat()
        }
        
        # Save report
        report_file = self.reports_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Daily report generated: {report_file}")
        return report
    
    def start_automated_reporting(self, interval_hours: int = 24):
        """Start automated daily reporting"""
        def reporting_loop():
            while True:
                try:
                    self.generate_daily_report()
                    time.sleep(interval_hours * 3600)
                except Exception as e:
                    self.logger.error(f"Error in automated reporting: {e}")
                    time.sleep(3600)  # Retry in 1 hour
        
        thread = threading.Thread(target=reporting_loop, daemon=True)
        thread.start()
        self.logger.info(f"Automated reporting started (interval: {interval_hours} hours)")

