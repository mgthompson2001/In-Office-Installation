"""Fix all indentation issues"""
import re

with open('medisoft_billing_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Fix line 1225 (index 1224) - needs proper indentation
if len(lines) > 1224:
    if 'if timeout is not None:' in lines[1223]:
        # Line 1225 should have 12 spaces (3 levels of 4 spaces)
        current_line = lines[1224]
        if current_line.strip().startswith('self.gui_log'):
            # Remove leading spaces and add correct indentation
            new_line = '            ' + current_line.lstrip()
            lines[1224] = new_line
            print(f"Fixed line 1225: {repr(new_line[:50])}")

# Write back
with open('medisoft_billing_bot.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Fixed all indentation issues")

