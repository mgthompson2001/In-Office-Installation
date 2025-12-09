# Data Collection Explained - What Gets Recorded

## ⚠️ Important Clarification

**The Automation Hub does NOT record "every move" like screen recording or keystroke logging.**

Instead, it records **workflow-related events** that happen within the automation system.

---

## ✅ What Gets Recorded (When Automation Hub is Open)

### 1. **Bot Executions** (Automatically Recorded)

**When:** Every time an employee launches a bot from the Automation Hub

**What Gets Recorded:**
- ✅ Which bot was launched (bot name and path)
- ✅ When it was launched (timestamp)
- ✅ Command/parameters used (if any)
- ✅ Files used (if any)
- ✅ Success/failure status
- ✅ Execution time

**Example:**
```
Employee clicks "Medical Records Bot" → Recorded:
- Bot: "Medical Records Bot"
- Timestamp: 2025-11-05T14:30:00
- Parameters: {"client": "ABC Corp", "date_range": "2025-01-01 to 2025-11-05"}
- Files: ["C:\Users\...\data.xlsx"]
- Success: True
- Execution Time: 120.5 seconds
```

---

### 2. **AI Task Assistant Prompts** (Automatically Recorded)

**When:** Every time an employee uses the AI Task Assistant

**What Gets Recorded:**
- ✅ The prompt entered (e.g., "Submit this week's claims")
- ✅ The AI's response
- ✅ Which bot was selected/executed
- ✅ Confidence score
- ✅ Timestamp

**Example:**
```
Employee types: "Submit this week's claims" → Recorded:
- Prompt: "Submit this week's claims"
- Response: {"bot": "claims_bot.py", "action": "submit_claims"}
- Bot Selected: "claims_bot.py"
- Confidence: 0.95
- Timestamp: 2025-11-05T14:35:00
```

---

### 3. **User Activities in Automation Hub** (Automatically Recorded)

**When:** Specific actions within the Automation Hub

**What Gets Recorded:**
- ✅ When Automation Hub is opened/closed
- ✅ When admin sections are accessed
- ✅ When bots are launched
- ✅ System events

**Example:**
```
Employee opens Automation Hub → Recorded:
- Activity Type: "LAUNCHER_OPENED"
- Timestamp: 2025-11-05T14:00:00

Employee clicks "AI Task Assistant" → Recorded:
- Activity Type: "AI_TASK_ASSISTANT_OPENED"
- Timestamp: 2025-11-05T14:05:00
```

---

### 4. **Workflow Patterns** (Automatically Recorded)

**When:** Patterns are identified from bot executions

**What Gets Recorded:**
- ✅ Common workflow sequences
- ✅ Frequency of patterns
- ✅ Success rates
- ✅ Parameter patterns

**Example:**
```
Pattern Identified: "Claims Bot → Report Generator"
- Pattern: ["claims_bot.py", "report_generator.py"]
- Frequency: 45 times
- Success Rate: 98%
- Common Parameters: {"date_range": "weekly"}
```

---

## ❌ What Does NOT Get Recorded

### 1. **Mouse Movements**
- ❌ Mouse movements outside the Automation Hub
- ❌ Mouse movements within the Automation Hub
- ❌ Mouse clicks outside the system

### 2. **Keystrokes**
- ❌ Keystrokes outside the Automation Hub
- ❌ Keystrokes in other applications
- ❌ Passwords or sensitive text (unless entered in bots)

### 3. **Screen Recording**
- ❌ No screenshots or screen recording
- ❌ No video capture
- ❌ No desktop activity monitoring

### 4. **Other Applications**
- ❌ Activities in other software (Word, Excel, etc.)
- ❌ Web browsing
- ❌ Email activity
- ❌ Any activity outside the Automation Hub

---

## 🔍 How Data Collection Works

### When Does Collection Start?

