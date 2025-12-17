"""Tests for XAI Unsigned Transaction (XUTX) format."""

import json
import pytest
import time

from xai.core.unsigned_transaction import (
    UnsignedTransaction,
    TxStatus,
    SignatureSlot,
    create_transfer,
    create_multisig_transfer,
)


class TestUnsignedTransaction:
    """Tests for UnsignedTransaction class."""

    def test_create_simple_transfer(self):
        """Test creating a simple transfer transaction."""
        tx = create_transfer(
            sender="XAI1234567890abcdef1234567890abcdef12345678",
            recipient="XAI0987654321fedcba0987654321fedcba09876543",
            amount=10.5,
            fee=0.001,
        )

        assert tx.sender == "XAI1234567890abcdef1234567890abcdef12345678"
        assert tx.recipient == "XAI0987654321fedcba0987654321fedcba09876543"
        assert tx.amount == 10.5
        assert tx.fee == 0.001
        assert tx.status == TxStatus.UNSIGNED.value
        assert tx.threshold == 1

    def test_payload_hash_deterministic(self):
        """Test that payload hash is deterministic."""
        tx1 = create_transfer("XAIabc", "XAIdef", 10.0)
        tx2 = create_transfer("XAIabc", "XAIdef", 10.0)

        # Same inputs should produce same hash
        # (excluding created_at which differs)
        tx2.created_at = tx1.created_at
        assert tx1.payload_hash == tx2.payload_hash

    def test_add_signature(self):
        """Test adding a signature to transaction."""
        tx = create_transfer("XAIsender", "XAIrecipient", 5.0)

        result = tx.add_signature(
            public_key="04abcdef1234567890",
            signature="3045022100...",
            label="Alice"
        )

        assert result is True
        assert tx.signature_count == 1
        assert tx.status == TxStatus.FULLY_SIGNED.value
        assert tx.is_ready is True

    def test_multisig_partial_signatures(self):
        """Test multisig with partial signature collection."""
        tx = create_multisig_transfer(
            sender="XAImultisig",
            recipient="XAIrecipient",
            amount=100.0,
            public_keys=["pk1", "pk2", "pk3"],
            threshold=2,
        )

        assert tx.threshold == 2
        assert len(tx.signature_slots) == 3
        assert tx.status == TxStatus.UNSIGNED.value

        # Add first signature
        tx.add_signature("pk1", "sig1")
        assert tx.signature_count == 1
        assert tx.status == TxStatus.PARTIALLY_SIGNED.value
        assert tx.is_ready is False

        # Add second signature
        tx.add_signature("pk2", "sig2")
        assert tx.signature_count == 2
        assert tx.status == TxStatus.FULLY_SIGNED.value
        assert tx.is_ready is True

    def test_serialization_roundtrip(self):
        """Test JSON serialization roundtrip."""
        tx = create_transfer("XAIsender", "XAIrecipient", 25.0, memo="Test payment")
        tx.add_signature("pubkey123", "signature456")

        # To JSON and back
        json_str = tx.to_json()
        tx2 = UnsignedTransaction.from_json(json_str)

        assert tx2.sender == tx.sender
        assert tx2.recipient == tx.recipient
        assert tx2.amount == tx.amount
        assert tx2.memo == tx.memo
        assert tx2.signature_count == tx.signature_count

    def test_base64_roundtrip(self):
        """Test base64 serialization roundtrip."""
        tx = create_transfer("XAIsender", "XAIrecipient", 50.0)

        b64 = tx.to_base64()
        tx2 = UnsignedTransaction.from_base64(b64)

        assert tx2.sender == tx.sender
        assert tx2.amount == tx.amount

    def test_display_for_review(self):
        """Test human-readable display generation."""
        tx = create_transfer(
            sender="XAI1234567890abcdef1234567890abcdef12345678",
            recipient="XAI0987654321fedcba0987654321fedcba09876543",
            amount=100.0,
            fee=0.01,
            memo="Payment for services",
        )

        display = tx.display_for_review()

        assert "100.0 XAI" in display
        assert "Payment for services" in display
        assert "REVIEW CAREFULLY" in display
        assert tx.sender in display
        assert tx.recipient in display

    def test_duplicate_signature_rejected(self):
        """Test that duplicate signatures are rejected."""
        tx = create_multisig_transfer(
            sender="XAImultisig",
            recipient="XAIrecipient",
            amount=50.0,
            public_keys=["pk1", "pk2"],
            threshold=2,
        )

        tx.add_signature("pk1", "sig1")
        result = tx.add_signature("pk1", "sig1_duplicate")

        assert result is False
        assert tx.signature_count == 1


class TestPayloadHash:
    """Tests for payload hashing."""

    def test_hash_changes_with_amount(self):
        """Different amounts produce different hashes."""
        tx1 = create_transfer("XAIsender", "XAIrecipient", 10.0)
        tx2 = create_transfer("XAIsender", "XAIrecipient", 20.0)
        tx2.created_at = tx1.created_at

        assert tx1.payload_hash != tx2.payload_hash

    def test_hash_changes_with_recipient(self):
        """Different recipients produce different hashes."""
        tx1 = create_transfer("XAIsender", "XAIrecipient1", 10.0)
        tx2 = create_transfer("XAIsender", "XAIrecipient2", 10.0)
        tx2.created_at = tx1.created_at

        assert tx1.payload_hash != tx2.payload_hash
