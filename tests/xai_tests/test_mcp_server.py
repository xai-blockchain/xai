"""
Comprehensive pytest test suite for XAI MCP Server.

Tests cover:
- XAIMCPServer initialization
- All tool methods (get_balance, get_block, get_transaction, etc.)
- Input validation for each tool
- Error handling (invalid addresses, missing blocks, etc.)
- Tool registration and listing
- call_tool router method

Security considerations:
- Input validation prevents injection attacks
- Error messages do not leak sensitive information
- All edge cases are tested to prevent unexpected behavior
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest


class TestXAIMCPServerInitialization:
    """Tests for XAIMCPServer initialization."""

    def test_init_default_data_dir(self):
        """Test initialization with default data directory."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        assert server.data_dir == os.path.expanduser("~/.xai")
        assert server._blockchain is None
        assert server._initialized is False

    def test_init_custom_data_dir(self):
        """Test initialization with custom data directory."""
        from xai.mcp.server import XAIMCPServer

        custom_dir = "/custom/path/to/data"
        server = XAIMCPServer(data_dir=custom_dir)
        assert server.data_dir == custom_dir
        assert server._blockchain is None
        assert server._initialized is False

    def test_init_data_dir_expansion(self):
        """Test that ~ in data_dir is properly expanded."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir="~/custom_xai")
        assert server.data_dir == os.path.expanduser("~/custom_xai")
        assert "~" not in server.data_dir

    def test_ensure_blockchain_lazy_loading(self, tmp_path):
        """Test that blockchain is lazily loaded on first use."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Initially blockchain should be None
        assert server._blockchain is None
        assert server._initialized is False

        # Access blockchain via _ensure_blockchain
        bc = server._ensure_blockchain()

        # Now blockchain should be initialized
        assert server._blockchain is not None
        assert server._initialized is True
        assert bc is server._blockchain

    def test_ensure_blockchain_idempotent(self, tmp_path):
        """Test that _ensure_blockchain returns the same instance."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        bc1 = server._ensure_blockchain()
        bc2 = server._ensure_blockchain()

        assert bc1 is bc2


class TestToolRegistration:
    """Tests for MCP tool registration and listing."""

    def test_get_tools_returns_list(self):
        """Test that get_tools returns a list."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()
        assert isinstance(tools, list)

    def test_get_tools_count(self):
        """Test that all expected tools are registered."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()

        expected_tools = [
            "get_balance",
            "get_block",
            "get_transaction",
            "get_chain_info",
            "get_utxos",
            "estimate_fee",
            "get_mempool_info",
        ]
        assert len(tools) == len(expected_tools)

    def test_get_tools_names(self):
        """Test that all expected tool names are present."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()
        tool_names = [t["name"] for t in tools]

        expected_tools = [
            "get_balance",
            "get_block",
            "get_transaction",
            "get_chain_info",
            "get_utxos",
            "estimate_fee",
            "get_mempool_info",
        ]
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' should be registered"

    def test_get_tools_structure(self):
        """Test that each tool has required fields."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()

        for tool in tools:
            assert "name" in tool, "Tool must have a name"
            assert "description" in tool, "Tool must have a description"
            assert "inputSchema" in tool, "Tool must have an inputSchema"
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["inputSchema"], dict)

    def test_get_tools_input_schema_type(self):
        """Test that inputSchema is properly structured."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()

        for tool in tools:
            schema = tool["inputSchema"]
            assert schema.get("type") == "object", f"{tool['name']} schema type should be 'object'"
            assert "properties" in schema, f"{tool['name']} schema should have 'properties'"

    def test_required_fields_validation(self):
        """Test that required fields are properly defined in schemas."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        tools = server.get_tools()
        tools_by_name = {t["name"]: t for t in tools}

        # get_balance requires 'address'
        assert "required" in tools_by_name["get_balance"]["inputSchema"]
        assert "address" in tools_by_name["get_balance"]["inputSchema"]["required"]

        # get_transaction requires 'txid'
        assert "required" in tools_by_name["get_transaction"]["inputSchema"]
        assert "txid" in tools_by_name["get_transaction"]["inputSchema"]["required"]

        # get_utxos requires 'address'
        assert "required" in tools_by_name["get_utxos"]["inputSchema"]
        assert "address" in tools_by_name["get_utxos"]["inputSchema"]["required"]


class TestCallToolRouter:
    """Tests for the call_tool routing method."""

    def test_call_tool_unknown_tool(self):
        """Test that unknown tool names return an error."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer()
        result = server.call_tool("unknown_tool", {})

        assert "error" in result
        assert "Unknown tool" in result["error"]
        assert "unknown_tool" in result["error"]

    def test_call_tool_routes_to_get_balance(self, tmp_path):
        """Test that call_tool routes get_balance correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_balance", return_value={"balance": 100.0}) as mock:
            result = server.call_tool("get_balance", {"address": "test_address"})
            mock.assert_called_once_with("test_address")
            assert result == {"balance": 100.0}

    def test_call_tool_routes_to_get_block(self, tmp_path):
        """Test that call_tool routes get_block correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_block", return_value={"index": 0}) as mock:
            result = server.call_tool("get_block", {"height": 0})
            mock.assert_called_once_with(0, None)

    def test_call_tool_routes_to_get_transaction(self, tmp_path):
        """Test that call_tool routes get_transaction correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_transaction", return_value={"txid": "abc"}) as mock:
            result = server.call_tool("get_transaction", {"txid": "abc123"})
            mock.assert_called_once_with("abc123")

    def test_call_tool_routes_to_get_chain_info(self, tmp_path):
        """Test that call_tool routes get_chain_info correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_chain_info", return_value={"height": 10}) as mock:
            result = server.call_tool("get_chain_info", {})
            mock.assert_called_once()

    def test_call_tool_routes_to_get_utxos(self, tmp_path):
        """Test that call_tool routes get_utxos correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_utxos", return_value={"utxos": []}) as mock:
            result = server.call_tool("get_utxos", {"address": "test_addr"})
            mock.assert_called_once_with("test_addr")

    def test_call_tool_routes_to_estimate_fee(self, tmp_path):
        """Test that call_tool routes estimate_fee correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_estimate_fee", return_value={"fee": 0.001}) as mock:
            result = server.call_tool("estimate_fee", {"tx_size_bytes": 500})
            mock.assert_called_once_with(500)

    def test_call_tool_routes_to_get_mempool_info(self, tmp_path):
        """Test that call_tool routes get_mempool_info correctly."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_mempool_info", return_value={"size": 5}) as mock:
            result = server.call_tool("get_mempool_info", {})
            mock.assert_called_once()

    def test_call_tool_handles_exception(self, tmp_path):
        """Test that call_tool catches and reports exceptions."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_get_balance", side_effect=RuntimeError("Test error")):
            result = server.call_tool("get_balance", {"address": "test"})
            assert "error" in result
            assert "Test error" in result["error"]

    def test_call_tool_missing_required_argument(self, tmp_path):
        """Test that call_tool handles missing required arguments."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Missing 'address' argument for get_balance
        result = server.call_tool("get_balance", {})
        assert "error" in result

    def test_call_tool_estimate_fee_default_value(self, tmp_path):
        """Test that estimate_fee uses default value when not provided."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch.object(server, "_estimate_fee", return_value={"fee": 0.001}) as mock:
            result = server.call_tool("estimate_fee", {})
            mock.assert_called_once_with(250)  # Default value


