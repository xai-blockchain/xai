#!/usr/bin/env python3
"""
Fix logger calls that use unsupported kwargs like error_type=.
Convert them to use the 'extra' dict parameter instead.
"""

import re
import sys
from pathlib import Path


def fix_logger_call(match):
    """
    Convert logger calls with direct kwargs to use 'extra' dict.

    Example:
        logger.error("message", error_type="ValueError", error="something")
    becomes:
        logger.error("message", extra={"error_type": "ValueError", "error": "something"})
    """
    indent = match.group(1)
    logger_name = match.group(2)
    log_level = match.group(3)
    message = match.group(4)
    kwargs = match.group(5)

    # Parse existing kwargs
    # Look for key=value patterns
    kwarg_pattern = r'(\w+)=([^,\n]+)'
    kwargs_dict = {}

    for kwarg_match in re.finditer(kwarg_pattern, kwargs):
        key = kwarg_match.group(1)
        value = kwarg_match.group(2).strip()

        # Skip if it's already part of an extra dict or exc_info/stack_info
        if key in ['exc_info', 'stack_info', 'stacklevel', 'extra']:
            continue

        kwargs_dict[key] = value

    if not kwargs_dict:
        return match.group(0)  # No kwargs to convert

    # Build the extra dict string
    extra_items = [f'"{k}": {v}' for k, v in kwargs_dict.items()]
    extra_str = ', '.join(extra_items)

    # Reconstruct the logger call
    result = f'{indent}{logger_name}.{log_level}(\n{indent}    {message},\n{indent}    extra={{{extra_str}}}\n{indent})'

    return result


def fix_simple_logger_call(line):
    """
    Fix simple single-line logger calls.

    Example:
        logger.error("msg", error_type="ValueError")
    becomes:
        logger.error("msg", extra={"error_type": "ValueError"})
    """
    # Pattern for single-line logger calls with kwargs
    pattern = r'(\s*)([\w.]+)\.(debug|info|warning|error|critical)\(([^,\n]+),\s*([^)]+)\)'

    def replace_func(match):
        indent = match.group(1)
        logger_name = match.group(2)
        log_level = match.group(3)
        message = match.group(4).strip()
        kwargs = match.group(5).strip()

        # Check if kwargs contain error_type or other custom fields
        if 'error_type=' not in kwargs and 'error=' not in kwargs and \
           'function=' not in kwargs and 'endpoint=' not in kwargs and \
           'message_type=' not in kwargs:
            return match.group(0)  # No custom kwargs to fix

        # Check if already using extra
        if 'extra=' in kwargs:
            return match.group(0)

        # Parse kwargs
        kwarg_pattern = r'(\w+)=([^,]+)'
        kwargs_list = []
        extra_dict = {}

        for kw_match in re.finditer(kwarg_pattern, kwargs):
            key = kw_match.group(1)
            value = kw_match.group(2).strip().rstrip(',')

            # Standard logging kwargs that should stay as-is
            if key in ['exc_info', 'stack_info', 'stacklevel']:
                kwargs_list.append(f'{key}={value}')
            else:
                # Custom kwargs go into extra
                extra_dict[key] = value

        if not extra_dict:
            return match.group(0)

        # Build new call
        extra_items = [f'"{k}": {v}' for k, v in extra_dict.items()]
        extra_str = '{' + ', '.join(extra_items) + '}'

        result = f'{indent}{logger_name}.{log_level}({message}, extra={extra_str})'
        if kwargs_list:
            result = f'{indent}{logger_name}.{log_level}({message}, {", ".join(kwargs_list)}, extra={extra_str})'

        return result

    return re.sub(pattern, replace_func, line)


def process_file(filepath):
    """Process a single file to fix logger calls."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    lines = content.split('\n')
    modified_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for multi-line logger calls
        if re.search(r'(logger|self\.logger)\.(debug|info|warning|error|critical)\(', line):
            # Check if this is a multi-line call
            if 'error_type=' in line or i + 1 < len(lines) and 'error_type=' in lines[i + 1]:
                # Collect all lines of this call
                call_lines = [line]
                j = i + 1
                paren_count = line.count('(') - line.count(')')

                while j < len(lines) and paren_count > 0:
                    call_lines.append(lines[j])
                    paren_count += lines[j].count('(') - lines[j].count(')')
                    j += 1

                # Join and process
                full_call = '\n'.join(call_lines)

                if 'error_type=' in full_call and 'extra=' not in full_call:
                    # Need to fix this call
                    fixed_call = fix_logger_multiline(full_call)
                    modified_lines.append(fixed_call)
                    i = j
                    continue

        # Try simple single-line fix
        fixed_line = fix_simple_logger_call(line)
        modified_lines.append(fixed_line)
        i += 1

    new_content = '\n'.join(modified_lines)

    if new_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True

    return False


def fix_logger_multiline(call_text):
    """Fix multi-line logger calls."""
    lines = call_text.split('\n')

    # Extract the logger call info
    first_line = lines[0]
    match = re.search(r'(\s*)([\w.]+)\.(debug|info|warning|error|critical)\(', first_line)

    if not match:
        return call_text

    indent = match.group(1)
    logger_name = match.group(2)
    log_level = match.group(3)

    # Extract message (first argument)
    message_match = re.search(r'\((.*?)(?:,|\))', first_line)
    if not message_match:
        return call_text

    message = message_match.group(1).strip()

    # Collect all kwargs
    full_text = ' '.join(lines)
    kwargs_match = re.search(r'\([^,]+,(.+)\)', full_text, re.DOTALL)

    if not kwargs_match:
        return call_text

    kwargs_text = kwargs_match.group(1)

    # Parse kwargs
    kwarg_pattern = r'(\w+)=([^,\n]+?)(?:,|\s*$)'
    extra_dict = {}
    standard_kwargs = []

    for kw_match in re.finditer(kwarg_pattern, kwargs_text):
        key = kw_match.group(1)
        value = kw_match.group(2).strip().rstrip(',')

        if key in ['exc_info', 'stack_info', 'stacklevel']:
            standard_kwargs.append(f'{key}={value}')
        else:
            extra_dict[key] = value

    if not extra_dict:
        return call_text

    # Build new call
    extra_items = [f'"{k}": {v}' for k, v in extra_dict.items()]
    extra_str = '{' + ', '.join(extra_items) + '}'

    result = f'{indent}{logger_name}.{log_level}({message}, extra={extra_str})'
    if standard_kwargs:
        result = f'{indent}{logger_name}.{log_level}({message}, {", ".join(standard_kwargs)}, extra={extra_str})'

    return result


def main():
    # Find all Python files with error_type= in src/xai
    src_dir = Path(__file__).parent / 'src' / 'xai'

    if not src_dir.exists():
        print(f"Error: {src_dir} does not exist")
        sys.exit(1)

    files_to_fix = []
    for py_file in src_dir.rglob('*.py'):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'error_type=' in content:
                files_to_fix.append(py_file)

    print(f"Found {len(files_to_fix)} files with error_type= kwarg")

    fixed_count = 0
    for filepath in files_to_fix:
        print(f"Processing {filepath.relative_to(src_dir.parent.parent)}...", end=' ')
        if process_file(filepath):
            print("FIXED")
            fixed_count += 1
        else:
            print("NO CHANGES")

    print(f"\nFixed {fixed_count} files")


if __name__ == '__main__':
    main()