**Collection starts automatically when:**
1. ✅ Automation Hub (Secure Launcher) opens
2. ✅ `SecureDataCollector` is initialized
3. ✅ `start_collection()` is called

**Collection stops when:**
1. ✅ Automation Hub closes
2. ✅ `stop_collection()` is called
3. ✅ System shuts down

---

### What Triggers Recording?

**Recording is event-based, not continuous:**

1. **Bot Execution Event:**
   - Employee clicks bot button → `record_bot_execution()` called → Data recorded

2. **AI Prompt Event:**
   - Employee uses AI Task Assistant → `record_ai_prompt()` called → Data recorded

3. **User Activity Event:**
   - Specific actions in Automation Hub → `record_user_activity()` called → Data recorded

4. **System Event:**
   - System events (startup, shutdown, errors) → `record_system_event()` called → Data recorded

---

## 🔒 Privacy & Security

### What Gets Encrypted?

**All recorded data is encrypted:**
- ✅ Bot execution parameters (encrypted before storage)
- ✅ AI prompts and responses (encrypted)
- ✅ User activity data (encrypted)
- ✅ File paths (encrypted)

### What Gets Anonymized?

**PII (Personally Identifiable Information) is anonymized:**
- ✅ User names → Hashed (SHA-256)
- ✅ File paths → Encrypted
- ✅ Sensitive data → Removed or encrypted

### HIPAA Compliance:

- ✅ **7-year retention**: Data kept for 7 years (HIPAA requirement)
- ✅ **90-day anonymization**: PII anonymized after 90 days
- ✅ **Audit logging**: Complete audit trail
- ✅ **Access control**: Password-protected admin access
- ✅ **Encryption**: Military-grade AES-256 encryption

---

## 📊 Data Collection Summary

### What Gets Recorded:

| Event Type | When | What |
|-----------|------|------|
| **Bot Executions** | When bot launched | Bot name, parameters, files, success, time |
| **AI Prompts** | When AI Task Assistant used | Prompt, response, bot selected, confidence |
| **User Activities** | Specific actions in Hub | Activity type, timestamp |
| **Workflow Patterns** | Patterns identified | Sequence, frequency, success rate |
| **System Events** | System events | Event type, timestamp |

### What Does NOT Get Recorded:

| Item | Status |
|------|--------|
| Mouse movements | ❌ NOT recorded |
| Keystrokes | ❌ NOT recorded |
| Screen recording | ❌ NOT recorded |
| Other applications | ❌ NOT recorded |
| Web browsing | ❌ NOT recorded |

---

## 🎯 Accurate Description

### Correct Statement:

**"When the Automation Hub is open, it passively records workflow-related events:**
- Bot executions (which bots, when, parameters, results)
- AI Task Assistant usage (prompts, responses, bots selected)
- User activities within the Automation Hub
- Workflow patterns identified from usage"

### Incorrect Statement:

**"The Automation Hub records every move"** ❌
- This implies screen recording or keystroke logging
- This is NOT what happens
- Only workflow-related events are recorded

---

## ✅ Summary

### What Actually Happens:

1. **Automation Hub Opens:**
   - Data collection starts automatically
   - Ready to record workflow events

2. **Employee Uses System:**
   - Launches bot → Bot execution recorded
   - Uses AI Task Assistant → AI prompt recorded
   - Performs actions in Hub → User activity recorded

3. **Data Gets Processed:**
   - Encrypted before storage
   - PII anonymized
   - Patterns identified
   - Used for AI training

4. **Automation Hub Closes:**
   - Data collection stops
   - No further recording

### Key Points:

- ✅ **Event-based recording**: Only records specific workflow events
- ✅ **NOT continuous monitoring**: Doesn't record mouse movements or keystrokes
- ✅ **Workflow-focused**: Only records activities within the Automation Hub
- ✅ **HIPAA-compliant**: All data encrypted and anonymized
- ✅ **Transparent**: Employees can see what's being recorded

**The system records workflow intelligence, not personal activity.** 🎯

