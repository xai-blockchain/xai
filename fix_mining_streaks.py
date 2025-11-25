#!/usr/bin/env python3
"""Fix corrupted mining_streaks.json file"""

import json
import sys

# Read the entire file
with open('src/xai/core/gamification_data/mining_streaks.json', 'r') as f:
    content = f.read()

# Find the first closing brace that ends the JSON object
brace_count = 0
first_brace = False
valid_end = 0

for i, char in enumerate(content):
    if char == '{':
        brace_count += 1
        first_brace = True
    elif char == '}':
        brace_count -= 1
        if first_brace and brace_count == 0:
            valid_end = i + 1
            break

if valid_end > 0:
    valid_json = content[:valid_end]
    # Verify it's valid
    try:
        data = json.loads(valid_json)
        print(f'Found valid JSON ending at position {valid_end}')
        print(f'Total addresses: {len(data)}')
        # Write the fixed version
        with open('src/xai/core/gamification_data/mining_streaks.json', 'w') as f:
            json.dump(data, f, indent=2)
        print('File fixed successfully')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
else:
    print('Could not find valid JSON structure')
    sys.exit(1)
