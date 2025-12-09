"""LLM integration utilities for Master AI Dashboard."""

from __future__ import annotations

import json
import threading
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List
from pathlib import Path

try:
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except Exception as exc:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore
    print(f"[LLMService] OpenAI import failed: {exc}")

from .sanitizer import sanitize_text


CONFIG_FILE_NAME = "llm_config.json"


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-5-mini"
    api_key: str = ""
    temperature: float = 0.2


class LLMService:
    """Manages LLM configuration and calls to external providers."""

    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.secure_dir = self.installation_dir / "_secure_data"
        self.secure_dir.mkdir(exist_ok=True, mode=0o700)
        self.config_path = self.secure_dir / CONFIG_FILE_NAME
        self._config_lock = threading.Lock()
        self._config = self._load_config()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def _load_config(self) -> LLMConfig:
        if not self.config_path.exists():
            return LLMConfig()
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            return LLMConfig(
                provider=data.get("provider", "openai"),
                model=data.get("model", "gpt-5-mini"),
                api_key=data.get("api_key", ""),
                temperature=float(data.get("temperature", 0.2)),
            )
        except Exception:
            return LLMConfig()

    def save_config(self, api_key: str, model: str, provider: str = "openai", temperature: float = 0.2) -> None:
        with self._config_lock:
            self._config = LLMConfig(provider=provider, model=model, api_key=api_key, temperature=temperature)
            self.config_path.write_text(
                json.dumps(self._config.__dict__, indent=2),
                encoding="utf-8"
            )

    def get_config(self) -> LLMConfig:
        return self._config

    def is_configured(self) -> bool:
        cfg = self.get_config()
        return bool(cfg.api_key and cfg.model and cfg.provider == "openai")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def available(self) -> bool:
        return OPENAI_AVAILABLE

    def generate_summary(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> Optional[str]:
        if not self.is_configured() or not OPENAI_AVAILABLE:
            return None

        cfg = self.get_config()
        sanitized_prompt = sanitize_text(prompt)

        try:
            client = OpenAI(api_key=cfg.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": sanitize_text(system_prompt)})
            else:
                messages.append({"role": "system", "content": "You are a helpful assistant that summarizes business workflows."})
            messages.append({"role": "user", "content": sanitized_prompt})

            attempt_order = [
                {"include_temperature": True, "param": "max_tokens"},
                {"include_temperature": True, "param": "max_completion_tokens"},
                {"include_temperature": False, "param": "max_tokens"},
                {"include_temperature": False, "param": "max_completion_tokens"},
            ]

            primary_model = cfg.model
            fallback_models = []
            if primary_model in {"gpt-5-mini", "gpt-5"}:
                fallback_models.extend(["gpt-5-nano", "gpt-4o-mini"])
            elif primary_model == "gpt-5-nano":
                fallback_models.append("gpt-4o-mini")

            models_to_try = [primary_model] + [m for m in fallback_models if m != primary_model]

            last_error: Optional[Exception] = None

            for model_name in models_to_try:
                response = None
                for attempt in attempt_order:
                    try:
                        call_kwargs = {
                            "model": model_name,
                            "messages": messages,
                            attempt["param"]: max_tokens,
                        }
                        if attempt["include_temperature"]:
                            call_kwargs["temperature"] = cfg.temperature
                        response = client.chat.completions.create(**call_kwargs)
                        if response:
                            break
                    except Exception as exc:
                        code = getattr(exc, "code", "")
                        if code in {"unsupported_parameter", "unsupported_value"}:
                            last_error = exc
                            continue
                        last_error = exc
                        response = None
                        break

                if response and response.choices:
                    content = response.choices[0].message.content or ""
                    if content.strip():
                        if model_name != primary_model:
                            print(f"LLMService: Falling back to {model_name} (primary {primary_model} produced no response)")
                        return content
                    else:
                        # Empty response, try next model in list
                        last_error = Exception("Empty response from LLM")

            if last_error:
                raise last_error
        except Exception as exc:
            print(f"LLMService error: {exc}")
        return None
    
    def generate_summary_with_images(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None, 
        max_tokens: int = 500,
        images: Optional[List[Path]] = None
    ) -> Optional[str]:
        """Generate summary using OpenAI Vision API with image analysis"""
        if not self.is_configured() or not OPENAI_AVAILABLE:
            return None
        
        if not images:
            # Fallback to text-only
            return self.generate_summary(prompt, system_prompt, max_tokens)
        
        cfg = self.get_config()
        sanitized_prompt = sanitize_text(prompt)
        
        try:
            client = OpenAI(api_key=cfg.api_key)
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": sanitize_text(system_prompt)})
            else:
                messages.append({"role": "system", "content": "You are a helpful assistant that analyzes workflow screenshots and summarizes business workflows."})
            
            # Build content with text and images
            content = [{"type": "text", "text": sanitized_prompt}]
            
            # Add images (base64 encoded)
            import base64
            for img_path in images[:10]:  # Limit to 10 images to avoid token limits
                try:
                    if img_path.exists():
                        with open(img_path, "rb") as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_data}"
                                }
                            })
                except Exception as e:
                    print(f"Could not encode image {img_path}: {e}")
                    continue
            
            messages.append({"role": "user", "content": content})
            
            # Use gpt-4o or gpt-4o-mini for vision (they support images)
            vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-vision-preview"]
            last_error = None
            
            for model_name in vision_models:
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=cfg.temperature
                    )
                    
                    if response and response.choices:
                        content = response.choices[0].message.content or ""
                        if content.strip():
                            print(f"Vision API analysis completed using {model_name}")
                            return content
                except Exception as exc:
                    last_error = exc
                    code = getattr(exc, "code", "")
                    if code == "model_not_found":
                        continue
                    print(f"Vision API error with {model_name}: {exc}")
            
            if last_error:
                print(f"All vision models failed, falling back to text-only")
                return self.generate_summary(prompt, system_prompt, max_tokens)
            
        except Exception as exc:
            print(f"LLMService Vision API error: {exc}")
            # Fallback to text-only
            return self.generate_summary(prompt, system_prompt, max_tokens)
        
        return None

    def chat(self, user_prompt: str, context: Optional[str] = None) -> Optional[str]:
        if not self.is_configured() or not OPENAI_AVAILABLE:
            return None

        system_prompt = (
            "You are the AI assistant inside the Master AI Dashboard. Provide concise, actionable answers based on the user's workflow data."
        )
        if context:
            system_prompt += "\nContext:\n" + sanitize_text(context)

        return self.generate_summary(user_prompt, system_prompt=system_prompt, max_tokens=700)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def redact_and_prepare_workflow(self, workflow: Dict) -> str:
        lines = []
        lines.append(f"Workflow ID: {workflow.get('workflow_id')}")
        lines.append(f"Goal: {workflow.get('goal')}")
        lines.append(f"Type: {workflow.get('workflow_type')}")
        lines.append(f"Confidence: {workflow.get('confidence', 0.0):.2f}")
        steps = workflow.get("steps", [])

        business_steps = [
            step for step in steps
            if step.get("intent_category") != "development_activity"
        ]

        intents = Counter(
            step.get("intent_category") for step in business_steps if step.get("intent_category")
        )
        applications = Counter(
            step.get("contexts", {}).get("application")
            for step in business_steps
            if step.get("contexts", {}).get("application")
        )

        if intents:
            top_intents = ", ".join(
                f"{intent}:{count}" for intent, count in intents.most_common(3)
            )
            lines.append(f"Top intents: {top_intents}")
        if applications:
            top_apps = ", ".join(
                f"{app}:{count}" for app, count in applications.most_common(3)
            )
            lines.append(f"Primary applications: {top_apps}")

        lines.append("Steps:")
        for step in steps[:50]:  # limit to reduce token usage
            intent = step.get("intent_description") or step.get("intent_category")
            contexts = step.get("contexts", {})
            context_str = ", ".join(f"{k}={v}" for k, v in contexts.items())
            lines.append(f"- {intent} [{context_str}]")
        if len(steps) > 50:
            lines.append("(Only first 50 steps shown.)")
        return sanitize_text("\n".join(lines))

