import json

from xai.core.blockchain import Blockchain
from xai.core.vm.executor import ExecutionMessage, SimpleContractExecutor


def test_simple_contract_deploy_and_storage():
    blockchain = Blockchain()
    executor = SimpleContractExecutor(blockchain)

    sender = "XAI1234567890ABCDEF1234567890ABCDEF123456"
    deploy_result = executor.execute(
        ExecutionMessage(sender=sender, to=None, value=0, gas_limit=100_000, data=b"{}", nonce=1)
    )

    assert deploy_result.success
    contract_address = deploy_result.return_data.decode("utf-8")
    assert contract_address in blockchain.contracts

    set_payload = json.dumps({"op": "set", "key": "counter", "value": 42}).encode("utf-8")
    call_result = executor.execute(
        ExecutionMessage(
            sender=sender,
            to=contract_address,
            value=0,
            gas_limit=80_000,
            data=set_payload,
            nonce=2,
        )
    )

    assert call_result.success
    assert blockchain.contracts[contract_address]["storage"]["counter"] == 42

    get_payload = json.dumps({"op": "get", "key": "counter"}).encode("utf-8")
    static_result = executor.call_static(
        ExecutionMessage(
            sender=sender,
            to=contract_address,
            value=0,
            gas_limit=80_000,
            data=get_payload,
            nonce=3,
        )
    )

    assert static_result.success
    assert static_result.return_data == b"42"
