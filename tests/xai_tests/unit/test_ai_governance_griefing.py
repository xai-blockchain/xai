"""
Tests for governance fraud detector covering burst/griefing scenarios.
"""

import pytest
import time

from xai.core.governance.ai_governance import GovernanceFraudDetector


def test_burst_activity_triggers_alert(monkeypatch):
    """Low-cost burst of votes within window raises burst alert."""
    detector = GovernanceFraudDetector()
    now = time.time()
    monkeypatch.setattr("xai.core.ai_governance.time.time", lambda: now)

    # Simulate rapid votes from many addresses
    for i in range(detector.BURST_MIN_TOTAL):
        detector.record_vote(
            proposal_id="p1",
            voter_address=f"addr{i}",
            voting_power=1.0,
            metadata={},
        )

    alerts = detector.get_alerts("p1")
    assert any(alert.get("type") == "burst_activity" for alert in alerts)


def test_power_skew_alert(monkeypatch):
    """Few voters controlling majority power triggers skew alert."""
    detector = GovernanceFraudDetector()
    now = time.time()
    monkeypatch.setattr("xai.core.ai_governance.time.time", lambda: now)

    meta_cluster = {"wallet_cluster": "clusterA"}
    detector.record_vote("p2", "whale1", voting_power=70.0, metadata=meta_cluster)
    detector.record_vote("p2", "whale2", voting_power=20.0, metadata=meta_cluster)
    detector.record_vote("p2", "small1", voting_power=1.0, metadata=meta_cluster)

    alerts = detector.get_alerts("p2")
    assert any(alert.get("type") in ("power_skew", "power_anomaly") for alert in alerts)


def test_new_account_swarm_alert(monkeypatch):
    """Many newly created accounts voting quickly should trigger swarm alert."""
    detector = GovernanceFraudDetector()
    base_time = time.time()

    def fake_time():
        return fake_time.current

    fake_time.current = base_time
    monkeypatch.setattr("xai.core.ai_governance.time.time", fake_time)

    for idx in range(detector.NEW_ACCOUNT_MIN_VOTERS):
        fake_time.current = base_time + idx  # keep within window
        detector.record_vote(
            proposal_id="swarm",
            voter_address=f"newbie{idx}",
            voting_power=detector.NEW_ACCOUNT_MIN_POWER / detector.NEW_ACCOUNT_MIN_VOTERS,
            metadata={"account_age_days": 0.5},
        )

    alerts = detector.get_alerts("swarm")
    assert any(alert.get("type") == "new_account_suspicion" for alert in alerts)


def test_identity_cluster_alert(monkeypatch):
    """Multiple voters sharing the same IP subnet should raise cluster alert."""
    detector = GovernanceFraudDetector()
    now = time.time()
    monkeypatch.setattr("xai.core.ai_governance.time.time", lambda: now)

    for idx in range(detector.CLUSTER_MIN_UNIQUE):
        detector.record_vote(
            proposal_id="cluster",
            voter_address=f"cluster_addr{idx}",
            voting_power=detector.CLUSTER_MIN_POWER / detector.CLUSTER_MIN_UNIQUE,
            metadata={"ip_address": "10.0.1.%d" % idx},
        )

    alerts = detector.get_alerts("cluster")
    assert any(alert.get("type") == "identity_cluster" for alert in alerts)
