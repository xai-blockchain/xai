#!/usr/bin/env python3
"""Fix all test files to use create_transaction method"""

import re
import os
import glob

# Find all test files
test_files = glob.glob('tests/**/*.py', recursive=True)

for filepath in test_files:
    if '__pycache__' in filepath or 'fix_' in filepath:
        continue

    print(f"Processing {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Pattern to find Transaction creations followed by public_key and sign_transaction
    # Handle various wallet variable names
    pattern = r'(\s+)tx = Transaction\(([^,]+), ([^,]+), ([^,]+), ([^)]+)\)\n(\s+)tx\.public_key = ([^\.]+)\.public_key\n\s+tx\.sign_transaction\(\7\.private_key\)'

    def replace_tx(match):
        indent = match.group(1)
        sender = match.group(2)
        recipient = match.group(3)
        amount = match.group(4)
        fee = match.group(5)
        wallet_var = match.group(7)

        return (f'{indent}tx = bc.create_transaction(\n'
                f'{indent}    {sender}, {recipient}, {amount}, {fee},\n'
                f'{indent}    {wallet_var}.private_key, {wallet_var}.public_key\n'
                f'{indent})')

    content = re.sub(pattern, replace_tx, content)

    # Also handle tx1, tx2, etc.
    for i in range(1, 10):
        pattern_n = rf'(\s+)tx{i} = Transaction\(([^,]+), ([^,]+), ([^,]+), ([^)]+)\)\n(\s+)tx{i}\.public_key = ([^\.]+)\.public_key\n\s+tx{i}\.sign_transaction\(\7\.private_key\)'

        def replace_txn(match):
            indent = match.group(1)
            sender = match.group(2)
            recipient = match.group(3)
            amount = match.group(4)
            fee = match.group(5)
            wallet_var = match.group(7)

            return (f'{indent}tx{i} = bc.create_transaction(\n'
                    f'{indent}    {sender}, {recipient}, {amount}, {fee},\n'
                    f'{indent}    {wallet_var}.private_key, {wallet_var}.public_key\n'
                    f'{indent})')

        content = re.sub(pattern_n, replace_txn, content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Updated {filepath}")

print("Done!")
