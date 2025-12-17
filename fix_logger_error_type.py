#!/usr/bin/env python3
"""
Fix logger calls that use error_type= as a direct kwarg.
Convert them to use the 'extra' dict parameter.
"""

import re
import sys
from pathlib import Path


def fix_file(filepath):
    """Fix all logger calls in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    lines = content.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line contains a logger call with potential kwargs
        if re.search(r'(self\.)?logger\.(debug|info|warning|error|critical)\(', line):
            # Check if error_type= appears in this or next few lines
            block_end = min(i + 10, len(lines))
            block = '\n'.join(lines[i:block_end])

            if 'error_type=' in block and 'extra={' not in block:
                # This needs fixing - collect the full call
                call_lines = [line]
                j = i + 1
                paren_depth = line.count('(') - line.count(')')

                while j < len(lines) and paren_depth > 0:
                    call_lines.append(lines[j])
                    paren_depth += lines[j].count('(') - lines[j].count(')')
                    j += 1

                full_call = '\n'.join(call_lines)

                # Parse and fix the call
                fixed_call = fix_logger_call(full_call)
                if fixed_call != full_call:
                    result_lines.extend(fixed_call.split('\n'))
                    i = j
                    continue

        result_lines.append(line)
        i += 1

    new_content = '\n'.join(result_lines)

    if new_content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True

    return False


def fix_logger_call(call_text):
    """Fix a single logger call by moving kwargs to extra dict."""
    lines = call_text.split('\n')

    # Find the logger call line
    logger_match = None
    for idx, line in enumerate(lines):
        match = re.search(r'(\s*)(self\.)?logger\.(debug|info|warning|error|critical)\((.*)', line)
        if match:
            logger_match = (idx, match)
            break

    if not logger_match:
        return call_text

    idx, match = logger_match
    indent = match.group(1)
    logger_prefix = match.group(2) or ''
    log_level = match.group(3)
    rest = match.group(4)

    # Extract message (first argument) - handle multiline
    message = None
    if ',' in rest or ')' in rest:
        # Message might be on same line
        msg_match = re.match(r'([^,\)]+)', rest)
        if msg_match:
            message = msg_match.group(1).strip()
    else:
        # Message continues on next line
        if idx + 1 < len(lines):
            message = lines[idx + 1].strip().rstrip(',')

    if not message:
        return call_text

    # Find all kwargs in the call
    full_text = ' '.join(lines)
    kwargs_section = re.search(r'\(' + re.escape(message) + r'\s*,\s*(.+)\)', full_text, re.DOTALL)

    if not kwargs_section:
        return call_text

    kwargs_text = kwargs_section.group(1).strip()

    # Parse individual kwargs
    # Handle key=value, key="value", key=type(e).__name__, etc.
    kwarg_pairs = []
    current_key = None
    current_value = []
    in_value = False

    # Simple regex to find kwargs
    pattern = r'(\w+)=((?:[^,\n]|,(?![^\(]*\)))+)'
    for match in re.finditer(pattern, kwargs_text):
        key = match.group(1).strip()
        value = match.group(2).strip().rstrip(',').strip()

        if key in ['exc_info', 'stack_info', 'stacklevel']:
            continue  # Skip standard logging kwargs

        kwarg_pairs.append((key, value))

    if not kwarg_pairs:
        return call_text

    # Build the fixed call
    extra_items = [f'"{k}": {v}' for k, v in kwarg_pairs]
    extra_str = '{' + ', '.join(extra_items) + '}'

    # Construct new call
    result = f'{indent}{logger_prefix}logger.{log_level}(\n'
    result += f'{indent}    {message},\n'
    result += f'{indent}    extra={extra_str}\n'
    result += f'{indent})'

    return result


def main():
    src_dir = Path('/home/hudson/blockchain-projects/xai/src/xai')

    if not src_dir.exists():
        print(f"Error: {src_dir} does not exist")
        sys.exit(1)

    # Find all Python files with error_type=
    files_to_check = []
    for py_file in src_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'error_type=' in content:
                    # Check if it's a logger call (not just a prometheus label)
                    if re.search(r'logger\.[a-z]+\([^)]*error_type=', content, re.MULTILINE | re.DOTALL):
                        files_to_check.append(py_file)
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    print(f"Found {len(files_to_check)} files with logger error_type= kwarg")
    print()

    fixed_count = 0
    for filepath in files_to_check:
        rel_path = filepath.relative_to(src_dir.parent.parent)
        print(f"Processing {rel_path}...", end=' ')
        try:
            if fix_file(filepath):
                print("FIXED")
                fixed_count += 1
            else:
                print("NO CHANGES")
        except Exception as e:
            print(f"ERROR: {e}")

    print()
    print(f"Fixed {fixed_count} files")


if __name__ == '__main__':
    main()
