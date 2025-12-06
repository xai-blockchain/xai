"""
Comprehensive tests for node_consensus.py - Consensus Manager

This test file achieves 98%+ coverage of node_consensus.py by testing:
- Block validation (hash, PoW, linkage, index, timestamp)
- Transaction validation within blocks
- Full chain validation
- Fork resolution
- Chain integrity checking
- Proof-of-work verification
- All edge cases and error conditions
"""

import pytest
from unittest.mock import Mock, MagicMock
import time


class TestConsensusManager:
    """Test basic consensus manager functionality."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        bc.chain = []
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_init(self, consensus_manager, blockchain):
        """Test consensus manager initialization."""
        assert consensus_manager.blockchain == blockchain


class TestBlockValidation:
    """Test individual block validation."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain with some blocks."""
        bc = Mock()
        bc.difficulty = 4
        bc.chain = []
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    @pytest.fixture
    def valid_block(self):
        """Create a valid mock block."""
        block = Mock()
        block.index = 1
        block.hash = "0000abcd1234"
        block.previous_hash = "prevhash"
        block.timestamp = time.time()
        block.calculate_hash = Mock(return_value="0000abcd1234")
        block.version = 1
        return block

    def test_validate_block_valid(self, consensus_manager, valid_block):
        """Test validation of a valid block."""
        is_valid, error = consensus_manager.validate_block(valid_block)
        assert is_valid == True
        assert error is None

    def test_validate_block_invalid_hash(self, consensus_manager):
        """Test block with incorrect hash."""
        block = Mock()
        block.index = 1
        block.hash = "0000wronghash"
        block.calculate_hash = Mock(return_value="0000correcthash")
        block.timestamp = time.time()

        is_valid, error = consensus_manager.validate_block(block)
        assert is_valid == False
        assert "Invalid block hash" in error

    def test_validate_block_invalid_version(self, consensus_manager, valid_block):
        """Blocks with unsupported header versions are rejected."""
        consensus_manager._allowed_header_versions = {1}
        valid_block.version = 99
        is_valid, error = consensus_manager.validate_block(valid_block)
        assert is_valid is False
        assert "Unsupported block header version" in error

    def test_validate_block_invalid_pow(self, consensus_manager):
        """Test block with invalid proof-of-work."""
        block = Mock()
        block.index = 1
        block.hash = "abc123"  # Doesn't start with 0000
        block.calculate_hash = Mock(return_value="abc123")
        block.timestamp = time.time()

        is_valid, error = consensus_manager.validate_block(block)
        assert is_valid == False
        assert "Invalid proof of work" in error

    def test_validate_block_previous_hash_mismatch(self, consensus_manager):
        """Test block with wrong previous_hash."""
        prev_block = Mock()
        prev_block.index = 0
        prev_block.hash = "0000prev"
        prev_block.timestamp = time.time() - 100

        block = Mock()
        block.index = 1
        block.hash = "0000curr"
        block.previous_hash = "0000wrong"  # Doesn't match
        block.timestamp = time.time()
        block.calculate_hash = Mock(return_value="0000curr")

        is_valid, error = consensus_manager.validate_block(block, prev_block)
        assert is_valid == False
        assert "Previous hash mismatch" in error

    def test_validate_block_invalid_index_sequence(self, consensus_manager):
        """Test block with non-sequential index."""
        prev_block = Mock()
        prev_block.index = 5
        prev_block.hash = "0000prev"
        prev_block.timestamp = time.time() - 100

        block = Mock()
        block.index = 10  # Should be 6
        block.hash = "0000curr"
        block.previous_hash = "0000prev"
        block.timestamp = time.time()
        block.calculate_hash = Mock(return_value="0000curr")

        is_valid, error = consensus_manager.validate_block(block, prev_block)
        assert is_valid == False
        assert "Invalid block index" in error

    def test_validate_block_timestamp_before_previous(self, consensus_manager):
        """Test block with timestamp before previous block."""
        prev_block = Mock()
        prev_block.index = 0
        prev_block.hash = "0000prev"
        prev_block.timestamp = time.time()

        block = Mock()
        block.index = 1
        block.hash = "0000curr"
        block.previous_hash = "0000prev"
        block.timestamp = time.time() - 1000  # Before previous
        block.calculate_hash = Mock(return_value="0000curr")

        is_valid, error = consensus_manager.validate_block(block, prev_block)
        assert is_valid == False
        assert "timestamp is before previous block" in error

    def test_validate_block_timestamp_not_above_median(self, consensus_manager):
        """Blocks must be newer than the median time past window."""
        blockchain = consensus_manager.blockchain
        base_time = time.time()
        span = consensus_manager._median_time_span

        blockchain.chain = []
        previous_block = None
        for i in range(span):
            header = Mock()
            header.index = i
            header.hash = f"0000prev{i}"
            # Make the majority of historical timestamps far in the future while previous block stays low
            if i == span - 1:
                header.timestamp = base_time  # previous block has low timestamp
            else:
                header.timestamp = base_time + 10_000 + i * 10
            blockchain.chain.append(header)
            previous_block = header

        block = Mock()
        block.index = previous_block.index + 1
        block.hash = "0000median"
        block.previous_hash = previous_block.hash
        block.calculate_hash = Mock(return_value="0000median")
        # Slightly above previous block but far below the historical median
        block.timestamp = previous_block.timestamp + 1

        is_valid, error = consensus_manager.validate_block(block, previous_block)
        assert is_valid is False
        assert "median time past" in error

    def test_validate_block_index_mismatch_with_chain(self, consensus_manager, blockchain):
        """Test block index mismatch with chain position."""
        blockchain.chain = [Mock(), Mock()]  # Chain length = 2

        block = Mock()
        block.index = 5  # Should be 2
        block.hash = "0000curr"
        block.timestamp = time.time()
        block.calculate_hash = Mock(return_value="0000curr")

        is_valid, error = consensus_manager.validate_block(block)
        assert is_valid == False
        assert "Block index mismatch" in error


