"""
Tests for mempool eviction under load and RBF/conflict handling.
"""

from __future__ import annotations

import threading
import time
import pytest

from xai.core.blockchain_components.mempool_mixin import BlockchainMempoolMixin


class _DummyLogger:
    def __init__(self):
        self.logs = []

    def info(self, msg, **kwargs):
        self.logs.append(("info", msg, kwargs))

    def warn(self, msg, **kwargs):
        self.logs.append(("warn", msg, kwargs))

    def error(self, msg, **kwargs):
        self.logs.append(("error", msg, kwargs))


class _DummyNonceTracker:
    def __init__(self):
        self.reserved = []

    def reserve_nonce(self, sender, nonce):
        self.reserved.append((sender, nonce))


class _DummyUTXOManager:
    def get_utxos_for_address(self, _):
        return []

    def get_unspent_output(self, *_args, **_kwargs):
        return {}

    def unlock_utxos_by_keys(self, _):
        return None


class _DummyValidator:
    def validate_transaction(self, _):
        return True


class DummyBlockchain(BlockchainMempoolMixin):
    def __init__(self, max_size=5, max_per_sender=100):
        # Initialize required attributes for mixin
        self.pending_transactions = []
        self.orphan_transactions = []
        self.seen_txids = set()
        self._sender_pending_count = {}
        self._invalid_sender_tracker = {}
        self._mempool_lock = threading.RLock()
        self._mempool_max_age_seconds = 3600
        self._mempool_min_fee_rate = 0.0
        self._mempool_invalid_threshold = 3
        self._mempool_invalid_ban_seconds = 60
        self._mempool_invalid_window_seconds = 120
        self._mempool_rejected_invalid_total = 0
        self._mempool_rejected_banned_total = 0
        self._mempool_rejected_low_fee_total = 0
        self._mempool_rejected_sender_cap_total = 0
        self._mempool_evicted_low_fee_total = 0
        self._mempool_expired_total = 0
        self._mempool_max_size = max_size
        self._mempool_max_per_sender = max_per_sender
        self._mempool_rejected_invalid_total = 0
        self._mempool_rejected_low_fee_total = 0
        self._mempool_invalid_threshold = 3
        self._mempool_invalid_window_seconds = 60
        self._mempool_invalid_ban_seconds = 30
        self._mempool_rejected_sender_cap_total = 0
        self._spent_inputs = set()  # O(1) double-spend detection
        self.logger = _DummyLogger()
        self.utxo_manager = _DummyUTXOManager()
        self.transaction_validator = _DummyValidator()
        self.nonce_tracker = _DummyNonceTracker()


class DummyTx:
    def __init__(self, txid, sender, fee, nonce=None, fee_rate=None, inputs=None, timestamp=None, recipient="dest"):
        self.txid = txid
        self.sender = sender
        self.fee = fee
        self.nonce = nonce or 0
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.tx_type = "normal"
        self.signature = "sig"
        self.inputs = inputs or []
        self.outputs = []
        self.amount = fee  # minimal attribute to satisfy fee math in some paths
        self.recipient = recipient
        self.fee_rate = fee_rate if fee_rate is not None else fee

    def get_fee_rate(self):
        return self.fee_rate

    def calculate_hash(self):
        return self.txid

    def get_size(self):
        return 250


def test_eviction_when_full_keeps_high_fee():
    """When mempool is full, lowest fee-rate tx is evicted for higher fee-rate arrival."""
    bc = DummyBlockchain(max_size=2)
    tx_low = DummyTx("tx1", "a", fee=0.1)
    tx_high = DummyTx("tx2", "b", fee=1.0)
    bc.pending_transactions.extend([tx_low, tx_high])
    bc.seen_txids.update({"tx1", "tx2"})
    bc._sender_pending_count = {"a": 1, "b": 1}

    tx_mid = DummyTx("tx3", "c", fee=0.5)
    assert bc.add_transaction(tx_mid) is True
    fees = [tx.get_fee_rate() for tx in bc.pending_transactions]
    assert 0.1 not in fees
    assert 1.0 in fees and 0.5 in fees
    assert bc._mempool_evicted_low_fee_total == 1


def test_rbf_replaces_lower_fee_same_sender_nonce():
    """RBF replacement succeeds when replacement has higher fee rate."""
    bc = DummyBlockchain()
    original = DummyTx("tx1", "a", fee=0.5, nonce=1, inputs=[{"txid": "p", "vout": 0}], fee_rate=0.5)
    original.rbf_enabled = True
    replacement = DummyTx("tx2", "a", fee=0.7, nonce=1, inputs=[{"txid": "p", "vout": 0}], fee_rate=0.7)
    replacement.replaces_txid = "tx1"

    bc.pending_transactions.append(original)
    bc.seen_txids.add("tx1")
    bc._sender_pending_count["a"] = 1
    result = bc._handle_rbf_replacement(replacement)
    assert result is True
    assert bc.pending_transactions == []
    assert bc._sender_pending_count.get("a", 0) == 0


