from xai.core.blockchain_components import mining_mixin


def test_record_economic_metrics_invokes_helper(monkeypatch):
    captured = []

    def fake_record(metric_name, value, operation="inc", labels=None):
        captured.append((metric_name, value))

    monkeypatch.setattr(mining_mixin, "_record_mining_metrics", fake_record)
    mining_mixin._record_economic_metrics(12.5, 1.25, 0.75, 14.5)

    assert ("xai_economic_block_reward_total", 12.5) in captured
    assert ("xai_economic_fees_total", 1.25) in captured
    assert ("xai_economic_streak_bonus_total", 0.75) in captured
    assert ("xai_economic_coinbase_payout_total", 14.5) in captured
