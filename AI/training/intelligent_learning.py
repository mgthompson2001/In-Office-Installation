#!/usr/bin/env python3
"""
Intelligent Learning System - Enterprise-Grade AI Learning Engine
Uses recorded workflow history to provide intelligent suggestions,
parameter pre-filling, and context-aware automation.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
import re

from workflow_recorder import WorkflowRecorder


class IntelligentLearning:
    """
    Intelligent learning system that analyzes workflow patterns
    and provides smart automation suggestions.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize the intelligent learning system"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.recorder = WorkflowRecorder(installation_dir)
    
    def analyze_command(self, command: str, user_name: Optional[str] = None) -> Dict:
        """
        Analyze a natural language command and provide intelligent suggestions.
        
        Returns:
            Dictionary with:
            - bot_suggestions: List of likely bots with confidence
            - parameter_suggestions: Suggested parameters based on history
            - file_suggestions: Suggested files to use
            - context_info: Extracted context (dates, etc.)
        """
        # Extract context from command
        context = self._extract_context(command)
        
        # Get context-based suggestions
        context_suggestions = self.recorder.get_context_suggestions(command)
        
        # Analyze command patterns
        bot_suggestions = self._analyze_bot_suggestions(command, context_suggestions)
        
        # Get parameter suggestions for most likely bot
        parameter_suggestions = {}
        file_suggestions = []
        
        if bot_suggestions:
            top_bot = bot_suggestions[0]["bot_name"]
            parameter_suggestions = self._get_parameter_suggestions(
                top_bot, user_name, context
            )
            file_suggestions = self.recorder.get_file_suggestions(top_bot, user_name)
        
        return {
            "bot_suggestions": bot_suggestions,
            "parameter_suggestions": parameter_suggestions,
            "file_suggestions": file_suggestions,
            "context_info": context,
            "confidence": bot_suggestions[0]["confidence"] if bot_suggestions else 0.0
        }
    
    def _extract_context(self, command: str) -> Dict:
        """Extract contextual information from command"""
        context = {
            "dates": {},
            "file_types": [],
            "user_intent": None,
            "time_references": []
        }
        
        command_lower = command.lower()
        
        # Extract date patterns
        today = datetime.now()
        
        # Week patterns
        if "this week" in command_lower:
            context["dates"]["start"] = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
            context["dates"]["end"] = today.strftime("%Y-%m-%d")
            context["dates"]["range"] = "this_week"
        elif "last week" in command_lower:
            last_week_start = today - timedelta(days=today.weekday() + 7)
            last_week_end = last_week_start + timedelta(days=6)
            context["dates"]["start"] = last_week_start.strftime("%Y-%m-%d")
            context["dates"]["end"] = last_week_end.strftime("%Y-%m-%d")
            context["dates"]["range"] = "last_week"
        
        # Month patterns
        if "this month" in command_lower:
            context["dates"]["start"] = today.replace(day=1).strftime("%Y-%m-%d")
            context["dates"]["end"] = today.strftime("%Y-%m-%d")
            context["dates"]["range"] = "this_month"
        elif "last month" in command_lower:
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            context["dates"]["start"] = first_day_last_month.strftime("%Y-%m-%d")
            context["dates"]["end"] = last_day_last_month.strftime("%Y-%m-%d")
            context["dates"]["range"] = "last_month"
        
        # Specific date extraction (YYYY-MM-DD, MM/DD/YYYY, etc.)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, command)
            if matches:
                context["dates"]["specific_dates"] = matches
        
        # File type extraction
        if "excel" in command_lower or ".xlsx" in command_lower or ".xls" in command_lower:
            context["file_types"].append("excel")
        if "csv" in command_lower or ".csv" in command_lower:
            context["file_types"].append("csv")
        if "pdf" in command_lower or ".pdf" in command_lower:
            context["file_types"].append("pdf")
        
        # Intent detection
        if any(word in command_lower for word in ["submit", "send", "upload"]):
            context["user_intent"] = "submit"
        elif any(word in command_lower for word in ["process", "run", "execute"]):
            context["user_intent"] = "process"
        elif any(word in command_lower for word in ["generate", "create", "make"]):
            context["user_intent"] = "generate"
        elif any(word in command_lower for word in ["update", "modify", "change"]):
            context["user_intent"] = "update"
        
        return context
    
    def _analyze_bot_suggestions(self, command: str, context_suggestions: List[Dict]) -> List[Dict]:
        """Analyze command and rank bot suggestions"""
        suggestions = []
        
        # Use historical context suggestions
        for suggestion in context_suggestions:
            suggestions.append({
                "bot_name": suggestion["bot_name"],
                "confidence": suggestion["success_rate"] * (suggestion["frequency"] / 100.0),
                "parameters": suggestion.get("parameters"),
                "file_pattern": suggestion.get("file_pattern"),
                "frequency": suggestion["frequency"]
            })
        
        # Add keyword-based matching
        command_lower = command.lower()
        keyword_mappings = {
            "consent": ("consent_form", 0.9),
            "welcome": ("welcome_letter", 0.9),
            "medisoft": ("medisoft_billing", 0.95),
            "billing": ("medisoft_billing", 0.8),
            "insurance claim": ("medisoft_billing", 0.85),
            "refiling": ("tn_refiling", 0.9),
            "therapy notes": ("tn_refiling", 0.85),
            "referral": ("referral", 0.9),
            "counselor": ("counselor_assignment", 0.8),
            "remove counselor": ("remove_counselor", 0.9),
            "medical record": ("medical_records", 0.9),
            "penelope": ("penelope_workflow", 0.9)
        }
        
        for keyword, (bot_name, confidence) in keyword_mappings.items():
            if keyword in command_lower:
                # Check if already in suggestions
                existing = next((s for s in suggestions if s["bot_name"] == bot_name), None)
                if existing:
                    existing["confidence"] = max(existing["confidence"], confidence)
                else:
                    suggestions.append({
                        "bot_name": bot_name,
                        "confidence": confidence,
                        "parameters": None,
                        "file_pattern": None,
                        "frequency": 0
                    })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return suggestions[:5]  # Top 5 suggestions
    
    def _get_parameter_suggestions(self, bot_name: str, user_name: Optional[str],
                                  context: Dict) -> Dict:
        """Get intelligent parameter suggestions based on history and context"""
        if not user_name:
            user_name = os.getenv("USERNAME") or os.getenv("USER") or "Unknown"
        
        # Get user patterns
        user_patterns = self.recorder.get_user_patterns(user_name, bot_name)
        
        # Get workflow history
        history = self.recorder.get_workflow_history(bot_name, user_name, days=90)
        
        suggestions = {}
        
        # Analyze most common parameters
        for param_name, patterns in user_patterns.items():
            if patterns:
                # Get most frequent value
                most_common = max(patterns, key=lambda x: x["frequency"])
                suggestions[param_name] = {
                    "value": most_common["value"],
                    "confidence": most_common["frequency"] / 10.0,  # Normalize
                    "source": "user_history"
                }
        
        # Apply context to suggestions
        if context.get("dates"):
            if "date_from" not in suggestions:
                suggestions["date_from"] = {
                    "value": context["dates"].get("start"),
                    "confidence": 0.9,
                    "source": "context_extraction"
                }
            if "date_to" not in suggestions:
                suggestions["date_to"] = {
                    "value": context["dates"].get("end"),
                    "confidence": 0.9,
                    "source": "context_extraction"
                }
            if "date_range" not in suggestions:
                suggestions["date_range"] = {
                    "value": context["dates"].get("range"),
                    "confidence": 0.9,
                    "source": "context_extraction"
                }
        
        # Analyze recent history for temporal patterns
        if history:
            recent_params = []
            for record in history[:10]:  # Last 10 executions
                if record.get("parameters"):
                    recent_params.append(record["parameters"])
            
            # Find patterns in recent parameters
            for param_name in set().union(*(p.keys() for p in recent_params if p)):
                values = [p.get(param_name) for p in recent_params if p.get(param_name)]
                if values:
                    most_common_value = Counter(values).most_common(1)[0][0]
                    if param_name not in suggestions or suggestions[param_name]["confidence"] < 0.7:
                        suggestions[param_name] = {
                            "value": most_common_value,
                            "confidence": 0.7,
                            "source": "recent_history"
                        }
        
        return suggestions
    
    def get_smart_parameters(self, bot_name: str, command: str,
                           user_name: Optional[str] = None) -> Dict:
        """
        Get smart parameter values to pre-fill based on:
        - User history
        - Command context
        - Recent patterns
        - File associations
        """
        context = self._extract_context(command)
        suggestions = self._get_parameter_suggestions(bot_name, user_name, context)
        
        # Build final parameter dictionary
        parameters = {}
        for param_name, suggestion in suggestions.items():
            if suggestion["confidence"] >= 0.6:  # Only use high-confidence suggestions
                parameters[param_name] = suggestion["value"]
        
        return parameters
    
    def get_file_recommendations(self, bot_name: str, command: str,
                                user_name: Optional[str] = None) -> List[str]:
        """Get file recommendations based on history and context"""
        suggestions = self.recorder.get_file_suggestions(bot_name, user_name)
        
        # Filter by context
        context = self._extract_context(command)
        recommended_files = []
        
        for suggestion in suggestions:
            file_path = suggestion["file_path"]
            
            # Check if file exists
            if not os.path.exists(file_path):
                continue
            
            # Check file type match
            if context.get("file_types"):
                file_ext = Path(file_path).suffix.lower()
                if file_ext in [".xlsx", ".xls"] and "excel" not in context["file_types"]:
                    continue
                if file_ext == ".csv" and "csv" not in context["file_types"]:
                    continue
            
            recommended_files.append(file_path)
            
            # Limit to top 5
            if len(recommended_files) >= 5:
                break
        
        return recommended_files
    
    def learn_from_execution(self, bot_name: str, command: str,
                            parameters: Dict, files: List[str],
                            success: bool, user_name: Optional[str] = None):
        """Update learning models based on execution results"""
        # This is handled by WorkflowRecorder, but we can add additional learning here
        pass
    
    def get_workflow_template(self, template_name: str) -> Optional[Dict]:
        """Get a saved workflow template"""
        # This would retrieve saved workflow templates
        # Implementation depends on template storage system
        return None
    
    def predict_next_action(self, current_sequence: List[str]) -> Optional[str]:
        """Predict next action based on current workflow sequence"""
        # Analyze common sequences from history
        # Return most likely next action
        return None

