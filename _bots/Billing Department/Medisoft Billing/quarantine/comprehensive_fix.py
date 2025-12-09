"""Comprehensive fix for all indentation errors"""
with open('medisoft_billing_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = False

# Fix line 1225 (index 1224) - should be indented under the if statement
if len(lines) > 1224:
    line_1224 = lines[1223]  # The if statement
    line_1225 = lines[1224]  # The line that needs fixing
    
    if 'if timeout is not None:' in line_1224:
        # Line 1225 should have 12 spaces (indented under if)
        stripped = line_1225.lstrip()
        if stripped.startswith('self.gui_log'):
            lines[1224] = '            ' + stripped  # 12 spaces
            fixed = True
            print(f"Fixed line 1225")

# Write back
if fixed:
    with open('medisoft_billing_bot.py', 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print("✅ Fixed all indentation issues")
else:
    print("⚠️ No fixes needed or issue not found")

