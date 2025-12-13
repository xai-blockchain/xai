"""
Test suite for XAI Blockchain - Encoding and Serialization Primitives Verification

This test suite verifies the correctness of serialization and deserialization logic:
- Transaction encoding/decoding
- Block encoding/decoding
- Canonical JSON for consensus-critical hashing
- Network message formats
- UTXO serialization

These are consensus-critical operations that must produce identical results
across all nodes to maintain network integrity.
"""

import pytest
import json
import hashlib
from decimal import Decimal
from xai.core.blockchain import Transaction, Block
from xai.core.wallet import Wallet
from xai.core.transaction import canonical_json


class TestCanonicalJSON:
    """Verify canonical JSON encoding for consensus-critical operations."""

    def test_canonical_json_determinism(self):
        """Verify canonical_json produces same output for same input."""
        data = {
            "sender": "XAI1234567890",
            "recipient": "XAI0987654321",
            "amount": 10.5,
            "timestamp": 1234567890,
        }

        json1 = canonical_json(data)
        json2 = canonical_json(data)

        assert json1 == json2

    def test_canonical_json_key_ordering(self):
        """Verify canonical_json sorts keys alphabetically."""
        # Create dict with keys in non-alphabetical order
        data = {"z": 1, "a": 2, "m": 3}

        result = canonical_json(data)

        # Keys should be in alphabetical order
        assert result == '{"a":2,"m":3,"z":1}'

    def test_canonical_json_no_whitespace(self):
        """Verify canonical_json has no extra whitespace."""
        data = {"key": "value", "number": 123}

        result = canonical_json(data)

        # Should have no spaces
        assert " " not in result
        # Should use minimal separators
        assert result == '{"key":"value","number":123}'

    def test_canonical_json_nested_ordering(self):
        """Verify canonical_json sorts keys in nested objects."""
        data = {
            "outer_z": {"inner_z": 1, "inner_a": 2},
            "outer_a": {"inner_z": 3, "inner_a": 4},
        }

        result = canonical_json(data)

        # Both outer and inner keys should be sorted
        assert result == '{"outer_a":{"inner_a":4,"inner_z":3},"outer_z":{"inner_a":2,"inner_z":1}}'

    def test_canonical_json_different_order_same_hash(self):
        """Verify dicts with same content but different key order produce same canonical JSON."""
        data1 = {"sender": "Alice", "recipient": "Bob", "amount": 10}
        data2 = {"amount": 10, "sender": "Alice", "recipient": "Bob"}
        data3 = {"recipient": "Bob", "amount": 10, "sender": "Alice"}

        json1 = canonical_json(data1)
        json2 = canonical_json(data2)
        json3 = canonical_json(data3)

        assert json1 == json2 == json3

        # Hashes should also be identical
        hash1 = hashlib.sha256(json1.encode()).hexdigest()
        hash2 = hashlib.sha256(json2.encode()).hexdigest()
        hash3 = hashlib.sha256(json3.encode()).hexdigest()

        assert hash1 == hash2 == hash3


class TestTransactionSerialization:
    """Verify transaction serialization and deserialization."""

    def test_transaction_to_dict(self):
        """Verify transaction can be serialized to dict."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=5,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
            metadata={"note": "test payment"},
        )
        tx.sign_transaction(wallet1.private_key)

        # Serialize to dict
        tx_dict = tx.to_dict()

        # Verify all required fields are present
        assert "txid" in tx_dict
        assert "sender" in tx_dict
        assert "recipient" in tx_dict
        assert "amount" in tx_dict
        assert "fee" in tx_dict
        assert "timestamp" in tx_dict
        assert "signature" in tx_dict
        assert "public_key" in tx_dict
        assert "nonce" in tx_dict
        assert "inputs" in tx_dict
        assert "outputs" in tx_dict
        assert "metadata" in tx_dict

    def test_transaction_dict_json_serializable(self):
        """Verify transaction dict can be serialized to JSON."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        tx_dict = tx.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(tx_dict)
        assert isinstance(json_str, str)

        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized == tx_dict

    def test_transaction_hash_consistency(self):
        """Verify transaction hash is consistent with serialized data."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        # Calculate hash twice
        hash1 = tx.calculate_hash()
        hash2 = tx.calculate_hash()

        # Should be identical
        assert hash1 == hash2
        assert hash1 == tx.txid

    def test_transaction_roundtrip(self):
        """Verify transaction can be serialized and key fields preserved."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        original_tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        original_tx.sign_transaction(wallet1.private_key)

        # Serialize
        tx_dict = original_tx.to_dict()

        # Verify key fields match
        assert tx_dict["txid"] == original_tx.txid
        assert tx_dict["sender"] == original_tx.sender
        assert tx_dict["recipient"] == original_tx.recipient
        assert tx_dict["amount"] == original_tx.amount
        assert tx_dict["fee"] == original_tx.fee
        assert tx_dict["signature"] == original_tx.signature
        assert tx_dict["public_key"] == original_tx.public_key
        assert tx_dict["nonce"] == original_tx.nonce


