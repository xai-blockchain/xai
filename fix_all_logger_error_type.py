#!/usr/bin/env python3
"""
Systematically fix all logger calls with error_type= kwargs.
"""

import re
from pathlib import Path


def fix_multiline_logger(content):
    """
    Fix multi-line logger calls where kwargs are on separate lines.

    Pattern:
        logger.error(
            "message",
            key1=value1,
            error_type="Type",
            key2=value2,
        )

    Becomes:
        logger.error(
            "message",
            extra={
                "key1": value1,
                "error_type": "Type",
                "key2": value2
            }
        )
    """
    # Find logger calls with error_type on separate lines
    pattern = r'(\s*)((?:self\.)?logger)\.(debug|info|warning|error|critical)\(\s*\n(\s+)"([^"]+)",\s*\n((?:\s+\w+=.+,?\s*\n)+)(\s*)\)'

    def replace_func(match):
        indent = match.group(1)
        logger_ref = match.group(2)
        log_level = match.group(3)
        msg_indent = match.group(4)
        message = match.group(5)
        kwargs_block = match.group(6)
        closing_indent = match.group(7)

        # Check if error_type is in kwargs
        if 'error_type=' not in kwargs_block:
            return match.group(0)

        # Check if already using extra
        if 'extra=' in kwargs_block:
            return match.group(0)

        # Parse kwargs
        kwarg_lines = [l.strip() for l in kwargs_block.strip().split('\n') if l.strip()]
        kwargs = {}

        for line in kwarg_lines:
            line = line.rstrip(',').strip()
            if '=' in line:
                parts = line.split('=', 1)
                key = parts[0].strip()
                value = parts[1].strip().rstrip(',')

                if key in ['exc_info', 'stack_info', 'stacklevel']:
                    continue  # Skip standard logging params

                kwargs[key] = value

        if not kwargs:
            return match.group(0)

        # Build extra dict
        extra_items = [f'"{k}": {v}' for k, v in kwargs.items()]
        extra_dict = ',\n'.join([f'{msg_indent}    {item}' for item in extra_items])

        result = f'{indent}{logger_ref}.{log_level}(\n{msg_indent}"{message}",\n{msg_indent}extra={{\n{extra_dict}\n{msg_indent}}}\n{closing_indent})'

        return result

    return re.sub(pattern, replace_func, content)


def main():
    src_dir = Path('/home/hudson/blockchain-projects/xai/src/xai')

    # Get all Python files with error_type=
    files_to_fix = []
    for py_file in src_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'error_type=' in content and 'logger.' in content:
                    files_to_fix.append(py_file)
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    print(f"Found {len(files_to_fix)} files to check")

    fixed = 0
    for filepath in files_to_fix:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()

            # Apply fixes
            content = fix_multiline_logger(original)

            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed: {filepath.relative_to(src_dir.parent.parent)}")
                fixed += 1
            else:
                # Check if still has issues
                if re.search(r'logger\.[a-z]+\([^)]*\n[^)]*error_type=', original):
                    print(f"REVIEW: {filepath.relative_to(src_dir.parent.parent)}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    print(f"\nFixed {fixed} files")


if __name__ == '__main__':
    main()
