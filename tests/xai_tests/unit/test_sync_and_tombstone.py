import pytest

from xai.blockchain.sync_validator import SyncValidator
from xai.blockchain.tombstone_manager import TombstoneManager


def test_sync_validator_success_and_checkpoint_conflict():
    validator = SyncValidator(
        trusted_checkpoints=[{"height": 10, "hash": "hash10"}]
    )

    block = {
        "header": {
            "hash": "hash11",
            "previous_hash": "hash10",
            "height": 11,
            "timestamp": 100,
        },
        "transactions": [
            {
                "sender": "0xA",
                "recipient": "0xB",
                "amount": 25,
                "nonce": 1,
                "signature": "sig",
            }
        ],
    }
    assert validator.validate_incoming_block(block) is True

    conflict_block = {
        "header": {
            "hash": "evil",
            "previous_hash": "hash9",
            "height": 10,
            "timestamp": 101,
        },
        "transactions": [],
    }
    assert validator.validate_incoming_block(conflict_block) is False


def test_sync_validator_rejects_invalid_blocks():
    validator = SyncValidator()
    missing_header_block = {"transactions": []}
    assert validator.validate_incoming_block(missing_header_block) is False

    bad_tx_block = {
        "header": {
            "hash": "hash12",
            "previous_hash": "hash11",
            "height": 12,
            "timestamp": 102,
        },
        "transactions": [
            {
                "sender": "0xA",
                "recipient": "0xB",
                "amount": -5,
                "nonce": 2,
                "signature": "sig",
            }
        ],
    }
    assert validator.validate_incoming_block(bad_tx_block) is False


def test_tombstone_manager_flow():
    manager = TombstoneManager({"val1": 100.0, "val2": 50.0}, tombstone_threshold=2)

    manager.record_slashing_event("val1", 10)
    assert manager.get_validator_status("val1") == "Active"

    manager.record_slashing_event("val1", 5)
    assert manager.get_validator_status("val1") == "Tombstoned"
    assert "val1" in manager.tombstoned_validators

    manager.record_slashing_event("val1", 5)
    assert manager.active_validators.get("val1") is None

    manager.record_slashing_event("unknown", 5)
    manager.record_slashing_event("val2", 10)
    assert manager.get_validator_status("val2") == "Active"
