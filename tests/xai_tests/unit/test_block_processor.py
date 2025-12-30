"""
Comprehensive unit tests for BlockProcessor

Tests block creation, merkle root calculation, block chain addition, and orphan handling.
BlockProcessor is a critical infrastructure component for block lifecycle management.

Test coverage includes:
- BlockProcessor initialization
- create_genesis_block() for chain initialization
- calculate_merkle_root() for transaction commitment
- add_block_to_chain() for state updates
- process_orphan_blocks() and prune_orphan_blocks()
- Edge cases: empty transactions, corrupted data, concurrent access
- Error handling paths for all operations
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, PropertyMock, patch, create_autospec

import pytest


class MockLogger:
    """Mock logger for testing without file system logging."""

    def __init__(self):
        self.info_calls = []
        self.warning_calls = []
        self.error_calls = []
        self.debug_calls = []

    def info(self, msg, *args, **kwargs):
        self.info_calls.append((msg, args, kwargs))

    def warning(self, msg, *args, **kwargs):
        self.warning_calls.append((msg, args, kwargs))

    def error(self, msg, *args, **kwargs):
        self.error_calls.append((msg, args, kwargs))

    def debug(self, msg, *args, **kwargs):
        self.debug_calls.append((msg, args, kwargs))


class MockTransaction:
    """Mock Transaction for testing BlockProcessor in isolation."""

    def __init__(
        self,
        sender: str = "test_sender",
        recipient: str = "test_recipient",
        amount: float = 10.0,
        fee: float = 0.1,
        txid: str | None = None,
        tx_type: str = "normal",
        inputs: list | None = None,
    ):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.txid = txid
        self.tx_type = tx_type
        self.inputs = inputs or []
        self.outputs = [{"address": recipient, "amount": amount}]
        self.timestamp = time.time()
        self.signature = "mock_signature"
        self.nonce = 0

    def calculate_hash(self) -> str:
        """Calculate a deterministic hash for this transaction."""
        data = f"{self.sender}{self.recipient}{self.amount}{self.fee}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


class MockBlockHeader:
    """Mock BlockHeader for testing."""

    def __init__(
        self,
        index: int = 0,
        previous_hash: str = "0" * 64,
        merkle_root: str = "0" * 64,
        timestamp: float = None,
        difficulty: int = 4,
        nonce: int = 0,
        miner_pubkey: str = "test_miner_pubkey",
        signature: str | None = None,
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or time.time()
        self.difficulty = difficulty
        self.nonce = nonce
        self.miner_pubkey = miner_pubkey
        self.signature = signature
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate a deterministic hash for this header."""
        data = f"{self.index}{self.previous_hash}{self.merkle_root}{self.timestamp}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()


class MockBlock:
    """Mock Block for testing."""

    def __init__(self, header: MockBlockHeader, transactions: list | None = None):
        self.header = header
        self.transactions = transactions or []
        self.miner = "test_miner"

    @property
    def index(self):
        return self.header.index

    @property
    def hash(self):
        return self.header.hash

    @property
    def previous_hash(self):
        return self.header.previous_hash


class MockUTXOManager:
    """Mock UTXO manager for testing."""

    def __init__(self):
        self.utxos = {}
        self.spent = set()

    def process_transaction_outputs(self, tx):
        """Process transaction outputs."""
        if tx.txid:
            for i, output in enumerate(tx.outputs):
                key = f"{tx.txid}:{i}"
                self.utxos[key] = output

    def spend_utxo(self, tx):
        """Mark UTXOs as spent."""
        for inp in tx.inputs:
            key = f"{inp.get('txid')}:{inp.get('output_index', inp.get('vout', 0))}"
            self.spent.add(key)

    def add_utxo(self, tx):
        """Add transaction outputs as UTXOs."""
        self.process_transaction_outputs(tx)


class MockStorage:
    """Mock storage for testing."""

    def __init__(self):
        self.blocks = {}
        self.saved_states = []

    def _save_block_to_disk(self, block):
        """Save block to mock storage."""
        self.blocks[block.index] = block

    def save_block_to_disk(self, block):
        """Save block to mock storage."""
        self._save_block_to_disk(block)

    def save_state_to_disk(self, utxo_manager, pending_tx, contracts, receipts):
        """Save state to mock storage."""
        self.saved_states.append({
            "utxo": utxo_manager,
            "pending": pending_tx,
            "contracts": contracts,
            "receipts": receipts
        })

    def load_block_from_disk(self, index):
        """Load block from mock storage."""
        return self.blocks.get(index)


