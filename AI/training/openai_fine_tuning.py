#!/usr/bin/env python3
"""
OpenAI Fine-Tuning Integration - Send training data to OpenAI for model improvement
Automatically prepares and sends training data to OpenAI API for fine-tuning.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

_LOGGER = logging.getLogger("openai_fine_tuning")


class OpenAIFineTuningManager:
    """Manages OpenAI fine-tuning integration for proprietary AI system."""
    
    def __init__(self, installation_dir: Path, api_key: Optional[str] = None):
        """
        Initialize OpenAI fine-tuning manager.
        
        Args:
            installation_dir: Base installation directory
            api_key: OpenAI API key. If None, loads from llm_config.json
        """
        self.installation_dir = Path(installation_dir)
        self.ai_dir = installation_dir / "AI"
        self.training_data_dir = self.ai_dir / "training_data"
        self.models_dir = self.ai_dir / "models"
        self.models_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Load API key
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._load_api_key()
        
        # Initialize OpenAI client
        self.client = None
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                _LOGGER.info("OpenAI client initialized successfully")
            except Exception as e:
                _LOGGER.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Fine-tuning settings
        self.min_training_examples = 10  # Minimum examples needed for fine-tuning
        self.max_training_examples = 1000  # Maximum examples per fine-tuning job
        
    def _load_api_key(self) -> Optional[str]:
        """Load OpenAI API key from llm_config.json"""
        try:
            config_path = self.installation_dir / "_secure_data" / "llm_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get("provider") == "openai":
                        return config.get("api_key", "")
        except Exception as e:
            _LOGGER.warning(f"Failed to load API key from config: {e}")
        return None
    
    def is_configured(self) -> bool:
        """Check if OpenAI fine-tuning is properly configured"""
        return OPENAI_AVAILABLE and self.client is not None and self.api_key is not None
    
    def prepare_training_data(self, dataset_file: Optional[Path] = None) -> Optional[List[Dict[str, str]]]:
        """
        Prepare training data in OpenAI fine-tuning format.
        
        Format: [{"messages": [{"role": "system", "content": "..."}, 
                               {"role": "user", "content": "..."}, 
                               {"role": "assistant", "content": "..."}]}]
        
        Args:
            dataset_file: Path to training dataset JSON file. If None, uses latest.
            
        Returns:
            List of training examples in OpenAI format, or None if preparation fails
        """
        try:
            # Find dataset file
            if dataset_file is None:
                dataset_file = self._find_latest_training_dataset()
            
            if not dataset_file or not dataset_file.exists():
                _LOGGER.warning("No training dataset found")
                return None
            
            # Load dataset
            _LOGGER.info(f"Loading training dataset: {dataset_file.name}")
            with open(dataset_file, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            # Convert to OpenAI format
            training_examples = []
            
            # Process bot logs - load actual bot log files directly
            bot_log_files = list(self.training_data_dir.glob("bot_logs_*.json"))
            for bot_log_file in bot_log_files[:2]:  # Use last 2 bot log files
                examples = self._extract_bot_examples_from_file(bot_log_file)
                training_examples.extend(examples)
            
            # Also process browser activity
            browser_files = list(self.training_data_dir.glob("browser_activity_*.json"))
            for browser_file in browser_files[:1]:  # Use latest browser activity
                examples = self._extract_browser_examples(browser_file)
                training_examples.extend(examples)
            
            if len(training_examples) < self.min_training_examples:
                _LOGGER.warning(f"Insufficient training examples: {len(training_examples)} < {self.min_training_examples}")
                return None
            
            # Limit to max examples
            if len(training_examples) > self.max_training_examples:
                training_examples = training_examples[:self.max_training_examples]
                _LOGGER.info(f"Limited to {self.max_training_examples} examples")
            
            _LOGGER.info(f"Prepared {len(training_examples)} training examples")
            return training_examples
            
        except Exception as e:
            _LOGGER.error(f"Error preparing training data: {e}")
            return None
    
    def _find_latest_training_dataset(self) -> Optional[Path]:
        """Find the latest training dataset file"""
        try:
            if not self.training_data_dir.exists():
                return None
            
            # Find all training dataset files
            dataset_files = list(self.training_data_dir.glob("training_dataset_*.json"))
            if not dataset_files:
                return None
            
            # Return the most recent one
            return max(dataset_files, key=lambda f: f.stat().st_mtime)
            
        except Exception as e:
            _LOGGER.warning(f"Error finding latest dataset: {e}")
            return None
    
    def _extract_bot_examples_from_file(self, log_file: Path) -> List[Dict[str, Any]]:
        """Extract training examples directly from bot log JSON file."""
        examples = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract entries from bot logs (try different possible structures)
            entries = data.get("log_entries", []) or data.get("entries", []) or []
            if not entries:
                _LOGGER.warning(f"No entries found in {log_file.name}")
                return examples
            
            # Sample entries to create training examples (every Nth entry to get variety)
            # Limit to reasonable number for OpenAI fine-tuning
            max_entries = min(len(entries), 500)  # Use up to 500 entries per file
            sample_rate = max(1, max_entries // 200)  # Get ~200 examples per file
            
            for i in range(0, max_entries, sample_rate):
                entry = entries[i]
                # Handle both dict and string formats
                if isinstance(entry, dict):
                    entry_text = entry.get("entry", "") or entry.get("message", "") or str(entry)
                else:
                    entry_text = str(entry)
                
                if not entry_text or len(entry_text) < 20:
                    continue
                
                # Create training example
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant specialized in healthcare billing automation. You understand bot workflows, user interactions, and can predict next actions."
                        },
                        {
                            "role": "user",
                            "content": f"Bot action: {entry_text[:400]}"
                        },
                        {
                            "role": "assistant",
                            "content": f"This is a {self._classify_action(entry_text)}. The bot is {self._describe_action(entry_text)}."
                        }
                    ]
                }
                examples.append(example)
            
            _LOGGER.info(f"Extracted {len(examples)} examples from {log_file.name}")
            
        except Exception as e:
            _LOGGER.warning(f"Error extracting from {log_file}: {e}")
        
        return examples
    
    def _extract_browser_examples(self, browser_file: Path) -> List[Dict[str, Any]]:
        """Extract training examples from browser activity logs."""
        examples = []
        
        try:
            with open(browser_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            activities = data.get("activities", []) or data.get("entries", [])
            if not activities:
                return examples
            
            # Sample browser activities
            sample_rate = max(1, len(activities) // 100)  # Get ~100 examples
            
            for i in range(0, min(len(activities), 200), sample_rate):
                activity = activities[i]
                activity_text = str(activity)[:300]
                
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You understand browser automation patterns and user navigation flows in healthcare billing systems."
                        },
                        {
                            "role": "user",
                            "content": f"Browser activity: {activity_text}"
                        },
                        {
                            "role": "assistant",
                            "content": "I understand this browser interaction pattern in the healthcare billing workflow."
                        }
                    ]
                }
                examples.append(example)
            
            _LOGGER.info(f"Extracted {len(examples)} examples from {browser_file.name}")
            
        except Exception as e:
            _LOGGER.warning(f"Error extracting browser examples: {e}")
        
        return examples
    
    def _extract_bot_examples(self, source: Dict) -> List[Dict[str, Any]]:
        """Legacy method - now redirects to file-based extraction."""
        return []
    
    def _classify_action(self, entry_text: str) -> str:
        """Classify the type of action from log entry text."""
        entry_lower = entry_text.lower()
        
        if "login" in entry_lower or "authenticate" in entry_lower:
            return "authentication"
        elif "click" in entry_lower or "button" in entry_lower:
            return "UI interaction"
        elif "navigate" in entry_lower or "open" in entry_lower:
            return "navigation"
        elif "error" in entry_lower or "failed" in entry_lower:
            return "error handling"
        elif "parse" in entry_lower or "extract" in entry_lower:
            return "data extraction"
        elif "fill" in entry_lower or "input" in entry_lower:
            return "data entry"
        else:
            return "workflow action"
    
    def _describe_action(self, entry_text: str) -> str:
        """Describe what the bot is doing in this action."""
        entry_lower = entry_text.lower()
        
        if "success" in entry_lower:
            return "successfully completing a workflow step"
        elif "error" in entry_lower or "failed" in entry_lower:
            return "handling an error condition"
        elif "wait" in entry_lower or "sleep" in entry_lower:
            return "waiting for a system response"
        elif "found" in entry_lower or "located" in entry_lower:
            return "locating UI elements or data"
        elif "processing" in entry_lower:
            return "processing data or files"
        else:
            return "executing a workflow step"
    
    def upload_training_file(self, training_data: List[Dict[str, str]]) -> Optional[str]:
        """
        Upload training data to OpenAI and return file ID.
        
        Args:
            training_data: List of training examples in OpenAI format
            
        Returns:
            File ID from OpenAI, or None if upload fails
        """
        if not self.is_configured():
            _LOGGER.error("OpenAI not configured")
            return None
        
        try:
            # Save training data to temporary file
            temp_file = self.models_dir / f"fine_tuning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
            # Convert to JSONL format (one JSON object per line)
            with open(temp_file, 'w', encoding='utf-8') as f:
                for example in training_data:
                    f.write(json.dumps(example) + '\n')
            
            # Upload to OpenAI
            _LOGGER.info(f"Uploading training file to OpenAI: {temp_file.name}")
            with open(temp_file, 'rb') as f:
                response = self.client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            file_id = response.id
            _LOGGER.info(f"Training file uploaded successfully. File ID: {file_id}")
            
            # Save file ID for reference
            self._save_file_id(file_id, temp_file)
            
            return file_id
            
        except Exception as e:
            _LOGGER.error(f"Error uploading training file: {e}")
            return None
    
    def create_fine_tuning_job(self, file_id: str, model: str = "gpt-3.5-turbo", 
                               suffix: Optional[str] = None) -> Optional[str]:
        """
        Create a fine-tuning job with OpenAI.
        
        Args:
            file_id: File ID from uploaded training data
            model: Base model to fine-tune (default: gpt-3.5-turbo)
            suffix: Optional suffix for the fine-tuned model name
            
        Returns:
            Fine-tuning job ID, or None if creation fails
        """
        if not self.is_configured():
            _LOGGER.error("OpenAI not configured")
            return None
        
        try:
            _LOGGER.info(f"Creating fine-tuning job for model: {model}")
            
            job_params = {
                "training_file": file_id,
                "model": model
            }
            
            if suffix:
                job_params["suffix"] = suffix
            
            response = self.client.fine_tuning.jobs.create(**job_params)
            
            job_id = response.id
            _LOGGER.info(f"Fine-tuning job created successfully. Job ID: {job_id}")
            
            # Save job ID for tracking
            self._save_job_id(job_id, file_id, model)
            
            return job_id
            
        except Exception as e:
            _LOGGER.error(f"Error creating fine-tuning job: {e}")
            return None
    
    def check_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Check the status of a fine-tuning job"""
        if not self.is_configured():
            return None
        
        try:
            response = self.client.fine_tuning.jobs.retrieve(job_id)
            return {
                "id": response.id,
                "status": response.status,
                "model": response.model,
                "fine_tuned_model": getattr(response, 'fine_tuned_model', None),
                "created_at": response.created_at,
                "finished_at": getattr(response, 'finished_at', None)
            }
        except Exception as e:
            _LOGGER.error(f"Error checking job status: {e}")
            return None
    
    def _save_file_id(self, file_id: str, file_path: Path) -> None:
        """Save file ID for reference"""
        try:
            metadata_file = self.models_dir / "fine_tuning_metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            if "files" not in metadata:
                metadata["files"] = []
            
            metadata["files"].append({
                "file_id": file_id,
                "file_path": str(file_path),
                "uploaded_at": datetime.now().isoformat()
            })
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            _LOGGER.warning(f"Error saving file ID: {e}")
    
    def _save_job_id(self, job_id: str, file_id: str, model: str) -> None:
        """Save job ID for tracking"""
        try:
            metadata_file = self.models_dir / "fine_tuning_metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            if "jobs" not in metadata:
                metadata["jobs"] = []
            
            metadata["jobs"].append({
                "job_id": job_id,
                "file_id": file_id,
                "model": model,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            })
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            _LOGGER.warning(f"Error saving job ID: {e}")
    
    def run_fine_tuning_pipeline(self, model: str = "gpt-3.5-turbo", 
                                 suffix: Optional[str] = None) -> Optional[str]:
        """
        Complete fine-tuning pipeline: prepare data, upload, and create job.
        
        Args:
            model: Base model to fine-tune
            suffix: Optional suffix for fine-tuned model
            
        Returns:
            Fine-tuning job ID, or None if pipeline fails
        """
        if not self.is_configured():
            _LOGGER.error("OpenAI fine-tuning not configured. Check API key.")
            return None
        
        # Step 1: Prepare training data
        training_data = self.prepare_training_data()
        if not training_data:
            _LOGGER.error("Failed to prepare training data")
            return None
        
        # Step 2: Upload training file
        file_id = self.upload_training_file(training_data)
        if not file_id:
            _LOGGER.error("Failed to upload training file")
            return None
        
        # Step 3: Create fine-tuning job
        job_id = self.create_fine_tuning_job(file_id, model=model, suffix=suffix)
        if not job_id:
            _LOGGER.error("Failed to create fine-tuning job")
            return None
        
        _LOGGER.info(f"Fine-tuning pipeline completed. Job ID: {job_id}")
        return job_id


def get_fine_tuning_manager(installation_dir: Optional[Path] = None, 
                           api_key: Optional[str] = None) -> OpenAIFineTuningManager:
    """Get or create OpenAI fine-tuning manager instance"""
    if installation_dir is None:
        # Auto-detect installation directory
        current_file = Path(__file__).resolve()
        if current_file.parent.name == "training" and current_file.parent.parent.name == "AI":
            installation_dir = current_file.parent.parent.parent
        else:
            installation_dir = current_file.parent.parent.parent
    
    return OpenAIFineTuningManager(Path(installation_dir), api_key=api_key)

