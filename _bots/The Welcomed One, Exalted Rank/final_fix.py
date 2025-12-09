#!/usr/bin/env python3
with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'rb') as f:
    lines = f.readlines()

# Fix line 76 (index 75) - ensure it has 8 spaces
if len(lines) > 75:
    lines[75] = b'        return name.endswith(".pdf") and all(tok in name for tok in PACKET_TOKENS)\r\n'
    print("Fixed line 76")

with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'wb') as f:
    f.writelines(lines)

print("File saved. Compiling...")
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'isws_welcome_packet_uploader_v14style_FIXED.py'], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("SUCCESS: File compiles!")
else:
    print(f"ERROR: {result.stderr}")

