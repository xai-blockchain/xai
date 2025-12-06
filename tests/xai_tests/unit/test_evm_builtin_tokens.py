"""
Regression tests for ERC20/ERC721 builtin contract integration.
"""

from __future__ import annotations

from dataclasses import dataclass

from xai.core.vm.evm.executor import EVMBytecodeExecutor, ExecutionMessage
from xai.core.vm.evm.abi import encode_call


class DummyNonceTracker:
    def get_nonce(self, _address: str) -> int:
        return 0

    def set_nonce(self, _address: str, _value: int) -> None:
        return None


@dataclass
class DummyBlockchain:
    contracts: dict

    def __post_init__(self) -> None:
        self.chain = []
        self.nonce_tracker = DummyNonceTracker()


ERC20_RECEIVE_HOOK_CODE = bytes.fromhex("6388a7ca5c6000526004601cf3")
ERC721_RECEIVE_HOOK_CODE = bytes.fromhex("63150b7a026000526004601cf3")
BAD_HOOK_CODE = bytes.fromhex("6000f3")


def make_executor_with_contract(contract_record: dict) -> tuple[EVMBytecodeExecutor, str]:
    address = contract_record["address"]
    bc = DummyBlockchain(contracts={address.upper(): contract_record})
    executor = EVMBytecodeExecutor(bc)
    return executor, address


def _register_contract(
    blockchain: DummyBlockchain,
    address: str,
    *,
    code: bytes,
) -> None:
    blockchain.contracts[address.upper()] = {
        "address": address.upper(),
        "code": code.hex(),
        "creator": "0xdeadbeef",
        "storage": {},
    }


def _execute(
    executor: EVMBytecodeExecutor,
    sender: str,
    to: str,
    data: bytes,
    *,
    value: int = 0,
):
    message = ExecutionMessage(
        sender=sender,
        to=to,
        value=value,
        gas_limit=500_000,
        data=data,
        nonce=0,
    )
    return executor.execute(message)


def _send_call(executor: EVMBytecodeExecutor, sender: str, to: str, data: bytes) -> bytes:
    message = ExecutionMessage(
        sender=sender,
        to=to,
        value=0,
        gas_limit=500_000,
        data=data,
        nonce=0,
    )
    result = executor.execute(message)
    assert result.success, result.return_data
    return result.return_data


def test_erc20_builtin_transfer_and_balances() -> None:
    owner = "0x" + "11" * 20
    recipient = "0x" + "22" * 20
    record = {
        "type": "ERC20",
        "address": "0x" + "ab" * 20,
        "metadata": {
            "name": "TestToken",
            "symbol": "TT",
            "decimals": 18,
            "owner": owner,
            "max_supply": 0,
            "initial_supply": 1_000,
            "initial_holder": owner,
        },
        "storage": {},
    }
    executor, address = make_executor_with_contract(record)

    # transfer 100 tokens
    transfer_data = encode_call("transfer(address,uint256)", [recipient, 100])
    _send_call(executor, owner, address, transfer_data)

    # balances reflect transfer
    bal_call_owner = encode_call("balanceOf(address)", [owner])
    bal_bytes = _send_call(executor, owner, address, bal_call_owner)
    owner_balance = int.from_bytes(bal_bytes[-32:], "big")
    assert owner_balance == 900

    bal_call_recipient = encode_call("balanceOf(address)", [recipient])
    rec_bytes = _send_call(executor, owner, address, bal_call_recipient)
    recipient_balance = int.from_bytes(rec_bytes[-32:], "big")
    assert recipient_balance == 100


def test_erc20_builtin_approve_and_transfer_from() -> None:
    owner = "0x" + "33" * 20
    spender = "0x" + "44" * 20
    recipient = "0x" + "55" * 20
    record = {
        "type": "ERC20",
        "address": "0x" + "cd" * 20,
        "metadata": {
            "name": "AllowanceToken",
            "symbol": "ALT",
            "decimals": 18,
            "owner": owner,
            "max_supply": 0,
            "initial_supply": 500,
            "initial_holder": owner,
        },
        "storage": {},
    }
    executor, address = make_executor_with_contract(record)

    approve_call = encode_call("approve(address,uint256)", [spender, 200])
    _send_call(executor, owner, address, approve_call)

    transfer_from_call = encode_call(
        "transferFrom(address,address,uint256)",
        [owner, recipient, 150],
    )
    _send_call(executor, spender, address, transfer_from_call)

    # allowance reduced to 50
    allowance_call = encode_call("allowance(address,address)", [owner, spender])
    allowance_bytes = _send_call(executor, owner, address, allowance_call)
    remaining = int.from_bytes(allowance_bytes[-32:], "big")
    assert remaining == 50


