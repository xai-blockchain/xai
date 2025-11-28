import contextlib

import pytest

from xai.core.monitoring import MetricsCollector
from xai.core.security_validation import SecurityEventRouter


@pytest.fixture
def security_router_reset():
    original_sinks = list(SecurityEventRouter._sinks)
    SecurityEventRouter._sinks = []
    yield
    SecurityEventRouter._sinks = original_sinks


@pytest.fixture
def metrics_reset():
    # MetricsCollector uses a singleton; snapshot and restore to avoid cross-test pollution.
    original = getattr(MetricsCollector, "_instance", None)
    with contextlib.suppress(Exception):
        MetricsCollector._instance = None
    metrics = MetricsCollector(update_interval=0)
    yield metrics
    MetricsCollector._instance = original


def test_p2p_security_probes_increment_metrics(security_router_reset, metrics_reset):
    metrics = metrics_reset

    SecurityEventRouter.register_sink(lambda event, details, severity: metrics.record_security_event(event, severity, details))

    SecurityEventRouter.dispatch("p2p.replay_detected", {"peer": "replay-test"}, "WARNING")
    SecurityEventRouter.dispatch("p2p.rate_limited", {"peer": "rate-test"}, "WARNING")
    SecurityEventRouter.dispatch("p2p.invalid_signature", {"peer": "sig-test"}, "ERROR")

    replay_metric = metrics.get_metric("xai_p2p_nonce_replay_total")
    rate_metric = metrics.get_metric("xai_p2p_rate_limited_total")
    invalid_metric = metrics.get_metric("xai_p2p_invalid_signature_total")

    assert replay_metric is not None and replay_metric.value >= 1
    assert rate_metric is not None and rate_metric.value >= 1
    assert invalid_metric is not None and invalid_metric.value >= 1

    # Verify severity counters also tick for warnings/errors
    warn_metric = metrics.get_metric("xai_security_events_warning_total")
    crit_metric = metrics.get_metric("xai_security_events_critical_total")
    assert warn_metric is not None and warn_metric.value >= 2  # replay + rate limited
    assert crit_metric is not None and crit_metric.value >= 1  # invalid signature
