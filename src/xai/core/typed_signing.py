"""
XAI Typed Data Signing - EIP-712/EIP-191 Equivalent

Provides standardized message and structured data signing for XAI blockchain.

Standards implemented:
- XIP-191: Personal message signing (like EIP-191)
- XIP-712: Typed structured data signing (like EIP-712)

These standards prevent signature replay attacks and ensure users know
exactly what they're signing.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


# XAI signing prefixes (similar to Ethereum's)
XIP191_PREFIX = b"\x19XAI Signed Message:\n"
XIP712_PREFIX = b"\x19\x01"


@dataclass
class TypedDataDomain:
    """
    EIP-712 style domain separator.

    Prevents signature replay across different:
    - Contracts/applications (name, verifyingContract)
    - Chains (chainId)
    - Versions (version)
    """
    name: str
    version: str
    chain_id: int
    verifying_contract: Optional[str] = None
    salt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for hashing."""
        d = {
            "name": self.name,
            "version": self.version,
            "chainId": self.chain_id,
        }
        if self.verifying_contract:
            d["verifyingContract"] = self.verifying_contract
        if self.salt:
            d["salt"] = self.salt
        return d


# Standard type definitions for XIP-712
PRIMITIVE_TYPES = {
    "bool", "address", "string", "bytes",
    "uint8", "uint16", "uint32", "uint64", "uint128", "uint256",
    "int8", "int16", "int32", "int64", "int128", "int256",
    "bytes1", "bytes2", "bytes4", "bytes8", "bytes16", "bytes32",
}


def _is_array_type(type_name: str) -> Tuple[bool, str, Optional[int]]:
    """
    Check if type is an array type.

    Returns:
        Tuple of (is_array, base_type, array_length or None for dynamic)
    """
    match = re.match(r'^(.+)\[(\d*)\]$', type_name)
    if match:
        base_type = match.group(1)
        length = int(match.group(2)) if match.group(2) else None
        return True, base_type, length
    return False, type_name, None


def _encode_type(type_name: str, types: Dict[str, List[Dict[str, str]]]) -> str:
    """
    Encode a type string for hashing (EIP-712 encodeType).

    Args:
        type_name: Name of the type to encode
        types: Dictionary of type definitions

    Returns:
        Encoded type string
    """
    if type_name not in types:
        return ""

    # Get direct encoding
    fields = types[type_name]
    encoded = f"{type_name}({','.join(f['type'] + ' ' + f['name'] for f in fields)})"

    # Find and sort dependencies
    deps = set()
    for field in fields:
        field_type = field['type']
        is_array, base_type, _ = _is_array_type(field_type)
        if is_array:
            field_type = base_type
        if field_type in types and field_type != type_name:
            deps.add(field_type)
            # Recursively find dependencies
            for dep in _find_type_dependencies(field_type, types):
                deps.add(dep)

    # Append sorted dependencies
    for dep in sorted(deps):
        dep_fields = types[dep]
        encoded += f"{dep}({','.join(f['type'] + ' ' + f['name'] for f in dep_fields)})"

    return encoded


def _find_type_dependencies(type_name: str, types: Dict, visited: Optional[set] = None) -> set:
    """Find all type dependencies recursively."""
    if visited is None:
        visited = set()

    if type_name in visited or type_name not in types:
        return set()

    visited.add(type_name)
    deps = set()

    for field in types[type_name]:
        field_type = field['type']
        is_array, base_type, _ = _is_array_type(field_type)
        if is_array:
            field_type = base_type
        if field_type in types:
            deps.add(field_type)
            deps.update(_find_type_dependencies(field_type, types, visited))

    return deps


def _hash_type(type_name: str, types: Dict[str, List[Dict[str, str]]]) -> bytes:
    """Compute typeHash for a type."""
    encoded = _encode_type(type_name, types)
    return hashlib.sha256(encoded.encode('utf-8')).digest()


def _encode_data(
    type_name: str,
    data: Dict[str, Any],
    types: Dict[str, List[Dict[str, str]]]
) -> bytes:
    """
    Encode structured data for hashing (EIP-712 encodeData).

    Args:
        type_name: Name of the primary type
        data: Data to encode
        types: Type definitions

    Returns:
        Encoded data bytes
    """
    encoded = _hash_type(type_name, types)

    for field in types[type_name]:
        field_name = field['name']
        field_type = field['type']
        value = data.get(field_name)

        encoded += _encode_value(field_type, value, types)

    return encoded


def _encode_value(
    type_name: str,
    value: Any,
    types: Dict[str, List[Dict[str, str]]]
) -> bytes:
    """Encode a single value based on its type."""
    # Handle arrays
    is_array, base_type, _ = _is_array_type(type_name)
    if is_array:
        if not isinstance(value, (list, tuple)):
            value = [value] if value is not None else []
        encoded = b''
        for item in value:
            encoded += _encode_value(base_type, item, types)
        return hashlib.sha256(encoded).digest()

    # Handle primitive types
    if type_name == "string":
        return hashlib.sha256((value or "").encode('utf-8')).digest()
    elif type_name == "bytes":
        if isinstance(value, str):
            value = bytes.fromhex(value.replace('0x', ''))
        return hashlib.sha256(value or b'').digest()
    elif type_name == "bool":
        return (1 if value else 0).to_bytes(32, 'big')
    elif type_name == "address":
        # XAI address - hash to 32 bytes
        addr = (value or "").replace("XAI", "").replace("TXAI", "")
        # Convert to hex if not already
        if not all(c in '0123456789abcdefABCDEF' for c in addr):
            # Hash the string representation
            addr_bytes = addr.encode('utf-8')
            return hashlib.sha256(addr_bytes).digest()
        return bytes.fromhex(addr.ljust(64, '0')[:64])
    elif type_name.startswith("uint") or type_name.startswith("int"):
        # Extract bit size
        bits = int(re.search(r'\d+', type_name).group())
        byte_size = bits // 8
        val = int(value or 0)
        if type_name.startswith("int") and val < 0:
            # Two's complement for signed
            val = (1 << bits) + val
        return val.to_bytes(32, 'big')
    elif type_name.startswith("bytes") and type_name != "bytes":
        # Fixed-size bytes
        size = int(type_name[5:])
        if isinstance(value, str):
            value = bytes.fromhex(value.replace('0x', ''))
        value = (value or b'').ljust(size, b'\x00')[:size]
        return value.ljust(32, b'\x00')
    elif type_name in types:
        # Struct type - recursive encoding
        return hashlib.sha256(_encode_data(type_name, value or {}, types)).digest()
    else:
        raise ValueError(f"Unknown type: {type_name}")


