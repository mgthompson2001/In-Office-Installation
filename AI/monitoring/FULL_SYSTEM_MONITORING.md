# Full System Monitoring - Personal Use

## ⚠️ Important Notice

**This system is for PERSONAL USE ONLY with EXPLICIT CONSENT.**

Full system monitoring records:
- Screen activity (screenshots)
- Keyboard input (all keystrokes)
- Mouse activity (movements, clicks, scrolls)
- Application usage (which apps are used)
- File system activity (file access, changes)

**All data is encrypted and stored locally. No data is transmitted externally.**

---

## 🚀 Quick Start

### 1. Install Dependencies

Run the installation script:
```batch
install_full_monitoring.bat
```

This will install:
- `mss` - Screen capture
- `pynput` - Keyboard/mouse monitoring
- `psutil` - Process monitoring
- `watchdog` - File system monitoring

### 2. Launch Full System Monitor

Run the launcher:
```batch
launch_full_monitoring.bat
```

Or directly:
```batch
python full_monitoring_gui.py
```

### 3. Start Monitoring

1. **Configure Options:**
   - Check/uncheck what you want to record:
     - ✅ Record Screen
     - ✅ Record Keyboard
     - ✅ Record Mouse
     - ✅ Record Applications
     - ✅ Record Files

2. **Give Consent:**
   - Click "Start Monitoring"
   - Confirm your explicit consent in the dialog

3. **Monitor Status:**
   - Watch the status panel for real-time metrics
   - See screens, keystrokes, mouse events, app switches, and file events

4. **Stop Monitoring:**
   - Click "Stop Monitoring" when done
   - All data will be flushed to the database

---

## 📊 What Gets Recorded

### Screen Recordings
- Screenshots at configurable intervals (default: 1 FPS)
- Compressed JPEG format (quality: 70%)
- Active window title and application name
- Timestamp for each screenshot

### Keyboard Input
- All keystrokes (including special keys)
- Active application and window title
- Timestamp for each keystroke
- **Note:** Passwords and sensitive data are recorded - use with caution!

### Mouse Activity
- Mouse movements (x, y coordinates)
- Mouse clicks (left, right, middle)
- Mouse scrolls (scroll delta)
- Active application and window title
- Timestamp for each event

### Application Usage
- Application switches (when you change apps)
- Active application name
- Window title
- Duration in each application
- Timestamp for each switch

### File System Activity
- File creation
- File modification
- File deletion
- File moves
- File path, size, and type
- Active application that accessed the file
- Timestamp for each event

---

## 🔒 Security & Privacy

### Encryption
- All data is encrypted using AES-256 encryption
- Encryption key is stored locally (machine-specific)
- Data is encrypted at rest and in transit (local only)

### Storage
- All data is stored locally in:
  ```
  In-Office Installation\_secure_data\full_monitoring\
  ```
- Database: `full_monitoring.db`
- Logs: `monitoring.log`
- Encryption key: `.encryption_key` (hidden file)

### Privacy
- **No external transmission:** All data stays on your computer
- **Local-only:** Data is never sent to external servers
- **Encrypted:** All sensitive data is encrypted
- **HIPAA-compliant:** Follows healthcare privacy standards

---

## 📈 Data Analysis

### Analyze Recorded Sessions

Use the AI Activity Analyzer to process recorded data:

```python
from ai_activity_analyzer import AIActivityAnalyzer

analyzer = AIActivityAnalyzer()
training_data = analyzer.generate_training_data()
```

This will:
- Extract patterns from recorded activities
- Identify sequences and workflows
- Generate training data for AI models
- Save training data to `_ai_models/training_data.json`

### View Session Data

```python
from full_system_monitor import get_full_monitor

monitor = get_full_monitor()
session_data = monitor.get_session_data("session_20250101_120000")
print(session_data)
```

---

## 🎯 AI Training

### Generate Training Data

1. **Record your activities:**
   - Start monitoring
   - Use your computer normally
   - Stop monitoring when done

2. **Analyze sessions:**
   ```python
   from ai_activity_analyzer import AIActivityAnalyzer
   
   analyzer = AIActivityAnalyzer()
   training_data = analyzer.generate_training_data()
   ```

3. **Train AI model:**
   - Use the training data to train your AI model
   - The model will learn your patterns and behaviors
   - Eventually, it can replicate your functions and movements

### Training Data Format

```json
{
  "session_id": "session_20250101_120000",
  "patterns": [
    {
      "pattern_type": "app_usage",
      "app": "chrome.exe",
      "window": "Google - Chrome",
      "frequency": 45
    }
  ],
  "sequences": [
    {
      "sequence": [...],
      "duration": 120.5,
      "activities": 15
    }
  ],
  "workflows": [
    {
      "workflow_type": "standard_workflow",
      "sequence": [...],
      "start_time": "2025-01-01T12:00:00",
      "end_time": "2025-01-01T12:02:00"
    }
  ]
}
```

---

## ⚙️ Configuration

### Screen Recording Settings

