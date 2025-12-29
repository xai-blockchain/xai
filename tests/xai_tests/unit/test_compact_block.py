"""
Tests for Compact Block Relay implementation.
"""

import hashlib
import pytest

from xai.core.p2p.compact_block import (
    CompactBlock,
    CompactBlockReconstructor,
    BlockTransactionsRequest,
    BlockTransactionsResponse,
    PrefilledTransaction,
    calculate_bandwidth_savings,
    _siphash_short_txid,
)


class TestShortTxId:
    """Tests for short transaction ID computation."""

    def test_short_txid_is_6_bytes(self):
        """Short txids should be exactly 6 bytes."""
        txid = "a" * 64
        short_txid = _siphash_short_txid(txid, 12345)
        assert len(short_txid) == 6
        assert isinstance(short_txid, bytes)

    def test_short_txid_deterministic(self):
        """Same inputs should produce same short txid."""
        txid = "abcd1234" * 8
        nonce = 99999
        stxid1 = _siphash_short_txid(txid, nonce)
        stxid2 = _siphash_short_txid(txid, nonce)
        assert stxid1 == stxid2

    def test_short_txid_different_nonce(self):
        """Different nonces should produce different short txids."""
        txid = "abcd1234" * 8
        stxid1 = _siphash_short_txid(txid, 1)
        stxid2 = _siphash_short_txid(txid, 2)
        assert stxid1 != stxid2

    def test_short_txid_different_txid(self):
        """Different txids should produce different short txids."""
        nonce = 12345
        stxid1 = _siphash_short_txid("a" * 64, nonce)
        stxid2 = _siphash_short_txid("b" * 64, nonce)
        assert stxid1 != stxid2


class TestPrefilledTransaction:
    """Tests for prefilled transaction dataclass."""

    def test_prefilled_transaction_creation(self):
        """Test creating a prefilled transaction."""
        pt = PrefilledTransaction(
            index=0,
            tx_data={"sender": "alice", "recipient": "bob", "amount": 10}
        )
        assert pt.index == 0
        assert pt.tx_data["sender"] == "alice"


class TestCompactBlock:
    """Tests for CompactBlock class."""

    def test_compact_block_to_dict(self):
        """Test serialization of compact block."""
        cb = CompactBlock(
            header_hash="abc123",
            previous_hash="0" * 64,
            merkle_root="merkle" * 10 + "1234",
            timestamp=1234567890.0,
            difficulty=4,
            nonce=999,
            block_index=100,
            block_nonce=54321,
            short_txid_nonce=999,
            short_txids=[b"\x01\x02\x03\x04\x05\x06", b"\x0a\x0b\x0c\x0d\x0e\x0f"],
            prefilled_txns=[
                PrefilledTransaction(index=0, tx_data={"coinbase": True})
            ],
        )

        data = cb.to_dict()

        assert data["type"] == "compact_block"
        assert data["header_hash"] == "abc123"
        assert data["block_index"] == 100
        assert len(data["short_txids"]) == 2
        assert data["short_txids"][0] == "010203040506"
        assert len(data["prefilled_txns"]) == 1

    def test_compact_block_from_dict(self):
        """Test deserialization of compact block."""
        data = {
            "header_hash": "xyz789",
            "previous_hash": "1" * 64,
            "merkle_root": "merkle" * 10 + "5678",
            "timestamp": 9999999999.0,
            "difficulty": 5,
            "block_index": 200,
            "block_nonce": 11111,
            "short_txid_nonce": 777,
            "short_txids": ["aabbccddeeff"],
            "prefilled_txns": [],
            "version": 2,
        }

        cb = CompactBlock.from_dict(data)

        assert cb.header_hash == "xyz789"
        assert cb.block_index == 200
        assert cb.short_txid_nonce == 777
        assert len(cb.short_txids) == 1
        assert cb.short_txids[0] == bytes.fromhex("aabbccddeeff")
        assert cb.version == 2

    def test_compact_block_roundtrip(self):
        """Test serialization roundtrip."""
        original = CompactBlock(
            header_hash="roundtrip",
            previous_hash="2" * 64,
            merkle_root="m" * 64,
            timestamp=1111111111.0,
            difficulty=3,
            nonce=123,
            block_index=50,
            block_nonce=456,
            short_txid_nonce=123,
            short_txids=[b"\xff" * 6],
            prefilled_txns=[PrefilledTransaction(0, {"test": "data"})],
            miner_pubkey="pubkey123",
            signature="sig456",
        )

        data = original.to_dict()
        restored = CompactBlock.from_dict(data)

        assert restored.header_hash == original.header_hash
        assert restored.block_index == original.block_index
        assert restored.short_txids == original.short_txids
        assert restored.miner_pubkey == original.miner_pubkey

    def test_size_bytes_estimation(self):
        """Test size estimation."""
        cb = CompactBlock(
            header_hash="size",
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=0,
            difficulty=1,
            nonce=0,
            block_index=0,
            block_nonce=0,
            short_txid_nonce=0,
            short_txids=[b"\x00" * 6] * 1000,  # 1000 transactions
            prefilled_txns=[PrefilledTransaction(0, {})],
        )

        size = cb.size_bytes()
        # Should be roughly: 150 (header) + 6000 (short txids) + 200 (prefilled)
        assert size > 6000
        assert size < 10000