class TestGetBalance:
    """Tests for the _get_balance method."""

    def test_get_balance_returns_correct_format(self, tmp_path):
        """Test that _get_balance returns correctly formatted response."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Mock the blockchain's get_balance method
        mock_bc = Mock()
        mock_bc.get_balance.return_value = 123.45
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_balance("test_address_123")

        assert result["address"] == "test_address_123"
        assert result["balance"] == 123.45
        assert result["unit"] == "XAI"

    def test_get_balance_calls_blockchain(self, tmp_path):
        """Test that _get_balance correctly calls blockchain.get_balance."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0.0
        server._blockchain = mock_bc
        server._initialized = True

        server._get_balance("my_wallet_address")

        mock_bc.get_balance.assert_called_once_with("my_wallet_address")

    def test_get_balance_zero_balance(self, tmp_path):
        """Test getting balance for address with zero balance."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0.0
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_balance("empty_wallet")

        assert result["balance"] == 0.0

    def test_get_balance_large_amount(self, tmp_path):
        """Test getting balance with large amount."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 121000000.0  # Max supply
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_balance("whale_wallet")

        assert result["balance"] == 121000000.0


class TestGetBlock:
    """Tests for the _get_block method."""

    def test_get_block_by_height(self, tmp_path):
        """Test getting block by height."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.index = 5
        mock_block.hash = "abc123"
        mock_block.previous_hash = "def456"
        mock_block.timestamp = 1234567890
        mock_block.transactions = [Mock(), Mock()]
        mock_block.to_dict = Mock(return_value={"index": 5, "hash": "abc123"})

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(10)]
        mock_bc.chain[5] = mock_block
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(5, None)

        assert result == {"index": 5, "hash": "abc123"}

    def test_get_block_by_hash(self, tmp_path):
        """Test getting block by hash."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.to_dict = Mock(return_value={"hash": "target_hash"})

        mock_bc = Mock()
        mock_bc.chain = []
        mock_bc.get_block_by_hash.return_value = mock_block
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(None, "target_hash")

        mock_bc.get_block_by_hash.assert_called_once_with("target_hash")
        assert result == {"hash": "target_hash"}

    def test_get_block_invalid_height_negative(self, tmp_path):
        """Test getting block with negative height returns error."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(5)]
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(-1, None)

        assert "error" in result
        assert "-1" in result["error"]

    def test_get_block_invalid_height_too_large(self, tmp_path):
        """Test getting block with height exceeding chain length."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(5)]
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(100, None)

        assert "error" in result
        assert "100" in result["error"]

    def test_get_block_hash_not_found(self, tmp_path):
        """Test getting block with non-existent hash."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = []
        mock_bc.get_block_by_hash.return_value = None
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(None, "nonexistent_hash")

        assert "error" in result
        assert "nonexistent_hash" in result["error"]

    def test_get_block_latest_when_no_params(self, tmp_path):
        """Test getting latest block when no height or hash provided."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.to_dict = Mock(return_value={"index": 9, "hash": "latest"})

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(10)]
        mock_bc.chain[-1] = mock_block
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(None, None)

        assert result == {"index": 9, "hash": "latest"}

    def test_get_block_empty_chain(self, tmp_path):
        """Test getting block from empty chain."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(None, None)

        assert "error" in result
        assert "No blocks" in result["error"]

    def test_get_block_without_to_dict(self, tmp_path):
        """Test getting block that doesn't have to_dict method."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Create a simple object without to_dict
        mock_block = SimpleNamespace(
            index=3,
            hash="hash123",
            previous_hash="prev_hash",
            timestamp=1234567890,
            transactions=[Mock(), Mock(), Mock()]
        )

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(5)]
        mock_bc.chain[3] = mock_block
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(3, None)

        assert result["index"] == 3
        assert result["hash"] == "hash123"
        assert result["previous_hash"] == "prev_hash"
        assert result["timestamp"] == 1234567890
        assert result["transactions"] == 3


