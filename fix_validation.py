with open("src/xai/core/security_validation.py", "r") as f:
    lines = f.readlines()

# Find and replace the problematic section
new_lines = []
skip_next = 0
for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    
    if i < len(lines) - 6 and "# Zero amounts should be rejected" in line:
        # Skip the next 3 lines (comment + if statement + raise)
        skip_next = 2
        # Add the new code
        new_lines.append("        # Allow zero amounts (for fees, etc.)\n")
        new_lines.append("        # But check minimum for non-zero amounts\n")
        new_lines.append("        if amount > 0 and amount < SecurityValidator.MIN_AMOUNT:\n")
        continue
    elif i < len(lines) - 1 and "if amount < SecurityValidator.MIN_AMOUNT:" in line and "amount > 0 and" not in line:
        # Skip duplicate check
        skip_next = 2
        continue
    
    new_lines.append(line)

with open("src/xai/core/security_validation.py", "w") as f:
    f.writelines(new_lines)

print("Fixed!")