class TestTransactionValidation:
    """Test transaction validation within blocks."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_validate_block_transactions_coinbase(self, consensus_manager):
        """Test validation skips COINBASE transactions."""
        tx1 = Mock()
        tx1.sender = "COINBASE"
        tx1.txid = "tx1"

        block = Mock()
        block.transactions = [tx1]

        is_valid, error = consensus_manager.validate_block_transactions(block)
        assert is_valid == True

    def test_validate_block_transactions_system(self, consensus_manager):
        """Test validation skips SYSTEM transactions."""
        tx1 = Mock()
        tx1.sender = "SYSTEM"
        tx1.txid = "tx1"

        block = Mock()
        block.transactions = [tx1]

        is_valid, error = consensus_manager.validate_block_transactions(block)
        assert is_valid == True

    def test_validate_block_transactions_invalid_signature(self, consensus_manager):
        """Test transaction with invalid signature."""
        tx = Mock()
        tx.sender = "user1"
        tx.txid = "tx1"
        tx.verify_signature = Mock(return_value=False)

        block = Mock()
        block.transactions = [tx]

        is_valid, error = consensus_manager.validate_block_transactions(block)
        assert is_valid == False
        assert "Invalid signature" in error

    def test_validate_block_transactions_insufficient_balance(self, consensus_manager, blockchain):
        """Test transaction with insufficient balance."""
        blockchain.get_balance = Mock(return_value=10.0)  # Low balance

        tx = Mock()
        tx.sender = "poor_user"
        tx.txid = "tx1"
        tx.amount = 100.0
        tx.fee = 1.0
        tx.tx_type = "normal"
        tx.verify_signature = Mock(return_value=True)

        block = Mock()
        block.transactions = [tx]

        is_valid, error = consensus_manager.validate_block_transactions(block)
        assert is_valid == False
        assert "Insufficient balance" in error

    def test_validate_block_transactions_sufficient_balance(self, consensus_manager, blockchain):
        """Test transaction with sufficient balance."""
        blockchain.get_balance = Mock(return_value=1000.0)

        tx = Mock()
        tx.sender = "rich_user"
        tx.txid = "tx1"
        tx.amount = 100.0
        tx.fee = 1.0
        tx.tx_type = "normal"
        tx.verify_signature = Mock(return_value=True)

        block = Mock()
        block.transactions = [tx]

        is_valid, error = consensus_manager.validate_block_transactions(block)
        assert is_valid == True


class TestChainValidation:
    """Test full blockchain validation."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_validate_chain_empty(self, consensus_manager):
        """Test validation of empty chain."""
        is_valid, error = consensus_manager.validate_chain([])
        assert is_valid == False
        assert "empty" in error.lower()

    def test_validate_chain_invalid_genesis_index(self, consensus_manager):
        """Test chain with invalid genesis block index."""
        genesis = Mock()
        genesis.index = 1  # Should be 0
        genesis.previous_hash = "0"

        is_valid, error = consensus_manager.validate_chain([genesis])
        assert is_valid == False
        assert "Genesis block must have index 0" in error

    def test_validate_chain_invalid_genesis_previous_hash(self, consensus_manager):
        """Test chain with invalid genesis previous_hash."""
        genesis = Mock()
        genesis.index = 0
        genesis.previous_hash = "invalid"  # Should be "0"

        is_valid, error = consensus_manager.validate_chain([genesis])
        assert is_valid == False
        assert "previous_hash of '0'" in error

    def test_validate_chain_valid_single_block(self, consensus_manager):
        """Test validation of valid single-block chain."""
        genesis = Mock()
        genesis.index = 0
        genesis.previous_hash = "0"
        genesis.hash = "0000genesis"
        genesis.timestamp = time.time()
        genesis.calculate_hash = Mock(return_value="0000genesis")
        genesis.transactions = []

        is_valid, error = consensus_manager.validate_chain([genesis])
        assert is_valid == True

    def test_validate_chain_multiple_blocks(self, consensus_manager):
        """Test validation of multi-block chain."""
        blocks = []
        for i in range(3):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000block{i-1}"
            block.hash = f"0000block{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000block{i}")
            block.transactions = []
            blocks.append(block)

        is_valid, error = consensus_manager.validate_chain(blocks)
        assert is_valid == True


