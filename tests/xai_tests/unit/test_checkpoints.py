"""
Tests for the Checkpoint System

Tests checkpoint creation, loading, validation, and long-range attack protection.
"""

import os
import json
import shutil
import tempfile
import pytest
from xai.core.blockchain import Blockchain, Block, Transaction
from xai.core.checkpoints import Checkpoint, CheckpointManager
from xai.core.utxo_manager import UTXOManager


class TestCheckpoint:
    """Test Checkpoint class"""

    def test_checkpoint_creation(self):
        """Test creating a checkpoint"""
        utxo_snapshot = {
            "utxo_set": {"addr1": [{"txid": "abc", "vout": 0, "amount": 100.0}]},
            "total_utxos": 1,
            "total_value": 100.0,
        }

        checkpoint = Checkpoint(
            height=1000,
            block_hash="block_hash_1000",
            previous_hash="block_hash_999",
            utxo_snapshot=utxo_snapshot,
            timestamp=1234567890.0,
            difficulty=4,
            total_supply=1000000.0,
            merkle_root="merkle_root",
            nonce=12345,
        )

        assert checkpoint.height == 1000
        assert checkpoint.block_hash == "block_hash_1000"
        assert checkpoint.utxo_snapshot == utxo_snapshot
        assert checkpoint.verify_integrity()

    def test_checkpoint_serialization(self):
        """Test checkpoint serialization and deserialization"""
        utxo_snapshot = {
            "utxo_set": {"addr1": [{"txid": "abc", "vout": 0, "amount": 100.0}]},
            "total_utxos": 1,
            "total_value": 100.0,
        }

        checkpoint = Checkpoint(
            height=1000,
            block_hash="block_hash_1000",
            previous_hash="block_hash_999",
            utxo_snapshot=utxo_snapshot,
            timestamp=1234567890.0,
            difficulty=4,
            total_supply=1000000.0,
            merkle_root="merkle_root",
            nonce=12345,
        )

        # Serialize
        data = checkpoint.to_dict()

        # Deserialize
        loaded_checkpoint = Checkpoint.from_dict(data)

        assert loaded_checkpoint.height == checkpoint.height
        assert loaded_checkpoint.block_hash == checkpoint.block_hash
        assert loaded_checkpoint.checkpoint_hash == checkpoint.checkpoint_hash
        assert loaded_checkpoint.verify_integrity()

    def test_checkpoint_integrity_verification(self):
        """Test checkpoint integrity verification detects tampering"""
        utxo_snapshot = {
            "utxo_set": {"addr1": [{"txid": "abc", "vout": 0, "amount": 100.0}]},
            "total_utxos": 1,
            "total_value": 100.0,
        }

        checkpoint = Checkpoint(
            height=1000,
            block_hash="block_hash_1000",
            previous_hash="block_hash_999",
            utxo_snapshot=utxo_snapshot,
            timestamp=1234567890.0,
            difficulty=4,
            total_supply=1000000.0,
            merkle_root="merkle_root",
            nonce=12345,
        )

        # Original is valid
        assert checkpoint.verify_integrity()

        # Tamper with data
        data = checkpoint.to_dict()
        data["block_hash"] = "tampered_hash"

        # Should raise error on deserialization
        with pytest.raises(ValueError):
            Checkpoint.from_dict(data)


