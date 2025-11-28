"""
Unit tests for TimeCapsuleProtocol

Focus on reserve wallet validation and the hardening rules added in the protocol layer.
"""

import json
import time
from pathlib import Path

from xai.core.time_capsule_protocol import TimeCapsuleProtocol


def _write_reserve(tmp_path: Path, overrides: dict = None) -> dict:
    """Write a reserve file to disk with sensible defaults and optional overrides."""
    reserve = {
        "address": "XAI_RESERVE",
        "public_key": "pub_reserve",
        "private_key": "priv_reserve",
        "initial_balance": 450000,
        "current_balance": 450000,
        "purpose": "Test Reserve",
        "max_disbursements": 10,
        "disbursement_amount": 450,
        "disbursements_made": 0,
        "disbursement_window_seconds": 86400,
        "max_disbursements_per_window": 4,
        "max_disbursement_amount_per_window": 450 * 4,
        "disbursement_history": [],
    }
    overrides = overrides or {}
    reserve.update(overrides)
    path = tmp_path / "TIME_CAPSULE_RESERVE.json"
    path.write_text(json.dumps(reserve, indent=2))
    return reserve


def _eligible_wallet() -> dict:
    """Build a wallet payload that qualifies for time capsule protocol."""
    return {
        "address": "XAI_TESTER",
        "private_key": "privx",
        "public_key": "pubx",
        "initial_balance": 50,
        "time_capsule_bonus": 450,
        "time_capsule_eligible": True,
        "time_capsule_claimed": False,
    }


def test_window_limit_blocks_disbursement(tmp_path):
    """Reserve should reject new bonuses when the window limit is already reached."""
    now = time.time()
    _write_reserve(
        tmp_path,
        overrides={
            "current_balance": 900,
            "max_disbursements_per_window": 1,
            "disbursement_history": [{"timestamp": now, "amount": 450}],
        },
    )

    protocol = TimeCapsuleProtocol(data_dir=str(tmp_path))
    wallet_data = _eligible_wallet()
    result = protocol.initiate_time_capsule(wallet_data)

    assert result["success"] is False
    assert "window" in result["error"].lower()


def test_global_disbursement_limit_enforced(tmp_path):
    """Reserve should stop handing out bonuses after the configured global cap."""
    _write_reserve(
        tmp_path,
        overrides={
            "current_balance": 450,
            "max_disbursements": 1,
            "disbursements_made": 1,
            "disbursement_history": [],
        },
    )

    protocol = TimeCapsuleProtocol(data_dir=str(tmp_path))
    wallet_data = _eligible_wallet()
    result = protocol.initiate_time_capsule(wallet_data)

    assert result["success"] is False
    assert "max disbursements" in result["error"].lower()
