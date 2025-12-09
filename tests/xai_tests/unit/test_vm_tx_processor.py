"""
Unit tests for ContractTransactionProcessor.

Coverage targets:
- Message building for deploy vs call transactions
- Static vs stateful execution routing
- Data handling for hex string metadata
"""

from types import SimpleNamespace

import pytest

from xai.core.vm.tx_processor import ContractTransactionProcessor
from xai.core.vm.executor import ProductionContractExecutor


class _DummyBlockchain:
    """Minimal blockchain harness used for end-to-end executor calls."""

    def __init__(self):
        self.contracts = {}
        self.nonce_tracker = SimpleNamespace(get_nonce=lambda _self=None, _addr=None: 0, set_nonce=lambda *_: None)

    def derive_contract_address(self, sender, nonce):
        return f"{sender}-{nonce}"

    def register_contract(self, address, creator, code, gas_limit, value):
        self.contracts[address.upper()] = {
            "creator": creator,
            "code": code,
            "gas_limit": gas_limit,
            "value": value,
            "storage": {},
            "storage_size": 0,
        }

    def get_balance(self, address):
        return 0


class _DummyExecutor:
    def __init__(self):
        self.last_message = None
        self.executed = 0
        self.static_called = 0

    def execute(self, message):
        self.executed += 1
        self.last_message = message
        return "executed"

    def call_static(self, message):
        self.static_called += 1
        self.last_message = message
        return "static"


def _tx(tx_type="contract_call", metadata=None, recipient="0xR", amount=5, nonce=2):
    meta = metadata or {}
    return SimpleNamespace(
        sender="0xS",
        recipient=recipient,
        amount=amount,
        metadata=meta,
        nonce=nonce,
        tx_type=tx_type,
    )


def test_process_routes_to_executor_static_and_stateful():
    """Static flag uses call_static; default uses execute."""
    execu = _DummyExecutor()
    processor = ContractTransactionProcessor(blockchain=SimpleNamespace(), executor=execu)
    tx = _tx()
    block = SimpleNamespace()

    result_exec = processor.process(tx, block, static=False)
    assert result_exec == "executed"
    assert execu.executed == 1

    result_static = processor.process(tx, block, static=True)
    assert result_static == "static"
    assert execu.static_called == 1


def test_build_message_for_deploy_and_data_hex():
    """Deploy tx nulls 'to'; metadata hex string decoded into bytes."""
    execu = _DummyExecutor()
    processor = ContractTransactionProcessor(blockchain=SimpleNamespace(), executor=execu)

    deploy_tx = _tx(tx_type="contract_deploy", metadata={"data": "ff", "gas_limit": 12345})
    block = SimpleNamespace()
    processor.process(deploy_tx, block)
    msg = execu.last_message
    assert msg.to is None
    assert msg.data == b"\xff"
    assert msg.gas_limit == 12345
    assert msg.nonce == 2


def test_build_message_defaults_and_bytes_metadata():
    """Non-dict metadata falls back to default gas and empty data; bytes metadata passed through."""
    execu = _DummyExecutor()
    processor = ContractTransactionProcessor(blockchain=SimpleNamespace(), executor=execu)

    tx = _tx(metadata=None, nonce=None)
    block = SimpleNamespace()
    processor.process(tx, block)
    msg = execu.last_message
    assert msg.gas_limit == processor.config.default_gas_limit
    assert msg.data == b""
    assert msg.nonce == 0

    data_bytes = b"\x01\x02"
    tx_bytes = _tx(metadata={"data": data_bytes}, nonce=3)
    processor.process(tx_bytes, block)
    msg2 = execu.last_message
    assert msg2.data == data_bytes
    assert msg2.nonce == 3


def test_end_to_end_deploy_and_call_with_production_executor():
    """Processor wires deploy + call through ProductionContractExecutor with storage mutation."""
    chain = _DummyBlockchain()
    executor = ProductionContractExecutor(chain)
    processor = ContractTransactionProcessor(blockchain=chain, executor=executor)
    block = SimpleNamespace()

    deploy_tx = _tx(tx_type="contract_deploy", metadata={"data": b"\xAA", "gas_limit": 80_000}, nonce=1)
    deploy_result = processor.process(deploy_tx, block)
    deployed_addr = deploy_result.return_data.decode("utf-8")
    assert deployed_addr.upper() in chain.contracts

    call_payload = b'{"op":"set","key":"k","value":7}'
    call_tx = _tx(
        tx_type="contract_call",
        recipient=deployed_addr,
        metadata={"data": call_payload, "gas_limit": 60_000},
        nonce=2,
        amount=0,
    )
    call_result = processor.process(call_tx, block)
    assert call_result.success is True
    assert chain.contracts[deployed_addr.upper()]["storage"]["k"] == 7


def test_static_processing_respects_gas_limit_metadata():
    """Static processing uses metadata gas_limit when provided."""
    execu = _DummyExecutor()
    processor = ContractTransactionProcessor(blockchain=SimpleNamespace(), executor=execu)
    tx = _tx(metadata={"data": "00", "gas_limit": 1234})
    block = SimpleNamespace()

    processor.process(tx, block, static=True)

    assert execu.static_called == 1
    assert execu.last_message.gas_limit == 1234
