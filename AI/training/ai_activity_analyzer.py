#!/usr/bin/env python3
"""
AI Activity Analyzer
Analyzes recorded activity data to extract patterns and train AI models.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
import logging


class AIActivityAnalyzer:
    """
    Analyzes recorded activity data to extract patterns for AI training.
    Identifies workflows, sequences, and behaviors.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize AI activity analyzer"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        # Database is actually stored in _secure_data/full_monitoring (not AI/data/full_monitoring)
        self.data_dir = installation_dir / "_secure_data" / "full_monitoring"
        self.models_dir = ai_dir / "models"
        self.models_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Database
        self.db_path = self.data_dir / "full_monitoring.db"
        
        # Setup logging
        self.log_file = self.models_dir / "activity_analysis.log"
        self._setup_logging()
        
        # Analysis settings
        self.min_pattern_frequency = 3  # Minimum occurrences to be a pattern
        self.sequence_window_seconds = 60  # Time window for sequences
    
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
    
    def analyze_session(self, session_id: str) -> Dict:
        """Analyze a specific session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all activity for session
            activities = []
            
            # Get screen recordings
            cursor.execute("""
                SELECT timestamp, window_title, active_app
                FROM screen_recordings
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": row[0],
                    "type": "screen",
                    "window_title": row[1],
                    "active_app": row[2]
                })
            
            # Get keyboard input
            cursor.execute("""
                SELECT timestamp, key_pressed, active_app, window_title
                FROM keyboard_input
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": row[0],
                    "type": "keyboard",
                    "key": row[1],
                    "active_app": row[2],
                    "window_title": row[3]
                })
            
            # Get mouse activity
            cursor.execute("""
                SELECT timestamp, event_type, x_position, y_position, active_app, window_title
                FROM mouse_activity
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": row[0],
                    "type": "mouse",
                    "event_type": row[1],
                    "x": row[2],
                    "y": row[3],
                    "active_app": row[4],
                    "window_title": row[5]
                })
            
            # Get application usage
            cursor.execute("""
                SELECT timestamp, app_name, window_title, duration_seconds
                FROM application_usage
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": row[0],
                    "type": "app",
                    "app_name": row[1],
                    "window_title": row[2],
                    "duration": row[3]
                })
            
            # Get file activity
            cursor.execute("""
                SELECT timestamp, event_type, file_path, file_type, app_name
                FROM file_activity
                WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            for row in cursor.fetchall():
                activities.append({
                    "timestamp": row[0],
                    "type": "file",
                    "event_type": row[1],
                    "file_path": row[2],
                    "file_type": row[3],
                    "app_name": row[4]
                })
            
            # Sort by timestamp
            activities.sort(key=lambda x: x["timestamp"])
            
            # Extract patterns
            patterns = self._extract_patterns(activities)
            
            # Extract sequences
            sequences = self._extract_sequences(activities)
            
            conn.close()
            
            return {
                "session_id": session_id,
                "total_activities": len(activities),
                "patterns": patterns,
                "sequences": sequences,
                "workflows": self._identify_workflows(activities)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing session: {e}")
            return {}
    
    def _extract_patterns(self, activities: List[Dict]) -> List[Dict]:
        """Extract patterns from activities"""
        patterns = []
        
        # Group by app and window
        app_patterns = defaultdict(list)
        for activity in activities:
            app = activity.get("active_app") or activity.get("app_name", "Unknown")
            window = activity.get("window_title", "Unknown")
            key = f"{app}:{window}"
            app_patterns[key].append(activity)
        
        # Identify frequent patterns
        for key, activities_list in app_patterns.items():
            if len(activities_list) >= self.min_pattern_frequency:
                app, window = key.split(":", 1)
                patterns.append({
                    "pattern_type": "app_usage",
                    "app": app,
                    "window": window,
                    "frequency": len(activities_list),
                    "activities": activities_list[:10]  # Sample
                })
        
        return patterns
    
    def _extract_sequences(self, activities: List[Dict]) -> List[Dict]:
        """Extract activity sequences"""
        sequences = []
        
        # Group activities by time window
        current_sequence = []
        last_timestamp = None
        
        for activity in activities:
            timestamp = datetime.fromisoformat(activity["timestamp"])
            
            if last_timestamp:
                time_diff = (timestamp - last_timestamp).total_seconds()
                
                # If gap is too large, start new sequence
                if time_diff > self.sequence_window_seconds:
                    if len(current_sequence) >= 3:  # Minimum sequence length
                        sequences.append({
                            "sequence": current_sequence,
                            "duration": (timestamp - datetime.fromisoformat(current_sequence[0]["timestamp"])).total_seconds(),
                            "activities": len(current_sequence)
                        })
                    current_sequence = []
            
            current_sequence.append(activity)
            last_timestamp = timestamp
        
        # Add final sequence
        if len(current_sequence) >= 3:
            sequences.append({
                "sequence": current_sequence,
                "duration": (datetime.fromisoformat(current_sequence[-1]["timestamp"]) - 
                           datetime.fromisoformat(current_sequence[0]["timestamp"])).total_seconds(),
                "activities": len(current_sequence)
            })
        
        return sequences
    
    def _identify_workflows(self, activities: List[Dict]) -> List[Dict]:
        """Identify workflows from activities"""
        workflows = []
        
        # Identify common workflow patterns
        # Example: App switch → Keyboard input → Mouse click → File save
        
        workflow_patterns = [
            {"type": "app", "action": "switch"},
            {"type": "keyboard", "action": "input"},
            {"type": "mouse", "action": "click"},
            {"type": "file", "action": "save"}
        ]
        
        # Find matching sequences
        for i in range(len(activities) - len(workflow_patterns)):
            sequence = activities[i:i+len(workflow_patterns)]
            
            # Check if sequence matches pattern
            matches = True
            for j, pattern in enumerate(workflow_patterns):
                if sequence[j].get("type") != pattern["type"]:
                    matches = False
                    break
            
            if matches:
                workflows.append({
                    "workflow_type": "standard_workflow",
                    "sequence": sequence,
                    "start_time": sequence[0]["timestamp"],
                    "end_time": sequence[-1]["timestamp"]
                })
        
        return workflows
    
    def generate_training_data(self, session_ids: Optional[List[str]] = None) -> List[Dict]:
        """Generate training data from recorded sessions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all sessions if not specified
            if session_ids is None:
                cursor.execute("SELECT DISTINCT session_id FROM screen_recordings")
                session_ids = [row[0] for row in cursor.fetchall()]
            
            training_data = []
            
            for session_id in session_ids:
                analysis = self.analyze_session(session_id)
                
                # Convert to training format
                training_example = {
                    "session_id": session_id,
                    "patterns": analysis.get("patterns", []),
                    "sequences": analysis.get("sequences", []),
                    "workflows": analysis.get("workflows", [])
                }
                
                training_data.append(training_example)
            
            conn.close()
            
            # Save training data
            training_file = self.models_dir / "training_data.json"
            with open(training_file, 'w', encoding='utf-8') as f:
                json.dump(training_data, f, indent=2, default=str)
            
            self.logger.info(f"Generated training data for {len(training_data)} sessions")
            
            return training_data
            
        except Exception as e:
            self.logger.error(f"Error generating training data: {e}")
            return []


if __name__ == "__main__":
    analyzer = AIActivityAnalyzer()
    training_data = analyzer.generate_training_data()
    print(f"Generated training data for {len(training_data)} sessions")

