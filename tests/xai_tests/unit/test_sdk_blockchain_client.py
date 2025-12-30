"""
Comprehensive tests for XAI SDK BlockchainClient module.

Tests cover:
- Block retrieval (single and list)
- Block transactions
- Sync status
- Blockchain statistics
- Node information
- Health checks
- Error handling and validation
"""

from datetime import datetime
from unittest.mock import Mock
import pytest

from xai.sdk.python.xai_sdk.clients.blockchain_client import BlockchainClient
from xai.sdk.python.xai_sdk.exceptions import (
    NetworkError,
    ValidationError,
    XAIError,
)
from xai.sdk.python.xai_sdk.models import Block, BlockchainStats


class TestBlockchainClientInit:
    """Tests for BlockchainClient initialization."""

    def test_init_with_http_client(self):
        """Test BlockchainClient initializes with HTTP client."""
        mock_http = Mock()
        client = BlockchainClient(mock_http)
        assert client.http_client is mock_http


class TestGetBlock:
    """Tests for get_block method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_block_success(self, client):
        """Test successful block retrieval."""
        client.http_client.get.return_value = {
            "number": 12345,
            "hash": "0xblockhash123",
            "parent_hash": "0xparenthash",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "1000000",
            "gas_limit": "30000000",
            "gas_used": "15000000",
            "transaction_count": 150,
            "transactions": ["0xtx1", "0xtx2", "0xtx3"],
        }

        block = client.get_block(block_number=12345)

        assert isinstance(block, Block)
        assert block.number == 12345
        assert block.hash == "0xblockhash123"
        assert block.parent_hash == "0xparenthash"
        assert block.miner == "0xminer"
        assert block.difficulty == "1000000"
        assert block.transactions == 150
        assert len(block.transaction_hashes) == 3

    def test_get_block_calls_correct_endpoint(self, client):
        """Test get_block calls correct API endpoint."""
        client.http_client.get.return_value = {
            "number": 100,
            "hash": "0xhash",
            "parent_hash": "0xparent",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "1000",
        }

        client.get_block(block_number=100)

        client.http_client.get.assert_called_once_with("/blocks/100")

    def test_get_block_negative_number_raises_validation(self, client):
        """Test negative block_number raises ValidationError."""
        with pytest.raises(ValidationError, match="block_number must be non-negative"):
            client.get_block(block_number=-1)

    def test_get_block_zero_valid(self, client):
        """Test block zero (genesis) is valid."""
        client.http_client.get.return_value = {
            "number": 0,
            "hash": "0xgenesishash",
            "parent_hash": "0x" + "0" * 64,
            "timestamp": 1609459200,
            "miner": "0x" + "0" * 40,
            "difficulty": "1",
        }

        block = client.get_block(block_number=0)

        assert block.number == 0

    def test_get_block_default_values(self, client):
        """Test block with default values for optional fields."""
        client.http_client.get.return_value = {
            "number": 100,
            "hash": "0xhash",
            "parent_hash": "0xparent",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "1000",
        }

        block = client.get_block(block_number=100)

        assert block.gas_limit == "0"
        assert block.gas_used == "0"
        assert block.transactions == 0
        assert block.transaction_hashes == []

    def test_get_block_very_large_number(self, client):
        """Test block with very large block number."""
        client.http_client.get.return_value = {
            "number": 999999999,
            "hash": "0xhash",
            "parent_hash": "0xparent",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "999999999999",
        }

        block = client.get_block(block_number=999999999)

        assert block.number == 999999999


class TestListBlocks:
    """Tests for list_blocks method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_list_blocks_success(self, client):
        """Test successful block listing."""
        client.http_client.get.return_value = {
            "blocks": [
                {
                    "number": 100,
                    "hash": "0xhash100",
                    "parent_hash": "0xparent100",
                    "timestamp": 1705320600,
                    "miner": "0xminer",
                    "difficulty": "1000",
                    "transaction_count": 50,
                },
                {
                    "number": 99,
                    "hash": "0xhash99",
                    "parent_hash": "0xparent99",
                    "timestamp": 1705320585,
                    "miner": "0xminer",
                    "difficulty": "999",
                    "transaction_count": 45,
                },
            ],
            "total": 100,
            "limit": 20,
            "offset": 0,
        }

        result = client.list_blocks()

        assert len(result["blocks"]) == 2
        assert isinstance(result["blocks"][0], Block)
        assert result["blocks"][0].number == 100
        assert result["total"] == 100

    def test_list_blocks_with_pagination(self, client):
        """Test block listing with pagination."""
        client.http_client.get.return_value = {
            "blocks": [],
            "total": 1000,
            "limit": 10,
            "offset": 50,
        }

        result = client.list_blocks(limit=10, offset=50)

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["offset"] == 50

    def test_list_blocks_limit_capped_at_100(self, client):
        """Test limit is capped at 100."""
        client.http_client.get.return_value = {
            "blocks": [],
            "total": 0,
        }

        client.list_blocks(limit=500)

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["limit"] == 100

    def test_list_blocks_empty(self, client):
        """Test empty block list."""
        client.http_client.get.return_value = {
            "blocks": [],
            "total": 0,
        }

        result = client.list_blocks()

        assert result["blocks"] == []

    def test_list_blocks_defaults(self, client):
        """Test block listing with default values."""
        client.http_client.get.return_value = {
            "blocks": [
                {
                    "number": 1,
                    "hash": "0xhash",
                    "parent_hash": "0xparent",
                    "timestamp": 1705320600,
                    "miner": "0xminer",
                },
            ],
            "total": 1,
        }

        result = client.list_blocks()

        block = result["blocks"][0]
        assert block.difficulty == "0"
        assert block.gas_limit == "0"


