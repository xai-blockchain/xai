from __future__ import annotations

"""
Security test to ensure no hardcoded credentials in source code.

This test scans the codebase for common credential patterns that should
never be committed to source control.
"""

import os
import re
from pathlib import Path

import pytest

def get_source_files() -> list[Path]:
    """Get all Python source files in the src/xai directory."""
    src_dir = Path(__file__).parent.parent.parent.parent / "src" / "xai"
    python_files = []

    for path in src_dir.rglob("*.py"):
        # Skip __pycache__ directories
        if "__pycache__" in str(path):
            continue
        python_files.append(path)

    return python_files

def scan_file_for_credentials(file_path: Path) -> list[tuple[int, str, str]]:
    """
    Scan a file for hardcoded credentials.

    Returns:
        List of tuples (line_number, pattern_name, matching_line)
    """
    issues = []

    # Patterns to detect hardcoded credentials
    # These patterns look for actual API keys, not the blacklist definitions
    patterns = {
        "anthropic_api_key": r'(?:api_key|user_api_key)\s*=\s*["\']sk-ant-api03-[^"\']+["\']',
        "openai_api_key": r'(?:api_key|user_api_key)\s*=\s*["\']sk-[A-Za-z0-9]{20,}["\']',
        "aws_access_key": r'(?:aws_access_key_id|AWS_ACCESS_KEY_ID)\s*=\s*["\']AKIA[0-9A-Z]{16}["\']',
        "generic_bearer_token": r'(?:token|bearer|authorization)\s*=\s*["\']Bearer [A-Za-z0-9\-._~+/]+=*["\']',
        "github_token": r'(?:github_token|GITHUB_TOKEN)\s*=\s*["\']ghp_[A-Za-z0-9]{36}["\']',
        "generic_api_key": r'(?:api_key|API_KEY)\s*=\s*["\'][A-Za-z0-9]{32,}["\']',
    }

    # Exception: Allow these patterns in specific contexts
    exceptions = [
        "INVALID_DEMO_KEYS",  # The blacklist of demo keys
        "FORBIDDEN_PATTERNS",  # Security pattern lists
        "test_validate_api_key",  # Test functions
        "# Example:",  # Documentation examples
        "# Blacklist",  # Comment explaining blacklist
        "SECURITY:",  # Security comments
    ]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            # Skip lines with exceptions
            if any(exc in line for exc in exceptions):
                continue

            # Skip comments (but not all, in case credentials are in comments)
            stripped = line.strip()
            if stripped.startswith("#") and "SECURITY" not in stripped:
                continue

            # Check each pattern
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((line_num, pattern_name, line.strip()))

    except Exception as e:
        pytest.fail(f"Error scanning {file_path}: {e}")

    return issues

def test_no_hardcoded_api_keys():
    """
    Test that no hardcoded API keys exist in source code.

    This is a critical security test - hardcoded credentials should NEVER
    be committed to source control. All secrets must be loaded from
    environment variables.
    """
    source_files = get_source_files()
    assert len(source_files) > 0, "No source files found to scan"

    all_issues = {}

    for file_path in source_files:
        issues = scan_file_for_credentials(file_path)
        if issues:
            all_issues[file_path] = issues

    # Report all findings
    if all_issues:
        error_msg = "\n\n🚨 SECURITY VIOLATION: Hardcoded credentials detected!\n\n"
        for file_path, issues in all_issues.items():
            error_msg += f"\nFile: {file_path.relative_to(file_path.parent.parent.parent.parent)}\n"
            for line_num, pattern_name, line in issues:
                error_msg += f"  Line {line_num}: [{pattern_name}] {line}\n"

        error_msg += "\n❌ All credentials must be loaded from environment variables.\n"
        error_msg += "   Use: os.environ.get('API_KEY_NAME')\n"

        pytest.fail(error_msg)

