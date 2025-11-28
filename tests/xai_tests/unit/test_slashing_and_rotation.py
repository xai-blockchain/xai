import pytest

from xai.blockchain.slashing_manager import SlashingManager
from xai.blockchain.validator_rotation import Validator, ValidatorSetManager
from xai.blockchain.dust_prevention import DustPreventionManager


def test_slashing_manager_applies_penalties():
    manager = SlashingManager({"validator1": 1000.0})
    assert manager.report_misbehavior("watcher", "validator1", "DOUBLE_SIGNING", evidence="proof")
    status = manager.get_validator_status("validator1")
    assert status["staked_amount"] < 1000.0
    assert status["slashed_count"] == 1

    # Unknown validator or misbehavior
    assert manager.report_misbehavior("watcher", "validatorX", "DOUBLE_SIGNING") is False
    assert manager.report_misbehavior("watcher", "validator1", "UNKNOWN") is False


def test_validator_rotation_unique_selection():
    validators = [
        Validator("0xA", 1000, 0.9),
        Validator("0xB", 800, 0.8),
        Validator("0xC", 600, 0.7),
        Validator("0xD", 500, 0.6),
        Validator("0xE", 400, 0.5),
    ]
    manager = ValidatorSetManager(validators, set_size=3)
    new_set = manager.rotate_validator_set()
    assert len(new_set) <= 3
    assert len({v.address for v in new_set}) == len(new_set)
    manager.remove_validator("0xB")
    assert "0xB" not in manager.all_validators


def test_dust_prevention_logs_and_consolidates():
    manager = DustPreventionManager("BTC", dust_threshold_amount=0.0001)
    assert manager.process_incoming_transaction("0xUser", 0.00005, "0xAttacker") is False
    assert manager.process_incoming_transaction("0xUser", 0.001, "0xFriend") is True
    manager.consolidate_dust("0xUser", ["0xUser", "0xDust"])
