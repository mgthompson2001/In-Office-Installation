#!/usr/bin/env python3
"""
Goal Identifier - Understands WHAT the end goal is
Part of the Context Understanding Engine
"""

import json
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
import logging


class GoalIdentifier:
    """
    Goal Identifier - Understands the end goal of workflows
    
    Identifies:
    - Task goals: What task is being completed
    - Outcome goals: What outcome is desired
    - Process goals: What process is being executed
    - Business goals: What business objective is being met
    """
    
    def __init__(self):
        """Initialize Goal Identifier"""
        self.logger = logging.getLogger(__name__)
        
        # Goal patterns
        self.goal_patterns = {
            "complete_task": {
                "keywords": ["complete", "finish", "done", "accomplish", "achieve"],
                "intent_sequence": ["login", "navigate", "search", "view", "edit", "submit"],
                "description": "Complete a task or workflow"
            },
            "find_information": {
                "keywords": ["find", "locate", "discover", "identify", "retrieve"],
                "intent_sequence": ["search", "view"],
                "description": "Find or locate information"
            },
            "update_record": {
                "keywords": ["update", "modify", "change", "edit", "correct"],
                "intent_sequence": ["view", "edit", "submit"],
                "description": "Update or modify a record"
            },
            "create_record": {
                "keywords": ["create", "add", "new", "generate", "make"],
                "intent_sequence": ["navigate", "edit", "submit"],
                "description": "Create a new record"
            },
            "process_batch": {
                "keywords": ["process", "batch", "bulk", "multiple", "all"],
                "intent_sequence": ["upload", "process", "submit"],
                "description": "Process multiple items in batch"
            },
            "generate_report": {
                "keywords": ["report", "generate", "export", "download"],
                "intent_sequence": ["navigate", "view", "download"],
                "description": "Generate or export a report"
            },
            "remove_item": {
                "keywords": ["remove", "delete", "eliminate", "clear"],
                "intent_sequence": ["view", "delete", "confirm"],
                "description": "Remove or delete an item"
            },
            "upload_data": {
                "keywords": ["upload", "import", "add", "attach"],
                "intent_sequence": ["navigate", "upload", "submit"],
                "description": "Upload or import data"
            }
        }
        
        # Business goal patterns
        self.business_goal_patterns = {
            "billing": {
                "keywords": ["billing", "invoice", "payment", "charge"],
                "description": "Billing-related task"
            },
            "medical_records": {
                "keywords": ["medical records", "patient record", "chart"],
                "description": "Medical records management"
            },
            "consent": {
                "keywords": ["consent", "form", "agreement"],
                "description": "Consent form processing"
            },
            "intake": {
                "keywords": ["intake", "admission", "enrollment"],
                "description": "Intake or admission process"
            },
            "referral": {
                "keywords": ["referral", "refer", "transfer"],
                "description": "Referral processing"
            }
        }
    
    def identify_goal(self, actions: List[Dict], contexts: Optional[List[Dict]] = None) -> Dict:
        """
        Identify goal from actions and contexts
        
        Args:
            actions: List of actions in sequence
            contexts: Optional list of contexts
            
        Returns:
            Dictionary with:
                - goal_category: Primary goal category
                - goal_description: Human-readable description
                - goal_confidence: Confidence (0.0-1.0)
                - goal_metadata: Additional goal information
        """
        if not actions:
            return {
                "goal_category": "unknown",
                "goal_description": "No actions to analyze",
                "goal_confidence": 0.0,
                "goal_metadata": {}
            }
        
        # Extract intent sequence
        intent_sequence = [action.get("intent_category", "") for action in actions]
        
        # Extract text from actions
        text = " ".join([
            action.get("window_title", "") or action.get("url", "") or action.get("key", "")
            for action in actions
        ]).lower()
        
        # Match against goal patterns
        goal_scores = {}
        
        for goal_category, pattern in self.goal_patterns.items():
            score = 0.0
            
            # Check keyword matches
            keyword_matches = sum(1 for keyword in pattern["keywords"] if keyword in text)
            if keyword_matches > 0:
                score += keyword_matches / len(pattern["keywords"])
            
            # Check intent sequence matches
            intent_matches = self._match_intent_sequence(intent_sequence, pattern["intent_sequence"])
            if intent_matches > 0:
                score += intent_matches / len(pattern["intent_sequence"])
            
            if score > 0:
                goal_scores[goal_category] = score / 2.0  # Average of keyword and intent scores
        
        # Get best match
        if goal_scores:
            best_goal = max(goal_scores.items(), key=lambda x: x[1])
            goal_category = best_goal[0]
            confidence = min(best_goal[1] * 1.5, 1.0)  # Scale confidence
            
            # Get business goal
            business_goal = self._identify_business_goal(text, contexts)
            
            # Generate description
            description = self._generate_goal_description(goal_category, business_goal)
            
            return {
                "goal_category": goal_category,
                "goal_description": description,
                "goal_confidence": confidence,
                "business_goal": business_goal,
                "goal_metadata": {
                    "intent_sequence": intent_sequence,
                    "matched_pattern": self.goal_patterns[goal_category],
                    "text_analysis": text[:200]  # First 200 chars
                }
            }
        
        # Default: unknown goal
        return {
            "goal_category": "unknown",
            "goal_description": "Goal unclear from actions",
            "goal_confidence": 0.0,
            "goal_metadata": {
                "intent_sequence": intent_sequence,
                "text_analysis": text[:200]
            }
        }
    
    def _match_intent_sequence(self, actual_sequence: List[str], expected_sequence: List[str]) -> float:
        """Match actual intent sequence against expected pattern"""
        if not actual_sequence or not expected_sequence:
            return 0.0
        
        # Check if expected sequence appears in actual sequence
        matches = 0
        expected_index = 0
        
        for actual_intent in actual_sequence:
            if expected_index < len(expected_sequence):
                if actual_intent == expected_sequence[expected_index]:
                    matches += 1
                    expected_index += 1
                elif actual_intent in expected_sequence:
                    # Intent appears but out of order - partial match
                    matches += 0.5
        
        return matches / len(expected_sequence) if expected_sequence else 0.0
    
    def _identify_business_goal(self, text: str, contexts: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Identify business goal from text and contexts"""
        text_lower = text.lower()
        
        # Match against business goal patterns
        for business_goal, pattern in self.business_goal_patterns.items():
            if any(keyword in text_lower for keyword in pattern["keywords"]):
                return {
                    "business_goal": business_goal,
                    "description": pattern["description"],
                    "confidence": 0.8
                }
        
        # Check contexts for business goal
        if contexts:
            for context in contexts:
                task = context.get("task", {}).get("task", "")
                if task != "unknown":
                    return {
                        "business_goal": task,
                        "description": f"{task.replace('_', ' ')} task",
                        "confidence": 0.7
                    }
        
        return None
    
    def _generate_goal_description(self, goal_category: str, business_goal: Optional[Dict]) -> str:
        """Generate human-readable goal description"""
        base_description = self.goal_patterns[goal_category]["description"]
        
        if business_goal:
            business_desc = business_goal["description"]
            return f"{base_description} - {business_desc}"
        
        return base_description
    
    def identify_workflow_goals(self, workflows: List[Dict]) -> List[Dict]:
        """
        Identify goals for multiple workflows
        
        Args:
            workflows: List of workflow dictionaries with actions
            
        Returns:
            List of goal identifications
        """
        goals = []
        
        for workflow in workflows:
            workflow_id = workflow.get("workflow_id", "")
            actions = workflow.get("actions", [])
            contexts = workflow.get("contexts", [])
            
            goal = self.identify_goal(actions, contexts)
            goal["workflow_id"] = workflow_id
            
            goals.append(goal)
        
        return goals
    
    def analyze_goal_achievement(self, actions: List[Dict], goal: Dict) -> Dict:
        """
        Analyze whether goal was achieved
        
        Args:
            actions: List of actions
            goal: Goal dictionary
            
        Returns:
            Dictionary with:
                - achieved: Whether goal was achieved
                - achievement_confidence: Confidence in achievement
                - achievement_metadata: Additional information
        """
        goal_category = goal.get("goal_category", "")
        
        # Check for completion indicators
        completion_indicators = {
            "complete_task": ["submit", "save", "confirm", "complete"],
            "find_information": ["view", "display", "show"],
            "update_record": ["submit", "save", "update"],
            "create_record": ["submit", "save", "create"],
            "process_batch": ["submit", "complete", "finish"],
            "generate_report": ["download", "export", "save"],
            "remove_item": ["delete", "remove", "confirm"],
            "upload_data": ["submit", "upload", "complete"]
        }
        
        # Get intent sequence
        intent_sequence = [action.get("intent_category", "") for action in actions]
        
        # Check if completion indicators are present
        indicators = completion_indicators.get(goal_category, [])
        has_completion = any(indicator in intent_sequence for indicator in indicators)
        
        # Check if final action suggests completion
        if actions:
            final_action = actions[-1]
            final_intent = final_action.get("intent_category", "")
            has_final_completion = final_intent in indicators
        
        # Determine achievement
        achieved = has_completion or has_final_completion
        confidence = 0.8 if achieved else 0.3
        
        return {
            "achieved": achieved,
            "achievement_confidence": confidence,
            "achievement_metadata": {
                "completion_indicators": indicators,
                "has_completion": has_completion,
                "has_final_completion": has_final_completion,
                "final_intent": final_intent if actions else None
            }
        }

