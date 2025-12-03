"""
Helper methods for EVM interpreter CREATE/CREATE2 operations.

These methods handle contract deployment logic including:
- RLP encoding for CREATE address calculation
- Address computation for CREATE and CREATE2
- Init code execution and deployed bytecode extraction
"""

from __future__ import annotations

import hashlib
from typing import Optional, TYPE_CHECKING

from .context import CallContext, CallType
from ..exceptions import VMExecutionError

if TYPE_CHECKING:
    from .interpreter import EVMInterpreter


CODE_DEPOSIT_GAS = 200  # Gas per byte to store deployed contract code


def rlp_encode_address_nonce(address: str, nonce: int) -> bytes:
    """
    RLP encode [address, nonce] for CREATE address calculation.

    Simple RLP encoding for the specific case of address and nonce.

    Args:
        address: 20-byte address (with or without 0x prefix)
        nonce: Account nonce

    Returns:
        RLP-encoded bytes
    """
    # Remove 0x prefix if present
    if address.startswith("0x"):
        address = address[2:]

    # Convert address to bytes
    addr_bytes = bytes.fromhex(address)

    # Encode address (20 bytes = 0x94 prefix for list of 20 items)
    if len(addr_bytes) == 20:
        addr_rlp = b"\x94" + addr_bytes
    else:
        # Fallback for non-standard addresses
        addr_rlp = bytes([0x80 + len(addr_bytes)]) + addr_bytes

    # Encode nonce
    if nonce == 0:
        nonce_rlp = b"\x80"  # Empty string
    elif nonce < 0x80:
        nonce_rlp = bytes([nonce])
    else:
        # Convert nonce to minimal big-endian bytes
        nonce_bytes = nonce.to_bytes((nonce.bit_length() + 7) // 8, "big")
        nonce_rlp = bytes([0x80 + len(nonce_bytes)]) + nonce_bytes

    # Combine with list prefix
    payload = addr_rlp + nonce_rlp
    list_prefix = bytes([0xC0 + len(payload)])
    return list_prefix + payload


def compute_create_address(sender: str, nonce: int) -> str:
    """
    Compute CREATE contract address.

    Address = keccak256(rlp([sender, nonce]))[12:]

    Args:
        sender: Sender address
        nonce: Sender nonce

    Returns:
        New contract address (20 bytes as hex string with 0x prefix)
    """
    rlp_encoded = rlp_encode_address_nonce(sender, nonce)
    addr_hash = hashlib.sha3_256(rlp_encoded).digest()
    return f"0x{addr_hash[-20:].hex()}"


def compute_create2_address(sender: str, salt: int, init_code_hash: bytes) -> str:
    """
    Compute CREATE2 contract address.

    Address = keccak256(0xff ++ sender ++ salt ++ keccak256(init_code))[12:]

    Args:
        sender: Sender address
        salt: 32-byte salt
        init_code_hash: Keccak256 hash of init code (32 bytes)

    Returns:
        New contract address (20 bytes as hex string with 0x prefix)
    """
    # Remove 0x prefix if present
    if sender.startswith("0x"):
        sender = sender[2:]

    # Pad sender to 20 bytes if needed
    sender_bytes = bytes.fromhex(sender.zfill(40))

    # Build: 0xff ++ address(20) ++ salt(32) ++ init_code_hash(32)
    addr_input = b"\xff" + sender_bytes + salt.to_bytes(32, "big") + init_code_hash

    addr_hash = hashlib.sha3_256(addr_input).digest()
    return f"0x{addr_hash[-20:].hex()}"


def account_exists(interpreter: "EVMInterpreter", address: str) -> bool:
    """
    Check if an account exists (has code, balance, or nonce > 0).

    Args:
        interpreter: Interpreter instance
        address: Account address

    Returns:
        True if account exists
    """
    # Check if has code
    code = interpreter.context.get_code(address)
    if code:
        return True

    # Check if has balance
    balance = interpreter.context.get_balance(address)
    if balance > 0:
        return True

    # Check if has nonce
    nonce = interpreter.context.get_nonce(address)
    if nonce > 0:
        return True

    return False


def execute_create(
    interpreter: "EVMInterpreter",
    call: CallContext,
    value: int,
    init_code: bytes,
    salt: Optional[int],
) -> int:
    """
    Execute CREATE or CREATE2 operation.

    Args:
        interpreter: Interpreter instance
        call: Current call context
        value: Value to transfer to new contract
        init_code: Initialization code (constructor)
        salt: Salt for CREATE2, None for CREATE

    Returns:
        New contract address as integer (0 on failure)
    """
    # Check call depth
    if call.depth >= interpreter.context.max_call_depth:
        return 0

    # Get sender nonce and compute address
    if salt is None:
        # CREATE: use nonce
        nonce = interpreter.context.get_nonce(call.address)
        interpreter.context.increment_nonce(call.address)
        new_address = compute_create_address(call.address, nonce)
    else:
        # CREATE2: use salt
        init_code_hash = hashlib.sha3_256(init_code).digest()
        new_address = compute_create2_address(call.address, salt, init_code_hash)

    # Check if address already has code (collision)
    if interpreter.context.get_code(new_address):
        return 0

    # Transfer value if specified
    if value > 0:
        sender_balance = interpreter.context.get_balance(call.address)
        if sender_balance < value:
            return 0  # Insufficient balance

        if not interpreter.context.transfer(call.address, new_address, value):
            return 0

    # Calculate gas to forward (EIP-150: 63/64 rule)
    gas_to_forward = (call.gas * 63) // 64

    # Create init call context
    init_call = CallContext(
        call_type=CallType.CREATE if salt is None else CallType.CREATE2,
        depth=call.depth + 1,
        address=new_address,
        caller=call.address,
        origin=call.origin,
        value=value,
        gas=gas_to_forward,
        code=init_code,
        calldata=b"",  # Constructor has no calldata (args are in init code)
        static=False,
    )

    # Take snapshot for potential revert
    snapshot_id = interpreter.context.take_snapshot()

    try:
        # Execute init code
        interpreter.execute(init_call)

        # Check if execution succeeded
        if init_call.reverted:
            # Revert state changes
            interpreter.context.revert_to_snapshot(snapshot_id)
            return 0

        # Get deployed bytecode from RETURN
        deployed_code = init_call.output

        # Check deployed code size (EIP-170: max 24KB)
        MAX_CODE_SIZE = 24576
        if len(deployed_code) > MAX_CODE_SIZE:
            interpreter.context.revert_to_snapshot(snapshot_id)
            return 0

        # Charge code deposit gas (200 gas per byte stored)
        code_deposit_cost = len(deployed_code) * CODE_DEPOSIT_GAS
        if code_deposit_cost and not call.use_gas(code_deposit_cost):
            interpreter.context.revert_to_snapshot(snapshot_id)
            return 0

        # Empty code is allowed (but unusual)
        # Store deployed code at new address
        interpreter.context.set_code(new_address, deployed_code)

        # Refund remaining gas to caller
        call.gas += init_call.gas

        # Convert address to integer for stack
        addr_int = int(new_address[2:], 16)
        return addr_int

    except VMExecutionError:
        # Execution failed - revert
        interpreter.context.revert_to_snapshot(snapshot_id)
        return 0


def execute_subcall(
    interpreter: "EVMInterpreter",
    call_type: CallType,
    caller: str,
    address: str,
    value: int,
    calldata: bytes,
    gas: int,
    depth: int,
    static: bool,
    code_address: Optional[str] = None,
) -> tuple[bool, bytes]:
    """
    Execute a subcall (CALL, DELEGATECALL, STATICCALL).

    Args:
        interpreter: Interpreter instance
        call_type: Type of call
        caller: Caller address
        address: Target address
        value: Value to transfer
        calldata: Input data
        gas: Gas limit
        depth: Call depth
        static: Static mode flag
        code_address: Code source address (for DELEGATECALL)

    Returns:
        Tuple of (success, return_data)
    """
    # Get code to execute
    if code_address:
        code = interpreter.context.get_code(code_address)
    else:
        code = interpreter.context.get_code(address)

    # If no code, just transfer value and return success
    if not code:
        if value > 0:
            if not interpreter.context.transfer(caller, address, value):
                return False, b""
        return True, b""

    # Create call context
    subcall = CallContext(
        call_type=call_type,
        depth=depth,
        address=address,
        caller=caller,
        origin=interpreter.context.tx_origin,
        value=value,
        gas=gas,
        code=code,
        calldata=calldata,
        static=static,
    )

    # Take snapshot for potential revert
    snapshot_id = interpreter.context.take_snapshot()

    try:
        # Execute the call
        interpreter.execute(subcall)

        # Check if reverted
        if subcall.reverted:
            interpreter.context.revert_to_snapshot(snapshot_id)
            return False, subcall.output

        # Success
        return True, subcall.output

    except VMExecutionError:
        # Execution error - revert
        interpreter.context.revert_to_snapshot(snapshot_id)
        return False, b""
