#!/usr/bin/env python3
"""Batch add structured logging to exception handlers."""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

def get_function_name(lines: List[str], handler_idx: int) -> Optional[str]:
    """Get the function name containing this exception handler."""
    for i in range(handler_idx - 1, max(0, handler_idx - 100), -1):
        line = lines[i]
        if line.strip().startswith('def '):
            match = re.search(r'def\s+(\w+)\s*\(', line)
            if match:
                return match.group(1)
        elif line.strip().startswith('class ') and 'def ' not in line:
            # Reached class definition without finding function
            break
    return None

def get_indentation(line: str) -> int:
    """Get indentation level of a line."""
    return len(line) - len(line.lstrip())

def has_logging(lines: List[str], start_idx: int, except_indent: int) -> bool:
    """Check if exception handler already has logging."""
    for i in range(start_idx + 1, min(start_idx + 20, len(lines))):
        line = lines[i]
        if line.strip() and get_indentation(line) <= except_indent:
            break
        if 'logger.' in line or 'logging.' in line:
            return True
    return False

def should_add_logging(lines: List[str], handler_idx: int, exception_type: str, except_indent: int) -> bool:
    """Determine if we should add logging to this handler."""
    # Check if already has logging
    if has_logging(lines, handler_idx, except_indent):
        return False

    # Get handler body
    handler_body = []
    for i in range(handler_idx + 1, min(handler_idx + 20, len(lines))):
        line = lines[i]
        if line.strip() and get_indentation(line) <= except_indent:
            break
        handler_body.append(line.strip())

    body_text = ' '.join(handler_body)

    # Skip if it's just re-raising immediately
    if handler_body and handler_body[0].startswith('raise') and len(handler_body) <= 2:
        return False

    # Skip ImportError at module level
    if 'ImportError' in exception_type and handler_idx < 50:
        return False

    # Add logging for everything else
    return True

def get_log_level(exception_type: str, handler_body: List[str]) -> str:
    """Determine appropriate log level."""
    body_text = ' '.join(handler_body).lower()

    if 'ImportError' in exception_type:
        return 'warning'
    elif any(t in exception_type for t in ['ValueError', 'ValidationError', 'TypeError']):
        if 'raise' in body_text:
            return 'debug'
        return 'warning'
    elif 'return' in body_text or 'jsonify' in body_text:
        return 'warning'
    else:
        return 'error'

def process_file(filepath: Path) -> int:
    """Add structured logging to a file's exception handlers."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

    # Remove trailing newlines for processing
    lines = [line.rstrip('\n') for line in lines]

    # Check if file has logger
    content = '\n'.join(lines)
    has_logger = bool(re.search(r'logger\s*=\s*logging\.getLogger', content))

    changes_made = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # Find exception handlers
        match = re.match(r'^(\s*)except\s+(\w+(?:\s*,\s*\w+)*)\s+as\s+(\w+):', line)
        if not match:
            i += 1
            continue

        indent_str = match.group(1)
        exception_type = match.group(2)
        var_name = match.group(3)
        except_indent = len(indent_str)
        body_indent = except_indent + 4

        # Check if we should add logging
        if not should_add_logging(lines, i, exception_type, except_indent):
            i += 1
            continue

        # Get handler body to determine log level
        handler_body = []
        for j in range(i + 1, min(i + 15, len(lines))):
            if lines[j].strip() and get_indentation(lines[j]) <= except_indent:
                break
            handler_body.append(lines[j].strip())

        # Get function name
        func_name = get_function_name(lines, i)

        # Determine log level
        log_level = get_log_level(exception_type, handler_body)

        # Create log message
        if func_name:
            msg = f"{exception_type} in {func_name}"
        else:
            msg = f"{exception_type} occurred"

        # Build logging statement
        log_indent = ' ' * body_indent
        log_lines = [
            f'{log_indent}logger.{log_level}(',
            f'{log_indent}    "{msg}",',
            f'{log_indent}    error_type="{exception_type}",',
            f'{log_indent}    error=str({var_name}),',
        ]

        if func_name:
            log_lines.append(f'{log_indent}    function="{func_name}",')

        log_lines.append(f'{log_indent})')

        # Find insertion point (skip comments and empty lines after except)
        insert_idx = i + 1
        while insert_idx < len(lines) and (
            not lines[insert_idx].strip() or
            lines[insert_idx].strip().startswith('#')
        ):
            insert_idx += 1

        # Insert logging
        for offset, log_line in enumerate(log_lines):
            lines.insert(insert_idx + offset, log_line)

        changes_made += 1
        # Skip past inserted lines
        i = insert_idx + len(log_lines) + 5

    if changes_made > 0:
        # Add logger import if needed
        if not has_logger:
            # Find where to add import
            import_idx = 0
            for idx, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_idx = idx + 1
                elif import_idx > 0 and not line.strip():
                    break

            if import_idx == 0:
                # No imports found, add at top after docstring
                for idx, line in enumerate(lines):
                    if '"""' in line or "'''" in line:
                        # Skip docstring
                        quote = '"""' if '"""' in line else "'''"
                        if line.count(quote) == 1:
                            # Multi-line docstring
                            for j in range(idx + 1, len(lines)):
                                if quote in lines[j]:
                                    import_idx = j + 1
                                    break
                        else:
                            import_idx = idx + 1
                        break
                    elif line.strip() and not line.strip().startswith('#'):
                        import_idx = idx
                        break

            lines.insert(import_idx, '')
            lines.insert(import_idx + 1, 'import logging')
            lines.insert(import_idx + 2, 'logger = logging.getLogger(__name__)')
            lines.insert(import_idx + 3, '')

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

    return changes_made

def main():
    """Main processing."""
    src_path = Path('/home/hudson/blockchain-projects/xai/src/xai')

    # Skip test files and specific patterns
    skip_patterns = ['test_', 'conftest.py', '__init__.py', '__pycache__']

    stats = {
        'files_processed': 0,
        'files_updated': 0,
        'handlers_updated': 0,
    }

    updated_files = []

    print("Processing Python files...")
    for py_file in sorted(src_path.rglob('*.py')):
        if any(pattern in str(py_file) for pattern in skip_patterns):
            continue

        stats['files_processed'] += 1
        changes = process_file(py_file)

        if changes > 0:
            stats['files_updated'] += 1
            stats['handlers_updated'] += changes
            rel_path = str(py_file).replace(str(src_path.parent) + '/', '')
            updated_files.append((rel_path, changes))
            print(f"  ✓ {rel_path}: {changes} handlers")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files updated: {stats['files_updated']}")
    print(f"Exception handlers updated: {stats['handlers_updated']}")

    if updated_files:
        print(f"\nUpdated files ({len(updated_files)}):")
        for path, count in updated_files[:30]:
            print(f"  - {path} ({count} handlers)")
        if len(updated_files) > 30:
            print(f"  ... and {len(updated_files) - 30} more")

if __name__ == '__main__':
    main()
