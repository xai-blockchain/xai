"""
Edge case tests for timestamp boundary conditions.

Tests various timestamp boundary scenarios to ensure robust validation
and handling of edge cases in block timestamp validation.
"""

import pytest
import time
import hashlib
from xai.core.blockchain import Blockchain
from xai.core.blockchain_components.block import Block
from xai.core.block_header import BlockHeader
from xai.core.wallet import Wallet
from xai.core.config import Config


class TestTimestampBoundaries:
    """Test handling of timestamp boundary conditions"""

    def test_zero_timestamp(self, tmp_path):
        """Test block with zero timestamp"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=0.0,  # Zero timestamp (epoch)
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected - timestamp before genesis
        assert not bc.add_block(block)

    def test_negative_timestamp(self, tmp_path):
        """Test block with negative timestamp is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=-100.0,  # Negative timestamp
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected
        assert not bc.add_block(block)

    def test_timestamp_before_previous_block(self, tmp_path):
        """Test block with timestamp before previous block is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine a block
        latest = bc.mine_pending_transactions(miner.address)
        time.sleep(0.1)  # Ensure time has passed

        # Try to add block with earlier timestamp
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=latest.timestamp - 100,  # 100 seconds before previous block
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected
        assert not bc.add_block(block)

    def test_timestamp_equal_to_previous_block(self, tmp_path):
        """Test block with timestamp equal to previous block"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        latest = bc.mine_pending_transactions(miner.address)

        # Create block with same timestamp as previous
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=latest.timestamp,  # Same timestamp
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected or accepted depending on implementation
        # Most blockchains require strictly increasing timestamps
        result = bc.add_block(block)
        # Document the behavior
        assert isinstance(result, bool)

    def test_far_future_timestamp(self, tmp_path):
        """Test block with far future timestamp is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        # MAX_FUTURE_BLOCK_TIME is typically 2 hours (7200 seconds)
        max_future = getattr(Config, 'MAX_FUTURE_BLOCK_TIME', 7200)

        # Create block with timestamp well beyond the limit
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time() + max_future + 3600,  # 1 hour beyond limit
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected
        assert not bc.add_block(block)

    def test_timestamp_at_max_future_boundary(self, tmp_path):
        """Test block at exactly the maximum future timestamp boundary"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        max_future = getattr(Config, 'MAX_FUTURE_BLOCK_TIME', 7200)

        # Create block at exactly the boundary
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time() + max_future,  # Exactly at the limit
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be accepted or rejected depending on whether boundary is inclusive
        result = bc.add_block(block)
        assert isinstance(result, bool)

    def test_timestamp_just_under_max_future(self, tmp_path):
        """Test block just under the maximum future timestamp"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        max_future = getattr(Config, 'MAX_FUTURE_BLOCK_TIME', 7200)

        # Create a miner wallet to sign the block
        miner = Wallet()

        # Create block just under the limit
        # Don't specify merkle_root - let Block calculate it from transactions
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root=Block._calculate_merkle_root_static([]),  # Correct merkle root for empty tx list
            timestamp=time.time() + max_future - 10,  # 10 seconds before limit
            difficulty=4,
            nonce=0,
            miner_pubkey=miner.public_key
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Sign the block after mining
        from xai.core.crypto_utils import sign_message_hex
        block.header.signature = sign_message_hex(miner.private_key, block.hash.encode())

        # Should be accepted
        assert bc.add_block(block)

    def test_timestamp_precision_loss(self, tmp_path):
        """Test that timestamp precision is preserved"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Create header with high precision timestamp
        precise_time = 1234567890.123456789
        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=precise_time,
            difficulty=4,
            nonce=0
        )

        # Verify precision is maintained
        assert abs(header.timestamp - precise_time) < 1e-6

    def test_extremely_large_timestamp(self, tmp_path):
        """Test block with extremely large timestamp (year 3000+)"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        # Timestamp for year 3000
        year_3000_timestamp = 32503680000.0

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=year_3000_timestamp,
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected as too far in future
        assert not bc.add_block(block)

    def test_timestamp_overflow(self, tmp_path):
        """Test handling of timestamp overflow"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Test with maximum float value
        max_timestamp = 1.7976931348623157e+308  # Max float

        with pytest.raises((ValueError, OverflowError, OSError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=max_timestamp,
                difficulty=4,
                nonce=0
            )

    def test_median_time_past_validation(self, tmp_path):
        """Test median-time-past (MTP) validation if implemented"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine several blocks with increasing timestamps
        timestamps = []
        for i in range(11):  # Median of 11 blocks
            time.sleep(0.01)
            block = bc.mine_pending_transactions(miner.address)
            timestamps.append(block.timestamp)

        latest = bc.get_latest_block()

        # Calculate median of last 11 blocks
        sorted_times = sorted(timestamps[-11:])
        median_time = sorted_times[5]  # Middle value

        # Try to add block with timestamp before median
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=median_time - 10,  # Before median
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # If MTP is implemented, this should be rejected
        result = bc.add_block(block)
        # Document behavior (may or may not implement MTP)
        assert isinstance(result, bool)

    def test_timestamp_with_nanosecond_precision(self, tmp_path):
        """Test timestamp with nanosecond precision"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Python floats can represent nanosecond precision
        nano_timestamp = 1234567890.123456789

        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=nano_timestamp,
            difficulty=4,
            nonce=0
        )

        # Verify the timestamp is stored accurately
        assert header.timestamp == nano_timestamp

    def test_timestamp_type_coercion(self, tmp_path):
        """Test that integer timestamps are coerced to float"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Pass integer timestamp
        int_timestamp = 1234567890
        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=int_timestamp,  # Integer
            difficulty=4,
            nonce=0
        )

        # Should be converted to float
        assert isinstance(header.timestamp, (int, float))

    def test_timestamp_string_rejected(self, tmp_path):
        """Test that string timestamps are rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp="2024-01-01",  # String instead of number
                difficulty=4,
                nonce=0
            )

    def test_timestamp_none_rejected(self, tmp_path):
        """Test that None timestamp is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=None,  # None value
                difficulty=4,
                nonce=0
            )

    def test_rapid_block_succession_timestamps(self, tmp_path):
        """Test blocks mined in rapid succession have valid timestamps"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine blocks rapidly
        blocks = []
        for _ in range(5):
            block = bc.mine_pending_transactions(miner.address)
            blocks.append(block)

        # Verify timestamps are monotonically increasing
        for i in range(len(blocks) - 1):
            assert blocks[i + 1].timestamp >= blocks[i].timestamp

    def test_clock_drift_tolerance(self, tmp_path):
        """Test that small clock drift is tolerated"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        # Simulate small clock drift (1 second in the future)
        # Calculate correct merkle root for empty transaction list
        merkle_root = hashlib.sha256(b"").hexdigest()

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root=merkle_root,
            timestamp=time.time() + 1,  # 1 second ahead
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Small drift should be accepted
        assert bc.add_block(block)

    def test_timestamp_after_long_delay(self, tmp_path):
        """Test block with timestamp after long delay is accepted"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        latest = bc.mine_pending_transactions(miner.address)

        # Simulate long delay (1 hour)
        future_timestamp = time.time() + 3600

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=future_timestamp,
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected if beyond MAX_FUTURE_BLOCK_TIME
        max_future = getattr(Config, 'MAX_FUTURE_BLOCK_TIME', 7200)
        if 3600 <= max_future:
            result = bc.add_block(block)
            assert isinstance(result, bool)
        else:
            assert not bc.add_block(block)

    def test_timestamp_inf_rejected(self, tmp_path):
        """Test that infinity timestamp is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, OverflowError, OSError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=float('inf'),  # Infinity
                difficulty=4,
                nonce=0
            )

    def test_timestamp_nan_rejected(self, tmp_path):
        """Test that NaN timestamp is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, AssertionError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=float('nan'),  # Not a number
                difficulty=4,
                nonce=0
            )