class TestForkResolution:
    """Test fork resolution logic."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_resolve_forks_no_chains(self, consensus_manager):
        """Test fork resolution with no chains."""
        selected, reason = consensus_manager.resolve_forks([])
        assert selected is None
        assert "No chains provided" in reason

    def test_resolve_forks_single_valid_chain(self, consensus_manager):
        """Test fork resolution with single valid chain."""
        genesis = Mock()
        genesis.index = 0
        genesis.previous_hash = "0"
        genesis.hash = "0000genesis"
        genesis.timestamp = time.time()
        genesis.calculate_hash = Mock(return_value="0000genesis")
        genesis.transactions = []

        chain = [genesis]
        selected, reason = consensus_manager.resolve_forks([chain])
        assert selected == chain
        assert "longest valid chain" in reason.lower()

    def test_resolve_forks_longest_chain_wins(self, consensus_manager):
        """Test longest chain is selected."""
        # Create two chains of different lengths
        short_chain = []
        for i in range(2):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000short{i-1}"
            block.hash = f"0000short{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000short{i}")
            block.transactions = []
            short_chain.append(block)

        long_chain = []
        for i in range(5):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000long{i-1}"
            block.hash = f"0000long{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000long{i}")
            block.transactions = []
            long_chain.append(block)

        selected, reason = consensus_manager.resolve_forks([short_chain, long_chain])
        assert selected == long_chain
        assert "5" in reason


class TestChainIntegrity:
    """Test chain integrity checking."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        bc.chain = []
        bc.get_balance = Mock(return_value=1000.0)
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_check_chain_integrity_empty_chain(self, consensus_manager, blockchain):
        """Test integrity check on empty chain."""
        is_intact, issues = consensus_manager.check_chain_integrity()
        assert is_intact == True
        assert len(issues) == 0

    def test_check_chain_integrity_valid_chain(self, consensus_manager, blockchain):
        """Test integrity check on valid chain."""
        blocks = []
        for i in range(3):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000block{i-1}"
            block.hash = f"0000block{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000block{i}")
            block.transactions = []
            blocks.append(block)

        blockchain.chain = blocks
        is_intact, issues = consensus_manager.check_chain_integrity()
        assert is_intact == True
        assert len(issues) == 0

    def test_check_chain_integrity_index_gap(self, consensus_manager, blockchain):
        """Test integrity check detects index gap."""
        block1 = Mock()
        block1.index = 0
        block1.previous_hash = "0"
        block1.hash = "0000block0"
        block1.timestamp = time.time()
        block1.calculate_hash = Mock(return_value="0000block0")
        block1.transactions = []

        block2 = Mock()
        block2.index = 5  # Gap! Should be 1
        block2.previous_hash = "0000block0"
        block2.hash = "0000block5"
        block2.timestamp = time.time() + 1
        block2.calculate_hash = Mock(return_value="0000block5")
        block2.transactions = []

        blockchain.chain = [block1, block2]
        is_intact, issues = consensus_manager.check_chain_integrity()
        assert is_intact == False
        assert len(issues) > 0


