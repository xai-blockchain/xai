"""Unit tests for CLI tooling modules."""

from __future__ import annotations

import argparse
from unittest.mock import Mock, patch

import pytest

from xai.cli import main as cli_main
from xai.wallet import cli as wallet_cli


class TestXaiNodeCLI:
    def test_node_run_starts_node(self):
        args = argparse.Namespace(host="0.0.0.0", port=9000, miner="XAI123", peer=["http://peer1"], debug=False)

        with patch.object(cli_main, "Blockchain") as MockBlockchain, patch.object(
            cli_main, "BlockchainNode"
        ) as MockNode:
            mock_node = Mock()
            MockNode.return_value = mock_node

            result = cli_main._node_run(args)

        assert result == 0
        MockNode.assert_called_once_with(
            blockchain=MockBlockchain.return_value,
            host="0.0.0.0",
            port=9000,
            miner_address="XAI123",
        )
        mock_node.add_peer.assert_any_call("http://peer1")
        mock_node.run.assert_called_once_with(debug=False)

    def test_node_status_success_text(self, capsys):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "blockchain": {"height": 10},
            "services": {"api": "running"},
        }

        with patch.object(cli_main.requests, "get", return_value=mock_response):
            args = argparse.Namespace(base_url="http://localhost:18545", timeout=1.0, json=False)
            result = cli_main._node_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "healthy" in captured.out

    def test_node_sync_json_output(self, capsys):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"synced": True, "chain_length": 42}

        with patch.object(cli_main.requests, "post", return_value=mock_response):
            args = argparse.Namespace(base_url="http://localhost:18545", timeout=2.0, json=True)
            result = cli_main._node_sync(args)

        assert result == 0
        captured = capsys.readouterr()
        assert '"synced": true' in captured.out.lower()


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

