#!/usr/bin/env python3
"""
AI Training Status Report
Shows current status of proprietary AI training system.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Get installation directory (parent of _tools)
installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"
training_data_dir = ai_dir / "training_data"
models_dir = ai_dir / "models"
secure_data_dir = installation_dir / "_secure_data"

print("=" * 70)
print("PROPRIETARY AI TRAINING STATUS REPORT")
print("=" * 70)
print()

# 1. Data Collection Status
print("📊 DATA COLLECTION STATUS")
print("-" * 70)
training_files = list(training_data_dir.glob("*.json")) if training_data_dir.exists() else []
if training_files:
    total_size = sum(f.stat().st_size for f in training_files) / (1024 * 1024)  # MB
    print(f"✅ Training data collected: {len(training_files)} files ({total_size:.2f} MB)")
    
    # Count records
    total_records = 0
    for file in training_files:
        if "training_dataset" in file.name:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    sources = data.get("data_sources", [])
                    for source in sources:
                        total_records += source.get("record_count", 0)
            except:
                pass
    
    print(f"   Total records: ~{total_records:,}")
    print(f"   Latest dataset: {max(training_files, key=lambda f: f.stat().st_mtime).name}")
else:
    print("❌ No training data files found")

print()

# 2. Local Training Status (Ollama)
print("🤖 LOCAL AI TRAINING STATUS (Ollama)")
print("-" * 70)
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    if response.status_code == 200:
        print("✅ Ollama is running")
        models = response.json().get("models", [])
        print(f"   Available models: {len(models)}")
        for model in models[:3]:  # Show first 3
            print(f"   - {model.get('name', 'Unknown')}")
    else:
        print("❌ Ollama is not responding")
except:
    print("❌ Ollama is NOT running")
    print("   To enable local training: Install Ollama from https://ollama.ai")

print()

# 3. OpenAI Fine-Tuning Status
print("🔮 OPENAI FINE-TUNING STATUS")
print("-" * 70)
config_path = secure_data_dir / "llm_config.json"
if config_path.exists():
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            if config.get("api_key") and config.get("provider") == "openai":
                print("✅ OpenAI API configured")
                print(f"   Model: {config.get('model', 'Unknown')}")
                
                # Check for fine-tuning metadata
                metadata_path = models_dir / "fine_tuning_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        jobs = metadata.get("jobs", [])
                        if jobs:
                            print(f"   Fine-tuning jobs: {len(jobs)}")
                            latest_job = max(jobs, key=lambda j: j.get("created_at", ""))
                            print(f"   Latest job: {latest_job.get('created_at', 'Unknown')}")
                            print(f"   Status: {latest_job.get('status', 'Unknown')}")
                        else:
                            print("   ⚠️  No fine-tuning jobs created yet")
                else:
                    print("   ⚠️  Fine-tuning not started yet")
            else:
                print("❌ OpenAI API not configured")
    except Exception as e:
        print(f"❌ Error reading config: {e}")
else:
    print("❌ OpenAI API not configured")

print()

# 4. Training Integration Status
print("🔄 TRAINING INTEGRATION STATUS")
print("-" * 70)
integration_log = models_dir / "ai_training_integration.log"
if integration_log.exists() and integration_log.stat().st_size > 0:
    print("✅ Training integration is active")
    # Read last few lines
    with open(integration_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_line = lines[-1].strip()
            print(f"   Last activity: {last_line[:100]}...")
else:
    print("⚠️  Training integration log is empty")
    print("   This may mean training hasn't run yet")

print()

# 5. Data Processing Status
print("📈 DATA PROCESSING STATUS")
print("-" * 70)
# Check if cleanup has run (which triggers AI learning)
cleanup_log = installation_dir / "_system" / "logs" / "system_cleanup.log"
if cleanup_log.exists():
    print("✅ Cleanup system is active (triggers AI learning)")
    with open(cleanup_log, 'r') as f:
        lines = f.readlines()
        if lines:
            last_line = lines[-1].strip()
            if "AI learned" in last_line or "records" in last_line:
                print(f"   Last learning: {last_line[:100]}...")
else:
    print("⚠️  Cleanup log not found (may not have run yet)")

print()

# 6. Summary & Recommendations
print("=" * 70)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 70)
print()

issues = []
if not training_files:
    issues.append("❌ No training data collected")
if not any("ollama" in str(line).lower() for line in [""]):  # Simplified check
    try:
        requests.get("http://localhost:11434/api/tags", timeout=1)
    except:
        issues.append("❌ Local training (Ollama) not available")
if not config_path.exists() or not json.load(open(config_path)).get("api_key"):
    issues.append("⚠️  OpenAI fine-tuning not configured")

if issues:
    print("ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("TO ENABLE TRAINING:")
    print("  1. Data collection: ✅ Already working")
    print("  2. Local training: Install Ollama from https://ollama.ai")
    print("  3. OpenAI fine-tuning: Configure API key in _secure_data/llm_config.json")
else:
    print("✅ All systems operational!")
    print("   Your AI is being trained from bot run data.")

print()
print("=" * 70)

