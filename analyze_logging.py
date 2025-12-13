#!/usr/bin/env python3
"""Analyze exception handlers and logging across the codebase."""

import os
import re
from pathlib import Path
from collections import defaultdict

def analyze_file(filepath):
    """Analyze a single Python file for exception handlers and logging."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return None

    results = {
        'filepath': str(filepath),
        'exception_handlers': [],
        'has_logger': 'logger' in content or 'logging' in content,
        'has_structured_logging': 'logger.error(' in content or 'logger.warning(' in content,
    }

    # Find all exception handlers with context
    for i, line in enumerate(lines):
        # Match: except SomeException as e:
        match = re.search(r'^\s*except\s+(\w+(?:\s*,\s*\w+)*)\s+as\s+(\w+):', line)
        if match:
            exception_type = match.group(1)
            var_name = match.group(2)

            # Get next 10 lines to see if there's logging
            next_lines = lines[i+1:i+11]
            handler_code = '\n'.join(next_lines)

            has_logging = any(
                'logger.' in l or 'logging.' in l
                for l in next_lines
            )
            has_structured = any(
                ('logger.error(' in l or 'logger.warning(' in l or 'logger.info(' in l)
                and ('extra=' in l or 'error_type=' in handler_code or '"' in l)
                for l in next_lines
            )

            results['exception_handlers'].append({
                'line': i + 1,
                'exception_type': exception_type,
                'var_name': var_name,
                'has_logging': has_logging,
                'has_structured': has_structured,
                'context': line.strip() + '\n' + '\n'.join(next_lines[:3])
            })

    return results

def main():
    """Main analysis."""
    src_path = Path('/home/hudson/blockchain-projects/xai/src/xai')

    stats = {
        'total_files': 0,
        'files_with_exceptions': 0,
        'total_exception_handlers': 0,
        'handlers_with_logging': 0,
        'handlers_with_structured_logging': 0,
        'handlers_without_logging': [],
    }

    for py_file in src_path.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        stats['total_files'] += 1
        result = analyze_file(py_file)

        if not result:
            continue

        if result['exception_handlers']:
            stats['files_with_exceptions'] += 1

            for handler in result['exception_handlers']:
                stats['total_exception_handlers'] += 1

                if handler['has_logging']:
                    stats['handlers_with_logging'] += 1

                if handler['has_structured']:
                    stats['handlers_with_structured_logging'] += 1
                else:
                    # Handler lacks structured logging
                    stats['handlers_without_logging'].append({
                        'file': result['filepath'],
                        'line': handler['line'],
                        'exception_type': handler['exception_type'],
                        'has_any_logging': handler['has_logging'],
                        'context': handler['context']
                    })

    # Print summary
    print("=" * 80)
    print("EXCEPTION HANDLER LOGGING ANALYSIS")
    print("=" * 80)
    print(f"Total Python files: {stats['total_files']}")
    print(f"Files with exception handlers: {stats['files_with_exceptions']}")
    print(f"Total exception handlers: {stats['total_exception_handlers']}")
    print(f"Handlers with any logging: {stats['handlers_with_logging']}")
    print(f"Handlers with structured logging: {stats['handlers_with_structured_logging']}")
    print(f"Handlers WITHOUT structured logging: {len(stats['handlers_without_logging'])}")
    print()

    # Print handlers that need structured logging
    if stats['handlers_without_logging']:
        print("=" * 80)
        print("HANDLERS NEEDING STRUCTURED LOGGING")
        print("=" * 80)

        for i, handler in enumerate(stats['handlers_without_logging'][:50], 1):
            rel_path = handler['file'].replace('/home/hudson/blockchain-projects/xai/src/', '')
            print(f"\n{i}. {rel_path}:{handler['line']}")
            print(f"   Exception: {handler['exception_type']}")
            print(f"   Has basic logging: {handler['has_any_logging']}")
            print(f"   Context:")
            for line in handler['context'].split('\n')[:4]:
                if line.strip():
                    print(f"      {line}")

        if len(stats['handlers_without_logging']) > 50:
            print(f"\n... and {len(stats['handlers_without_logging']) - 50} more")

    return stats

if __name__ == '__main__':
    main()