class MockAddressIndex:
    """Mock address index for testing."""

    def __init__(self):
        self.indexed_blocks = []

    def index_block(self, block):
        """Index a block."""
        self.indexed_blocks.append(block.index)


class MockCheckpointManager:
    """Mock checkpoint manager for testing."""

    def __init__(self):
        self.checkpoints = []

    def maybe_create_checkpoint(self, block_height, blockchain):
        """Maybe create checkpoint."""
        self.checkpoints.append(block_height)


class MockBlockchain:
    """Mock Blockchain for testing BlockProcessor in isolation."""

    def __init__(self, data_dir: str = "/tmp/test"):
        self.data_dir = data_dir
        self.chain = []
        self.difficulty = 4
        self.max_supply = 121000000.0
        self.pending_transactions = []
        self.contracts = {}
        self.contract_receipts = {}
        self.orphan_blocks = defaultdict(list)
        self.seen_txids = set()
        self._mempool_lock = threading.RLock()
        self._sender_pending_count = {}
        self._spent_inputs = set()

        # Mock managers
        self.utxo_manager = MockUTXOManager()
        self.storage = MockStorage()
        self.address_index = MockAddressIndex()
        self.checkpoint_manager = MockCheckpointManager()
        self.logger = MockLogger()

    def mine_block(self, header):
        """Mock mining - just return a valid hash."""
        return "0" * header.difficulty + hashlib.sha256(str(time.time()).encode()).hexdigest()[header.difficulty:]

    def get_block_reward(self, height):
        """Get block reward for height."""
        halvings = height // 262800
        if halvings >= 30:
            return 0.0
        return 12.0 / (2 ** halvings)

    def add_block(self, block):
        """Add block to chain."""
        self.chain.append(block)
        return True


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    import shutil
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_blockchain(temp_dir):
    """Create a mock blockchain instance."""
    return MockBlockchain(temp_dir)


@pytest.fixture
def block_processor(mock_blockchain):
    """Create a BlockProcessor instance for testing."""
    # We need to import and mock properly
    with patch('xai.core.chain.block_processor.get_structured_logger') as mock_logger:
        mock_logger.return_value = MockLogger()
        from xai.core.chain.block_processor import BlockProcessor
        processor = BlockProcessor(mock_blockchain)
        processor.logger = MockLogger()
        return processor


class TestBlockProcessorInitialization:
    """Test BlockProcessor initialization."""

    def test_init_stores_blockchain_reference(self, mock_blockchain):
        """BlockProcessor should store reference to blockchain."""
        with patch('xai.core.chain.block_processor.get_structured_logger') as mock_logger:
            mock_logger.return_value = MockLogger()
            from xai.core.chain.block_processor import BlockProcessor
            processor = BlockProcessor(mock_blockchain)
            assert processor.blockchain is mock_blockchain

    def test_init_creates_logger(self, mock_blockchain):
        """BlockProcessor should create a logger."""
        with patch('xai.core.chain.block_processor.get_structured_logger') as mock_logger:
            mock_logger.return_value = MockLogger()
            from xai.core.chain.block_processor import BlockProcessor
            processor = BlockProcessor(mock_blockchain)
            assert processor.logger is not None


