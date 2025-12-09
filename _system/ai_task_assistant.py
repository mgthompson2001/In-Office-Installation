#!/usr/bin/env python3
"""
AI Task Assistant - Main Orchestrator
Interprets natural language commands and routes to appropriate bots.
Integrates with SecureDataCollector for continuous AI training.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import AI Agent
try:
    from ai_agent import AIAgent
    AI_AGENT_AVAILABLE = True
except ImportError:
    AI_AGENT_AVAILABLE = False
    AIAgent = None

# Import Secure Data Collector
try:
    from secure_data_collector import SecureDataCollector
    DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    DATA_COLLECTOR_AVAILABLE = False
    SecureDataCollector = None

# Import fuzzy matching for fallback
try:
    from difflib import get_close_matches
    FUZZY_MATCHING_AVAILABLE = True
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False


class AITaskAssistant:
    """
    Main orchestrator for AI Task Assistant.
    Interprets natural language and routes to appropriate bots.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None,
                 data_collector: Optional[SecureDataCollector] = None):
        """
        Initialize AI Task Assistant.
        
        Args:
            installation_dir: Base installation directory
            data_collector: SecureDataCollector instance for recording data
        """
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.data_collector = data_collector
        
        # Initialize AI Agent
        if AI_AGENT_AVAILABLE:
            self.ai_agent = AIAgent(self.installation_dir)
        else:
            self.ai_agent = None
        
        # Bot mapping (matches secure_launcher.py)
        self.bot_map = {
            "Medical Records Bot": {
                "path": str(self.installation_dir / "_bots" / "Med Rec" / "Finished Product, Launch Ready" / "Bot and extender" / "integrity_medical_records_bot_v3g_batchclicks.py"),
                "description": "Medical records management and processing"
            },
            "Consent Form Bot": {
                "path": str(self.installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "integrity_consent_bot_v2.py"),
                "description": "Consent forms with Penelope extraction (English/Spanish)"
            },
            "Welcome Letter Bot": {
                "path": str(self.installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "isws_welcome_DEEPFIX2_NOTEFORCE_v14.py"),
                "description": "Generate and send welcome letters"
            },
            "Intake & Referral Department": {
                "path": str(self.installation_dir / "_bots" / "Launcher" / "intake_referral_launcher.py"),
                "description": "Access all intake and referral related bots"
            },
            "Billing Department": {
                "path": str(self.installation_dir / "_bots" / "Billing Department" / "billing_department_launcher.py"),
                "description": "Access all billing department automation tools"
            },
            "Penelope Workflow Tool": {
                "path": str(self.installation_dir / "_bots" / "Penelope Workflow Tool" / "penelope_workflow_tool.py"),
                "description": "Multi-purpose Penelope workflow automation tool"
            }
        }
    
    def is_available(self) -> bool:
        """Check if AI Task Assistant is available"""
        return AI_AGENT_AVAILABLE and self.ai_agent is not None
    
    def is_configured(self) -> bool:
        """Check if AI Task Assistant is configured with API keys"""
        if not self.is_available():
            return False
        return self.ai_agent.is_configured()
    
    def interpret_and_select_bot(self, user_prompt: str) -> Dict:
        """
        Interpret user prompt and select appropriate bot.
        
        Args:
            user_prompt: User's natural language command
            
        Returns:
            Dictionary with:
                - bot_name: Selected bot name (or None)
                - bot_path: Path to bot script (or None)
                - confidence: Confidence score
                - reasoning: Explanation
                - error: Error message if any
        """
        result = {
            "bot_name": None,
            "bot_path": None,
            "confidence": 0.0,
            "reasoning": "",
            "error": None
        }
        
        # Try AI Agent first (if configured)
        if self.is_configured():
            try:
                ai_result = self.ai_agent.interpret_task(user_prompt, self.bot_map)
                result["bot_name"] = ai_result.get("bot_name")
                result["confidence"] = ai_result.get("confidence", 0.0)
                result["reasoning"] = ai_result.get("reasoning", "")
                result["error"] = ai_result.get("error")
                
                # Get bot path if bot selected
                if result["bot_name"] and result["bot_name"] in self.bot_map:
                    result["bot_path"] = self.bot_map[result["bot_name"]]["path"]
                
                # Record AI prompt for training
                if self.data_collector and self.data_collector.collection_active:
                    try:
                        self.data_collector.record_ai_prompt(
                            prompt_text=user_prompt,
                            response_data={
                                "bot_name": result["bot_name"],
                                "confidence": result["confidence"],
                                "reasoning": result["reasoning"]
                            },
                            bot_selected=result["bot_name"],
                            confidence_score=result["confidence"],
                            user_identifier=os.getenv("USERNAME", "Unknown")
                        )
                    except Exception as e:
                        # Silent fail - don't break the flow
                        pass
                
                return result
            except Exception as e:
                result["error"] = f"AI interpretation failed: {str(e)}"
                result["reasoning"] = f"Error calling AI service: {str(e)}"
        
        # Fallback to fuzzy matching if AI not available or failed
        if not result["bot_name"]:
            return self._fuzzy_match_bot(user_prompt)
        
        return result
    
    def _fuzzy_match_bot(self, user_prompt: str) -> Dict:
        """Fallback fuzzy matching when AI is not available"""
        result = {
            "bot_name": None,
            "bot_path": None,
            "confidence": 0.0,
            "reasoning": "AI not configured - using fuzzy matching",
            "error": "AI_NOT_CONFIGURED"
        }
        
        if not FUZZY_MATCHING_AVAILABLE:
            result["reasoning"] = "AI not configured and fuzzy matching not available"
            return result
        
        # Extract keywords from prompt
        prompt_lower = user_prompt.lower()
        
        # Simple keyword matching
        keywords_map = {
            "Medical Records Bot": ["medical", "records", "med rec"],
            "Consent Form Bot": ["consent", "form"],
            "Welcome Letter Bot": ["welcome", "letter"],
            "Intake & Referral Department": ["intake", "referral"],
            "Billing Department": ["billing", "bill", "invoice"],
            "Penelope Workflow Tool": ["penelope", "workflow"]
        }
        
        best_match = None
        best_score = 0.0
        
        for bot_name, keywords in keywords_map.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            if score > best_score:
                best_score = score
                best_match = bot_name
        
        if best_match and best_score > 0:
            result["bot_name"] = best_match
            result["bot_path"] = self.bot_map[best_match]["path"]
            result["confidence"] = min(best_score / len(keywords_map[best_match]), 1.0)
            result["reasoning"] = f"Matched keywords: {', '.join([k for k in keywords_map[best_match] if k in prompt_lower])}"
        
        # Record fuzzy match for training
        if self.data_collector and self.data_collector.collection_active:
            try:
                self.data_collector.record_ai_prompt(
                    prompt_text=user_prompt,
                    response_data={
                        "bot_name": result["bot_name"],
                        "confidence": result["confidence"],
                        "reasoning": result["reasoning"],
                        "method": "fuzzy_matching"
                    },
                    bot_selected=result["bot_name"],
                    confidence_score=result["confidence"],
                    user_identifier=os.getenv("USERNAME", "Unknown")
                )
            except Exception:
                pass
        
        return result
    
    def get_bot_list(self) -> Dict[str, Dict]:
        """Get list of available bots"""
        return self.bot_map.copy()

