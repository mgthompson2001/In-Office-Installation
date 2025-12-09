#!/usr/bin/env python3
"""
Shared initialization helper for passive data cleanup across ALL bots.

Usage in ANY bot (2 lines of code):
    from init_passive_cleanup import init_passive_cleanup
    init_passive_cleanup()
    
Or with logger:
    from init_passive_cleanup import init_passive_cleanup
    import logging
    logger = logging.getLogger(__name__)
    init_passive_cleanup(logger=logger)
"""

import sys
from pathlib import Path

# Find root AI folder and add to path
_bots_dir = Path(__file__).parent
_installation_root = _bots_dir.parent
_ai_dir = _installation_root / "AI"

# Add AI directory to path so we can import from root AI folder
if _ai_dir.exists() and str(_ai_dir) not in sys.path:
    sys.path.insert(0, str(_ai_dir))

# Import from root AI/monitoring folder
try:
    from monitoring.data_cleanup import init_passive_cleanup as _init_cleanup
except ImportError:
    # Fallback: try importing from _bots if AI folder structure doesn't exist yet
    try:
        from data_cleanup import init_passive_cleanup as _init_cleanup
    except ImportError:
        _init_cleanup = None


def init_passive_cleanup(installation_dir=None, logger=None):
    """Initialize passive cleanup for ANY bot.
    
    This function can be called from ANY bot to enable automatic
    data cleanup across the ENTIRE installation (all bots).
    
    Args:
        installation_dir: Optional path to installation root. Auto-detects if None.
        logger: Optional logger instance for cleanup messages.
    """
    if _init_cleanup is None:
        # Silently fail if cleanup module not available
        if logger:
            logger.debug("Passive cleanup module not available")
        return
    
    # Auto-detect installation directory if not provided
    if installation_dir is None:
        installation_dir = _installation_root
    
    _init_cleanup(installation_dir=installation_dir, logger=logger)