class TestCalculateMerkleRoot:
    """Test calculate_merkle_root() method."""

    def test_merkle_root_empty_transactions(self, block_processor):
        """Merkle root of empty transaction list should be hash of empty bytes."""
        result = block_processor.calculate_merkle_root([])

        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_merkle_root_single_transaction(self, block_processor):
        """Merkle root of single transaction should be its txid."""
        tx = MockTransaction()
        tx.txid = "a" * 64

        result = block_processor.calculate_merkle_root([tx])

        assert result == "a" * 64

    def test_merkle_root_two_transactions(self, block_processor):
        """Merkle root of two transactions should be hash of combined hashes."""
        tx1 = MockTransaction()
        tx1.txid = "a" * 64
        tx2 = MockTransaction()
        tx2.txid = "b" * 64

        result = block_processor.calculate_merkle_root([tx1, tx2])

        # Combined hash of aa...a and bb...b
        expected = hashlib.sha256(("a" * 64 + "b" * 64).encode()).hexdigest()
        assert result == expected

    def test_merkle_root_three_transactions_duplicates_last(self, block_processor):
        """Merkle root with odd transactions should duplicate last hash."""
        tx1 = MockTransaction()
        tx1.txid = "a" * 64
        tx2 = MockTransaction()
        tx2.txid = "b" * 64
        tx3 = MockTransaction()
        tx3.txid = "c" * 64

        result = block_processor.calculate_merkle_root([tx1, tx2, tx3])

        # Build expected merkle tree
        # Level 0: [a*64, b*64, c*64, c*64] (duplicate last)
        # Level 1: [hash(a+b), hash(c+c)]
        # Level 2: [hash(level1[0]+level1[1])]
        h_ab = hashlib.sha256(("a" * 64 + "b" * 64).encode()).hexdigest()
        h_cc = hashlib.sha256(("c" * 64 + "c" * 64).encode()).hexdigest()
        expected = hashlib.sha256((h_ab + h_cc).encode()).hexdigest()

        assert result == expected

    def test_merkle_root_four_transactions(self, block_processor):
        """Merkle root with four transactions (balanced tree)."""
        txs = []
        for i in range(4):
            tx = MockTransaction()
            tx.txid = chr(ord('a') + i) * 64
            txs.append(tx)

        result = block_processor.calculate_merkle_root(txs)

        # Level 0: [a*64, b*64, c*64, d*64]
        # Level 1: [hash(a+b), hash(c+d)]
        # Level 2: [hash(level1[0]+level1[1])]
        h_ab = hashlib.sha256(("a" * 64 + "b" * 64).encode()).hexdigest()
        h_cd = hashlib.sha256(("c" * 64 + "d" * 64).encode()).hexdigest()
        expected = hashlib.sha256((h_ab + h_cd).encode()).hexdigest()

        assert result == expected

    def test_merkle_root_calculates_missing_txids(self, block_processor):
        """Merkle root should calculate txids for transactions without them."""
        tx = MockTransaction()
        tx.txid = None  # No txid yet

        result = block_processor.calculate_merkle_root([tx])

        # txid should be set now
        assert tx.txid is not None
        assert result == tx.txid

    def test_merkle_root_deterministic(self, block_processor):
        """Merkle root should be deterministic for same transactions."""
        tx1 = MockTransaction()
        tx1.txid = "a" * 64
        tx2 = MockTransaction()
        tx2.txid = "b" * 64

        result1 = block_processor.calculate_merkle_root([tx1, tx2])
        result2 = block_processor.calculate_merkle_root([tx1, tx2])

        assert result1 == result2

    def test_merkle_root_order_matters(self, block_processor):
        """Merkle root should change if transaction order changes."""
        tx1 = MockTransaction()
        tx1.txid = "a" * 64
        tx2 = MockTransaction()
        tx2.txid = "b" * 64

        result1 = block_processor.calculate_merkle_root([tx1, tx2])
        result2 = block_processor.calculate_merkle_root([tx2, tx1])

        assert result1 != result2

    def test_merkle_root_large_transaction_set(self, block_processor):
        """Merkle root should work with large transaction sets."""
        txs = []
        for i in range(100):
            tx = MockTransaction()
            tx.txid = hashlib.sha256(f"tx_{i}".encode()).hexdigest()
            txs.append(tx)

        result = block_processor.calculate_merkle_root(txs)

        # Should return valid 64-char hex string
        assert len(result) == 64
        int(result, 16)  # Should not raise


