#!/usr/bin/env python3
"""
Verify Full System Monitoring Dependencies
Checks that all dependencies are installed and working.
"""

import sys
from pathlib import Path

print("="*60)
print("Full System Monitoring - Dependency Verification")
print("="*60)
print()

# Check core dependencies
print("Checking core dependencies...")
dependencies = {
    "mss": "Screen capture",
    "pynput": "Keyboard/mouse monitoring",
    "psutil": "Process monitoring",
    "watchdog": "File system monitoring",
    "PIL": "Image processing",
    "cryptography": "Encryption",
    "opencv-python": "Computer vision (optional)",
    "numpy": "Numerical computing (optional)"
}

all_ok = True
for module_name, description in dependencies.items():
    try:
        if module_name == "PIL":
            import PIL
            status = "✓"
        elif module_name == "opencv-python":
            import cv2
            status = "✓"
        else:
            __import__(module_name)
            status = "✓"
        print(f"  [OK] {module_name:20} - {description}")
    except ImportError:
        print(f"  [FAIL] {module_name:20} - {description} (NOT INSTALLED)")
        all_ok = False

print()

# Check advanced AI dependencies
print("Checking advanced AI dependencies...")
ai_dependencies = {
    "transformers": "HuggingFace Transformers (AI models)",
    "torch": "PyTorch (deep learning)",
    "accelerate": "Model optimization",
    "langchain": "LangChain (AI orchestration)",
    "langchain_community": "LangChain community",
    "ollama": "Ollama (local LLM)",
    "pandas": "Data processing",
    "scikit-learn": "Machine learning"
}

for module_name, description in ai_dependencies.items():
    try:
        # scikit-learn imports as sklearn
        import_name = "sklearn" if module_name == "scikit-learn" else module_name
        __import__(import_name)
        print(f"  [OK] {module_name:20} - {description}")
    except ImportError:
        print(f"  [FAIL] {module_name:20} - {description} (NOT INSTALLED)")
        all_ok = False

print()

# Check full_system_monitor module
print("Checking full_system_monitor module...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from full_system_monitor import FullSystemMonitor, MSS_AVAILABLE, INPUT_MONITORING_AVAILABLE, PROCESS_MONITORING_AVAILABLE, FILESYSTEM_MONITORING_AVAILABLE
    
    print(f"  [OK] FullSystemMonitor imported successfully")
    print(f"  [OK] MSS_AVAILABLE: {MSS_AVAILABLE}")
    print(f"  [OK] INPUT_MONITORING_AVAILABLE: {INPUT_MONITORING_AVAILABLE}")
    print(f"  [OK] PROCESS_MONITORING_AVAILABLE: {PROCESS_MONITORING_AVAILABLE}")
    print(f"  [OK] FILESYSTEM_MONITORING_AVAILABLE: {FILESYSTEM_MONITORING_AVAILABLE}")
    
    if MSS_AVAILABLE and INPUT_MONITORING_AVAILABLE and PROCESS_MONITORING_AVAILABLE and FILESYSTEM_MONITORING_AVAILABLE:
        print()
        print("="*60)
        print("[OK] ALL DEPENDENCIES VERIFIED - SYSTEM READY!")
        print("="*60)
    else:
        print()
        print("="*60)
        print("[WARN] SOME DEPENDENCIES MISSING - CHECK ABOVE")
        print("="*60)
        all_ok = False
        
except Exception as e:
    print(f"  [FAIL] Error importing full_system_monitor: {e}")
    all_ok = False

print()

# Check AI training integration
print("Checking AI training integration...")
try:
    from ai_training_integration import AITrainingIntegration
    print("  [OK] AI training integration available")
except ImportError as e:
    print(f"  [WARN] AI training integration not available: {e}")

print()

if all_ok:
    print("="*60)
    print("[OK] ALL SYSTEMS READY FOR FULL SYSTEM MONITORING!")
    print("="*60)
    print()
    print("You can now:")
    print("  1. Launch full_monitoring_gui.py")
    print("  2. Start monitoring your activities")
    print("  3. Train AI models from your recorded data")
    print()
else:
    print("="*60)
    print("[WARN] SOME DEPENDENCIES MISSING")
    print("="*60)
    print()
    print("Please install missing dependencies:")
    print("  python -m pip install mss pynput psutil watchdog")
    print("  python -m pip install transformers torch accelerate langchain ollama")
    print()

