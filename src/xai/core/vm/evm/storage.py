from __future__ import annotations

"""
EVM Storage Implementation.

Contract storage is a persistent key-value store where both keys and values
are 256-bit words. Storage operations have complex gas pricing based on
EIP-2200 and EIP-2929 (warm/cold access).
"""

from dataclasses import dataclass, field

from ..exceptions import VMExecutionError

# Storage gas constants (EIP-2200, EIP-2929)
SLOAD_COLD = 2100  # Cold storage read
SLOAD_WARM = 100  # Warm storage read
SSTORE_SET = 20000  # Setting from zero to non-zero
SSTORE_RESET = 2900  # Changing non-zero to non-zero
SSTORE_CLEAR_REFUND = 4800  # Refund for clearing storage
SSTORE_RESET_REFUND = 2800  # Refund for resetting original value
ACCESS_LIST_STORAGE_KEY = 1900  # EIP-2930 access list storage key

@dataclass
class StorageSlot:
    """Represents a single storage slot with original and current values."""

    original: int  # Value at start of transaction
    current: int  # Current value
    warm: bool = False  # Whether slot has been accessed this transaction

@dataclass
class EVMStorage:
    """
    EVM Storage implementation with EIP-2200/2929 gas accounting.

    Contract storage provides persistent key-value storage where:
    - Keys are 256-bit slot indices
    - Values are 256-bit words
    - Zero values are equivalent to non-existent slots
    - Gas costs depend on warm/cold access and value transitions

    Security features:
    - Storage size limiting per contract
    - Gas refund tracking
    - Access pattern tracking (warm/cold)
    - Original value tracking for accurate gas calculation
    """

    address: str  # Contract address
    max_size: int = 10 * 1024 * 1024  # 10 MB default limit
    _slots: dict[int, StorageSlot] = field(default_factory=dict)
    _accessed_keys: set[int] = field(default_factory=set)
    _pending_refund: int = 0
    _size_bytes: int = 0

    def load(self, key: int) -> tuple[int, int]:
        """
        Load a value from storage (SLOAD).

        Args:
            key: 256-bit storage slot key

        Returns:
            Tuple of (value, gas_cost)
        """
        slot = self._slots.get(key)

        # Calculate gas cost (warm/cold)
        if key in self._accessed_keys:
            gas_cost = SLOAD_WARM
        else:
            gas_cost = SLOAD_COLD
            self._accessed_keys.add(key)

        if slot is None:
            # Non-existent slot returns zero
            return 0, gas_cost

        # Mark as warm
        slot.warm = True
        return slot.current, gas_cost

    def store(self, key: int, value: int) -> tuple[int, int]:
        """
        Store a value to storage (SSTORE).

        Implements EIP-2200 gas metering with net gas metering.

        Args:
            key: 256-bit storage slot key
            value: 256-bit value to store

        Returns:
            Tuple of (gas_cost, refund)

        Raises:
            VMExecutionError: If storage limit exceeded
        """
        value = value & ((1 << 256) - 1)  # Ensure 256-bit

        slot = self._slots.get(key)
        is_cold = key not in self._accessed_keys
        self._accessed_keys.add(key)

        if slot is None:
            # New slot
            original = 0
            current = 0
            slot = StorageSlot(original=original, current=current, warm=True)
            self._slots[key] = slot
        else:
            original = slot.original
            current = slot.current
            slot.warm = True

        # Calculate gas cost and refund per EIP-2200
        gas_cost, refund = self._calculate_sstore_gas(
            original, current, value, is_cold
        )

        # Update value
        slot.current = value

        # Track storage size changes
        if current == 0 and value != 0:
            # Adding new non-zero value
            new_size = self._size_bytes + 32
            if new_size > self.max_size:
                raise VMExecutionError(
                    f"Storage limit exceeded: {new_size} > {self.max_size}"
                )
            self._size_bytes = new_size
        elif current != 0 and value == 0:
            # Clearing a value
            self._size_bytes = max(0, self._size_bytes - 32)

        self._pending_refund += refund
        return gas_cost, refund

    def _calculate_sstore_gas(
        self, original: int, current: int, new: int, is_cold: bool
    ) -> tuple[int, int]:
        """
        Calculate SSTORE gas cost and refund per EIP-2200.

        Args:
            original: Value at transaction start
            current: Current value
            new: New value to store
            is_cold: Whether this is a cold access

        Returns:
            Tuple of (gas_cost, refund)
        """
        # Base cost for cold access
        cold_cost = SLOAD_COLD if is_cold else 0

        # No change - warm access only
        if current == new:
            return SLOAD_WARM + cold_cost, 0

        refund = 0

        if original == current:
            # Slot hasn't been modified yet in this transaction
            if original == 0:
                # 0 -> non-zero (fresh slot)
                return SSTORE_SET + cold_cost, 0
            else:
                if new == 0:
                    # non-zero -> 0 (clearing)
                    refund = SSTORE_CLEAR_REFUND
                # non-zero -> non-zero (or non-zero -> 0)
                return SSTORE_RESET + cold_cost, refund
        else:
            # Slot was already modified in this transaction
            gas = SLOAD_WARM + cold_cost

            # Handle refund adjustments
            if original != 0:
                if current == 0:
                    # We previously got a clear refund, now restoring
                    refund = -SSTORE_CLEAR_REFUND
                elif new == 0:
                    # Now clearing
                    refund = SSTORE_CLEAR_REFUND

            if original == new:
                # Resetting to original value
                if original == 0:
                    refund += SSTORE_SET - SLOAD_WARM
                else:
                    refund += SSTORE_RESET - SLOAD_WARM

            return gas, refund

    def commit(self) -> None:
        """
        Commit current values as original values for next transaction.

        Called at end of successful transaction.
        """
        for slot in self._slots.values():
            slot.original = slot.current
            slot.warm = False
        self._accessed_keys.clear()
        self._pending_refund = 0

    def rollback(self) -> None:
        """
        Rollback to original values.

        Called on revert.
        """
        for slot in self._slots.values():
            slot.current = slot.original
            slot.warm = False
        self._accessed_keys.clear()
        self._pending_refund = 0

    def warm_slot(self, key: int) -> int:
        """
        Pre-warm a storage slot (EIP-2930 access list).

        Args:
            key: Storage slot to warm

        Returns:
            Gas cost for warming
        """
        if key in self._accessed_keys:
            return 0
        self._accessed_keys.add(key)
        return ACCESS_LIST_STORAGE_KEY

    def get_refund(self) -> int:
        """Get accumulated refund."""
        return max(0, self._pending_refund)

    def clear_refund(self) -> None:
        """Clear accumulated refund."""
        self._pending_refund = 0

    @property
    def size(self) -> int:
        """Get current storage size in bytes."""
        return self._size_bytes

    @property
    def slot_count(self) -> int:
        """Get number of non-zero slots."""
        return sum(1 for slot in self._slots.values() if slot.current != 0)

    def get_raw(self, key: int) -> int:
        """
        Get raw value without gas accounting.

        For internal/testing use only.

        Args:
            key: Storage slot key

        Returns:
            Current value (0 if not set)
        """
        slot = self._slots.get(key)
        return slot.current if slot else 0

    def set_raw(self, key: int, value: int) -> None:
        """
        Set raw value without gas accounting.

        For initialization/testing use only.

        Args:
            key: Storage slot key
            value: Value to set
        """
        value = value & ((1 << 256) - 1)
        if key in self._slots:
            self._slots[key].current = value
            self._slots[key].original = value
        else:
            self._slots[key] = StorageSlot(original=value, current=value, warm=False)

    def to_dict(self) -> dict[str, int]:
        """
        Export storage as dictionary for serialization.

        Returns:
            dict mapping hex keys to values
        """
        return {
            f"0x{key:064x}": slot.current
            for key, slot in self._slots.items()
            if slot.current != 0
        }

    @classmethod
    def from_dict(cls, address: str, data: dict[str, int]) -> "EVMStorage":
        """
        Import storage from dictionary.

        Args:
            address: Contract address
            data: dict mapping hex keys to values

        Returns:
            EVMStorage instance
        """
        storage = cls(address=address)
        for key_hex, value in data.items():
            key = int(key_hex, 16) if isinstance(key_hex, str) else key_hex
            storage.set_raw(key, value)
        return storage

    def __repr__(self) -> str:
        """Return string representation."""
        return f"EVMStorage(address={self.address}, slots={self.slot_count}, size={self._size_bytes})"

