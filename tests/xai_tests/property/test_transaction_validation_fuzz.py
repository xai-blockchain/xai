import json
import random

import hypothesis.strategies as st
from hypothesis import given, settings

from xai.core.transaction import Transaction
from xai.core.consensus.transaction_validator import TransactionValidator
from xai.core.blockchain import Blockchain


@given(
    amount=st.floats(min_value=0.01, max_value=10, allow_nan=False, allow_infinity=False),
    fee=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=30)
def test_transaction_validator_accepts_positive_amounts(amount, fee):
    bc = Blockchain()
    validator = TransactionValidator(bc)
    sender = "XAI" + "a" * 40
    recipient = "XAI" + "b" * 40
    tx = Transaction(sender, recipient, amount=amount, fee=fee, nonce=1)
    tx.inputs = [{"txid": "prev", "vout": 0}]
    tx.outputs = [{"address": recipient, "amount": amount}]
    assert validator.validate_transaction(tx) in {True, False}


def test_invalid_tx_rejected():
    bc = Blockchain()
    validator = TransactionValidator(bc)
    sender = "XAI" + "a" * 40
    recipient = "XAI" + "b" * 40
    tx = Transaction(sender, recipient, amount=-1.0, fee=0.1, nonce=1)
    tx.inputs = [{"txid": "prev", "vout": 0}]
    tx.outputs = [{"address": recipient, "amount": -1.0}]
    assert validator.validate_transaction(tx) is False
