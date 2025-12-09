#!/usr/bin/env python3
"""
AI Agent - LLM Interface for Task Interpretation
This module provides an interface to language models for interpreting natural language commands
and routing them to appropriate bots.
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime


class AIAgent:
    """
    AI Agent class for interpreting natural language commands and routing to bots.
    Supports multiple LLM backends (OpenAI, Claude, or local models).
    """
    
    def __init__(self, model: str = "claude-sonnet", temperature: float = 0.3):
        """
        Initialize the AI Agent.
        
        Args:
            model: Model identifier (e.g., "claude-sonnet", "gpt-5-mini", "local")
            temperature: Temperature for LLM responses (0.0-1.0)
        """
        self.model = model
        self.temperature = temperature
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load API key from environment variables or config file"""
        # Try environment variables first
        if self.model.startswith("claude"):
            self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        elif self.model.startswith("gpt"):
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Try config file if environment variable not found
        if not self.api_key:
            config_path = os.path.join(os.path.dirname(__file__), "ai_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if self.model.startswith("claude"):
                            self.api_key = config.get("anthropic_api_key") or config.get("claude_api_key")
                        elif self.model.startswith("gpt"):
                            self.api_key = config.get("openai_api_key")
                except Exception:
                    pass
    
    def interpret(self, prompt: str) -> Dict:
        """
        Interpret a natural language command and return structured output.
        
        Args:
            prompt: User's natural language command (e.g., "Submit this week's insurance claims")
        
        Returns:
            Dictionary with keys:
                - bot: Bot identifier or filename
                - action: Specific action to perform
                - params: Dictionary of parameters for the bot
                - confidence: Confidence score (0.0-1.0)
                - reasoning: Explanation of the interpretation
        """
        try:
            # Use fuzzy matching first for quick responses
            parsed = self._fuzzy_match(prompt)
            if parsed and parsed.get("confidence", 0) > 0.7:
                return parsed
            
            # If fuzzy matching isn't confident enough, try LLM
            if self.api_key:
                return self._llm_interpret(prompt)
            else:
                # Fallback to fuzzy matching if no API key
                return parsed or {
                    "bot": None,
                    "action": None,
                    "params": {},
                    "confidence": 0.0,
                    "reasoning": "No API key configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
                }
        except Exception as e:
            return {
                "bot": None,
                "action": None,
                "params": {},
                "confidence": 0.0,
                "reasoning": f"Error during interpretation: {str(e)}"
            }
    
    def _fuzzy_match(self, prompt: str) -> Optional[Dict]:
        """
        Fast fuzzy matching using keyword matching.
        This provides quick responses without API calls.
        """
        prompt_lower = prompt.lower()
        
        # Keyword mappings to bot identifiers
        keyword_map = {
            # Medical Records
            "medical record": "medical_records",
            "med rec": "medical_records",
            "medical records": "medical_records",
            
            # Consent Forms
            "consent": "consent_form",
            "consent form": "consent_form",
            
            # Welcome Letters
            "welcome": "welcome_letter",
            "welcome letter": "welcome_letter",
            
            # Billing
            "billing": "billing",
            "medisoft": "medisoft_billing",
            "insurance claim": "medisoft_billing",
            "claim": "tn_refiling",
            "refiling": "tn_refiling",
            "tn refiling": "tn_refiling",
            
            # Intake & Referral
            "referral": "referral",
            "intake": "referral",
            "counselor": "counselor_assignment",
            "assign counselor": "counselor_assignment",
            "remove counselor": "remove_counselor",
            
            # Penelope
            "penelope": "penelope_workflow",
            "workflow": "penelope_workflow",
        }
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for keyword, bot_id in keyword_map.items():
            if keyword in prompt_lower:
                score = len(keyword) / len(prompt_lower)  # Simple scoring
                if score > best_score:
                    best_score = score
                    best_match = {
                        "bot": bot_id,
                        "action": "execute",
                        "params": self._extract_params(prompt),
                        "confidence": min(0.8, best_score * 2),
                        "reasoning": f"Matched keyword '{keyword}' to {bot_id}"
                    }
        
        return best_match
    
    def _extract_params(self, prompt: str) -> Dict:
        """Extract parameters from the prompt (dates, file paths, etc.)"""
        params = {}
        prompt_lower = prompt.lower()
        
        # Extract date-related keywords
        if "this week" in prompt_lower:
            params["date_range"] = "this_week"
        elif "last week" in prompt_lower:
            params["date_range"] = "last_week"
        elif "this month" in prompt_lower:
            params["date_range"] = "this_month"
        elif "last month" in prompt_lower:
            params["date_range"] = "last_month"
        
        # Extract file-related keywords
        if "csv" in prompt_lower or "excel" in prompt_lower:
            params["file_type"] = "csv"
        
        return params
    
    def _llm_interpret(self, prompt: str) -> Dict:
        """
        Use LLM API to interpret the command.
        Currently supports OpenAI and Anthropic APIs.
        """
        try:
            if self.model.startswith("claude"):
                return self._claude_interpret(prompt)
            elif self.model.startswith("gpt"):
                return self._openai_interpret(prompt)
            else:
                # Fallback to fuzzy matching
                return self._fuzzy_match(prompt) or {
                    "bot": None,
                    "action": None,
                    "params": {},
                    "confidence": 0.0,
                    "reasoning": f"Unsupported model: {self.model}"
                }
        except Exception as e:
            # Fallback to fuzzy matching on error
            return self._fuzzy_match(prompt) or {
                "bot": None,
                "action": None,
                "params": {},
                "confidence": 0.0,
                "reasoning": f"LLM interpretation failed: {str(e)}"
            }
    
    def _claude_interpret(self, prompt: str) -> Dict:
        """Use Anthropic Claude API for interpretation"""
        try:
            import anthropic
            
            if not self.api_key:
                return {
                    "bot": None,
                    "action": None,
                    "params": {},
                    "confidence": 0.0,
                    "reasoning": "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
                }
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            # Determine model version
            model_map = {
                "claude-sonnet": "claude-sonnet-3.5-20241022",
                "claude-opus": "claude-opus-20240229",
                "claude-haiku": "claude-3-haiku-20240307"
            }
            
            model_name = model_map.get(self.model, "claude-sonnet-3.5-20241022")
            
            system_prompt = """You are a task routing assistant for an automation system. 
            Analyze user commands and return JSON with:
            - bot: bot identifier (medical_records, consent_form, welcome_letter, medisoft_billing, tn_refiling, referral, counselor_assignment, remove_counselor, penelope_workflow)
            - action: action to perform (usually "execute")
            - params: dictionary of extracted parameters
            - confidence: confidence score 0.0-1.0
            - reasoning: brief explanation
            
            Return ONLY valid JSON, no other text."""
            
            message = client.messages.create(
                model=model_name,
                max_tokens=500,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            response_text = message.content[0].text
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            return result
            
        except ImportError:
            return {
                "bot": None,
                "action": None,
                "params": {},
                "confidence": 0.0,
                "reasoning": "Anthropic SDK not installed. Install with: pip install anthropic"
            }
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
    
    def _openai_interpret(self, prompt: str) -> Dict:
        """Use OpenAI API for interpretation"""
        try:
            import openai

            if not self.api_key:
                return {
                    "bot": None,
                    "action": None,
                    "params": {},
                    "confidence": 0.0,
                    "reasoning": "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
                }

            client = openai.OpenAI(api_key=self.api_key)

            # Determine model version (default to latest recommended lightweight model)
            model_name = self.model or "gpt-5-mini"
            if not model_name.startswith("gpt"):
                model_name = "gpt-5-mini"

            system_prompt = """You are a task routing assistant for an automation system. 
            Analyze user commands and return JSON with:
            - bot: bot identifier (medical_records, consent_form, welcome_letter, medisoft_billing, tn_refiling, referral, counselor_assignment, remove_counselor, penelope_workflow)
            - action: action to perform (usually "execute")
            - params: dictionary of extracted parameters
            - confidence: confidence score 0.0-1.0
            - reasoning: brief explanation
            
            Return ONLY valid JSON, no other text."""
            
            def _call(include_temperature: bool = True, **kwargs):
                call_kwargs = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                }
                if include_temperature:
                    call_kwargs["temperature"] = self.temperature
                call_kwargs.update(kwargs)
                return client.chat.completions.create(**call_kwargs)

            attempt_order = [
                {"include_temperature": True, "param": "max_tokens"},
                {"include_temperature": True, "param": "max_completion_tokens"},
                {"include_temperature": False, "param": "max_tokens"},
                {"include_temperature": False, "param": "max_completion_tokens"},
            ]

            response = None
            last_error: Optional[Exception] = None

            for attempt in attempt_order:
                try:
                    response = _call(
                        include_temperature=attempt["include_temperature"],
                        **{attempt["param"]: 500},
                    )
                    if response:
                        break
                except Exception as exc:
                    code = getattr(exc, "code", "")
                    if code in {"unsupported_parameter", "unsupported_value"}:
                        last_error = exc
                        continue
                    raise

            if response is None and last_error:
                raise last_error
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except ImportError:
            return {
                "bot": None,
                "action": None,
                "params": {},
                "confidence": 0.0,
                "reasoning": "OpenAI SDK not installed. Install with: pip install openai"
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

