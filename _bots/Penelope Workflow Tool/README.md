# Penelope Workflow Tool

## Overview
The Penelope Workflow Tool is a flexible, multi-purpose automation bot for Penelope workflows. It provides a modular interface that reuses proven functions from the Remove Counselor bot for reliable Penelope navigation and workflow management.

## Location
**In-Office Installation Folder:**
```
C:\Users\MichaelLocal\Desktop\In-Office Installation\_bots\Penelope Workflow Tool\
```

## Features

### Core Capabilities (Inherited from Remove Counselor Bot)
- ✅ **Iframe-aware element search** - Automatically finds elements across nested iframes
- ✅ **Visibility-safe Chrome launcher** - DPI-stable browser initialization
- ✅ **Workflow drawer navigation** - Open and navigate Penelope workflow tabs
- ✅ **Zoom reset functionality** - Ensures consistent UI rendering
- ✅ **Robust click handlers** - JavaScript fallback for unreliable elements

### Current Features
- Login to Penelope with credentials
- Activity logging for all operations
- Ready to add custom workflow operations

### Planned Features (Coming Soon)
As you specify which functions you need from the Remove Counselor bot, we'll add:
- Custom workflow operations
- CSV/Excel data processing
- Batch operations
- Advanced workflow filtering
- Date range operations
- And more!

## Installation

### Prerequisites
- Python 3.8 or higher
- Google Chrome browser

### Required Python Packages
```bash
pip install selenium webdriver-manager pandas openpyxl
```

## Usage

### Launching from Bot Launcher
1. Open **Bot Launcher** from: `In-Office Installation\_bots\Launcher\bot_launcher.py`
2. Select **"Penelope Workflow Tool"** from the dropdown
3. Click **"Launch Selected Bot"**

### Launching Directly
```bash
python "C:\Users\MichaelLocal\Desktop\In-Office Installation\_bots\Penelope Workflow Tool\penelope_workflow_tool.py"
```

### First Time Setup
1. Enter your Penelope username and password
2. Click "Login to Penelope"
3. Wait for successful login confirmation
4. The bot is now ready for workflow operations

## Architecture

### Modular Design
The bot is designed to import and reuse functions from the Remove Counselor bot:

```python
# Shared functions available:
- start_chrome_visibility_safe()     # Chrome launcher
- _find_element_any_frame()          # Iframe-aware search
- _open_workflow_drawer()            # Open workflow drawer
- _go_tab_by_text()                  # Navigate tabs
- reset_page_zoom_100()              # Zoom reset
```

### Adding New Operations
As you specify which functions you need, we'll add them as modular operations that can be:
- Called individually
- Chained together
- Applied to CSV/Excel data
- Scheduled for batch processing

## File Structure
```
In-Office Installation\_bots\
├── Penelope Workflow Tool/
│   ├── penelope_workflow_tool.py    # Main bot application
│   └── README.md                     # This file
├── Launcher/
│   └── bot_launcher.py              # Updated with this bot
└── (other bots...)
```

## Development Notes

### Next Steps
1. **Tell me which functions** you want from the Remove Counselor bot
2. **Specify the workflow operations** you need
3. **Define the data format** (CSV columns, expected inputs)
4. We'll add each operation incrementally with proper testing

### Design Philosophy
- **Reuse proven code** from Remove Counselor bot
- **Modular operations** that can be mixed and matched
- **Clear logging** for debugging and monitoring
- **User-friendly UI** consistent with other CCMD bots
- **Flexible data input** supporting both CSV and Excel

## Version History

### v1.0 (Current)
- Initial release
- Basic Penelope login
- Core framework established
- Integrated with Bot Launcher
- Ready for custom operations

---

**Status:** Ready for custom operation development
**Location:** In-Office Installation\_bots folder
**Last Updated:** October 2025

