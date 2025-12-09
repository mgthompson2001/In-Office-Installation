#!/usr/bin/env python3
"""
Verification script for AI Task Assistant installation
"""

import sys
from pathlib import Path

def verify_installation():
    """Verify that all AI Task Assistant components are installed correctly"""
    print("=" * 70)
    print("AI Task Assistant - Installation Verification")
    print("=" * 70)
    print()
    
    all_good = True
    
    # Check Python packages
    print("Checking Python packages...")
    print("-" * 70)
    
    try:
        import anthropic
        print(f"[OK] anthropic installed (version: {anthropic.__version__})")
    except ImportError:
        print("[X] anthropic NOT installed")
        all_good = False
    
    try:
        import openai
        print(f"[OK] openai installed (version: {openai.__version__})")
    except ImportError:
        print("[X] openai NOT installed")
        all_good = False
    
    print()
    
    # Check module files
    print("Checking module files...")
    print("-" * 70)
    
    system_dir = Path(__file__).parent
    
    modules = [
        "ai_agent.py",
        "ai_task_assistant.py",
        "ai_task_assistant_gui.py",
        "secure_launcher.py"
    ]
    
    for module in modules:
        module_path = system_dir / module
        if module_path.exists():
            print(f"[OK] {module} found")
        else:
            print(f"[X] {module} NOT found")
            all_good = False
    
    print()
    
    # Check API keys
    print("Checking API key configuration...")
    print("-" * 70)
    
    import os
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    config_path = system_dir / "ai_config.json"
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                if not anthropic_key:
                    anthropic_key = config.get("anthropic_api_key") or config.get("claude_api_key")
                if not openai_key:
                    openai_key = config.get("openai_api_key")
            print("[OK] ai_config.json found")
        except Exception as e:
            print(f"[!] ai_config.json exists but could not be read: {e}")
    else:
        print("[!] ai_config.json not found (API keys can be set via environment variables)")
    
    if anthropic_key:
        print("[OK] Anthropic API Key configured")
    else:
        print("[!] Anthropic API Key not configured (fuzzy matching will be used)")
    
    if openai_key:
        print("[OK] OpenAI API Key configured")
    else:
        print("[!] OpenAI API Key not configured (fuzzy matching will be used)")
    
    print()
    
    # Test imports
    print("Testing module imports...")
    print("-" * 70)
    
    try:
        sys.path.insert(0, str(system_dir))
        from ai_agent import AIAgent
        print("[OK] ai_agent.py imports successfully")
        
        from ai_task_assistant import AITaskAssistant
        print("[OK] ai_task_assistant.py imports successfully")
        
        from ai_task_assistant_gui import open_ai_task_assistant
        print("[OK] ai_task_assistant_gui.py imports successfully")
        
    except ImportError as e:
        print(f"[X] Import error: {e}")
        all_good = False
    except Exception as e:
        print(f"[X] Error: {e}")
        all_good = False
    
    print()
    
    # Summary
    print("=" * 70)
    if all_good:
        print("[OK] All components verified successfully!")
        print("\nThe AI Task Assistant is ready to use.")
        print("Note: API keys are optional - the system works with fuzzy matching.")
    else:
        print("[!] Some components are missing or have errors.")
        print("The AI Task Assistant will still work with fuzzy matching.")
    print("=" * 70)

if __name__ == "__main__":
    verify_installation()

