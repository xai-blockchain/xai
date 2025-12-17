"""CLI integration tests for hardware wallet commands.

Tests the hw-address, hw-sign, hw-verify, and hw-send CLI commands
using the mock hardware wallet for automated testing.
"""

import json
import os
import subprocess
import sys
from unittest import mock

import pytest


CLI_MODULE = "xai.wallet.cli"


@pytest.fixture
def mock_hw_env():
    """Environment enabling mock hardware wallet."""
    env = os.environ.copy()
    env["XAI_ALLOW_MOCK_HARDWARE_WALLET"] = "1"
    env["XAI_HARDWARE_WALLET_ENABLED"] = "1"
    env["XAI_HARDWARE_WALLET_PROVIDER"] = "mock"
    return env


class TestHwAddressCommand:
    """Tests for hw-address subcommand."""

    def test_hw_address_requires_device_flag(self):
        """hw-address without --ledger or --trezor should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-address"],
            capture_output=True,
            text=True,
        )
        # Should fail because no device specified
        assert result.returncode != 0

    def test_hw_address_ledger_missing_dependency(self):
        """hw-address --ledger fails gracefully without ledgerblue."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-address", "--ledger"],
            capture_output=True,
            text=True,
        )
        # Should fail with helpful message about missing dependency
        assert result.returncode != 0
        assert "ledger" in result.stderr.lower() or "pip install" in result.stderr.lower()

    def test_hw_address_trezor_missing_dependency(self):
        """hw-address --trezor fails gracefully without trezorlib."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-address", "--trezor"],
            capture_output=True,
            text=True,
        )
        # Should fail with helpful message about missing dependency
        assert result.returncode != 0
        assert "trezor" in result.stderr.lower() or "pip install" in result.stderr.lower()


class TestHwSignCommand:
    """Tests for hw-sign subcommand."""

    def test_hw_sign_requires_device_flag(self):
        """hw-sign without device flag should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-sign", "--message", "test"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


class TestHwVerifyCommand:
    """Tests for hw-verify subcommand."""

    def test_hw_verify_requires_device_flag(self):
        """hw-verify without device flag should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-verify"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


class TestHwSendCommand:
    """Tests for hw-send subcommand."""

    def test_hw_send_requires_device_flag(self):
        """hw-send without device flag should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-send",
             "--recipient", "XAI1234567890abcdef1234567890abcdef12345678",
             "--amount", "1.0"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0

    def test_hw_send_requires_recipient(self):
        """hw-send without --recipient should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-send", "--ledger", "--amount", "1.0"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "recipient" in result.stderr.lower() or "required" in result.stderr.lower()

    def test_hw_send_requires_amount(self):
        """hw-send without --amount should fail."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-send", "--ledger",
             "--recipient", "XAI1234567890abcdef1234567890abcdef12345678"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "amount" in result.stderr.lower() or "required" in result.stderr.lower()


class TestCliHelpOutput:
    """Tests for CLI help messages."""

    def test_main_help_includes_hw_commands(self):
        """Main help should list hardware wallet commands."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "hw-address" in result.stdout
        assert "hw-send" in result.stdout

    def test_hw_address_help(self):
        """hw-address --help should work."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-address", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--ledger" in result.stdout
        assert "--trezor" in result.stdout

    def test_hw_send_help(self):
        """hw-send --help should show all options."""
        result = subprocess.run(
            [sys.executable, "-m", CLI_MODULE, "hw-send", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--recipient" in result.stdout
        assert "--amount" in result.stdout
        assert "--ledger" in result.stdout
        assert "hardware wallet" in result.stdout.lower()


class TestParserConstruction:
    """Tests that parser builds correctly."""

    def test_build_parser_succeeds(self):
        """Parser construction should not raise."""
        from xai.wallet.cli import build_parser
        parser = build_parser()
        assert parser is not None

    def test_parser_has_hw_subcommands(self):
        """Parser should have all hw-* subcommands."""
        from xai.wallet.cli import build_parser
        parser = build_parser()

        # Parse help to check subcommands exist
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1

        choices = subparsers_actions[0].choices
        assert "hw-address" in choices
        assert "hw-sign" in choices
        assert "hw-verify" in choices
        assert "hw-send" in choices


import argparse  # needed for TestParserConstruction
