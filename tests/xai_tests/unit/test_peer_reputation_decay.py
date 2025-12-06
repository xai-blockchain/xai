import time
import math

from xai.network.peer_manager import PeerReputation


def test_reputation_decays_toward_baseline(monkeypatch):
    rep = PeerReputation()
    peer = "peer1"

    # Start from neutral and penalize heavily
    rep.record_invalid_block(peer)
    rep.record_invalid_block(peer)
    low_score = rep.get_score(peer)
    assert low_score < rep.BASELINE_SCORE

    # Fast-forward time beyond a half-life and ensure score moves back toward baseline
    # Set a short half-life to make the test deterministic (~3.6 seconds)
    rep.DECAY_HALF_LIFE_HOURS = 0.001
    rep._decay_constant = math.log(2) / (rep.DECAY_HALF_LIFE_HOURS * 3600)

    # Advance time by two half-lives; score should be close to baseline
    monkeypatch.setenv("P2P_REPUTATION_DECAY_HALF_LIFE_HOURS", "0.001")
    original_time = time.time()

    def fake_time():
        return original_time + 8  # > two half-lives

    rep._last_decay[peer] = original_time
    rep.scores[peer] = low_score

    # Monkeypatch time module inside PeerReputation
    monkeypatch.setattr("xai.network.peer_manager.time.time", fake_time)
    decayed_score = rep.get_score(peer)

    assert decayed_score > low_score
    assert decayed_score < rep.BASELINE_SCORE + 1  # Close to baseline


def test_reputation_decay_does_not_exceed_bounds():
    rep = PeerReputation()
    peer = "peer2"
    rep.record_valid_block(peer)
    rep.record_valid_block(peer)
    rep._last_decay[peer] = time.time() - 60 * 60 * 24  # 1 day ago
    decayed = rep.get_score(peer)
    assert rep.MIN_SCORE <= decayed <= rep.MAX_SCORE
