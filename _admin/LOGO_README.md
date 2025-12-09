# CCMD Bot Logo Creator

## Overview
The logo creator now supports using your own custom image files instead of generating the logo programmatically every time.

## How to Use Your Custom Logo

### Method 1: Using the Batch File (Easiest)
1. Save your logo as a PNG file (recommended format)
2. Right-click on `create_custom_logo.bat`
3. Select "Run with administrator privileges" (if needed)
4. Drag and drop your logo file onto the batch file, OR
5. Run: `create_custom_logo.bat "path\to\your\logo.png"`

### Method 2: Using Python Directly
1. Open Command Prompt in the `_admin` folder
2. Run: `python create_icon.py "path\to\your\logo.png"`

### Method 3: Default (Programmatic Creation)
1. Run: `python create_icon.py` (without any arguments)
2. This will create the default red pillar "I" logo

## Supported Image Formats
- PNG (recommended)
- JPG/JPEG
- GIF
- BMP
- TIFF

## Output Files
The script creates two files:
- `ccmd_bot_icon.ico` - For Windows shortcuts and desktop icons
- `ccmd_bot_icon.png` - For general use and preview

## Logo Requirements
- **Recommended size**: 256x256 pixels or larger
- **Format**: Square aspect ratio works best
- **Background**: Transparent or solid color (will be preserved)
- **Quality**: High resolution for best results

## Tips for Best Results
1. Use a square image (1:1 aspect ratio)
2. Ensure your logo is high resolution
3. Use PNG format for transparency support
4. Test with a simple design first

## Troubleshooting
- If the image doesn't load, check the file path
- Make sure the image file isn't corrupted
- Try converting to PNG format first
- Ensure PIL (Pillow) is installed: `pip install Pillow`

## Example Usage
```bash
# Using your custom logo
python create_icon.py "C:\Users\YourName\Desktop\my_company_logo.png"

# Using the default programmatic logo
python create_icon.py
```
