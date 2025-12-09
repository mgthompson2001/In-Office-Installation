# File Organization Guide

## Root Directory

The root directory now contains only:
- `INSTALL_BOTS.bat` - Main installation script
- `START_SYSTEM_CLEANUP.bat` - Manual cleanup trigger

## Organized Folders

### `_tools/` - Utility Scripts and Tools

#### `_tools/training/` - AI Training Scripts
- `CANCEL_OPENAI_TRAINING.py` - Cancel OpenAI fine-tuning jobs
- `CHECK_AI_TRAINING_STATUS.py` - Check training status
- `CHECK_TRAINING_STATUS.py` - Alternative training status checker
- `START_LOCAL_TRAINING.py` - Start local Ollama training
- `START_TRAINING_NOW.py` - Immediate training trigger
- `SETUP_OLLAMA_TRAINING.bat` - Setup Ollama for training
- `SETUP_OLLAMA_AUTOSTART.bat` - Configure Ollama auto-start
- `ENSURE_OLLAMA_RUNNING.py` - Ensure Ollama is running

#### `_tools/cleanup/` - Cleanup Scripts
- `SYSTEM_CLEANUP_SERVICE.py` - Standalone cleanup service
- `SCHEDULE_CLEANUP.bat` - Schedule cleanup via Task Scheduler

#### `_tools/config/` - Configuration Scripts
- `CONFIGURE_EMPLOYEE_MODE.py` - Configure employee/central mode
- `CHECK_CONFIG_STATUS.py` - Check system configuration
- `VERIFY_DATA_COLLECTION.py` - Verify data collection setup
- `VERIFY_TRAINING_FLOW.py` - Verify training flow

### `_docs/` - Documentation
- `HUB_AND_SPOKE_SYSTEM.md` - Hub-and-spoke architecture guide
- `TRAINING_SYSTEM_STATUS.md` - Training system status documentation
- `FILE_ORGANIZATION.md` - This file

## Usage

### Running Training Scripts
```batch
python _tools\training\CHECK_AI_TRAINING_STATUS.py
python _tools\training\START_LOCAL_TRAINING.py
```

### Running Configuration Scripts
```batch
python _tools\config\CONFIGURE_EMPLOYEE_MODE.py
python _tools\config\CHECK_CONFIG_STATUS.py
```

### Running Cleanup
```batch
START_SYSTEM_CLEANUP.bat
python _tools\cleanup\SYSTEM_CLEANUP_SERVICE.py
_tools\cleanup\SCHEDULE_CLEANUP.bat
```

## Path Updates

All scripts have been updated to use correct relative paths. The installation root is automatically detected from script locations.

