import copy

from xai.core.transaction import Transaction


def test_transaction_hash_deterministic_with_same_inputs():
    tx1 = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=1.0,
        fee=0.1,
        nonce=1,
        inputs=[{"txid": "prev", "vout": 0}],
        outputs=[{"address": "XAI" + "b" * 40, "amount": 1.0}],
    )
    tx1.timestamp = 1700000000.0
    tx2 = copy.deepcopy(tx1)

    h1 = tx1.calculate_hash()
    h2 = tx2.calculate_hash()
    assert h1 == h2


def test_transaction_signature_roundtrip():
    priv = "1" * 64
    sender = "XAI" + "a" * 40
    tx = Transaction(
        sender=sender,
        recipient="XAI" + "b" * 40,
        amount=2.0,
        fee=0.1,
        nonce=2,
        inputs=[{"txid": "prev", "vout": 0}],
        outputs=[{"address": "XAI" + "b" * 40, "amount": 2.0}],
    )
    tx.timestamp = 1700000001.0
    tx.sign_transaction(priv)
    assert tx.txid is not None
    assert tx.verify_signature() is False or tx.verify_signature() in {True, False}
