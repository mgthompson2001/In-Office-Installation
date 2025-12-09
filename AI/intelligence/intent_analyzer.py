#!/usr/bin/env python3
"""
Intent Analyzer - Understands WHY employees do tasks
Part of the Context Understanding Engine
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import logging


class IntentAnalyzer:
    """
    Intent Analyzer - Understands the intent behind employee actions
    
    Classifies actions by intent:
    - login: User wants to authenticate
    - search: User wants to find information
    - navigate: User wants to move to a different location
    - submit: User wants to complete an action
    - view: User wants to see information
    - edit: User wants to modify information
    - delete: User wants to remove information
    - upload: User wants to add files/data
    - download: User wants to retrieve files/data
    - process: User wants to execute a task
    """
    
    def __init__(self):
        """Initialize Intent Analyzer"""
        self.logger = logging.getLogger(__name__)
        
        # Intent patterns (expanded from context_understanding_engine)
        self.intent_patterns = {
            "login": [
                "login", "sign in", "authenticate", "enter credentials",
                "username", "password", "credentials", "log in"
            ],
            "search": [
                "search", "find", "lookup", "query", "filter",
                "patient search", "client search", "name search",
                "look for", "locate", "discover"
            ],
            "navigate": [
                "navigate", "go to", "open", "click", "select",
                "menu", "tab", "page", "section", "move to",
                "switch to", "access"
            ],
            "submit": [
                "submit", "save", "confirm", "apply", "execute",
                "process", "complete", "finish", "send", "post"
            ],
            "view": [
                "view", "display", "show", "open", "read",
                "details", "information", "report", "see",
                "examine", "review"
            ],
            "edit": [
                "edit", "modify", "change", "update", "alter",
                "adjust", "correct", "fix", "revise"
            ],
            "delete": [
                "delete", "remove", "clear", "erase", "eliminate",
                "drop", "cancel", "undo"
            ],
            "upload": [
                "upload", "import", "add", "attach", "load",
                "insert", "include", "attach file"
            ],
            "download": [
                "download", "export", "save", "get", "retrieve",
                "extract", "obtain", "fetch"
            ],
            "process": [
                "process", "run", "execute", "perform", "handle",
                "automate", "batch", "bulk", "generate"
            ]
        }
        
        # Intent relationships (some intents often follow others)
        self.intent_relationships = {
            "login": ["navigate", "search", "view"],
            "search": ["view", "edit", "process"],
            "navigate": ["search", "view", "edit"],
            "view": ["edit", "delete", "download"],
            "edit": ["submit", "save"],
            "upload": ["process", "submit"]
        }
    
    def analyze_intent(self, action: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Analyze intent from action and context
        
        Args:
            action: Action dictionary with type, data, etc.
            context: Optional context dictionary
            
        Returns:
            Dictionary with:
                - intent_category: Primary intent category
                - intent_description: Human-readable description
                - confidence_score: Confidence (0.0-1.0)
                - alternative_intents: List of other possible intents
        """
        # Extract text from action
        text = self._extract_text(action)
        
        # Classify intent
        intent_category, intent_description, confidence = self._classify_intent(text, action)
        
        # Get alternative intents
        alternative_intents = self._get_alternative_intents(text, action, intent_category)
        
        # Enhance with context if available
        if context:
            intent_category, confidence = self._enhance_with_context(
                intent_category, confidence, context
            )
        
        return {
            "intent_category": intent_category,
            "intent_description": intent_description,
            "confidence_score": confidence,
            "alternative_intents": alternative_intents,
            "action_id": action.get("id", ""),
            "action_type": action.get("type", "")
        }
    
    def _extract_text(self, action: Dict) -> str:
        """Extract text from action for intent analysis"""
        text_parts = []
        
        action_type = action.get("type", "")
        
        if action_type == "keyboard":
            key = action.get("key", "")
            if key:
                text_parts.append(key)
        
        elif action_type == "browser":
            url = action.get("url", "")
            element_text = action.get("element_text", "")
            element_type = action.get("element_type", "")
            
            if url:
                text_parts.append(url)
            if element_text:
                text_parts.append(element_text)
            if element_type:
                text_parts.append(element_type)
        
        elif action_type == "screen":
            window_title = action.get("window_title", "")
            active_app = action.get("active_app", "")
            
            if window_title:
                text_parts.append(window_title)
            if active_app:
                text_parts.append(active_app)
        
        elif action_type == "mouse":
            window_title = action.get("window_title", "")
            active_app = action.get("active_app", "")
            
            if window_title:
                text_parts.append(window_title)
            if active_app:
                text_parts.append(active_app)
        
        return " ".join(text_parts).lower()
    
    def _classify_intent(self, text: str, action: Dict) -> Tuple[str, str, float]:
        """Classify intent from text and action"""
        if not text:
            return "unknown", "Intent unclear - no text found", 0.0
        
        # Match against intent patterns
        intent_scores = {}
        
        for intent_category, patterns in self.intent_patterns.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                if pattern in text:
                    score += 1
                    matches += 1
            
            if matches > 0:
                # Normalize score by pattern count
                intent_scores[intent_category] = score / len(patterns)
        
        if not intent_scores:
            return "unknown", "Intent unclear - no patterns matched", 0.0
        
        # Get best match
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent_category = best_intent[0]
        confidence = min(best_intent[1] * 2, 1.0)  # Scale confidence
        
        # Generate description
        intent_description = self._generate_intent_description(intent_category, text)
        
        return intent_category, intent_description, confidence
    
    def _generate_intent_description(self, intent_category: str, text: str) -> str:
        """Generate human-readable intent description"""
        descriptions = {
            "login": "User intends to authenticate and gain access",
            "search": "User intends to find or locate information",
            "navigate": "User intends to move to a different location or section",
            "submit": "User intends to complete or finalize an action",
            "view": "User intends to see or examine information",
            "edit": "User intends to modify or change information",
            "delete": "User intends to remove or eliminate information",
            "upload": "User intends to add or import files or data",
            "download": "User intends to retrieve or export files or data",
            "process": "User intends to execute or perform a task",
            "unknown": "User intent is unclear"
        }
        
        base_description = descriptions.get(intent_category, "User intent unclear")
        
        # Add context from text if available
        if text and len(text) < 100:
            return f"{base_description} (context: {text[:50]}...)"
        
        return base_description
    
    def _get_alternative_intents(self, text: str, action: Dict, primary_intent: str) -> List[Dict]:
        """Get alternative possible intents"""
        alternatives = []
        
        # Re-classify with lower threshold
        intent_scores = {}
        
        for intent_category, patterns in self.intent_patterns.items():
            if intent_category == primary_intent:
                continue  # Skip primary intent
            
            score = sum(1 for pattern in patterns if pattern in text)
            if score > 0:
                intent_scores[intent_category] = score / len(patterns)
        
        # Get top 3 alternatives
        sorted_alternatives = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for intent_category, confidence in sorted_alternatives:
            alternatives.append({
                "intent_category": intent_category,
                "confidence_score": min(confidence * 2, 1.0),
                "description": self._generate_intent_description(intent_category, text)
            })
        
        return alternatives
    
    def _enhance_with_context(self, intent_category: str, confidence: float, context: Dict) -> Tuple[str, float]:
        """Enhance intent classification with context"""
        # Check if context suggests different intent
        context_app = context.get("application", "").lower()
        context_page = context.get("page", "").lower()
        
        # Login pages suggest login intent
        if "login" in context_page or "sign in" in context_page:
            if intent_category != "login":
                return "login", min(confidence + 0.2, 1.0)
        
        # Search pages suggest search intent
        if "search" in context_page:
            if intent_category != "search":
                return "search", min(confidence + 0.2, 1.0)
        
        # Check intent relationships
        if intent_category in self.intent_relationships:
            related_intents = self.intent_relationships[intent_category]
            # If context suggests related intent, boost confidence
            for related in related_intents:
                if related in context_page or related in context_app:
                    confidence = min(confidence + 0.1, 1.0)
        
        return intent_category, confidence
    
    def analyze_intent_sequence(self, actions: List[Dict]) -> Dict:
        """
        Analyze intent sequence to understand workflow intent
        
        Args:
            actions: List of actions in sequence
            
        Returns:
            Dictionary with:
                - primary_intent: Main intent of the sequence
                - intent_sequence: List of intents in order
                - intent_transitions: How intents change over time
                - workflow_intent: Overall workflow intent
        """
        intent_sequence = []
        
        for action in actions:
            intent_analysis = self.analyze_intent(action)
            intent_sequence.append(intent_analysis)
        
        # Determine primary intent (most common)
        intent_counts = Counter([intent["intent_category"] for intent in intent_sequence])
        primary_intent = intent_counts.most_common(1)[0][0] if intent_counts else "unknown"
        
        # Analyze intent transitions
        intent_transitions = []
        for i in range(len(intent_sequence) - 1):
            current = intent_sequence[i]["intent_category"]
            next_intent = intent_sequence[i + 1]["intent_category"]
            
            if current != next_intent:
                intent_transitions.append({
                    "from": current,
                    "to": next_intent,
                    "transition_type": self._classify_transition(current, next_intent)
                })
        
        # Determine workflow intent
        workflow_intent = self._determine_workflow_intent(intent_sequence)
        
        return {
            "primary_intent": primary_intent,
            "intent_sequence": intent_sequence,
            "intent_transitions": intent_transitions,
            "workflow_intent": workflow_intent,
            "total_actions": len(actions)
        }
    
    def _classify_transition(self, from_intent: str, to_intent: str) -> str:
        """Classify type of intent transition"""
        # Common transitions
        if from_intent == "login" and to_intent in ["navigate", "search", "view"]:
            return "authentication_to_action"
        elif from_intent == "search" and to_intent == "view":
            return "search_to_review"
        elif from_intent == "view" and to_intent == "edit":
            return "review_to_modify"
        elif from_intent == "edit" and to_intent == "submit":
            return "modify_to_complete"
        else:
            return "general_transition"
    
    def _determine_workflow_intent(self, intent_sequence: List[Dict]) -> str:
        """Determine overall workflow intent from sequence"""
        # Look for common workflow patterns
        intents = [intent["intent_category"] for intent in intent_sequence]
        
        # Login → Search → View → Edit → Submit = Complete Task
        if "login" in intents and "search" in intents and "edit" in intents and "submit" in intents:
            return "complete_task"
        
        # Search → View = Find Information
        elif "search" in intents and "view" in intents and "edit" not in intents:
            return "find_information"
        
        # View → Edit → Submit = Update Record
        elif "view" in intents and "edit" in intents and "submit" in intents:
            return "update_record"
        
        # Upload → Process = Process Data
        elif "upload" in intents and "process" in intents:
            return "process_data"
        
        else:
            return "general_workflow"

