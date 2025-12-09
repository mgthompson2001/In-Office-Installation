#!/usr/bin/env python3
"""
Start Context Understanding Engine
Automatically processes recent sessions to build understanding
"""

import sys
from pathlib import Path
import threading
import time
from datetime import datetime, timedelta
import logging

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_understanding_engine import ContextUnderstandingEngine


def start_context_understanding(installation_dir: Path = None, 
                               check_interval: int = 300,
                               auto_start: bool = True):
    """
    Start automatic context understanding processing
    
    Args:
        installation_dir: Base installation directory
        check_interval: How often to check for new sessions (seconds)
        auto_start: Whether to start processing immediately
    """
    if installation_dir is None:
        installation_dir = Path(__file__).parent.parent.parent
    
    engine = ContextUnderstandingEngine(installation_dir)
    
    if auto_start:
        # Process recent sessions immediately
        print("Processing recent sessions...")
        result = engine.process_recent_sessions(hours=24)
        print(f"Processed {result['processed']} sessions")
    
    # Start background processing
    def background_processing():
        while True:
            try:
                time.sleep(check_interval)
                result = engine.process_recent_sessions(hours=24)
                if result['processed'] > 0:
                    print(f"[{datetime.now()}] Processed {result['processed']} new sessions")
            except Exception as e:
                print(f"Error in background processing: {e}")
                time.sleep(60)  # Wait before retrying
    
    thread = threading.Thread(target=background_processing, daemon=True)
    thread.start()
    
    print(f"Context Understanding Engine started (checking every {check_interval} seconds)")
    
    return engine


if __name__ == "__main__":
    engine = start_context_understanding()
    
    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nStopping Context Understanding Engine...")