def test_erc721_builtin_mint_and_transfer() -> None:
    owner = "0x" + "66" * 20
    minter = owner
    recipient = "0x" + "77" * 20
    record = {
        "type": "ERC721",
        "address": "0x" + "ef" * 20,
        "metadata": {
            "name": "NFTCollectible",
            "symbol": "NFT",
            "owner": owner,
        },
        "storage": {},
    }
    executor, address = make_executor_with_contract(record)

    # Mint tokenId=1 to recipient
    mint_call = encode_call("mint(address,uint256)", [recipient, 1])
    _send_call(executor, minter, address, mint_call)

    owner_of_call = encode_call("ownerOf(uint256)", [1])
    owner_bytes = _send_call(executor, recipient, address, owner_of_call)
    resolved_owner = "0x" + owner_bytes[-20:].hex()
    assert resolved_owner.lower() == recipient.lower()

    # transfer to new owner
    new_owner = "0x" + "88" * 20
    transfer_call = encode_call(
        "transferFrom(address,address,uint256)", [recipient, new_owner, 1]
    )
    _send_call(executor, recipient, address, transfer_call)

    owner_bytes = _send_call(executor, new_owner, address, owner_of_call)
    resolved_owner = "0x" + owner_bytes[-20:].hex()
    assert resolved_owner.lower() == new_owner.lower()


def test_erc20_transfer_triggers_receive_hook() -> None:
    owner = "0x" + "21" * 20
    recipient_contract = "0x" + "31" * 20
    record = {
        "type": "ERC20",
        "address": "0x" + "aa" * 20,
        "metadata": {
            "name": "HookToken",
            "symbol": "HOOK",
            "decimals": 18,
            "owner": owner,
            "max_supply": 0,
            "initial_supply": 1_000,
            "initial_holder": owner,
        },
        "storage": {},
    }
    executor, token_address = make_executor_with_contract(record)
    _register_contract(executor.blockchain, recipient_contract, code=ERC20_RECEIVE_HOOK_CODE)

    transfer_data = encode_call("transfer(address,uint256)", [recipient_contract, 50])
    result = _execute(executor, owner, token_address, transfer_data)
    assert result.success

    owner_balance = int.from_bytes(
        _send_call(executor, owner, token_address, encode_call("balanceOf(address)", [owner]))[-32:],
        "big",
    )
    recipient_balance = int.from_bytes(
        _send_call(executor, owner, token_address, encode_call("balanceOf(address)", [recipient_contract]))[-32:],
        "big",
    )
    assert owner_balance == 950
    assert recipient_balance == 50


def test_erc20_receive_hook_failure_reverts_transfer() -> None:
    owner = "0x" + "41" * 20
    failing_contract = "0x" + "51" * 20
    record = {
        "type": "ERC20",
        "address": "0x" + "bb" * 20,
        "metadata": {
            "name": "FailToken",
            "symbol": "FAIL",
            "decimals": 18,
            "owner": owner,
            "max_supply": 0,
            "initial_supply": 1_000,
            "initial_holder": owner,
        },
        "storage": {},
    }
    executor, token_address = make_executor_with_contract(record)
    _register_contract(executor.blockchain, failing_contract, code=BAD_HOOK_CODE)

    transfer_data = encode_call("transfer(address,uint256)", [failing_contract, 25])
    result = _execute(executor, owner, token_address, transfer_data)
    assert not result.success

    owner_balance = int.from_bytes(
        _send_call(executor, owner, token_address, encode_call("balanceOf(address)", [owner]))[-32:],
        "big",
    )
    failing_balance = int.from_bytes(
        _send_call(
            executor,
            owner,
            token_address,
            encode_call("balanceOf(address)", [failing_contract]),
        )[-32:],
        "big",
    )
    assert owner_balance == 1_000
    assert failing_balance == 0


def test_erc721_safe_transfer_invokes_receive_hook() -> None:
    owner = "0x" + "61" * 20
    receiver = "0x" + "71" * 20
    record = {
        "type": "ERC721",
        "address": "0x" + "cc" * 20,
        "metadata": {
            "name": "SafeNFT",
            "symbol": "SNFT",
            "owner": owner,
        },
        "storage": {},
    }
    executor, token_address = make_executor_with_contract(record)
    _register_contract(executor.blockchain, receiver, code=ERC721_RECEIVE_HOOK_CODE)

    mint_call = encode_call("mint(address,uint256)", [owner, 1])
    _send_call(executor, owner, token_address, mint_call)

    safe_transfer = encode_call("safeTransferFrom(address,address,uint256)", [owner, receiver, 1])
    result = _execute(executor, owner, token_address, safe_transfer)
    assert result.success

    owner_bytes = _send_call(executor, owner, token_address, encode_call("ownerOf(uint256)", [1]))
    assert ("0x" + owner_bytes[-20:].hex()).lower() == receiver.lower()


def test_erc721_safe_transfer_reverts_without_receive_hook() -> None:
    owner = "0x" + "81" * 20
    receiver = "0x" + "91" * 20
    record = {
        "type": "ERC721",
        "address": "0x" + "dd" * 20,
        "metadata": {
            "name": "UnsafeNFT",
            "symbol": "UNFT",
            "owner": owner,
        },
        "storage": {},
    }
    executor, token_address = make_executor_with_contract(record)
    _register_contract(executor.blockchain, receiver, code=BAD_HOOK_CODE)

    mint_call = encode_call("mint(address,uint256)", [owner, 7])
    _send_call(executor, owner, token_address, mint_call)

    safe_transfer = encode_call("safeTransferFrom(address,address,uint256)", [owner, receiver, 7])
    result = _execute(executor, owner, token_address, safe_transfer)
    assert not result.success

    owner_bytes = _send_call(executor, owner, token_address, encode_call("ownerOf(uint256)", [7]))
    assert ("0x" + owner_bytes[-20:].hex()).lower() == owner.lower()
