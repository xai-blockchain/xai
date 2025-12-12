"""
Unit tests for BlockchainMempoolMixin helpers.

Coverage targets:
- Expiration pruning of pending and orphan pools
- Sender ban tracking for invalid transactions
"""

import time
from collections import defaultdict

import pytest

from xai.core.blockchain_components.mempool_mixin import BlockchainMempoolMixin
import threading


class _Tx:
    def __init__(
        self,
        sender: str,
        txid: str,
        timestamp: float,
        inputs=None,
        fee: float = 0.0,
        size_bytes: int = 250,
        nonce: int | None = None,
        tx_type: str = "payment",
        recipient: str = "B",
        signature: str | None = None,
        replaces_txid: str | None = None,
        rbf_enabled: bool = False,
        amount: float = 0.0,
        gas_sponsor: str | None = None,
    ):
        self.sender = sender
        self.txid = txid
        self.timestamp = timestamp
        self.inputs = inputs or []
        self.fee = fee
        self.size_bytes = size_bytes
        self.nonce = nonce if nonce is not None else 0
        self.tx_type = tx_type
        self.recipient = recipient
        self.signature = signature
        self.replaces_txid = replaces_txid
        self.rbf_enabled = rbf_enabled
        self.outputs = []
        self.amount = amount
        self.gas_sponsor = gas_sponsor

    def get_fee_rate(self):
        return self.fee / self.size_bytes if self.size_bytes else 0.0

    def get_size(self):
        return self.size_bytes


class _UTXOManager:
    def __init__(self):
        self.unlocked = []

    def unlock_utxos_by_keys(self, keys):
        self.unlocked.extend(keys)

    def get_utxos_for_address(self, _address):
        return []

    def get_unspent_output(self, *_args, **_kwargs):
        return {}


class DummyMempool(BlockchainMempoolMixin):
    """Concrete harness supplying required attributes."""

    def __init__(self, now: float):
        self.pending_transactions = []
        self.orphan_transactions = []
        self.seen_txids = set()
        self._sender_pending_count = defaultdict(int)
        self._invalid_sender_tracker = {}
        self._mempool_lock = threading.RLock()
        self._mempool_max_size = 1000
        self._mempool_max_per_sender = 10
        self._mempool_max_age_seconds = 10
        self._mempool_min_fee_rate = 0.0
        self._mempool_invalid_threshold = 2
        self._mempool_invalid_ban_seconds = 30
        self._mempool_invalid_window_seconds = 60
        self._mempool_max_per_block = 2
        self._mempool_rejected_invalid_total = 0
        self._mempool_rejected_banned_total = 0
        self._mempool_rejected_low_fee_total = 0
        self._mempool_rejected_sender_cap_total = 0
        self._mempool_evicted_low_fee_total = 0
        self._mempool_expired_total = 0
        self.utxo_manager = _UTXOManager()
        self.nonce_tracker = type(
            "NonceTracker",
            (),
            {
                "get_nonce": lambda self, _addr=None: 0,
                "pending_nonces": {},
                "nonces": {},
                "reserve_nonce": lambda self, *_args, **_kwargs: None,
            },
        )()
        self.transaction_validator = type(
            "Validator", (), {"validate_transaction": lambda self, _tx=None: True}
        )()
        self.logger = type("Logger", (), {"info": lambda *a, **k: None, "warn": lambda *a, **k: None})()
        self.now = now

    def validate_transaction(self, tx):
        return True

    def _prioritize_transactions(self, txs, max_count=None):
        return super()._prioritize_transactions(txs, max_count=max_count)


def test_prune_expired_mempool_and_unlocks():
    """Expired transactions are removed, state rebuilt, and UTXOs unlocked."""
    now = time.time()
    mp = DummyMempool(now)
    old_tx = _Tx("A", "old", timestamp=now - 20, inputs=[{"txid": "p", "vout": 0}])
    fresh_tx = _Tx("B", "fresh", timestamp=now)
    mp.pending_transactions = [old_tx, fresh_tx]

    removed = mp._prune_expired_mempool(current_time=now)
    assert removed == 1
    assert len(mp.pending_transactions) == 1
    assert "fresh" in mp.pending_transactions[0].txid
    assert mp.utxo_manager.unlocked == [("p", 0)]
    assert mp._mempool_expired_total == 1
    assert mp._sender_pending_count["B"] == 1


