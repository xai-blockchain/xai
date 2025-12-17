import time
from types import SimpleNamespace

import pytest

from xai.core.transaction import Transaction
from xai.core.vm.manager import SmartContractManager, ExecutionResult
from xai.core.vm.exceptions import VMExecutionError


class DummyMetric:
    def __init__(self):
        self.value = 0
        self.observations = []

    def inc(self, amount: float = 1.0):
        self.value += amount

    def set(self, value: float):
        self.value = value

    def observe(self, value: float, labels=None):
        self.observations.append(value)


class DummyCollector:
    def __init__(self, metrics):
        self._metrics = metrics

    def get_metric(self, name):
        return self._metrics.get(name)


class DummyBlockchain:
    def __init__(self):
        self.contracts = {}
        self.contract_receipts = []
        self.logger = None
        self.nonce_tracker = SimpleNamespace(get_next_nonce=lambda sender: 1)

    def derive_contract_address(self, sender, nonce):
        return "XAI" + "C" * 20

    def store_contract_abi(self, *args, **kwargs):
        return None


class DummyProcessor:
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    def process(self, tx, block):
        current = self._responses[self._index]
        self._index += 1
        if isinstance(current, Exception):
            raise current
        return current


@pytest.fixture()
def contract_metrics_stub(monkeypatch):
    from xai.core import vm as vm_pkg
    metrics = {
        name: DummyMetric()
        for name in [
            "xai_contract_calls_total",
            "xai_contract_deployments_total",
            "xai_contract_success_total",
            "xai_contract_failures_total",
            "xai_contract_gas_used_total",
            "xai_contract_execution_duration_seconds",
        ]
    }
    wrapper = type("Wrapper", (), {})()
    wrapper._instance = DummyCollector(metrics)
    monkeypatch.setattr(vm_pkg.manager, "MetricsCollector", wrapper, raising=False)
    monkeypatch.setattr(
        vm_pkg.manager,
        "logger",
        SimpleNamespace(warning=lambda *args, **kwargs: None, debug=lambda *a, **k: None),
        raising=False,
    )
    return metrics


def _build_transaction(tx_type: str) -> Transaction:
    tx = Transaction(
        sender="XAI" + "A" * 40,
        recipient="XAI" + "B" * 40,
        amount=0,
        fee=0,
        tx_type="normal",
    )
    tx.tx_type = tx_type
    tx.nonce = 1
    tx.txid = tx.calculate_hash()
    tx.metadata = {}
    return tx


def _build_block():
    header = SimpleNamespace(index=1, hash="A" * 64, timestamp=time.time())
    return SimpleNamespace(index=1, hash="A" * 64, timestamp=time.time(), header=header)


def test_contract_metrics_record_success_and_failure(contract_metrics_stub, monkeypatch):
    blockchain = DummyBlockchain()
    manager = SmartContractManager(blockchain)
    manager.processor = DummyProcessor(
        [
            ExecutionResult(success=True, gas_used=21000, return_data=b"", logs=[]),
            VMExecutionError("boom"),
        ]
    )

    tx_call = _build_transaction("contract_call")
    manager.process_transaction(tx_call, _build_block())

    tx_deploy = _build_transaction("contract_deploy")
    tx_deploy.metadata = {"abi": {"name": "Test"}}
    manager.process_transaction(tx_deploy, _build_block())

    assert contract_metrics_stub["xai_contract_calls_total"].value == 1
    assert contract_metrics_stub["xai_contract_deployments_total"].value == 1
    assert contract_metrics_stub["xai_contract_success_total"].value == 1
    assert contract_metrics_stub["xai_contract_failures_total"].value == 1
    assert contract_metrics_stub["xai_contract_gas_used_total"].value >= 21000
    assert contract_metrics_stub["xai_contract_execution_duration_seconds"].observations
