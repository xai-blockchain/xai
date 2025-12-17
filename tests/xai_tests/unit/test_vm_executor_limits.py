import json
import pytest

from xai.core.vm.executor import (
    ExecutionMessage,
    ProductionContractExecutor,
    VMExecutionError,
)


class FakeBlockchain:
    """Minimal blockchain stub to exercise ProductionContractExecutor."""

    def __init__(self) -> None:
        self.contracts: dict[str, dict] = {}

    def derive_contract_address(self, sender: str, nonce: int) -> str:
        return f"{sender.upper()}_{nonce}"

    def register_contract(self, *, address: str, creator: str, code: bytes, gas_limit: int, value: int) -> None:
        self.contracts[address] = {
            "creator": creator,
            "code": code,
            "storage": {},
            "storage_size": 0,
        }


def _deploy_sample_contract(executor: ProductionContractExecutor) -> str:
    deploy_msg = ExecutionMessage(
        sender="0xabc",
        to=None,
        value=0,
        gas_limit=200000,
        data=b'{"op":"noop"}',
        nonce=1,
    )
    result = executor.execute(deploy_msg)
    assert result.success
    return result.return_data.decode()


def test_deploy_and_storage_set_get_paths_enforce_gas_and_storage_limits():
    blockchain = FakeBlockchain()
    executor = ProductionContractExecutor(blockchain)
    contract_address = _deploy_sample_contract(executor)

    set_payload = json.dumps({"op": "set", "key": "alpha", "value": "beta"}).encode()
    set_msg = ExecutionMessage(
        sender="0xabc",
        to=contract_address,
        value=0,
        gas_limit=200000,
        data=set_payload,
        nonce=2,
    )
    set_result = executor.execute(set_msg)
    assert set_result.success
    assert any(log["event"] == "StorageSet" for log in set_result.logs)

    get_msg = ExecutionMessage(
        sender="0xabc",
        to=contract_address,
        value=0,
        gas_limit=50000,
        data=json.dumps({"op": "get", "key": "alpha"}).encode(),
        nonce=3,
    )
    get_result = executor.execute(get_msg)
    assert get_result.success
    assert get_result.return_data == b"beta"

    # Large payload exceeds per-contract storage limit
    huge_value = "x" * (executor.MAX_STORAGE_PER_CONTRACT + 1)
    huge_payload = json.dumps({"op": "set", "key": "fat", "value": huge_value}).encode()
    huge_msg = ExecutionMessage(
        sender="0xabc",
        to=contract_address,
        value=0,
        gas_limit=80_000_000,  # large enough to reach storage limit path
        data=huge_payload,
        nonce=4,
    )
    with pytest.raises(VMExecutionError):
        executor.execute(huge_msg)


def test_reentrancy_lock_rejects_parallel_execution():
    blockchain = FakeBlockchain()
    executor = ProductionContractExecutor(blockchain)
    address = _deploy_sample_contract(executor)

    assert executor._acquire_contract_lock(address) is True
    assert executor._acquire_contract_lock(address) is False
    executor._release_contract_lock(address)
    assert executor._acquire_contract_lock(address) is True
    executor._release_contract_lock(address)


def test_estimate_gas_provides_buffer_for_create_and_call():
    blockchain = FakeBlockchain()
    executor = ProductionContractExecutor(blockchain)
    create_estimate = executor.estimate_gas(
        ExecutionMessage(
            sender="0xabc",
            to=None,
            value=0,
            gas_limit=1000,
            data=b"initcode",
            nonce=1,
        )
    )
    assert create_estimate > executor.GAS_COSTS["BASE"]

    call_estimate = executor.estimate_gas(
        ExecutionMessage(
            sender="0xabc",
            to="0xdead",
            value=0,
            gas_limit=1000,
            data=b"payload",
            nonce=2,
        )
    )
    assert call_estimate > executor.GAS_COSTS["CALL"]