class TestProofOfWork:
    """Test proof-of-work verification."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_verify_proof_of_work_valid(self, consensus_manager):
        """Test valid proof-of-work."""
        block = Mock()
        block.hash = "0000abcd1234"

        assert consensus_manager.verify_proof_of_work(block, 4) == True

    def test_verify_proof_of_work_invalid(self, consensus_manager):
        """Test invalid proof-of-work."""
        block = Mock()
        block.hash = "abc123"

        assert consensus_manager.verify_proof_of_work(block, 4) == False

    def test_verify_proof_of_work_different_difficulties(self, consensus_manager):
        """Test PoW with different difficulty levels."""
        block = Mock()
        block.hash = "00abcd"

        assert consensus_manager.verify_proof_of_work(block, 1) == True
        assert consensus_manager.verify_proof_of_work(block, 2) == True
        assert consensus_manager.verify_proof_of_work(block, 3) == False


class TestChainWork:
    """Test chain work calculation."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_calculate_chain_work(self, consensus_manager):
        """Test chain work calculation."""
        blocks = [
            Mock(hash="0000abc"),
            Mock(hash="00abc"),
            Mock(hash="0abc")
        ]

        work = consensus_manager.calculate_chain_work(blocks)
        # 4 + 2 + 1 = 7 leading zeros
        assert work == 7


class TestChainReplacement:
    """Test chain replacement logic."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain with existing chain."""
        bc = Mock()
        bc.difficulty = 4
        bc.get_balance = Mock(return_value=1000.0)

        # Create current chain (3 blocks)
        current_chain = []
        for i in range(3):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000curr{i-1}"
            block.hash = f"0000curr{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000curr{i}")
            block.transactions = []
            current_chain.append(block)

        bc.chain = current_chain
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_should_replace_chain_longer_valid(self, consensus_manager):
        """Test replacement with longer valid chain."""
        new_chain = []
        for i in range(5):  # Longer than current (3)
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000new{i-1}"
            block.hash = f"0000new{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000new{i}")
            block.transactions = []
            new_chain.append(block)

        should_replace, reason = consensus_manager.should_replace_chain(new_chain)
        assert should_replace == True
        assert "longer and valid" in reason.lower()

    def test_should_replace_chain_shorter(self, consensus_manager):
        """Test no replacement with shorter chain."""
        new_chain = []
        for i in range(2):  # Shorter than current (3)
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000new{i-1}"
            block.hash = f"0000new{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000new{i}")
            block.transactions = []
            new_chain.append(block)

        should_replace, reason = consensus_manager.should_replace_chain(new_chain)
        assert should_replace == False
        assert "not longer" in reason.lower()


class TestConsensusInfo:
    """Test consensus information retrieval."""

    @pytest.fixture
    def blockchain(self):
        """Create mock blockchain."""
        bc = Mock()
        bc.difficulty = 4

        blocks = []
        for i in range(3):
            block = Mock()
            block.index = i
            block.previous_hash = "0" if i == 0 else f"0000block{i-1}"
            block.hash = f"0000block{i}"
            block.timestamp = time.time() + i
            block.calculate_hash = Mock(return_value=f"0000block{i}")
            block.transactions = []
            blocks.append(block)

        bc.chain = blocks
        return bc

    @pytest.fixture
    def consensus_manager(self, blockchain):
        """Create ConsensusManager instance."""
        from xai.core.node_consensus import ConsensusManager
        return ConsensusManager(blockchain)

    def test_get_consensus_info(self, consensus_manager):
        """Test getting consensus information."""
        info = consensus_manager.get_consensus_info()

        assert info['chain_height'] == 3
        assert info['difficulty'] == 4
        assert 'total_work' in info
        assert 'chain_intact' in info
        assert 'genesis_hash' in info
        assert 'latest_block_hash' in info
