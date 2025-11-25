#!/usr/bin/env python3
"""Check which source modules are missing tests."""

import os
from pathlib import Path

def check_missing_tests():
    """Check which modules don't have tests."""

    # Get all source modules
    src_modules = []

    # Core modules
    for file in Path("src/xai/core").rglob("*.py"):
        if file.name != "__init__.py" and "node_modules" not in str(file):
            module_name = file.stem
            src_modules.append((module_name, str(file), "core"))

    # Blockchain modules
    for file in Path("src/xai/blockchain").rglob("*.py"):
        if file.name != "__init__.py":
            module_name = file.stem
            src_modules.append((module_name, str(file), "blockchain"))

    # AI modules
    for file in Path("src/xai/ai").rglob("*.py"):
        if file.name != "__init__.py":
            module_name = file.stem
            src_modules.append((module_name, str(file), "ai"))

    # Get all test files
    test_files = []
    for file in Path("tests").rglob("*.py"):
        if file.name.startswith("test_"):
            test_files.append(file.stem)

    # Find modules without tests
    modules_without_tests = []
    modules_with_tests = []

    for module_name, module_path, category in src_modules:
        # Check if any test file contains this module name
        has_test = False
        for test_file in test_files:
            if module_name in test_file.replace("test_", ""):
                has_test = True
                modules_with_tests.append((module_name, category))
                break

        if not has_test:
            modules_without_tests.append((module_name, module_path, category))

    # Write detailed report
    with open("MISSING_TESTS_REPORT.md", "w") as f:
        f.write("# Missing Tests Report\n\n")
        f.write(f"Total source modules analyzed: {len(src_modules)}\n")
        f.write(f"Modules WITH tests: {len(modules_with_tests)}\n")
        f.write(f"Modules WITHOUT tests: {len(modules_without_tests)}\n\n")

        f.write("## Critical Modules Without Tests\n\n")

        # Group by category
        by_category = {}
        for module_name, module_path, category in modules_without_tests:
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((module_name, module_path))

        for category in sorted(by_category.keys()):
            f.write(f"\n### {category.upper()} Modules ({len(by_category[category])} missing tests)\n\n")
            for module_name, module_path in sorted(by_category[category]):
                f.write(f"- **{module_name}**\n")
                f.write(f"  - Path: `{module_path}`\n")
                f.write(f"  - Needs: `tests/xai_tests/unit/test_{module_name}.py` or `test_{module_name}_coverage.py`\n\n")

        f.write("\n## Modules WITH Tests\n\n")
        by_cat_with = {}
        for module_name, category in modules_with_tests:
            if category not in by_cat_with:
                by_cat_with[category] = []
            by_cat_with[category].append(module_name)

        for category in sorted(by_cat_with.keys()):
            f.write(f"\n### {category.upper()} ({len(by_cat_with[category])} modules)\n\n")
            for module_name in sorted(by_cat_with[category]):
                f.write(f"- {module_name}\n")

    # Write blockchain-specific report
    blockchain_modules = [m for m in modules_without_tests if m[2] == "blockchain"]

    with open("BLOCKCHAIN_MODULES_NO_TESTS.txt", "w") as f:
        f.write("BLOCKCHAIN MODULES WITHOUT TESTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total blockchain modules: {len([m for m in src_modules if m[2] == 'blockchain'])}\n")
        f.write(f"Blockchain modules WITHOUT tests: {len(blockchain_modules)}\n\n")

        for module_name, module_path, _ in sorted(blockchain_modules):
            f.write(f"{module_name}\n")
            f.write(f"  -> {module_path}\n\n")

    print(f"Analysis complete!")
    print(f"Total modules: {len(src_modules)}")
    print(f"Modules WITH tests: {len(modules_with_tests)}")
    print(f"Modules WITHOUT tests: {len(modules_without_tests)}")
    print(f"  - Core: {len([m for m in modules_without_tests if m[2] == 'core'])}")
    print(f"  - Blockchain: {len(blockchain_modules)}")
    print(f"  - AI: {len([m for m in modules_without_tests if m[2] == 'ai'])}")

if __name__ == "__main__":
    check_missing_tests()
