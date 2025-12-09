#!/usr/bin/env python3
"""
Cancel OpenAI Fine-Tuning Job
This will cancel the current fine-tuning job to avoid API charges.
"""

import sys
from pathlib import Path

installation_dir = Path(__file__).parent.parent.parent
ai_dir = installation_dir / "AI"

if str(ai_dir) not in sys.path:
    sys.path.insert(0, str(ai_dir))

print("=" * 70)
print("CANCELING OPENAI FINE-TUNING JOB")
print("=" * 70)
print()

try:
    from training.openai_fine_tuning import get_fine_tuning_manager
    
    manager = get_fine_tuning_manager(installation_dir)
    
    if not manager.is_configured():
        print("OpenAI not configured - nothing to cancel")
        sys.exit(0)
    
    # Get latest job
    metadata_file = manager.models_dir / "fine_tuning_metadata.json"
    if metadata_file.exists():
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            jobs = metadata.get("jobs", [])
            
            if jobs:
                latest_job = max(jobs, key=lambda j: j.get("created_at", ""))
                job_id = latest_job.get("job_id")
                
                print(f"Found job: {job_id}")
                print(f"Status: {latest_job.get('status', 'Unknown')}")
                print()
                
                # Check current status
                status = manager.check_job_status(job_id)
                if status:
                    current_status = status.get('status', 'unknown')
                    print(f"Current status: {current_status}")
                    
                    if current_status in ['validating_files', 'queued', 'running']:
                        print()
                        print("⚠️  WARNING: Job is still active!")
                        print("   OpenAI may charge for work already done.")
                        print("   Canceling now will stop further charges.")
                        print()
                        
                        try:
                            # Try to cancel (OpenAI API may not support cancellation)
                            response = manager.client.fine_tuning.jobs.cancel(job_id)
                            print(f"✅ Job cancellation requested")
                            print(f"   Note: OpenAI may still charge for work completed")
                        except Exception as e:
                            print(f"⚠️  Could not cancel job: {e}")
                            print(f"   You may need to cancel manually in OpenAI dashboard")
                            print(f"   Job ID: {job_id}")
                    elif current_status == 'succeeded':
                        print()
                        print("⚠️  Job already completed!")
                        print("   You will be charged for this training.")
                        print(f"   Fine-tuned model: {status.get('fine_tuned_model', 'Unknown')}")
                    elif current_status in ['failed', 'canceled']:
                        print()
                        print("✅ Job is already stopped")
                else:
                    print("Could not retrieve job status")
            else:
                print("No jobs found to cancel")
    else:
        print("No training metadata found - no jobs to cancel")
    
    print()
    print("=" * 70)
    print("OPENAI FINE-TUNING HAS BEEN DISABLED IN CLEANUP SYSTEM")
    print("=" * 70)
    print()
    print("Future cleanup runs will use Ollama (free, local) instead.")
    print("To re-enable OpenAI fine-tuning later, edit:")
    print("  AI/monitoring/data_cleanup.py")
    print("  (Uncomment the OpenAI fine-tuning section)")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

