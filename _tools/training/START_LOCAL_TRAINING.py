#!/usr/bin/env python3
"""
Start Local AI Training with Ollama (FREE)
This trains your AI locally using Ollama - no API charges!
"""

import sys
from pathlib import Path

installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"

if str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

print("=" * 70)
print("STARTING LOCAL AI TRAINING (OLLAMA - FREE)")
print("=" * 70)
print()

try:
    from training.local_ai_trainer import LocalAITrainer
    
    print("1. Initializing local trainer...")
    trainer = LocalAITrainer(installation_dir, model_type="ollama")
    
    if not trainer.model:
        print("❌ Ollama is not running!")
        print()
        print("To start Ollama:")
        print("  1. Install from: https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Or run: SETUP_OLLAMA_TRAINING.bat")
        sys.exit(1)
    
    print("   ✅ Ollama is running")
    print()
    
    print("2. Training on collected bot data...")
    trainer.train_on_collected_data()
    
    print()
    print("=" * 70)
    print("✅ LOCAL TRAINING COMPLETED!")
    print("=" * 70)
    print()
    print("Your AI has been trained on your bot run data.")
    print("Training data is stored in: AI/models/")
    print()
    print("The AI will use these patterns to better understand your workflows.")
    print("This training is FREE and runs locally - no API charges!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

