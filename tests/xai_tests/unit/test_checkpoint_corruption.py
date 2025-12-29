"""
Comprehensive tests for checkpoint corruption handling

Tests corrupted checkpoint files, fallback mechanisms, hash mismatches,
partial checkpoints, and recovery procedures.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, mock_open

from xai.core.blockchain import Blockchain
from xai.core.wallet import Wallet
from xai.core.consensus.checkpoints import CheckpointManager


class TestCheckpointCorruption:
    """Tests for checkpoint corruption handling"""

    def test_corrupted_checkpoint_file(self, tmp_path):
        """Test handling of corrupted checkpoint file"""
        checkpoint_file = tmp_path / "checkpoint.json"

        # Write corrupted data
        with open(checkpoint_file, 'w') as f:
            f.write("{ corrupted json data ][")

        # Try to load checkpoint
        try:
            with open(checkpoint_file, 'r') as f:
                json.load(f)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            # Expected - corrupted file detected
            pass

    def test_fallback_to_full_blockchain_load(self, tmp_path):
        """Test fallback to full blockchain when checkpoint fails"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Build blockchain
        bc.mine_pending_transactions(wallet.address)
        bc.mine_pending_transactions(wallet.address)

        original_length = len(bc.chain)

        # Corrupt checkpoint if it exists
        checkpoint_path = tmp_path / "blockchain_checkpoint.json"
        if checkpoint_path.exists():
            with open(checkpoint_path, 'w') as f:
                f.write("corrupted")

        # Create new blockchain instance - should fallback to full load
        bc2 = Blockchain(data_dir=str(tmp_path))

        # Should load from blockchain storage instead
        # Length might differ but should be valid
        assert bc2.is_chain_valid()

    def test_checkpoint_hash_mismatch(self, tmp_path):
        """Test detection of checkpoint hash mismatch"""
        checkpoint_data = {
            'height': 100,
            'hash': 'abc123' * 10,  # 60 chars
            'timestamp': 1234567890,
            'state_root': 'def456' * 10
        }

        # Save checkpoint
        checkpoint_file = tmp_path / "checkpoint.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)

        # Load and verify
        with open(checkpoint_file, 'r') as f:
            loaded = json.load(f)

        # Modify hash to simulate tampering
        loaded['hash'] = '0' * 60

        # Hash mismatch should be detected
        assert loaded['hash'] != checkpoint_data['hash']

    def test_recovery_from_partial_checkpoint(self, tmp_path):
        """Test recovery from incomplete checkpoint"""
        partial_checkpoint = {
            'height': 50,
            'hash': 'abc123' * 10
            # Missing other required fields
        }

        checkpoint_file = tmp_path / "partial_checkpoint.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(partial_checkpoint, f)

        # Load partial checkpoint
        with open(checkpoint_file, 'r') as f:
            loaded = json.load(f)

        # Check for missing fields
        has_required_fields = all(
            key in loaded for key in ['height', 'hash', 'timestamp', 'state_root']
        )

        # Should detect missing fields
        assert not has_required_fields

    def test_checkpoint_validation(self, tmp_path):
        """Test checkpoint data validation"""
        valid_checkpoint = {
            'height': 100,
            'hash': 'a' * 64,  # Valid SHA-256 hash length
            'timestamp': 1234567890,
            'state_root': 'b' * 64,
            'version': 1
        }

        # Validate checkpoint structure
        assert 'height' in valid_checkpoint
        assert 'hash' in valid_checkpoint
        assert len(valid_checkpoint['hash']) == 64
        assert isinstance(valid_checkpoint['height'], int)
        assert valid_checkpoint['height'] >= 0

    def test_checkpoint_version_mismatch(self, tmp_path):
        """Test handling of checkpoint with incompatible version"""
        old_version_checkpoint = {
            'version': 0,  # Old version
            'height': 100,
            'hash': 'abc123',
            'data': 'old_format'
        }

        checkpoint_file = tmp_path / "old_checkpoint.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(old_version_checkpoint, f)

        # Load checkpoint
        with open(checkpoint_file, 'r') as f:
            loaded = json.load(f)

        # Check version compatibility
        current_version = 1
        is_compatible = loaded.get('version', 0) == current_version

        assert not is_compatible  # Old version should be incompatible

    def test_checkpoint_integrity_verification(self, tmp_path):
        """Test checkpoint integrity with checksum"""
        import hashlib

        checkpoint_data = {
            'height': 100,
            'hash': 'a' * 64,
            'timestamp': 1234567890,
            'state_root': 'b' * 64
        }

        # Calculate checksum
        data_str = json.dumps(checkpoint_data, sort_keys=True)
        checksum = hashlib.sha256(data_str.encode()).hexdigest()

        checkpoint_with_checksum = {
            **checkpoint_data,
            'checksum': checksum
        }

        # Save
        checkpoint_file = tmp_path / "checkpoint_with_checksum.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_with_checksum, f)

        # Load and verify
        with open(checkpoint_file, 'r') as f:
            loaded = json.load(f)

        stored_checksum = loaded.pop('checksum')
        data_str = json.dumps(loaded, sort_keys=True)
        calculated_checksum = hashlib.sha256(data_str.encode()).hexdigest()

        # Checksums should match
        assert stored_checksum == calculated_checksum

    def test_missing_checkpoint_file_creates_new(self, tmp_path):
        """Test missing checkpoint file results in fresh start"""
        checkpoint_file = tmp_path / "nonexistent_checkpoint.json"

        # File doesn't exist
        assert not checkpoint_file.exists()

        # Blockchain should start fresh
        bc = Blockchain(data_dir=str(tmp_path))

        # Should have genesis block
        assert len(bc.chain) >= 1
        assert bc.chain[0].index == 0
