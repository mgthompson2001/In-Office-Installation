#!/usr/bin/env python3
"""
Ensure Ollama is Running
This script ensures Ollama starts automatically when needed.
Can be called by bots or run as a service.
"""

import subprocess
import time
import requests
from pathlib import Path

def ensure_ollama_running():
    """Ensure Ollama service is running, start it if not."""
    try:
        # Check if Ollama is already running
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            return True  # Already running
    except:
        pass  # Not running, continue to start it
    
    # Try to start Ollama
    try:
        # Find Ollama executable
        import shutil
        ollama_path = shutil.which("ollama")
        
        if not ollama_path:
            # Try common installation paths
            common_paths = [
                Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
                Path("C:/Program Files/Ollama/ollama.exe"),
                Path("C:/Program Files (x86)/Ollama/ollama.exe"),
            ]
            
            for path in common_paths:
                if path.exists():
                    ollama_path = str(path)
                    break
        
        if ollama_path:
            # Start Ollama in background
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Wait a moment for it to start
            time.sleep(3)
            
            # Verify it's running
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    return True
            except:
                pass
        
        return False
        
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

if __name__ == "__main__":
    if ensure_ollama_running():
        print("Ollama is running")
    else:
        print("Could not start Ollama - may need manual installation")