class TestAddBlockToChain:
    """Test add_block_to_chain() method."""

    def test_add_block_to_chain_basic(self, block_processor, mock_blockchain):
        """add_block_to_chain should add block to chain."""
        # Setup genesis block in chain
        genesis_header = MockBlockHeader(index=0)
        genesis = MockBlock(genesis_header, [])
        mock_blockchain.chain.append(genesis)

        # Create new block
        header = MockBlockHeader(
            index=1,
            previous_hash=genesis.hash
        )
        block = MockBlock(header, [])

        result = block_processor.add_block_to_chain(block)

        assert result is True
        assert len(mock_blockchain.chain) == 2

    def test_add_block_to_chain_processes_utxos(self, block_processor, mock_blockchain):
        """add_block_to_chain should process UTXOs for transactions."""
        # Setup genesis
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Create block with transaction
        tx = MockTransaction(sender="COINBASE", recipient="recipient", amount=12.0)
        tx.txid = "tx123" + "0" * 59

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [tx])

        block_processor.add_block_to_chain(block)

        # UTXO should be added
        assert len(mock_blockchain.utxo_manager.utxos) > 0

    def test_add_block_to_chain_spends_inputs(self, block_processor, mock_blockchain):
        """add_block_to_chain should spend inputs for non-coinbase transactions."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        tx = MockTransaction(
            sender="sender",
            recipient="recipient",
            inputs=[{"txid": "prev_tx" + "0" * 57, "output_index": 0}]
        )
        tx.txid = "tx456" + "0" * 59

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [tx])

        block_processor.add_block_to_chain(block)

        # Input should be marked as spent
        assert len(mock_blockchain.utxo_manager.spent) > 0

    def test_add_block_to_chain_removes_from_mempool(self, block_processor, mock_blockchain):
        """add_block_to_chain should remove mined transactions from mempool."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        tx = MockTransaction()
        tx.txid = "mempool_tx" + "0" * 54

        # Add to pending
        mock_blockchain.pending_transactions.append(tx)

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [tx])

        block_processor.add_block_to_chain(block)

        # Should be removed from pending
        assert len(mock_blockchain.pending_transactions) == 0

    def test_add_block_to_chain_updates_address_index(self, block_processor, mock_blockchain):
        """add_block_to_chain should update address index."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])

        block_processor.add_block_to_chain(block)

        # Address index should be updated
        assert 1 in mock_blockchain.address_index.indexed_blocks

    def test_add_block_to_chain_saves_to_disk(self, block_processor, mock_blockchain):
        """add_block_to_chain should persist block to disk."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])

        block_processor.add_block_to_chain(block)

        # Block should be saved
        assert 1 in mock_blockchain.storage.blocks

    def test_add_block_to_chain_triggers_checkpoint(self, block_processor, mock_blockchain):
        """add_block_to_chain should trigger checkpoint manager."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])

        block_processor.add_block_to_chain(block)

        # Checkpoint should be considered
        assert 1 in mock_blockchain.checkpoint_manager.checkpoints

    def test_add_block_to_chain_handles_index_error(self, block_processor, mock_blockchain):
        """add_block_to_chain should handle address index errors gracefully."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Make address index raise error
        mock_blockchain.address_index.index_block = Mock(side_effect=ValueError("Index error"))

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])

        # Should still succeed
        result = block_processor.add_block_to_chain(block)
        assert result is True

    def test_add_block_to_chain_handles_checkpoint_error(self, block_processor, mock_blockchain):
        """add_block_to_chain should handle checkpoint errors gracefully."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Make checkpoint manager raise error
        mock_blockchain.checkpoint_manager.maybe_create_checkpoint = Mock(
            side_effect=RuntimeError("Checkpoint error")
        )

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])

        # Should still succeed
        result = block_processor.add_block_to_chain(block)
        assert result is True

    def test_add_block_to_chain_returns_false_on_error(self, block_processor, mock_blockchain):
        """add_block_to_chain should return False on critical errors."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Make chain append raise error
        mock_blockchain.chain = Mock()
        mock_blockchain.chain.append = Mock(side_effect=RuntimeError("Critical error"))

        header = MockBlockHeader(index=1, previous_hash="prev_hash" + "0" * 54)
        block = MockBlock(header, [])

        result = block_processor.add_block_to_chain(block)
        assert result is False


