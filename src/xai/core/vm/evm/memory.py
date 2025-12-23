from __future__ import annotations

"""
EVM Memory Implementation.

The EVM memory is a byte-addressable linear memory that expands dynamically.
Memory expansion has a gas cost that grows quadratically with size.
"""

from ..exceptions import VMExecutionError

# Memory constants
WORD_SIZE = 32  # 256 bits = 32 bytes
MAX_MEMORY_SIZE = 32 * 1024 * 1024  # 32 MB default limit

class EVMMemory:
    """
    EVM Memory implementation with byte-addressable storage.

    Memory is a simple word-addressed byte array that:
    - Starts empty (zero bytes)
    - Expands automatically when accessed beyond current size
    - Has quadratic gas cost for expansion
    - Is volatile (cleared between transactions)

    Security features:
    - Memory size limiting
    - Gas cost tracking for expansion
    - Out-of-bounds access protection
    """

    def __init__(self, max_size: int = MAX_MEMORY_SIZE) -> None:
        """
        Initialize empty EVM memory.

        Args:
            max_size: Maximum memory size in bytes
        """
        self._data: bytearray = bytearray()
        self._max_size = max_size
        self._highest_accessed = 0

    def load(self, offset: int) -> int:
        """
        Load a 256-bit word from memory.

        Args:
            offset: Byte offset to load from

        Returns:
            256-bit word value

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        end = offset + WORD_SIZE
        self._ensure_capacity(end)
        word_bytes = self._data[offset:end]
        # Pad with zeros if needed
        if len(word_bytes) < WORD_SIZE:
            word_bytes = word_bytes + bytes(WORD_SIZE - len(word_bytes))
        return int.from_bytes(word_bytes, "big")

    def load_byte(self, offset: int) -> int:
        """
        Load a single byte from memory.

        Args:
            offset: Byte offset to load from

        Returns:
            Single byte value (0-255)

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        self._ensure_capacity(offset + 1)
        if offset < len(self._data):
            return self._data[offset]
        return 0

    def store(self, offset: int, value: int) -> None:
        """
        Store a 256-bit word to memory.

        Args:
            offset: Byte offset to store at
            value: 256-bit word value

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        end = offset + WORD_SIZE
        self._ensure_capacity(end)

        # Convert value to 32 bytes, big-endian
        value_bytes = (value & ((1 << 256) - 1)).to_bytes(WORD_SIZE, "big")

        # Expand memory if needed
        if end > len(self._data):
            self._data.extend(bytes(end - len(self._data)))

        self._data[offset:end] = value_bytes

    def store_byte(self, offset: int, value: int) -> None:
        """
        Store a single byte to memory.

        Args:
            offset: Byte offset to store at
            value: Byte value (0-255)

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        self._ensure_capacity(offset + 1)

        # Expand memory if needed
        if offset >= len(self._data):
            self._data.extend(bytes(offset + 1 - len(self._data)))

        self._data[offset] = value & 0xFF

    def load_range(self, offset: int, size: int) -> bytes:
        """
        Load a range of bytes from memory.

        Args:
            offset: Byte offset to start from
            size: Number of bytes to load

        Returns:
            Bytes from memory (zero-padded if needed)

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        if size == 0:
            return b""

        end = offset + size
        self._ensure_capacity(end)

        # Expand memory if needed
        if end > len(self._data):
            self._data.extend(bytes(end - len(self._data)))

        return bytes(self._data[offset:end])

    def store_range(self, offset: int, data: bytes) -> None:
        """
        Store a range of bytes to memory.

        Args:
            offset: Byte offset to start at
            data: Bytes to store

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        if not data:
            return

        end = offset + len(data)
        self._ensure_capacity(end)

        # Expand memory if needed
        if end > len(self._data):
            self._data.extend(bytes(end - len(self._data)))

        self._data[offset:end] = data

    def copy(self, dest_offset: int, src_offset: int, size: int) -> None:
        """
        Copy a region of memory (MCOPY - EIP-5656).

        Handles overlapping regions correctly.

        Args:
            dest_offset: Destination byte offset
            src_offset: Source byte offset
            size: Number of bytes to copy

        Raises:
            VMExecutionError: If access exceeds memory limit
        """
        if size == 0:
            return

        # Ensure both regions are accessible
        self._ensure_capacity(max(dest_offset + size, src_offset + size))

        # Read source data first (handles overlapping regions)
        src_data = self.load_range(src_offset, size)
        self.store_range(dest_offset, src_data)

    def _ensure_capacity(self, required_size: int) -> None:
        """
        Ensure memory can accommodate required size.

        Args:
            required_size: Required size in bytes

        Raises:
            VMExecutionError: If required size exceeds limit
        """
        if required_size > self._max_size:
            raise VMExecutionError(
                f"Memory access out of bounds: {required_size} > {self._max_size}"
            )

        if required_size > self._highest_accessed:
            self._highest_accessed = required_size

    @property
    def size(self) -> int:
        """
        Get current memory size (active words * 32).

        Returns number of bytes that have been paid for via gas.
        """
        return self._word_count * WORD_SIZE

    @property
    def _word_count(self) -> int:
        """Get number of 32-byte words in memory."""
        return (self._highest_accessed + WORD_SIZE - 1) // WORD_SIZE

    @property
    def active_size(self) -> int:
        """Get actual byte array size."""
        return len(self._data)

    def expansion_cost(self, offset: int, size: int) -> int:
        """
        Calculate gas cost for memory expansion.

        Memory cost = (memory_size_word ** 2) / 512 + (3 * memory_size_word)
        Expansion cost is the difference between new and current costs.

        Args:
            offset: Access offset
            size: Access size

        Returns:
            Gas cost for this expansion
        """
        if size == 0:
            return 0

        new_size = offset + size
        if new_size <= self._highest_accessed:
            return 0

        current_words = self._word_count
        new_words = (new_size + WORD_SIZE - 1) // WORD_SIZE

        current_cost = self._memory_cost(current_words)
        new_cost = self._memory_cost(new_words)

        return new_cost - current_cost

    @staticmethod
    def _memory_cost(word_count: int) -> int:
        """
        Calculate memory gas cost for given word count.

        Args:
            word_count: Number of 32-byte words

        Returns:
            Gas cost
        """
        return (word_count * word_count) // 512 + (3 * word_count)

    def __len__(self) -> int:
        """Return current memory size in bytes."""
        return self.size

    def __repr__(self) -> str:
        """Return string representation of memory."""
        if self.size == 0:
            return "EVMMemory(size=0)"
        return f"EVMMemory(size={self.size}, active={self.active_size})"

    def clear(self) -> None:
        """Clear memory."""
        self._data.clear()
        self._highest_accessed = 0

    def dump(self, start: int = 0, length: int | None = None) -> str:
        """
        Dump memory contents as hex string for debugging.

        Args:
            start: Starting offset
            length: Number of bytes to dump (None = all)

        Returns:
            Hex string of memory contents
        """
        if length is None:
            length = self.active_size - start
        if length <= 0:
            return ""

        end = min(start + length, self.active_size)
        return self._data[start:end].hex()
