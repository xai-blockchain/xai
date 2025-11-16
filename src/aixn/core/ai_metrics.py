"""Stub for metrics module."""


_metrics_data = {}


def metrics():
    return _metrics_data.copy()


def reset_metrics():
    """Reset all metrics to initial state."""
    global _metrics_data
    _metrics_data = {}
