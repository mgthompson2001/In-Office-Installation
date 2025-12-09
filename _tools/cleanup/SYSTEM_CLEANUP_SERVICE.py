#!/usr/bin/env python3
"""
Standalone System-Wide Passive Cleanup Service
Runs cleanup independently of any bot - can be scheduled or run as a service.
This ensures training data and other files are cleaned up regularly.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
# Get installation root (parent of _tools)
installation_root = Path(__file__).parent.parent.parent
log_dir = installation_root / "_system" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "system_cleanup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_cleanup():
    """Run system-wide passive cleanup."""
    try:
        # Get installation root (parent of _tools)
        installation_dir = Path(__file__).parent.parent.parent
        
        # Import cleanup
        bots_dir = installation_dir / "_bots" / "Billing Department"
        if str(bots_dir) not in sys.path:
            sys.path.insert(0, str(bots_dir))
        
        from init_passive_cleanup import init_passive_cleanup
        
        logger.info("=" * 60)
        logger.info("Starting System-Wide Passive Cleanup")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Run cleanup (this will run in a thread, but we'll wait a bit)
        init_passive_cleanup(installation_dir=installation_dir, logger=logger)
        
        # Wait a moment for cleanup to complete
        time.sleep(5)
        
        logger.info("Cleanup service completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup service: {e}", exc_info=True)

if __name__ == "__main__":
    run_cleanup()

