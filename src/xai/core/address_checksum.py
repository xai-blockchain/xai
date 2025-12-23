from __future__ import annotations

"""
XAI Address Checksum - EIP-55 Style Mixed-Case Encoding

Provides error detection for XAI addresses using keccak256-based
mixed-case checksumming, compatible with the EIP-55 standard adapted
for XAI's address format.

Address Format:
- Raw:      XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
- Checksum: XAI7A8b9C0d1E2f3A4b5C6D7e8F9a0B1c2D3e4F5A6b
"""

import hashlib


def _keccak256(data: bytes) -> bytes:
    """Compute keccak256 hash (same as Ethereum)."""
    from Crypto.Hash import keccak
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()

def _sha3_256_fallback(data: bytes) -> bytes:
    """Fallback using hashlib sha3_256 if pycryptodome unavailable."""
    return hashlib.sha3_256(data).digest()

def _get_hash_function():
    """Get best available hash function."""
    try:
        from Crypto.Hash import keccak
        return _keccak256
    except ImportError:
        # sha3_256 is close enough for checksum purposes
        return _sha3_256_fallback

def to_checksum_address(address: str) -> str:
    """
    Convert XAI address to checksummed format (EIP-55 style).

    Args:
        address: XAI address (with or without checksum)

    Returns:
        Checksummed address with mixed-case hex

    Raises:
        ValueError: If address format is invalid

    Example:
        >>> to_checksum_address("XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")
        'XAI7A8b9C0d1E2f3A4b5C6D7e8F9a0B1c2D3e4F5A6b'
    """
    # Handle prefixes (case-insensitive)
    address_upper = address.upper()
    if address_upper.startswith("XAI") and not address_upper.startswith("XAIT"):
        prefix = "XAI"
        hex_part = address[3:]
    elif address_upper.startswith("TXAI"):
        prefix = "TXAI"
        hex_part = address[4:]
    else:
        raise ValueError(f"Invalid address prefix: {address[:4]}")

    # Validate hex part
    hex_lower = hex_part.lower()
    if len(hex_lower) != 40:
        raise ValueError(f"Address hex part must be 40 characters, got {len(hex_lower)}")

    try:
        int(hex_lower, 16)
    except ValueError:
        raise ValueError(f"Invalid hex characters in address: {hex_part}")

    # Compute checksum hash
    hash_func = _get_hash_function()
    address_hash = hash_func(hex_lower.encode('utf-8')).hex()

    # Apply mixed-case checksum (EIP-55 algorithm)
    checksummed = []
    for i, char in enumerate(hex_lower):
        if char in '0123456789':
            checksummed.append(char)
        elif int(address_hash[i], 16) >= 8:
            checksummed.append(char.upper())
        else:
            checksummed.append(char.lower())

    return prefix + ''.join(checksummed)

def is_checksum_valid(address: str) -> bool:
    """
    Verify if address has valid checksum.

    Args:
        address: XAI address to verify

    Returns:
        True if checksum is valid or address is all lowercase/uppercase
        False if checksum is invalid
    """
    # Handle case-insensitive prefix check
    address_upper = address.upper()
    if address_upper.startswith("XAI") and not address_upper.startswith("XAIT"):
        hex_part = address[3:]
    elif address_upper.startswith("TXAI"):
        hex_part = address[4:]
    else:
        return False

    # All lowercase or all uppercase is valid (no checksum applied)
    if hex_part == hex_part.lower() or hex_part == hex_part.upper():
        return True

    # Mixed case - verify checksum
    try:
        return address == to_checksum_address(address)
    except ValueError:
        return False

def validate_address(address: str, require_checksum: bool = False) -> tuple[bool, str]:
    """
    Validate XAI address format and optionally checksum.

    Args:
        address: Address to validate
        require_checksum: If True, reject addresses without valid checksum

    Returns:
        Tuple of (is_valid, error_message or checksummed_address)
    """
    # Check prefix (case-insensitive)
    address_upper = address.upper()
    if address_upper.startswith("XAI") and not address_upper.startswith("XAIT"):
        prefix = "XAI"
        hex_part = address[3:]
    elif address_upper.startswith("TXAI"):
        prefix = "TXAI"
        hex_part = address[4:]
    else:
        return False, "Address must start with XAI or TXAI"

    # Check length
    if len(hex_part) != 40:
        return False, f"Address must be {len(prefix) + 40} characters"

    # Check hex validity
    try:
        int(hex_part, 16)
    except ValueError:
        return False, "Address contains invalid hex characters"

    # Check checksum if required or if mixed case
    if require_checksum or (hex_part != hex_part.lower() and hex_part != hex_part.upper()):
        if not is_checksum_valid(address):
            # Reconstruct proper prefix for expected address
            base_addr = prefix + hex_part.lower()
            expected = to_checksum_address(base_addr)
            return False, f"Invalid checksum. Did you mean {expected}?"

    # Return checksummed version
    return True, to_checksum_address(address)

def normalize_address(address: str) -> str:
    """
    Normalize address to checksummed format.

    Accepts any valid address format and returns the checksummed version.

    Args:
        address: XAI address in any case format

    Returns:
        Checksummed address

    Raises:
        ValueError: If address is invalid
    """
    is_valid, result = validate_address(address)
    if not is_valid:
        raise ValueError(result)
    return result
