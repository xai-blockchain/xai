from dataclasses import dataclass, field
import threading
import time
from typing import Dict

from prometheus_client import Counter, Gauge


@dataclass
class AIMetricsSnapshot:
    queue_events: int = 0
    completed_tasks: int = 0
    tokens_consumed: int = 0
    bridge_syncs: int = 0
    last_sync: float = 0.0
    memory: Dict[str, int] = field(default_factory=dict)


class AIMetrics:
    queue_counter = Counter('xai_ai_bridge_queue_events_total', 'Queue events processed by the AI bridge')
    completed_counter = Counter('xai_ai_completed_tasks_total', 'Number of AI tasks completed')
    tokens_counter = Counter('xai_ai_tokens_consumed_total', 'Total donated AI tokens consumed')
    bridge_counter = Counter('xai_ai_bridge_sync_total', 'AI bridge sync operations')
    last_sync_gauge = Gauge('xai_ai_bridge_last_sync_timestamp', 'Timestamp of the last AI bridge sync')

    def __init__(self):
        self.lock = threading.Lock()
        self.snapshot = AIMetricsSnapshot()

    def reset(self):
        with self.lock:
            self.snapshot = AIMetricsSnapshot()

    def record_bridge_sync(self):
        with self.lock:
            self.snapshot.bridge_syncs += 1
            self.snapshot.last_sync = time.time()
        self.bridge_counter.inc()
        self.last_sync_gauge.set(time.time())

    def record_queue_event(self):
        with self.lock:
            self.snapshot.queue_events += 1
        self.queue_counter.inc()

    def record_completed_task(self):
        with self.lock:
            self.snapshot.completed_tasks += 1
        self.completed_counter.inc()

    def record_tokens(self, tokens: int):
        if tokens <= 0:
            return
        with self.lock:
            self.snapshot.tokens_consumed += tokens
        self.tokens_counter.inc(tokens)

    def record(self, key: str, value: int = 1):
        with self.lock:
            self.snapshot.memory[key] = self.snapshot.memory.get(key, 0) + value

    def get_snapshot(self) -> Dict:
        with self.lock:
            data = {
                'queue_events': self.snapshot.queue_events,
                'completed_tasks': self.snapshot.completed_tasks,
                'tokens_consumed': self.snapshot.tokens_consumed,
                'bridge_syncs': self.snapshot.bridge_syncs,
                'last_sync': self.snapshot.last_sync,
                'custom': dict(self.snapshot.memory)
            }
        return data


metrics = AIMetrics()


def reset_metrics():
    metrics.reset()
