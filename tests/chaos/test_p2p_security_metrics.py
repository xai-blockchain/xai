from xai.core.monitoring import MetricsCollector


def test_p2p_security_metrics_spike_simulation():
    metrics = MetricsCollector(update_interval=0)
    for _ in range(5):
        metrics.record_security_event("p2p.replay_detected", "WARNING", {"peer": "peer-a"})
    for _ in range(10):
        metrics.record_security_event("p2p.rate_limited", "WARNING", {"peer": "peer-b"})
    for _ in range(3):
        metrics.record_security_event("p2p.invalid_signature", "ERROR", {"peer": "peer-c"})

    assert metrics.get_metric("xai_p2p_nonce_replay_total").value >= 5
    assert metrics.get_metric("xai_p2p_rate_limited_total").value >= 10
    assert metrics.get_metric("xai_p2p_invalid_signature_total").value >= 3
