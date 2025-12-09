"""
Unit tests for TimeCapsuleProtocol initiation, eligibility, unlock checks, and stats.
"""

import json
import time
from pathlib import Path

from xai.core.time_capsule_protocol import TimeCapsuleProtocol


class DummyWallet:
    """Minimal wallet stub with deterministic keys."""

    def __init__(self, address="addr", priv="priv", pub="pub"):
        self.address = address
        self.private_key = priv
        self.public_key = pub


def test_initiate_and_claim_flow(tmp_path, monkeypatch):
    """Initiation requires eligibility and reserve funds; claim after unlock works."""
    data_dir = tmp_path
    # Seed reserve wallet file
    reserve = {
        "address": "reserve",
        "initial_balance": 500,
        "current_balance": 500,
        "disbursements_made": 0,
        "disbursement_amount": 450,
        "disbursement_history": [],
    }
    (data_dir / "TIME_CAPSULE_RESERVE.json").write_text(json.dumps(reserve))
    tcp = TimeCapsuleProtocol(data_dir=str(data_dir))
    monkeypatch.setattr("xai.core.time_capsule_protocol.Wallet", DummyWallet)
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now)
    monkeypatch.setattr("time.time", lambda: now)  # ensure module-level calls align

    wallet_data = {
        "address": "user",
        "private_key": "pk",
        "public_key": "pub",
        "time_capsule_eligible": True,
        "time_capsule_claimed": False,
        "initial_balance": 50,
        "time_capsule_bonus": 450,
    }

    res = tcp.initiate_time_capsule(wallet_data, user_accepted=True)
    assert res["success"] is True
    assert tcp.reserve_balance == 50  # 500 - 450

    locked_addr = wallet_data["address"]
    # Force unlock by setting past timestamp
    tcp.time_capsules[0]["unlock_timestamp_utc"] = now - 1
    claim = tcp.claim_time_capsule(locked_addr)
    assert claim["success"] is True
    assert claim["wallet"]["balance"] == 500


def test_eligibility_and_limits(tmp_path, monkeypatch):
    """Non-eligible wallets or insufficient reserve return errors."""
    data_dir = tmp_path
    reserve = {
        "address": "reserve",
        "initial_balance": 100,
        "current_balance": 100,
        "disbursements_made": 0,
        "disbursement_amount": 450,
        "disbursement_history": [],
    }
    (data_dir / "TIME_CAPSULE_RESERVE.json").write_text(json.dumps(reserve))
    tcp = TimeCapsuleProtocol(data_dir=str(data_dir))
    monkeypatch.setattr("xai.core.time_capsule_protocol.Wallet", DummyWallet)

    ineligible = {"address": "a", "time_capsule_eligible": False}
    res_ineligible = tcp.initiate_time_capsule(ineligible, user_accepted=True)
    assert res_ineligible["success"] is False

    eligible = {
        "address": "b",
        "private_key": "pk",
        "public_key": "pub",
        "time_capsule_eligible": True,
        "initial_balance": 50,
        "time_capsule_bonus": 450,
    }
    res_insufficient = tcp.initiate_time_capsule(eligible, user_accepted=True)
    assert res_insufficient["success"] is False
    assert "Insufficient reserve funds" in res_insufficient["error"]


def test_stats_and_unlock_status(tmp_path, monkeypatch):
    """Stats reflect locked/claimed counts; unlock checks report remaining days."""
    data_dir = tmp_path
    reserve = {
        "address": "reserve",
        "initial_balance": 500,
        "current_balance": 500,
        "disbursements_made": 0,
        "disbursement_amount": 450,
        "disbursement_history": [],
    }
    (data_dir / "TIME_CAPSULE_RESERVE.json").write_text(json.dumps(reserve))
    tcp = TimeCapsuleProtocol(data_dir=str(data_dir))
    monkeypatch.setattr("xai.core.time_capsule_protocol.Wallet", DummyWallet)

    eligible = {
        "address": "c",
        "private_key": "pk",
        "public_key": "pub",
        "time_capsule_eligible": True,
        "initial_balance": 50,
        "time_capsule_bonus": 450,
    }
    tcp.initiate_time_capsule(eligible, user_accepted=True)
    locked_addr = eligible["address"]
    stats = tcp.get_time_capsule_stats()
    assert stats["active_locked"] == 1

    status = tcp.check_unlock_eligibility(locked_addr)
    assert status["success"] is True
    assert status["unlocked"] is False

    # Claim to update stats
    tcp.time_capsules[0]["unlock_timestamp_utc"] = time.time() - 1
    tcp.claim_time_capsule(locked_addr)
    stats_after = tcp.get_time_capsule_stats()
    assert stats_after["total_claimed"] == 1
