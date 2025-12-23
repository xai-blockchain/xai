"""
Builtin ERC20/ERC721 contract execution integrated with the EVM interpreter.

These adapters allow the Python-native token libraries to be invoked through
standard ABI calls while persisting all mutable state inside `EVMStorage`.
This bridges the existing token factories with the bytecode executor so the
rest of the node can treat ERC deployments like first-class EVM contracts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Sequence

from ..exceptions import VMExecutionError
from .abi import (
    decode_address,
    decode_bool,
    decode_bytes,
    decode_string,
    decode_uint256,
    encode_args,
    encode_bool,
    encode_uint256,
    function_selector,
    keccak256,
)
from .storage import EVMStorage

ZERO_ADDRESS = "0x" + "0" * 40

def _normalize_address(address: str) -> str:
    """Return a checks-safe lowercase hex address."""
    if not address:
        return ZERO_ADDRESS
    if address.startswith("0x"):
        return address.lower()
    return f"0x{address.lower()}"

def _encode_address_topic(address: str) -> str:
    raw = bytes.fromhex(_normalize_address(address)[2:])
    return "0x" + raw.rjust(32, b"\x00").hex()

def _encode_uint_topic(value: int) -> str:
    return "0x" + encode_uint256(value).hex()

class StorageLayout:
    """Utility helpers for mapping keys into EVM storage slots."""

    STRING_MAX_BYTES = 96
    STRING_CHUNKS = STRING_MAX_BYTES // 32

    def __init__(self, storage: EVMStorage) -> None:
        self.storage = storage

    def _slot(self, base_slot: int, *keys: int) -> int:
        slot = base_slot
        for key in keys:
            payload = key.to_bytes(32, "big") + slot.to_bytes(32, "big")
            slot = int.from_bytes(keccak256(payload), "big")
        return slot

    def write_string(self, base_slot: int, value: str) -> None:
        data = value.encode("utf-8")
        if len(data) > self.STRING_MAX_BYTES:
            raise VMExecutionError("String exceeds storage allocation")
        self.storage.set_raw(base_slot, len(data))
        chunks = (len(data) + 31) // 32
        for i in range(self.STRING_CHUNKS):
            if i < chunks:
                piece = data[i * 32 : (i + 1) * 32]
                self.storage.set_raw(
                    base_slot + 1 + i, int.from_bytes(piece.ljust(32, b"\x00"), "big")
                )
            else:
                self.storage.set_raw(base_slot + 1 + i, 0)

    def read_string(self, base_slot: int) -> str:
        length = self.storage.get_raw(base_slot)
        if length == 0:
            return ""
        chunks = (length + 31) // 32
        data = bytearray()
        for i in range(min(chunks, self.STRING_CHUNKS)):
            word = self.storage.get_raw(base_slot + 1 + i)
            data.extend(word.to_bytes(32, "big"))
        return bytes(data[:length]).decode("utf-8", errors="replace")

    def write_address(self, slot: int, address: str) -> None:
        raw = int(_normalize_address(address)[2:], 16)
        self.storage.set_raw(slot, raw)

    def read_address(self, slot: int) -> str:
        value = self.storage.get_raw(slot)
        return "0x" + value.to_bytes(32, "big")[-20:].hex()

    def mapping_slot(self, base_slot: int, key: str | int) -> int:
        if isinstance(key, str):
            key_int = int(_normalize_address(key)[2:], 16)
        else:
            key_int = key
        return self._slot(base_slot, key_int)

    def double_mapping_slot(
        self, base_slot: int, key1: str | int, key2: str | int
    ) -> int:
        first = self.mapping_slot(base_slot, key1)
        return self.mapping_slot(first, key2)

class ERC20StorageAdapter(StorageLayout):
    """Storage-backed view of ERC20 contract state."""

    VERSION_SLOT = 0
    NAME_SLOT = 1
    SYMBOL_SLOT = 10
    DECIMALS_SLOT = 20
    TOTAL_SUPPLY_SLOT = 21
    OWNER_SLOT = 22
    MAX_SUPPLY_SLOT = 23
    PAUSED_SLOT = 24
    BALANCES_BASE = 1000
    ALLOWANCES_BASE = 2000
    NONCES_BASE = 3000
    DOMAIN_SEPARATOR_SLOT = 50
    VERSION_VALUE = int.from_bytes(b"XAI20V1".rjust(32, b"\x00"), "big")

    def is_initialized(self) -> bool:
        return self.storage.get_raw(self.VERSION_SLOT) == self.VERSION_VALUE

    def initialize(
        self,
        *,
        name: str,
        symbol: str,
        decimals: int,
        owner: str,
        max_supply: int,
    ) -> None:
        self.storage.set_raw(self.VERSION_SLOT, self.VERSION_VALUE)
        self.write_string(self.NAME_SLOT, name)
        self.write_string(self.SYMBOL_SLOT, symbol)
        self.storage.set_raw(self.DECIMALS_SLOT, decimals)
        self.storage.set_raw(self.TOTAL_SUPPLY_SLOT, 0)
        self.storage.set_raw(self.MAX_SUPPLY_SLOT, max_supply)
        self.storage.set_raw(self.PAUSED_SLOT, 0)
        self.write_address(self.OWNER_SLOT, owner)
        domain = keccak256(
            f"{name}:{symbol}:{decimals}".encode("utf-8") + owner.encode("utf-8")
        )
        self.storage.set_raw(self.DOMAIN_SEPARATOR_SLOT, int.from_bytes(domain, "big"))

    def get_name(self) -> str:
        return self.read_string(self.NAME_SLOT)

    def get_symbol(self) -> str:
        return self.read_string(self.SYMBOL_SLOT)

    def get_decimals(self) -> int:
        return self.storage.get_raw(self.DECIMALS_SLOT)

    def get_total_supply(self) -> int:
        return self.storage.get_raw(self.TOTAL_SUPPLY_SLOT)

    def set_total_supply(self, value: int) -> None:
        self.storage.set_raw(self.TOTAL_SUPPLY_SLOT, value)

    def get_owner(self) -> str:
        return self.read_address(self.OWNER_SLOT)

    def set_owner(self, address: str) -> None:
        self.write_address(self.OWNER_SLOT, address)

    def get_max_supply(self) -> int:
        return self.storage.get_raw(self.MAX_SUPPLY_SLOT)

    def is_paused(self) -> bool:
        return self.storage.get_raw(self.PAUSED_SLOT) == 1

    def set_paused(self, value: bool) -> None:
        self.storage.set_raw(self.PAUSED_SLOT, 1 if value else 0)

    def get_balance(self, address: str) -> int:
        slot = self.mapping_slot(self.BALANCES_BASE, address)
        return self.storage.get_raw(slot)

    def set_balance(self, address: str, value: int) -> None:
        slot = self.mapping_slot(self.BALANCES_BASE, address)
        self.storage.set_raw(slot, value)

    def get_allowance(self, owner: str, spender: str) -> int:
        slot = self.double_mapping_slot(self.ALLOWANCES_BASE, owner, spender)
        return self.storage.get_raw(slot)

    def set_allowance(self, owner: str, spender: str, value: int) -> None:
        slot = self.double_mapping_slot(self.ALLOWANCES_BASE, owner, spender)
        self.storage.set_raw(slot, value)

    def clear_allowance(self, owner: str, spender: str) -> None:
        self.set_allowance(owner, spender, 0)

    def get_nonce(self, owner: str) -> int:
        slot = self.mapping_slot(self.NONCES_BASE, owner)
        return self.storage.get_raw(slot)

    def increment_nonce(self, owner: str) -> int:
        slot = self.mapping_slot(self.NONCES_BASE, owner)
        current = self.storage.get_raw(slot)
        self.storage.set_raw(slot, current + 1)
        return current

    def get_domain_separator(self) -> bytes:
        return self.storage.get_raw(self.DOMAIN_SEPARATOR_SLOT).to_bytes(32, "big")

class ERC20BuiltinContract:
    """Implements ERC20 logic on top of EVM storage."""

    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f714f1fdfcbf8f286d71c2d0d0eebe5d4b59eb93dfff6"

    STATEFUL_FUNCTIONS = {
        "a9059cbb",  # transfer
        "095ea7b3",  # approve
        "23b872dd",  # transferFrom
        "40c10f19",  # mint
        "42966c68",  # burn
        "79cc6790",  # burnFrom
        "8456cb59",  # pause
        "3f4ba83a",  # unpause
        "f2fde38b",  # transferOwnership
        "d505accf",  # permit
    }

    def __init__(
        self,
        *,
        storage: EVMStorage,
        metadata: dict[str, int | str],
        address: str,
        receive_hook: Callable[[str, str, str, int, bytes], None] | None = None,
    ) -> None:
        self.address = _normalize_address(address)
        self.storage = storage
        self.adapter = ERC20StorageAdapter(storage)
        self._receive_hook = receive_hook
        if not self.adapter.is_initialized():
            self.adapter.initialize(
                name=str(metadata.get("name", "")),
                symbol=str(metadata.get("symbol", "")),
                decimals=int(metadata.get("decimals", 18)),
                owner=_normalize_address(str(metadata.get("owner", ZERO_ADDRESS))),
                max_supply=int(metadata.get("max_supply", 0)),
            )
            balances = metadata.get("balances")
            if isinstance(balances, dict) and balances:
                total = 0
                for addr, amount in balances.items():
                    amount_int = int(amount)
                    self.adapter.set_balance(addr, amount_int)
                    total += amount_int
                self.adapter.set_total_supply(total)
            else:
                initial_supply = int(metadata.get("initial_supply", metadata.get("total_supply", 0)))
                distributor = _normalize_address(
                    str(metadata.get("initial_holder", metadata.get("owner", ZERO_ADDRESS)))
                )
                if initial_supply > 0 and distributor != ZERO_ADDRESS:
                    self.adapter.set_total_supply(initial_supply)
                    self.adapter.set_balance(distributor, initial_supply)

    def execute(
        self,
        selector: str,
        calldata: bytes,
        sender: str,
        *,
        value: int,
        static: bool,
    ) -> tuple[bytes, int, list[dict[str, Sequence[str] | str]]]:
        sender = _normalize_address(sender)
        selector_hex = selector.lower()
        if static and selector_hex in self.STATEFUL_FUNCTIONS:
            raise VMExecutionError("State-changing ERC20 call not allowed in static context")
        if value:
            raise VMExecutionError("ERC20 builtin does not accept native token value")

        handlers: dict[str, Callable[[bytes, str], bytes]] = {
            "06fdde03": self._handle_name,
            "95d89b41": self._handle_symbol,
            "313ce567": self._handle_decimals,
            "18160ddd": self._handle_total_supply,
            "70a08231": self._handle_balance_of,
            "a9059cbb": self._handle_transfer,
            "dd62ed3e": self._handle_allowance,
            "095ea7b3": self._handle_approve,
            "23b872dd": self._handle_transfer_from,
            "40c10f19": self._handle_mint,
            "42966c68": self._handle_burn,
            "79cc6790": self._handle_burn_from,
            "8456cb59": self._handle_pause,
            "3f4ba83a": self._handle_unpause,
            "f2fde38b": self._handle_transfer_ownership,
            "d505accf": self._handle_permit,
            "7ecebe00": self._handle_nonce,
            "3644e515": self._handle_domain_separator,
        }

        handler = handlers.get(selector_hex)
        if handler is None:
            raise VMExecutionError(f"ERC20 builtin does not implement selector 0x{selector_hex}")

        logs: list[dict[str, Sequence[str] | str]] = []
        result = handler(calldata, sender, logs)
        return result, 50_000 if selector_hex in self.STATEFUL_FUNCTIONS else 20_000, logs

    def _require_owner(self, caller: str) -> None:
        if _normalize_address(caller) != _normalize_address(self.adapter.get_owner()):
            raise VMExecutionError("ERC20: caller is not owner")

    def _require_not_paused(self) -> None:
        if self.adapter.is_paused():
            raise VMExecutionError("ERC20: token is paused")

    def _handle_name(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_args(["string"], [self.adapter.get_name()])

    def _handle_symbol(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_args(["string"], [self.adapter.get_symbol()])

    def _handle_decimals(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_uint256(self.adapter.get_decimals())

    def _handle_total_supply(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_uint256(self.adapter.get_total_supply())

    def _handle_balance_of(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        addr, _ = decode_address(data, 0)
        balance = self.adapter.get_balance(addr)
        return encode_uint256(balance)

    def _handle_allowance(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        owner, offset = decode_address(data, 0)
        spender, _ = decode_address(data, offset)
        amount = self.adapter.get_allowance(owner, spender)
        return encode_uint256(amount)

    def _handle_transfer(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_not_paused()
        to_addr, offset = decode_address(data, 0)
        amount, _ = decode_uint256(data, offset)
        if amount < 0:
            raise VMExecutionError("ERC20: negative transfer amount")
        balance = self.adapter.get_balance(sender)
        if balance < amount:
            raise VMExecutionError("ERC20: transfer amount exceeds balance")
        dest_balance = self.adapter.get_balance(to_addr)
        self.adapter.set_balance(sender, balance - amount)
        self.adapter.set_balance(to_addr, dest_balance + amount)
        try:
            self._trigger_receive_hook(
                operator=self.address,
                from_addr=sender,
                to_addr=to_addr,
                amount=amount,
                data=b"",
            )
        except VMExecutionError:
            # Revert balances if hook rejects the transfer
            self.adapter.set_balance(sender, balance)
            self.adapter.set_balance(to_addr, dest_balance)
            raise
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(sender),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_approve(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        spender, offset = decode_address(data, 0)
        amount, _ = decode_uint256(data, offset)
        self.adapter.set_allowance(sender, spender, amount)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.APPROVAL_TOPIC,
                    _encode_address_topic(sender),
                    _encode_address_topic(spender),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_transfer_from(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_not_paused()
        from_addr, offset = decode_address(data, 0)
        to_addr, offset = decode_address(data, offset)
        amount, _ = decode_uint256(data, offset)
        allowance = self.adapter.get_allowance(from_addr, sender)
        if allowance < amount:
            raise VMExecutionError("ERC20: insufficient allowance")
        recipient_balance = self.adapter.get_balance(to_addr)
        if allowance != (1 << 256) - 1:
            self.adapter.set_allowance(from_addr, sender, allowance - amount)
        balance = self.adapter.get_balance(from_addr)
        if balance < amount:
            raise VMExecutionError("ERC20: transfer amount exceeds balance")
        self.adapter.set_balance(from_addr, balance - amount)
        self.adapter.set_balance(to_addr, recipient_balance + amount)
        try:
            self._trigger_receive_hook(
                operator=self.address,
                from_addr=from_addr,
                to_addr=to_addr,
                amount=amount,
                data=b"",
            )
        except VMExecutionError:
            # Revert state if hook fails
            self.adapter.set_balance(from_addr, balance)
            self.adapter.set_balance(to_addr, recipient_balance)
            self.adapter.set_allowance(from_addr, sender, allowance)
            raise
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(from_addr),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_mint(
        self, data: bytes, caller: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        self._require_not_paused()
        to_addr, offset = decode_address(data, 0)
        amount, _ = decode_uint256(data, offset)
        if amount <= 0:
            raise VMExecutionError("ERC20: mint amount must be positive")
        max_supply = self.adapter.get_max_supply()
        new_total = self.adapter.get_total_supply() + amount
        if max_supply and new_total > max_supply:
            raise VMExecutionError("ERC20: mint would exceed cap")
        previous_supply = self.adapter.get_total_supply()
        recipient_balance = self.adapter.get_balance(to_addr)
        self.adapter.set_total_supply(new_total)
        self.adapter.set_balance(to_addr, recipient_balance + amount)
        try:
            self._trigger_receive_hook(
                operator=self.address,
                from_addr=ZERO_ADDRESS,
                to_addr=to_addr,
                amount=amount,
                data=b"",
            )
        except VMExecutionError:
            self.adapter.set_total_supply(previous_supply)
            self.adapter.set_balance(to_addr, recipient_balance)
            raise
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(ZERO_ADDRESS),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_burn(
        self, data: bytes, caller: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_not_paused()
        amount, _ = decode_uint256(data, 0)
        balance = self.adapter.get_balance(caller)
        if balance < amount:
            raise VMExecutionError("ERC20: burn amount exceeds balance")
        self.adapter.set_balance(caller, balance - amount)
        self.adapter.set_total_supply(self.adapter.get_total_supply() - amount)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(caller),
                    _encode_address_topic(ZERO_ADDRESS),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_burn_from(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        holder, offset = decode_address(data, 0)
        amount, _ = decode_uint256(data, offset)
        allowance = self.adapter.get_allowance(holder, sender)
        if allowance < amount:
            raise VMExecutionError("ERC20: burn amount exceeds allowance")
        if allowance != (1 << 256) - 1:
            self.adapter.set_allowance(holder, sender, allowance - amount)
        balance = self.adapter.get_balance(holder)
        if balance < amount:
            raise VMExecutionError("ERC20: burn amount exceeds balance")
        self.adapter.set_balance(holder, balance - amount)
        self.adapter.set_total_supply(self.adapter.get_total_supply() - amount)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(holder),
                    _encode_address_topic(ZERO_ADDRESS),
                ],
                "data": encode_uint256(amount).hex(),
            }
        )
        return encode_bool(True)

    def _handle_pause(
        self, _data: bytes, caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        self.adapter.set_paused(True)
        return encode_bool(True)

    def _handle_unpause(
        self, _data: bytes, caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        self.adapter.set_paused(False)
        return encode_bool(True)

    def _handle_transfer_ownership(
        self, data: bytes, caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        new_owner, _ = decode_address(data, 0)
        if new_owner == ZERO_ADDRESS:
            raise VMExecutionError("ERC20: new owner is zero address")
        self.adapter.set_owner(new_owner)
        return encode_bool(True)

    def _handle_nonce(
        self, data: bytes, _caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        owner, _ = decode_address(data, 0)
        nonce = self.adapter.get_nonce(owner)
        return encode_uint256(nonce)

    def _handle_domain_separator(
        self, _data: bytes, _caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return self.adapter.get_domain_separator()

    def _handle_permit(
        self, data: bytes, _caller: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        base = 0
        owner, base = decode_address(data, base)
        spender, base = decode_address(data, base)
        value, base = decode_uint256(data, base)
        deadline, base = decode_uint256(data, base)
        v, base = decode_uint256(data, base)
        r, base = decode_bytes(data, 0, base)
        s, _ = decode_bytes(data, 0, base)
        if deadline < int(time.time()):
            raise VMExecutionError("ERC20Permit: expired deadline")
        if not (v or r or s):
            raise VMExecutionError("ERC20Permit: malformed signature payload")
        self.adapter.set_allowance(owner, spender, value)
        self.adapter.increment_nonce(owner)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.APPROVAL_TOPIC,
                    _encode_address_topic(owner),
                    _encode_address_topic(spender),
                ],
                "data": encode_uint256(value).hex(),
            }
        )
        return encode_bool(True)

    def _trigger_receive_hook(
        self,
        *,
        operator: str,
        from_addr: str,
        to_addr: str,
        amount: int,
        data: bytes,
    ) -> None:
        if (
            not self._receive_hook
            or amount <= 0
            or _normalize_address(to_addr) == ZERO_ADDRESS
        ):
            return
        self._receive_hook(
            operator,
            from_addr,
            to_addr,
            amount,
            data,
        )

@dataclass
class ERC721StorageAdapter(StorageLayout):
    """Minimal storage layout for ERC721 contracts."""

    storage: EVMStorage

    VERSION_SLOT: int = 0
    NAME_SLOT: int = 1
    SYMBOL_SLOT: int = 10
    OWNER_SLOT: int = 20
    TOTAL_SUPPLY_SLOT: int = 21
    BALANCES_BASE: int = 1000
    OWNERS_BASE: int = 2000
    TOKEN_APPROVAL_BASE: int = 3000
    OPERATOR_APPROVAL_BASE: int = 4000
    TOKEN_URI_BASE: int = 5000
    VERSION_VALUE: int = int.from_bytes(b"XAI721".rjust(32, b"\x00"), "big")

    def __post_init__(self) -> None:
        super().__init__(self.storage)

    def is_initialized(self) -> bool:
        return self.storage.get_raw(self.VERSION_SLOT) == self.VERSION_VALUE

    def initialize(self, *, name: str, symbol: str, owner: str) -> None:
        self.storage.set_raw(self.VERSION_SLOT, self.VERSION_VALUE)
        self.write_string(self.NAME_SLOT, name)
        self.write_string(self.SYMBOL_SLOT, symbol)
        self.write_address(self.OWNER_SLOT, owner)
        self.storage.set_raw(self.TOTAL_SUPPLY_SLOT, 0)

    def get_name(self) -> str:
        return self.read_string(self.NAME_SLOT)

    def get_symbol(self) -> str:
        return self.read_string(self.SYMBOL_SLOT)

    def get_owner(self) -> str:
        return self.read_address(self.OWNER_SLOT)

    def set_owner(self, owner: str) -> None:
        self.write_address(self.OWNER_SLOT, owner)

    def get_total_supply(self) -> int:
        return self.storage.get_raw(self.TOTAL_SUPPLY_SLOT)

    def set_total_supply(self, value: int) -> None:
        self.storage.set_raw(self.TOTAL_SUPPLY_SLOT, value)

    def get_balance(self, address: str) -> int:
        slot = self.mapping_slot(self.BALANCES_BASE, address)
        return self.storage.get_raw(slot)

    def set_balance(self, address: str, value: int) -> None:
        slot = self.mapping_slot(self.BALANCES_BASE, address)
        self.storage.set_raw(slot, value)

    def get_token_owner(self, token_id: int) -> str:
        slot = self.mapping_slot(self.OWNERS_BASE, token_id)
        owner_raw = self.storage.get_raw(slot)
        if owner_raw == 0:
            return ZERO_ADDRESS
        return "0x" + owner_raw.to_bytes(32, "big")[-20:].hex()

    def set_token_owner(self, token_id: int, owner: str) -> None:
        slot = self.mapping_slot(self.OWNERS_BASE, token_id)
        self.storage.set_raw(slot, int(_normalize_address(owner)[2:], 16))

    def get_token_approval(self, token_id: int) -> str:
        slot = self.mapping_slot(self.TOKEN_APPROVAL_BASE, token_id)
        raw = self.storage.get_raw(slot)
        return "0x" + raw.to_bytes(32, "big")[-20:].hex()

    def set_token_approval(self, token_id: int, operator: str) -> None:
        slot = self.mapping_slot(self.TOKEN_APPROVAL_BASE, token_id)
        self.storage.set_raw(slot, int(_normalize_address(operator)[2:], 16))

    def clear_token_approval(self, token_id: int) -> None:
        self.set_token_approval(token_id, ZERO_ADDRESS)

    def get_operator_approval(self, owner: str, operator: str) -> bool:
        slot = self.double_mapping_slot(self.OPERATOR_APPROVAL_BASE, owner, operator)
        return self.storage.get_raw(slot) == 1

    def set_operator_approval(self, owner: str, operator: str, approved: bool) -> None:
        slot = self.double_mapping_slot(self.OPERATOR_APPROVAL_BASE, owner, operator)
        self.storage.set_raw(slot, 1 if approved else 0)

    def get_token_uri(self, token_id: int) -> str:
        slot = self.mapping_slot(self.TOKEN_URI_BASE, token_id)
        return self.read_string(slot)

    def set_token_uri(self, token_id: int, uri: str) -> None:
        slot = self.mapping_slot(self.TOKEN_URI_BASE, token_id)
        self.write_string(slot, uri)

class ERC721BuiltinContract:
    """Minimal ERC721 runtime for builtin execution."""

    TRANSFER_TOPIC = ERC20BuiltinContract.TRANSFER_TOPIC
    APPROVAL_TOPIC = ERC20BuiltinContract.APPROVAL_TOPIC
    APPROVAL_FOR_ALL_TOPIC = (
        "0x17307eab39c368c5e5f1dfad57f82f7aaf2ff9e4f3f9f5a64d5fbd49c3a6f2be"
    )

    STATEFUL_SELECTORS = {
        "42842e0e",
        "b88d4fde",
        "23b872dd",
        "095ea7b3",
        "a22cb465",
        "40c10f19",
        "42966c68",
        "f2fde38b",
    }

    def __init__(
        self,
        *,
        storage: EVMStorage,
        metadata: dict[str, str | int],
        address: str,
        receive_hook: Callable[[str, str, str, int, bytes], None] | None = None,
    ) -> None:
        self.address = _normalize_address(address)
        self.storage = storage
        self.adapter = ERC721StorageAdapter(storage)
        self._receive_hook = receive_hook
        if not self.adapter.is_initialized():
            self.adapter.initialize(
                name=str(metadata.get("name", "")),
                symbol=str(metadata.get("symbol", "")),
                owner=_normalize_address(str(metadata.get("owner", ZERO_ADDRESS))),
            )

    def execute(
        self,
        selector: str,
        calldata: bytes,
        sender: str,
        *,
        value: int,
        static: bool,
    ) -> tuple[bytes, int, list[dict[str, Sequence[str] | str]]]:
        sender = _normalize_address(sender)
        if value:
            raise VMExecutionError("ERC721 builtin does not accept native value")
        selector_hex = selector.lower()
        if static and selector_hex in self.STATEFUL_SELECTORS:
            raise VMExecutionError("State-changing ERC721 call in static context")

        handlers: dict[str, Callable[[bytes, str, list[dict[str, Sequence[str] | str]]], bytes]] = {
            "06fdde03": self._handle_name,
            "95d89b41": self._handle_symbol,
            "18160ddd": self._handle_total_supply,
            "70a08231": self._handle_balance_of,
            "6352211e": self._handle_owner_of,
            "23b872dd": self._handle_transfer_from,
            "42842e0e": self._handle_safe_transfer_from,
            "b88d4fde": self._handle_safe_transfer_from_data,
            "095ea7b3": self._handle_approve,
            "081812fc": self._handle_get_approved,
            "a22cb465": self._handle_set_approval_for_all,
            "e985e9c5": self._handle_is_approved_for_all,
            "c87b56dd": self._handle_token_uri,
            "40c10f19": self._handle_mint,
            "42966c68": self._handle_burn,
            "f2fde38b": self._handle_transfer_ownership,
        }

        handler = handlers.get(selector_hex)
        if handler is None:
            raise VMExecutionError(f"ERC721 builtin missing selector 0x{selector_hex}")

        logs: list[dict[str, Sequence[str] | str]] = []
        result = handler(calldata, sender, logs)
        gas = 90_000 if selector_hex in self.STATEFUL_SELECTORS else 30_000
        return result, gas, logs

    def _require_owner(self, caller: str) -> None:
        if _normalize_address(caller) != _normalize_address(self.adapter.get_owner()):
            raise VMExecutionError("ERC721: caller is not owner")

    def _handle_name(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_args(["string"], [self.adapter.get_name()])

    def _handle_symbol(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_args(["string"], [self.adapter.get_symbol()])

    def _handle_total_supply(
        self, _data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        return encode_uint256(self.adapter.get_total_supply())

    def _handle_balance_of(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        owner, _ = decode_address(data, 0)
        if owner == ZERO_ADDRESS:
            raise VMExecutionError("ERC721: balance query for zero address")
        return encode_uint256(self.adapter.get_balance(owner))

    def _handle_owner_of(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        token_id, _ = decode_uint256(data, 0)
        owner = self.adapter.get_token_owner(token_id)
        if owner == ZERO_ADDRESS:
            raise VMExecutionError("ERC721: owner query for nonexistent token")
        return encode_args(["address"], [owner])

    def _is_authorized(
        self, caller: str, owner: str, token_id: int
    ) -> bool:
        if caller == owner:
            return True
        approved = self.adapter.get_token_approval(token_id)
        if approved == caller:
            return True
        return self.adapter.get_operator_approval(owner, caller)

    def _transfer(
        self,
        from_addr: str,
        to_addr: str,
        token_id: int,
        caller: str,
        logs: list[dict[str, Sequence[str] | str]],
    ) -> None:
        owner = self.adapter.get_token_owner(token_id)
        if owner != _normalize_address(from_addr):
            raise VMExecutionError("ERC721: transfer of token not owned by from address")
        if not self._is_authorized(_normalize_address(caller), owner, token_id):
            raise VMExecutionError("ERC721: caller is not owner nor approved")
        if _normalize_address(to_addr) == ZERO_ADDRESS:
            raise VMExecutionError("ERC721: transfer to zero address")
        self.adapter.set_token_owner(token_id, to_addr)
        self.adapter.clear_token_approval(token_id)
        sender_balance = self.adapter.get_balance(owner)
        self.adapter.set_balance(owner, max(0, sender_balance - 1))
        recipient_balance = self.adapter.get_balance(to_addr)
        self.adapter.set_balance(to_addr, recipient_balance + 1)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(owner),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(token_id).hex(),
            }
        )

    def _handle_transfer_from(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        from_addr, offset = decode_address(data, 0)
        to_addr, offset = decode_address(data, offset)
        token_id, _ = decode_uint256(data, offset)
        self._transfer(from_addr, to_addr, token_id, sender, logs)
        return b""

    def _handle_safe_transfer_from(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        from_addr, offset = decode_address(data, 0)
        to_addr, offset = decode_address(data, offset)
        token_id, _ = decode_uint256(data, offset)
        self._perform_safe_transfer(from_addr, to_addr, token_id, sender, logs, b"")
        return b""

    def _handle_safe_transfer_from_data(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        from_addr, offset = decode_address(data, 0)
        to_addr, offset = decode_address(data, offset)
        token_id, offset = decode_uint256(data, offset)
        extra_data, _ = decode_bytes(data, 0, offset)
        self._perform_safe_transfer(from_addr, to_addr, token_id, sender, logs, extra_data)
        return b""

    def _perform_safe_transfer(
        self,
        from_addr: str,
        to_addr: str,
        token_id: int,
        operator: str,
        logs: list[dict[str, Sequence[str] | str]],
        data: bytes,
    ) -> None:
        previous_owner = self.adapter.get_token_owner(token_id)
        previous_owner_balance = self.adapter.get_balance(previous_owner)
        previous_recipient_balance = self.adapter.get_balance(to_addr)
        previous_approval = self.adapter.get_token_approval(token_id)
        self._transfer(from_addr, to_addr, token_id, operator, logs)
        try:
            self._trigger_erc721_receive_hook(
                operator=_normalize_address(operator),
                previous_owner=_normalize_address(previous_owner),
                to_addr=_normalize_address(to_addr),
                token_id=token_id,
                data=data,
            )
        except VMExecutionError:
            # Roll back storage changes on hook failure
            self.adapter.set_token_owner(token_id, previous_owner)
            self.adapter.set_balance(previous_owner, previous_owner_balance)
            self.adapter.set_balance(to_addr, previous_recipient_balance)
            if previous_approval and previous_approval != ZERO_ADDRESS:
                self.adapter.set_token_approval(token_id, previous_approval)
            else:
                self.adapter.clear_token_approval(token_id)
            if logs:
                logs.pop()
            raise

    def _handle_approve(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        to_addr, offset = decode_address(data, 0)
        token_id, _ = decode_uint256(data, offset)
        owner = self.adapter.get_token_owner(token_id)
        if owner in (ZERO_ADDRESS,):
            raise VMExecutionError("ERC721: approving nonexistent token")
        if owner != sender and not self.adapter.get_operator_approval(owner, sender):
            raise VMExecutionError("ERC721: approve caller is not owner nor approved for all")
        self.adapter.set_token_approval(token_id, to_addr)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.APPROVAL_TOPIC,
                    _encode_address_topic(owner),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(token_id).hex(),
            }
        )
        return b""

    def _handle_get_approved(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        token_id, _ = decode_uint256(data, 0)
        approved = self.adapter.get_token_approval(token_id)
        return encode_args(["address"], [approved])

    def _handle_set_approval_for_all(
        self, data: bytes, sender: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        operator, offset = decode_address(data, 0)
        approved, _ = decode_bool(data, offset)
        if operator == sender:
            raise VMExecutionError("ERC721: setting approval status for self")
        self.adapter.set_operator_approval(sender, operator, approved)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.APPROVAL_FOR_ALL_TOPIC,
                    _encode_address_topic(sender),
                    _encode_address_topic(operator),
                ],
                "data": encode_bool(approved).hex(),
            }
        )
        return b""

    def _handle_is_approved_for_all(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        owner, offset = decode_address(data, 0)
        operator, _ = decode_address(data, offset)
        approved = self.adapter.get_operator_approval(owner, operator)
        return encode_bool(approved)

    def _handle_token_uri(
        self, data: bytes, _sender: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        token_id, _ = decode_uint256(data, 0)
        uri = self.adapter.get_token_uri(token_id)
        return encode_args(["string"], [uri])

    def _handle_mint(
        self, data: bytes, caller: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        to_addr, offset = decode_address(data, 0)
        token_id, offset = decode_uint256(data, offset)
        uri = ""
        if len(data) > offset:
            uri_data, _ = decode_bytes(data, 0, offset)
            uri = uri_data.decode("utf-8", errors="replace")
        if self.adapter.get_token_owner(token_id) != ZERO_ADDRESS:
            raise VMExecutionError("ERC721: token already minted")
        self.adapter.set_token_owner(token_id, to_addr)
        self.adapter.set_balance(to_addr, self.adapter.get_balance(to_addr) + 1)
        self.adapter.set_total_supply(self.adapter.get_total_supply() + 1)
        if uri:
            self.adapter.set_token_uri(token_id, uri)
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(ZERO_ADDRESS),
                    _encode_address_topic(to_addr),
                ],
                "data": encode_uint256(token_id).hex(),
            }
        )
        return b""

    def _handle_burn(
        self, data: bytes, caller: str, logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        token_id, _ = decode_uint256(data, 0)
        owner = self.adapter.get_token_owner(token_id)
        if owner == ZERO_ADDRESS:
            raise VMExecutionError("ERC721: burn of nonexistent token")
        if not self._is_authorized(_normalize_address(caller), owner, token_id):
            raise VMExecutionError("ERC721: caller is not owner nor approved")
        self.adapter.set_token_owner(token_id, ZERO_ADDRESS)
        self.adapter.set_balance(owner, max(0, self.adapter.get_balance(owner) - 1))
        self.adapter.set_total_supply(max(0, self.adapter.get_total_supply() - 1))
        logs.append(
            {
                "address": self.address,
                "topics": [
                    self.TRANSFER_TOPIC,
                    _encode_address_topic(owner),
                    _encode_address_topic(ZERO_ADDRESS),
                ],
                "data": encode_uint256(token_id).hex(),
            }
        )
        return b""

    def _handle_transfer_ownership(
        self, data: bytes, caller: str, _logs: list[dict[str, Sequence[str] | str]]
    ) -> bytes:
        self._require_owner(caller)
        new_owner, _ = decode_address(data, 0)
        if new_owner == ZERO_ADDRESS:
            raise VMExecutionError("ERC721: new owner is zero address")
        self.adapter.set_owner(new_owner)
        return b""

    def _trigger_erc721_receive_hook(
        self,
        *,
        operator: str,
        previous_owner: str,
        to_addr: str,
        token_id: int,
        data: bytes,
    ) -> None:
        if not self._receive_hook or _normalize_address(to_addr) == ZERO_ADDRESS:
            return
        self._receive_hook(operator, previous_owner, to_addr, token_id, data)

BuiltinContractResult = tuple[
    bytes, int, list[dict[str, Sequence[str] | str]], EVMStorage
]

def execute_builtin_contract(
    *,
    contract_type: str,
    contract_address: str,
    storage_data: dict[str, int],
    metadata: dict[str, str | int],
    selector: str,
    calldata: bytes,
    sender: str,
    value: int,
    static: bool,
    erc20_receive_hook: Callable[[str, str, str, int, bytes], None] | None = None,
    erc721_receive_hook: Callable[[str, str, str, int, bytes], None] | None = None,
) -> BuiltinContractResult:
    """
    Dispatch an ERC builtin contract call.

    Returns ABI-encoded return data, gas used, and structured logs.
    """
    storage = EVMStorage.from_dict(contract_address, storage_data)
    if contract_type == "ERC20":
        handler = ERC20BuiltinContract(
            storage=storage,
            metadata=metadata,
            address=contract_address,
            receive_hook=erc20_receive_hook,
        )
    elif contract_type == "ERC721":
        handler = ERC721BuiltinContract(
            storage=storage,
            metadata=metadata,
            address=contract_address,
            receive_hook=erc721_receive_hook,
        )
    else:
        raise VMExecutionError(f"Unsupported builtin contract type: {contract_type}")

    output, gas_used, logs = handler.execute(
        selector,
        calldata,
        sender,
        value=value,
        static=static,
    )
    return output, gas_used, logs, handler.storage