```python
monitor = FullSystemMonitor()
monitor.screen_fps = 1  # Frames per second (default: 1)
monitor.screen_quality = 0.7  # JPEG quality 0-1 (default: 0.7)
```

### Monitoring Options

```python
monitor = FullSystemMonitor(
    record_screen=True,      # Record screen
    record_keyboard=True,    # Record keyboard
    record_mouse=True,       # Record mouse
    record_apps=True,        # Record applications
    record_files=True        # Record files
)
```

---

## 📝 Usage Examples

### Basic Usage

```python
from full_system_monitor import start_full_monitoring, stop_full_monitoring

# Start monitoring
monitor = start_full_monitoring(user_consent=True)

# ... use your computer ...

# Stop monitoring
stop_full_monitoring()
```

### Custom Configuration

```python
from full_system_monitor import FullSystemMonitor

monitor = FullSystemMonitor(
    user_consent=True,
    record_screen=True,
    record_keyboard=True,
    record_mouse=True,
    record_apps=True,
    record_files=True
)

monitor.screen_fps = 2  # 2 FPS
monitor.screen_quality = 0.8  # 80% quality

monitor.start_monitoring()

# ... use your computer ...

monitor.stop_monitoring()
```

### Get Metrics

```python
metrics = monitor.get_metrics()
print(f"Screens recorded: {metrics['screens_recorded']}")
print(f"Keystrokes recorded: {metrics['keystrokes_recorded']}")
print(f"Mouse events recorded: {metrics['mouse_events_recorded']}")
```

---

## 🛠️ Troubleshooting

### Monitoring Not Starting

**Issue:** "Full system monitor not available"

**Solution:**
1. Install dependencies:
   ```batch
   install_full_monitoring.bat
   ```

2. Check if all packages are installed:
   ```python
   import mss
   import pynput
   import psutil
   import watchdog
   ```

### Keyboard/Mouse Not Recording

**Issue:** Keyboard or mouse events not being recorded

**Solution:**
1. Check if `pynput` is installed:
   ```batch
   pip install pynput>=1.7.6
   ```

2. On Windows, you may need to run as Administrator for keyboard/mouse hooks

### Screen Recording Not Working

**Issue:** Screenshots not being captured

**Solution:**
1. Check if `mss` is installed:
   ```batch
   pip install mss>=9.0.0
   ```

2. Check if `Pillow` is installed:
   ```batch
   pip install Pillow>=10.0.0
   ```

### Application Detection Not Working

**Issue:** Active application not being detected

**Solution:**
1. Check if `psutil` is installed:
   ```batch
   pip install psutil>=5.9.0
   ```

2. Check if `pywin32` is installed (Windows):
   ```batch
   pip install pywin32>=306
   ```

### File System Monitoring Not Working

**Issue:** File events not being recorded

**Solution:**
1. Check if `watchdog` is installed:
   ```batch
   pip install watchdog>=3.0.0
   ```

2. Check if monitored directories exist:
   - Desktop
   - Documents
   - Downloads
   - Installation directory

---

## 📋 Requirements

- **Python 3.8+**
- **Windows 10/11** (primary support)
- **Administrator privileges** (recommended for keyboard/mouse hooks)

### Required Packages

- `mss>=9.0.0` - Screen capture
- `pynput>=1.7.6` - Keyboard/mouse monitoring
- `psutil>=5.9.0` - Process monitoring
- `watchdog>=3.0.0` - File system monitoring
- `cryptography>=41.0.0` - Encryption
- `Pillow>=10.0.0` - Image processing
- `pywin32>=306` - Windows window detection (Windows only)

---

## ⚠️ Legal & Ethical Considerations

### Personal Use Only

**This system is designed for PERSONAL USE with EXPLICIT CONSENT.**

### Important Notes

1. **Consent Required:**
   - You must give explicit consent before monitoring starts
   - The system will not start without consent

2. **Privacy:**
   - All data is stored locally
   - No data is transmitted externally
   - All data is encrypted

3. **Legal:**
   - Use only on your own computer
   - Do not use on others' computers without explicit consent
   - Follow all applicable privacy laws

4. **Security:**
   - Passwords and sensitive data are recorded
   - Use with caution
   - Keep encryption key secure

---

## 🎓 Future Enhancements

### Planned Features

- [ ] AI model training pipeline
- [ ] Pattern recognition and prediction
- [ ] Workflow automation based on patterns
- [ ] Real-time AI assistance
- [ ] Advanced analytics dashboard
- [ ] Export/import training data
- [ ] Model fine-tuning interface

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `_secure_data/full_monitoring/monitoring.log`
3. Check the database for recorded data

---

## ✅ Summary

**Full System Monitoring** is a comprehensive system for recording all computer activity for personal use with explicit consent. It records screen, keyboard, mouse, applications, and files, encrypts all data, and stores it locally for AI training purposes.

**Key Features:**
- ✅ Complete activity recording
- ✅ Encrypted local storage
- ✅ HIPAA-compliant
- ✅ AI training data generation
- ✅ Pattern extraction and analysis
- ✅ Personal use with explicit consent

**Use responsibly and ethically!** 🎯

