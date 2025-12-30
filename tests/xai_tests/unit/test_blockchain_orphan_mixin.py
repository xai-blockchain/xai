"""Unit tests for BlockchainOrphanMixin methods."""

import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from xai.core.blockchain_components.orphan_mixin import BlockchainOrphanMixin


class MockBlock:
    """Mock block for testing."""

    def __init__(self, index, previous_hash, block_hash, transactions=None, timestamp=None):
        self.index = index
        self.hash = block_hash
        self.header = MagicMock()
        self.header.previous_hash = previous_hash
        self.transactions = transactions or []
        self.timestamp = timestamp or time.time()


class MockTransaction:
    """Mock transaction for testing."""

    def __init__(self, txid, sender="USER", inputs=None, timestamp=None):
        self.txid = txid
        self.sender = sender
        self.inputs = inputs or []
        self.timestamp = timestamp or time.time()


class MockBlockchain(BlockchainOrphanMixin):
    """Mock blockchain for testing orphan mixin methods."""

    def __init__(self):
        self.chain = [MockBlock(0, "", "genesis_hash")]
        self.orphan_blocks = {}
        self.orphan_transactions = []
        self.pending_transactions = []
        self._cumulative_tx_count = 0
        self.logger = MagicMock()
        self.utxo_manager = MagicMock()
        self.address_index = MagicMock()
        self.storage = MagicMock()
        self.contracts = {}
        self.contract_receipts = {}
        self.transaction_validator = MagicMock()

    def _process_governance_block_transactions(self, block):
        pass

    def _calculate_chain_work(self, chain):
        # Simple work calculation: length * 1000
        return len(chain) * 1000

    def _validate_chain_structure(self, chain):
        return True

    def replace_chain(self, new_chain):
        self.chain = new_chain
        return True


class TestProcessOrphanBlocks:
    """Tests for _process_orphan_blocks method."""

    def test_no_orphans(self):
        blockchain = MockBlockchain()
        blockchain.orphan_blocks = {}

        blockchain._process_orphan_blocks()

        assert len(blockchain.chain) == 1  # Just genesis

    def test_orphan_not_at_next_index(self):
        blockchain = MockBlockchain()
        # Orphan at index 5, but chain length is 1
        blockchain.orphan_blocks = {
            5: [MockBlock(5, "hash4", "hash5")]
        }

        blockchain._process_orphan_blocks()

        assert len(blockchain.chain) == 1
        assert 5 in blockchain.orphan_blocks

    def test_orphan_wrong_previous_hash(self):
        blockchain = MockBlockchain()
        # Orphan at correct index but wrong previous hash
        blockchain.orphan_blocks = {
            1: [MockBlock(1, "wrong_hash", "hash1")]
        }

        blockchain._process_orphan_blocks()

        assert len(blockchain.chain) == 1
        assert 1 in blockchain.orphan_blocks

    def test_connects_valid_orphan(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1", "COINBASE")
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [tx])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        assert len(blockchain.chain) == 2
        assert blockchain.chain[1].hash == "block1_hash"
        assert 1 not in blockchain.orphan_blocks

    def test_connects_multiple_orphans(self):
        blockchain = MockBlockchain()
        orphan1 = MockBlock(1, "genesis_hash", "block1_hash", [])
        orphan2 = MockBlock(2, "block1_hash", "block2_hash", [])
        blockchain.orphan_blocks = {
            1: [orphan1],
            2: [orphan2]
        }

        blockchain._process_orphan_blocks()

        assert len(blockchain.chain) == 3
        assert blockchain.chain[1].hash == "block1_hash"
        assert blockchain.chain[2].hash == "block2_hash"

    def test_processes_non_coinbase_inputs(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1", "USER", inputs=[{"txid": "prev", "vout": 0}])
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [tx])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        blockchain.utxo_manager.process_transaction_inputs.assert_called_once()
        blockchain.utxo_manager.process_transaction_outputs.assert_called()

    def test_skips_coinbase_inputs(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1", "COINBASE")
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [tx])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        blockchain.utxo_manager.process_transaction_inputs.assert_not_called()
        blockchain.utxo_manager.process_transaction_outputs.assert_called()

    def test_indexes_transactions(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1")
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [tx])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        blockchain.address_index.index_transaction.assert_called()
        blockchain.address_index.commit.assert_called()

    def test_handles_indexing_error(self):
        blockchain = MockBlockchain()
        from xai.core.chain.blockchain_exceptions import DatabaseError
        blockchain.address_index.index_transaction.side_effect = DatabaseError("test")

        tx = MockTransaction("tx1")
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [tx])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        blockchain.address_index.rollback.assert_called()
        blockchain.logger.error.assert_called()

    def test_saves_to_storage(self):
        blockchain = MockBlockchain()
        orphan = MockBlock(1, "genesis_hash", "block1_hash", [])
        blockchain.orphan_blocks = {1: [orphan]}

        blockchain._process_orphan_blocks()

        blockchain.storage._save_block_to_disk.assert_called_once()
        blockchain.storage.save_state_to_disk.assert_called_once()


