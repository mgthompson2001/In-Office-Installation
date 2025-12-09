# Universal Browser Monitoring Bridge

## Overview

The Universal Browser Monitoring Bridge automatically monitors ALL bots in the `_bots` folder, regardless of how they're launched (directly or through Automation Hub).

## How It Works

### 1. **Package-Level Auto-Installation**

When any Python script in the `_bots` folder imports Python modules, the `__init__.py` files automatically install the browser monitoring bridge.

**Files:**
- `_bots/__init__.py` - Auto-installs monitoring when bots are imported
- `_system/__init__.py` - Auto-installs monitoring when system modules are imported

### 2. **Bot Launcher Bridge**

The `bot_launcher_bridge.py` module:
- Patches `webdriver.Chrome()` automatically
- Initializes browser monitoring
- Works transparently (no bot code changes needed)

### 3. **Secure Launcher Integration**

When bots are launched through Automation Hub:
- Monitoring bridge is installed before bot launch
- Ensures browser activity is recorded

## Implementation Details

### Installation Order

1. **Python starts** → `__init__.py` files run
2. **Monitoring bridge installed** → Patches `webdriver.Chrome()`
3. **Bot creates driver** → `driver = webdriver.Chrome()` 
4. **Automatic wrapping** → Driver is wrapped with event listener
5. **Browser activity recorded** → All events captured

### Works For

✅ **Bots launched directly** (e.g., `python bot.py`)
✅ **Bots launched through Automation Hub**
✅ **Bots imported as modules**
✅ **Any Python script in `_bots` folder**

## Testing

To verify monitoring is working:

1. Run any bot (directly or through Automation Hub)
2. Let it navigate and interact with pages
3. Run `analyze_browser_data.py` to see recorded activity

## Files Created

- `_bots/__init__.py` - Auto-installs monitoring for bots
- `_system/__init__.py` - Auto-installs monitoring for system
- `bot_launcher_bridge.py` - Core monitoring bridge
- `sitecustomize.py` - Python-level auto-installation (optional)

## Benefits

- ✅ **Zero bot modifications** - Works automatically
- ✅ **Universal coverage** - All bots monitored
- ✅ **Transparent operation** - No performance impact
- ✅ **HIPAA-compliant** - All data encrypted and anonymized

## Status

**ACTIVE** - Browser monitoring is now enabled for all bots in the `_bots` folder.

