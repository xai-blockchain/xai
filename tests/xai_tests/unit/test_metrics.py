"""
Unit tests for blockchain metrics helper wiring.
"""

import sys
import types

from prometheus_client import CollectorRegistry

# Provide dummy pythonjsonlogger for metrics import if dependency absent
if "pythonjsonlogger" not in sys.modules:
    jsonlogger = types.SimpleNamespace(JsonFormatter=lambda *a, **k: None)
    sys.modules["pythonjsonlogger"] = types.SimpleNamespace(jsonlogger=jsonlogger)

import xai.core.api.metrics as metrics_mod
from xai.core.api.prometheus_metrics import BlockchainMetrics as SimpleMetrics


# Stub StructuredLogger to avoid LogRecord 'message' clashes during tests
class _StubLogger:
    def __init__(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def log(self, *a, **k):
        pass

    def debug(self, *a, **k):
        pass


metrics_mod.StructuredLogger = _StubLogger
BlockchainMetrics = metrics_mod.BlockchainMetrics


def test_blockchain_metrics_updates_counters():
    """Basic metric update methods increment counters and gauges."""
    registry = CollectorRegistry()
    metrics = BlockchainMetrics(port=0, registry=registry, log_file=None)

    metrics.record_block(height=5, size=1024, difficulty=2, mining_time=3)
    metrics.record_transaction(status="confirmed", value=10, fee=0.1, processing_time=0.05)

    # Counters/gauges should be instantiated and have positive values recorded
    assert metrics.blocks_total._value.get() >= 1
    assert metrics.transactions_total.labels(status="confirmed")._value.get() >= 1


def test_prometheus_metrics_simplified_registration():
    """Simplified metrics class registers expected gauges/counters."""
    registry = CollectorRegistry()
    metrics = SimpleMetrics(port=0, registry=registry)
    metrics.blocks_total.inc()
    metrics.block_height.set(3)

    assert metrics.blocks_total._value.get() >= 1
    assert metrics.block_height._value.get() == 3
