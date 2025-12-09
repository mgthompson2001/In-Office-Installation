# 🎨 Setup Your Custom Logo

## Quick Setup (2 minutes)

### Step 1: Save Your Logo
1. Save your pillar "I" logo as a PNG file
2. Name it exactly: `custom_logo.png`
3. Place it in this folder: `_admin/custom_logo.png`

### Step 2: That's It!
- The installer will automatically use your custom logo
- No other steps needed!

## What Happens Next

When employees download and install the software:

✅ **Your custom logo will appear on the desktop shortcut**  
✅ **No extra steps for employees**  
✅ **Automatic icon generation**  
✅ **Professional branded experience**  

## File Structure
```
_admin/
├── custom_logo.png          ← Put your logo here
├── create_icon.py           ← Logo creator (updated)
├── create_custom_logo.bat   ← Easy setup tool
└── LOGO_README.md          ← Detailed instructions
```

## Logo Requirements
- **Format**: PNG (recommended)
- **Size**: 256x256 pixels or larger
- **Name**: Must be exactly `custom_logo.png`
- **Location**: Must be in the `_admin` folder

## Testing Your Logo
1. Place your `custom_logo.png` in the `_admin` folder
2. Run `create_custom_logo.bat` to test
3. Check that `ccmd_bot_icon.ico` is created
4. The installer will use this automatically

## Troubleshooting
- **Logo not showing?** Check the filename is exactly `custom_logo.png`
- **Wrong location?** Make sure it's in the `_admin` folder
- **Format issues?** Convert to PNG format first
- **Size problems?** Use a square image (1:1 aspect ratio)

## Fallback
If no custom logo is found, the system will create the default red pillar "I" logo automatically.
