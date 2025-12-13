"""
Edge case tests for malformed block headers.

Tests various malformed block header scenarios to ensure robust validation
and error handling for invalid or corrupted block headers.
"""

import pytest
import time
from xai.core.blockchain import Blockchain
from xai.core.blockchain_components.block import Block
from xai.core.block_header import BlockHeader
from xai.core.wallet import Wallet
from xai.core.transaction import Transaction
from xai.core.config import Config


class TestMalformedBlockHeaders:
    """Test handling of malformed block headers"""

    def test_negative_index(self, tmp_path):
        """Test block with negative index is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Create block with negative index
        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=-1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
            block = Block(header=header, transactions=[])

    def test_zero_index_for_non_genesis(self, tmp_path):
        """Test that non-genesis blocks cannot have index 0"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        # Mine one block so we have a valid chain
        bc.mine_pending_transactions(miner.address)

        # Try to add a non-genesis block with index 0
        header = BlockHeader(
            index=0,
            previous_hash=bc.get_latest_block().hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])

        # Should be rejected due to index mismatch
        assert not bc.add_block(block)

    def test_non_sequential_index(self, tmp_path):
        """Test block with non-sequential index is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        latest = bc.get_latest_block()

        # Create block with index that skips ahead
        header = BlockHeader(
            index=latest.index + 10,  # Skip 9 blocks
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])

        # Should be rejected
        assert not bc.add_block(block)

    def test_invalid_previous_hash(self, tmp_path):
        """Test block with invalid previous hash is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()

        latest = bc.get_latest_block()

        # Create block with wrong previous hash
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash="1" * 64,  # Wrong hash
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[])

        # Should be rejected
        assert not bc.add_block(block)

    def test_malformed_previous_hash(self, tmp_path):
        """Test block with malformed previous hash is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Create block with invalid hash format
        with pytest.raises((ValueError, AttributeError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="invalid_hash",  # Not hex
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
            block = Block(header=header, transactions=[])
            bc.add_block(block)

    def test_empty_previous_hash(self, tmp_path):
        """Test block with empty previous hash is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="",  # Empty hash
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
            block = Block(header=header, transactions=[])
            bc.add_block(block)

    def test_negative_difficulty(self, tmp_path):
        """Test block with negative difficulty is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=-1,  # Negative difficulty
                nonce=0
            )

    def test_zero_difficulty(self, tmp_path):
        """Test block with zero difficulty is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=0,  # Zero difficulty
            nonce=0
        )
        block = Block(header=header, transactions=[])

        # Should be rejected due to invalid difficulty
        assert not bc.add_block(block)

    def test_extreme_difficulty(self, tmp_path):
        """Test block with extremely high difficulty"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        # Create block with unrealistic difficulty
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=256,  # Would require hash with 256 leading zeros (impossible)
            nonce=0
        )
        block = Block(header=header, transactions=[])

        # Should be rejected - hash won't meet difficulty requirement
        assert not bc.add_block(block)

    def test_negative_nonce(self, tmp_path):
        """Test block with negative nonce is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=-1  # Negative nonce
            )

    def test_invalid_merkle_root(self, tmp_path):
        """Test block with incorrect merkle root is rejected"""
        bc = Blockchain(data_dir=str(tmp_path))
        miner = Wallet()
        sender = Wallet()
        recipient = Wallet()

        # Create a valid transaction
        bc.mine_pending_transactions(sender.address)
        tx = bc.create_transaction(
            sender.address, recipient.address, 0.1, 0.01,
            sender.private_key, sender.public_key
        )

        latest = bc.get_latest_block()

        # Create block with wrong merkle root
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,  # Wrong merkle root
            timestamp=time.time(),
            difficulty=4,
            nonce=0
        )
        block = Block(header=header, transactions=[tx])
        block.mine_block()

        # Should be rejected due to merkle root mismatch
        assert not bc.add_block(block)

    def test_malformed_merkle_root_format(self, tmp_path):
        """Test block with malformed merkle root format"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="not_a_hash",  # Invalid format
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
            block = Block(header=header, transactions=[])
            bc.add_block(block)

    def test_missing_required_fields(self, tmp_path):
        """Test block header with missing required fields"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Try to create header without required fields
        with pytest.raises(TypeError):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64
                # Missing merkle_root, timestamp, difficulty, nonce
            )

    def test_invalid_signature_format(self, tmp_path):
        """Test block with malformed signature"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()
        miner = Wallet()

        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0,
            signature="invalid_signature_format",  # Malformed signature
            miner_pubkey=miner.public_key
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected or signature verification should fail
        result = bc.add_block(block)
        # Either rejected outright or verification fails
        assert not result or not block.verify_signature(miner.public_key)

    def test_invalid_version(self, tmp_path):
        """Test block with unsupported version number"""
        bc = Blockchain(data_dir=str(tmp_path))
        latest = bc.get_latest_block()

        # Create block with unsupported version
        header = BlockHeader(
            index=latest.index + 1,
            previous_hash=latest.hash,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0,
            version=999  # Unsupported version
        )
        block = Block(header=header, transactions=[])
        block.mine_block()

        # Should be rejected due to unsupported version
        assert not bc.add_block(block)

    def test_float_index(self, tmp_path):
        """Test block with float index is coerced or rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Float index should either be rejected or coerced to int
        try:
            header = BlockHeader(
                index=1.5,  # Float index
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
            # If it's coerced, verify it's an integer
            assert isinstance(header.index, int)
            assert header.index == 1
        except (ValueError, TypeError):
            # Rejection is also acceptable
            pass

    def test_string_difficulty(self, tmp_path):
        """Test block with string difficulty is coerced or rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        # String difficulty should be rejected or coerced
        try:
            header = BlockHeader(
                index=1,
                previous_hash="0" * 64,
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty="4",  # String instead of int
                nonce=0
            )
            # If coerced, verify it's an integer
            assert isinstance(header.difficulty, int)
        except (ValueError, TypeError):
            # Rejection is also acceptable
            pass

    def test_hash_recalculation_consistency(self, tmp_path):
        """Test that hash recalculation is consistent"""
        bc = Blockchain(data_dir=str(tmp_path))

        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=1234567890.0,  # Fixed timestamp
            difficulty=4,
            nonce=12345
        )

        # Calculate hash multiple times
        hash1 = header.calculate_hash()
        hash2 = header.calculate_hash()
        hash3 = header.hash

        # All should be identical
        assert hash1 == hash2 == hash3

    def test_null_byte_injection_in_hashes(self, tmp_path):
        """Test that null bytes in hash fields are handled properly"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Try to inject null bytes in hash
        with pytest.raises((ValueError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 32 + "\x00" + "0" * 31,  # Null byte injection
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )

    def test_extremely_large_nonce(self, tmp_path):
        """Test block with extremely large nonce value"""
        bc = Blockchain(data_dir=str(tmp_path))

        # Test with max integer value
        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=2**63 - 1  # Max signed 64-bit int
        )

        # Should handle large nonces gracefully
        assert isinstance(header.nonce, int)
        assert header.calculate_hash() is not None

    def test_corrupted_header_dict(self, tmp_path):
        """Test handling of corrupted header dictionary"""
        bc = Blockchain(data_dir=str(tmp_path))

        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=time.time(),
            difficulty=4,
            nonce=0
        )

        # Get dict and corrupt it
        header_dict = header.to_dict()
        header_dict['index'] = None  # Corrupt field

        # Attempting to use corrupted dict should fail safely
        with pytest.raises((ValueError, TypeError, KeyError)):
            # Simulate loading from corrupted data
            corrupted_header = BlockHeader(
                index=header_dict['index'],
                previous_hash=header_dict['previous_hash'],
                merkle_root=header_dict['merkle_root'],
                timestamp=header_dict['timestamp'],
                difficulty=header_dict['difficulty'],
                nonce=header_dict['nonce']
            )

    def test_unicode_in_hash_fields(self, tmp_path):
        """Test that unicode characters in hash fields are rejected"""
        bc = Blockchain(data_dir=str(tmp_path))

        with pytest.raises((ValueError, UnicodeEncodeError, TypeError)):
            header = BlockHeader(
                index=1,
                previous_hash="0" * 32 + "ñ" + "0" * 31,  # Unicode character
                merkle_root="0" * 64,
                timestamp=time.time(),
                difficulty=4,
                nonce=0
            )
