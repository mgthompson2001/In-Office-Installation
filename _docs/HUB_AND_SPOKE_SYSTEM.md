# Hub-and-Spoke Data Collection & Training System

## Overview

This system implements a **hub-and-spoke architecture** for AI training:

- **Employee Computers (Spokes)**: Collect data, transfer to central location
- **Central Computer (Hub)**: Receives data, runs training, manages AI models

## How It Works

### Employee Computers

1. **Data Collection**: Bots collect training data as normal (browser activity, bot logs, coordinates, screenshots)
2. **Data Transfer**: On a timer (default: 24 hours), data is transferred to the central location
3. **No Training**: Employee computers do NOT run AI training (no Ollama needed)
4. **Minimal Cleanup**: Only cleans up very old files, preserves data for transfer

### Central Computer

1. **Data Collection**: Collects data from employee computers via central data folder
2. **Data Processing**: Processes all collected data for AI training
3. **AI Training**: Runs Ollama training on all collected data
4. **Normal Cleanup**: Standard cleanup and compression of training data

## Configuration

### Setting Up Employee Computers

When employees run `INSTALL_BOTS.bat`, they will be prompted to:

1. Enter the **central data folder path** (network share or shared folder)
2. Set the **transfer interval** (how often to transfer data, default: 24 hours)

Example central data paths:
- Network share: `\\server\shared\bot_data`
- Local shared folder: `C:\Shared\BotData`
- OneDrive/SharePoint: `C:\Users\Admin\OneDrive\BotData`

### Setting Up Central Computer

1. Run `_tools\config\CONFIGURE_EMPLOYEE_MODE.py`
2. Choose option 2 (Central Computer)
3. Optionally set the central data folder path (where employee data arrives)

## Files Created

### Configuration Files

- `AI/monitoring/system_config.json` - Stores computer mode and settings
  ```json
  {
    "mode": "employee" or "central",
    "central_data_path": "path/to/central/folder",
    "transfer_interval_hours": 24,
    "computer_id": "COMPUTERNAME_USERNAME"
  }
  ```

### Data Transfer

- Employee computers transfer data to: `{central_data_path}/{computer_id}/`
- Central computer collects from: `{central_data_path}/` and moves to `AI/training_data/`

## Manual Configuration

If you need to configure after installation:

```bash
python _tools\config\CONFIGURE_EMPLOYEE_MODE.py
```

This will let you:
- Switch between employee and central mode
- Update central data path
- Change transfer interval

## How Data Flows

```
Employee Computer 1
  └─> Collects data
  └─> Transfers to: \\server\bot_data\COMPUTER1\
  
Employee Computer 2
  └─> Collects data
  └─> Transfers to: \\server\bot_data\COMPUTER2\
  
Central Computer
  └─> Collects from: \\server\bot_data\
  └─> Processes all data
  └─> Trains AI model
  └─> Stores patterns in AI/models/
```

## Benefits

1. **No Storage Overload**: Employee computers don't store massive training datasets
2. **Centralized Training**: All data trains one AI model (better results)
3. **No Ollama on Employees**: Employee computers don't need Ollama installed
4. **Automatic**: Everything happens passively when bots run
5. **Scalable**: Add as many employee computers as needed

## Troubleshooting

### Employee Computer Not Transferring

1. Check `AI/monitoring/system_config.json` exists and has correct mode
2. Verify central data path is accessible (test by creating a file there)
3. Check transfer interval hasn't passed yet (check `AI/monitoring/last_transfer.json`)
4. Look for errors in cleanup logs

### Central Computer Not Collecting

1. Verify central data path is set in config
2. Check that employee computers are actually transferring data
3. Look for collection errors in cleanup logs

### Data Not Appearing

1. Check file permissions on central data folder
2. Verify network connectivity (if using network share)
3. Check that transfer actually occurred (look for manifest files)

## Technical Details

### Employee Mode Flow

```
Bot Starts
  └─> Cleanup runs
      └─> Detects employee mode
      └─> Checks transfer interval
      └─> Transfers data to central location
      └─> Records transfer time
      └─> Minimal cleanup (only very old files)
```

### Central Mode Flow

```
Bot Starts
  └─> Cleanup runs
      └─> Detects central mode
      └─> Collects data from employee folders
      └─> Moves to training_data/
      └─> Runs AI learning
      └─> Runs Ollama training
      └─> Normal cleanup
```

## Security Notes

- Data is transferred as-is (no encryption in transit)
- If using network shares, ensure proper permissions
- Consider encrypting central data folder if sensitive
- Employee computers can only write to their own folder

