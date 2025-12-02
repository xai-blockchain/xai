"""
EVM Stack Implementation.

The EVM stack is a 256-bit word addressable LIFO structure with a maximum
depth of 1024 items. All stack operations work with 256-bit unsigned integers.
"""

from typing import List, Optional
from ..exceptions import VMExecutionError


# EVM constants
MAX_STACK_DEPTH = 1024
UINT256_MAX = 2**256 - 1
INT256_MAX = 2**255 - 1
INT256_MIN = -(2**255)


class EVMStack:
    """
    EVM Stack implementation with 256-bit word size.

    The stack is the primary working memory for EVM computation.
    All values are stored as Python integers and automatically
    bounded to 256 bits when pushed.

    Security features:
    - Stack depth limiting (1024 max)
    - Underflow detection
    - Overflow detection
    - 256-bit value bounding
    """

    def __init__(self, max_depth: int = MAX_STACK_DEPTH) -> None:
        """
        Initialize empty EVM stack.

        Args:
            max_depth: Maximum stack depth (default 1024)
        """
        self._stack: List[int] = []
        self._max_depth = max_depth

    def push(self, value: int) -> None:
        """
        Push a value onto the stack.

        Args:
            value: Value to push (will be bounded to uint256)

        Raises:
            VMExecutionError: If stack overflow
        """
        if len(self._stack) >= self._max_depth:
            raise VMExecutionError(
                f"Stack overflow: depth {len(self._stack)} >= max {self._max_depth}"
            )

        # Ensure value is within uint256 bounds
        bounded_value = value & UINT256_MAX
        self._stack.append(bounded_value)

    def pop(self) -> int:
        """
        Pop a value from the stack.

        Returns:
            The top stack value

        Raises:
            VMExecutionError: If stack underflow
        """
        if not self._stack:
            raise VMExecutionError("Stack underflow: attempted pop on empty stack")
        return self._stack.pop()

    def peek(self, depth: int = 0) -> int:
        """
        Peek at a value on the stack without removing it.

        Args:
            depth: How far down to peek (0 = top of stack)

        Returns:
            The value at the specified depth

        Raises:
            VMExecutionError: If depth exceeds stack size
        """
        if depth >= len(self._stack):
            raise VMExecutionError(
                f"Stack peek out of range: depth {depth} >= size {len(self._stack)}"
            )
        return self._stack[-(depth + 1)]

    def dup(self, position: int) -> None:
        """
        Duplicate the nth stack item to the top.

        Args:
            position: Position to duplicate (1-indexed, DUP1 = position 1)

        Raises:
            VMExecutionError: If position out of range or stack overflow
        """
        if position < 1 or position > len(self._stack):
            raise VMExecutionError(
                f"Stack DUP{position} out of range: stack size {len(self._stack)}"
            )
        if len(self._stack) >= self._max_depth:
            raise VMExecutionError(f"Stack overflow on DUP{position}")

        value = self._stack[-position]
        self._stack.append(value)

    def swap(self, position: int) -> None:
        """
        Swap the top stack item with the nth item.

        Args:
            position: Position to swap with (1-indexed, SWAP1 = position 1)

        Raises:
            VMExecutionError: If position out of range
        """
        if position < 1 or position > len(self._stack) - 1:
            raise VMExecutionError(
                f"Stack SWAP{position} out of range: stack size {len(self._stack)}"
            )

        # SWAP1 swaps positions 0 and 1 (top and second)
        self._stack[-1], self._stack[-(position + 1)] = (
            self._stack[-(position + 1)],
            self._stack[-1],
        )

    def pop_n(self, n: int) -> List[int]:
        """
        Pop n values from the stack.

        Args:
            n: Number of values to pop

        Returns:
            List of popped values (first = was on top)

        Raises:
            VMExecutionError: If stack underflow
        """
        if n > len(self._stack):
            raise VMExecutionError(
                f"Stack underflow: tried to pop {n} from stack of size {len(self._stack)}"
            )
        result = [self._stack.pop() for _ in range(n)]
        return result

    def push_n(self, values: List[int]) -> None:
        """
        Push multiple values onto the stack.

        Args:
            values: Values to push (first = pushed first, ends up deepest)

        Raises:
            VMExecutionError: If stack overflow
        """
        if len(self._stack) + len(values) > self._max_depth:
            raise VMExecutionError(
                f"Stack overflow: {len(self._stack)} + {len(values)} > {self._max_depth}"
            )
        for value in values:
            self.push(value)

    def __len__(self) -> int:
        """Return current stack depth."""
        return len(self._stack)

    def __repr__(self) -> str:
        """Return string representation of stack."""
        if not self._stack:
            return "EVMStack([])"
        top_items = self._stack[-5:] if len(self._stack) > 5 else self._stack
        hex_items = [f"0x{v:064x}" for v in reversed(top_items)]
        if len(self._stack) > 5:
            return f"EVMStack(depth={len(self._stack)}, top=[{', '.join(hex_items)}...])"
        return f"EVMStack([{', '.join(hex_items)}])"

    @property
    def depth(self) -> int:
        """Return current stack depth."""
        return len(self._stack)

    @property
    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return len(self._stack) == 0

    def clear(self) -> None:
        """Clear the stack."""
        self._stack.clear()


def to_signed(value: int) -> int:
    """
    Convert unsigned 256-bit value to signed.

    Args:
        value: Unsigned 256-bit integer

    Returns:
        Signed integer representation
    """
    if value > INT256_MAX:
        return value - (UINT256_MAX + 1)
    return value


def to_unsigned(value: int) -> int:
    """
    Convert signed value to unsigned 256-bit.

    Args:
        value: Signed integer

    Returns:
        Unsigned 256-bit representation
    """
    if value < 0:
        return value + (UINT256_MAX + 1)
    return value & UINT256_MAX


def sign_extend(value: int, byte_size: int) -> int:
    """
    Sign-extend a value from byte_size bytes to 256 bits.

    Args:
        value: Value to extend
        byte_size: Original byte size (0-31)

    Returns:
        Sign-extended 256-bit value
    """
    if byte_size >= 32:
        return value & UINT256_MAX

    bit_size = (byte_size + 1) * 8
    sign_bit = 1 << (bit_size - 1)
    mask = (1 << bit_size) - 1

    value = value & mask
    if value & sign_bit:
        # Negative - extend with 1s
        return value | (UINT256_MAX ^ mask)
    else:
        # Positive - already correct
        return value
