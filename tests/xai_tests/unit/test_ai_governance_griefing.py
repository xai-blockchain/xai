"""
Tests for governance fraud detector covering burst/griefing scenarios.
"""

import time

from xai.core.ai_governance import GovernanceFraudDetector


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
