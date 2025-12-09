#!/usr/bin/env python3
import re

with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line 76 indentation
content = content.replace(
    '    return name.endswith(".pdf") and all(tok in name for tok in PACKET_TOKENS)',
    '        return name.endswith(".pdf") and all(tok in name for tok in PACKET_TOKENS)'
)

with open('isws_welcome_packet_uploader_v14style_FIXED.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed indentation")

