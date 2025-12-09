"""Fix indentation on line 1225"""
with open('medisoft_billing_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 1225 (index 1224) - needs 4 more spaces
if len(lines) > 1224:
    line = lines[1224]
    if line.startswith('        self.gui_log'):
        lines[1224] = '            self.gui_log' + line[8:]

with open('medisoft_billing_bot.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation")

