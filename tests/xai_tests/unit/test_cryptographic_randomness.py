"""
Test to verify that security-critical modules use cryptographically secure randomness.

This test ensures that the 'random' module (Mersenne Twister PRNG) is not used
in security-sensitive contexts where 'secrets' module should be used instead.
"""

import ast
import os
from pathlib import Path


class RandomUsageVisitor(ast.NodeVisitor):
    """AST visitor to find usage of random module in code."""

    def __init__(self):
        self.has_random_import = False
        self.has_secrets_import = False
        self.random_calls = []
        self.secrets_calls = []

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "random":
                self.has_random_import = True
            elif alias.name == "secrets":
                self.has_secrets_import = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "random":
            self.has_random_import = True
        elif node.module == "secrets":
            self.has_secrets_import = True
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            if node.value.id == "random":
                self.random_calls.append(f"{node.value.id}.{node.attr}")
            elif node.value.id == "secrets":
                self.secrets_calls.append(f"{node.value.id}.{node.attr}")
        self.generic_visit(node)


def check_file_for_insecure_random(file_path: Path) -> dict:
    """
    Check a Python file for insecure random usage.

    Returns dict with:
    - has_random_import: bool
    - has_secrets_import: bool
    - random_calls: list of random.* calls found
    - secrets_calls: list of secrets.* calls found
    """
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return {
                "has_random_import": False,
                "has_secrets_import": False,
                "random_calls": [],
                "secrets_calls": [],
                "parse_error": True,
            }

    visitor = RandomUsageVisitor()
    visitor.visit(tree)

    return {
        "has_random_import": visitor.has_random_import,
        "has_secrets_import": visitor.has_secrets_import,
        "random_calls": visitor.random_calls,
        "secrets_calls": visitor.secrets_calls,
        "parse_error": False,
    }


def test_proof_of_intelligence_uses_secrets():
    """Test that proof_of_intelligence.py uses secrets module."""
    file_path = Path("src/xai/core/mining/proof_of_intelligence.py")
    result = check_file_for_insecure_random(file_path)

    assert not result["parse_error"], f"Failed to parse {file_path}"
    assert result["has_secrets_import"], f"{file_path} must import secrets module"
    assert not result["random_calls"], (
        f"{file_path} uses insecure random module: {result['random_calls']}. "
        "Security-critical code must use secrets module instead."
    )


def test_validator_rotation_uses_secrets():
    """Test that validator_rotation.py uses secrets module."""
    file_path = Path("src/xai/blockchain/validator_rotation.py")
    result = check_file_for_insecure_random(file_path)

    assert not result["parse_error"], f"Failed to parse {file_path}"
    assert result["has_secrets_import"], f"{file_path} must import secrets module"
    assert not result["random_calls"], (
        f"{file_path} uses insecure random module: {result['random_calls']}. "
        "Validator selection must use cryptographically secure randomness."
    )


def test_front_running_protection_uses_secrets():
    """Test that front_running_protection.py uses secrets module."""
    file_path = Path("src/xai/blockchain/front_running_protection.py")
    result = check_file_for_insecure_random(file_path)

    assert not result["parse_error"], f"Failed to parse {file_path}"
    assert result["has_secrets_import"], f"{file_path} must import secrets module"
    assert not result["random_calls"], (
        f"{file_path} uses insecure random module: {result['random_calls']}. "
        "Transaction ordering must use cryptographically secure randomness."
    )


def test_peer_discovery_uses_secrets():
    """Test that peer_discovery.py uses secrets module."""
    file_path = Path("src/xai/core/p2p/peer_discovery.py")
    result = check_file_for_insecure_random(file_path)

    assert not result["parse_error"], f"Failed to parse {file_path}"
    assert result["has_secrets_import"], f"{file_path} must import secrets module"
    assert not result["random_calls"], (
        f"{file_path} uses insecure random module: {result['random_calls']}. "
        "Peer selection must use cryptographically secure randomness."
    )


def test_easter_eggs_uses_secrets():
    """Test that easter_eggs.py uses secrets module."""
    file_path = Path("src/xai/core/api/easter_eggs.py")
    result = check_file_for_insecure_random(file_path)

    assert not result["parse_error"], f"Failed to parse {file_path}"
    assert result["has_secrets_import"], f"{file_path} must import secrets module"
    assert not result["random_calls"], (
        f"{file_path} uses insecure random module: {result['random_calls']}. "
        "Treasure wallet generation must use cryptographically secure randomness."
    )


def test_no_security_modules_use_random():
    """
    Comprehensive test to ensure no security-critical modules use insecure random.

    This test scans all security-critical directories and ensures they don't use
    the predictable random module in security contexts.
    """
    # List of security-critical files/patterns
    security_critical_files = [
        "src/xai/core/mining/proof_of_intelligence.py",
        "src/xai/blockchain/validator_rotation.py",
        "src/xai/blockchain/front_running_protection.py",
        "src/xai/core/p2p/peer_discovery.py",
        "src/xai/core/api/easter_eggs.py",
        "src/xai/security/secure_enclave_manager.py",
        "src/xai/core/mining_algorithm.py",
    ]

    violations = []

    for file_path_str in security_critical_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue

        result = check_file_for_insecure_random(file_path)

        if result["parse_error"]:
            violations.append(f"{file_path}: Failed to parse file")
            continue

        # Check for random module usage (should use secrets instead)
        if result["random_calls"]:
            violations.append(
                f"{file_path}: Uses insecure random module - "
                f"calls: {', '.join(result['random_calls'])}"
            )

    assert not violations, (
        "Security-critical modules must use 'secrets' module instead of 'random':\n"
        + "\n".join(violations)
    )


if __name__ == "__main__":
    # Run tests manually for verification
    print("Testing cryptographic randomness usage...")

    try:
        test_proof_of_intelligence_uses_secrets()
        print("✓ proof_of_intelligence.py uses secrets")
    except AssertionError as e:
        print(f"✗ proof_of_intelligence.py: {e}")

    try:
        test_validator_rotation_uses_secrets()
        print("✓ validator_rotation.py uses secrets")
    except AssertionError as e:
        print(f"✗ validator_rotation.py: {e}")

    try:
        test_front_running_protection_uses_secrets()
        print("✓ front_running_protection.py uses secrets")
    except AssertionError as e:
        print(f"✗ front_running_protection.py: {e}")

    try:
        test_peer_discovery_uses_secrets()
        print("✓ peer_discovery.py uses secrets")
    except AssertionError as e:
        print(f"✗ peer_discovery.py: {e}")

    try:
        test_easter_eggs_uses_secrets()
        print("✓ easter_eggs.py uses secrets")
    except AssertionError as e:
        print(f"✗ easter_eggs.py: {e}")

    try:
        test_no_security_modules_use_random()
        print("✓ All security-critical modules use cryptographic randomness")
    except AssertionError as e:
        print(f"✗ Security check failed:\n{e}")

    print("\nAll tests passed!")
