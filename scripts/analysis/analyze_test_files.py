#!/usr/bin/env python3
"""Analyze all test files in the project."""

import os
from pathlib import Path

def analyze_test_files():
    """Analyze all test files and generate report."""
    test_dir = Path("tests")

    test_files = sorted(test_dir.rglob("*.py"))

    results = []
    total_lines = 0

    for file_path in test_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
                total_lines += line_count

                # Try to extract module being tested
                module_tested = ""
                if "test_" in file_path.name:
                    module_tested = file_path.name.replace("test_", "").replace(".py", "")

                # Get first docstring if available
                description = ""
                for line in lines[:20]:
                    if '"""' in line or "'''" in line:
                        description = line.strip()[:100]
                        break

                file_size = os.path.getsize(file_path)

                results.append({
                    'path': str(file_path),
                    'lines': line_count,
                    'bytes': file_size,
                    'module': module_tested,
                    'description': description
                })
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    # Generate catalog
    with open("EXISTING_TESTS_CATALOG.md", "w") as f:
        f.write("# Existing Test Files Catalog\n\n")
        f.write(f"Total test files: {len(results)}\n")
        f.write(f"Total lines of test code: {total_lines:,}\n\n")

        # Group by directory
        from collections import defaultdict
        by_dir = defaultdict(list)
        for result in results:
            dir_name = str(Path(result['path']).parent)
            by_dir[dir_name].append(result)

        for dir_name in sorted(by_dir.keys()):
            f.write(f"\n## {dir_name}\n\n")
            for result in by_dir[dir_name]:
                f.write(f"### {Path(result['path']).name}\n")
                f.write(f"- **Full path:** `{result['path']}`\n")
                f.write(f"- **Lines:** {result['lines']:,}\n")
                f.write(f"- **Size:** {result['bytes']:,} bytes\n")
                f.write(f"- **Tests module:** {result['module']}\n")
                if result['description']:
                    f.write(f"- **Description:** {result['description']}\n")
                f.write("\n")

    # Generate summary
    coverage_files = [r for r in results if 'coverage' in r['path'].lower()]

    with open("EXISTING_TESTS_SUMMARY.txt", "w") as f:
        f.write("EXISTING TESTS SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total test files found: {len(results)}\n")
        f.write(f"Total lines of test code: {total_lines:,}\n")
        f.write(f"Test files with 'coverage' in name: {len(coverage_files)}\n\n")

        f.write("Test files by category:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Unit tests: {len([r for r in results if 'unit' in r['path']])}\n")
        f.write(f"Integration tests: {len([r for r in results if 'integration' in r['path']])}\n")
        f.write(f"Security tests: {len([r for r in results if 'security' in r['path']])}\n")
        f.write(f"Performance tests: {len([r for r in results if 'performance' in r['path']])}\n")
        f.write(f"E2E tests: {len([r for r in results if 'e2e' in r['path']])}\n")
        f.write(f"Chaos tests: {len([r for r in results if 'chaos' in r['path']])}\n\n")

        f.write("\nCoverage-specific test files:\n")
        f.write("-" * 80 + "\n")
        for cf in coverage_files:
            f.write(f"- {Path(cf['path']).name} ({cf['lines']} lines)\n")

        f.write("\n\nModules with tests:\n")
        f.write("-" * 80 + "\n")
        modules = sorted(set([r['module'] for r in results if r['module']]))
        for module in modules:
            count = len([r for r in results if r['module'] == module])
            f.write(f"- {module}: {count} test file(s)\n")

    print(f"Analysis complete!")
    print(f"Total test files: {len(results)}")
    print(f"Total lines: {total_lines:,}")
    print(f"Coverage files: {len(coverage_files)}")

if __name__ == "__main__":
    analyze_test_files()
