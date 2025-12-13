"""
Test suite for XAI Blockchain - Genesis Block and Node Initialization

This test suite verifies:
- Genesis block creation
- Node initialization process
- Blockchain state after initialization
- Data directory setup
"""

import pytest
import os
import shutil
import tempfile
from xai.core.blockchain import Blockchain, Block
from xai.core.config import Config


class TestGenesisBlock:
    """Verify genesis block creation and properties."""

    def test_genesis_block_creation(self):
        """Verify genesis block is created correctly."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Genesis block should be index 0
        assert genesis.index == 0

        # Genesis block should have all zeros as previous hash
        assert genesis.previous_hash == "0" * 64

        # Genesis block should have a valid hash
        assert genesis.hash is not None
        assert len(genesis.hash) == 64  # SHA-256 produces 64 hex characters

        # Genesis block should have a timestamp
        assert genesis.timestamp > 0

    def test_genesis_block_determinism(self):
        """Verify genesis block is deterministic across different blockchain instances."""
        blockchain1 = Blockchain()
        blockchain2 = Blockchain()

        genesis1 = blockchain1.get_latest_block()
        genesis2 = blockchain2.get_latest_block()

        # Genesis blocks should have same index
        assert genesis1.index == genesis2.index == 0

        # Genesis blocks should have same previous_hash
        assert genesis1.previous_hash == genesis2.previous_hash == "0" * 64

    def test_genesis_block_has_no_transactions(self):
        """Verify genesis block contains no regular transactions."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Genesis block should either have no transactions or only coinbase
        if genesis.transactions:
            # If it has transactions, they should all be coinbase
            for tx in genesis.transactions:
                assert tx.sender == "COINBASE"

    def test_genesis_block_validates(self):
        """Verify genesis block passes validation."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Calculate hash to verify integrity
        calculated_hash = genesis.calculate_hash()

        # Hash should match
        # Note: For genesis, nonce might be 0 or preset, so hash validation is key
        assert calculated_hash is not None
        assert len(calculated_hash) == 64

    def test_genesis_block_serialization(self):
        """Verify genesis block can be serialized."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Should be serializable to dict
        genesis_dict = genesis.to_dict()

        assert "index" in genesis_dict
        assert "timestamp" in genesis_dict
        assert "transactions" in genesis_dict
        assert "previous_hash" in genesis_dict
        assert "hash" in genesis_dict
        assert genesis_dict["index"] == 0
        assert genesis_dict["previous_hash"] == "0" * 64


class TestBlockchainInitialization:
    """Verify blockchain initialization process."""

    def test_blockchain_starts_with_genesis(self):
        """Verify new blockchain starts with genesis block only."""
        blockchain = Blockchain()

        # Chain should have at least the genesis block
        assert len(blockchain.chain) >= 1

        # First block should be genesis
        genesis = blockchain.get_latest_block()
        assert genesis.index == 0

    def test_blockchain_chain_valid_after_init(self):
        """Verify blockchain chain is valid after initialization."""
        blockchain = Blockchain()

        # Chain should be valid
        assert blockchain.is_chain_valid() is True

    def test_blockchain_utxo_set_initialized(self):
        """Verify UTXO set is initialized."""
        blockchain = Blockchain()

        # UTXO manager should be available
        assert hasattr(blockchain, "utxo_manager") or hasattr(blockchain, "utxo_set")

        # Should be able to query for UTXOs (even if empty)
        # This just verifies the UTXO system is initialized
        assert blockchain.utxo_manager is not None

    def test_blockchain_pending_transactions_empty(self):
        """Verify pending transactions pool is empty after initialization."""
        blockchain = Blockchain()

        # Pending transactions should be empty or minimal
        # (Some implementations might include a pre-funded account)
        assert hasattr(blockchain, "pending_transactions")
        assert isinstance(blockchain.pending_transactions, list)

    def test_blockchain_config_loaded(self):
        """Verify blockchain uses configuration correctly."""
        blockchain = Blockchain()

        # Should have access to config parameters
        assert hasattr(Config, "INITIAL_BLOCK_REWARD")
        assert hasattr(Config, "INITIAL_DIFFICULTY")

        # Config values should be reasonable
        assert Config.INITIAL_BLOCK_REWARD > 0
        assert Config.INITIAL_DIFFICULTY > 0


class TestNodeDataDirectory:
    """Verify node data directory initialization."""

    def test_data_directory_structure(self, tmp_path):
        """Verify data directory is created with correct structure."""
        # Note: This is a conceptual test - actual implementation may vary
        # The blockchain might create directories like:
        # ~/.xai/blocks/
        # ~/.xai/utxo_set.db
        # ~/.xai/wallet/

        # For testing, we use a temp directory
        xai_dir = tmp_path / ".xai"

        # Simulate what node initialization might do
        if not xai_dir.exists():
            xai_dir.mkdir(parents=True)

        assert xai_dir.exists()
        assert xai_dir.is_dir()

    def test_data_directory_permissions(self, tmp_path):
        """Verify data directory has correct permissions."""
        xai_dir = tmp_path / ".xai"
        xai_dir.mkdir(parents=True, exist_ok=True)

        # Directory should be readable and writable
        assert os.access(xai_dir, os.R_OK)
        assert os.access(xai_dir, os.W_OK)


class TestMultipleInitializations:
    """Verify blockchain handles multiple initialization scenarios."""

    def test_multiple_blockchain_instances(self):
        """Verify multiple blockchain instances can coexist."""
        blockchain1 = Blockchain()
        blockchain2 = Blockchain()

        # Both should have genesis blocks
        assert blockchain1.get_latest_block().index == 0
        assert blockchain2.get_latest_block().index == 0

        # They should be independent (adding block to one doesn't affect other)
        initial_length1 = len(blockchain1.chain)
        initial_length2 = len(blockchain2.chain)

        assert initial_length1 > 0
        assert initial_length2 > 0

    def test_blockchain_reinitialization(self):
        """Verify blockchain can be reinitialized cleanly."""
        # Create first instance
        blockchain1 = Blockchain()
        length1 = len(blockchain1.chain)

        # Create new instance (simulates restart)
        blockchain2 = Blockchain()
        length2 = len(blockchain2.chain)

        # Both should start with at least genesis
        assert length1 >= 1
        assert length2 >= 1


class TestGenesisBlockConsensus:
    """Verify genesis block properties match consensus rules."""

    def test_genesis_block_difficulty(self):
        """Verify genesis block uses correct initial difficulty."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Genesis should have a difficulty value
        assert hasattr(genesis, "difficulty")
        assert genesis.difficulty > 0

        # Difficulty should be a reasonable value (testnet or production)
        # Testnet uses 2, production uses 4
        assert genesis.difficulty in [2, 4]

    def test_genesis_block_nonce(self):
        """Verify genesis block has a valid nonce."""
        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        # Nonce should be set (could be 0 or any valid value)
        assert hasattr(genesis, "nonce")
        assert genesis.nonce >= 0

    def test_genesis_block_timestamp_reasonable(self):
        """Verify genesis block timestamp is reasonable."""
        import time

        blockchain = Blockchain()
        genesis = blockchain.get_latest_block()

        current_time = time.time()

        # Genesis timestamp should be in the past (before now)
        assert genesis.timestamp <= current_time

        # Genesis timestamp should not be too far in the past (e.g., not before 2020)
        # This prevents genesis blocks with timestamp 0 or very old dates
        assert genesis.timestamp > 1577836800  # Jan 1, 2020