def test_prune_orphan_pool():
    """Orphans older than max age are pruned."""
    now = time.time()
    mp = DummyMempool(now)
    mp.orphan_transactions = [_Tx("A", "o1", timestamp=now - 20), _Tx("B", "o2", timestamp=now)]
    removed = mp._prune_orphan_pool(current_time=now)
    assert removed == 1
    assert len(mp.orphan_transactions) == 1


def test_sender_ban_and_reset():
    """Repeated invalid attempts trigger ban, and bans expire after window reset."""
    now = time.time()
    mp = DummyMempool(now)
    sender = "attacker"
    # Two attempts trigger ban
    mp._record_invalid_sender_attempt(sender, current_time=now)
    mp._record_invalid_sender_attempt(sender, current_time=now + 1)
    assert mp._is_sender_banned(sender, current_time=now + 2) is True
    # After ban expires, sender unbanned and counters reset
    assert mp._is_sender_banned(sender, current_time=now + 100) is False


def test_rbf_replacement_success_and_state_updates():
    """RBF replacement removes original tx, decrements sender count, and enforces fee/overlap."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(sender="A", txid="orig", timestamp=now, inputs=[{"txid": "u1", "vout": 0}], fee=1, rbf_enabled=True)
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is True
    assert len(mp.pending_transactions) == 0
    assert mp._sender_pending_count["A"] == 0


def test_rbf_replacement_rejects_mismatch_and_retains_original():
    """Mismatch sender or lower fee blocks replacement and leaves original intact."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(sender="A", txid="orig", timestamp=now, inputs=[{"txid": "u1", "vout": 0}], fee=2, rbf_enabled=True)
    replacement = _Tx(
        sender="B",  # different sender
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=1,  # lower fee
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is False
    assert len(mp.pending_transactions) == 1
    assert mp.pending_transactions[0].txid == "orig"


def test_add_transaction_rejects_sender_cap():
    """Per-sender cap stops admission when count already at limit."""
    now = time.time()
    mp = DummyMempool(now)
    mp._mempool_max_per_sender = 1
    existing = _Tx(sender="S", txid="t1", timestamp=now, signature="sig", fee=1.0)
    mp.pending_transactions = [existing]
    mp.seen_txids = {"t1"}
    tx = _Tx(sender="S", txid="t2", timestamp=now, signature="sig", fee=1.5)

    accepted = mp.add_transaction(tx)

    assert accepted is False
    assert mp._mempool_rejected_sender_cap_total == 1


def test_fee_eviction_prefers_higher_fee_rate():
    """When mempool full, higher fee rate replaces lowest-fee tx and updates counters."""
    now = time.time()
    mp = DummyMempool(now)
    mp._mempool_max_size = 1
    low = _Tx(sender="A", txid="low", timestamp=now, fee=1.0, size_bytes=250, signature="sig")
    mp.pending_transactions = [low]
    mp.seen_txids = {"low"}
    mp._sender_pending_count["A"] = 1

    high = _Tx(sender="B", txid="high", timestamp=now, fee=5.0, size_bytes=250, signature="sig")

    accepted = mp.add_transaction(high)

    assert accepted is True
    assert mp.pending_transactions[-1].txid == "high"
    assert "low" not in mp.seen_txids
    assert mp._mempool_evicted_low_fee_total == 1


def test_low_fee_rejected_when_mempool_full():
    """Lower fee rate is rejected when mempool is full and eviction not justified."""
    now = time.time()
    mp = DummyMempool(now)
    mp._mempool_max_size = 1
    existing = _Tx(sender="A", txid="hi", timestamp=now, fee=5.0, size_bytes=250, signature="sig")
    mp.pending_transactions = [existing]
    mp.seen_txids = {"hi"}
    mp._sender_pending_count["A"] = 1

    low = _Tx(sender="B", txid="lo", timestamp=now, fee=1.0, size_bytes=250, signature="sig")

    accepted = mp.add_transaction(low)

    assert accepted is False
    assert mp._mempool_rejected_low_fee_total == 1
    assert mp.pending_transactions[0].txid == "hi"


def test_mempool_full_with_same_sender_preserves_nonce_and_rejects_over_cap():
    """When sender has sequential nonces and mempool full, lower fee same-sender tx rejected."""
    now = time.time()
    mp = DummyMempool(now)
    mp._mempool_max_size = 1
    mp._mempool_max_per_sender = 2
    existing = _Tx(sender="A", txid="a1", timestamp=now, fee=5.0, size_bytes=250, signature="sig", nonce=1)
    mp.pending_transactions = [existing]
    mp.seen_txids = {"a1"}
    mp._sender_pending_count["A"] = 1

    new_tx = _Tx(sender="A", txid="a0", timestamp=now, fee=1.0, size_bytes=250, signature="sig", nonce=0)

    accepted = mp.add_transaction(new_tx)

    assert accepted is False
    assert mp._mempool_rejected_low_fee_total == 1


def test_fee_eviction_with_same_sender_updates_counters():
    """Higher-fee replacement from same sender evicts lower-fee tx and updates counts."""
    now = time.time()
    mp = DummyMempool(now)
    mp._mempool_max_size = 1
    low = _Tx(sender="A", txid="low", timestamp=now, fee=1.0, size_bytes=250, signature="sig")
    mp.pending_transactions = [low]
    mp.seen_txids = {"low"}
    mp._sender_pending_count["A"] = 1

    high = _Tx(sender="A", txid="high", timestamp=now, fee=3.0, size_bytes=250, signature="sig")

    accepted = mp.add_transaction(high)

    assert accepted is True
    assert mp.pending_transactions[-1].txid == "high"
    assert mp._sender_pending_count["A"] == 1
    assert "low" not in mp.seen_txids


def test_active_ban_count_and_reset_on_expiry():
    """Active ban count decreases after expiry and state resets."""
    now = time.time()
    mp = DummyMempool(now)
    sender = "S"
    mp._record_invalid_sender_attempt(sender, current_time=now)
    mp._record_invalid_sender_attempt(sender, current_time=now + 1)  # triggers ban

    assert mp._count_active_bans(now + 2) == 1
    # After expiry, ban cleared and count resets
    assert mp._count_active_bans(now + mp._mempool_invalid_ban_seconds + 5) == 0
    assert mp._invalid_sender_tracker[sender]["count"] == 0


def test_rbf_replacement_missing_original_returns_false():
    """RBF replacement fails when original not found."""
    mp = DummyMempool(time.time())
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=time.time(),
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        replaces_txid="missing",
    )

    assert mp._handle_rbf_replacement(replacement) is False


