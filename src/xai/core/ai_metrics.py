"""Metrics tracking for AI bridge and development pool."""


class MetricsCollector:
    """Collect and track metrics for the blockchain and AI systems."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics to initial state."""
        self._data = {
            "queue_events": 0,
            "completed_tasks": 0,
            "bridge_syncs": 0,
            "tokens_used": 0,
        }

    def record_queue_event(self):
        """Record a proposal queue event."""
        self._data["queue_events"] += 1

    def record_bridge_sync(self):
        """Record a bridge sync event."""
        self._data["bridge_syncs"] += 1

    def record_completed_task(self):
        """Record a completed task."""
        self._data["completed_tasks"] += 1

    def record_tokens(self, tokens: int):
        """Record tokens used."""
        self._data["tokens_used"] += tokens

    def get_snapshot(self):
        """Get a snapshot of current metrics."""
        return self._data.copy()


# Global metrics instance
metrics = MetricsCollector()


def reset_metrics():
    """Reset all metrics to initial state."""
    metrics.reset()
