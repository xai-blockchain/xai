"""
Comprehensive tests for Proof of Work validation.

Tests verify that PoW validation uses proper numeric target comparison
instead of the incorrect string prefix approach.

Security context:
    The string prefix approach (checking for leading zeros) is incorrect
    because it doesn't properly validate that the hash is below the target.

    Correct approach: hash_int < (2^256 / difficulty)

    Example: With difficulty=2, target = 2^255
    - Hash 0x7FFF...FFFF should PASS (below target)
    - Hash 0x8000...0000 should FAIL (at/above target)
    - But string prefix would accept both (no leading zeros required)
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestLightClientPoWValidation:
    """Tests for LightClient._validate_pow method."""

    @pytest.fixture
    def light_client(self):
        """Create a light client instance."""
        from xai.core.light_client import LightClient
        return LightClient()

    def test_valid_hash_below_target(self, light_client):
        """Test that hash below target is accepted."""
        # Create header with hash well below target
        header = Mock()
        header.difficulty = 16  # target = 2^256 / 16 = 2^252
        # This hash is 0x0FFF...F which is way below 2^252
        header.hash = "0" * 63 + "1"  # Small hash

        result = light_client._validate_pow(header)
        assert result is True

    def test_invalid_hash_above_target(self, light_client):
        """Test that hash above target is rejected."""
        header = Mock()
        header.difficulty = 2**200  # Very high difficulty
        # Any normal hash will be above this target
        header.hash = "f" * 64  # Maximum hash value

        result = light_client._validate_pow(header)
        assert result is False

    def test_empty_hash_rejected(self, light_client):
        """Test that empty hash is rejected."""
        header = Mock()
        header.hash = ""
        header.difficulty = 1

        result = light_client._validate_pow(header)
        assert result is False

    def test_none_hash_rejected(self, light_client):
        """Test that None hash is rejected."""
        header = Mock()
        header.hash = None
        header.difficulty = 1

        result = light_client._validate_pow(header)
        assert result is False

    def test_zero_difficulty_rejected(self, light_client):
        """Test that zero difficulty is rejected."""
        header = Mock()
        header.hash = "0" * 64
        header.difficulty = 0

        result = light_client._validate_pow(header)
        assert result is False

    def test_negative_difficulty_rejected(self, light_client):
        """Test that negative difficulty is rejected."""
        header = Mock()
        header.hash = "0" * 64
        header.difficulty = -1

        result = light_client._validate_pow(header)
        assert result is False

    def test_invalid_hex_hash_rejected(self, light_client):
        """Test that invalid hex hash is rejected."""
        header = Mock()
        header.hash = "not_a_valid_hex"
        header.difficulty = 1

        result = light_client._validate_pow(header)
        assert result is False

    def test_boundary_hash_at_target(self, light_client):
        """Test hash exactly at target boundary (should fail)."""
        header = Mock()
        header.difficulty = 2  # target = 2^255

        # Hash equal to target should FAIL (must be strictly less than)
        # 2^255 in hex = 8000...0 (followed by 63 zeros)
        header.hash = "8" + "0" * 63

        result = light_client._validate_pow(header)
        # Hash equal to target should fail
        assert result is False

    def test_hash_just_below_target(self, light_client):
        """Test hash just below target (should pass)."""
        header = Mock()
        header.difficulty = 2  # target = 2^255

        # Hash just below 2^255 should pass
        # 2^255 - 1 in hex = 7FFF...F
        header.hash = "7" + "f" * 63

        result = light_client._validate_pow(header)
        assert result is True


class TestConsensusManagerPoWValidation:
    """Tests for ConsensusManager._validate_pow method."""

    @pytest.fixture
    def consensus_manager(self):
        """Create a consensus manager with mocked blockchain."""
        from xai.core.node_consensus import ConsensusManager

        mock_blockchain = Mock()
        mock_blockchain.difficulty = 4
        mock_blockchain.chain = []

        return ConsensusManager(mock_blockchain)

    def test_valid_hash_below_target(self, consensus_manager):
        """Test that hash below target is accepted."""
        # With difficulty 4, target = 2^254
        # A hash starting with 00 is definitely below target
        result = consensus_manager._validate_pow("00" + "a" * 62, difficulty=4)
        assert result is True

    def test_invalid_hash_above_target(self, consensus_manager):
        """Test that hash above target is rejected."""
        # With very high difficulty, almost any hash fails
        result = consensus_manager._validate_pow("f" * 64, difficulty=2**200)
        assert result is False

    def test_empty_hash_rejected(self, consensus_manager):
        """Test that empty hash is rejected."""
        result = consensus_manager._validate_pow("", difficulty=1)
        assert result is False

    def test_zero_difficulty_rejected(self, consensus_manager):
        """Test that zero difficulty is rejected."""
        result = consensus_manager._validate_pow("0" * 64, difficulty=0)
        assert result is False

    def test_negative_difficulty_rejected(self, consensus_manager):
        """Test that negative difficulty is rejected."""
        result = consensus_manager._validate_pow("0" * 64, difficulty=-1)
        assert result is False

    def test_verify_proof_of_work_delegates(self, consensus_manager):
        """Test that verify_proof_of_work uses _validate_pow."""
        mock_block = Mock()
        mock_block.hash = "0" * 64

        result = consensus_manager.verify_proof_of_work(mock_block, difficulty=1)
        assert result is True

    def test_validate_block_uses_proper_pow(self, consensus_manager):
        """Test that validate_block uses proper PoW validation."""
        mock_block = Mock()
        mock_block.index = 1
        mock_block.timestamp = 1000
        mock_block.hash = "0" * 64  # Valid PoW
        mock_block.calculate_hash = Mock(return_value="0" * 64)

        is_valid, error = consensus_manager.validate_block(mock_block)
        assert is_valid is True

    def test_validate_block_rejects_invalid_pow(self, consensus_manager):
        """Test that validate_block rejects invalid PoW."""
        mock_block = Mock()
        mock_block.index = 1
        mock_block.timestamp = 1000
        mock_block.hash = "f" * 64  # Invalid PoW (too high)
        mock_block.calculate_hash = Mock(return_value="f" * 64)

        is_valid, error = consensus_manager.validate_block(mock_block)
        assert is_valid is False
        assert "proof of work" in error.lower()


class TestPoWSecurityScenarios:
    """Security-focused tests for PoW validation edge cases."""

    @pytest.fixture
    def consensus_manager(self):
        """Create a consensus manager."""
        from xai.core.node_consensus import ConsensusManager

        mock_blockchain = Mock()
        mock_blockchain.difficulty = 4
        mock_blockchain.chain = []

        return ConsensusManager(mock_blockchain)

    def test_string_prefix_attack_prevented(self, consensus_manager):
        """
        Test that string prefix attack is prevented.

        With old string prefix validation, a hash like 0x1000...0
        would fail because it doesn't start with "0000".
        But a hash like 0x0FFF...F would pass.

        With difficulty=4 (target=2^254), both should behave differently:
        - 0x0FFF...F < 2^254 -> should PASS
        - 0x1000...0 > 2^254 -> should FAIL

        This test verifies we use proper numeric comparison.
        """
        # With difficulty=4, target = 2^254 = 0x4000...0

        # This hash starts with "0" but numerically is 0x0FFF...F
        # which is below 2^254, so it should PASS
        hash_with_leading_zero = "0" + "f" * 63
        assert consensus_manager._validate_pow(hash_with_leading_zero, 4) is True

        # This hash starts with "4" which is 0x4000...0
        # which equals 2^254 (the target), so it should FAIL
        hash_at_boundary = "4" + "0" * 63
        assert consensus_manager._validate_pow(hash_at_boundary, 4) is False

        # This hash starts with "3" which is below target
        hash_below_target = "3" + "f" * 63
        assert consensus_manager._validate_pow(hash_below_target, 4) is True

    def test_large_difficulty_values(self, consensus_manager):
        """Test handling of very large difficulty values."""
        # Difficulty of 2^255 means target is 2^1 = 2
        # Only hashes 0x0 and 0x1 would be valid
        extremely_high_difficulty = 2**255

        # Hash of 0x0000...0001 should pass
        result = consensus_manager._validate_pow("0" * 63 + "1", extremely_high_difficulty)
        assert result is True

        # Hash of 0x0000...0002 should fail (>= 2)
        result = consensus_manager._validate_pow("0" * 63 + "2", extremely_high_difficulty)
        assert result is False

    def test_minimum_difficulty(self, consensus_manager):
        """Test minimum difficulty (1) allows all valid hashes."""
        # Difficulty 1 means target = 2^256, which means all hashes pass
        # (since all hashes are < 2^256)
        result = consensus_manager._validate_pow("f" * 64, difficulty=1)
        assert result is True

    def test_consistent_with_mining_algorithm(self):
        """Test that consensus validation matches mining algorithm validation."""
        from xai.core.mining_algorithm import MiningAlgorithm
        from xai.core.node_consensus import ConsensusManager

        mining = MiningAlgorithm()
        mock_blockchain = Mock()
        mock_blockchain.difficulty = 4
        mock_blockchain.chain = []
        consensus = ConsensusManager(mock_blockchain)

        # Test various hashes - both should give same results
        test_cases = [
            ("0" * 64, 4),
            ("f" * 64, 4),
            ("0" * 63 + "1", 2**200),
            ("0" + "f" * 63, 16),
        ]

        for hash_val, difficulty in test_cases:
            mining_result = mining._is_valid_hash(hash_val, difficulty)
            consensus_result = consensus._validate_pow(hash_val, difficulty)
            assert mining_result == consensus_result, \
                f"Mismatch for hash={hash_val[:10]}..., difficulty={difficulty}"
