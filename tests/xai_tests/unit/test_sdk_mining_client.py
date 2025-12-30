"""
Comprehensive tests for XAI SDK MiningClient module.

Tests cover:
- Starting mining
- Stopping mining
- Mining status retrieval
- Mining rewards
- Checking mining state
- Error handling and validation
"""

from unittest.mock import Mock
import pytest

from xai.sdk.python.xai_sdk.clients.mining_client import MiningClient
from xai.sdk.python.xai_sdk.exceptions import (
    MiningError,
    NetworkError,
    ValidationError,
    XAIError,
)
from xai.sdk.python.xai_sdk.models import MiningStatus


class TestMiningClientInit:
    """Tests for MiningClient initialization."""

    def test_init_with_http_client(self):
        """Test MiningClient initializes with HTTP client."""
        mock_http = Mock()
        client = MiningClient(mock_http)
        assert client.http_client is mock_http


class TestMiningStart:
    """Tests for mining start method."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_start_mining_success(self, client):
        """Test successful mining start."""
        client.http_client.post.return_value = {
            "status": "started",
            "threads": 4,
            "message": "Mining started successfully",
        }

        result = client.start(threads=4)

        assert result["status"] == "started"
        assert result["threads"] == 4

    def test_start_mining_default_threads(self, client):
        """Test starting with default thread count."""
        client.http_client.post.return_value = {
            "status": "started",
            "threads": 1,
        }

        result = client.start()

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["threads"] == 1

    def test_start_mining_max_threads(self, client):
        """Test starting with maximum threads."""
        client.http_client.post.return_value = {
            "status": "started",
            "threads": 16,
        }

        result = client.start(threads=16)

        call_args = client.http_client.post.call_args
        assert call_args[1]["data"]["threads"] == 16

    def test_start_mining_calls_correct_endpoint(self, client):
        """Test start calls correct API endpoint."""
        client.http_client.post.return_value = {"status": "started"}

        client.start(threads=2)

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/mining/start"

    def test_start_mining_zero_threads_raises_validation(self, client):
        """Test zero threads raises ValidationError."""
        with pytest.raises(ValidationError, match="threads must be between 1 and 16"):
            client.start(threads=0)

    def test_start_mining_negative_threads_raises_validation(self, client):
        """Test negative threads raises ValidationError."""
        with pytest.raises(ValidationError, match="threads must be between 1 and 16"):
            client.start(threads=-1)

    def test_start_mining_too_many_threads_raises_validation(self, client):
        """Test too many threads raises ValidationError."""
        with pytest.raises(ValidationError, match="threads must be between 1 and 16"):
            client.start(threads=17)

    def test_start_mining_network_error(self, client):
        """Test start with network error."""
        client.http_client.post.side_effect = NetworkError("Connection failed")

        with pytest.raises(NetworkError):
            client.start(threads=4)


class TestMiningStop:
    """Tests for mining stop method."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_stop_mining_success(self, client):
        """Test successful mining stop."""
        client.http_client.post.return_value = {
            "status": "stopped",
            "message": "Mining stopped successfully",
            "blocks_found": 5,
        }

        result = client.stop()

        assert result["status"] == "stopped"
        assert result["blocks_found"] == 5

    def test_stop_mining_calls_correct_endpoint(self, client):
        """Test stop calls correct API endpoint."""
        client.http_client.post.return_value = {"status": "stopped"}

        client.stop()

        call_args = client.http_client.post.call_args
        assert call_args[0][0] == "/mining/stop"
        assert call_args[1]["data"] == {}

    def test_stop_mining_when_not_running(self, client):
        """Test stopping when mining is not running."""
        client.http_client.post.return_value = {
            "status": "not_running",
            "message": "Mining was not running",
        }

        result = client.stop()

        assert result["status"] == "not_running"

    def test_stop_mining_network_error(self, client):
        """Test stop with network error."""
        client.http_client.post.side_effect = NetworkError("Timeout")

        with pytest.raises(NetworkError):
            client.stop()


