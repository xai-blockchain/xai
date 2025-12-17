"""Tests for XAI typed data signing (XIP-191/XIP-712)."""

import pytest

from xai.core.typed_signing import (
    hash_personal_message,
    hash_typed_data,
    TypedDataDomain,
    create_personal_sign_request,
    create_typed_sign_request,
    create_permit_signature_request,
    PERMIT_TYPES,
    TRANSFER_TYPES,
)


class TestPersonalMessage:
    """Tests for XIP-191 personal message signing."""

    def test_hash_string_message(self):
        """Test hashing a string message."""
        hash1 = hash_personal_message("Hello XAI")
        hash2 = hash_personal_message("Hello XAI")

        assert len(hash1) == 32
        assert hash1 == hash2  # Deterministic

    def test_different_messages_different_hashes(self):
        """Different messages produce different hashes."""
        hash1 = hash_personal_message("Hello")
        hash2 = hash_personal_message("World")

        assert hash1 != hash2

    def test_hash_bytes_message(self):
        """Test hashing bytes message."""
        hash1 = hash_personal_message(b"Binary data")
        assert len(hash1) == 32

    def test_create_personal_sign_request(self):
        """Test creating a personal_sign request."""
        request = create_personal_sign_request("Sign this message")

        assert request["method"] == "personal_sign"
        assert request["params"]["message"] == "Sign this message"
        assert "hash" in request["params"]
        assert len(request["params"]["hash"]) == 64  # Hex string


class TestTypedData:
    """Tests for XIP-712 typed data signing."""

    def test_hash_typed_data_deterministic(self):
        """Test that typed data hashing is deterministic."""
        domain = TypedDataDomain(
            name="Test App",
            version="1",
            chain_id=1,
        )

        message = {"from": "XAI123", "to": "XAI456", "amount": 100, "nonce": 0}

        hash1 = hash_typed_data(domain, "Transfer", TRANSFER_TYPES, message)
        hash2 = hash_typed_data(domain, "Transfer", TRANSFER_TYPES, message)

        assert hash1 == hash2

    def test_different_domains_different_hashes(self):
        """Different domains produce different hashes."""
        domain1 = TypedDataDomain(name="App1", version="1", chain_id=1)
        domain2 = TypedDataDomain(name="App2", version="1", chain_id=1)

        message = {"from": "XAI123", "to": "XAI456", "amount": 100, "nonce": 0}

        hash1 = hash_typed_data(domain1, "Transfer", TRANSFER_TYPES, message)
        hash2 = hash_typed_data(domain2, "Transfer", TRANSFER_TYPES, message)

        assert hash1 != hash2

    def test_different_chain_ids_different_hashes(self):
        """Different chain IDs produce different hashes."""
        domain1 = TypedDataDomain(name="App", version="1", chain_id=1)
        domain2 = TypedDataDomain(name="App", version="1", chain_id=2)

        message = {"from": "XAI123", "to": "XAI456", "amount": 100, "nonce": 0}

        hash1 = hash_typed_data(domain1, "Transfer", TRANSFER_TYPES, message)
        hash2 = hash_typed_data(domain2, "Transfer", TRANSFER_TYPES, message)

        assert hash1 != hash2

    def test_create_typed_sign_request(self):
        """Test creating a typed sign request."""
        domain = TypedDataDomain(name="Test", version="1", chain_id=1)
        message = {"from": "XAI123", "to": "XAI456", "amount": 100, "nonce": 0}

        request = create_typed_sign_request(domain, "Transfer", TRANSFER_TYPES, message)

        assert request["method"] == "xai_signTypedData"
        assert "typedData" in request["params"]
        assert request["params"]["typedData"]["primaryType"] == "Transfer"


class TestPermitSignature:
    """Tests for token permit signatures."""

    def test_create_permit_request(self):
        """Test creating a permit signature request."""
        request = create_permit_signature_request(
            token_name="XAI Token",
            token_address="XAI_TOKEN_CONTRACT",
            chain_id=1,
            owner="XAI_OWNER_ADDRESS",
            spender="XAI_SPENDER_ADDRESS",
            value=1000,
            nonce=0,
            deadline=1700000000,
        )

        assert request["method"] == "xai_signTypedData"
        assert request["params"]["typedData"]["primaryType"] == "Permit"
        assert request["params"]["typedData"]["message"]["value"] == 1000

    def test_permit_different_values_different_hashes(self):
        """Different permit values produce different hashes."""
        request1 = create_permit_signature_request(
            "Token", "XAI123", 1, "owner", "spender", 100, 0, 1700000000
        )
        request2 = create_permit_signature_request(
            "Token", "XAI123", 1, "owner", "spender", 200, 0, 1700000000
        )

        assert request1["params"]["hash"] != request2["params"]["hash"]


class TestTypeEncoding:
    """Tests for type encoding edge cases."""

    def test_nested_types(self):
        """Test hashing with nested struct types."""
        types = {
            "Mail": [
                {"name": "from", "type": "Person"},
                {"name": "to", "type": "Person"},
                {"name": "contents", "type": "string"},
            ],
            "Person": [
                {"name": "name", "type": "string"},
                {"name": "wallet", "type": "address"},
            ]
        }

        domain = TypedDataDomain(name="Mail", version="1", chain_id=1)
        message = {
            "from": {"name": "Alice", "wallet": "XAI_ALICE"},
            "to": {"name": "Bob", "wallet": "XAI_BOB"},
            "contents": "Hello Bob!",
        }

        hash_result = hash_typed_data(domain, "Mail", types, message)
        assert len(hash_result) == 32

    def test_array_types(self):
        """Test hashing with array types."""
        types = {
            "BatchTransfer": [
                {"name": "recipients", "type": "address[]"},
                {"name": "amounts", "type": "uint256[]"},
            ]
        }

        domain = TypedDataDomain(name="Batch", version="1", chain_id=1)
        message = {
            "recipients": ["XAI1", "XAI2", "XAI3"],
            "amounts": [100, 200, 300],
        }

        hash_result = hash_typed_data(domain, "BatchTransfer", types, message)
        assert len(hash_result) == 32