def test_environment_variable_usage():
    """
    Test that demo scripts properly use environment variables for API keys.

    This verifies that the main demonstration scripts have been updated to
    load credentials from the environment.
    """
    # Files that should use environment variables for API keys
    critical_files = [
        "src/xai/core/ai_trading_bot.py",
        "src/xai/core/secure_api_key_manager.py",
        "src/xai/core/ai_pool_with_strict_limits.py",
    ]

    project_root = Path(__file__).parent.parent.parent.parent

    for file_rel_path in critical_files:
        file_path = project_root / file_rel_path

        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should use os.environ for API keys
        assert "os.environ.get" in content, (
            f"{file_rel_path} should use os.environ.get() for API keys"
        )

        # Should have ANTHROPIC_API_KEY
        assert "ANTHROPIC_API_KEY" in content, (
            f"{file_rel_path} should reference ANTHROPIC_API_KEY environment variable"
        )

def test_no_placeholder_api_keys():
    """
    Test that placeholder strings like 'YOUR_API_KEY_HERE' are not used in code.

    Exception: The INVALID_DEMO_KEYS blacklist is allowed to contain these
    as part of the security validation.
    """
    source_files = get_source_files()

    placeholder_patterns = [
        "YOUR_ANTHROPIC_API_KEY_HERE",
        "YOUR_API_KEY_HERE",
        "YOUR_OPENAI_API_KEY",
        "REPLACE_WITH_YOUR_KEY",
        "INSERT_API_KEY_HERE",
    ]

    issues = []

    for file_path in source_files:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            # Skip the INVALID_DEMO_KEYS list - that's the blacklist
            if "INVALID_DEMO_KEYS" in line or "# SECURITY:" in line:
                continue

            # Skip comments explaining the blacklist
            if line.strip().startswith("#") and "blacklist" in line.lower():
                continue

            for placeholder in placeholder_patterns:
                # Look for actual usage, not in blacklist or comments
                if placeholder in line:
                    # Skip if it's in the blacklist definition
                    if f'"{placeholder}"' in line and "INVALID_DEMO_KEYS" not in file_path.name:
                        # This is a potential issue - placeholder used as actual value
                        if "api_key=" in line or "user_api_key=" in line:
                            issues.append((file_path, line_num, line.strip()))

    if issues:
        error_msg = "\n\n🚨 Placeholder API keys found in code!\n\n"
        for file_path, line_num, line in issues:
            error_msg += f"{file_path}:{line_num}\n  {line}\n"
        error_msg += "\nUse environment variables instead.\n"
        pytest.fail(error_msg)

def test_env_file_not_committed():
    """
    Test that .env files with potential secrets are not in the repository.

    .env files should be in .gitignore and never committed.
    """
    project_root = Path(__file__).parent.parent.parent.parent

    # Check for .env files in common locations
    env_file_locations = [
        project_root / ".env",
        project_root / "src" / ".env",
        project_root / "src" / "xai" / ".env",
    ]

    for env_file in env_file_locations:
        if env_file.exists():
            # Check if it contains actual secrets (not just templates)
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for patterns that suggest real credentials
            if re.search(r'sk-[A-Za-z0-9]{20,}', content):
                pytest.fail(
                    f"🚨 .env file with potential secrets found: {env_file}\n"
                    f".env files should never be committed to git!"
                )

def test_gitignore_includes_env():
    """
    Test that .gitignore properly excludes .env files.
    """
    project_root = Path(__file__).parent.parent.parent.parent
    gitignore_path = project_root / ".gitignore"

    if not gitignore_path.exists():
        pytest.skip(".gitignore not found")
        return

    with open(gitignore_path, "r", encoding="utf-8") as f:
        gitignore_content = f.read()

    # .env should be in .gitignore
    assert ".env" in gitignore_content or "*.env" in gitignore_content, (
        ".gitignore should include .env files to prevent credential leaks"
    )

def test_api_key_validation_function_exists():
    """
    Test that API key validation exists to reject demo/placeholder keys.
    """
    ai_trading_bot_path = (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "xai"
        / "core"
        / "ai_trading_bot.py"
    )

    if not ai_trading_bot_path.exists():
        pytest.skip("ai_trading_bot.py not found")
        return

    with open(ai_trading_bot_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Should have validation function
    assert "validate_api_key" in content, (
        "API key validation function should exist"
    )

    # Should have demo key blacklist
    assert "INVALID_DEMO_KEYS" in content, (
        "Demo key blacklist should exist"
    )

if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v"])