def test_rbf_replacement_requires_overlapping_inputs():
    """Replacement without overlapping inputs is rejected and original retained."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(
        sender="A",
        txid="orig",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        rbf_enabled=True,
    )
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "other", "vout": 0}],
        fee=3,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is False
    assert mp.pending_transactions[0].txid == "orig"


def test_prioritize_transactions_orders_by_fee_rate_desc():
    """Transactions are ordered by fee rate descending."""
    mp = DummyMempool(time.time())
    tx_a = _Tx(sender="A", txid="a", timestamp=time.time(), fee=1.0, size_bytes=100, nonce=1)
    tx_b = _Tx(sender="B", txid="b", timestamp=time.time(), fee=4.0, size_bytes=200, nonce=0)
    tx_c = _Tx(sender="C", txid="c", timestamp=time.time(), fee=2.0, size_bytes=100, nonce=0)

    ordered = mp._prioritize_transactions([tx_a, tx_b, tx_c])

    assert [t.txid for t in ordered] == ["b", "c", "a"]


def test_prioritize_transactions_preserves_sender_nonce_order():
    """Same-sender transactions remain in nonce order even when fee rates equal."""
    mp = DummyMempool(time.time())
    tx1 = _Tx(sender="A", txid="a1", timestamp=time.time(), fee=1.0, size_bytes=100, nonce=2)
    tx0 = _Tx(sender="A", txid="a0", timestamp=time.time(), fee=1.0, size_bytes=100, nonce=1)

    ordered = mp._prioritize_transactions([tx1, tx0])

    assert [t.txid for t in ordered] == ["a0", "a1"]


def test_prioritize_transactions_respects_max_count():
    """max_count limits returned transactions after ordering."""
    mp = DummyMempool(time.time())
    txs = [
        _Tx(sender="A", txid="t1", timestamp=time.time(), fee=1.0, size_bytes=100, nonce=0),
        _Tx(sender="B", txid="t2", timestamp=time.time(), fee=3.0, size_bytes=100, nonce=0),
        _Tx(sender="C", txid="t3", timestamp=time.time(), fee=2.0, size_bytes=100, nonce=0),
    ]

    ordered = mp._prioritize_transactions(txs, max_count=2)

    assert len(ordered) == 2
    assert [t.txid for t in ordered] == ["t2", "t3"]


def test_prioritize_transactions_grouped_nonce_blocking():
    """Fee sorting can reorder same-sender txs; ensure both returned."""
    mp = DummyMempool(time.time())
    tx_low_nonce = _Tx(sender="A", txid="a0", timestamp=time.time(), fee=0.5, size_bytes=100, nonce=0)
    tx_high_nonce_high_fee = _Tx(sender="A", txid="a1", timestamp=time.time() + 10, fee=5.0, size_bytes=100, nonce=1)

    ordered = mp._prioritize_transactions([tx_high_nonce_high_fee, tx_low_nonce])

    assert set(t.txid for t in ordered) == {"a0", "a1"}


def test_get_mempool_overview_and_size_kb():
    """Overview reports counts, limits, fee stats, and includes transaction summaries."""
    now = time.time()
    mp = DummyMempool(now)
    tx1 = _Tx(sender="A", txid="t1", timestamp=now - 5, fee=2.0, size_bytes=200, nonce=1, amount=10)
    tx2 = _Tx(sender="B", txid="t2", timestamp=now - 1, fee=1.0, size_bytes=100, nonce=0, amount=5, gas_sponsor="S")
    mp.pending_transactions = [tx1, tx2]

    overview = mp.get_mempool_overview(limit=2)
    assert overview["pending_count"] == 2
    assert overview["limits"]["max_transactions"] == mp._mempool_max_size
    assert overview["transactions_returned"] == 2
    assert {t["txid"] for t in overview["transactions"]} == {"t1", "t2"}
    assert overview["transactions"][0]["fee_rate"] == tx1.get_fee_rate()
    assert overview["sponsored_transactions"] == 1

    size_kb = mp.get_mempool_size_kb()
    assert size_kb == (tx1.get_size() + tx2.get_size()) / 1024.0


def test_prioritize_transactions_max_per_block_limits():
    """max_count trims prioritized list after fee/nonce ordering."""
    now = time.time()
    mp = DummyMempool(now)
    txs = [
        _Tx(sender="A", txid="t1", timestamp=now, fee=1.0, size_bytes=100, nonce=0),
        _Tx(sender="B", txid="t2", timestamp=now, fee=2.0, size_bytes=100, nonce=0),
        _Tx(sender="C", txid="t3", timestamp=now, fee=3.0, size_bytes=100, nonce=0),
    ]

    ordered = mp._prioritize_transactions(txs, max_count=mp._mempool_max_per_block)

    assert len(ordered) == mp._mempool_max_per_block
    assert [t.txid for t in ordered] == ["t3", "t2"]


def test_rbf_replacement_requires_opt_in_flag():
    """RBF fails when original did not opt in."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(sender="A", txid="orig", timestamp=now, inputs=[{"txid": "u1", "vout": 0}], fee=2, rbf_enabled=False)
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=3,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is False
    assert mp.pending_transactions[0].txid == "orig"


