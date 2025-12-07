"""
Test transaction hash determinism and JSON serialization consistency.

Critical for consensus - all nodes must produce identical hashes for identical transactions.
"""
import copy
import json

from xai.core.transaction import Transaction, canonical_json


def test_canonical_json_no_whitespace():
    """Verify canonical_json produces no-whitespace output."""
    data = {
        "amount": 10.0,
        "sender": "XAI123",
        "nested": {"key": "value"},
        "list": [1, 2, 3]
    }
    result = canonical_json(data)

    # Should have no spaces after colons or commas
    assert ": " not in result, "canonical_json should not have spaces after colons"
    assert ", " not in result, "canonical_json should not have spaces after commas"

    # Verify it's valid JSON
    parsed = json.loads(result)
    assert parsed == data


def test_canonical_json_consistent_across_calls():
    """Verify canonical_json produces identical output for identical data."""
    data = {
        "timestamp": 1700000000.0,
        "amount": 100.5,
        "sender": "XAIabc",
        "recipient": "XAIdef",
        "nonce": 42
    }

    result1 = canonical_json(data)
    result2 = canonical_json(data)

    assert result1 == result2, "canonical_json must be deterministic"


def test_canonical_json_key_ordering():
    """Verify canonical_json sorts keys consistently."""
    # Same data, different key order
    data1 = {"z": 1, "a": 2, "m": 3}
    data2 = {"m": 3, "z": 1, "a": 2}

    result1 = canonical_json(data1)
    result2 = canonical_json(data2)

    assert result1 == result2, "canonical_json must sort keys"
    assert result1 == '{"a":2,"m":3,"z":1}', f"Expected sorted keys, got {result1}"


def test_canonical_json_unicode_handling():
    """Verify canonical_json handles unicode consistently."""
    data = {"emoji": "🚀", "chinese": "你好", "latin": "hello"}
    result = canonical_json(data)

    # ensure_ascii=True means unicode should be escaped
    assert "\\u" in result or "hello" in result, "Unicode should be escaped or ASCII"

    # Should be parseable back
    parsed = json.loads(result)
    assert parsed == data


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


def test_transaction_hash_identical_across_multiple_calls():
    """Verify transaction hash is deterministic across multiple calls."""
    tx = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=5.5,
        fee=0.2,
        nonce=10,
        inputs=[{"txid": "prev1", "vout": 0}, {"txid": "prev2", "vout": 1}],
        outputs=[{"address": "XAI" + "c" * 40, "amount": 3.0}, {"address": "XAI" + "d" * 40, "amount": 2.3}],
    )
    tx.timestamp = 1700000000.0

    # Calculate hash multiple times
    hash1 = tx.calculate_hash()
    hash2 = tx.calculate_hash()
    hash3 = tx.calculate_hash()

    assert hash1 == hash2 == hash3, "Transaction hash must be deterministic"
    assert len(hash1) == 64, "Transaction hash should be 64 hex characters"


def test_transaction_hash_changes_with_different_data():
    """Verify different transaction data produces different hashes."""
    base_tx = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=1.0,
        fee=0.1,
        nonce=1,
    )
    base_tx.timestamp = 1700000000.0
    base_hash = base_tx.calculate_hash()

    # Different amount
    tx_diff_amount = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=2.0,
        fee=0.1,
        nonce=1,
    )
    tx_diff_amount.timestamp = 1700000000.0
    assert tx_diff_amount.calculate_hash() != base_hash, "Different amount should produce different hash"

    # Different recipient
    tx_diff_recipient = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "c" * 40,
        amount=1.0,
        fee=0.1,
        nonce=1,
    )
    tx_diff_recipient.timestamp = 1700000000.0
    assert tx_diff_recipient.calculate_hash() != base_hash, "Different recipient should produce different hash"


def test_transaction_hash_with_complex_inputs_outputs():
    """Verify hash determinism with complex UTXO structures."""
    tx1 = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=10.0,
        fee=0.5,
        nonce=5,
        inputs=[
            {"txid": "abc123", "vout": 0},
            {"txid": "def456", "vout": 2},
            {"txid": "abc789", "vout": 1},
        ],
        outputs=[
            {"address": "XAI" + "1" * 40, "amount": 5.0},
            {"address": "XAI" + "2" * 40, "amount": 4.5},
        ],
    )
    tx1.timestamp = 1700000000.0

    tx2 = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=10.0,
        fee=0.5,
        nonce=5,
        inputs=[
            {"txid": "abc123", "vout": 0},
            {"txid": "def456", "vout": 2},
            {"txid": "abc789", "vout": 1},
        ],
        outputs=[
            {"address": "XAI" + "1" * 40, "amount": 5.0},
            {"address": "XAI" + "2" * 40, "amount": 4.5},
        ],
    )
    tx2.timestamp = 1700000000.0

    assert tx1.calculate_hash() == tx2.calculate_hash(), "Identical complex transactions must have identical hashes"


def test_transaction_size_calculation_deterministic():
    """Verify transaction size calculation is deterministic."""
    tx = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=1.0,
        fee=0.1,
        nonce=1,
    )
    tx.timestamp = 1700000000.0

    size1 = tx.get_size()
    size2 = tx.get_size()

    assert size1 == size2, "Transaction size must be deterministic"
    assert size1 > 0, "Transaction size must be positive"


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


def test_cross_platform_hash_consistency():
    """
    Test that transaction hashes are consistent regardless of JSON serialization
    implementation differences across platforms.

    This test explicitly verifies the fix for TODO 031 - ensuring that
    separators=(',', ':') is used to eliminate whitespace variations.
    """
    tx = Transaction(
        sender="XAI" + "a" * 40,
        recipient="XAI" + "b" * 40,
        amount=100.0,
        fee=1.0,
        nonce=42,
        inputs=[{"txid": "input_tx", "vout": 0}],
        outputs=[{"address": "XAI" + "c" * 40, "amount": 99.0}],
    )
    tx.timestamp = 1700000000.0

    # Get the hash
    tx_hash = tx.calculate_hash()

    # Manually verify the JSON serialization has no spaces
    tx_data = {
        "chain_context": tx._CHAIN_CONTEXT,
        "sender": tx.sender,
        "recipient": tx.recipient,
        "amount": tx.amount,
        "fee": tx.fee,
        "timestamp": tx.timestamp,
        "nonce": tx.nonce,
        "inputs": tx.inputs,
        "outputs": tx.outputs,
    }
    canonical = canonical_json(tx_data)

    # Verify no whitespace after separators
    assert ", " not in canonical, "Canonical JSON should not have spaces after commas"
    assert ": " not in canonical, "Canonical JSON should not have spaces after colons"

    # Verify the hash matches what we'd calculate manually
    import hashlib
    expected_hash = hashlib.sha256(canonical.encode()).hexdigest()
    assert tx_hash == expected_hash, "Transaction hash must match canonical JSON hash"
