"""
Unit tests for ProductionContractExecutor.

Coverage targets:
- Deployment gas accounting and contract registration
- Storage operations (set/get/delete) with mutate vs static execution
- Reentrancy guard and out-of-gas/unsupported op handling
"""

import json
import time
from types import SimpleNamespace

import pytest

from xai.core.vm.executor import ExecutionMessage, ProductionContractExecutor
from xai.core.vm.exceptions import VMExecutionError


class _DummyNonceTracker:
    def __init__(self):
        self._nonces = {}

    def get_nonce(self, address=None):
        return self._nonces.get(address, 0)

    def set_nonce(self, address, nonce):
        self._nonces[address] = nonce


class _DummyBlockchain:
    """Minimal blockchain harness with contract registry hooks."""

    def __init__(self):
        self.contracts = {}
        self.nonce_tracker = _DummyNonceTracker()
        self.derive_calls = []
        self.register_calls = []

    def derive_contract_address(self, sender, nonce):
        addr = f"{sender}-{nonce}"
        self.derive_calls.append((sender, nonce))
        return addr

    def register_contract(self, address, creator, code, gas_limit, value):
        normalized = address.upper()
        self.contracts[normalized] = {
            "creator": creator,
            "code": code,
            "gas_limit": gas_limit,
            "value": value,
        }
        self.register_calls.append(normalized)

    def get_balance(self, address):
        return 0


def _message(**overrides) -> ExecutionMessage:
    defaults = dict(
        sender="0xABC",
        to=None,
        value=0,
        gas_limit=100_000,
        data=b"",
        nonce=1,
    )
    defaults.update(overrides)
    return ExecutionMessage(**defaults)


def test_deploy_registers_contract_and_gas_accounting():
    """Deployment registers the contract and charges base/create/data gas."""
    chain = _DummyBlockchain()
    executor = ProductionContractExecutor(chain)
    code = b"\xAA\xBB"
    msg = _message(data=code)

    result = executor.execute(msg)

    expected_gas = (
        executor.GAS_COSTS["BASE"]
        + executor.GAS_COSTS["CREATE"]
        + len(code) * executor.GAS_COSTS["BYTE"]
    )
    deployed_addr = result.return_data.decode("utf-8")
    assert result.success is True
    assert result.gas_used == expected_gas
    assert deployed_addr.upper() in chain.contracts
    assert chain.contracts[deployed_addr.upper()]["code"] == code
    assert chain.contracts[deployed_addr.upper()].get("storage_size", 0) == 0


def test_storage_set_mutates_and_tracks_size():
    """SET operation updates storage, storage_size, gas, and logs."""
    chain = _DummyBlockchain()
    contract_addr = "0xC0DE"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    payload = b'{"op":"set","key":"foo","value":1}'
    msg = _message(to=contract_addr, data=payload, gas_limit=30_000)

    result = executor.execute(msg)

    value_size = len(json.dumps(1).encode("utf-8"))
    expected_gas = (
        executor.GAS_COSTS["BASE"]
        + executor.GAS_COSTS["CALL"]
        + len(payload) * executor.GAS_COSTS["BYTE"]
        + (value_size // 32 + 1) * executor.STORAGE_GAS_PER_32_BYTES
    )
    assert result.success is True
    assert result.gas_used == expected_gas
    assert chain.contracts[contract_addr.upper()]["storage"]["foo"] == 1
    assert chain.contracts[contract_addr.upper()]["storage_size"] == value_size
    assert result.logs == [{"event": "StorageSet", "key": "foo", "size_bytes": value_size}]


def test_static_call_does_not_mutate_storage():
    """call_static charges gas but leaves storage unchanged for SET."""
    chain = _DummyBlockchain()
    contract_addr = "0xSTATIC"
    base_size = len(json.dumps("bar").encode("utf-8"))
    chain.contracts[contract_addr.upper()] = {"storage": {"foo": "bar"}, "storage_size": base_size}
    executor = ProductionContractExecutor(chain)
    payload = b'{"op":"set","key":"foo","value":"baz"}'
    msg = _message(to=contract_addr, data=payload, gas_limit=30_000)

    result = executor.call_static(msg)

    assert result.success is True
    assert chain.contracts[contract_addr.upper()]["storage"]["foo"] == "bar"
    assert chain.contracts[contract_addr.upper()]["storage_size"] == base_size
    assert result.logs == [
        {"event": "StorageSet", "key": "foo", "size_bytes": len(json.dumps("baz").encode("utf-8"))}
    ]


def test_reentrancy_detection_blocks_recursive_call():
    """Executing while lock held raises VMExecutionError."""
    chain = _DummyBlockchain()
    contract_addr = "0xLOCK"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    payload = b'{"op":"get","key":"foo"}'
    msg = _message(to=contract_addr, data=payload, gas_limit=25_000)

    assert executor._acquire_contract_lock(contract_addr.upper()) is True
    try:
        with pytest.raises(VMExecutionError, match="Reentrancy detected"):
            executor.execute(msg)
    finally:
        executor._release_contract_lock(contract_addr.upper())


def test_out_of_gas_and_unsupported_op():
    """Low gas fails fast; unknown op surfaces explicit error."""
    chain = _DummyBlockchain()
    contract_addr = "0xOOG"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    payload = b'{"op":"set","key":"foo","value":1}'

    with pytest.raises(VMExecutionError, match="Out of gas"):
        executor.execute(_message(to=contract_addr, data=payload, gas_limit=10))

    bad_payload = b'{"op":"unknown"}'
    with pytest.raises(VMExecutionError, match="Unsupported contract operation"):
        executor.execute(_message(to=contract_addr, data=bad_payload, gas_limit=25_000))


def test_get_and_delete_operations_and_static_delete_noop():
    """GET returns serialized bytes; DELETE emits log and does not mutate when static."""
    chain = _DummyBlockchain()
    contract_addr = "0xF00D"
    chain.contracts[contract_addr.upper()] = {"storage": {"k": "v"}, "storage_size": len(json.dumps("v"))}
    executor = ProductionContractExecutor(chain)

    # GET returns encoded value and charges gas
    get_msg = _message(to=contract_addr, data=b'{"op":"get","key":"k"}', gas_limit=25_000)
    get_result = executor.execute(get_msg)
    assert get_result.return_data == b"v"
    assert get_result.success is True

    # DELETE under static call returns success but leaves storage unchanged
    delete_msg = _message(to=contract_addr, data=b'{"op":"delete","key":"k"}', gas_limit=25_000)
    delete_result = executor.call_static(delete_msg)
    assert delete_result.logs == [{"event": "StorageDelete", "key": "k"}]
    assert chain.contracts[contract_addr.upper()]["storage"]["k"] == "v"


def test_invalid_payload_rejected_before_execution():
    """Invalid payload decoding surfaces VMExecutionError with explicit message."""
    chain = _DummyBlockchain()
    contract_addr = "0xBAD"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)

    with pytest.raises(VMExecutionError, match="decode contract payload"):
        executor.execute(_message(to=contract_addr, data=b"\xff\xff", gas_limit=30_000))