def test_rbf_replacement_sender_mismatch_rejected():
    """Replacement from different sender must be rejected to block theft."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(
        sender="A",
        txid="orig",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        rbf_enabled=True,
    )
    replacement = _Tx(
        sender="B",
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=3,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is False
    assert mp.pending_transactions[0].txid == "orig"


def test_rbf_replacement_requires_higher_fee_rate():
    """Replacement must pay strictly higher fee-per-byte."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(
        sender="A",
        txid="orig",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        size_bytes=100,
        rbf_enabled=True,
    )
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,  # same fee -> same rate
        size_bytes=100,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is False
    assert mp.pending_transactions[0].txid == "orig"


def test_rbf_replacement_successfully_updates_state():
    """Valid replacement removes original and keeps sender counters accurate."""
    now = time.time()
    mp = DummyMempool(now)
    original = _Tx(
        sender="A",
        txid="orig",
        timestamp=now,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=1,
        size_bytes=100,
        rbf_enabled=True,
    )
    replacement = _Tx(
        sender="A",
        txid="repl",
        timestamp=now + 1,
        inputs=[{"txid": "u1", "vout": 0}],
        fee=2,
        size_bytes=100,
        replaces_txid="orig",
    )
    mp.pending_transactions = [original]
    mp.seen_txids = {"orig"}
    mp._sender_pending_count["A"] = 1

    assert mp._handle_rbf_replacement(replacement) is True
    assert mp.pending_transactions == []
    assert "orig" not in mp.seen_txids
    assert mp._sender_pending_count["A"] == 0
