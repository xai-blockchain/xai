"""
XAI Blockchain - Anonymity Fix Script

Automatically fixes critical anonymity issues:
1. Changes genesis timestamp to safe date (Jan 1, 2024)
3. Verifies no identifying information
4. Prepares for anonymous release

"""

import os
import sys
import re
import json

# Safe genesis timestamp (Jan 1, 2024 00:00:00 UTC)
SAFE_GENESIS_TIMESTAMP = 1704067200
OLD_GENESIS_TIMESTAMP = 1730851200  # Nov 6, 2024 (original identifying timestamp)


def fix_timestamp_in_file(file_path, description):
    """Replace genesis timestamp in a file"""
    if not os.path.exists(file_path):
        print(f"[WARN]  {description}: File not found - {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if old timestamp exists
    if str(OLD_GENESIS_TIMESTAMP) not in content:
        print(f"[OK] {description}: Already safe or not applicable")
        return True

    # Replace old timestamp with safe timestamp
    new_content = content.replace(str(OLD_GENESIS_TIMESTAMP), str(SAFE_GENESIS_TIMESTAMP))

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] {description}: Genesis timestamp updated")
    return True


def create_gitignore(auto_yes=False):
    gitignore_content = """# XAI Blockchain - Anonymous Release Configuration

# ============================================================
# CRITICAL: Private wallet files (NEVER COMMIT)
# ============================================================
*PRIVATE*.json
*_YOURS.json
reserved_wallets*.json
premium_wallets_PRIVATE.json
standard_wallets_PRIVATE.json
wallet_claims.json

# Personal notes (NEVER COMMIT)
NOTES.md
TODO_PERSONAL.md
PERSONAL_*.md
*_PERSONAL.*

# ============================================================
# Blockchain data (release separately as ZIP)
# ============================================================
blockchain_data/
checkpoints/
*.dat
*.db

# ============================================================
# Python
# ============================================================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/
*.egg

# ============================================================
# Logs and temporary files
# ============================================================
*.log
logs/
*.tmp
*.temp
*.swp
*.swo
*~

# ============================================================
# OS Files (contain metadata)
# ============================================================
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
desktop.ini

# ============================================================
# IDEs (contain local paths)
# ============================================================
.vscode/
.idea/
*.sublime-project
*.sublime-workspace
.project
.pydevproject
.settings/

# ============================================================
# Environment variables (may contain secrets)
# ============================================================
.env
.env.local
.env.*.local

# ============================================================
# Testing artifacts
# ============================================================
.pytest_cache/
.coverage
htmlcov/
.tox/

# ============================================================
# Package managers
# ============================================================
node_modules/
package-lock.json
yarn.lock

# ============================================================
# Backup files
# ============================================================
*.bak
*.backup
*~

# ============================================================
# Windows
# ============================================================
[Tt]humbs.db
[Ee]hthumbs.db
[Ee]hthumbs_vista.db
*.stackdump
[Dd]esktop.ini
$RECYCLE.BIN/

# ============================================================
# macOS
# ============================================================
.AppleDouble
.LSOverride
Icon
"""


    if os.path.exists(gitignore_path):
        if not auto_yes:
            response = input("   Overwrite? (y/n): ")
            if response.lower() != "y":
                return False
        else:
            print("   Overwriting in auto mode")

    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    return True


