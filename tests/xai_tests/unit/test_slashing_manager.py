"""
Unit tests for SlashingManager.

Coverage targets:
- Validator seeding and add_validator validation
- Evidence validation and slashing application
- Unknown validator/type handling
"""

from pathlib import Path

import pytest

from xai.blockchain.slashing_manager import SlashingManager, get_validator_key


def _manager(tmp_path: Path) -> SlashingManager:
    db = tmp_path / "slash.db"
    return SlashingManager(db, initial_validators={"val1": 100.0})


def test_add_validator_and_duplicate(tmp_path):
    mgr = _manager(tmp_path)
    mgr.add_validator("val2", 50.0)
    assert mgr.get_validator_status("val2")["staked_amount"] == 50.0
    with pytest.raises(ValueError):
        mgr.add_validator("val2", 10)


def test_report_misbehavior_validates_evidence(tmp_path):
    mgr = _manager(tmp_path)
    # Missing evidence
    assert mgr.report_misbehavior("rep", "val1", "DOUBLE_SIGNING", evidence=None) is False
    # Invalid type
    assert mgr.report_misbehavior("rep", "val1", "UNKNOWN", evidence={}) is False
    # Valid evidence structure triggers slashing
    evidence = {"header1": "h1", "header2": "h2"}
    assert mgr.report_misbehavior("rep", "val1", "DOUBLE_SIGNING", evidence=evidence) is True
    status = mgr.get_validator_status("val1")
    assert status["staked_amount"] < 100.0
    assert status["slashed_count"] == 1


def test_apply_slashing_unknown_validator(tmp_path):
    mgr = _manager(tmp_path)
    assert mgr.apply_slashing("missing", "DOUBLE_SIGNING") is False