class TestProcessOrphanTransactions:
    """Tests for _process_orphan_transactions method."""

    def test_no_orphan_transactions(self):
        blockchain = MockBlockchain()
        blockchain.orphan_transactions = []

        blockchain._process_orphan_transactions()

        assert len(blockchain.pending_transactions) == 0

    def test_adds_valid_orphan(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1")
        blockchain.orphan_transactions = [tx]
        blockchain.transaction_validator.validate_transaction.return_value = True

        blockchain._process_orphan_transactions()

        assert len(blockchain.pending_transactions) == 1
        assert len(blockchain.orphan_transactions) == 0

    def test_keeps_invalid_orphan(self):
        blockchain = MockBlockchain()
        tx = MockTransaction("tx1")
        blockchain.orphan_transactions = [tx]
        blockchain.transaction_validator.validate_transaction.return_value = False

        blockchain._process_orphan_transactions()

        assert len(blockchain.pending_transactions) == 0
        # Note: Still in orphan list but will be pruned if old

    def test_detects_double_spend(self):
        blockchain = MockBlockchain()
        # Create orphan transaction that references same input as pending
        orphan_tx = MockTransaction("tx2", inputs=[{"txid": "shared", "vout": 0}])
        pending_tx = MockTransaction("tx1", inputs=[{"txid": "shared", "vout": 0}])

        blockchain.orphan_transactions = [orphan_tx]
        blockchain.pending_transactions = [pending_tx]
        blockchain.transaction_validator.validate_transaction.return_value = True

        blockchain._process_orphan_transactions()

        # Should not add duplicate
        assert len(blockchain.pending_transactions) == 1
        assert blockchain.pending_transactions[0].txid == "tx1"

    def test_prunes_old_orphans(self):
        blockchain = MockBlockchain()
        # Create old orphan (older than 24 hours)
        old_tx = MockTransaction("old_tx", timestamp=time.time() - 100000)
        blockchain.orphan_transactions = [old_tx]
        blockchain.transaction_validator.validate_transaction.return_value = False

        blockchain._process_orphan_transactions()

        assert len(blockchain.orphan_transactions) == 0

    def test_keeps_recent_orphans(self):
        blockchain = MockBlockchain()
        recent_tx = MockTransaction("recent_tx", timestamp=time.time() - 3600)
        blockchain.orphan_transactions = [recent_tx]
        blockchain.transaction_validator.validate_transaction.return_value = False

        blockchain._process_orphan_transactions()

        assert len(blockchain.orphan_transactions) == 1


class TestCheckOrphanChainsForReorg:
    """Tests for _check_orphan_chains_for_reorg method."""

    def test_no_orphans(self):
        blockchain = MockBlockchain()
        blockchain.orphan_blocks = {}

        result = blockchain._check_orphan_chains_for_reorg()

        assert result is False

    def test_no_chain_with_more_work(self):
        blockchain = MockBlockchain()
        # Chain has 3 blocks, orphan chain is shorter so less work
        genesis = MockBlock(0, "", "genesis")
        block1 = MockBlock(1, "genesis", "block1")
        block2 = MockBlock(2, "block1", "block2")
        blockchain.chain = [genesis, block1, block2]

        # Orphan at index 1 with wrong prev hash (can't connect)
        orphan = MockBlock(1, "other_genesis", "orphan1")
        blockchain.orphan_blocks = {1: [orphan]}

        result = blockchain._check_orphan_chains_for_reorg()

        # Orphan can't connect due to wrong prev_hash
        assert result is False

    def test_reorg_to_heavier_chain(self):
        blockchain = MockBlockchain()
        genesis = MockBlock(0, "", "genesis")
        blockchain.chain = [genesis, MockBlock(1, "genesis", "block1")]

        # Create orphan chain with more work
        orphan1 = MockBlock(1, "genesis", "orphan1")
        orphan2 = MockBlock(2, "orphan1", "orphan2")
        orphan3 = MockBlock(3, "orphan2", "orphan3")
        blockchain.orphan_blocks = {
            1: [orphan1],
            2: [orphan2],
            3: [orphan3]
        }

        result = blockchain._check_orphan_chains_for_reorg()

        assert result is True
        assert len(blockchain.chain) == 4

    def test_orphan_with_wrong_prev_hash_ignored(self):
        blockchain = MockBlockchain()
        blockchain.chain = [MockBlock(0, "", "genesis")]

        # Orphan with wrong previous hash
        bad_orphan = MockBlock(1, "wrong_hash", "block1")
        blockchain.orphan_blocks = {1: [bad_orphan]}

        result = blockchain._check_orphan_chains_for_reorg()

        assert result is False
        assert len(blockchain.chain) == 1


class TestPruneOrphans:
    """Tests for _prune_orphans method."""

    def test_no_orphans(self):
        blockchain = MockBlockchain()
        blockchain.orphan_blocks = {}

        blockchain._prune_orphans()

        assert blockchain.orphan_blocks == {}

    def test_keeps_recent_orphans(self):
        blockchain = MockBlockchain()
        # Chain length is 10, orphans at index 5 should be kept (within 100)
        blockchain.chain = [MockBlock(i, f"hash{i-1}", f"hash{i}") for i in range(10)]
        blockchain.chain[0] = MockBlock(0, "", "hash0")
        blockchain.orphan_blocks = {
            5: [MockBlock(5, "hash4", "orphan5")]
        }

        blockchain._prune_orphans()

        assert 5 in blockchain.orphan_blocks

    def test_prunes_old_orphans(self):
        blockchain = MockBlockchain()
        # Chain length is 200, orphans at index 50 should be pruned (>100 blocks old)
        blockchain.chain = [MockBlock(i, f"hash{i-1}", f"hash{i}") for i in range(200)]
        blockchain.chain[0] = MockBlock(0, "", "hash0")
        blockchain.orphan_blocks = {
            50: [MockBlock(50, "hash49", "orphan50")],
            150: [MockBlock(150, "hash149", "orphan150")]
        }

        blockchain._prune_orphans()

        assert 50 not in blockchain.orphan_blocks
        assert 150 in blockchain.orphan_blocks

    def test_logs_pruned_orphans(self):
        blockchain = MockBlockchain()
        blockchain.chain = [MockBlock(i, f"hash{i-1}", f"hash{i}") for i in range(200)]
        blockchain.chain[0] = MockBlock(0, "", "hash0")
        blockchain.orphan_blocks = {
            10: [MockBlock(10, "hash9", "orphan10")]
        }

        blockchain._prune_orphans()

        blockchain.logger.debug.assert_called()
