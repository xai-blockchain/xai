#!/usr/bin/env python3
"""
Quick script to fix broad exception handlers in SDK client files.
Replaces 'except Exception as e:' with specific exception types.
"""

import re
from pathlib import Path

SDK_CLIENT_DIR = Path("src/xai/sdk/python/xai_sdk/clients")

def fix_sdk_client(filepath: Path):
    """Fix exception handlers in an SDK client file."""
    content = filepath.read_text()
    original = content

    # Pattern 1: except Exception as e: raise CustomError(...) - add re-raise and specific types
    # Look for the pattern but preserve the custom error type
    pattern1 = r'(\s+)except Exception as e:\s*\n\s+raise (\w+Error)\(f"([^"]+): \{str\(e\)\}"\)'

    def replacement1(match):
        indent = match.group(1)
        error_type = match.group(2)
        message = match.group(3)
        return f'''{indent}except {error_type}:
{indent}    raise
{indent}except (KeyError, ValueError, TypeError) as e:
{indent}    raise {error_type}(f"{message}: {{str(e)}}") from e'''

    content = re.sub(pattern1, replacement1, content)

    if content != original:
        filepath.write_text(content)
        print(f"Fixed {filepath.name}")
        return True
    return False

def main():
    if not SDK_CLIENT_DIR.exists():
        print(f"Directory not found: {SDK_CLIENT_DIR}")
        return

    fixed = 0
    for filepath in SDK_CLIENT_DIR.glob("*.py"):
        if filepath.name == "__init__.py":
            continue
        if fix_sdk_client(filepath):
            fixed += 1

    print(f"\nFixed {fixed} files")

if __name__ == "__main__":
    main()
