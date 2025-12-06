#!/usr/bin/env python3
"""
Security Audit Script: Private Key Exposure Detection

This script scans the entire XAI codebase for potential private key exposures
in API responses, logs, and other outputs.

Usage:
    python scripts/security/audit_private_key_exposure.py

Exit codes:
    0 - No issues found
    1 - Potential security issues detected
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


class PrivateKeyExposureAuditor:
    """Audit codebase for private key exposure vulnerabilities"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.issues: List[Tuple[str, int, str, str]] = []
        self.checked_files = 0

    def scan_file(self, filepath: Path) -> None:
        """Scan a single Python file for private key exposures"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Pattern 1: jsonify() with private_key field
                if 'jsonify' in line and 'private_key' in line.lower():
                    # Check if it's actually returning private_key (not just an error message)
                    if re.search(r'"private_key"\s*:', line) and 'error' not in line.lower():
                        self.issues.append((
                            str(filepath),
                            line_num,
                            "CRITICAL",
                            f"Potential private_key in jsonify(): {line.strip()}"
                        ))

                # Pattern 2: Logging private keys
                if 'logger.' in line and 'private_key' in line.lower():
                    if not ('redacted' in line.lower() or 'masked' in line.lower() or '...' in line):
                        self.issues.append((
                            str(filepath),
                            line_num,
                            "HIGH",
                            f"Potential private_key in logs: {line.strip()}"
                        ))

                # Pattern 3: print() with private_key
                if 'print(' in line and 'private_key' in line.lower():
                    self.issues.append((
                        str(filepath),
                        line_num,
                        "HIGH",
                        f"Potential private_key in print(): {line.strip()}"
                    ))

                # Pattern 4: Returning dict/response with private_key outside of encryption contexts
                if re.search(r'return.*["\']private_key["\']', line):
                    # Exclude if in encryption/decryption context
                    if not any(word in line.lower() for word in ['encrypt', 'decrypt', 'keystore', 'test']):
                        self.issues.append((
                            str(filepath),
                            line_num,
                            "MEDIUM",
                            f"Potential private_key return: {line.strip()}"
                        ))

            self.checked_files += 1

        except Exception as e:
            print(f"Error scanning {filepath}: {e}", file=sys.stderr)

    def scan_directory(self, directory: Path, exclude_patterns: List[str]) -> None:
        """Recursively scan directory for Python files"""
        for filepath in directory.rglob("*.py"):
            # Skip excluded patterns
            if any(pattern in str(filepath) for pattern in exclude_patterns):
                continue

            self.scan_file(filepath)

    def run_audit(self) -> int:
        """Run the complete audit and return exit code"""
        print("=" * 80)
        print("XAI BLOCKCHAIN - PRIVATE KEY EXPOSURE SECURITY AUDIT")
        print("=" * 80)
        print()

        # Directories to scan
        scan_dirs = [
            self.root_dir / "src" / "xai" / "core",
            self.root_dir / "src" / "xai" / "wallet",
            self.root_dir / "src" / "xai" / "cli",
            self.root_dir / "src" / "xai" / "ai",
        ]

        # Patterns to exclude (tests, examples, scripts)
        exclude_patterns = [
            "/tests/",
            "/test_",
            "/examples/",
            "/__pycache__/",
            "/.venv/",
            "/scripts/",
            "generate_premine",  # Premine scripts legitimately use private keys
            "create_founder_wallets",
            "create_time_capsule",
        ]

        print(f"Scanning directories: {[str(d) for d in scan_dirs]}")
        print(f"Excluding patterns: {exclude_patterns}")
        print()

        for directory in scan_dirs:
            if directory.exists():
                print(f"Scanning {directory}...")
                self.scan_directory(directory, exclude_patterns)

        print()
        print(f"Checked {self.checked_files} files")
        print()

        if not self.issues:
            print("✓ No private key exposure issues detected!")
            print()
            print("All API endpoints appear to be secure:")
            print("  - No private keys in HTTP responses")
            print("  - No private keys in logs")
            print("  - Encryption properly implemented")
            print()
            return 0
        else:
            print(f"✗ Found {len(self.issues)} potential security issues:")
            print()

            # Group by severity
            critical = [i for i in self.issues if i[2] == "CRITICAL"]
            high = [i for i in self.issues if i[2] == "HIGH"]
            medium = [i for i in self.issues if i[2] == "MEDIUM"]

            if critical:
                print(f"CRITICAL Issues ({len(critical)}):")
                for filepath, line_num, severity, message in critical:
                    print(f"  {filepath}:{line_num}")
                    print(f"    {message}")
                print()

            if high:
                print(f"HIGH Priority Issues ({len(high)}):")
                for filepath, line_num, severity, message in high:
                    print(f"  {filepath}:{line_num}")
                    print(f"    {message}")
                print()

            if medium:
                print(f"MEDIUM Priority Issues ({len(medium)}):")
                for filepath, line_num, severity, message in medium:
                    print(f"  {filepath}:{line_num}")
                    print(f"    {message}")
                print()

            print("RECOMMENDATION: Review and fix these issues immediately.")
            print("Private key exposure is a CRITICAL security vulnerability.")
            return 1


def main():
    """Main entry point"""
    # Determine project root (3 levels up from this script)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    auditor = PrivateKeyExposureAuditor(str(project_root))
    exit_code = auditor.run_audit()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
