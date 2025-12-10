import time

from scripts.tools import refund_sweep_runner
from xai.core.refund_sweep_manager import RefundSweepManager


def test_refund_sweep_runs_with_mocked_btc_rpc(monkeypatch):
    calls = {"send": 0}

    def fake_btc_rpc(method, params=None):
        if method == "createrawtransaction":
            return "raw-tx"
        if method == "signrawtransactionwithwallet":
            return {"hex": "signed-hex"}
        if method == "sendrawtransaction":
            calls["send"] += 1
            return "txid123"
        if method == "getblockcount":
            return 200
        return None

    monkeypatch.setattr(refund_sweep_runner, "btc_rpc", fake_btc_rpc)
    swaps = [
        {
            "id": "s1",
            "funding_txid": "ok",
            "coin": "BTC",
            "timelock": time.time() - 4000,
            "sender_address": "sender",
            "utxo": {"txid": "prev", "vout": 0, "amount": 0.5},
        }
    ]
    verifier = refund_sweep_runner.CrossChainVerifier()
    monkeypatch.setattr(
        verifier,
        "verify_minimum_confirmations",
        lambda coin, txid, min_confirmations=3: (True, 6),
    )
    filtered = refund_sweep_runner.filter_refundable_swaps(swaps, verifier, safety_margin_seconds=0, min_confirmations=1)
    refund_sweep_runner.sweep_utxo(filtered, RefundSweepManager(safety_margin_seconds=0))
    assert calls["send"] == 1


def test_refund_sweep_runs_with_mocked_eth(monkeypatch):
    calls = {"send": 0}

    class DummyContractFn:
        def build_transaction(self, params):
            return {"from": params["from"], "nonce": 0}

    class DummyContract:
        def __init__(self):
            self.functions = type("fn", (), {"refund": lambda self=None: DummyContractFn()})()

    class DummyEth:
        def __init__(self, calls):
            self.accounts = ["0xabc"]
            self._calls = calls

        def get_transaction_count(self, sender):
            return 0

        def estimate_gas(self, tx):
            return 21000

        def send_transaction(self, tx):
            self._calls["send"] += 1
            return "0xhash"

        def wait_for_transaction_receipt(self, tx_hash, timeout=120):
            return type("rcpt", (), {"tx_hash": type("h", (), {"hex": lambda self=None: "0xhash"})()})()

    class DummyWeb3:
        def __init__(self, *_):
            self.eth = DummyEth(calls)

        class HTTPProvider:
            def __init__(self, url):
                self.url = url

    monkeypatch.setattr(refund_sweep_runner, "Web3", DummyWeb3)

    swaps = [
        {
            "id": "eth1",
            "funding_txid": "ok",
            "coin": "ETH",
            "timelock": time.time() - 4000,
            "sender": "0xabc",
            "contract": DummyContract(),
        }
    ]
    verifier = refund_sweep_runner.CrossChainVerifier()
    monkeypatch.setattr(
        verifier,
        "verify_minimum_confirmations",
        lambda coin, txid, min_confirmations=3: (True, 12),
    )
    filtered = refund_sweep_runner.filter_refundable_swaps(swaps, verifier, safety_margin_seconds=0, min_confirmations=1)
    refund_sweep_runner.sweep_eth(filtered, RefundSweepManager(safety_margin_seconds=0))
    assert calls["send"] == 1