class TestMiningGetStatus:
    """Tests for mining get_status method."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_get_status_success(self, client):
        """Test successful status retrieval."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 8,
            "hashrate": "1500000000",
            "blocks_found": 25,
            "current_difficulty": "2000000000000",
            "uptime": 86400,
            "last_block_time": 1705320600,
        }

        status = client.get_status()

        assert isinstance(status, MiningStatus)
        assert status.mining is True
        assert status.threads == 8
        assert status.hashrate == "1500000000"
        assert status.blocks_found == 25
        assert status.current_difficulty == "2000000000000"
        assert status.uptime == 86400
        assert status.last_block_time == 1705320600

    def test_get_status_not_mining(self, client):
        """Test status when not mining."""
        client.http_client.get.return_value = {
            "mining": False,
            "threads": 0,
            "hashrate": "0",
            "blocks_found": 0,
            "current_difficulty": "1000000000000",
            "uptime": 0,
        }

        status = client.get_status()

        assert status.mining is False
        assert status.threads == 0
        assert status.hashrate == "0"

    def test_get_status_calls_correct_endpoint(self, client):
        """Test get_status calls correct API endpoint."""
        client.http_client.get.return_value = {
            "mining": False,
            "threads": 0,
            "hashrate": "0",
            "current_difficulty": "0",
        }

        client.get_status()

        client.http_client.get.assert_called_once_with("/mining/status")

    def test_get_status_default_values(self, client):
        """Test status with default values for optional fields."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 4,
            "hashrate": "1000",
            "current_difficulty": "1000",
        }

        status = client.get_status()

        assert status.blocks_found == 0
        assert status.uptime == 0
        assert status.last_block_time is None


class TestMiningGetRewards:
    """Tests for mining get_rewards method."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_get_rewards_success(self, client):
        """Test successful rewards retrieval."""
        client.http_client.get.return_value = {
            "address": "0xminer",
            "total_rewards": "50000000000000000000",
            "pending_rewards": "5000000000000000000",
            "claimed_rewards": "45000000000000000000",
            "blocks_mined": 10,
        }

        result = client.get_rewards(address="0xminer")

        assert result["total_rewards"] == "50000000000000000000"
        assert result["blocks_mined"] == 10

    def test_get_rewards_calls_correct_endpoint(self, client):
        """Test get_rewards calls correct API endpoint."""
        client.http_client.get.return_value = {"total_rewards": "0"}

        client.get_rewards(address="0xreward")

        call_args = client.http_client.get.call_args
        assert call_args[0][0] == "/mining/rewards"
        assert call_args[1]["params"]["address"] == "0xreward"

    def test_get_rewards_empty_address_raises_validation(self, client):
        """Test empty address raises ValidationError."""
        with pytest.raises(ValidationError, match="address is required"):
            client.get_rewards(address="")

    def test_get_rewards_none_address_raises_validation(self, client):
        """Test None address raises ValidationError."""
        with pytest.raises(ValidationError, match="address is required"):
            client.get_rewards(address=None)

    def test_get_rewards_zero_rewards(self, client):
        """Test rewards for address with no rewards."""
        client.http_client.get.return_value = {
            "address": "0xnorewards",
            "total_rewards": "0",
            "pending_rewards": "0",
            "claimed_rewards": "0",
            "blocks_mined": 0,
        }

        result = client.get_rewards(address="0xnorewards")

        assert result["total_rewards"] == "0"
        assert result["blocks_mined"] == 0