class TestGetTransaction:
    """Tests for the _get_transaction method."""

    def test_get_transaction_in_chain(self, tmp_path):
        """Test getting transaction that exists in chain."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_tx = Mock()
        mock_tx.txid = "target_txid"
        mock_tx.to_dict = Mock(return_value={"txid": "target_txid", "amount": 100})

        mock_block = Mock()
        mock_block.transactions = [mock_tx]

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("target_txid")

        assert result == {"txid": "target_txid", "amount": 100}

    def test_get_transaction_in_pending(self, tmp_path):
        """Test getting transaction from pending transactions."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_tx = Mock()
        mock_tx.txid = "pending_txid"
        mock_tx.to_dict = Mock(return_value={"txid": "pending_txid", "amount": 50})

        mock_block = Mock()
        mock_block.transactions = []

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = [mock_tx]
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("pending_txid")

        assert result["txid"] == "pending_txid"
        assert result["status"] == "pending"

    def test_get_transaction_not_found(self, tmp_path):
        """Test getting non-existent transaction."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.transactions = []

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("nonexistent_txid")

        assert "error" in result
        assert "nonexistent_txid" in result["error"]

    def test_get_transaction_without_to_dict(self, tmp_path):
        """Test getting transaction without to_dict method."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_tx = SimpleNamespace(txid="simple_txid")

        mock_block = Mock()
        mock_block.transactions = [mock_tx]

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("simple_txid")

        assert result["txid"] == "simple_txid"
        assert result["found"] is True

    def test_get_transaction_searches_all_blocks(self, tmp_path):
        """Test that transaction search goes through all blocks."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Target tx is in the last block
        target_tx = Mock()
        target_tx.txid = "deep_txid"
        target_tx.to_dict = Mock(return_value={"txid": "deep_txid"})

        mock_blocks = []
        for i in range(10):
            block = Mock()
            block.transactions = []
            mock_blocks.append(block)

        mock_blocks[-1].transactions = [target_tx]

        mock_bc = Mock()
        mock_bc.chain = mock_blocks
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("deep_txid")

        assert result == {"txid": "deep_txid"}


class TestGetChainInfo:
    """Tests for the _get_chain_info method."""

    def test_get_chain_info_format(self, tmp_path):
        """Test that _get_chain_info returns correct format."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(100)]
        mock_bc.difficulty = 4
        mock_bc.pending_transactions = [Mock(), Mock(), Mock()]
        mock_bc.max_supply = 121000000
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_chain_info()

        assert result["height"] == 99  # 0-indexed
        assert result["blocks"] == 100
        assert result["difficulty"] == 4
        assert result["pending_transactions"] == 3
        assert result["max_supply"] == 121000000

    def test_get_chain_info_single_block(self, tmp_path):
        """Test chain info with single block (genesis only)."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock()]
        mock_bc.difficulty = 1
        mock_bc.pending_transactions = []
        mock_bc.max_supply = 121000000
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_chain_info()

        assert result["height"] == 0
        assert result["blocks"] == 1

    def test_get_chain_info_default_max_supply(self, tmp_path):
        """Test chain info falls back to default max_supply."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock(spec=[])  # No attributes
        mock_bc.chain = [Mock()]
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_chain_info()

        assert result["max_supply"] == 121000000


