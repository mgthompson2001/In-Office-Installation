#!/usr/bin/env python3
"""
Check AI Training Status
Shows the current status of your fine-tuning job.
"""

import sys
from pathlib import Path

installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"

if str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

try:
    from training.openai_fine_tuning import get_fine_tuning_manager
    
    manager = get_fine_tuning_manager(installation_dir)
    
    # Check metadata for job IDs
    metadata_file = manager.models_dir / "fine_tuning_metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            import json
            metadata = json.load(f)
            jobs = metadata.get("jobs", [])
            
            if jobs:
                print("=" * 70)
                print("FINE-TUNING JOB STATUS")
                print("=" * 70)
                print()
                
                for job in jobs[-5:]:  # Show last 5 jobs
                    job_id = job.get("job_id")
                    status = manager.check_job_status(job_id)
                    
                    if status:
                        print(f"Job ID: {job_id}")
                        print(f"Status: {status['status']}")
                        if status.get('fine_tuned_model'):
                            print(f"✅ Model Ready: {status['fine_tuned_model']}")
                        print(f"Created: {status.get('created_at', 'Unknown')}")
                        if status.get('finished_at'):
                            print(f"Finished: {status['finished_at']}")
                        print()
                    else:
                        print(f"Job ID: {job_id}")
                        print(f"Status: {job.get('status', 'Unknown')}")
                        print()
            else:
                print("No fine-tuning jobs found.")
    else:
        print("No training metadata found. Training may not have started yet.")
        
except Exception as e:
    print(f"Error checking status: {e}")
    import traceback
    traceback.print_exc()