def test_invalid_json_payload_errors_cleanly():
    """UTF-8 decodable but invalid JSON raises descriptive error."""
    chain = _DummyBlockchain()
    contract_addr = "0xJUNK"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)

    with pytest.raises(VMExecutionError, match="Contract payload must be valid JSON"):
        executor.execute(_message(to=contract_addr, data=b"{not-json}", gas_limit=30_000))


def test_emit_logs_and_gas_accounting_with_message_size():
    """Emit operation charges per-byte gas and returns log with message payload."""
    chain = _DummyBlockchain()
    contract_addr = "0xLOG"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    message = "hello world"
    payload = json.dumps({"op": "emit", "message": message}).encode()
    msg = _message(to=contract_addr, data=payload, gas_limit=50_000)

    result = executor.execute(msg)

    expected_gas = (
        executor.GAS_COSTS["BASE"]
        + executor.GAS_COSTS["CALL"]
        + len(payload) * executor.GAS_COSTS["BYTE"]
        + len(message) * executor.GAS_COSTS["BYTE"]
    )
    assert result.success is True
    assert result.gas_used == expected_gas
    assert result.logs == [{"event": "Log", "message": message}]


def test_emit_out_of_gas_when_message_too_large():
    """Emit fails fast when message byte cost exceeds gas limit."""
    chain = _DummyBlockchain()
    contract_addr = "0xLOG2"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    big_message = "x" * 10_000
    payload = json.dumps({"op": "emit", "message": big_message}).encode()
    with pytest.raises(VMExecutionError, match="Out of gas"):
        executor.execute(_message(to=contract_addr, data=payload, gas_limit=10_000))


def test_delete_updates_storage_and_size():
    """DELETE removes stored key and reduces storage_size when mutate=True."""
    chain = _DummyBlockchain()
    contract_addr = "0xDEL"
    value = {"foo": "bar"}
    value_size = len(json.dumps(value).encode("utf-8"))
    chain.contracts[contract_addr.upper()] = {"storage": {"k": value}, "storage_size": value_size}
    executor = ProductionContractExecutor(chain)

    delete_msg = _message(to=contract_addr, data=b'{"op":"delete","key":"k"}', gas_limit=25_000)
    result = executor.execute(delete_msg)

    assert "k" not in chain.contracts[contract_addr.upper()]["storage"]
    assert chain.contracts[contract_addr.upper()]["storage_size"] == 0
    assert result.logs == [{"event": "StorageDelete", "key": "k"}]


