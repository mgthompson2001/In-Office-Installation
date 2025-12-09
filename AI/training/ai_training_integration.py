#!/usr/bin/env python3
"""
AI Training Integration - Automatic AI Training from Full System Monitoring
Automatically processes recorded data to train AI models that understand every motion.
For training employee models later.
"""

import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import json

# Import full system monitor
try:
    from full_system_monitor import FullSystemMonitor, get_full_monitor
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False
    FullSystemMonitor = None
    get_full_monitor = None

# Import AI analyzer
try:
    from ai_activity_analyzer import AIActivityAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    AIActivityAnalyzer = None

# Import local AI trainer
try:
    from local_ai_trainer import LocalAITrainer
    TRAINER_AVAILABLE = True
except ImportError:
    TRAINER_AVAILABLE = False
    LocalAITrainer = None

# Import Context Understanding Engine
try:
    import sys
    from pathlib import Path
    intelligence_dir = Path(__file__).parent.parent / "intelligence"
    sys.path.insert(0, str(intelligence_dir))
    from context_understanding_engine import ContextUnderstandingEngine
    CONTEXT_ENGINE_AVAILABLE = True
except ImportError:
    CONTEXT_ENGINE_AVAILABLE = False
    ContextUnderstandingEngine = None


class AITrainingIntegration:
    """
    Integrates full system monitoring with AI training.
    Automatically processes recorded data to understand every motion.
    Trains AI models for employee model training.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize AI training integration"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        # Database is actually stored in _secure_data/full_monitoring (not AI/data/full_monitoring)
        self.data_dir = installation_dir / "_secure_data" / "full_monitoring"
        self.models_dir = ai_dir / "models"
        self.models_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Setup logging
        self.log_file = self.models_dir / "ai_training_integration.log"
        self._setup_logging()
        
        # Initialize components
        self.monitor = None
        self.analyzer = None
        self.trainer = None
        self.context_engine = None
        
        # Processing state
        self.processing_active = False
        self.processing_thread = None
        
        # Training settings
        self.analysis_interval_seconds = 300  # Analyze every 5 minutes
        self.training_interval_hours = 24  # Train daily
        self.min_data_points = 100  # Minimum data points before training
        
        # Last processing times
        self.last_analysis_time = None
        self.last_training_time = None
        
        # Initialize components
        self._initialize_components()
    
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
    
    def _initialize_components(self):
        """Initialize AI components"""
        try:
            # Initialize monitor
            if MONITOR_AVAILABLE:
                self.monitor = get_full_monitor(self.installation_dir, user_consent=True)
                self.logger.info("Full system monitor initialized")
            else:
                self.logger.warning("Full system monitor not available")
            
            # Initialize analyzer
            if ANALYZER_AVAILABLE:
                self.analyzer = AIActivityAnalyzer(self.installation_dir)
                self.logger.info("AI activity analyzer initialized")
            else:
                self.logger.warning("AI activity analyzer not available")
            
            # Initialize trainer
            if TRAINER_AVAILABLE:
                self.trainer = LocalAITrainer(self.installation_dir)
                self.logger.info("Local AI trainer initialized")
            else:
                self.logger.warning("Local AI trainer not available")
            
            # Initialize Context Understanding Engine
            if CONTEXT_ENGINE_AVAILABLE:
                self.context_engine = ContextUnderstandingEngine(self.installation_dir)
                self.logger.info("Context Understanding Engine initialized")
            else:
                self.logger.warning("Context Understanding Engine not available")
        
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
    
    def start_automatic_processing(self):
        """Start automatic processing of recorded data"""
        if self.processing_active:
            self.logger.warning("Processing already active")
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        self.logger.info("Automatic AI training processing started")
    
    def stop_automatic_processing(self):
        """Stop automatic processing"""
        self.processing_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        self.logger.info("Automatic AI training processing stopped")
    
    def _processing_loop(self):
        """Main processing loop"""
        while self.processing_active:
            try:
                # Check if monitoring is active
                if self.monitor and self.monitor.monitoring_active:
                    # Analyze recent data
                    self._analyze_recent_data()
                    
                    # Check if enough data for training
                    if self._has_enough_data():
                        # Train model
                        self._train_model()
                
                # Sleep until next check
                time.sleep(self.analysis_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _analyze_recent_data(self):
        """Analyze recent recorded data"""
        try:
            if not self.analyzer:
                return
            
            # Get recent sessions
            recent_sessions = self._get_recent_sessions()
            
            if not recent_sessions:
                return
            
            self.logger.info(f"Analyzing {len(recent_sessions)} recent sessions...")
            
            # Analyze each session
            for session_id in recent_sessions:
                try:
                    analysis = self.analyzer.analyze_session(session_id)
                    
                    # Extract patterns
                    patterns = analysis.get("patterns", [])
                    sequences = analysis.get("sequences", [])
                    workflows = analysis.get("workflows", [])
                    
                    # Log findings
                    if patterns:
                        self.logger.info(f"Session {session_id}: Found {len(patterns)} patterns")
                    if sequences:
                        self.logger.info(f"Session {session_id}: Found {len(sequences)} sequences")
                    if workflows:
                        self.logger.info(f"Session {session_id}: Found {len(workflows)} workflows")
                    
                    # Store analysis results
                    self._store_analysis(session_id, analysis)
                    
                    # Understand context (NEW - Context Understanding Engine)
                    if self.context_engine:
                        try:
                            understanding = self.context_engine.understand_session(session_id)
                            if understanding:
                                self.logger.info(f"Session {session_id}: Context understood - "
                                               f"{len(understanding.get('intent_understanding', []))} intents, "
                                               f"{len(understanding.get('context_understanding', []))} contexts, "
                                               f"{len(understanding.get('dependency_mapping', []))} dependencies, "
                                               f"{len(understanding.get('goal_understanding', []))} goals")
                        except Exception as e:
                            self.logger.error(f"Error understanding context for session {session_id}: {e}")
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing session {session_id}: {e}")
            
            self.last_analysis_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error in analyze_recent_data: {e}")
    
    def _get_recent_sessions(self, hours: int = 24) -> List[str]:
        """Get recent session IDs"""
        try:
            import sqlite3
            
            db_path = self.data_dir / "full_monitoring.db"
            if not db_path.exists():
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get sessions from last N hours
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute("""
                SELECT DISTINCT session_id 
                FROM screen_recordings 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (cutoff_time,))
            
            sessions = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error getting recent sessions: {e}")
            return []
    
    def _store_analysis(self, session_id: str, analysis: Dict):
        """Store analysis results"""
        try:
            analysis_file = self.models_dir / f"analysis_{session_id}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            self.logger.debug(f"Stored analysis for session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing analysis: {e}")
    
    def _has_enough_data(self) -> bool:
        """Check if there's enough data for training"""
        try:
            import sqlite3
            
            db_path = self.data_dir / "full_monitoring.db"
            if not db_path.exists():
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Count total data points
            cursor.execute("SELECT COUNT(*) FROM screen_recordings")
            screen_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM keyboard_input")
            keyboard_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mouse_activity")
            mouse_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM application_usage")
            app_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM file_activity")
            file_count = cursor.fetchone()[0]
            
            total_data_points = screen_count + keyboard_count + mouse_count + app_count + file_count
            
            conn.close()
            
            has_enough = total_data_points >= self.min_data_points
            
            if has_enough:
                self.logger.info(f"Enough data for training: {total_data_points} data points")
            
            return has_enough
            
        except Exception as e:
            self.logger.error(f"Error checking data: {e}")
            return False
    
    def _train_model(self):
        """Train AI model from recorded data"""
        try:
            if not self.trainer:
                return
            
            # Check if it's time to train (daily)
            if self.last_training_time:
                time_since_training = (datetime.now() - self.last_training_time).total_seconds()
                if time_since_training < (self.training_interval_hours * 3600):
                    return  # Not time to train yet
            
            self.logger.info("Starting AI model training...")
            
            # Generate training data
            if not self.analyzer:
                return
            
            training_data = self.analyzer.generate_training_data()
            
            if not training_data:
                self.logger.warning("No training data generated")
                return
            
            self.logger.info(f"Generated training data from {len(training_data)} sessions")
            
            # Train model
            if self.trainer:
                # Prepare training data for model
                prepared_data = self._prepare_training_data(training_data)
                
                # Train model
                success = self.trainer.train_model(prepared_data)
                
                if success:
                    self.logger.info("AI model training completed successfully")
                    self.last_training_time = datetime.now()
                else:
                    self.logger.warning("AI model training failed")
            
        except Exception as e:
            self.logger.error(f"Error in train_model: {e}")
    
    def _prepare_training_data(self, training_data: List[Dict]) -> List[Dict]:
        """Prepare training data for model training"""
        try:
            prepared = []
            
            for session_data in training_data:
                # Extract patterns, sequences, and workflows
                patterns = session_data.get("patterns", [])
                sequences = session_data.get("sequences", [])
                workflows = session_data.get("workflows", [])
                
                # Create training examples
                for pattern in patterns:
                    prepared.append({
                        "type": "pattern",
                        "data": pattern,
                        "session_id": session_data.get("session_id")
                    })
                
                for sequence in sequences:
                    prepared.append({
                        "type": "sequence",
                        "data": sequence,
                        "session_id": session_data.get("session_id")
                    })
                
                for workflow in workflows:
                    prepared.append({
                        "type": "workflow",
                        "data": workflow,
                        "session_id": session_data.get("session_id")
                    })
            
            return prepared
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return []
    
    def get_training_status(self) -> Dict:
        """Get current training status"""
        return {
            "processing_active": self.processing_active,
            "monitoring_active": self.monitor.monitoring_active if self.monitor else False,
            "last_analysis_time": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "has_enough_data": self._has_enough_data(),
            "components_available": {
                "monitor": MONITOR_AVAILABLE,
                "analyzer": ANALYZER_AVAILABLE,
                "trainer": TRAINER_AVAILABLE
            }
        }


# Global integration instance
_global_integration = None


def get_ai_training_integration(installation_dir: Optional[Path] = None) -> AITrainingIntegration:
    """Get global AI training integration instance"""
    global _global_integration
    if _global_integration is None:
        _global_integration = AITrainingIntegration(installation_dir)
    return _global_integration


def start_ai_training(installation_dir: Optional[Path] = None) -> AITrainingIntegration:
    """Start automatic AI training from full system monitoring"""
    integration = get_ai_training_integration(installation_dir)
    integration.start_automatic_processing()
    return integration


def stop_ai_training():
    """Stop automatic AI training"""
    global _global_integration
    if _global_integration:
        _global_integration.stop_automatic_processing()
        _global_integration = None

