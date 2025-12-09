"""Final fix for line 1225 indentation"""
with open('medisoft_billing_bot.py', 'rb') as f:
    lines = f.readlines()

# Line 1225 (index 1224) needs to be indented properly
if len(lines) > 1224:
    line_bytes = lines[1224]
    # Current line starts with 8 spaces, needs 12 spaces
    line_str = line_bytes.decode('utf-8', errors='ignore')
    stripped = line_str.lstrip()
    if stripped.startswith('self.gui_log'):
        # Add correct indentation (12 spaces = 3 levels of 4)
        lines[1224] = ('            ' + stripped).encode('utf-8')
        print("Fixed line 1225 indentation")

with open('medisoft_billing_bot.py', 'wb') as f:
    f.writelines(lines)

print("Done")