class TestGetBlockTransactions:
    """Tests for get_block_transactions method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_block_transactions_success(self, client):
        """Test successful block transactions retrieval."""
        client.http_client.get.return_value = {
            "transactions": [
                {"hash": "0xtx1", "amount": "100"},
                {"hash": "0xtx2", "amount": "200"},
                {"hash": "0xtx3", "amount": "300"},
            ],
        }

        result = client.get_block_transactions(block_number=12345)

        assert len(result) == 3
        assert result[0]["hash"] == "0xtx1"

    def test_get_block_transactions_calls_correct_endpoint(self, client):
        """Test get_block_transactions calls correct API endpoint."""
        client.http_client.get.return_value = {"transactions": []}

        client.get_block_transactions(block_number=100)

        client.http_client.get.assert_called_once_with("/blocks/100/transactions")

    def test_get_block_transactions_negative_number_raises_validation(self, client):
        """Test negative block_number raises ValidationError."""
        with pytest.raises(ValidationError, match="block_number must be non-negative"):
            client.get_block_transactions(block_number=-1)

    def test_get_block_transactions_empty(self, client):
        """Test empty transactions list."""
        client.http_client.get.return_value = {"transactions": []}

        result = client.get_block_transactions(block_number=12345)

        assert result == []

    def test_get_block_transactions_missing_key(self, client):
        """Test missing transactions key returns empty list."""
        client.http_client.get.return_value = {}

        result = client.get_block_transactions(block_number=12345)

        assert result == []


class TestGetSyncStatus:
    """Tests for get_sync_status method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_sync_status_success(self, client):
        """Test successful sync status retrieval."""
        client.http_client.get.return_value = {
            "syncing": True,
            "current_block": 50000,
            "highest_block": 100000,
            "starting_block": 0,
            "progress_percent": 50.0,
        }

        result = client.get_sync_status()

        assert result["syncing"] is True
        assert result["current_block"] == 50000
        assert result["progress_percent"] == 50.0

    def test_get_sync_status_calls_correct_endpoint(self, client):
        """Test get_sync_status calls correct API endpoint."""
        client.http_client.get.return_value = {"syncing": False}

        client.get_sync_status()

        client.http_client.get.assert_called_once_with("/sync")

    def test_get_sync_status_fully_synced(self, client):
        """Test sync status when fully synced."""
        client.http_client.get.return_value = {
            "syncing": False,
            "current_block": 100000,
            "highest_block": 100000,
        }

        result = client.get_sync_status()

        assert result["syncing"] is False


