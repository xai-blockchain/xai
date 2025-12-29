"""
Unit tests for StateManager mempool/orphan pruning and snapshot helpers.
"""

import threading
import time
from types import SimpleNamespace

from xai.core.chain.state_manager import StateManager


class DummyBlockchain:
    """Minimal blockchain stub to satisfy StateManager dependencies."""

    def __init__(self):
        self._chain_lock = threading.Lock()
        self._mempool_lock = threading.Lock()
        self.chain = []
        self.pending_transactions = []
        self.orphan_transactions = []
        self.orphan_blocks = {}
        self._mempool_max_age_seconds = 10
        self._mempool_expired_total = 0
        self._state_integrity_snapshots = []
        self.utxo_manager = SimpleNamespace(utxo_set={})
        self.difficulty = 1


def test_prune_expired_mempool(monkeypatch):
    """Expired mempool entries are removed and counters updated."""
    bc = DummyBlockchain()
    bc.pending_transactions = [
        SimpleNamespace(timestamp=0),
        SimpleNamespace(timestamp=12),
    ]
    mgr = StateManager(bc)

    monkeypatch.setattr(time, "time", lambda: 20)

    pruned = mgr.prune_expired_mempool()

    assert pruned == 1
    assert len(bc.pending_transactions) == 1
    assert bc._mempool_expired_total == 1


def test_prune_orphan_pool(monkeypatch):
    """Old orphan transactions are dropped based on max age."""
    bc = DummyBlockchain()
    bc.orphan_transactions = [
        SimpleNamespace(timestamp=0),
        SimpleNamespace(timestamp=3500),
    ]
    mgr = StateManager(bc)
    monkeypatch.setattr(time, "time", lambda: 4000)

    pruned = mgr.prune_orphan_pool()

    assert pruned == 1
    assert len(bc.orphan_transactions) == 1


def test_compute_state_snapshot_and_overview():
    """Snapshot and mempool overview reflect blockchain attributes."""
    bc = DummyBlockchain()
    bc.chain = [SimpleNamespace(hash="h1", index=1)]
    bc.pending_transactions = [
        SimpleNamespace(
            txid="tx1",
            sender="a",
            recipient="b",
            amount=1,
            fee=0.1,
            timestamp=1.0,
            tx_type="normal",
        )
    ]
    bc.orphan_transactions = []
    bc.orphan_blocks = {5: [SimpleNamespace(hash="h-orphan")]}
    bc.utxo_manager.utxo_set = {"k": "v"}
    mgr = StateManager(bc)

    snapshot = mgr.compute_state_snapshot()
    overview = mgr.get_mempool_overview()

    assert snapshot["chain_length"] == 1
    assert snapshot["orphan_block_count"] == 1
    assert overview["total"] == 1
    assert overview["orphan_count"] == 0
    assert overview["transactions"][0]["txid"] == "tx1"