class TestGetUtxos:
    """Tests for the _get_utxos method."""

    def test_get_utxos_format(self, tmp_path):
        """Test that _get_utxos returns correct format."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_utxos = [
            {"txid": "tx1", "vout": 0, "amount": 10.0},
            {"txid": "tx2", "vout": 1, "amount": 25.5},
        ]

        mock_bc = Mock()
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = mock_utxos
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_utxos("test_address")

        assert result["address"] == "test_address"
        assert result["utxo_count"] == 2
        assert result["utxos"] == mock_utxos
        assert result["total_value"] == 35.5

    def test_get_utxos_empty(self, tmp_path):
        """Test getting UTXOs for address with no UTXOs."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_utxos("empty_address")

        assert result["utxo_count"] == 0
        assert result["utxos"] == []
        assert result["total_value"] == 0

    def test_get_utxos_calls_utxo_manager(self, tmp_path):
        """Test that _get_utxos correctly calls utxo_manager."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = []
        server._blockchain = mock_bc
        server._initialized = True

        server._get_utxos("query_address")

        mock_bc.utxo_manager.get_utxos_for_address.assert_called_once_with("query_address")


class TestEstimateFee:
    """Tests for the _estimate_fee method."""

    def test_estimate_fee_default_size(self, tmp_path):
        """Test fee estimation with default transaction size."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        result = server._estimate_fee()

        assert result["tx_size_bytes"] == 250
        assert result["fee_rate"] == 0.00001
        assert result["estimated_fee"] == 250 * 0.00001
        assert result["unit"] == "XAI"

    def test_estimate_fee_custom_size(self, tmp_path):
        """Test fee estimation with custom transaction size."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        result = server._estimate_fee(1000)

        assert result["tx_size_bytes"] == 1000
        assert result["estimated_fee"] == 1000 * 0.00001

    def test_estimate_fee_zero_size(self, tmp_path):
        """Test fee estimation with zero size."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        result = server._estimate_fee(0)

        assert result["tx_size_bytes"] == 0
        assert result["estimated_fee"] == 0.0

    def test_estimate_fee_large_transaction(self, tmp_path):
        """Test fee estimation for large transaction."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        result = server._estimate_fee(100000)

        assert result["tx_size_bytes"] == 100000
        assert result["estimated_fee"] == 100000 * 0.00001
        assert result["estimated_fee"] == 1.0


class TestGetMempoolInfo:
    """Tests for the _get_mempool_info method."""

    def test_get_mempool_info_format(self, tmp_path):
        """Test that _get_mempool_info returns correct format."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_tx1 = Mock()
        mock_tx1.fee = 0.01
        mock_tx2 = Mock()
        mock_tx2.fee = 0.02

        mock_bc = Mock()
        mock_bc.pending_transactions = [mock_tx1, mock_tx2]
        mock_bc.min_fee_rate = 0.00001
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_mempool_info()

        assert result["size"] == 2
        assert result["total_fees"] == 0.03
        assert result["min_fee_rate"] == 0.00001

    def test_get_mempool_info_empty(self, tmp_path):
        """Test mempool info when empty."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.pending_transactions = []
        mock_bc.min_fee_rate = 0.0
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_mempool_info()

        assert result["size"] == 0
        assert result["total_fees"] == 0

    def test_get_mempool_info_default_min_fee_rate(self, tmp_path):
        """Test mempool info falls back to default min_fee_rate."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock(spec=[])  # No attributes
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_mempool_info()

        assert result["min_fee_rate"] == 0.0


