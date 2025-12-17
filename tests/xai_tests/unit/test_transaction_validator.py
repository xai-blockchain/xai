import time

import pytest

from xai.core.transaction_validator import TransactionValidator
from xai.core.blockchain import Transaction
from xai.core.vm.exceptions import VMExecutionError


class StubUTXOManager:
    def __init__(self, utxo_map):
        self.utxo_map = utxo_map

    def get_unspent_output(self, txid, vout, exclude_pending=False):
        return self.utxo_map.get((txid, vout))


class StubNonceTracker:
    def __init__(self, next_nonce=1, valid=True):
        self._next = next_nonce
        self._valid = valid

    def get_next_nonce(self, sender):
        return self._next

    def validate_nonce(self, sender, nonce):
        return self._valid

    def get_nonce(self, sender):
        return self._next - 1


class StubLogger:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def warn(self, msg, **kwargs):
        self.warnings.append((msg, kwargs))

    def error(self, msg, **kwargs):
        self.errors.append((msg, kwargs))

    def debug(self, *args, **kwargs):
        return None


class StubBlockchain:
    def __init__(self, pending=None):
        self.pending_transactions = pending or []


SENDER = "TXAI" + "0" * 40
RECIPIENT = "TXAI" + "1" * 40


def _build_tx(
    *,
    timestamp_override: float | None = None,
    inputs_override=None,
    outputs_override=None,
    verify_signature_override=None,
):
    now = time.time()
    tx = Transaction(
        sender=SENDER,
        recipient=RECIPIENT,
        amount=1.0,
        fee=0.001,
        tx_type="normal",
        nonce=1,
        inputs=inputs_override or [{"txid": "prev", "vout": 0}],
        outputs=outputs_override or [{"address": RECIPIENT, "amount": 1.0}],
        metadata={},
    )
    tx.timestamp = timestamp_override if timestamp_override is not None else now
    tx.signature = "a" * 128
    tx.txid = tx.calculate_hash()
    tx.verify_signature = verify_signature_override or (lambda: True)  # type: ignore[method-assign]
    return tx


def test_valid_transaction_passes_all_checks():
    utxo_manager = StubUTXOManager({("prev", 0): {"amount": 1.001, "script_pubkey": f"P2PKH {SENDER}"}})
    nonce_tracker = StubNonceTracker(next_nonce=1)
    logger = StubLogger()
    blockchain = StubBlockchain()

    validator = TransactionValidator(
        blockchain,
        nonce_tracker=nonce_tracker,
        logger=logger,
        utxo_manager=utxo_manager,
    )

    tx = _build_tx()
    assert validator.validate_transaction(tx) is True
    assert not logger.warnings
    assert not logger.errors


def test_rejects_old_timestamp_and_logs_warning():
    utxo_manager = StubUTXOManager({("prev", 0): {"amount": 1.001, "script_pubkey": f"P2PKH {SENDER}"}})
    validator = TransactionValidator(
        StubBlockchain(),
        nonce_tracker=StubNonceTracker(next_nonce=1),
        logger=StubLogger(),
        utxo_manager=utxo_manager,
    )

    old_ts = time.time() - 4000
    tx = _build_tx(timestamp_override=old_ts)
    assert validator.validate_transaction(tx) is False


def test_rejects_missing_inputs():
    validator = TransactionValidator(
        StubBlockchain(),
        nonce_tracker=StubNonceTracker(next_nonce=1),
        logger=StubLogger(),
        utxo_manager=StubUTXOManager({}),
    )

    tx = _build_tx(inputs_override=[])
    assert validator.validate_transaction(tx) is False


def test_rejects_duplicate_pending_nonce():
    pending_tx = _build_tx()
    blockchain = StubBlockchain(pending=[pending_tx])
    validator = TransactionValidator(
        blockchain,
        nonce_tracker=StubNonceTracker(next_nonce=1, valid=False),
        logger=StubLogger(),
        utxo_manager=StubUTXOManager({("prev", 0): {"amount": 1.001, "script_pubkey": f"P2PKH {SENDER}"}}),
    )

    tx = _build_tx()
    assert validator.validate_transaction(tx) is False