class TestIsSynced:
    """Tests for is_synced method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_is_synced_true(self, client):
        """Test is_synced returns True when synced."""
        client.http_client.get.return_value = {"syncing": False}

        result = client.is_synced()

        assert result is True

    def test_is_synced_false(self, client):
        """Test is_synced returns False when syncing."""
        client.http_client.get.return_value = {"syncing": True}

        result = client.is_synced()

        assert result is False

    def test_is_synced_missing_syncing_key(self, client):
        """Test is_synced when syncing key is missing."""
        client.http_client.get.return_value = {}

        result = client.is_synced()

        # Missing key defaults to False for .get(), so not syncing means synced
        assert result is True


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_stats_success(self, client):
        """Test successful stats retrieval."""
        client.http_client.get.return_value = {
            "total_blocks": 100000,
            "total_transactions": 5000000,
            "total_accounts": 250000,
            "difficulty": "1500000000000",
            "hashrate": "500000000000",
            "average_block_time": 15.0,
            "total_supply": "21000000000000000000000000",
            "network": "mainnet",
        }

        stats = client.get_stats()

        assert isinstance(stats, BlockchainStats)
        assert stats.total_blocks == 100000
        assert stats.total_transactions == 5000000
        assert stats.total_accounts == 250000
        assert stats.difficulty == "1500000000000"
        assert stats.hashrate == "500000000000"
        assert stats.average_block_time == 15.0
        assert stats.network == "mainnet"

    def test_get_stats_calls_correct_endpoint(self, client):
        """Test get_stats calls correct API endpoint."""
        client.http_client.get.return_value = {
            "total_blocks": 0,
            "total_transactions": 0,
            "total_accounts": 0,
            "difficulty": "0",
            "hashrate": "0",
            "total_supply": "0",
        }

        client.get_stats()

        client.http_client.get.assert_called_once_with("/stats")

    def test_get_stats_default_values(self, client):
        """Test stats with default values."""
        client.http_client.get.return_value = {
            "total_blocks": 100,
            "total_transactions": 1000,
            "total_accounts": 50,
            "difficulty": "1000",
            "hashrate": "1000",
            "total_supply": "1000000",
        }

        stats = client.get_stats()

        assert stats.average_block_time == 0
        assert stats.network == "mainnet"

    def test_get_stats_testnet(self, client):
        """Test stats for testnet."""
        client.http_client.get.return_value = {
            "total_blocks": 50000,
            "total_transactions": 100000,
            "total_accounts": 1000,
            "difficulty": "100000",
            "hashrate": "10000",
            "total_supply": "1000000000",
            "network": "testnet",
        }

        stats = client.get_stats()

        assert stats.network == "testnet"


class TestGetNodeInfo:
    """Tests for get_node_info method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_node_info_success(self, client):
        """Test successful node info retrieval."""
        client.http_client.get.return_value = {
            "version": "1.0.0",
            "network": "mainnet",
            "protocol_version": 66,
            "peers": 25,
            "node_id": "enode://abc123...",
        }

        result = client.get_node_info()

        assert result["version"] == "1.0.0"
        assert result["network"] == "mainnet"
        assert result["peers"] == 25

    def test_get_node_info_calls_correct_endpoint(self, client):
        """Test get_node_info calls correct API endpoint."""
        client.http_client.get.return_value = {}

        client.get_node_info()

        client.http_client.get.assert_called_once_with("/")