def test_rbf_rejects_lower_fee_same_nonce():
    """Replacement must improve fee rate to pass RBF checks."""
    bc = DummyBlockchain()
    original = DummyTx("tx1", "a", fee=1.0, nonce=1, inputs=[{"txid": "p", "vout": 0}], fee_rate=1.0)
    original.rbf_enabled = True
    replacement = DummyTx("tx2", "a", fee=0.95, nonce=1, inputs=[{"txid": "p", "vout": 0}], fee_rate=0.95)
    replacement.replaces_txid = "tx1"

    bc.pending_transactions.append(original)
    bc._sender_pending_count["a"] = 1
    result = bc._handle_rbf_replacement(replacement)
    assert result is False
    assert bc.pending_transactions[0].txid == "tx1"


def test_sender_cap_enforced():
    """Per-sender pending cap rejects excessive in-flight transactions."""
    bc = DummyBlockchain(max_size=10, max_per_sender=2)
    tx1 = DummyTx("t1", "spam", fee=0.2)
    tx2 = DummyTx("t2", "spam", fee=0.3)
    tx3 = DummyTx("t3", "spam", fee=0.4)

    assert bc.add_transaction(tx1) is True
    assert bc.add_transaction(tx2) is True
    assert bc.add_transaction(tx3) is False
    assert bc._mempool_rejected_sender_cap_total == 1
    assert bc._sender_pending_count["spam"] == 2


def test_invalid_sender_ban_and_expiry():
    """Repeated invalid submissions trigger ban and expire after window."""
    bc = DummyBlockchain()
    sender = "mal"
    now = 100.0

    bc._record_invalid_sender_attempt(sender, now)
    bc._record_invalid_sender_attempt(sender, now + 1)
    assert bc._is_sender_banned(sender, now + 2) is False

    bc._record_invalid_sender_attempt(sender, now + 2)
    assert bc._is_sender_banned(sender, now + 3) is True

    # After ban duration, sender is cleared
    assert bc._is_sender_banned(sender, now + bc._mempool_invalid_ban_seconds + 4) is False


def test_prune_expired_resets_counters():
    """Expired mempool entries are removed and sender counters rebuilt."""
    bc = DummyBlockchain()
    old_tx = DummyTx("old", "alice", fee=0.1, timestamp=0)
    fresh_tx = DummyTx("fresh", "bob", fee=0.2, timestamp=time.time())
    bc.pending_transactions = [old_tx, fresh_tx]
    bc._sender_pending_count = {"alice": 1, "bob": 1}
    removed = bc._prune_expired_mempool(current_time=time.time())
    assert removed == 1
    assert len(bc.pending_transactions) == 1
    assert bc.pending_transactions[0].txid == "fresh"
    assert bc._sender_pending_count == {"bob": 1}
    assert bc._mempool_expired_total == 1


def test_orphan_pool_pruning_and_overview():
    """Orphan expiry and overview stats reflect mempool contents."""
    bc = DummyBlockchain()
    old_orphan = DummyTx("orph1", "x", fee=0.01, timestamp=0)
    fresh_orphan = DummyTx("orph2", "y", fee=0.02, timestamp=time.time())
    bc.orphan_transactions = [old_orphan, fresh_orphan]

    removed = bc._prune_orphan_pool(current_time=time.time())
    assert removed == 1
    assert bc.orphan_transactions == [fresh_orphan]

    tx_a = DummyTx("a", "alice", fee=0.3, timestamp=time.time())
    tx_b = DummyTx("b", "bob", fee=0.7, timestamp=time.time())
    bc.pending_transactions = [tx_a, tx_b]
    overview = bc.get_mempool_overview(limit=10)

    assert overview["pending_count"] == 2
    assert overview["limits"]["max_transactions"] == bc._mempool_max_size
    assert overview["rejections"]["expired_total"] == bc._mempool_expired_total
    assert overview["transactions_returned"] == 2
    assert {t["txid"] for t in overview["transactions"]} == {"a", "b"}


def test_low_fee_rejected_when_full():
    """If mempool full and new fee rate is lower, transaction is rejected."""
    bc = DummyBlockchain(max_size=2)
    high = DummyTx("high", "s1", fee=1.0, fee_rate=1.0)
    mid = DummyTx("mid", "s2", fee=0.8, fee_rate=0.8)
    low = DummyTx("low", "s3", fee=0.1, fee_rate=0.1)
    bc.pending_transactions = [high, mid]
    bc.seen_txids = {"high", "mid"}

    assert bc.add_transaction(low) is False
    assert len(bc.pending_transactions) == 2
    assert bc._mempool_rejected_low_fee_total == 1


def test_duplicate_txid_rejected():
    """Duplicate txid is rejected even if other fields differ."""
    bc = DummyBlockchain()
    original = DummyTx("dup", "alice", fee=0.2)
    bc.pending_transactions.append(original)
    bc.seen_txids.add("dup")

    duplicate = DummyTx("dup", "alice", fee=0.5)
    assert bc.add_transaction(duplicate) is False
    assert len(bc.pending_transactions) == 1
