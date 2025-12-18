"""
Test CLI entry points are properly configured and callable.

Verifies that pip entry points (xai, xai-wallet, xai-node) work correctly.
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


def test_xai_entry_point_exists():
    """Verify xai command is available after installation."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.cli.main", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "XAI Blockchain CLI" in result.stdout or "XAI wallet utilities" in result.stdout


def test_xai_wallet_entry_point_exists():
    """Verify xai-wallet command is available after installation."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.wallet.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "XAI wallet utilities" in result.stdout


def test_xai_node_entry_point_exists():
    """Verify xai-node command is available after installation."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.core.node", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "XAI Blockchain Node" in result.stdout


def test_xai_cli_has_main_function():
    """Verify xai.cli.main has a main() function."""
    from xai.cli.main import main

    assert callable(main)


def test_xai_wallet_cli_has_main_function():
    """Verify xai.wallet.cli has a main() function."""
    from xai.wallet.cli import main

    assert callable(main)


def test_xai_node_has_main_function():
    """Verify xai.core.node has a main() function."""
    from xai.core.node import main

    assert callable(main)


def test_pyproject_toml_has_entry_points(project_root):
    """Verify pyproject.toml contains the correct entry points."""
    pyproject_path = project_root / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check all three entry points are defined
    assert '[project.scripts]' in content, "[project.scripts] section not found"
    assert 'xai = "xai.cli.main:main"' in content, "xai entry point not found"
    assert 'xai-wallet = "xai.wallet.cli:main"' in content, "xai-wallet entry point not found"
    assert 'xai-node = "xai.core.node:main"' in content, "xai-node entry point not found"


def test_xai_cli_help_contains_commands():
    """Verify xai CLI shows command groups."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.cli.main", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0

    # Check for expected command groups (if using enhanced CLI)
    # or wallet utilities (if using legacy CLI)
    output = result.stdout
    assert (
        "Commands:" in output
        or "positional arguments:" in output
        or "wallet" in output.lower()
    )


def test_xai_wallet_help_contains_subcommands():
    """Verify xai-wallet CLI shows subcommands."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.wallet.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    output = result.stdout

    # Check for key wallet subcommands
    assert "generate-address" in output
    assert "request-faucet" in output
    assert "balance" in output
    assert "send" in output


def test_xai_node_help_contains_options():
    """Verify xai-node CLI shows configuration options."""
    result = subprocess.run(
        [sys.executable, "-m", "xai.core.node", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    output = result.stdout

    # Check for key node options
    assert "--port" in output
    assert "--host" in output
    assert "--miner" in output
    assert "--data-dir" in output


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / ".venv" / "bin" / "xai").exists(),
    reason="Package not installed in venv",
)
def test_installed_xai_command_works(project_root):
    """Test that installed xai command works (requires pip install -e .)."""
    venv_python = project_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        pytest.skip("Virtualenv not found")

    result = subprocess.run(
        [str(venv_python), "-c", "import sys; from xai.cli.main import main; sys.exit(main())"],
        capture_output=True,
        text=True,
        timeout=10,
        env={"PYTHONPATH": str(project_root / "src")},
    )

    # Command should run (may exit with error code but shouldn't crash)
    assert result.returncode in (0, 2), f"Unexpected exit code: {result.returncode}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
