# IPS IA Referral Form Implementation Summary

## Overview
Implemented dual-tab IPS IA Referral form uploader with intelligent file-based filtering to handle both regular and IPS therapy notes uploads.

## Key Features Implemented

### 1. Document Filename Modification ✅
**File**: `isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py`

**Changes Made**:
- Modified `click_print_and_save_pdf()` function to accept `counselor_name` parameter
- Added logic to check if counselor name contains "IPS"
- If IPS counselor detected, appends "IPS" to document filename

**Filename Examples**:
- Regular: `"John Doe Referral Form.pdf"`
- IPS: `"IPS John Doe Referral Form.pdf"`
- Urgent Regular: `"URGENT John Doe Referral Form.pdf"`
- Urgent IPS: `"URGENT IPS John Doe Referral Form.pdf"`

**Code Changes**:
```python
# Check if counselor has IPS in their name (for file naming)
is_ips_counselor = False
if counselor_name and "ips" in str(counselor_name).lower():
    is_ips_counselor = True
    self.log(f"[IPS] Counselor '{counselor_name}' has IPS - will append to filename")

# Generate filename with IPS prefix if needed
if is_ips_counselor:
    filename = f"IPS {client_name} Referral Form.pdf"
else:
    filename = f"{client_name} Referral Form.pdf"
```

### 2. Dual-Tab Uploader Interface ✅
**File**: `IPS_IA_Referral_Form_Uploader_Dual_Tab.py`

**Features**:
- **Tab 1**: Base IA Referral Uploader (existing functionality)
- **Tab 2**: IPS IA Referral Uploader (logs into IPS therapy notes)
- File-based filtering logic ready for implementation
- Separate configuration for each uploader
- Independent logging and status tracking

**Interface Structure**:
- Configuration sections for Penelope URLs, credentials
- Options for file filtering (Base: skip IPS files, IPS: only IPS files)
- Action buttons for folder selection and uploader launch
- Dedicated log areas for each tab

## File-Based Filtering Logic

### Base IA Referral Uploader
- **Purpose**: Processes regular therapy notes
- **File Filtering**: Skips files with "IPS" in filename
- **Login Target**: Regular Penelope therapy notes system

### IPS IA Referral Uploader  
- **Purpose**: Processes IPS therapy notes
- **File Filtering**: Only processes files with "IPS" in filename
- **Login Target**: IPS Penelope therapy notes system

## Data Flow

1. **Form Creation Phase**:
   - IA Referral bot reads CSV data
   - Checks counselor name in column L ("Therapist Name")
   - If counselor contains "IPS", appends "IPS" to document filename
   - Saves files to "Referral Form Bot Output" folder

2. **Upload Phase**:
   - Base uploader: Processes all files EXCEPT those with "IPS" in filename
   - IPS uploader: Processes ONLY files with "IPS" in filename
   - Each uploader logs into appropriate therapy notes system

## CSV Column Mapping
Based on the test CSV structure:
- **Column L (index 11)**: "Therapist Name" 
- **Example**: "Perez, Ethel - IPS" → triggers IPS file naming

## Next Steps for Full Integration

### 1. Integrate Existing Uploader Logic
- Copy existing IA Referral bot uploader functionality to both tabs
- Implement file filtering based on filename patterns
- Add Selenium automation for both Base and IPS login systems

### 2. File Filtering Implementation
```python
def filter_files_for_uploader(folder_path, is_ips_mode):
    files = os.listdir(folder_path)
    if is_ips_mode:
        # Only process files with "IPS" in filename
        return [f for f in files if "IPS" in f]
    else:
        # Skip files with "IPS" in filename
        return [f for f in files if "IPS" not in f]
```

### 3. Login System Integration
- Base uploader: Regular Penelope login
- IPS uploader: IPS-specific Penelope login
- Separate credential management for each system

## Benefits

1. **Clear Separation**: Files are automatically categorized by filename
2. **No Data Loss**: All files are created, just routed differently
3. **Flexible Processing**: Can run Base and IPS uploaders independently
4. **Audit Trail**: Clear logging shows which files are processed by which uploader
5. **Scalable**: Easy to add more therapy note systems in the future

## Testing

To test the implementation:
1. Run IA Referral bot with CSV containing IPS counselors
2. Verify files with "IPS" prefix are created in output folder
3. Test Base uploader skips IPS files
4. Test IPS uploader only processes IPS files
