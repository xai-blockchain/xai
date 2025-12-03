"""
Integration-style test for the EVMBytecodeExecutor.delegatecall harness.
"""

from xai.core.vm.evm.executor import EVMBytecodeExecutor
from xai.core.vm.executor import ExecutionMessage


def test_delegatecall_writes_to_proxy_storage():
    class Chain:
        def __init__(self):
            self.contracts = {}
            self.chain = []
            self.nonce_tracker = type("NT", (), {"get_nonce": lambda s, a: 0})()

        def get_balance(self, addr):
            return 0

    chain = Chain()
    # Implementation bytecode: store 0x42 at storage slot 0 and return 0
    # PUSH1 0x42 PUSH1 0x00 SSTORE PUSH1 0x00 PUSH1 0x00 RETURN
    impl_code = bytes([0x60, 0x42, 0x60, 0x00, 0x55, 0x60, 0x00, 0x60, 0x00, 0xF3])
    impl_addr = "0x" + "b" * 40
    proxy_addr = "0x" + "c" * 40
    chain.contracts[impl_addr.upper()] = {"code": impl_code.hex(), "storage": {}}
    chain.contracts[proxy_addr.upper()] = {"code": "", "storage": {}}

    ex = EVMBytecodeExecutor(chain)
    res = ex.delegatecall(
        sender="0x" + "a" * 40,
        proxy_address=proxy_addr,
        implementation_address=impl_addr,
        calldata=b"",
        gas_limit=200000,
    )
    assert res.success is True
    # Verify proxy storage slot 0 is now 0x42
    storage = chain.contracts[proxy_addr.upper()]["storage"]
    # EVMStorage stores keys as ints; our persistence writes dict via to_dict with hex keys
    # Accept either int key 0 or hex string "0"
    # Storage key may be serialized as 32-byte hex string; check both formats
    value = (
        storage.get("0")
        or storage.get(0)
        or storage.get("0x" + ("0" * 63) + "0")
        or storage.get("0x" + ("0" * 64))
        or storage.get("0x0000000000000000000000000000000000000000000000000000000000000000")
    )
    assert value == 0x42