class TestBlockTransactionsRequest:
    """Tests for BlockTransactionsRequest."""

    def test_request_to_dict(self):
        """Test request serialization."""
        req = BlockTransactionsRequest(
            block_hash="blockhash123",
            indexes=[1, 5, 10, 15]
        )

        data = req.to_dict()

        assert data["type"] == "getblocktxn"
        assert data["block_hash"] == "blockhash123"
        assert data["indexes"] == [1, 5, 10, 15]

    def test_request_from_dict(self):
        """Test request deserialization."""
        data = {
            "block_hash": "hash456",
            "indexes": [2, 4, 6],
        }

        req = BlockTransactionsRequest.from_dict(data)

        assert req.block_hash == "hash456"
        assert req.indexes == [2, 4, 6]


class TestBlockTransactionsResponse:
    """Tests for BlockTransactionsResponse."""

    def test_response_to_dict(self):
        """Test response serialization."""
        resp = BlockTransactionsResponse(
            block_hash="resp_hash",
            transactions=[{"tx": 1}, {"tx": 2}]
        )

        data = resp.to_dict()

        assert data["type"] == "blocktxn"
        assert data["block_hash"] == "resp_hash"
        assert len(data["transactions"]) == 2

    def test_response_from_dict(self):
        """Test response deserialization."""
        data = {
            "block_hash": "hash789",
            "transactions": [{"a": 1}],
        }

        resp = BlockTransactionsResponse.from_dict(data)

        assert resp.block_hash == "hash789"
        assert resp.transactions == [{"a": 1}]


class TestBandwidthCalculation:
    """Tests for bandwidth savings calculation."""

    def test_bandwidth_savings_97_percent(self):
        """Test 97% savings case (500KB -> 13KB)."""
        savings = calculate_bandwidth_savings(500000, 13000)
        assert savings > 97.0
        assert savings < 98.0

    def test_bandwidth_savings_zero_full_block(self):
        """Test edge case with zero full block size."""
        savings = calculate_bandwidth_savings(0, 100)
        assert savings == 0.0

    def test_bandwidth_savings_equal_sizes(self):
        """Test no savings when sizes are equal."""
        savings = calculate_bandwidth_savings(1000, 1000)
        assert savings == 0.0

    def test_bandwidth_savings_50_percent(self):
        """Test 50% savings."""
        savings = calculate_bandwidth_savings(1000, 500)
        assert savings == 50.0


class TestCompactBlockReconstructor:
    """Tests for CompactBlockReconstructor."""

    def test_reconstructor_initialization(self):
        """Test reconstructor initialization."""
        reconstructor = CompactBlockReconstructor([])
        assert reconstructor._mempool == []

    def test_can_reconstruct_empty_block(self):
        """Test reconstruction check with empty block."""
        reconstructor = CompactBlockReconstructor([])
        cb = CompactBlock(
            header_hash="empty",
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=0,
            difficulty=1,
            nonce=0,
            block_index=0,
            block_nonce=0,
            short_txid_nonce=0,
            short_txids=[],
            prefilled_txns=[],
        )
        # Empty block with no transactions can always be reconstructed
        assert reconstructor.can_reconstruct(cb)

    def test_find_missing_with_empty_mempool(self):
        """Test finding missing transactions with empty mempool."""
        reconstructor = CompactBlockReconstructor([])
        cb = CompactBlock(
            header_hash="missing",
            previous_hash="0" * 64,
            merkle_root="0" * 64,
            timestamp=0,
            difficulty=1,
            nonce=0,
            block_index=0,
            block_nonce=0,
            short_txid_nonce=12345,
            short_txids=[b"\x01" * 6, b"\x02" * 6],
            prefilled_txns=[],
        )

        found, missing = reconstructor.find_missing_transactions(cb)

        assert len(found) == 0
        assert len(missing) == 2


class TestIntegration:
    """Integration tests with real block/transaction objects."""

    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction for testing."""
        from xai.core.transaction import Transaction
        # Use valid XAI testnet addresses
        tx = Transaction(
            sender="TXAI1111111111111111111111111111111111",
            recipient="TXAI2222222222222222222222222222222222",
            amount=10.0
        )
        tx.txid = tx.calculate_hash()
        return tx

    @pytest.fixture
    def sample_block(self, sample_transaction):
        """Create a sample block for testing."""
        from xai.core.chain.block_header import BlockHeader
        from xai.core.blockchain_components.block import Block

        header = BlockHeader(
            index=1,
            previous_hash="0" * 64,
            merkle_root="1" * 64,
            timestamp=1234567890.0,
            difficulty=4,
            nonce=999,
        )
        return Block(header=header, transactions=[sample_transaction])

    def test_compact_block_from_real_block(self, sample_block):
        """Test creating compact block from real block."""
        cb = CompactBlock.from_block(sample_block, include_coinbase=True)

        assert cb.block_index == sample_block.header.index
        assert cb.previous_hash == sample_block.header.previous_hash
        assert cb.difficulty == sample_block.header.difficulty
        assert len(cb.prefilled_txns) == 1  # First tx (coinbase) is prefilled

    def test_compact_block_serialization_with_real_block(self, sample_block):
        """Test compact block roundtrip with real block."""
        cb = CompactBlock.from_block(sample_block)
        data = cb.to_dict()
        restored = CompactBlock.from_dict(data)

        assert restored.block_index == cb.block_index
        assert restored.previous_hash == cb.previous_hash
        assert restored.merkle_root == cb.merkle_root