class TestBlockSerialization:
    """Verify block serialization and deserialization."""

    def test_block_to_dict(self):
        """Verify block can be serialized to dict."""
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain()
        block = blockchain.get_latest_block()

        # Serialize to dict
        block_dict = block.to_dict()

        # Verify all required fields are present
        assert "index" in block_dict
        assert "timestamp" in block_dict
        assert "transactions" in block_dict
        assert "previous_hash" in block_dict
        assert "nonce" in block_dict
        assert "hash" in block_dict
        assert "difficulty" in block_dict

    def test_block_dict_json_serializable(self):
        """Verify block dict can be serialized to JSON."""
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain()
        block = blockchain.get_latest_block()

        block_dict = block.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(block_dict)
        assert isinstance(json_str, str)

        # Should be deserializable
        deserialized = json.loads(json_str)
        assert isinstance(deserialized, dict)

    def test_block_hash_consistency(self):
        """Verify block hash is consistent with serialized data."""
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain()
        block = blockchain.get_latest_block()

        # Calculate hash twice
        hash1 = block.calculate_hash()
        hash2 = block.calculate_hash()

        # Should be identical
        assert hash1 == hash2
        assert hash1 == block.hash

    def test_block_with_transactions_serialization(self):
        """Verify block with transactions serializes correctly."""
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create a transaction
        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        # Create block with transaction
        previous_block = blockchain.get_latest_block()
        block = Block(
            index=previous_block.index + 1,
            transactions=[tx],
            previous_hash=previous_block.hash,
        )

        # Serialize
        block_dict = block.to_dict()

        # Verify transactions are included
        assert len(block_dict["transactions"]) == 1
        assert block_dict["transactions"][0]["sender"] == wallet1.address


class TestUTXOSerialization:
    """Verify UTXO serialization for state management."""

    def test_utxo_dict_structure(self):
        """Verify UTXO has expected dict structure."""
        utxo = {
            "txid": "a" * 64,
            "vout": 0,
            "amount": 10.0,
            "script_pubkey": "P2PKH XAI1234567890",
        }

        # Should be JSON serializable
        json_str = json.dumps(utxo)
        assert isinstance(json_str, str)

        # Should roundtrip
        deserialized = json.loads(json_str)
        assert deserialized == utxo

    def test_utxo_set_serialization(self):
        """Verify UTXO set can be serialized."""
        utxo_set = {
            "utxo1": {
                "txid": "a" * 64,
                "vout": 0,
                "amount": 10.0,
                "script_pubkey": "P2PKH XAI1111",
            },
            "utxo2": {
                "txid": "b" * 64,
                "vout": 1,
                "amount": 20.0,
                "script_pubkey": "P2PKH XAI2222",
            },
        }

        # Should be JSON serializable
        json_str = json.dumps(utxo_set)
        assert isinstance(json_str, str)

        # Should roundtrip
        deserialized = json.loads(json_str)
        assert deserialized == utxo_set


class TestNetworkMessageFormats:
    """Verify network message encoding for P2P communication."""

    def test_transaction_broadcast_format(self):
        """Verify transaction broadcast message format."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        # Create broadcast message
        message = {
            "type": "new_transaction",
            "transaction": tx.to_dict(),
        }

        # Should be JSON serializable
        json_str = json.dumps(message)
        assert isinstance(json_str, str)

        # Should deserialize
        deserialized = json.loads(json_str)
        assert deserialized["type"] == "new_transaction"
        assert "transaction" in deserialized

    def test_block_broadcast_format(self):
        """Verify block broadcast message format."""
        from xai.core.blockchain import Blockchain

        blockchain = Blockchain()
        block = blockchain.get_latest_block()

        # Create broadcast message
        message = {
            "type": "new_block",
            "block": block.to_dict(),
        }

        # Should be JSON serializable
        json_str = json.dumps(message)
        assert isinstance(json_str, str)

        # Should deserialize
        deserialized = json.loads(json_str)
        assert deserialized["type"] == "new_block"
        assert "block" in deserialized


class TestSerializationEdgeCases:
    """Test edge cases and special values in serialization."""

    def test_zero_amount_transaction(self):
        """Verify zero-amount transactions serialize correctly."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=0.0,
            fee=0.1,
            public_key=wallet1.public_key,
            tx_type="governance_vote",
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 0.0}],
        )
        tx.sign_transaction(wallet1.private_key)

        tx_dict = tx.to_dict()
        assert tx_dict["amount"] == 0.0

        # Should be JSON serializable
        json_str = json.dumps(tx_dict)
        deserialized = json.loads(json_str)
        assert deserialized["amount"] == 0.0

    def test_large_metadata_serialization(self):
        """Verify transactions with large metadata serialize correctly."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create large metadata (but within limit)
        large_metadata = {"data": "X" * 4000}  # 4KB is the limit

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
            metadata=large_metadata,
        )
        tx.sign_transaction(wallet1.private_key)

        tx_dict = tx.to_dict()

        # Should be JSON serializable
        json_str = json.dumps(tx_dict)
        assert isinstance(json_str, str)

        # Should deserialize
        deserialized = json.loads(json_str)
        assert deserialized["metadata"]["data"] == "X" * 4000

    def test_unicode_handling(self):
        """Verify Unicode characters in metadata are handled correctly."""
        wallet1 = Wallet()
        wallet2 = Wallet()

        unicode_metadata = {
            "note": "Payment for café ☕",
            "emoji": "🚀🌙",
            "chinese": "你好",
        }

        tx = Transaction(
            sender=wallet1.address,
            recipient=wallet2.address,
            amount=10.0,
            fee=0.1,
            public_key=wallet1.public_key,
            nonce=0,
            inputs=[{"txid": "a" * 64, "vout": 0}],
            outputs=[{"address": wallet2.address, "amount": 10.0}],
            metadata=unicode_metadata,
        )
        tx.sign_transaction(wallet1.private_key)

        tx_dict = tx.to_dict()

        # Should be JSON serializable with ensure_ascii
        json_str = json.dumps(tx_dict, ensure_ascii=True)
        assert isinstance(json_str, str)

        # Should deserialize correctly
        deserialized = json.loads(json_str)
        assert deserialized["metadata"]["note"] == "Payment for café ☕"
