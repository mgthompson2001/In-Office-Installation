#!/usr/bin/env python3
"""
AI Task Assistant GUI - Modal Dialog for Natural Language Task Entry
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from pathlib import Path

# Import the AI Task Assistant
AITaskAssistant = None
import_error = None
try:
    import sys
    import os
    from pathlib import Path
    
    # Add the _system directory to the path
    system_dir = Path(__file__).parent
    if str(system_dir) not in sys.path:
        sys.path.insert(0, str(system_dir))
    
    from ai_task_assistant import AITaskAssistant
except ImportError as e:
    AITaskAssistant = None
    import_error = str(e)


class AITaskAssistantGUI:
    """
    GUI modal dialog for AI Task Assistant.
    Allows users to enter natural language commands and see results.
    """
    
    def __init__(self, parent_window, installation_dir=None):
        """
        Initialize the AI Task Assistant GUI.
        
        Args:
            parent_window: Parent tkinter window
            installation_dir: Base installation directory
        """
        self.parent = parent_window
        self.installation_dir = installation_dir
        
        # Initialize AI Task Assistant
        try:
            if AITaskAssistant is None:
                self.assistant = None
                error_msg = import_error if import_error else "Unknown import error"
                self.error_message = f"AI Task Assistant module not available. Import error: {error_msg}"
            elif installation_dir:
                self.assistant = AITaskAssistant(Path(installation_dir))
            else:
                self.assistant = AITaskAssistant()
        except Exception as e:
            self.assistant = None
            self.error_message = f"Failed to initialize AI Task Assistant: {str(e)}"
        
        # Create modal window
        self.window = tk.Toplevel(parent_window)
        self.window.title("🤖 AI Task Assistant")
        self.window.geometry("700x600")
        self.window.configure(bg="#f0f0f0")
        self.window.transient(parent_window)
        self.window.grab_set()
        
        # Center the window
        self._center_window()
        
        # Build UI
        self._build_ui()
        
        # Focus on input field
        self.input_entry.focus()
    
    def _center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
    
    def _build_ui(self):
        """Build the user interface"""
        # Header
        header_frame = tk.Frame(self.window, bg="#800000", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🤖 AI Task Assistant", 
                              font=("Arial", 20, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True, pady=10)
        
        subtitle_label = tk.Label(header_frame, text="Enter a task in natural language", 
                                 font=("Arial", 11), bg="#800000", fg="#cccccc")
        subtitle_label.pack()
        
        # Main content
        main_frame = tk.Frame(self.window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Instructions
        instructions_frame = tk.Frame(main_frame, bg="#f0f0f0")
        instructions_frame.pack(fill="x", pady=(0, 15))
        
        instructions_text = "Describe what you want to do in natural language.\nExamples: 'Submit this week's insurance claims', 'Generate welcome letters', 'Process consent forms'"
        instructions_label = tk.Label(instructions_frame, text=instructions_text,
                                     font=("Arial", 10), bg="#f0f0f0", 
                                     fg="#666666", justify="left", wraplength=650)
        instructions_label.pack(anchor="w")
        
        # Input frame
        input_frame = tk.LabelFrame(main_frame, text="Task Description", 
                                   font=("Arial", 11, "bold"), bg="#f0f0f0")
        input_frame.pack(fill="x", pady=(0, 15))
        
        self.input_entry = tk.Entry(input_frame, font=("Arial", 11), width=70)
        self.input_entry.pack(fill="x", padx=10, pady=10)
        self.input_entry.bind("<Return>", lambda e: self._run_task())
        
        # Buttons frame
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.pack(fill="x", pady=(0, 15))
        
        run_button = tk.Button(buttons_frame, text="▶ Run Task", 
                              command=self._run_task,
                              bg="#800000", fg="white", font=("Arial", 11, "bold"),
                              padx=20, pady=8, cursor="hand2")
        run_button.pack(side="left", padx=(0, 10))
        
        clear_button = tk.Button(buttons_frame, text="Clear", 
                                command=self._clear_input,
                                bg="#666666", fg="white", font=("Arial", 10),
                                padx=15, pady=8, cursor="hand2")
        clear_button.pack(side="left")
        
        # Output frame
        output_frame = tk.LabelFrame(main_frame, text="Status & Results", 
                                    font=("Arial", 11, "bold"), bg="#f0f0f0")
        output_frame.pack(fill="both", expand=True)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, 
                                                     font=("Consolas", 10), 
                                                     bg="#f8f8f8", wrap="word")
        self.output_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initial message
        if not self.assistant:
            self._log_output("❌ Error: AI Task Assistant not available.\n")
            self._log_output(f"{self.error_message}\n\n")
            self._log_output("Please check that all dependencies are installed.\n")
        else:
            self._log_output("✅ AI Task Assistant ready.\n")
            self._log_output("🚀 Enterprise Features Active:\n")
            self._log_output("   • Workflow Recording\n")
            self._log_output("   • Intelligent Parameter Pre-filling\n")
            self._log_output("   • File Pattern Recognition\n")
            self._log_output("   • Context-Aware Execution\n\n")
            self._log_output("Enter a task description above and click 'Run Task'.\n")
            self._log_output("The system will learn from your usage patterns.\n\n")
        
        # Close button
        close_frame = tk.Frame(main_frame, bg="#f0f0f0")
        close_frame.pack(fill="x", pady=(10, 0))
        
        close_button = tk.Button(close_frame, text="Close", 
                                command=self.window.destroy,
                                bg="#666666", fg="white", font=("Arial", 10),
                                padx=15, pady=5, cursor="hand2")
        close_button.pack(side="right")
    
    def _log_output(self, message: str):
        """Add a message to the output text area"""
        self.output_text.insert(tk.END, message)
        self.output_text.see(tk.END)
        self.window.update_idletasks()
    
    def _clear_input(self):
        """Clear the input field"""
        self.input_entry.delete(0, tk.END)
        self.input_entry.focus()
    
    def _run_task(self):
        """Run the task in a separate thread to avoid blocking UI"""
        user_command = self.input_entry.get().strip()
        
        if not user_command:
            messagebox.showwarning("No Input", "Please enter a task description.")
            return
        
        # Clear previous output or add separator
        if self.output_text.get("1.0", tk.END).strip():
            self._log_output("\n" + "="*70 + "\n\n")
        
        self._log_output(f"📝 User Command: {user_command}\n")
        self._log_output("🤖 Interpreting command...\n\n")
        
        # Disable input and run button during processing
        self.input_entry.config(state="disabled")
        
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=self._process_task_thread, args=(user_command,))
        thread.daemon = True
        thread.start()
    
    def _process_task_thread(self, user_command: str):
        """Process the task in a separate thread"""
        try:
            if not self.assistant:
                self.window.after(0, lambda: self._log_output("❌ AI Task Assistant not available.\n"))
                self.window.after(0, lambda: self.input_entry.config(state="normal"))
                return
            
            # Interpret and execute
            result = self.assistant.process_command(user_command)
            
            # Update UI in main thread
            self.window.after(0, lambda: self._display_result(result))
            
        except Exception as e:
            self.window.after(0, lambda: self._log_output(f"❌ Error: {str(e)}\n"))
            self.window.after(0, lambda: self.input_entry.config(state="normal"))
    
    def _display_result(self, result):
        """Display the result in the output area with smart suggestions"""
        self._log_output("📊 Interpretation Result:\n")
        self._log_output(f"   Bot: {result.get('bot_name', 'Unknown')}\n")
        self._log_output(f"   Confidence: {result.get('confidence', 0.0):.2%}\n")
        
        if result.get("reasoning"):
            self._log_output(f"   Reasoning: {result.get('reasoning')}\n")
        
        # Display smart parameters if available
        if result.get("smart_parameters"):
            self._log_output("\n   🎯 Smart Parameters (Pre-filled):\n")
            for param_name, param_value in result.get("smart_parameters", {}).items():
                self._log_output(f"      • {param_name}: {param_value}\n")
        
        # Display recommended files if available
        if result.get("recommended_files"):
            self._log_output("\n   📁 Recommended Files (from your history):\n")
            for i, file_path in enumerate(result.get("recommended_files", [])[:5], 1):
                file_name = file_path.split("\\")[-1] if "\\" in file_path else file_path.split("/")[-1]
                self._log_output(f"      {i}. {file_name}\n")
        
        # Display context if available
        if result.get("context"):
            context = result.get("context", {})
            if context.get("dates"):
                dates = context["dates"]
                if dates.get("start") or dates.get("end"):
                    self._log_output("\n   📅 Date Context:\n")
                    if dates.get("start"):
                        self._log_output(f"      Start: {dates['start']}\n")
                    if dates.get("end"):
                        self._log_output(f"      End: {dates['end']}\n")
        
        self._log_output("\n")
        
        if result.get("success"):
            if result.get("pid"):
                self._log_output(f"✅ Successfully launched: {result.get('bot_name')}\n")
                self._log_output(f"   Process ID: {result.get('pid')}\n")
                if result.get("execution_time"):
                    self._log_output(f"   Execution time: {result.get('execution_time'):.2f}s\n")
                self._log_output("\n   📝 This execution has been recorded for future learning.\n")
            else:
                self._log_output(f"✅ {result.get('message', 'Task completed')}\n")
        else:
            self._log_output(f"❌ {result.get('message', 'Task failed')}\n")
            
            # Suggest alternatives if confidence is low
            if result.get("confidence", 0) < 0.5:
                self._log_output("\n💡 Tip: Try being more specific about the task.\n")
                self._log_output("   Examples:\n")
                self._log_output("   - 'Submit insurance claims'\n")
                self._log_output("   - 'Process consent forms'\n")
                self._log_output("   - 'Generate welcome letters'\n")
        
        self._log_output("\n" + "="*70 + "\n\n")
        
        # Re-enable input
        self.input_entry.config(state="normal")
        self.input_entry.focus()


def open_ai_task_assistant(parent_window, installation_dir=None):
    """
    Convenience function to open the AI Task Assistant GUI.
    
    Args:
        parent_window: Parent tkinter window
        installation_dir: Base installation directory (optional)
    
    Returns:
        AITaskAssistantGUI instance
    """
    return AITaskAssistantGUI(parent_window, installation_dir)


if __name__ == "__main__":
    # Standalone testing
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    gui = AITaskAssistantGUI(root)
    root.mainloop()

