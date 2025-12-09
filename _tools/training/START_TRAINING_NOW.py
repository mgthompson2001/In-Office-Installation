#!/usr/bin/env python3
"""
IMMEDIATE AI TRAINING - Start training NOW
This will trigger OpenAI fine-tuning immediately with your collected data.
"""

import sys
from pathlib import Path

installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"

# Add to path
if str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

print("=" * 70)
print("STARTING AI TRAINING NOW...")
print("=" * 70)
print()

try:
    # Import OpenAI fine-tuning manager
    from training.openai_fine_tuning import get_fine_tuning_manager
    
    print("1. Initializing fine-tuning manager...")
    manager = get_fine_tuning_manager(installation_dir)
    
    if not manager.is_configured():
        print("❌ ERROR: OpenAI API not configured!")
        print("   Check: _secure_data/llm_config.json")
        sys.exit(1)
    
    print("   ✅ OpenAI API configured")
    print()
    
    print("2. Preparing training data...")
    training_data = manager.prepare_training_data()
    
    if not training_data:
        print("❌ ERROR: Could not prepare training data!")
        print("   This might mean the data extraction needs to be customized")
        print("   for your specific data format.")
        sys.exit(1)
    
    print(f"   ✅ Prepared {len(training_data)} training examples")
    print()
    
    print("3. Uploading training file to OpenAI...")
    file_id = manager.upload_training_file(training_data)
    
    if not file_id:
        print("❌ ERROR: Failed to upload training file!")
        sys.exit(1)
    
    print(f"   ✅ File uploaded: {file_id}")
    print()
    
    print("4. Creating fine-tuning job...")
    job_id = manager.run_fine_tuning_pipeline(
        model="gpt-3.5-turbo",
        suffix="integrity-bots"
    )
    
    if not job_id:
        print("❌ ERROR: Failed to create fine-tuning job!")
        sys.exit(1)
    
    print(f"   ✅ Fine-tuning job created: {job_id}")
    print()
    
    print("=" * 70)
    print("✅ TRAINING STARTED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print(f"Job ID: {job_id}")
    print()
    print("To check status, run:")
    print("  python CHECK_TRAINING_STATUS.py")
    print()
    print("Note: Fine-tuning can take several hours to complete.")
    print("You'll be able to use the fine-tuned model once it's done.")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

