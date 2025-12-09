# AI Task Assistant - Documentation

## Overview

The AI Task Assistant is an intelligent orchestrator that allows users to interact with the Automation Hub using natural language commands. Instead of manually selecting bots from a dropdown, users can describe what they want to do, and the AI will automatically find and launch the appropriate bot.

## Features

- **Natural Language Processing**: Describe tasks in plain English
- **Automatic Bot Routing**: Automatically finds and launches the correct bot
- **LLM Support**: Works with Claude (Anthropic) and OpenAI GPT models for better interpretation
- **Fuzzy Matching Fallback**: Works without API keys using keyword matching
- **Comprehensive Logging**: All commands and actions are logged to `ai_assistant_log.txt`

## Installation

### 1. Install Python Packages

The required packages are already included in `requirements.txt`:

```bash
pip install anthropic>=0.18.0 openai>=1.0.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Verify Installation

Run the verification script:

```bash
python _system/verify_ai_installation.py
```

### 3. Configure API Keys (Optional)

For better LLM support, you can configure API keys:

**Option A: Using the Setup Script**

```bash
python _system/setup_ai_api_keys.py
```

**Option B: Environment Variables**

Set these environment variables in Windows:

- `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY` - For Claude API
- `OPENAI_API_KEY` - For OpenAI API

**Option C: Config File**

Create `_system/ai_config.json`:

```json
{
  "anthropic_api_key": "your-key-here",
  "openai_api_key": "your-key-here"
}
```

**Note**: API keys are optional. The system works with fuzzy matching without them.

## Usage

### Using the GUI

1. Launch the Automation Hub (`secure_launcher.py`)
2. Click the **"🤖 AI Task Assistant"** button at the top
3. Enter your task in natural language, for example:
   - "Submit this week's insurance claims"
   - "Process consent forms"
   - "Generate welcome letters"
   - "Create referral forms"
4. Click **"Run Task"**
5. The AI will interpret your command and launch the appropriate bot

### Example Commands

- "Submit insurance claims for Medisoft"
- "Process consent forms in Penelope"
- "Generate welcome letters for new clients"
- "Create referral forms from CSV"
- "Assign counselors to clients"
- "Remove counselor assignments"
- "Process therapy notes refiling"

## Architecture

### Components

1. **ai_agent.py** - LLM interface for interpreting commands
   - Supports Claude (Anthropic) and OpenAI APIs
   - Falls back to fuzzy keyword matching
   - Extracts parameters from user commands

2. **ai_task_assistant.py** - Main orchestrator
   - Maps bot identifiers to actual bot file paths
   - Routes commands to appropriate bots
   - Handles bot execution via subprocess
   - Logs all activities

3. **ai_task_assistant_gui.py** - GUI modal dialog
   - Natural language input interface
   - Displays interpretation results
   - Shows execution status

4. **secure_launcher.py** - Main launcher (modified)
   - Added AI Task Assistant button at the top
   - Integrated AI Task Assistant modal

### Bot Mapping

The system uses a `BOT_MAP` dictionary that maps bot identifiers to actual bot file paths:

- `medical_records` → Medical Records Bot
- `consent_form` → Consent Form Bot
- `welcome_letter` → Welcome Letter Bot
- `medisoft_billing` → Medisoft Billing Bot
- `tn_refiling` → TN Refiling Bot
- `referral` → Referral Form Bot
- `counselor_assignment` → Counselor Assignment Bot
- `remove_counselor` → Remove Counselor Bot
- `penelope_workflow` → Penelope Workflow Tool

## Configuration

### Model Selection

By default, the AI Agent uses:
- Model: `claude-sonnet` (for Anthropic)
- Model: `gpt-5-mini` (for OpenAI)
- Temperature: `0.3` (lower = more deterministic)

You can customize these in `ai_agent.py`:

```python
ai_agent = AIAgent(model="claude-sonnet", temperature=0.3)
```

### Available Models

**Anthropic:**
- `claude-sonnet` - Claude Sonnet 3.5 (default)
- `claude-opus` - Claude Opus
- `claude-haiku` - Claude Haiku (fastest)

**OpenAI:**
- `gpt-5-mini` - GPT-5 Mini (default)
- `gpt-5-nano` - GPT-5 Nano
- `gpt-3.5-turbo` - GPT-3.5 Turbo (faster, cheaper)

## Logging

All commands and actions are logged to:
- `_system/ai_assistant_log.txt`

Log entries include:
- Timestamp
- User command
- Interpretation result
- Bot executed
- Success/failure status

## Troubleshooting

### AI Task Assistant Not Available

If the AI Task Assistant button doesn't appear or shows an error:

1. Verify installation:
   ```bash
   python _system/verify_ai_installation.py
   ```

2. Check that all module files exist:
   - `ai_agent.py`
   - `ai_task_assistant.py`
   - `ai_task_assistant_gui.py`

3. Check Python imports:
   ```python
   from ai_task_assistant_gui import open_ai_task_assistant
   ```

### API Key Issues

If LLM interpretation isn't working:

1. Check API keys are set:
   ```bash
   echo %ANTHROPIC_API_KEY%
   echo %OPENAI_API_KEY%
   ```

2. Verify config file exists and is readable:
   - `_system/ai_config.json`

3. The system will fall back to fuzzy matching if API keys are missing

### Bot Not Found

If a command doesn't find the right bot:

1. Check the `BOT_MAP` in `ai_task_assistant.py`
2. Verify the bot file path exists
3. Try using more specific keywords in your command
4. Check the log file for error messages

## Extending the System

### Adding New Bots

To add a new bot to the system:

1. Add entry to `BOT_MAP` in `ai_task_assistant.py`:

```python
"new_bot_id": {
    "path": str(bots_dir / "New Bot" / "new_bot.py"),
    "name": "New Bot Name",
    "keywords": ["keyword1", "keyword2"]
}
```

2. Update the LLM system prompt in `ai_agent.py` to include the new bot identifier

3. Test the new bot with natural language commands

### Customizing Interpretation

To customize how commands are interpreted:

1. Modify `_fuzzy_match()` in `ai_agent.py` for keyword matching
2. Modify the system prompt in `_claude_interpret()` or `_openai_interpret()`
3. Adjust `_extract_params()` for parameter extraction

## Security Notes

- API keys are stored in environment variables or config file
- Config file is stored in `_system/` directory (not in git if using version control)
- All bot executions are logged for audit purposes
- The system only executes existing bots - no arbitrary code execution

## Support

For issues or questions:
1. Check the log file: `_system/ai_assistant_log.txt`
2. Run verification: `python _system/verify_ai_installation.py`
3. Check that all dependencies are installed
4. Verify bot file paths are correct

---

**Last Updated**: January 2025
**Version**: 1.0