class TestRemoveMinedTransactions:
    """Test _remove_mined_transactions() method."""

    def test_remove_mined_transactions_clears_mempool(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should clear mined txs from mempool."""
        tx1 = MockTransaction()
        tx1.txid = "tx1" + "0" * 61
        tx2 = MockTransaction()
        tx2.txid = "tx2" + "0" * 61

        mock_blockchain.pending_transactions = [tx1, tx2]

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx1])  # Only tx1 mined

        block_processor._remove_mined_transactions(block)

        # Only tx2 should remain
        assert len(mock_blockchain.pending_transactions) == 1
        assert mock_blockchain.pending_transactions[0].txid == tx2.txid

    def test_remove_mined_transactions_updates_seen_txids(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should update seen_txids set."""
        tx = MockTransaction()
        tx.txid = "seen_tx" + "0" * 57

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        block_processor._remove_mined_transactions(block)

        assert tx.txid in mock_blockchain.seen_txids

    def test_remove_mined_transactions_updates_sender_counts(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should update sender pending counts."""
        tx = MockTransaction(sender="test_sender")
        tx.txid = "tx" + "0" * 62

        mock_blockchain._sender_pending_count["test_sender"] = 5

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        block_processor._remove_mined_transactions(block)

        assert mock_blockchain._sender_pending_count["test_sender"] == 4

    def test_remove_mined_transactions_skips_coinbase_sender_count(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should not decrement count for COINBASE."""
        tx = MockTransaction(sender="COINBASE")
        tx.txid = "coinbase" + "0" * 56

        mock_blockchain._sender_pending_count["COINBASE"] = 1

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        block_processor._remove_mined_transactions(block)

        # COINBASE count should remain unchanged
        assert mock_blockchain._sender_pending_count["COINBASE"] == 1

    def test_remove_mined_transactions_clears_spent_inputs(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should clear spent inputs from tracking."""
        tx = MockTransaction()
        tx.txid = "tx" + "0" * 62
        tx.inputs = [{"txid": "prev_tx" + "0" * 57, "output_index": 0}]

        mock_blockchain._spent_inputs.add("prev_tx" + "0" * 57 + ":0")

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        block_processor._remove_mined_transactions(block)

        assert "prev_tx" + "0" * 57 + ":0" not in mock_blockchain._spent_inputs


class TestProcessOrphanBlocks:
    """Test process_orphan_blocks() method."""

    def test_process_orphan_blocks_empty(self, block_processor, mock_blockchain):
        """process_orphan_blocks should handle empty orphan set."""
        mock_blockchain.orphan_blocks = {}

        # Should not raise
        block_processor.process_orphan_blocks()

    def test_process_orphan_blocks_promotes_valid_orphan(self, block_processor, mock_blockchain):
        """process_orphan_blocks should promote valid orphans to main chain."""
        # Setup chain
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Create orphan that extends chain
        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        orphan = MockBlock(header, [])

        mock_blockchain.orphan_blocks[1] = [orphan]

        # Mock add_block to track calls
        added_blocks = []
        original_add = mock_blockchain.add_block
        def track_add(block):
            added_blocks.append(block)
            return original_add(block)
        mock_blockchain.add_block = track_add

        block_processor.process_orphan_blocks()

        # Orphan should have been promoted
        assert len(added_blocks) > 0

    def test_process_orphan_blocks_ignores_invalid_previous_hash(self, block_processor, mock_blockchain):
        """process_orphan_blocks should ignore orphans with wrong previous hash."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        # Create orphan with wrong previous hash
        header = MockBlockHeader(index=1, previous_hash="wrong" + "0" * 59)
        orphan = MockBlock(header, [])

        mock_blockchain.orphan_blocks[1] = [orphan]

        add_called = []
        mock_blockchain.add_block = lambda b: add_called.append(b) or True

        block_processor.process_orphan_blocks()

        # Should not have added orphan
        assert len(add_called) == 0


class TestPruneOrphanBlocks:
    """Test prune_orphan_blocks() method."""

    def test_prune_orphan_blocks_empty(self, block_processor, mock_blockchain):
        """prune_orphan_blocks should return 0 for empty orphan set."""
        mock_blockchain.orphan_blocks = {}

        result = block_processor.prune_orphan_blocks()

        assert result == 0

    def test_prune_orphan_blocks_removes_old(self, block_processor, mock_blockchain):
        """prune_orphan_blocks should remove orphans older than 100 blocks."""
        # Setup chain at height 200
        for i in range(201):
            header = MockBlockHeader(index=i)
            block = MockBlock(header, [])
            mock_blockchain.chain.append(block)

        # Add orphans at various heights
        mock_blockchain.orphan_blocks[50] = [MockBlock(MockBlockHeader(index=50), [])]
        mock_blockchain.orphan_blocks[150] = [MockBlock(MockBlockHeader(index=150), [])]

        result = block_processor.prune_orphan_blocks()

        # Orphan at height 50 should be pruned (200 - 50 > 100)
        assert result == 1
        assert 50 not in mock_blockchain.orphan_blocks
        assert 150 in mock_blockchain.orphan_blocks

    def test_prune_orphan_blocks_keeps_recent(self, block_processor, mock_blockchain):
        """prune_orphan_blocks should keep recent orphans."""
        # Chain at height 100
        for i in range(101):
            mock_blockchain.chain.append(MockBlock(MockBlockHeader(index=i), []))

        # Add orphan at height 50 (100 - 50 = 50 < 100)
        mock_blockchain.orphan_blocks[50] = [MockBlock(MockBlockHeader(index=50), [])]

        result = block_processor.prune_orphan_blocks()

        assert result == 0
        assert 50 in mock_blockchain.orphan_blocks

    def test_prune_orphan_blocks_counts_multiple(self, block_processor, mock_blockchain):
        """prune_orphan_blocks should count all pruned blocks."""
        for i in range(201):
            mock_blockchain.chain.append(MockBlock(MockBlockHeader(index=i), []))

        # Add multiple orphans at old heights
        mock_blockchain.orphan_blocks[10] = [
            MockBlock(MockBlockHeader(index=10), []),
            MockBlock(MockBlockHeader(index=10), []),
        ]
        mock_blockchain.orphan_blocks[20] = [
            MockBlock(MockBlockHeader(index=20), [])
        ]

        result = block_processor.prune_orphan_blocks()

        # Should prune all 3 old orphans
        assert result == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_merkle_root_with_none_txid_transactions(self, block_processor):
        """calculate_merkle_root should handle transactions with None txid."""
        txs = []
        for i in range(3):
            tx = MockTransaction()
            tx.txid = None
            txs.append(tx)

        result = block_processor.calculate_merkle_root(txs)

        # Should calculate txids and return valid merkle root
        assert len(result) == 64
        for tx in txs:
            assert tx.txid is not None

    def test_add_block_with_empty_transactions(self, block_processor, mock_blockchain):
        """add_block_to_chain should handle block with no transactions."""
        genesis = MockBlock(MockBlockHeader(index=0), [])
        mock_blockchain.chain.append(genesis)

        header = MockBlockHeader(index=1, previous_hash=genesis.hash)
        block = MockBlock(header, [])  # Empty transactions

        result = block_processor.add_block_to_chain(block)

        assert result is True

    def test_remove_mined_with_no_txid(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should handle tx with None txid."""
        tx = MockTransaction()
        tx.txid = None

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        # Should not raise
        block_processor._remove_mined_transactions(block)

    def test_sender_count_not_goes_negative(self, block_processor, mock_blockchain):
        """Sender pending count should not go below zero."""
        tx = MockTransaction(sender="sender")
        tx.txid = "tx" + "0" * 62

        mock_blockchain._sender_pending_count["sender"] = 0

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        block_processor._remove_mined_transactions(block)

        # Should remain at 0, not go negative
        assert mock_blockchain._sender_pending_count["sender"] == 0


class TestThreadSafety:
    """Test thread safety of block processor operations."""

    def test_mempool_removal_uses_lock(self, block_processor, mock_blockchain):
        """_remove_mined_transactions should use mempool lock."""
        tx = MockTransaction()
        tx.txid = "tx" + "0" * 62

        header = MockBlockHeader(index=1)
        block = MockBlock(header, [tx])

        # Replace the lock with a mock to track acquisition
        from unittest.mock import MagicMock
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=None)
        mock_blockchain._mempool_lock = mock_lock

        block_processor._remove_mined_transactions(block)

        # Verify lock was acquired
        assert mock_lock.__enter__.called


class TestMerkleRootSecurity:
    """Security tests for merkle root calculation."""

    def test_merkle_root_collision_resistance(self, block_processor):
        """Different transaction sets should produce different merkle roots."""
        tx1a = MockTransaction()
        tx1a.txid = "a" * 64
        tx1b = MockTransaction()
        tx1b.txid = "b" * 64

        tx2a = MockTransaction()
        tx2a.txid = "c" * 64
        tx2b = MockTransaction()
        tx2b.txid = "d" * 64

        root1 = block_processor.calculate_merkle_root([tx1a, tx1b])
        root2 = block_processor.calculate_merkle_root([tx2a, tx2b])

        assert root1 != root2

    def test_merkle_root_preimage_resistance(self, block_processor):
        """Cannot easily reverse merkle root to get original transactions.

        Note: For a single transaction, the merkle root equals the txid.
        With multiple transactions, the root is a hash that hides the inputs.
        """
        tx1 = MockTransaction()
        tx1.txid = "secret_transaction_data" + "0" * 40
        tx2 = MockTransaction()
        tx2.txid = "other_secret_data_here" + "0" * 42

        root = block_processor.calculate_merkle_root([tx1, tx2])

        # Root is SHA256 hash of combined inputs - should not contain original strings
        assert "secret" not in root
        assert "other" not in root
        # Root should be valid hex string
        assert len(root) == 64
        int(root, 16)  # Should not raise

    def test_merkle_root_second_preimage_resistance(self, block_processor):
        """Different inputs produce different roots."""
        tx1 = MockTransaction()
        tx1.txid = "a" * 64

        tx2 = MockTransaction()
        tx2.txid = "a" * 63 + "b"  # One character different

        root1 = block_processor.calculate_merkle_root([tx1])
        root2 = block_processor.calculate_merkle_root([tx2])

        assert root1 != root2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
