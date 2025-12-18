"""Unit tests for CLI tooling modules."""

from __future__ import annotations

import argparse
from unittest.mock import Mock, patch

import pytest

from xai.wallet import cli as wallet_cli


# Note: TestXaiNodeCLI was removed as it tested obsolete internal functions
# (_node_run, _node_status, _node_sync) that no longer exist in the Click-based CLI.
# The enhanced CLI is now properly tested in test_cli_commands.py using subprocess
# to test the actual CLI entry points.


class TestWalletCLI:
    def test_generate_address_outputs_json(self, capsys):
        wallet = Mock(address="XAI1", public_key="PUB", private_key="PRIV")
        with patch.object(wallet_cli, "Wallet", return_value=wallet), \
             patch("builtins.input", return_value="SHOW JSON"):
            args = argparse.Namespace(json=True)
            result = wallet_cli._generate_address(args)

        assert result == 0
        captured = capsys.readouterr()
        assert '"address": "XAI1"' in captured.out

    def test_generate_address_json_cancelled(self, capsys):
        """Test that cancelling the JSON output confirmation works."""
        wallet = Mock(address="XAI1", public_key="PUB", private_key="PRIV")
        with patch.object(wallet_cli, "Wallet", return_value=wallet), \
             patch("builtins.input", return_value="NO"):
            args = argparse.Namespace(json=True)
            result = wallet_cli._generate_address(args)

        assert result == 1  # Should return error code
        captured = capsys.readouterr()
        assert "Cancelled" in captured.err