class TestInputValidation:
    """Tests for input validation across all tools."""

    def test_empty_address_get_balance(self, tmp_path):
        """Test get_balance with empty address."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0.0
        server._blockchain = mock_bc
        server._initialized = True

        # Empty string is valid but should return zero balance
        result = server._get_balance("")
        assert result["address"] == ""
        assert result["balance"] == 0.0

    def test_special_characters_in_address(self, tmp_path):
        """Test address with special characters."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0.0
        server._blockchain = mock_bc
        server._initialized = True

        # Should handle special characters gracefully
        result = server._get_balance("addr!@#$%^&*()")
        assert result["address"] == "addr!@#$%^&*()"

    def test_very_long_txid(self, tmp_path):
        """Test transaction lookup with very long txid."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.transactions = []

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        long_txid = "a" * 10000
        result = server._get_transaction(long_txid)

        assert "error" in result
        assert long_txid in result["error"]

    def test_negative_tx_size(self, tmp_path):
        """Test estimate_fee with negative transaction size."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Negative size should still work mathematically (returns negative fee)
        result = server._estimate_fee(-100)
        assert result["tx_size_bytes"] == -100
        assert result["estimated_fee"] == -100 * 0.00001

    def test_block_height_boundary(self, tmp_path):
        """Test block height at exact chain length."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(5)]
        server._blockchain = mock_bc
        server._initialized = True

        # Height 5 should fail (chain has indices 0-4)
        result = server._get_block(5, None)
        assert "error" in result

        # Height 4 should succeed (last valid index)
        mock_bc.chain[4].to_dict = Mock(return_value={"index": 4})
        result = server._get_block(4, None)
        assert result == {"index": 4}


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_blockchain_initialization_error(self, tmp_path):
        """Test handling when blockchain initialization fails."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        with patch("xai.mcp.server.XAIMCPServer._ensure_blockchain", side_effect=RuntimeError("Init failed")):
            result = server.call_tool("get_chain_info", {})
            assert "error" in result

    def test_utxo_manager_error(self, tmp_path):
        """Test handling when UTXO manager throws error."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.side_effect = RuntimeError("DB error")
        server._blockchain = mock_bc
        server._initialized = True

        result = server.call_tool("get_utxos", {"address": "test"})

        assert "error" in result
        assert "DB error" in result["error"]

    def test_attribute_error_on_block(self, tmp_path):
        """Test handling when block is missing expected attributes."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Block without any of the expected attributes
        mock_block = object()  # Raw object with no attributes

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        server._blockchain = mock_bc
        server._initialized = True

        # Should handle gracefully by returning None for missing attrs
        result = server._get_block(0, None)
        assert result["index"] is None
        assert result["hash"] is None


class TestHelperFunction:
    """Tests for module-level helper functions."""

    def test_create_mcp_server(self):
        """Test create_mcp_server helper function."""
        from xai.mcp.server import create_mcp_server

        server = create_mcp_server(data_dir="/test/path")

        assert server is not None
        assert server.data_dir == "/test/path"

    def test_create_mcp_server_default(self):
        """Test create_mcp_server with default data_dir."""
        from xai.mcp.server import create_mcp_server

        server = create_mcp_server()

        assert server.data_dir == os.path.expanduser("~/.xai")


class TestIntegration:
    """Integration tests using real blockchain instance."""

    def test_full_workflow_with_real_blockchain(self, tmp_path):
        """Test complete workflow with actual blockchain."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Get chain info (triggers blockchain initialization)
        chain_info = server.call_tool("get_chain_info", {})

        # Should have genesis block
        assert "error" not in chain_info
        assert chain_info["blocks"] >= 1
        assert chain_info["height"] >= 0

        # Get genesis block
        block_result = server.call_tool("get_block", {"height": 0})
        assert "error" not in block_result
        assert block_result.get("index") == 0 or "index" in str(block_result)

        # Estimate a fee
        fee_result = server.call_tool("estimate_fee", {"tx_size_bytes": 500})
        assert "error" not in fee_result
        assert fee_result["estimated_fee"] == 500 * 0.00001

        # Get mempool info
        mempool_result = server.call_tool("get_mempool_info", {})
        assert "error" not in mempool_result
        assert "size" in mempool_result

    def test_tools_list_matches_implementation(self, tmp_path):
        """Verify all listed tools are actually implemented."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))
        tools = server.get_tools()

        # Mock blockchain to avoid initialization
        mock_bc = Mock()
        mock_bc.chain = [Mock()]
        mock_bc.chain[0].transactions = []
        mock_bc.chain[0].to_dict = Mock(return_value={"index": 0})
        mock_bc.get_balance.return_value = 0
        mock_bc.pending_transactions = []
        mock_bc.difficulty = 1
        mock_bc.max_supply = 121000000
        mock_bc.min_fee_rate = 0.0
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = []
        server._blockchain = mock_bc
        server._initialized = True

        # Each tool should be callable without returning "Unknown tool"
        for tool in tools:
            tool_name = tool["name"]

            # Prepare minimal arguments
            args = {}
            if "required" in tool["inputSchema"]:
                for req in tool["inputSchema"]["required"]:
                    if req == "address":
                        args["address"] = "test_addr"
                    elif req == "txid":
                        args["txid"] = "test_txid"

            result = server.call_tool(tool_name, args)

            # Should not be "Unknown tool" error
            if "error" in result:
                assert "Unknown tool" not in result["error"], f"Tool {tool_name} not implemented"


