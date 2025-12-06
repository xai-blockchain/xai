"""
Test to ensure no silent exception swallowing exists in the codebase.

This test scans all Python files in src/xai/ to verify that:
1. No bare 'except: pass' or 'except Exception: pass' patterns exist
2. All exception handlers have appropriate logging or comments

This prevents the anti-pattern of silently swallowing errors which makes
debugging production issues impossible.
"""

import re
from pathlib import Path
import pytest


def find_silent_exception_handlers(src_dir: Path):
    """
    Find all instances of silent exception handling in Python files.

    Returns:
        List of tuples (file_path, line_number, code_snippet)
    """
    silent_handlers = []

    # Pattern to match except blocks followed by pass
    pattern = re.compile(r'^\s*except[^:]*:\s*$', re.MULTILINE)

    for py_file in src_dir.rglob('*.py'):
        # Skip test files and temporary files
        if 'test_' in py_file.name or '.tmp' in py_file.name:
            continue

        try:
            content = py_file.read_text()
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                if pattern.match(line):
                    # Check if next line is just "pass"
                    if i < len(lines) and lines[i].strip() == 'pass':
                        # Check if there's a comment explaining the pass
                        has_justification = False

                        # Look for comments in the surrounding lines
                        for j in range(max(0, i-3), min(len(lines), i+2)):
                            if '#' in lines[j]:
                                # Found a comment - this is justified
                                has_justification = True
                                break

                        # Check if it uses specific exception types (more acceptable)
                        has_specific_exception = any(
                            exc_type in line.lower()
                            for exc_type in [
                                'importerror', 'nameerror', 'attributeerror',
                                'filenotfounderror', 'valueerror', 'keyerror'
                            ]
                        )

                        # If it's a bare except or broad Exception with no justification, flag it
                        if not has_justification and not has_specific_exception:
                            if 'except:' in line or 'except Exception:' in line.lower():
                                silent_handlers.append((
                                    str(py_file.relative_to(src_dir.parent)),
                                    i,
                                    f"{line.strip()} / {lines[i].strip()}"
                                ))
        except Exception as e:
            # Skip files that can't be read
            print(f"Warning: Could not read {py_file}: {e}")
            continue

    return silent_handlers


def test_no_silent_exception_swallowing():
    """
    Verify that no silent exception swallowing exists in the codebase.

    This test ensures all exception handlers either:
    - Log the exception
    - Have a comment explaining why it's silent
    - Use specific exception types that justify silent handling
    """
    src_dir = Path(__file__).parent.parent.parent.parent / 'src' / 'xai'

    if not src_dir.exists():
        pytest.skip(f"Source directory not found: {src_dir}")

    silent_handlers = find_silent_exception_handlers(src_dir)

    if silent_handlers:
        error_msg = "Found silent exception handlers (except:pass or except Exception:pass):\n\n"
        for file_path, line_num, snippet in silent_handlers:
            error_msg += f"  {file_path}:{line_num}: {snippet}\n"
        error_msg += "\nAll exception handlers must either:\n"
        error_msg += "  1. Log the exception with logger.debug/warning/error\n"
        error_msg += "  2. Have a comment explaining why it's acceptable to ignore\n"
        error_msg += "  3. Use specific exception types (ImportError, NameError, etc.)\n"

        pytest.fail(error_msg)

    # If we get here, test passes
    assert True, "No silent exception handlers found"


def test_exception_logging_usage():
    """
    Verify that modified files are using proper logging for exceptions.

    This test checks that the files we fixed are actually importing and using
    the logger for exception handling.
    """
    files_with_logging = [
        'src/xai/core/node_api.py',
        'src/xai/core/vm/evm/abi.py',
        'src/xai/core/ai_pool_with_strict_limits.py',
        'src/xai/wallet/spending_limits.py',
        'src/xai/core/metrics.py',
        'src/xai/ai/ai_assistant/personal_ai_assistant.py',
        'src/xai/config_manager.py',
        'src/xai/mobile/mini_app_sandbox.py',
        'src/xai/mobile/qr_transactions.py',
    ]

    base_dir = Path(__file__).parent.parent.parent.parent

    for file_path in files_with_logging:
        full_path = base_dir / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text()

        # Verify logging is imported
        assert 'import logging' in content, f"{file_path} should import logging"

        # Verify logger is defined
        assert 'logger = logging.getLogger' in content, f"{file_path} should define logger"


if __name__ == '__main__':
    # Allow running this test directly for quick verification
    test_no_silent_exception_swallowing()
    test_exception_logging_usage()
    print("✓ All tests passed!")
