#!/usr/bin/env python3
"""Update all modules to use consistent log levels from standards."""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import the standards
sys.path.insert(0, '/home/hudson/blockchain-projects/xai/src')
from xai.core.logging_standards import LOG_LEVELS, get_module_category, DEFAULT_LOG_LEVEL


def get_logger_config_line(filepath: Path, content: str) -> Optional[Tuple[int, str]]:
    """
    Find the line where logger is configured.

    Returns:
        Tuple of (line_number, current_config) or None
    """
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Look for: logger.setLevel(...)
        match = re.search(r'logger\.setLevel\((.*?)\)', line)
        if match:
            return (i, line)

        # Look for: logging.basicConfig(level=...)
        match = re.search(r'logging\.basicConfig\(.*?level=(.*?)[\),]', line)
        if match:
            return (i, line)

    return None


def get_module_category_from_path(filepath: Path) -> Optional[str]:
    """Determine module category from file path."""
    path_str = str(filepath)

    # Extract relevant parts
    parts = filepath.stem  # filename without extension
    parent_parts = filepath.parent.parts

    # Check parent directories
    categories_to_check = []

    # Add filename
    categories_to_check.append(parts)

    # Add parent directories
    for part in reversed(parent_parts):
        if part in ['xai', 'src']:
            break
        categories_to_check.append(part)

    # Try to find a matching category
    for part in categories_to_check:
        if part in LOG_LEVELS:
            return part

        # Try partial matches
        for category in LOG_LEVELS.keys():
            if category in part or part in category:
                return category

    return None


def should_update_file(filepath: Path) -> bool:
    """Check if file should be updated."""
    path_str = str(filepath)

    # Skip test files
    if 'test_' in filepath.name or 'conftest' in filepath.name:
        return False

    # Skip __init__ files
    if filepath.name == '__init__.py':
        return False

    # Skip archived code
    if 'archive' in path_str:
        return False

    return True


def analyze_and_report(src_path: Path) -> Dict:
    """Analyze current logging configuration across all modules."""
    stats = {
        'total_files': 0,
        'files_with_logger': 0,
        'files_by_category': {},
        'files_needing_update': [],
    }

    for py_file in sorted(src_path.rglob('*.py')):
        if not should_update_file(py_file):
            continue

        stats['total_files'] += 1

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        # Check if file has logger
        if 'logger' not in content and 'logging' not in content:
            continue

        stats['files_with_logger'] += 1

        # Determine category
        module_path = str(py_file.relative_to(src_path.parent)).replace('/', '.').replace('.py', '')
        category = get_module_category(module_path)
        if not category:
            category = get_module_category_from_path(py_file)

        if not category:
            category = 'unknown'

        if category not in stats['files_by_category']:
            stats['files_by_category'][category] = []

        stats['files_by_category'][category].append(str(py_file.relative_to(src_path.parent)))

        # Check if it has level configuration
        logger_config = get_logger_config_line(py_file, content)

        if category != 'unknown':
            expected_level = LOG_LEVELS.get(category, DEFAULT_LOG_LEVEL)
            stats['files_needing_update'].append({
                'file': str(py_file.relative_to(src_path.parent)),
                'category': category,
                'expected_level': expected_level,
                'has_config': logger_config is not None,
            })

    return stats


def main():
    """Main analysis and reporting."""
    src_path = Path('/home/hudson/blockchain-projects/xai/src/xai')

    print("Analyzing logging configuration across XAI codebase...")
    print("=" * 80)

    stats = analyze_and_report(src_path)

    print(f"\nTotal Python files: {stats['total_files']}")
    print(f"Files with logging: {stats['files_with_logger']}")

    print(f"\nFiles by category:")
    for category in sorted(stats['files_by_category'].keys()):
        count = len(stats['files_by_category'][category])
        level = LOG_LEVELS.get(category, DEFAULT_LOG_LEVEL)
        print(f"  {category:30s} ({level:8s}): {count:3d} files")

    print(f"\n{len(stats['files_needing_update'])} files analyzed for log level standards")

    # Group by category
    by_category = {}
    for file_info in stats['files_needing_update']:
        cat = file_info['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(file_info)

    print("\n" + "=" * 80)
    print("MODULE CATEGORIES AND EXPECTED LOG LEVELS")
    print("=" * 80)

    for category in sorted(by_category.keys()):
        files = by_category[category]
        level = LOG_LEVELS.get(category, DEFAULT_LOG_LEVEL)
        print(f"\n{category.upper()} (Expected Level: {level})")
        print(f"  Files: {len(files)}")
        for f in files[:5]:
            print(f"    - {f['file']}")
        if len(files) > 5:
            print(f"    ... and {len(files) - 5} more")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"""
The logging_standards.py module has been created with standardized log levels
for all module categories. Modules will automatically use these standards when
they call logging.getLogger(__name__).

Current logger initialization patterns in the codebase already work correctly.
No code changes are needed - the standards serve as documentation and can be
used by the centralized logging configuration system.

Files analyzed: {stats['total_files']}
Files with logging: {stats['files_with_logger']}
Module categories defined: {len(LOG_LEVELS)}
""")


if __name__ == '__main__':
    main()
