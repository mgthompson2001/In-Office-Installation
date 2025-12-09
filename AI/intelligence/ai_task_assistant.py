#!/usr/bin/env python3
"""
AI Task Assistant - Intelligent Bot Orchestrator
This module provides natural language task interpretation and automatic bot routing.
"""

import os
import sys
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# Import the AI Agent
try:
    from ai_agent import AIAgent
except ImportError:
    # Fallback if import fails
    AIAgent = None

# Import learning systems
try:
    from workflow_recorder import WorkflowRecorder
    from intelligent_learning import IntelligentLearning
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    WorkflowRecorder = None
    IntelligentLearning = None


class AITaskAssistant:
    """
    Main orchestrator class that interprets natural language commands
    and routes them to appropriate bots.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """
        Initialize the AI Task Assistant.
        
        Args:
            installation_dir: Base installation directory (auto-detected if None)
        """
        # Auto-detect installation directory
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.ai_agent = AIAgent() if AIAgent else None
        
        # Initialize learning systems
        if LEARNING_AVAILABLE:
            self.workflow_recorder = WorkflowRecorder(installation_dir)
            self.learning_system = IntelligentLearning(installation_dir)
        else:
            self.workflow_recorder = None
            self.learning_system = None
        
        # Setup logging
        self.log_file = self.installation_dir / "_system" / "ai_assistant_log.txt"
        self._setup_logging()
        
        # Initialize bot map
        self._setup_bot_map()
    
    def _setup_logging(self):
        """Setup logging to file and console"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_bot_map(self):
        """
        Map bot identifiers to actual bot file paths.
        This maps the AI's interpretation to actual executable bots.
        """
        bots_dir = self.installation_dir / "_bots"
        
        self.BOT_MAP = {
            # Medical Records
            "medical_records": {
                "path": str(bots_dir / "Med Rec" / "Finished Product, Launch Ready" / "Bot and extender" / "integrity_medical_records_bot_v3g_batchclicks.py"),
                "name": "Medical Records Bot",
                "keywords": ["medical record", "med rec", "medical records"]
            },
            
            # Consent Forms
            "consent_form": {
                "path": str(bots_dir / "The Welcomed One, Exalted Rank" / "integrity_consent_bot_v2.py"),
                "name": "Consent Form Bot",
                "keywords": ["consent", "consent form"]
            },
            
            # Welcome Letters
            "welcome_letter": {
                "path": str(bots_dir / "The Welcomed One, Exalted Rank" / "isws_welcome_DEEPFIX2_NOTEFORCE_v14.py"),
                "name": "Welcome Letter Bot",
                "keywords": ["welcome", "welcome letter"]
            },
            
            # Billing Department - Medisoft
            "medisoft_billing": {
                "path": str(bots_dir / "Billing Department" / "Medisoft Billing" / "medisoft_billing_bot.py"),
                "name": "Medical Records Billing Log Bot",
                "keywords": ["medisoft", "billing", "insurance claim", "claim"]
            },
            
            # Billing Department - TN Refiling
            "tn_refiling": {
                "path": str(bots_dir / "Billing Department" / "TN Refiling Bot" / "tn_refiling_bot.py"),
                "name": "TN Refiling Bot",
                "keywords": ["tn refiling", "refiling", "therapy notes"]
            },
            
            # Billing Department Launcher
            "billing": {
                "path": str(bots_dir / "Billing Department" / "billing_department_launcher.py"),
                "name": "Billing Department",
                "keywords": ["billing department"]
            },
            
            # Intake & Referral - Referral Form
            "referral": {
                "path": str(bots_dir / "Referral bot and bridge (final)" / "isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py"),
                "name": "Referral Form/Upload Bot",
                "keywords": ["referral", "intake", "referral form"]
            },
            
            # Intake & Referral - Counselor Assignment
            "counselor_assignment": {
                "path": str(bots_dir / "Referral bot and bridge (final)" / "counselor_assignment_bot.py"),
                "name": "Counselor Assignment Bot",
                "keywords": ["counselor", "assign counselor", "assign"]
            },
            
            # Intake & Referral - Remove Counselor
            "remove_counselor": {
                "path": str(bots_dir / "Cursor versions" / "Goose" / "isws_remove_counselor_botcursor3.py"),
                "name": "Remove Counselor Bot",
                "keywords": ["remove counselor", "remove"]
            },
            
            # Intake & Referral Department Launcher
            "intake_referral": {
                "path": str(bots_dir / "Launcher" / "intake_referral_launcher.py"),
                "name": "Intake & Referral Department",
                "keywords": ["intake referral", "intake and referral"]
            },
            
            # Penelope Workflow Tool
            "penelope_workflow": {
                "path": str(bots_dir / "Penelope Workflow Tool" / "penelope_workflow_tool.py"),
                "name": "Penelope Workflow Tool",
                "keywords": ["penelope", "workflow"]
            }
        }
    
    def interpret_command(self, user_command: str, user_name: Optional[str] = None) -> Dict:
        """
        Interpret a natural language command using AI agent and learning system.
        
        Args:
            user_command: User's natural language command
            user_name: Name of user (for personalized suggestions)
        
        Returns:
            Dictionary with interpretation results including smart suggestions
        """
        self.logger.info(f"Interpreting command: {user_command}")
        start_time = time.time()
        
        # Use learning system for intelligent suggestions
        if self.learning_system:
            learning_analysis = self.learning_system.analyze_command(user_command, user_name)
            bot_suggestions = learning_analysis.get("bot_suggestions", [])
            parameter_suggestions = learning_analysis.get("parameter_suggestions", {})
            file_suggestions = learning_analysis.get("file_suggestions", [])
            context_info = learning_analysis.get("context_info", {})
        else:
            bot_suggestions = []
            parameter_suggestions = {}
            file_suggestions = []
            context_info = {}
        
        # Use AI agent for interpretation
        if not self.ai_agent:
            return {
                "success": False,
                "bot": None,
                "message": "AI Agent not available. Please check dependencies.",
                "confidence": 0.0
            }
        
        try:
            interpretation = self.ai_agent.interpret(user_command)
            
            # Override with learning system suggestions if available and confident
            if bot_suggestions and bot_suggestions[0]["confidence"] > interpretation.get("confidence", 0.0):
                top_suggestion = bot_suggestions[0]
                interpretation["bot"] = top_suggestion["bot_name"]
                interpretation["confidence"] = top_suggestion["confidence"]
                if top_suggestion.get("parameters"):
                    interpretation["params"] = top_suggestion["parameters"]
            
            # Map bot identifier to actual bot path
            bot_id = interpretation.get("bot")
            if bot_id and bot_id in self.BOT_MAP:
                bot_info = self.BOT_MAP[bot_id]
                interpretation["bot_path"] = bot_info["path"]
                interpretation["bot_name"] = bot_info["name"]
                interpretation["success"] = True
            elif bot_id:
                # Try fuzzy matching
                matched_bot = self._fuzzy_match_bot(bot_id)
                if matched_bot:
                    interpretation["bot_path"] = matched_bot["path"]
                    interpretation["bot_name"] = matched_bot["name"]
                    interpretation["success"] = True
                else:
                    interpretation["success"] = False
                    interpretation["message"] = f"Could not find bot for identifier: {bot_id}"
            else:
                interpretation["success"] = False
                interpretation["message"] = "Could not identify which bot to use for this task."
            
            # Add intelligent suggestions
            if self.learning_system and interpretation.get("success"):
                bot_name = interpretation.get("bot_name")
                
                # Get smart parameters
                smart_params = self.learning_system.get_smart_parameters(
                    bot_name, user_command, user_name
                )
                if smart_params:
                    # Merge with existing params
                    if "params" not in interpretation:
                        interpretation["params"] = {}
                    interpretation["params"].update(smart_params)
                    interpretation["smart_parameters"] = smart_params
                
                # Get file recommendations
                recommended_files = self.learning_system.get_file_recommendations(
                    bot_name, user_command, user_name
                )
                if recommended_files:
                    interpretation["recommended_files"] = recommended_files
            
            # Add context information
            if context_info:
                interpretation["context"] = context_info
            
            interpretation_time = time.time() - start_time
            interpretation["interpretation_time"] = interpretation_time
            
            self.logger.info(f"Interpretation result: {interpretation}")
            return interpretation
            
        except Exception as e:
            self.logger.error(f"Error interpreting command: {e}")
            return {
                "success": False,
                "bot": None,
                "message": f"Error during interpretation: {str(e)}",
                "confidence": 0.0
            }
    
    def _fuzzy_match_bot(self, bot_id: str) -> Optional[Dict]:
        """Try to find a bot by fuzzy matching the identifier"""
        bot_id_lower = bot_id.lower()
        
        for key, bot_info in self.BOT_MAP.items():
            if bot_id_lower in key or key in bot_id_lower:
                return bot_info
            if bot_id_lower in bot_info["name"].lower():
                return bot_info
            for keyword in bot_info.get("keywords", []):
                if bot_id_lower in keyword or keyword in bot_id_lower:
                    return bot_info
        
        return None
    
    def execute_task(self, interpretation: Dict, user_name: Optional[str] = None) -> Dict:
        """
        Execute a task based on the AI interpretation with workflow recording.
        
        Args:
            interpretation: Dictionary from interpret_command()
            user_name: Name of user executing
        
        Returns:
            Dictionary with execution results
        """
        if not interpretation.get("success"):
            return {
                "success": False,
                "message": interpretation.get("message", "Interpretation failed"),
                "bot_name": None
            }
        
        bot_path = interpretation.get("bot_path")
        bot_name = interpretation.get("bot_name", "Unknown Bot")
        command = interpretation.get("command") or interpretation.get("reasoning", "")
        parameters = interpretation.get("params") or interpretation.get("smart_parameters", {})
        files = interpretation.get("recommended_files") or []
        
        if not bot_path:
            return {
                "success": False,
                "message": "No bot path specified",
                "bot_name": bot_name
            }
        
        if not os.path.exists(bot_path):
            return {
                "success": False,
                "message": f"Bot file not found: {bot_path}",
                "bot_name": bot_name
            }
        
        execution_start = time.time()
        success = False
        error = None
        
        try:
            self.logger.info(f"Executing bot: {bot_name} at {bot_path}")
            
            # Prepare bot execution with parameters
            # Note: This is a simplified version - actual implementation would
            # need to pass parameters to bots via config files or environment variables
            
            # Launch the bot (hide console window for professional look)
            if os.name == 'nt':  # Windows
                # Use pythonw.exe if available, otherwise hide console window
                pythonw_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if Path(pythonw_exe).exists():
                    python_executable = pythonw_exe
                    creation_flags = 0
                else:
                    python_executable = sys.executable
                    # Hide console window (CREATE_NO_WINDOW = 0x08000000)
                    creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            else:
                python_executable = sys.executable
                creation_flags = 0
            
            process = subprocess.Popen(
                [python_executable, bot_path],
                cwd=os.path.dirname(bot_path),
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            execution_time = time.time() - execution_start
            success = True
            
            self.logger.info(f"Bot launched successfully (PID: {process.pid})")
            
            # Record workflow execution
            if self.workflow_recorder:
                try:
                    self.workflow_recorder.record_execution(
                        bot_name=bot_name,
                        bot_path=bot_path,
                        command=command,
                        parameters=parameters,
                        files=files,
                        success=success,
                        execution_time=execution_time,
                        error=error,
                        user_name=user_name,
                        context=interpretation.get("context", {})
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to record workflow: {e}")
            
            return {
                "success": True,
                "message": f"Successfully launched {bot_name}",
                "bot_name": bot_name,
                "pid": process.pid,
                "parameters": parameters,
                "files": files,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - execution_start
            error = str(e)
            success = False
            self.logger.error(f"Error executing bot: {e}")
            
            # Record failed execution
            if self.workflow_recorder:
                try:
                    self.workflow_recorder.record_execution(
                        bot_name=bot_name,
                        bot_path=bot_path,
                        command=command,
                        parameters=parameters,
                        files=files,
                        success=success,
                        execution_time=execution_time,
                        error=error,
                        user_name=user_name,
                        context=interpretation.get("context", {})
                    )
                except:
                    pass
            
            return {
                "success": False,
                "message": f"Failed to launch bot: {str(e)}",
                "bot_name": bot_name,
                "error": error
            }
    
    def process_command(self, user_command: str, user_name: Optional[str] = None) -> Dict:
        """
        Complete workflow: interpret command and execute task with learning.
        
        Args:
            user_command: User's natural language command
            user_name: Name of user (for personalized suggestions)
        
        Returns:
            Dictionary with complete results
        """
        # Get current user if not provided
        if not user_name:
            user_name = os.getenv("USERNAME") or os.getenv("USER") or "Unknown"
        
        # Log user command
        self.logger.info(f"Processing user command: {user_command} (User: {user_name})")
        
        # Interpret the command (with learning)
        interpretation = self.interpret_command(user_command, user_name)
        
        # Add user command to interpretation
        interpretation["command"] = user_command
        interpretation["user_name"] = user_name
        
        # Execute if interpretation was successful
        if interpretation.get("success"):
            execution_result = self.execute_task(interpretation, user_name)
            return {
                **interpretation,
                **execution_result
            }
        else:
            return interpretation
    
    def get_available_bots(self) -> List[Dict]:
        """
        Get list of all available bots with their information.
        
        Returns:
            List of dictionaries with bot information
        """
        bots = []
        for bot_id, bot_info in self.BOT_MAP.items():
            bots.append({
                "id": bot_id,
                "name": bot_info["name"],
                "path": bot_info["path"],
                "exists": os.path.exists(bot_info["path"]),
                "keywords": bot_info.get("keywords", [])
            })
        return bots


def main():
    """Standalone testing function"""
    assistant = AITaskAssistant()
    
    # Test commands
    test_commands = [
        "Submit this week's insurance claims",
        "Generate therapy progress reports",
        "Process consent forms",
        "Create welcome letters"
    ]
    
    print("=== AI Task Assistant Test ===")
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        result = assistant.process_command(cmd)
        print(f"Result: {result}")


if __name__ == "__main__":
    main()