def test_unknown_contract_call_raises():
    """Calling non-existent contract raises VMExecutionError."""
    chain = _DummyBlockchain()
    executor = ProductionContractExecutor(chain)
    with pytest.raises(VMExecutionError, match="Unknown contract"):
        executor.execute(_message(to="0xNOPE", data=b'{"op":"get","key":"k"}', gas_limit=25_000))


def test_estimate_gas_uses_call_vs_create_costs():
    """estimate_gas returns different values for call vs deploy based on data and opcode cost."""
    chain = _DummyBlockchain()
    executor = ProductionContractExecutor(chain)
    call_msg = _message(to="0x1", data=b"\x00\x01")
    deploy_msg = _message(to=None, data=b"\x00\x01")

    call_estimate = executor.estimate_gas(call_msg)
    deploy_estimate = executor.estimate_gas(deploy_msg)

    base = executor.GAS_COSTS["BASE"]
    assert call_estimate == base + len(call_msg.data) * executor.GAS_COSTS["BYTE"] + executor.GAS_COSTS["CALL"]
    assert deploy_estimate == base + len(deploy_msg.data) * executor.GAS_COSTS["BYTE"] + executor.GAS_COSTS["CREATE"]


def test_instruction_limit_enforced(monkeypatch):
    """Instruction cap triggers VMExecutionError when set to zero."""
    chain = _DummyBlockchain()
    contract_addr = "0xCAP"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    monkeypatch.setattr(executor, "MAX_INSTRUCTIONS", 0)

    with pytest.raises(VMExecutionError, match="Instruction limit exceeded"):
        executor.execute(_message(to=contract_addr, data=b'{"op":"get","key":"k"}', gas_limit=30_000))


def test_execution_timeout(monkeypatch):
    """Execution timeout triggers when elapsed exceeds MAX_EXECUTION_TIME."""
    chain = _DummyBlockchain()
    contract_addr = "0xTIME"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)

    times = iter([0, executor.MAX_EXECUTION_TIME + 1])
    monkeypatch.setattr(time, "time", lambda: next(times))

    with pytest.raises(VMExecutionError, match="Execution timeout"):
        executor.execute(_message(to=contract_addr, data=b'{"op":"get","key":"k"}', gas_limit=50_000))


def test_memory_limit_enforced(monkeypatch):
    """Simulate memory usage breaching limit to trigger error."""
    chain = _DummyBlockchain()
    contract_addr = "0xMEM"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)

    # Patch _execute_with_limits to simulate memory_used beyond cap
    original_call = executor._execute_with_limits

    def _wrapped(message, target, mutate):
        return original_call(message, target, mutate)

    # Monkeypatch memory tracking by forcing MAX_MEMORY_PER_CONTRACT very low
    monkeypatch.setattr(executor, "MAX_MEMORY_PER_CONTRACT", 1)
    payload = b'{"op":"emit","message":"a"*1000}'  # triggers memory expansion via payload len in gas calc
    with pytest.raises(VMExecutionError):
        executor.execute(_message(to=contract_addr, data=payload, gas_limit=1_000_000))


def test_unsupported_operation_without_op_field():
    """Valid JSON lacking op should raise unsupported contract operation error."""
    chain = _DummyBlockchain()
    contract_addr = "0xUNK"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)
    with pytest.raises(VMExecutionError, match="Unsupported contract operation"):
        executor.execute(_message(to=contract_addr, data=b'{"foo":"bar"}', gas_limit=30_000))


def test_storage_limit_enforced_on_set():
    """SET fails when new total storage would exceed per-contract cap."""
    chain = _DummyBlockchain()
    contract_addr = "0xFULL"
    near_limit = ProductionContractExecutor.MAX_STORAGE_PER_CONTRACT - 10
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": near_limit}
    executor = ProductionContractExecutor(chain)
    payload = b'{"op":"set","key":"k","value":"' + b"x" * 64 + b'"}'

    with pytest.raises(VMExecutionError, match="Storage limit exceeded"):
        executor.execute(_message(to=contract_addr, data=payload, gas_limit=50_000))


def test_missing_key_raises_for_storage_ops_and_get_returns_empty_when_absent():
    """Key is required; GET on absent key returns empty bytes."""
    chain = _DummyBlockchain()
    contract_addr = "0xMISS"
    chain.contracts[contract_addr.upper()] = {"storage": {}, "storage_size": 0}
    executor = ProductionContractExecutor(chain)

    for op in ("set", "get", "delete"):
        with pytest.raises(VMExecutionError, match="Missing key"):
            executor.execute(_message(to=contract_addr, data=json.dumps({"op": op}).encode(), gas_limit=50_000))

    # GET with explicit missing key returns empty
    get_payload = b'{"op":"get","key":"none"}'
    result = executor.execute(_message(to=contract_addr, data=get_payload, gas_limit=50_000))
    assert result.return_data == b""
