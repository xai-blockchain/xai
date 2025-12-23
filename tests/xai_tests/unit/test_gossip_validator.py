"""
Unit tests for GossipValidator.

Coverage targets:
- Transaction and block message validation paths
- Signature field presence checks
- Unknown message type handling
"""

import pytest

from xai.network.gossip_validator import GossipValidator


def _valid_tx():
    return {
        "sender": "A",
        "recipient": "B",
        "amount": 1.0,
        "nonce": 1,
        "payload": "p",
        "signature": "sig",
    }


def _valid_block():
    return {
        "block_hash": "h",
        "previous_block_hash": "p",
        "height": 1,
        "timestamp": 0,
        "transactions": [],
        "validator": "val",
        "payload": "p",
        "signature": "sig",
        "sender": "val",
    }


@pytest.mark.asyncio
async def test_validate_transaction_happy_path():
    validator = GossipValidator()
    assert await validator.validate_transaction_message(_valid_tx()) is True


@pytest.mark.asyncio
async def test_validate_transaction_missing_field():
    validator = GossipValidator()
    bad = _valid_tx()
    bad.pop("signature")
    assert await validator.validate_transaction_message(bad) is False


@pytest.mark.asyncio
async def test_validate_block_height_and_signature():
    validator = GossipValidator()
    block = _valid_block()
    assert await validator.validate_block_message(block) is True

    bad_block = _valid_block()
    bad_block["height"] = -1
    assert await validator.validate_block_message(bad_block) is False

    missing_sig = _valid_block()
    missing_sig.pop("signature")
    assert await validator.validate_block_message(missing_sig) is False


@pytest.mark.asyncio
async def test_process_gossip_unknown_type():
    validator = GossipValidator()
    assert await validator.process_gossip_message("unknown", {}) is False
