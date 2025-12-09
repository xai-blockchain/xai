from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import pytest

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


class FixtureVerifier(CrossChainVerifier):
    """
    CrossChainVerifier subclass that serves deterministic fixtures instead of
    performing real HTTP requests. Any unexpected call fails the test to ensure
    we never hit external networks in unit tests.
    """

    def __init__(self, fixtures: Dict[Tuple[str, Optional[Tuple[Tuple[str, Any], ...]]], Dict[str, Any]]):
        super().__init__()
        self.fixtures = fixtures

    def _http_get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: float = CrossChainVerifier.DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        key = (url, tuple(sorted(params.items())) if params else None)
        if key not in self.fixtures:
            raise AssertionError(f"Unexpected HTTP request for key {key}")
        return self.fixtures[key]


def test_verify_utxo_transaction_success():
    tx_hash = "a" * 64
    recipient = "bc1qrecipient0000000000000000000000000000"

    fixtures = {
        ("https://blockstream.info/api/tx/" + tx_hash, None): {
            "txid": tx_hash,
            "status": {"block_height": 800000},
            "vout": [
                {"scriptpubkey_address": recipient, "value": 125000000},
                {"scriptpubkey_address": "bc1qother", "value": 1000},
            ],
        },
        ("https://blockstream.info/api/blocks/tip/height", None): "800004",
    }

    verifier = FixtureVerifier(fixtures)
    valid, message, data = verifier.verify_transaction_on_chain(
        "BTC",
        tx_hash,
        expected_amount=Decimal("1.25"),
        recipient=recipient,
        min_confirmations=2,
    )

    assert valid is True
    assert "Transaction verified" in message
    assert data["confirmations"] == 5  # 800004 - 800000 + 1
    assert data["amount_to_recipient"] == pytest.approx(1.25)


def test_verify_utxo_transaction_insufficient_confirmations():
    tx_hash = "b" * 64
    recipient = "bc1qrecipient0000000000000000000000000000"

    fixtures = {
        ("https://blockstream.info/api/tx/" + tx_hash, None): {
            "txid": tx_hash,
            "status": {"block_height": 100},
            "vout": [{"scriptpubkey_address": recipient, "value": 50000000}],
        },
        ("https://blockstream.info/api/blocks/tip/height", None): 100,
    }
    verifier = FixtureVerifier(fixtures)

    valid, message, data = verifier.verify_transaction_on_chain(
        "BTC",
        tx_hash,
        expected_amount=Decimal("0.5"),
        recipient=recipient,
        min_confirmations=3,
    )

    assert valid is False
    assert "Insufficient confirmations" in message
    assert data["confirmations"] == 1


def test_verify_utxo_transaction_recipient_mismatch():
    tx_hash = "c" * 64

    fixtures = {
        ("https://blockstream.info/api/tx/" + tx_hash, None): {
            "txid": tx_hash,
            "status": {"block_height": 50},
            "vout": [{"scriptpubkey_address": "bc1qdifferent", "value": 100000000}],
        },
        ("https://blockstream.info/api/blocks/tip/height", None): 55,
    }
    verifier = FixtureVerifier(fixtures)

    valid, message, data = verifier.verify_transaction_on_chain(
        "BTC",
        tx_hash,
        expected_amount=Decimal("1"),
        recipient="bc1qrecipient0000000000000000000000000000",
        min_confirmations=1,
    )

    assert valid is False
    assert "Amount mismatch" in message
    assert data["amount_to_recipient"] == 0


def test_verify_account_chain_transaction_success():
    tx_hash = "d" * 64
    recipient = "0xabc1230000000000000000000000000000000000"
    block_number_hex = "0x5bad55"
    tip_hex = "0x5bad60"

    fixtures = {
        ("https://api.etherscan.io/api", tuple(sorted({
            "module": "proxy",
            "action": "eth_getTransactionByHash",
            "txhash": tx_hash,
        }.items()))): {
            "result": {
                "hash": tx_hash,
                "to": recipient,
                "value": hex(10**18),  # 1 ETH
                "blockNumber": block_number_hex,
            }
        },
        ("https://api.etherscan.io/api", tuple(sorted({
            "module": "proxy",
            "action": "eth_blockNumber",
        }.items()))): {"result": tip_hex},
    }

    verifier = FixtureVerifier(fixtures)
    valid, message, data = verifier.verify_transaction_on_chain(
        "ETH",
        tx_hash,
        expected_amount=Decimal("1"),
        recipient=recipient,
        min_confirmations=1,
    )

    assert valid is True
    assert "Transaction verified" in message
    assert data["confirmations"] == int(tip_hex, 16) - int(block_number_hex, 16) + 1
    assert data["amount_to_recipient"] == pytest.approx(1.0)


def test_invalid_tx_hash_rejected():
    verifier = FixtureVerifier({})
    valid, message, data = verifier.verify_transaction_on_chain(
        "BTC",
        "1234",
        expected_amount=Decimal("1"),
        recipient="bc1qrecipient0000000000000000000000000000",
        min_confirmations=1,
    )

    assert valid is False
    assert "Invalid transaction hash" in message
    assert data is None


def test_unsupported_coin_rejected():
    verifier = FixtureVerifier({})
    valid, message, data = verifier.verify_transaction_on_chain(
        "XYZ",
        "a" * 64,
        expected_amount=Decimal("1"),
        recipient="addr",
        min_confirmations=1,
    )
    assert valid is False
    assert "Unsupported coin" in message
    assert data is None


def test_cached_result_returned():
    tx_hash = "f" * 64
    recipient = "bc1qrecipient0000000000000000000000000000"
    fixtures = {
        ("https://blockstream.info/api/tx/" + tx_hash, None): {
            "txid": tx_hash,
            "status": {"block_height": 50},
            "vout": [{"scriptpubkey_address": recipient, "value": 100000000}],
        },
        ("https://blockstream.info/api/blocks/tip/height", None): 55,
    }
    verifier = FixtureVerifier(fixtures)
    valid, message, data = verifier.verify_transaction_on_chain(
        "BTC",
        tx_hash,
        expected_amount=Decimal("1"),
        recipient=recipient,
        min_confirmations=1,
    )
    assert valid is True

    # Second call should hit cache even if fixtures removed
    verifier.fixtures.clear()
    valid2, message2, data2 = verifier.verify_transaction_on_chain(
        "BTC",
        tx_hash,
        expected_amount=Decimal("1"),
        recipient=recipient,
        min_confirmations=1,
    )
    assert valid2 is True
    assert data2 == data