class TestCheckpointManager:
    """Test CheckpointManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def checkpoint_manager(self, temp_dir):
        """Create checkpoint manager for tests"""
        return CheckpointManager(
            data_dir=temp_dir, checkpoint_interval=100, max_checkpoints=5
        )

    def test_checkpoint_manager_initialization(self, temp_dir):
        """Test checkpoint manager initialization"""
        manager = CheckpointManager(
            data_dir=temp_dir, checkpoint_interval=100, max_checkpoints=5
        )

        assert manager.checkpoint_interval == 100
        assert manager.max_checkpoints == 5
        assert os.path.exists(manager.checkpoints_dir)

    def test_should_create_checkpoint(self, checkpoint_manager):
        """Test checkpoint interval logic"""
        # Should create at interval
        assert checkpoint_manager.should_create_checkpoint(100)
        assert checkpoint_manager.should_create_checkpoint(200)
        assert checkpoint_manager.should_create_checkpoint(1000)

        # Should not create between intervals
        assert not checkpoint_manager.should_create_checkpoint(50)
        assert not checkpoint_manager.should_create_checkpoint(150)
        assert not checkpoint_manager.should_create_checkpoint(999)

    def test_checkpoint_save_and_load(self, checkpoint_manager, temp_dir):
        """Test saving and loading checkpoints"""
        # Create mock block and UTXO manager
        utxo_manager = UTXOManager()
        utxo_manager.add_utxo("addr1", "tx1", 0, 100.0, "script")

        tx = Transaction("COINBASE", "addr1", 100.0)
        tx.txid = tx.calculate_hash()
        block = Block(100, [tx], "prev_hash", 4)
        block.hash = "block_hash_100"

        # Create checkpoint
        checkpoint = checkpoint_manager.create_checkpoint(block, utxo_manager, 100.0)
        assert checkpoint is not None

        # Load checkpoint
        loaded = checkpoint_manager.load_checkpoint(100)
        assert loaded is not None
        assert loaded.height == 100
        assert loaded.block_hash == "block_hash_100"
        assert loaded.verify_integrity()

    def test_checkpoint_cleanup(self, checkpoint_manager, temp_dir):
        """Test automatic cleanup of old checkpoints"""
        utxo_manager = UTXOManager()

        # Create more checkpoints than max_checkpoints
        for i in range(10):
            height = (i + 1) * 100
            tx = Transaction("COINBASE", "addr1", 100.0)
            tx.txid = tx.calculate_hash()
            block = Block(height, [tx], "prev_hash", 4)
            block.hash = f"block_hash_{height}"

            checkpoint_manager.create_checkpoint(block, utxo_manager, 100.0)

        # Should only keep max_checkpoints (5)
        checkpoints = checkpoint_manager.list_checkpoints()
        assert len(checkpoints) == 5

        # Should keep the most recent ones
        assert 1000 in checkpoints
        assert 900 in checkpoints
        assert 800 in checkpoints
        assert 700 in checkpoints
        assert 600 in checkpoints

        # Older ones should be removed
        assert 100 not in checkpoints
        assert 200 not in checkpoints

    def test_load_latest_checkpoint(self, checkpoint_manager):
        """Test loading the latest checkpoint"""
        utxo_manager = UTXOManager()

        # Create multiple checkpoints
        for i in [1, 2, 3]:
            height = i * 100
            tx = Transaction("COINBASE", "addr1", 100.0)
            tx.txid = tx.calculate_hash()
            block = Block(height, [tx], "prev_hash", 4)
            block.hash = f"block_hash_{height}"

            checkpoint_manager.create_checkpoint(block, utxo_manager, 100.0)

        # Load latest
        latest = checkpoint_manager.load_latest_checkpoint()
        assert latest is not None
        assert latest.height == 300

    def test_is_before_checkpoint(self, checkpoint_manager):
        """Test checkpoint protection logic"""
        utxo_manager = UTXOManager()

        # Create checkpoint at height 1000
        tx = Transaction("COINBASE", "addr1", 100.0)
        tx.txid = tx.calculate_hash()
        block = Block(1000, [tx], "prev_hash", 4)
        block.hash = "block_hash_1000"

        checkpoint_manager.create_checkpoint(block, utxo_manager, 100.0)

        # Heights before checkpoint
        assert checkpoint_manager.is_before_checkpoint(500)
        assert checkpoint_manager.is_before_checkpoint(999)

        # Heights at or after checkpoint
        assert not checkpoint_manager.is_before_checkpoint(1000)
        assert not checkpoint_manager.is_before_checkpoint(1001)


class TestBlockchainCheckpoints:
    """Test blockchain integration with checkpoints"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_blockchain_checkpoint_integration(self, temp_dir):
        """Test blockchain creates checkpoints automatically"""
        # Create blockchain with small checkpoint interval
        blockchain = Blockchain(
            data_dir=temp_dir, checkpoint_interval=10, max_checkpoints=3
        )

        # Mine blocks to trigger checkpoint
        for i in range(15):
            blockchain.mine_pending_transactions("miner1")

        # Should have created checkpoint at block 10
        checkpoint = blockchain.checkpoint_manager.load_checkpoint(10)
        assert checkpoint is not None
        assert checkpoint.height == 10

    def test_blockchain_manual_checkpoint(self, temp_dir):
        """Test manual checkpoint creation"""
        blockchain = Blockchain(data_dir=temp_dir)

        # Mine some blocks
        for i in range(5):
            blockchain.mine_pending_transactions("miner1")

        # Create manual checkpoint
        result = blockchain.create_manual_checkpoint()
        assert result is not None
        assert result["success"]
        assert result["height"] == 5

    def test_blockchain_fast_recovery(self, temp_dir):
        """Test blockchain fast recovery from checkpoint"""
        # Create blockchain and mine blocks
        blockchain1 = Blockchain(
            data_dir=temp_dir, checkpoint_interval=10, max_checkpoints=3
        )

        for i in range(25):
            blockchain1.mine_pending_transactions("miner1")

        # Should have checkpoints at 10 and 20
        assert blockchain1.checkpoint_manager.load_checkpoint(10) is not None
        assert blockchain1.checkpoint_manager.load_checkpoint(20) is not None

        # Create new blockchain instance (simulating restart)
        blockchain2 = Blockchain(
            data_dir=temp_dir, checkpoint_interval=10, max_checkpoints=3
        )

        # Should have loaded from checkpoint
        assert len(blockchain2.chain) == 25
        assert blockchain2.checkpoint_manager.latest_checkpoint_height == 20

    def test_checkpoint_prevents_deep_reorg(self, temp_dir):
        """Test checkpoint prevents reorganization before checkpoint"""
        blockchain = Blockchain(
            data_dir=temp_dir, checkpoint_interval=10, max_checkpoints=3
        )

        # Mine 20 blocks
        for i in range(20):
            blockchain.mine_pending_transactions("miner1")

        # Try to create a fork before the checkpoint at block 10
        # This should be rejected
        original_chain = blockchain.chain.copy()

        # Create alternative chain that forks at block 5
        fork_chain = blockchain.chain[:5].copy()

        # Mine alternative blocks
        for i in range(20):
            tx = Transaction("COINBASE", "attacker", 100.0)
            tx.txid = tx.calculate_hash()
            new_block = Block(len(fork_chain), [tx], fork_chain[-1].hash, 4)
            new_block.hash = new_block.mine_block()
            fork_chain.append(new_block)

        # Try to replace chain (should fail due to checkpoint protection)
        result = blockchain.replace_chain(fork_chain)
        assert not result

        # Original chain should remain
        assert blockchain.chain == original_chain

    def test_checkpoint_info(self, temp_dir):
        """Test getting checkpoint information"""
        blockchain = Blockchain(
            data_dir=temp_dir, checkpoint_interval=10, max_checkpoints=3
        )

        # Mine blocks to create checkpoints
        for i in range(25):
            blockchain.mine_pending_transactions("miner1")

        # Get checkpoint info
        info = blockchain.get_checkpoint_info()

        assert "total_checkpoints" in info
        assert "latest_checkpoint_height" in info
        assert "checkpoint_interval" in info
        assert "available_checkpoints" in info

        assert info["total_checkpoints"] >= 2
        assert info["checkpoint_interval"] == 10
        assert info["latest_checkpoint_height"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