def check_for_identifying_info():
    """Scan for potential identifying information"""
    print("\n[SCAN] Scanning for identifying information...")

    issues = []
    warnings = []

    # Check for common identifying patterns
    patterns = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "ip": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "path": r"C:\\Users\\[^\\]+|/Users/[^/]+|/home/[^/]+",
    }

    exclude_patterns = [
        "noreply@protonmail.com",  # Generic example
        "127.0.0.1",  # Localhost
        "0.0.0.0",  # Any address
        "example.com",  # Generic example
        "localhost",  # Localhost
    ]

    # Scan Python and JSON files
    root_dir = os.path.join(os.path.dirname(__file__), "..")

    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
            continue

        for file in files:
            if file.endswith((".py", ".json", ".md")):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for old timestamp
                    if str(OLD_GENESIS_TIMESTAMP) in content:
                        issues.append(f"[CRITICAL] {relative_path}: Contains old genesis timestamp")

                    # Check for patterns
                    for pattern_name, pattern in patterns.items():
                        matches = re.findall(pattern, content)
                        for match in matches:
                            if not any(exclude in match for exclude in exclude_patterns):
                                if pattern_name == "ip":
                                    # IPs are usually OK if they're examples
                                    warnings.append(
                                        f"[WARNING] {relative_path}: Found IP address: {match}"
                                    )
                                else:
                                    warnings.append(
                                        f"[WARNING] {relative_path}: Found {pattern_name}: {match}"
                                    )

                except Exception as e:
                    pass  # Skip files that can't be read

    return issues, warnings


def verify_git_config():

    try:
        import subprocess

        if not os.path.exists(git_dir):
            return True

        result_email = subprocess.run(
        )

        name = result_name.stdout.strip()
        email = result_email.stdout.strip()

        if name != "XAI Developer" or email != "noreply@protonmail.com":
            print(f"   Name: {name}")
            print(f"   Email: {email}")
            print("\n   FIX IT NOW:")
            return False

        return True

    except Exception as e:
        return True


def main(auto_yes=False):
    """Main execution"""
    print("=" * 70)
    print("XAI BLOCKCHAIN - ANONYMITY FIX SCRIPT")
    print("=" * 70)
    print("\nThis script will:")
    print("1. Change genesis timestamp to safe date (Jan 1, 2024)")
    print("3. Scan for identifying information")
    print()

    if not auto_yes:
        response = input("Continue? (y/n): ")
        if response.lower() != "y":
            print("Aborted.")
            return

    print("\n" + "=" * 70)
    print("STEP 1: Fixing Genesis Timestamps")
    print("=" * 70)

    base_dir = os.path.join(os.path.dirname(__file__), "..")

    files_to_fix = [
        (os.path.join(base_dir, "xai-blockchain", "genesis_new.json"), "Genesis block JSON"),
        (os.path.join(base_dir, "scripts", "premine_blockchain.py"), "Pre-mining script"),
        (
            os.path.join(base_dir, "scripts", "generate_early_adopter_wallets.py"),
            "Wallet generation script",
        ),
    ]

    for file_path, description in files_to_fix:
        fix_timestamp_in_file(file_path, description)

    print("\n" + "=" * 70)
    print("=" * 70)

    create_gitignore(auto_yes=auto_yes)

    print("\n" + "=" * 70)
    print("STEP 3: Scanning for Identifying Information")
    print("=" * 70)

    issues, warnings = check_for_identifying_info()

    if issues:
        print("\n[CRITICAL] CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n[OK] No critical issues found")

    if warnings:
        print("\n[WARNING] WARNINGS (review these):")
        for warning in warnings[:10]:  # Show first 10
            print(f"   {warning}")
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more")
    else:
        print("\n[OK] No warnings")

    verify_git_config()

    print("\n" + "=" * 70)
    print("ANONYMITY FIX COMPLETE")
    print("=" * 70)

    if issues:
        print("\n[CRITICAL] STATUS: CRITICAL ISSUES REMAIN")
        print("   Review and fix issues above before release")
    elif warnings:
        print("\n[WARNING] STATUS: REVIEW WARNINGS")
        print("   Most warnings are OK, but review them")
    else:
        print("\n[OK] STATUS: READY FOR ANONYMOUS RELEASE")
        print("   Remember:")
        print("   - Never commit *PRIVATE*.json files")

    print("\nSee ANONYMITY_COMPLIANCE_AUDIT.md for full checklist")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import sys

    auto_yes = "--auto" in sys.argv or "-y" in sys.argv
    main(auto_yes=auto_yes)
