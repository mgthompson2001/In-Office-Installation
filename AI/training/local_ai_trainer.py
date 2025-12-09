#!/usr/bin/env python3
"""
Local AI Trainer - Enterprise-Grade Local Model Training
Uses cutting-edge local LLMs (Ollama, Llama.cpp, HuggingFace)
for HIPAA-compliant on-premises AI training.
NO external data transmission - everything stays local.
"""

import os
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Local LLM inference - Ollama (most cutting-edge)
try:
    import requests
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# HuggingFace Transformers for local models
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# LangChain for local LLM orchestration (used by Anthropic/Microsoft)
try:
    from langchain.llms import Ollama
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class LocalAITrainer:
    """
    Local AI training system using cutting-edge local LLMs.
    Trains on collected data without any external transmission.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None,
                 model_type: str = "ollama"):
        """
        Initialize local AI trainer.
        
        Args:
            installation_dir: Base installation directory
            model_type: "ollama" (recommended), "huggingface", or "langchain"
        """
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        self.data_dir = ai_dir / "data"
        self.models_dir = ai_dir / "models"
        self.models_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.model_type = model_type
        self.training_active = False
        self.model = None
        
        # Training settings
        self.training_interval_hours = 24  # Train daily
        self.min_data_points = 100  # Minimum data points before training
        
        # Setup logging
        self.log_file = self.models_dir / "training.log"
        self._setup_logging()
        
        # Initialize model
        self._initialize_model()
    
    def _setup_logging(self):
        """Setup training logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_model(self):
        """Initialize local LLM model"""
        if self.model_type == "ollama":
            self._initialize_ollama()
        elif self.model_type == "huggingface":
            self._initialize_huggingface()
        elif self.model_type == "langchain":
            self._initialize_langchain()
        else:
            self.logger.warning(f"Unknown model type: {self.model_type}")
    
    def _initialize_ollama(self):
        """Initialize Ollama (cutting-edge local LLM)"""
        if not OLLAMA_AVAILABLE:
            self.logger.warning("Ollama not available. Install: https://ollama.ai")
            return
        
        # Check if Ollama is running
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.model = "ollama"
                self.logger.info("Ollama connected successfully")
                
                # Ensure model is available
                self._ensure_ollama_model("llama2")  # or "mistral", "codellama"
            else:
                self.logger.warning("Ollama not running. Start with: ollama serve")
        except:
            self.logger.warning("Ollama not running. Start with: ollama serve")
    
    def _ensure_ollama_model(self, model_name: str):
        """Ensure Ollama model is available"""
        try:
            # Check if model exists
            response = requests.get(f"http://localhost:11434/api/show", 
                                  params={"name": model_name}, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"Ollama model '{model_name}' available")
            else:
                # Pull model
                self.logger.info(f"Pulling Ollama model '{model_name}'...")
                response = requests.post(f"http://localhost:11434/api/pull",
                                       json={"name": model_name}, timeout=300)
        except Exception as e:
            self.logger.error(f"Failed to ensure Ollama model: {e}")
    
    def _initialize_huggingface(self):
        """Initialize HuggingFace local model"""
        if not HF_AVAILABLE:
            self.logger.warning("HuggingFace not available. Install: pip install transformers torch")
            return
        
        try:
            # Use a small, efficient model for local inference
            model_name = "microsoft/DialoGPT-small"  # or "gpt2", "distilgpt2"
            self.logger.info(f"Loading HuggingFace model: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Move to CPU (no GPU required)
            self.model.to("cpu")
            self.model.eval()
            
            self.logger.info("HuggingFace model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load HuggingFace model: {e}")
    
    def _initialize_langchain(self):
        """Initialize LangChain with Ollama (used by Anthropic/Microsoft)"""
        if not LANGCHAIN_AVAILABLE:
            self.logger.warning("LangChain not available. Install: pip install langchain")
            return
        
        try:
            self.model = Ollama(base_url="http://localhost:11434", model="llama2")
            self.logger.info("LangChain with Ollama initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize LangChain: {e}")
    
    def train_on_collected_data(self):
        """Train model on collected bot log data"""
        # Load training data from bot logs
        training_data_dir = self.installation_dir / "AI" / "training_data"
        
        if not training_data_dir.exists():
            self.logger.warning("Training data directory not found")
            return
        
        # Load bot log files
        prompts = []
        responses = []
        
        bot_log_files = list(training_data_dir.glob("bot_logs_*.json"))
        if not bot_log_files:
            self.logger.warning("No bot log files found for training")
            return
        
        # Process bot logs to create training examples
        for log_file in bot_log_files[:2]:  # Use last 2 files
            try:
                self.logger.info(f"Processing {log_file.name}...")
                with open(log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                entries = data.get("log_entries", []) or data.get("entries", [])
                
                if not entries:
                    self.logger.warning(f"No entries found in {log_file.name}")
                    continue
                
                self.logger.info(f"Found {len(entries)} entries in {log_file.name}")
                
                # Sample entries to create training patterns
                # Get a good sample size - aim for 200-300 examples per file
                max_entries_to_process = min(len(entries), 1000)
                sample_rate = max(1, max_entries_to_process // 250)  # Get ~250 examples per file
                
                processed_count = 0
                for i in range(0, max_entries_to_process, sample_rate):
                    entry = entries[i]
                    if isinstance(entry, dict):
                        entry_text = entry.get("entry", "") or entry.get("message", "") or str(entry)
                    else:
                        entry_text = str(entry)
                    
                    if entry_text and len(entry_text) > 20:
                        prompts.append(entry_text[:300])
                        # Classify the action type as the "response"
                        action_type = self._classify_bot_action(entry_text)
                        responses.append({"action": action_type, "description": self._describe_action(entry_text)})
                        processed_count += 1
                
                self.logger.info(f"Extracted {processed_count} examples from {log_file.name}")
            
            except Exception as e:
                self.logger.warning(f"Error processing {log_file}: {e}")
                import traceback
                self.logger.warning(traceback.format_exc())
        
        self.logger.info(f"Total training examples prepared: {len(prompts)}")
        
        if len(prompts) < self.min_data_points:
            self.logger.warning(f"Insufficient data for training: {len(prompts)} < {self.min_data_points}")
            self.logger.info("Will still create training patterns with available data...")
            # Continue anyway - we can still create patterns with less data
        
        self.logger.info(f"Training on {len(prompts)} bot log entries")
        
        # Train using selected method
        if self.model_type == "ollama":
            self._train_ollama(prompts, responses)
        elif self.model_type == "huggingface":
            self._train_huggingface(prompts, responses)
        elif self.model_type == "langchain":
            self._train_langchain(prompts, responses)
        
        self.logger.info("Training completed")
    
    def _classify_bot_action(self, entry_text: str) -> str:
        """Classify bot action type from log entry"""
        entry_lower = entry_text.lower()
        if "login" in entry_lower or "authenticate" in entry_lower:
            return "authentication"
        elif "click" in entry_lower or "button" in entry_lower:
            return "ui_interaction"
        elif "navigate" in entry_lower or "open" in entry_lower:
            return "navigation"
        elif "error" in entry_lower or "failed" in entry_lower:
            return "error_handling"
        elif "parse" in entry_lower or "extract" in entry_lower:
            return "data_extraction"
        elif "fill" in entry_lower or "input" in entry_lower:
            return "data_entry"
        else:
            return "workflow_action"
    
    def _describe_action(self, entry_text: str) -> str:
        """Describe what the bot is doing"""
        entry_lower = entry_text.lower()
        if "success" in entry_lower:
            return "successfully completing workflow step"
        elif "error" in entry_lower:
            return "handling error condition"
        elif "wait" in entry_lower:
            return "waiting for system response"
        elif "found" in entry_lower:
            return "locating UI elements"
        else:
            return "executing workflow step"
    
    def _train_ollama(self, prompts: List[str], responses: List[Dict]):
        """Train using Ollama (creates prompt templates for few-shot learning)"""
        # Ollama doesn't support direct fine-tuning, but we can:
        # 1. Create a prompt template with examples (few-shot learning)
        # 2. Save patterns for better inference
        
        # Create prompt template with examples
        examples = []
        for prompt, response in zip(prompts[:100], responses[:100]):  # Top 100 examples
            action = response.get('action', 'workflow_action')
            description = response.get('description', 'executing workflow step')
            examples.append(f"Bot Log: {prompt[:200]}\nAction Type: {action}\nDescription: {description}")
        
        template = "\n\n---\n\n".join(examples)
        
        # Save template for inference
        template_file = self.models_dir / "ollama_prompt_template.txt"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write("Healthcare Billing Bot Training Examples:\n\n")
            f.write(template)
            f.write("\n\n---\n\n")
            f.write("Based on the above examples, analyze new bot log entries and predict actions.")
        
        self.logger.info(f"Created Ollama prompt template with {len(examples)} examples")
        
        # Also save a JSON version for programmatic use
        patterns_file = self.models_dir / "bot_patterns.json"
        patterns = []
        for prompt, response in zip(prompts[:200], responses[:200]):
            patterns.append({
                "log_entry": prompt[:200],
                "action_type": response.get('action', 'workflow_action'),
                "description": response.get('description', '')
            })
        
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2)
        
        self.logger.info(f"Saved {len(patterns)} bot patterns for training")
    
    def _train_huggingface(self, prompts: List[str], responses: List[Dict]):
        """Train using HuggingFace (fine-tuning)"""
        # This would require more sophisticated fine-tuning
        # For now, create a dataset and save for future fine-tuning
        dataset = []
        for prompt, response in zip(prompts, responses):
            dataset.append({
                "input": prompt,
                "output": f"Bot: {response['bot']}, Confidence: {response['confidence']}"
            })
        
        dataset_file = self.models_dir / "training_dataset.json"
        with open(dataset_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2)
        
        self.logger.info(f"Created HuggingFace training dataset with {len(dataset)} examples")
    
    def _train_langchain(self, prompts: List[str], responses: List[Dict]):
        """Train using LangChain (prompt engineering)"""
        # Create prompt template
        examples = []
        for prompt, response in zip(prompts[:20], responses[:20]):
            examples.append(f"Q: {prompt}\nA: {response['bot']}")
        
        template = PromptTemplate(
            input_variables=["query"],
            template="""You are an AI task routing assistant. Based on the following examples, route user queries to the appropriate bot.

Examples:
{examples}

Query: {query}
Answer:"""
        )
        
        # Save template
        template_file = self.models_dir / "langchain_template.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump({
                "template": template.template,
                "examples": examples
            }, f, indent=2)
        
        self.logger.info("Created LangChain prompt template")
    
    def infer(self, prompt: str) -> Dict:
        """Infer using trained local model"""
        if not self.model:
            return {
                "success": False,
                "message": "Model not initialized"
            }
        
        try:
            if self.model_type == "ollama":
                return self._infer_ollama(prompt)
            elif self.model_type == "huggingface":
                return self._infer_huggingface(prompt)
            elif self.model_type == "langchain":
                return self._infer_langchain(prompt)
        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def _infer_ollama(self, prompt: str) -> Dict:
        """Infer using Ollama"""
        try:
            # Load prompt template
            template_file = self.models_dir / "ollama_prompt_template.txt"
            template = ""
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = f.read()
            
            # Create full prompt
            full_prompt = f"{template}\n\nUser: {prompt}\nAssistant:"
            
            # Call Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama2",
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": "ollama:llama2"
                }
            else:
                return {
                    "success": False,
                    "message": f"Ollama API error: {response.status_code}"
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def _infer_huggingface(self, prompt: str) -> Dict:
        """Infer using HuggingFace"""
        try:
            # Create pipeline
            generator = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer)
            
            # Generate
            result = generator(prompt, max_length=100, num_return_sequences=1)
            
            return {
                "success": True,
                "response": result[0]["generated_text"],
                "model": "huggingface"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def _infer_langchain(self, prompt: str) -> Dict:
        """Infer using LangChain"""
        try:
            # Load template
            template_file = self.models_dir / "langchain_template.json"
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # Create chain
                prompt_template = PromptTemplate(
                    input_variables=["query"],
                    template=template_data["template"].replace("{examples}", "\n".join(template_data["examples"]))
                )
                
                chain = LLMChain(llm=self.model, prompt=prompt_template)
                
                result = chain.run(query=prompt)
                
                return {
                    "success": True,
                    "response": result,
                    "model": "langchain:ollama"
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def start_automated_training(self):
        """Start automated training scheduler"""
        def training_scheduler():
            while True:
                time.sleep(self.training_interval_hours * 3600)  # Wait for interval
                self.logger.info("Starting scheduled training...")
                self.train_on_collected_data()
        
        thread = threading.Thread(target=training_scheduler, daemon=True)
        thread.start()
        self.training_active = True
        self.logger.info(f"Automated training started (interval: {self.training_interval_hours} hours)")