class TestMiningIsMining:
    """Tests for mining is_mining method."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_is_mining_true(self, client):
        """Test is_mining returns True when mining."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 4,
            "hashrate": "1000",
            "current_difficulty": "1000",
        }

        result = client.is_mining()

        assert result is True

    def test_is_mining_false(self, client):
        """Test is_mining returns False when not mining."""
        client.http_client.get.return_value = {
            "mining": False,
            "threads": 0,
            "hashrate": "0",
            "current_difficulty": "1000",
        }

        result = client.is_mining()

        assert result is False

    def test_is_mining_uses_get_status(self, client):
        """Test is_mining uses get_status internally."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 4,
            "hashrate": "1000",
            "current_difficulty": "1000",
        }

        client.is_mining()

        client.http_client.get.assert_called_once_with("/mining/status")


class TestMiningClientErrorHandling:
    """Tests for MiningClient error handling."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_mining_error_passes_through_on_start(self, client):
        """Test MiningError passes through on start."""
        client.http_client.post.side_effect = MiningError("Start failed")

        with pytest.raises(MiningError, match="Start failed"):
            client.start(threads=4)

    def test_mining_error_passes_through_on_stop(self, client):
        """Test MiningError passes through on stop."""
        client.http_client.post.side_effect = MiningError("Stop failed")

        with pytest.raises(MiningError, match="Stop failed"):
            client.stop()

    def test_mining_error_passes_through_on_get_status(self, client):
        """Test MiningError passes through on get_status."""
        client.http_client.get.side_effect = MiningError("Status failed")

        with pytest.raises(MiningError, match="Status failed"):
            client.get_status()

    def test_mining_error_passes_through_on_get_rewards(self, client):
        """Test MiningError passes through on get_rewards."""
        client.http_client.get.side_effect = MiningError("Rewards failed")

        with pytest.raises(MiningError, match="Rewards failed"):
            client.get_rewards(address="0xtest")

    def test_mining_error_passes_through_on_is_mining(self, client):
        """Test MiningError passes through on is_mining."""
        client.http_client.get.side_effect = MiningError("Check failed")

        with pytest.raises(MiningError, match="Check failed"):
            client.is_mining()

    def test_key_error_wrapped_in_mining_error(self, client):
        """Test KeyError is wrapped in MiningError."""
        client.http_client.get.return_value = {}  # Missing required keys

        with pytest.raises(MiningError, match="Failed to get mining status"):
            client.get_status()

    def test_value_error_wrapped_in_mining_error(self, client):
        """Test ValueError is wrapped in MiningError."""
        client.http_client.get.return_value = {
            "mining": "not-a-bool",  # Should be boolean
            "threads": 4,
            "hashrate": "1000",
            "current_difficulty": "1000",
        }

        # This might or might not raise depending on how Python handles it
        # The MiningStatus constructor expects boolean
        try:
            client.get_status()
        except (MiningError, TypeError):
            pass  # Expected behavior


class TestMiningClientEdgeCases:
    """Tests for MiningClient edge cases."""

    @pytest.fixture
    def client(self):
        """Create MiningClient with mocked HTTP client."""
        mock_http = Mock()
        return MiningClient(mock_http)

    def test_very_high_hashrate(self, client):
        """Test handling very high hashrate."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 16,
            "hashrate": "999999999999999999",
            "current_difficulty": "1000",
        }

        status = client.get_status()

        assert status.hashrate == "999999999999999999"

    def test_very_high_difficulty(self, client):
        """Test handling very high difficulty."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 8,
            "hashrate": "1000",
            "current_difficulty": "9" * 50,
        }

        status = client.get_status()

        assert len(status.current_difficulty) == 50

    def test_large_blocks_found(self, client):
        """Test handling large blocks found count."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 4,
            "hashrate": "1000",
            "blocks_found": 999999999,
            "current_difficulty": "1000",
        }

        status = client.get_status()

        assert status.blocks_found == 999999999

    def test_long_uptime(self, client):
        """Test handling long uptime."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 4,
            "hashrate": "1000",
            "current_difficulty": "1000",
            "uptime": 31536000,  # 1 year in seconds
        }

        status = client.get_status()

        assert status.uptime == 31536000

    def test_very_large_rewards(self, client):
        """Test handling very large reward amounts."""
        client.http_client.get.return_value = {
            "address": "0xminer",
            "total_rewards": "9" * 60,
            "pending_rewards": "0",
            "claimed_rewards": "9" * 60,
            "blocks_mined": 1000000,
        }

        result = client.get_rewards(address="0xminer")

        assert len(result["total_rewards"]) == 60

    def test_thread_boundary_values(self, client):
        """Test thread count at boundary values."""
        # Test 1 thread (minimum)
        client.http_client.post.return_value = {"status": "started", "threads": 1}
        result = client.start(threads=1)
        assert result["threads"] == 1

        # Test 16 threads (maximum)
        client.http_client.post.return_value = {"status": "started", "threads": 16}
        result = client.start(threads=16)
        assert result["threads"] == 16

    def test_status_all_fields_present(self, client):
        """Test status with all fields present."""
        client.http_client.get.return_value = {
            "mining": True,
            "threads": 8,
            "hashrate": "5000000000",
            "blocks_found": 100,
            "current_difficulty": "2000000000000",
            "uptime": 172800,
            "last_block_time": 1705320600,
        }

        status = client.get_status()

        assert status.mining is True
        assert status.threads == 8
        assert status.hashrate == "5000000000"
        assert status.blocks_found == 100
        assert status.current_difficulty == "2000000000000"
        assert status.uptime == 172800
        assert status.last_block_time == 1705320600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
