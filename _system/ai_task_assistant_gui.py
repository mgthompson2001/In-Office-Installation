#!/usr/bin/env python3
"""
AI Task Assistant GUI - Modal Dialog
Provides a user-friendly interface for natural language bot selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import subprocess
import sys
import os
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import AI Task Assistant
try:
    from ai_task_assistant import AITaskAssistant
    TASK_ASSISTANT_AVAILABLE = True
except ImportError:
    TASK_ASSISTANT_AVAILABLE = False
    AITaskAssistant = None

# Import Secure Data Collector
try:
    from secure_data_collector import SecureDataCollector
    DATA_COLLECTOR_AVAILABLE = True
except ImportError:
    DATA_COLLECTOR_AVAILABLE = False
    SecureDataCollector = None


def open_ai_task_assistant(parent_window, installation_dir: Optional[Path] = None):
    """
    Open AI Task Assistant GUI as a modal dialog.
    
    Args:
        parent_window: Parent Tkinter window
        installation_dir: Base installation directory
    """
    if not TASK_ASSISTANT_AVAILABLE:
        messagebox.showerror(
            "Not Available",
            "AI Task Assistant is not available.\n\n"
            "Please ensure all dependencies are installed:\n"
            "- ai_task_assistant.py\n"
            "- ai_agent.py"
        )
        return
    
    if installation_dir is None:
        installation_dir = Path(__file__).parent.parent
    
    # Get data collector from parent if available
    data_collector = None
    if hasattr(parent_window, 'data_collector'):
        data_collector = parent_window.data_collector
    elif DATA_COLLECTOR_AVAILABLE:
        try:
            data_collector = SecureDataCollector(installation_dir)
            if not data_collector.collection_active:
                data_collector.start_collection()
        except Exception:
            pass  # Continue without data collection
    
    # Create AI Task Assistant instance
    assistant = AITaskAssistant(installation_dir, data_collector)
    
    # Create modal dialog
    dialog = tk.Toplevel(parent_window)
    dialog.title("AI Task Assistant")
    dialog.geometry("700x600")
    dialog.transient(parent_window)
    dialog.grab_set()
    
    # Center window
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Main frame
    main_frame = ttk.Frame(dialog, padding="20")
    main_frame.pack(fill="both", expand=True)
    
    # Title
    title_label = tk.Label(
        main_frame,
        text="🤖 AI Task Assistant",
        font=("Arial", 18, "bold"),
        fg="#800000"
    )
    title_label.pack(pady=(0, 10))
    
    # Subtitle
    subtitle_label = tk.Label(
        main_frame,
        text="Tell me what you want to do in natural language",
        font=("Arial", 11),
        fg="#666666"
    )
    subtitle_label.pack(pady=(0, 20))
    
    # Input frame
    input_frame = ttk.Frame(main_frame)
    input_frame.pack(fill="x", pady=(0, 10))
    
    # Prompt entry
    prompt_label = tk.Label(input_frame, text="Your request:", font=("Arial", 10, "bold"))
    prompt_label.pack(anchor="w")
    
    prompt_entry = tk.Text(input_frame, height=3, font=("Arial", 11), wrap="word")
    prompt_entry.pack(fill="x", pady=(5, 0))
    prompt_entry.focus()
    
    # Buttons frame
    buttons_frame = ttk.Frame(main_frame)
    buttons_frame.pack(fill="x", pady=(0, 20))
    
    # Run button
    def run_assistant():
        user_prompt = prompt_entry.get("1.0", tk.END).strip()
        if not user_prompt:
            messagebox.showwarning("Empty Prompt", "Please enter what you want to do.")
            return
        
        # Disable button during processing
        run_btn.config(state="disabled")
        result_text.delete(1.0, tk.END)
        result_text.insert(1.0, "🤔 Thinking... Please wait...")
        dialog.update()
        
        try:
            # Interpret prompt
            result = assistant.interpret_and_select_bot(user_prompt)
            
            # Display result
            result_text.delete(1.0, tk.END)
            
            if result.get("error") == "AI_NOT_CONFIGURED":
                result_text.insert(1.0, 
                    "⚠️ AI not configured\n\n"
                    "To use AI-powered bot selection, please set one of:\n"
                    "- OPENAI_API_KEY environment variable\n"
                    "- ANTHROPIC_API_KEY environment variable\n\n"
                    "Using fuzzy matching instead...\n\n")
            
            if result["bot_name"]:
                result_text.insert(tk.END, f"✅ Selected Bot: {result['bot_name']}\n\n")
                result_text.insert(tk.END, f"Confidence: {result['confidence']:.1%}\n\n")
                result_text.insert(tk.END, f"Reasoning: {result['reasoning']}\n\n")
                
                # Launch button
                launch_btn.config(state="normal", command=lambda: launch_bot(result))
            else:
                result_text.insert(tk.END, 
                    "❌ No bot matched your request.\n\n"
                    f"Reasoning: {result['reasoning']}\n\n"
                    "Available bots:\n")
                for bot_name, bot_info in assistant.get_bot_list().items():
                    result_text.insert(tk.END, f"  • {bot_name}: {bot_info['description']}\n")
        except Exception as e:
            result_text.delete(1.0, tk.END)
            result_text.insert(1.0, f"❌ Error: {str(e)}")
        finally:
            run_btn.config(state="normal")
    
    run_btn = tk.Button(
        buttons_frame,
        text="Run",
        command=run_assistant,
        bg="#800000",
        fg="white",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=5,
        cursor="hand2"
    )
    run_btn.pack(side="left", padx=(0, 10))
    
    # Launch button (initially disabled)
    launch_btn = tk.Button(
        buttons_frame,
        text="Launch Selected Bot",
        command=lambda: None,
        bg="#27ae60",
        fg="white",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=5,
        cursor="hand2",
        state="disabled"
    )
    launch_btn.pack(side="left")
    
    # Result frame
    result_frame = ttk.Frame(main_frame)
    result_frame.pack(fill="both", expand=True)
    
    result_label = tk.Label(result_frame, text="Result:", font=("Arial", 10, "bold"))
    result_label.pack(anchor="w")
    
    result_text = scrolledtext.ScrolledText(
        result_frame,
        height=15,
        font=("Arial", 10),
        wrap="word",
        bg="#f8f8f8"
    )
    result_text.pack(fill="both", expand=True, pady=(5, 0))
    result_text.insert(1.0, "Enter your request above and click 'Run' to get started.")
    
    # Launch bot function
    def launch_bot(result):
        """Launch the selected bot"""
        bot_path = result.get("bot_path")
        if not bot_path or not Path(bot_path).exists():
            messagebox.showerror("Error", f"Bot script not found:\n{bot_path}")
            return
        
        try:
            # Launch bot without console window
            python_exe = sys.executable
            if os.name == 'nt':  # Windows
                subprocess.Popen(
                    [python_exe, bot_path],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    cwd=str(Path(bot_path).parent)
                )
            else:
                subprocess.Popen(
                    [python_exe, bot_path],
                    cwd=str(Path(bot_path).parent)
                )
            
            messagebox.showinfo("Bot Launched", f"Launching {result['bot_name']}...")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch bot:\n{str(e)}")
    
    # Bind Enter key to run
    def on_enter(event):
        run_assistant()
    
    prompt_entry.bind("<Control-Return>", on_enter)
    
    # Status bar
    status_frame = ttk.Frame(main_frame)
    status_frame.pack(fill="x", pady=(10, 0))
    
    status_text = "Ready"
    if not assistant.is_configured():
        status_text = "⚠️ AI not configured - using fuzzy matching"
    
    status_label = tk.Label(
        status_frame,
        text=status_text,
        font=("Arial", 9),
        fg="#666666"
    )
    status_label.pack(anchor="w")
    
    # Focus on entry
    dialog.after(100, lambda: prompt_entry.focus())
    
    # Wait for dialog to close
    dialog.wait_window()

