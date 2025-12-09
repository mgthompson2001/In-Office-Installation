#!/usr/bin/env python3
"""
Context Extractor - Understands WHAT context actions occur in
Part of the Context Understanding Engine
"""

import json
import re
from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging


class ContextExtractor:
    """
    Context Extractor - Understands the context of actions
    
    Extracts:
    - Application context: What application is being used
    - Page context: What page/screen is active
    - State context: What state the user is in
    - Task context: What task is being performed
    - Temporal context: When actions occur
    """
    
    def __init__(self):
        """Initialize Context Extractor"""
        self.logger = logging.getLogger(__name__)
        
        # Application patterns
        self.application_patterns = {
            "therapy_notes": ["therapy notes", "therapynotes", "tn"],
            "penelope": ["penelope", "penelope cms"],
            "medisoft": ["medisoft", "medisoft billing"],
            "browser": ["chrome", "firefox", "edge", "browser", "http", "https"],
            "excel": ["excel", "spreadsheet", ".xlsx", ".xls"],
            "word": ["word", "document", ".docx", ".doc"],
            "pdf": ["pdf", "adobe", ".pdf"]
        }
        
        # Page patterns
        self.page_patterns = {
            "login": ["login", "sign in", "authenticate", "credentials"],
            "dashboard": ["dashboard", "home", "main", "overview"],
            "search": ["search", "find", "lookup", "query"],
            "results": ["results", "list", "table", "grid"],
            "details": ["details", "information", "profile", "record"],
            "form": ["form", "entry", "input", "edit"],
            "report": ["report", "export", "download", "generate"]
        }
        
        # State patterns
        self.state_patterns = {
            "typing": ["keyboard", "input", "text", "type"],
            "clicking": ["click", "button", "link", "mouse"],
            "viewing": ["view", "display", "show", "read"],
            "waiting": ["loading", "wait", "processing", "spinner"],
            "navigating": ["navigate", "go to", "open", "switch"]
        }
        
        # Task patterns
        self.task_patterns = {
            "billing": ["billing", "invoice", "payment", "charge"],
            "medical_records": ["medical records", "patient record", "chart"],
            "consent": ["consent", "form", "agreement"],
            "intake": ["intake", "admission", "enrollment"],
            "referral": ["referral", "refer", "transfer"]
        }
    
    def extract_context(self, action: Dict, previous_actions: Optional[List[Dict]] = None) -> Dict:
        """
        Extract context from action
        
        Args:
            action: Action dictionary
            previous_actions: Optional list of previous actions for temporal context
            
        Returns:
            Dictionary with:
                - application: Application context
                - page: Page context
                - state: State context
                - task: Task context
                - temporal: Temporal context
        """
        context = {
            "application": self._extract_application_context(action),
            "page": self._extract_page_context(action),
            "state": self._extract_state_context(action),
            "task": self._extract_task_context(action),
            "temporal": self._extract_temporal_context(action, previous_actions)
        }
        
        return context
    
    def _extract_application_context(self, action: Dict) -> Dict:
        """Extract application context"""
        app = ""
        app_type = "unknown"
        
        # Get application from action
        if action.get("type") == "browser":
            url = action.get("url", "")
            if url:
                app = url
                app_type = "browser"
        elif action.get("type") in ["screen", "keyboard", "mouse"]:
            active_app = action.get("active_app", "")
            if active_app:
                app = active_app
                # Classify application type
                app_lower = active_app.lower()
                for app_name, patterns in self.application_patterns.items():
                    if any(pattern in app_lower for pattern in patterns):
                        app_type = app_name
                        break
        
        return {
            "application": app,
            "application_type": app_type,
            "confidence": 0.8 if app else 0.0
        }
    
    def _extract_page_context(self, action: Dict) -> Dict:
        """Extract page context"""
        page = ""
        page_type = "unknown"
        
        # Get page from action
        if action.get("type") == "browser":
            url = action.get("url", "")
            element_text = action.get("element_text", "")
            
            if url:
                page = url
            elif element_text:
                page = element_text
            
            # Classify page type
            page_lower = (url + " " + element_text).lower()
            for page_name, patterns in self.page_patterns.items():
                if any(pattern in page_lower for pattern in patterns):
                    page_type = page_name
                    break
        
        elif action.get("type") in ["screen", "keyboard", "mouse"]:
            window_title = action.get("window_title", "")
            if window_title:
                page = window_title
                
                # Classify page type
                page_lower = window_title.lower()
                for page_name, patterns in self.page_patterns.items():
                    if any(pattern in page_lower for pattern in patterns):
                        page_type = page_name
                        break
        
        return {
            "page": page,
            "page_type": page_type,
            "confidence": 0.8 if page else 0.0
        }
    
    def _extract_state_context(self, action: Dict) -> Dict:
        """Extract state context"""
        state = "unknown"
        state_type = "unknown"
        
        action_type = action.get("type", "")
        
        # Determine state from action type
        if action_type == "keyboard":
            state = "typing"
            state_type = "input"
        elif action_type == "mouse":
            event_type = action.get("event_type", "")
            if event_type == "click":
                state = "clicking"
                state_type = "interaction"
            elif event_type == "move":
                state = "hovering"
                state_type = "navigation"
        elif action_type == "browser":
            event_type = action.get("event_type", "")
            if event_type == "navigation":
                state = "navigating"
                state_type = "navigation"
            elif event_type == "click":
                state = "clicking"
                state_type = "interaction"
        elif action_type == "screen":
            state = "viewing"
            state_type = "observation"
        
        # Enhance with patterns
        text = self._extract_text(action)
        text_lower = text.lower()
        
        for state_name, patterns in self.state_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                state = state_name
                break
        
        return {
            "state": state,
            "state_type": state_type,
            "confidence": 0.7
        }
    
    def _extract_task_context(self, action: Dict) -> Dict:
        """Extract task context"""
        task = "unknown"
        task_type = "unknown"
        
        # Extract text from action
        text = self._extract_text(action)
        text_lower = text.lower()
        
        # Match against task patterns
        for task_name, patterns in self.task_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                task = task_name
                task_type = task_name.replace("_", " ")
                break
        
        return {
            "task": task,
            "task_type": task_type,
            "confidence": 0.7 if task != "unknown" else 0.0
        }
    
    def _extract_temporal_context(self, action: Dict, previous_actions: Optional[List[Dict]]) -> Dict:
        """Extract temporal context"""
        temporal = {
            "timestamp": action.get("timestamp", ""),
            "time_since_start": None,
            "time_since_last_action": None,
            "action_sequence_position": None
        }
        
        if previous_actions:
            temporal["action_sequence_position"] = len(previous_actions) + 1
            
            # Calculate time since last action
            if len(previous_actions) > 0:
                last_action = previous_actions[-1]
                last_timestamp = last_action.get("timestamp", "")
                current_timestamp = action.get("timestamp", "")
                
                try:
                    from datetime import datetime
                    last_dt = datetime.fromisoformat(last_timestamp)
                    current_dt = datetime.fromisoformat(current_timestamp)
                    time_diff = (current_dt - last_dt).total_seconds()
                    temporal["time_since_last_action"] = time_diff
                except:
                    pass
            
            # Calculate time since start
            if len(previous_actions) > 0:
                first_action = previous_actions[0]
                first_timestamp = first_action.get("timestamp", "")
                current_timestamp = action.get("timestamp", "")
                
                try:
                    from datetime import datetime
                    first_dt = datetime.fromisoformat(first_timestamp)
                    current_dt = datetime.fromisoformat(current_timestamp)
                    time_diff = (current_dt - first_dt).total_seconds()
                    temporal["time_since_start"] = time_diff
                except:
                    pass
        
        return temporal
    
    def _extract_text(self, action: Dict) -> str:
        """Extract text from action"""
        text_parts = []
        
        if action.get("type") == "browser":
            url = action.get("url", "")
            element_text = action.get("element_text", "")
            if url:
                text_parts.append(url)
            if element_text:
                text_parts.append(element_text)
        
        elif action.get("type") in ["screen", "keyboard", "mouse"]:
            window_title = action.get("window_title", "")
            active_app = action.get("active_app", "")
            if window_title:
                text_parts.append(window_title)
            if active_app:
                text_parts.append(active_app)
        
        return " ".join(text_parts)
    
    def extract_context_sequence(self, actions: List[Dict]) -> Dict:
        """
        Extract context sequence to understand workflow context
        
        Args:
            actions: List of actions in sequence
            
        Returns:
            Dictionary with:
                - context_sequence: List of contexts in order
                - context_transitions: How contexts change over time
                - workflow_context: Overall workflow context
        """
        context_sequence = []
        previous_actions = []
        
        for i, action in enumerate(actions):
            context = self.extract_context(action, previous_actions)
            context_sequence.append(context)
            previous_actions.append(action)
        
        # Analyze context transitions
        context_transitions = []
        for i in range(len(context_sequence) - 1):
            current = context_sequence[i]
            next_context = context_sequence[i + 1]
            
            # Check for context changes
            if current["application"]["application"] != next_context["application"]["application"]:
                context_transitions.append({
                    "type": "application_change",
                    "from": current["application"]["application"],
                    "to": next_context["application"]["application"]
                })
            
            if current["page"]["page"] != next_context["page"]["page"]:
                context_transitions.append({
                    "type": "page_change",
                    "from": current["page"]["page"],
                    "to": next_context["page"]["page"]
                })
            
            if current["state"]["state"] != next_context["state"]["state"]:
                context_transitions.append({
                    "type": "state_change",
                    "from": current["state"]["state"],
                    "to": next_context["state"]["state"]
                })
        
        # Determine workflow context
        workflow_context = self._determine_workflow_context(context_sequence)
        
        return {
            "context_sequence": context_sequence,
            "context_transitions": context_transitions,
            "workflow_context": workflow_context,
            "total_actions": len(actions)
        }
    
    def _determine_workflow_context(self, context_sequence: List[Dict]) -> Dict:
        """Determine overall workflow context from sequence"""
        # Get most common application
        applications = [ctx["application"]["application_type"] for ctx in context_sequence]
        from collections import Counter
        most_common_app = Counter(applications).most_common(1)[0][0] if applications else "unknown"
        
        # Get most common task
        tasks = [ctx["task"]["task"] for ctx in context_sequence if ctx["task"]["task"] != "unknown"]
        most_common_task = Counter(tasks).most_common(1)[0][0] if tasks else "unknown"
        
        # Get workflow type
        workflow_type = "unknown"
        if most_common_app == "browser":
            workflow_type = "web_automation"
        elif most_common_app in ["excel", "word", "pdf"]:
            workflow_type = "document_processing"
        elif most_common_app in ["therapy_notes", "penelope", "medisoft"]:
            workflow_type = "healthcare_automation"
        
        return {
            "primary_application": most_common_app,
            "primary_task": most_common_task,
            "workflow_type": workflow_type,
            "confidence": 0.7
        }

