"""
Minimal ABI encoding/decoding utilities for EVM contract calls.

Supports common Solidity types and call data construction:
- address, uint256, int256, bool
- bytes (dynamic), string (dynamic)
- bytes32 (static)

Implements function selector derivation and head/tail layout for dynamic types
following the Ethereum ABI specification.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

def keccak256(data: bytes) -> bytes:
    """Return Keccak-256 digest compatible with Ethereum.

    Tries multiple providers in order:
    - pysha3 (sha3.keccak_256)
    - pycryptodome (Crypto.Hash.keccak)
    - hashlib.new("keccak256") if available
    - as a last resort, hashlib.sha3_256 (note: different from Keccak-256)
    """
    # pysha3
    try:
        import sha3  # type: ignore

        k = sha3.keccak_256()
        k.update(data)
        return k.digest()
    except ImportError:
        logger.debug("sha3 library not available, trying fallback")
    except (AttributeError, TypeError, RuntimeError) as e:
        logger.warning("Failed to use sha3 library", extra={"error": str(e), "error_type": type(e).__name__})

    # pycryptodome
    try:
        from Crypto.Hash import keccak  # type: ignore

        k = keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except ImportError:
        logger.debug("pycryptodome library not available, trying fallback")
    except (AttributeError, TypeError, ValueError, RuntimeError) as e:
        logger.warning("Failed to use pycryptodome library", extra={"error": str(e), "error_type": type(e).__name__})

    # hashlib keccak (not widely available)
    try:
        return hashlib.new("keccak256", data).digest()
    except ValueError:
        logger.debug("hashlib keccak256 not available, using SHA3-256 fallback")
    except (AttributeError, TypeError, RuntimeError) as e:
        logger.warning("Failed to use hashlib keccak256", extra={"error": str(e), "error_type": type(e).__name__})

    # Fallback (SHA3-256) - not identical to Keccak-256
    logger.debug("Using SHA3-256 fallback (not identical to Keccak-256)")
    return hashlib.sha3_256(data).digest()

def function_selector(signature: str) -> bytes:
    """Return 4-byte function selector for a given function signature."""
    return keccak256(signature.encode("utf-8"))[:4]

def _pad_right(b: bytes, size: int = 32) -> bytes:
    if len(b) % size == 0:
        return b
    return b + bytes(size - (len(b) % size))

def _pad_left(b: bytes, size: int = 32) -> bytes:
    if len(b) >= size:
        return b[-size:]
    return bytes(size - len(b)) + b

# ==================== Encoders ====================

def encode_uint256(value: int) -> bytes:
    if value < 0:
        raise ValueError("uint256 cannot be negative")
    return _pad_left(value.to_bytes(32, "big"))

def encode_int256(value: int) -> bytes:
    if value >= 0:
        return _pad_left(value.to_bytes(32, "big"))
    # Two's complement for negative numbers
    return (value & ((1 << 256) - 1)).to_bytes(32, "big")

def encode_bool(value: bool) -> bytes:
    return encode_uint256(1 if value else 0)

def encode_address(addr: str) -> bytes:
    """Encode an Ethereum-style address (0x-prefixed or plain hex) as 32-byte word."""
    if addr.startswith("0x"):
        addr = addr[2:]
    if len(addr) != 40:
        # Accept shorter inputs if leading zeros omitted; left-pad to 20 bytes
        if len(addr) > 40:
            raise ValueError("Invalid address length")
        addr = addr.rjust(40, "0")
    raw = bytes.fromhex(addr)
    if len(raw) != 20:
        raise ValueError("Address must be 20 bytes")
    return _pad_left(raw, 32)

def encode_bytes32(value: bytes) -> bytes:
    if len(value) != 32:
        raise ValueError("bytes32 must be exactly 32 bytes")
    return value

def encode_bytes(value: bytes) -> bytes:
    length = encode_uint256(len(value))
    data = _pad_right(value, 32)
    return length + data

def encode_string(value: str) -> bytes:
    return encode_bytes(value.encode("utf-8"))

def encode_args(types: Sequence[str], values: Sequence[Any]) -> bytes:
    """
    Encode arguments following the ABI head/tail scheme.

    Supported static types: uint256, int256, bool, address, bytes32
    Supported dynamic types: bytes, string
    """
    if len(types) != len(values):
        raise ValueError("Types and values length mismatch")

    head_parts: list[bytes] = []
    tail_parts: list[bytes] = []

    # Determine dynamic offsets
    # Each head slot is 32 bytes; dynamic heads store offset from start of args payload
    dynamic_indices: list[int] = []
    for t in types:
        if t in ("bytes", "string"):
            dynamic_indices.append(1)
        else:
            dynamic_indices.append(0)

    # Calculate head size (in bytes)
    head_size = 32 * len(types)
    current_tail_offset = 0

    # First pass: build head
    for t, v in zip(types, values):
        if t == "uint256":
            head_parts.append(encode_uint256(int(v)))
        elif t == "int256":
            head_parts.append(encode_int256(int(v)))
        elif t == "bool":
            head_parts.append(encode_bool(bool(v)))
        elif t == "address":
            head_parts.append(encode_address(str(v)))
        elif t == "bytes32":
            b = v if isinstance(v, (bytes, bytearray)) else bytes.fromhex(str(v))
            if len(b) != 32:
                raise ValueError("bytes32 must be 32 bytes")
            head_parts.append(bytes(b))
        elif t == "bytes":
            # store offset placeholder now; tail added later
            head_parts.append(encode_uint256(head_size + current_tail_offset))
            data = v if isinstance(v, (bytes, bytearray)) else bytes(v)
            enc = encode_bytes(bytes(data))
            tail_parts.append(enc)
            current_tail_offset += len(enc)
        elif t == "string":
            head_parts.append(encode_uint256(head_size + current_tail_offset))
            enc = encode_string(str(v))
            tail_parts.append(enc)
            current_tail_offset += len(enc)
        else:
            raise ValueError(f"Unsupported type: {t}")

    return b"".join(head_parts) + b"".join(tail_parts)

def encode_call(signature: str, args: Sequence[Any]) -> bytes:
    """Encode a function call given signature like 'transfer(address,uint256)' and values."""
    # Parse types from signature inside parentheses
    name, _, rest = signature.partition("(")
    if not rest.endswith(")"):
        raise ValueError("Invalid function signature")
    types_str = rest[:-1]
    types = [t.strip() for t in types_str.split(",")] if types_str else []
    return function_selector(signature) + encode_args(types, list(args))

# ==================== Decoders (basic) ====================

def _require_len(data: bytes, size: int) -> None:
    if len(data) < size:
        raise ValueError("Insufficient data for decoding")

def decode_uint256(data: bytes, offset: int = 0) -> tuple[int, int]:
    _require_len(data[offset:], 32)
    return int.from_bytes(data[offset : offset + 32], "big"), offset + 32

def decode_bool(data: bytes, offset: int = 0) -> tuple[bool, int]:
    val, new_off = decode_uint256(data, offset)
    return val != 0, new_off

def decode_address(data: bytes, offset: int = 0) -> tuple[str, int]:
    _require_len(data[offset:], 32)
    raw = data[offset + 12 : offset + 32]
    return "0x" + raw.hex(), offset + 32

def decode_bytes32(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    _require_len(data[offset:], 32)
    return data[offset : offset + 32], offset + 32

def decode_bytes(data: bytes, base: int = 0, offset: int = 0) -> tuple[bytes, int]:
    # offset is the position in the head where the pointer resides
    ptr, off2 = decode_uint256(data, offset)
    length, _ = decode_uint256(data, base + ptr)
    start = base + ptr + 32
    end = start + ((length + 31) // 32) * 32
    _require_len(data, end)
    return data[start : start + length], off2

def decode_string(data: bytes, base: int = 0, offset: int = 0) -> tuple[str, int]:
    b, off = decode_bytes(data, base, offset)
    return b.decode("utf-8", errors="replace"), off