class TestGetHealth:
    """Tests for get_health method."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_get_health_success(self, client):
        """Test successful health check."""
        client.http_client.get.return_value = {
            "status": "healthy",
            "uptime": 86400,
            "database": "connected",
            "p2p": "connected",
        }

        result = client.get_health()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    def test_get_health_calls_correct_endpoint(self, client):
        """Test get_health calls correct API endpoint."""
        client.http_client.get.return_value = {"status": "ok"}

        client.get_health()

        client.http_client.get.assert_called_once_with("/health")

    def test_get_health_degraded(self, client):
        """Test health check with degraded status."""
        client.http_client.get.return_value = {
            "status": "degraded",
            "issues": ["high_memory_usage"],
        }

        result = client.get_health()

        assert result["status"] == "degraded"
        assert "high_memory_usage" in result["issues"]


class TestBlockchainClientErrorHandling:
    """Tests for BlockchainClient error handling."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_xai_error_passes_through_on_get_block(self, client):
        """Test XAIError passes through on get_block."""
        client.http_client.get.side_effect = XAIError("Block not found")

        with pytest.raises(XAIError, match="Block not found"):
            client.get_block(block_number=99999999)

    def test_xai_error_passes_through_on_list_blocks(self, client):
        """Test XAIError passes through on list_blocks."""
        client.http_client.get.side_effect = XAIError("List failed")

        with pytest.raises(XAIError, match="List failed"):
            client.list_blocks()

    def test_xai_error_passes_through_on_get_stats(self, client):
        """Test XAIError passes through on get_stats."""
        client.http_client.get.side_effect = XAIError("Stats error")

        with pytest.raises(XAIError, match="Stats error"):
            client.get_stats()

    def test_key_error_wrapped_in_xai_error(self, client):
        """Test KeyError is wrapped in XAIError."""
        client.http_client.get.return_value = {}  # Missing required keys

        with pytest.raises(XAIError, match="Failed to get block"):
            client.get_block(block_number=1)

    def test_network_error_on_get_health(self, client):
        """Test network error on get_health."""
        client.http_client.get.side_effect = NetworkError("Connection refused")

        with pytest.raises(NetworkError):
            client.get_health()


class TestBlockchainClientEdgeCases:
    """Tests for BlockchainClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create BlockchainClient with mocked HTTP client."""
        mock_http = Mock()
        return BlockchainClient(mock_http)

    def test_very_large_block_with_many_transactions(self, client):
        """Test block with many transactions."""
        client.http_client.get.return_value = {
            "number": 12345,
            "hash": "0xhash",
            "parent_hash": "0xparent",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "1000",
            "transaction_count": 10000,
            "transactions": ["0xtx" + str(i) for i in range(10000)],
        }

        block = client.get_block(block_number=12345)

        assert block.transactions == 10000
        assert len(block.transaction_hashes) == 10000

    def test_block_with_large_difficulty(self, client):
        """Test block with very large difficulty."""
        client.http_client.get.return_value = {
            "number": 12345,
            "hash": "0xhash",
            "parent_hash": "0xparent",
            "timestamp": 1705320600,
            "miner": "0xminer",
            "difficulty": "99999999999999999999999999",
        }

        block = client.get_block(block_number=12345)

        assert block.difficulty == "99999999999999999999999999"

    def test_stats_with_large_values(self, client):
        """Test stats with very large values."""
        client.http_client.get.return_value = {
            "total_blocks": 999999999,
            "total_transactions": 9999999999999,
            "total_accounts": 999999999,
            "difficulty": "9" * 50,
            "hashrate": "9" * 30,
            "total_supply": "9" * 60,
        }

        stats = client.get_stats()

        assert stats.total_blocks == 999999999
        assert len(stats.difficulty) == 50

    def test_block_timestamp_edge_cases(self, client):
        """Test block with edge case timestamps."""
        # Epoch timestamp
        client.http_client.get.return_value = {
            "number": 0,
            "hash": "0xhash",
            "parent_hash": "0x" + "0" * 64,
            "timestamp": 0,  # Unix epoch
            "miner": "0x" + "0" * 40,
            "difficulty": "1",
        }

        block = client.get_block(block_number=0)

        assert block.timestamp == 0

    def test_node_info_with_minimal_data(self, client):
        """Test node info with minimal data."""
        client.http_client.get.return_value = {"status": "ok"}

        result = client.get_node_info()

        assert result["status"] == "ok"

    def test_list_blocks_at_boundary(self, client):
        """Test list_blocks at boundary conditions."""
        client.http_client.get.return_value = {
            "blocks": [],
            "total": 0,
            "limit": 100,
            "offset": 0,
        }

        result = client.list_blocks(limit=100, offset=0)

        call_args = client.http_client.get.call_args
        assert call_args[1]["params"]["limit"] == 100
        assert call_args[1]["params"]["offset"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
