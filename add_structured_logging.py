#!/usr/bin/env python3
"""Add structured logging to exception handlers that lack it."""

import os
import re
from pathlib import Path
from collections import defaultdict

def get_logger_name(content):
    """Extract logger variable name from file content."""
    # Look for logger initialization
    patterns = [
        r'(\w+)\s*=\s*logging\.getLogger',
        r'(\w+)\s*=\s*get_logger\(',
        r'from xai\.core\.structured_logger import (\w+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    return None

def get_indentation(line):
    """Get indentation of a line."""
    return len(line) - len(line.lstrip())

def should_skip_file(filepath):
    """Check if file should be skipped."""
    skip_patterns = [
        'test_',
        'conftest.py',
        '__init__.py',
    ]
    filename = os.path.basename(filepath)
    return any(pattern in filename for pattern in skip_patterns)

def add_logging_to_handler(lines, handler_line_idx, exception_type, var_name, logger_var):
    """Add structured logging to an exception handler."""
    # Get indentation of the except line
    except_indent = get_indentation(lines[handler_line_idx])
    body_indent = except_indent + 4

    # Get the next few lines to analyze
    next_lines = []
    for i in range(handler_line_idx + 1, min(handler_line_idx + 15, len(lines))):
        line = lines[i]
        if line.strip() and get_indentation(line) <= except_indent:
            # End of this exception handler
            break
        next_lines.append(line)

    # Check if logging already exists
    handler_code = '\n'.join(next_lines)
    if 'logger.' in handler_code or 'logging.' in handler_code:
        # Already has logging
        return lines, False

    # Determine what kind of handler this is
    is_reraise = any('raise' in l for l in next_lines)
    is_import_error = 'ImportError' in exception_type
    is_validation = any(t in exception_type for t in ['ValueError', 'ValidationError', 'TypeError'])
    has_return = any('return' in l for l in next_lines)

    # Determine log level
    if is_import_error:
        log_level = 'warning'
    elif is_reraise and not has_return:
        # Just re-raising, use debug
        log_level = 'debug'
    elif is_validation:
        log_level = 'warning'
    else:
        log_level = 'error'

    # Find insertion point (right after except line)
    insert_idx = handler_line_idx + 1

    # Check if there's a comment or pass statement first
    while insert_idx < len(lines) and (
        not lines[insert_idx].strip() or
        lines[insert_idx].strip().startswith('#')
    ):
        insert_idx += 1

    # Create logging statement
    indent_str = ' ' * body_indent

    # Get context from function/class
    context_parts = []
    func_name = None
    for i in range(handler_line_idx - 1, max(0, handler_line_idx - 50), -1):
        line = lines[i]
        if line.strip().startswith('def '):
            match = re.search(r'def\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                break
        elif line.strip().startswith('class '):
            break

    # Create structured log message
    if func_name:
        message = f"{exception_type} in {func_name}"
    else:
        message = f"{exception_type} occurred"

    extra_fields = [
        f'error_type="{exception_type}"',
        f'error=str({var_name})',
    ]

    if func_name:
        extra_fields.append(f'function="{func_name}"')

    logging_lines = [
        f'{indent_str}{logger_var}.{log_level}(',
        f'{indent_str}    "{message}",',
    ]
    for field in extra_fields:
        logging_lines.append(f'{indent_str}    {field},')
    logging_lines.append(f'{indent_str})')

    # Insert the logging
    for offset, log_line in enumerate(logging_lines):
        lines.insert(insert_idx + offset, log_line)

    return lines, True

def process_file(filepath, dry_run=False):
    """Process a single file to add structured logging."""
    if should_skip_file(filepath):
        return 0

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

    # Check if file has logger
    logger_var = get_logger_name(content)
    if not logger_var and 'except' in content:
        # Need to add logger import
        # Find first import line
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                # Add logger import after existing imports
                insert_idx = i + 1
                while insert_idx < len(lines) and (
                    lines[insert_idx].strip().startswith('import ') or
                    lines[insert_idx].strip().startswith('from ') or
                    not lines[insert_idx].strip()
                ):
                    insert_idx += 1
                lines.insert(insert_idx, '')
                lines.insert(insert_idx + 1, 'import logging')
                lines.insert(insert_idx + 2, 'logger = logging.getLogger(__name__)')
                lines.insert(insert_idx + 3, '')
                logger_var = 'logger'
                break

    if not logger_var:
        # Still no logger, add at top
        lines.insert(0, 'import logging')
        lines.insert(1, 'logger = logging.getLogger(__name__)')
        lines.insert(2, '')
        logger_var = 'logger'

    # Find all exception handlers
    handlers_updated = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.search(r'^\s*except\s+(\w+(?:\s*,\s*\w+)*)\s+as\s+(\w+):', line)
        if match:
            exception_type = match.group(1)
            var_name = match.group(2)

            lines, updated = add_logging_to_handler(lines, i, exception_type, var_name, logger_var)
            if updated:
                handlers_updated += 1
                # Skip past the inserted lines
                i += 10

        i += 1

    if handlers_updated > 0 and not dry_run:
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    return handlers_updated

def main():
    """Main processing."""
    src_path = Path('/home/hudson/blockchain-projects/xai/src/xai')

    stats = {
        'files_processed': 0,
        'files_updated': 0,
        'handlers_updated': 0,
    }

    print("Processing files...")
    for py_file in sorted(src_path.rglob('*.py')):
        if '__pycache__' in str(py_file):
            continue

        stats['files_processed'] += 1
        handlers_updated = process_file(py_file, dry_run=False)

        if handlers_updated > 0:
            stats['files_updated'] += 1
            stats['handlers_updated'] += handlers_updated
            rel_path = str(py_file).replace('/home/hudson/blockchain-projects/xai/src/', '')
            print(f"  ✓ {rel_path}: {handlers_updated} handlers updated")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files updated: {stats['files_updated']}")
    print(f"Exception handlers updated: {stats['handlers_updated']}")

if __name__ == '__main__':
    main()
