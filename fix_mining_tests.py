#!/usr/bin/env python3
"""Fix mining tests to use create_transaction method"""

import re

# Read the test file
with open('tests/xai_tests/integration/test_mining.py', 'r') as f:
    content = f.read()

# Pattern to find Transaction creations followed by public_key and sign_transaction
pattern = r'(\s+)tx = Transaction\(([^,]+), ([^,]+), ([^,]+), ([^)]+)\)\n\s+tx\.public_key = ([^\.]+)\.public_key\n\s+tx\.sign_transaction\(\6\.private_key\)'

def replace_tx(match):
    indent = match.group(1)
    sender = match.group(2)
    recipient = match.group(3)
    amount = match.group(4)
    fee = match.group(5)
    wallet_var = match.group(6)

    return (f'{indent}tx = bc.create_transaction(\n'
            f'{indent}    {sender}, {recipient}, {amount}, {fee},\n'
            f'{indent}    {wallet_var}.private_key, {wallet_var}.public_key\n'
            f'{indent})')

# Apply replacements
content = re.sub(pattern, replace_tx, content)

# Write back
with open('tests/xai_tests/integration/test_mining.py', 'w') as f:
    f.write(content)

print("Fixed mining tests!")
