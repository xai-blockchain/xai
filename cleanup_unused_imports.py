#!/usr/bin/env python3
"""Remove unused typing imports from files."""
from __future__ import annotations

import re
from pathlib import Path


def cleanup_file(file_path: Path) -> bool:
    """Remove unused Optional, Union, List, Dict, etc. from typing imports."""
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Types to potentially remove
    remove_types = ['Optional', 'Union', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet']

    for type_name in remove_types:
        # Check if type is imported
        if f'from typing import' in content and type_name in content:
            # Check if type is actually used in code (not in import line)
            pattern = rf'{type_name}\['
            # Search for usage outside of import statements
            lines = content.split('\n')
            used = False
            for line in lines:
                if line.strip().startswith('from typing import'):
                    continue
                if re.search(pattern, line):
                    used = True
                    break

            if not used:
                # Remove from imports
                # Handle different import formats
                content = re.sub(rf'from typing import {type_name}\n', '', content)
                content = re.sub(rf'from typing import (.*), {type_name}(.*)\n',
                                r'from typing import \1\2\n', content)
                content = re.sub(rf'from typing import {type_name}, (.*)\n',
                                r'from typing import \1\n', content)
                # Clean up extra commas and spaces
                content = re.sub(r'from typing import (.*), , (.*)\n',
                                r'from typing import \1, \2\n', content)
                content = re.sub(r'from typing import (.*),  (.*)\n',
                                r'from typing import \1, \2\n', content)

    # Clean up empty import lines
    content = re.sub(r'^from typing import\s*$', '', content, flags=re.MULTILINE)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    """Main entry point."""
    src_path = Path('src')
    updated = 0

    for file_path in src_path.rglob('*.py'):
        if cleanup_file(file_path):
            print(f"Cleaned: {file_path}")
            updated += 1

    # Also do tests, scripts, explorer
    for base in ['tests', 'scripts', 'explorer']:
        path = Path(base)
        if path.exists():
            for file_path in path.rglob('*.py'):
                if cleanup_file(file_path):
                    print(f"Cleaned: {file_path}")
                    updated += 1

    print(f"\nTotal files cleaned: {updated}")


if __name__ == '__main__':
    main()