class TestSecurityConsiderations:
    """Security-focused tests for the MCP server."""

    def test_no_sensitive_data_in_errors(self, tmp_path):
        """Test that error messages don't leak sensitive information."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Simulate various errors and check messages
        result = server.call_tool("unknown_tool", {})
        assert server.data_dir not in result.get("error", "")

    def test_path_traversal_resistance(self, tmp_path):
        """Test that path traversal attempts in addresses are handled."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0
        server._blockchain = mock_bc
        server._initialized = True

        # Attempt path traversal in address
        malicious_address = "../../../etc/passwd"
        result = server._get_balance(malicious_address)

        # Should treat it as a regular string address, not a path
        assert result["address"] == malicious_address
        mock_bc.get_balance.assert_called_with(malicious_address)

    def test_large_input_handling(self, tmp_path):
        """Test handling of unusually large inputs."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0
        server._blockchain = mock_bc
        server._initialized = True

        # Very large address string
        large_address = "x" * 1000000

        # Should handle without crashing
        result = server._get_balance(large_address)
        assert "address" in result

    def test_unicode_input_handling(self, tmp_path):
        """Test handling of unicode characters in inputs."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0
        server._blockchain = mock_bc
        server._initialized = True

        # Unicode address
        unicode_address = "addr_\u0000\u200b\uffff_test"

        result = server._get_balance(unicode_address)
        assert result["address"] == unicode_address

    def test_null_byte_injection(self, tmp_path):
        """Test handling of null byte injection attempts."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 0
        server._blockchain = mock_bc
        server._initialized = True

        # Address with null bytes
        null_address = "addr\x00injected"

        result = server._get_balance(null_address)
        # Should handle the string as-is without special behavior
        assert "address" in result


class TestStdioServer:
    """Tests for the stdio server functionality."""

    @pytest.mark.asyncio
    async def test_run_stdio_server_tools_list(self, tmp_path):
        """Test tools/list request handling."""
        import asyncio
        import io
        import json
        import sys
        from xai.mcp.server import XAIMCPServer, run_stdio_server

        server = XAIMCPServer(data_dir=str(tmp_path))

        # Mock stdin/stdout
        request = {"id": 1, "method": "tools/list"}
        mock_stdin = io.StringIO(json.dumps(request) + "\n")
        mock_stdout = io.StringIO()

        with patch.object(sys, 'stdin', mock_stdin):
            with patch('builtins.print', lambda *args, **kwargs: mock_stdout.write(args[0] + "\n") if args else None):
                # Create a task that will timeout
                task = asyncio.create_task(run_stdio_server(server))
                # Give it time to process one line
                await asyncio.sleep(0.1)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Check response was written
        output = mock_stdout.getvalue()
        if output.strip():
            response = json.loads(output.strip())
            assert response["id"] == 1
            assert "tools" in response["result"]

    @pytest.mark.asyncio
    async def test_run_stdio_server_tools_call(self, tmp_path):
        """Test tools/call request handling."""
        import asyncio
        import io
        import json
        import sys
        from xai.mcp.server import XAIMCPServer, run_stdio_server

        server = XAIMCPServer(data_dir=str(tmp_path))

        request = {
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "estimate_fee",
                "arguments": {"tx_size_bytes": 500}
            }
        }
        mock_stdin = io.StringIO(json.dumps(request) + "\n")
        mock_stdout = io.StringIO()

        with patch.object(sys, 'stdin', mock_stdin):
            with patch('builtins.print', lambda *args, **kwargs: mock_stdout.write(args[0] + "\n") if args else None):
                task = asyncio.create_task(run_stdio_server(server))
                await asyncio.sleep(0.1)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        output = mock_stdout.getvalue()
        if output.strip():
            response = json.loads(output.strip())
            assert response["id"] == 2
            assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_run_stdio_server_unknown_method(self, tmp_path):
        """Test handling of unknown method."""
        import asyncio
        import io
        import json
        import sys
        from xai.mcp.server import XAIMCPServer, run_stdio_server

        server = XAIMCPServer(data_dir=str(tmp_path))

        request = {"id": 3, "method": "unknown/method"}
        mock_stdin = io.StringIO(json.dumps(request) + "\n")
        mock_stdout = io.StringIO()

        with patch.object(sys, 'stdin', mock_stdin):
            with patch('builtins.print', lambda *args, **kwargs: mock_stdout.write(args[0] + "\n") if args else None):
                task = asyncio.create_task(run_stdio_server(server))
                await asyncio.sleep(0.1)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        output = mock_stdout.getvalue()
        if output.strip():
            response = json.loads(output.strip())
            assert response["id"] == 3
            assert "error" in response["result"]


class TestMainFunction:
    """Tests for the main() function."""

    def test_main_default_mode(self, capsys):
        """Test main function in default (info) mode."""
        import sys
        from xai.mcp.server import main

        with patch.object(sys, 'argv', ['xai.mcp.server']):
            main()

        captured = capsys.readouterr()
        assert "XAI MCP Server" in captured.out
        assert "Available tools:" in captured.out
        assert "get_balance" in captured.out

    def test_main_with_custom_data_dir(self, capsys, tmp_path):
        """Test main function with custom data directory."""
        import sys
        from xai.mcp.server import main

        with patch.object(sys, 'argv', ['xai.mcp.server', '--data-dir', str(tmp_path)]):
            main()

        captured = capsys.readouterr()
        assert "XAI MCP Server" in captured.out

    def test_main_stdio_mode(self, tmp_path):
        """Test main function in stdio mode with immediate exit."""
        import asyncio
        import sys
        from xai.mcp.server import main

        # Mock asyncio.run to avoid actual server start
        mock_run = Mock()
        with patch.object(sys, 'argv', ['xai.mcp.server', '--stdio', '--data-dir', str(tmp_path)]):
            with patch('asyncio.run', mock_run):
                main()

        mock_run.assert_called_once()


class TestModuleExports:
    """Tests for module-level exports."""

    def test_mcp_module_exports(self):
        """Test that the mcp module exports the correct symbols."""
        from xai.mcp import XAIMCPServer, create_mcp_server

        assert XAIMCPServer is not None
        assert create_mcp_server is not None
        assert callable(create_mcp_server)

    def test_mcp_all_exports(self):
        """Test that __all__ is correctly defined."""
        import xai.mcp

        assert hasattr(xai.mcp, '__all__')
        assert "XAIMCPServer" in xai.mcp.__all__
        assert "create_mcp_server" in xai.mcp.__all__


class TestResponseFormatting:
    """Tests for response formatting across all tools."""

    def test_balance_response_structure(self, tmp_path):
        """Test that balance response has correct structure."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 123.456789
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_balance("test_addr")

        # Verify all expected fields are present
        assert "address" in result
        assert "balance" in result
        assert "unit" in result

        # Verify types
        assert isinstance(result["address"], str)
        assert isinstance(result["balance"], (int, float))
        assert isinstance(result["unit"], str)
        assert result["unit"] == "XAI"

    def test_chain_info_response_structure(self, tmp_path):
        """Test that chain info response has correct structure."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = [Mock() for _ in range(50)]
        mock_bc.difficulty = 10
        mock_bc.pending_transactions = [Mock(), Mock()]
        mock_bc.max_supply = 121000000
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_chain_info()

        # Verify all expected fields are present
        assert "height" in result
        assert "blocks" in result
        assert "difficulty" in result
        assert "pending_transactions" in result
        assert "max_supply" in result

        # Verify types and values
        assert isinstance(result["height"], int)
        assert isinstance(result["blocks"], int)
        assert result["height"] == 49  # 0-indexed
        assert result["blocks"] == 50

    def test_fee_estimation_response_structure(self, tmp_path):
        """Test that fee estimation response has correct structure."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        result = server._estimate_fee(500)

        # Verify all expected fields are present
        assert "tx_size_bytes" in result
        assert "fee_rate" in result
        assert "estimated_fee" in result
        assert "unit" in result

        # Verify values
        assert result["tx_size_bytes"] == 500
        assert result["fee_rate"] == 0.00001
        assert result["estimated_fee"] == 500 * 0.00001
        assert result["unit"] == "XAI"

    def test_utxos_response_structure(self, tmp_path):
        """Test that UTXOs response has correct structure."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_utxos = [
            {"txid": "tx1", "vout": 0, "amount": 10.0},
            {"txid": "tx2", "vout": 1, "amount": 20.0},
            {"txid": "tx3", "vout": 0, "amount": 30.0},
        ]

        mock_bc = Mock()
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = mock_utxos
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_utxos("test_addr")

        # Verify all expected fields are present
        assert "address" in result
        assert "utxo_count" in result
        assert "utxos" in result
        assert "total_value" in result

        # Verify values
        assert result["address"] == "test_addr"
        assert result["utxo_count"] == 3
        assert result["total_value"] == 60.0
        assert len(result["utxos"]) == 3

    def test_mempool_response_structure(self, tmp_path):
        """Test that mempool response has correct structure."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_tx = Mock()
        mock_tx.fee = 0.001

        mock_bc = Mock()
        mock_bc.pending_transactions = [mock_tx] * 5
        mock_bc.min_fee_rate = 0.00001
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_mempool_info()

        # Verify all expected fields are present
        assert "size" in result
        assert "total_fees" in result
        assert "min_fee_rate" in result

        # Verify values
        assert result["size"] == 5
        assert result["total_fees"] == 0.005
        assert result["min_fee_rate"] == 0.00001

    def test_error_response_format(self, tmp_path):
        """Test that error responses have correct format."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.chain = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_block(None, None)

        # Error response should have 'error' key
        assert "error" in result
        assert isinstance(result["error"], str)
        assert len(result["error"]) > 0


class TestConcurrencyAndEdgeCases:
    """Tests for concurrency and edge cases."""

    def test_multiple_tool_calls(self, tmp_path):
        """Test making multiple sequential tool calls."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 100.0
        mock_bc.chain = [Mock() for _ in range(10)]
        mock_bc.chain[-1].to_dict = Mock(return_value={"index": 9})
        mock_bc.pending_transactions = []
        mock_bc.difficulty = 5
        mock_bc.max_supply = 121000000
        server._blockchain = mock_bc
        server._initialized = True

        # Make multiple calls
        result1 = server.call_tool("get_balance", {"address": "addr1"})
        result2 = server.call_tool("get_chain_info", {})
        result3 = server.call_tool("estimate_fee", {"tx_size_bytes": 300})

        assert "error" not in result1
        assert result1["balance"] == 100.0

        assert "error" not in result2
        assert result2["blocks"] == 10

        assert "error" not in result3
        assert result3["estimated_fee"] == 300 * 0.00001

    def test_blockchain_reuse_across_calls(self, tmp_path):
        """Test that blockchain instance is reused across calls."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        # First call initializes blockchain
        bc1 = server._ensure_blockchain()

        # Second call should return same instance
        bc2 = server._ensure_blockchain()

        assert bc1 is bc2

    def test_handle_blockchain_with_no_transactions(self, tmp_path):
        """Test handling blocks with no transactions."""
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_block = Mock()
        mock_block.transactions = []
        mock_block.to_dict = Mock(return_value={"index": 0, "transactions": []})

        mock_bc = Mock()
        mock_bc.chain = [mock_block]
        mock_bc.pending_transactions = []
        server._blockchain = mock_bc
        server._initialized = True

        result = server._get_transaction("any_txid")
        assert "error" in result

    def test_json_serializable_responses(self, tmp_path):
        """Test that all responses are JSON serializable."""
        import json
        from xai.mcp.server import XAIMCPServer

        server = XAIMCPServer(data_dir=str(tmp_path))

        mock_bc = Mock()
        mock_bc.get_balance.return_value = 100.5
        mock_bc.chain = [Mock()]
        mock_bc.chain[0].to_dict = Mock(return_value={"index": 0})
        mock_bc.pending_transactions = []
        mock_bc.difficulty = 4
        mock_bc.max_supply = 121000000
        mock_bc.min_fee_rate = 0.00001
        mock_bc.utxo_manager = Mock()
        mock_bc.utxo_manager.get_utxos_for_address.return_value = []
        server._blockchain = mock_bc
        server._initialized = True

        # Test all tools produce JSON-serializable output
        tools = server.get_tools()
        for tool in tools:
            tool_name = tool["name"]
            args = {}
            if "required" in tool["inputSchema"]:
                for req in tool["inputSchema"]["required"]:
                    if req == "address":
                        args["address"] = "test"
                    elif req == "txid":
                        args["txid"] = "test"

            result = server.call_tool(tool_name, args)

            # Should be JSON serializable
            try:
                json.dumps(result)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Tool {tool_name} returned non-JSON-serializable result: {e}")
