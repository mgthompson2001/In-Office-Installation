#!/usr/bin/env python3
with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 76 (index 75) - needs 8 spaces, not 4
if len(lines) > 75:
    line = lines[75]
    if line.startswith('    return name.endswith'):
        lines[75] = '        return name.endswith(".pdf") and all(tok in name for tok in PACKET_TOKENS)\n'
        print(f"Fixed line 76")

with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation on line 76")

