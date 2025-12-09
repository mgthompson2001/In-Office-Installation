#!/usr/bin/env python3
with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 76 (index 75) - add 4 more spaces to make it 8 spaces total
if len(lines) > 75:
    line = lines[75]
    if line.startswith('    return name.endswith'):
        lines[75] = '        ' + line.lstrip()
        print(f"Fixed line 76: {repr(lines[75])}")
    else:
        print(f"Line 76 already fixed or different: {repr(line)}")

with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done")