def hash_personal_message(message: Union[str, bytes]) -> bytes:
    """
    Hash a personal message (XIP-191 equivalent of EIP-191).

    The message is prefixed with "\\x19XAI Signed Message:\\n<length>"
    to prevent signing arbitrary transaction data.

    Args:
        message: Message to hash (string or bytes)

    Returns:
        32-byte SHA256 hash ready for signing
    """
    if isinstance(message, str):
        message = message.encode('utf-8')

    # Prefix with XAI marker and length
    prefixed = XIP191_PREFIX + str(len(message)).encode('utf-8') + message
    return hashlib.sha256(prefixed).digest()


def hash_typed_data(
    domain: TypedDataDomain,
    primary_type: str,
    types: Dict[str, List[Dict[str, str]]],
    message: Dict[str, Any]
) -> bytes:
    """
    Hash typed structured data (XIP-712 equivalent of EIP-712).

    This creates a hash that:
    1. Is unique to this domain (app/chain)
    2. Includes type information (prevents type confusion)
    3. Includes all structured data

    Args:
        domain: Domain separator (app name, version, chain)
        primary_type: Name of the primary type being signed
        types: Dictionary of all type definitions
        message: The structured data to sign

    Returns:
        32-byte SHA256 hash ready for signing
    """
    # Add EIP712Domain to types if not present
    domain_type = [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
    ]
    if domain.verifying_contract:
        domain_type.append({"name": "verifyingContract", "type": "address"})
    if domain.salt:
        domain_type.append({"name": "salt", "type": "bytes32"})

    types_with_domain = {**types, "EIP712Domain": domain_type}

    # Hash domain separator
    domain_hash = hashlib.sha256(
        _encode_data("EIP712Domain", domain.to_dict(), types_with_domain)
    ).digest()

    # Hash message
    message_hash = hashlib.sha256(
        _encode_data(primary_type, message, types_with_domain)
    ).digest()

    # Combine with XIP-712 prefix
    return hashlib.sha256(XIP712_PREFIX + domain_hash + message_hash).digest()


def create_personal_sign_request(message: str) -> Dict[str, Any]:
    """
    Create a personal_sign request object.

    Compatible with wallet RPC methods.

    Args:
        message: Human-readable message to sign

    Returns:
        Request object with message and hash
    """
    msg_bytes = message.encode('utf-8')
    return {
        "method": "personal_sign",
        "params": {
            "message": message,
            "message_hex": msg_bytes.hex(),
            "hash": hash_personal_message(message).hex(),
        }
    }


def create_typed_sign_request(
    domain: TypedDataDomain,
    primary_type: str,
    types: Dict[str, List[Dict[str, str]]],
    message: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a signTypedData request object.

    Compatible with wallet RPC methods (like eth_signTypedData_v4).

    Args:
        domain: Domain separator
        primary_type: Primary type name
        types: Type definitions
        message: Structured message data

    Returns:
        Request object with full typed data and hash
    """
    typed_data = {
        "types": types,
        "primaryType": primary_type,
        "domain": domain.to_dict(),
        "message": message,
    }

    return {
        "method": "xai_signTypedData",
        "params": {
            "typedData": typed_data,
            "hash": hash_typed_data(domain, primary_type, types, message).hex(),
        }
    }


# Common type definitions for reuse
PERMIT_TYPES = {
    "Permit": [
        {"name": "owner", "type": "address"},
        {"name": "spender", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "deadline", "type": "uint256"},
    ]
}

TRANSFER_TYPES = {
    "Transfer": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
    ]
}

VOTE_TYPES = {
    "Vote": [
        {"name": "proposalId", "type": "uint256"},
        {"name": "support", "type": "bool"},
        {"name": "voter", "type": "address"},
    ]
}


def create_permit_signature_request(
    token_name: str,
    token_address: str,
    chain_id: int,
    owner: str,
    spender: str,
    value: int,
    nonce: int,
    deadline: int,
) -> Dict[str, Any]:
    """
    Create a token permit signature request (gasless approval).

    Args:
        token_name: Token name for domain
        token_address: Token contract address
        chain_id: Chain ID
        owner: Token owner address
        spender: Approved spender address
        value: Amount to approve
        nonce: Owner's nonce
        deadline: Permit deadline timestamp

    Returns:
        Typed sign request for permit
    """
    domain = TypedDataDomain(
        name=token_name,
        version="1",
        chain_id=chain_id,
        verifying_contract=token_address,
    )

    message = {
        "owner": owner,
        "spender": spender,
        "value": value,
        "nonce": nonce,
        "deadline": deadline,
    }

    return create_typed_sign_request(domain, "Permit", PERMIT_TYPES, message)