class TransientStorage:
    """
    EIP-1153 Transient Storage implementation.

    Transient storage is storage that:
    - Is cleared after each transaction
    - Has constant gas cost (100 gas)
    - Cannot be accessed by other transactions
    - Useful for reentrancy locks and other temporary state
    """

    TLOAD_GAS = 100
    TSTORE_GAS = 100

    def __init__(self) -> None:
        """Initialize empty transient storage."""
        self._data: dict[str, dict[int, int]] = {}

    def load(self, address: str, key: int) -> tuple[int, int]:
        """
        Load from transient storage (TLOAD).

        Args:
            address: Contract address
            key: Storage key

        Returns:
            Tuple of (value, gas_cost)
        """
        contract_data = self._data.get(address, {})
        value = contract_data.get(key, 0)
        return value, self.TLOAD_GAS

    def store(self, address: str, key: int, value: int) -> int:
        """
        Store to transient storage (TSTORE).

        Args:
            address: Contract address
            key: Storage key
            value: Value to store

        Returns:
            Gas cost
        """
        if address not in self._data:
            self._data[address] = {}
        self._data[address][key] = value & ((1 << 256) - 1)
        return self.TSTORE_GAS

    def clear(self) -> None:
        """Clear all transient storage (end of transaction)."""
        self._data.clear()

    def clear_contract(self, address: str) -> None:
        """Clear transient storage for a specific contract."""
        self._data.pop(address, None)
