"""Fix all indentation issues - ensure consistent spaces"""
with open('medisoft_billing_bot.py', 'rb') as f:
    content = f.read()

lines = content.decode('utf-8', errors='ignore').split('\n')

# Fix line 1337 if it has wrong indentation
if len(lines) > 1336:
    line_1337 = lines[1336]
    if 'time.sleep(1.5)' in line_1337:
        # Should have same indentation as line above (1336)
        line_1336 = lines[1335]
        indent_1336 = len(line_1336) - len(line_1336.lstrip())
        # Line 1337 should have same indentation
        stripped_1337 = line_1337.lstrip()
        correct_indent = ' ' * indent_1336
        lines[1336] = correct_indent + stripped_1337
        print(f"Fixed line 1337: indent={indent_1336}, content={stripped_1337[:40]}")

# Write back
with open('medisoft_billing_bot.py', 'w', encoding='utf-8', newline='') as f:
    f.write('\n'.join(lines))

print("Fixed all indentation issues")

