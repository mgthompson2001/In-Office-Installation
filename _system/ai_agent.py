#!/usr/bin/env python3
"""
AI Agent - LLM Interface for Natural Language Interpretation
Handles communication with OpenAI and Anthropic APIs for task understanding.
"""

import os
import json
from typing import Dict, Optional, List
from pathlib import Path

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# Try to import Anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class AIAgent:
    """
    LLM interface for natural language task interpretation.
    Supports OpenAI (GPT) and Anthropic (Claude) APIs.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize AI Agent"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.config_dir = self.installation_dir / "_system"
        self.config_file = self.config_dir / "ai_agent_config.json"
        
        # Load API keys
        self.openai_api_key = None
        self.anthropic_api_key = None
        self._load_api_keys()
        
        # Default model preferences
        self.preferred_provider = "openai"  # or "anthropic"
        self.openai_model = "gpt-5-mini"  # Cost-effective default
        self.anthropic_model = "claude-3-haiku-20240307"  # Cost-effective default
    
    def _load_api_keys(self):
        """Load API keys from config file or environment variables"""
        # Try environment variables first
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Try config file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if not self.openai_api_key:
                        self.openai_api_key = config.get("openai_api_key")
                    if not self.anthropic_api_key:
                        self.anthropic_api_key = config.get("anthropic_api_key")
                    self.preferred_provider = config.get("preferred_provider", "openai")
            except Exception:
                pass
    
    def _save_api_keys(self):
        """Save API keys to config file (encrypted in production)"""
        try:
            config = {
                "openai_api_key": self.openai_api_key,
                "anthropic_api_key": self.anthropic_api_key,
                "preferred_provider": self.preferred_provider
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass  # Silent fail
    
    def is_configured(self) -> bool:
        """Check if at least one API is configured"""
        return bool(self.openai_api_key) or bool(self.anthropic_api_key)
    
    def interpret_task(self, user_prompt: str, available_bots: Dict[str, str]) -> Dict:
        """
        Interpret user's natural language prompt and determine which bot to use.
        
        Args:
            user_prompt: User's natural language command
            available_bots: Dictionary of bot names to descriptions
            
        Returns:
            Dictionary with:
                - bot_name: Name of selected bot (or None)
                - confidence: Confidence score (0.0-1.0)
                - reasoning: Explanation of the selection
                - error: Error message if any
        """
        if not self.is_configured():
            return {
                "bot_name": None,
                "confidence": 0.0,
                "reasoning": "No API keys configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables.",
                "error": "API_NOT_CONFIGURED"
            }
        
        # Build bot list for context
        bot_list = "\n".join([
            f"- {name}: {info.get('description', 'No description')}"
            for name, info in available_bots.items()
        ])
        
        # Create prompt for LLM
        system_prompt = f"""You are an AI assistant that helps users select the right automation bot based on their natural language requests.

Available bots:
{bot_list}

Your task:
1. Understand what the user wants to do
2. Match their request to the most appropriate bot from the list above
3. Return ONLY a JSON object with:
   - "bot_name": The exact name of the bot (must match one from the list above, or null if no match)
   - "confidence": A number between 0.0 and 1.0 indicating how confident you are
   - "reasoning": A brief explanation of why you selected this bot

If no bot matches the user's request, set bot_name to null and explain why in reasoning."""

        user_message = f"User request: {user_prompt}"
        
        # Try preferred provider first, then fallback
        providers = [self.preferred_provider]
        if self.preferred_provider == "openai":
            providers.append("anthropic")
        else:
            providers.append("openai")
        
        for provider in providers:
            try:
                if provider == "openai" and OPENAI_AVAILABLE and self.openai_api_key:
                    return self._call_openai(system_prompt, user_message, available_bots)
                elif provider == "anthropic" and ANTHROPIC_AVAILABLE and self.anthropic_api_key:
                    return self._call_anthropic(system_prompt, user_message, available_bots)
            except Exception as e:
                continue  # Try next provider
        
        return {
            "bot_name": None,
            "confidence": 0.0,
            "reasoning": f"Failed to call AI service. Error: {str(e)}",
            "error": "API_CALL_FAILED"
        }
    
    def _call_openai(self, system_prompt: str, user_message: str, available_bots: Dict) -> Dict:
        """Call OpenAI API"""
        if not OPENAI_AVAILABLE or not self.openai_api_key:
            raise Exception("OpenAI not available")
        
        client = openai.OpenAI(api_key=self.openai_api_key)
        
        def _call(include_temperature: bool = True, **kwargs):
            call_kwargs = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {"type": "json_object"},
            }
            if include_temperature:
                call_kwargs["temperature"] = 0.3  # Lower temperature for more consistent results
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
        
        # Parse response
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
            # Validate bot_name exists in available_bots
            if result.get("bot_name") and result["bot_name"] not in available_bots:
                result["bot_name"] = None
                result["reasoning"] = f"Selected bot '{result.get('bot_name')}' not found in available bots."
                result["confidence"] = 0.0
            return result
        except json.JSONDecodeError:
            return {
                "bot_name": None,
                "confidence": 0.0,
                "reasoning": "Failed to parse AI response",
                "error": "PARSE_ERROR"
            }
    
    def _call_anthropic(self, system_prompt: str, user_message: str, available_bots: Dict) -> Dict:
        """Call Anthropic API"""
        if not ANTHROPIC_AVAILABLE or not self.anthropic_api_key:
            raise Exception("Anthropic not available")
        
        client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        
        response = client.messages.create(
            model=self.anthropic_model,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ],
            temperature=0.3
        )
        
        # Parse response
        content = response.content[0].text
        
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Try parsing entire content as JSON
                result = json.loads(content)
            
            # Validate bot_name exists in available_bots
            if result.get("bot_name") and result["bot_name"] not in available_bots:
                result["bot_name"] = None
                result["reasoning"] = f"Selected bot '{result.get('bot_name')}' not found in available bots."
                result["confidence"] = 0.0
            return result
        except (json.JSONDecodeError, AttributeError):
            return {
                "bot_name": None,
                "confidence": 0.0,
                "reasoning": "Failed to parse AI response",
                "error": "PARSE_ERROR"
            }

