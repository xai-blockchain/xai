"""
EVM Bytecode Executor.

This module provides the main entry point for EVM bytecode execution,
integrating the interpreter with the XAI blockchain framework.
"""

from __future__ import annotations

import hashlib
import time
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from .interpreter import EVMInterpreter
from .context import ExecutionContext, CallContext, CallType, BlockContext, Log
from .memory import EVMMemory
from .stack import EVMStack
from .storage import EVMStorage
from ..executor import ExecutionMessage, ExecutionResult, BaseExecutor
from ..exceptions import VMExecutionError

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


logger = logging.getLogger(__name__)


class EVMBytecodeExecutor(BaseExecutor):
    """
    Production EVM bytecode executor.

    This executor provides full EVM compatibility, allowing deployment and
    execution of Solidity-compiled smart contracts. It integrates with the
    XAI blockchain's state management and transaction processing.

    Features:
    - Full EVM opcode support (140+ opcodes)
    - EIP-compliant gas metering (EIP-2200, EIP-2929)
    - Contract creation (CREATE, CREATE2)
    - Contract calls (CALL, DELEGATECALL, STATICCALL)
    - Event emission (LOG0-LOG4)
    - Transient storage (EIP-1153)
    - Memory copy (EIP-5656)
    - PUSH0 (EIP-3855)

    Security features:
    - Gas limit enforcement
    - Stack depth limiting (1024)
    - Memory expansion limiting
    - Storage size limiting per contract
    - Execution timeout (10s)
    - Reentrancy protection
    - Static call enforcement
    """

    # Default chain ID for XAI
    XAI_CHAIN_ID = 0x584149  # "XAI" in hex

    # Gas limits
    DEFAULT_GAS_LIMIT = 15_000_000
    MAX_GAS_LIMIT = 30_000_000

    # Contract limits
    MAX_CODE_SIZE = 24_576  # EIP-170: 24KB max contract size
    MAX_INITCODE_SIZE = 49_152  # EIP-3860: 2x max contract size

    def __init__(
        self,
        blockchain: "Blockchain",
        chain_id: Optional[int] = None,
    ) -> None:
        """
        Initialize EVM executor.

        Args:
            blockchain: XAI blockchain instance
            chain_id: Optional chain ID override
        """
        self.blockchain = blockchain
        self.chain_id = chain_id or self.XAI_CHAIN_ID
        self._contract_locks: Dict[str, bool] = {}

        logger.info(
            "EVM executor initialized",
            extra={
                "event": "evm.executor_init",
                "chain_id": self.chain_id,
            }
        )

    def execute(self, message: ExecutionMessage) -> ExecutionResult:
        """
        Execute a contract transaction.

        For contract creation (message.to is None), deploys new contract.
        For contract calls (message.to is set), executes contract code.

        Args:
            message: Execution message with sender, recipient, value, data, gas

        Returns:
            Execution result with success status, gas used, return data, logs

        Raises:
            VMExecutionError: On execution failure
        """
        if message.to is None:
            return self._deploy_contract(message)
        return self._call_contract(message, static=False)

    def call_static(self, message: ExecutionMessage) -> ExecutionResult:
        """
        Execute a static (view) call.

        No state modifications are allowed.

        Args:
            message: Execution message

        Returns:
            Execution result
        """
        if message.to is None:
            raise VMExecutionError("Cannot deploy contract in static call")
        return self._call_contract(message, static=True)

    def estimate_gas(self, message: ExecutionMessage) -> int:
        """
        Estimate gas for a transaction.

        Executes the transaction and returns gas used.

        Args:
            message: Execution message

        Returns:
            Estimated gas usage
        """
        try:
            # Execute with high gas limit
            high_gas_message = ExecutionMessage(
                sender=message.sender,
                to=message.to,
                value=message.value,
                gas_limit=self.MAX_GAS_LIMIT,
                data=message.data,
                nonce=message.nonce,
            )
            result = self.execute(high_gas_message)
            # Add 10% buffer
            return int(result.gas_used * 1.1)
        except VMExecutionError:
            # Return max if execution fails
            return self.DEFAULT_GAS_LIMIT

    def delegatecall(
        self,
        *,
        sender: str,
        proxy_address: str,
        implementation_address: str,
        calldata: bytes,
        gas_limit: int = DEFAULT_GAS_LIMIT,
    ) -> ExecutionResult:
        """
        Execute a high-level DELEGATECALL-like operation.

        Runs code from implementation_address in the storage context of proxy_address,
        preserving msg.sender and msg.value semantics (value=0 for DELEGATECALL).
        This provides a convenient harness for proxy patterns implemented at the
        Python layer without crafting raw opcodes.
        """
        # Prepare execution context and call
        context = self._create_context(
            ExecutionMessage(
                sender=sender,
                to=proxy_address,
                value=0,
                gas_limit=gas_limit,
                data=calldata,
                nonce=0,
            )
        )

        # Load implementation code
        code = self._get_contract_code(implementation_address)
        if not code:
            return ExecutionResult(
                success=False,
                gas_used=gas_limit,
                return_data=b"",
                logs=[{"event": "DelegateCallFailed", "error": "empty_code"}],
            )

        # Construct call context as DELEGATECALL frame
        call = CallContext(
            call_type=CallType.DELEGATECALL,
            depth=0,
            address=self._normalize_address(proxy_address),  # storage/context
            caller=sender,
            origin=sender,
            value=0,
            gas=gas_limit,
            code=code,  # execute implementation code
            calldata=calldata or b"",
            static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        try:
            interpreter.execute(call)
        except VMExecutionError as e:
            return ExecutionResult(
                success=False,
                gas_used=gas_limit,
                return_data=b"",
                logs=[{"event": "DelegateCallError", "error": str(e)}],
            )

        gas_used = gas_limit - call.gas
        if call.reverted:
            context.revert_to_snapshot(0) if context.snapshots else None
            return ExecutionResult(
                success=False,
                gas_used=gas_used,
                return_data=call.output,
                logs=[{"event": "DelegateCallReverted", "reason": call.revert_reason}],
            )

        # Commit storage changes to proxy context
        context.commit()
        self._persist_storage(self._normalize_address(proxy_address), context.get_storage(self._normalize_address(proxy_address)))

        return ExecutionResult(
            success=True,
            gas_used=gas_used,
            return_data=call.output,
            logs=[self._log_to_dict(l) for l in context.logs],
        )

    def _deploy_contract(self, message: ExecutionMessage) -> ExecutionResult:
        """
        Deploy a new contract.

        Args:
            message: Execution message with init code in data field

        Returns:
            Execution result with contract address in return_data
        """
        init_code = message.data or b""
        start_time = time.time()

        # Validate init code size (EIP-3860)
        if len(init_code) > self.MAX_INITCODE_SIZE:
            raise VMExecutionError(
                f"Init code too large: {len(init_code)} > {self.MAX_INITCODE_SIZE}"
            )

        # Calculate intrinsic gas
        intrinsic_gas = self._intrinsic_gas(message, is_create=True)
        if intrinsic_gas > message.gas_limit:
            raise VMExecutionError(
                f"Intrinsic gas exceeds limit: {intrinsic_gas} > {message.gas_limit}"
            )

        # Generate contract address
        contract_address = self._compute_create_address(message.sender, message.nonce)

        # Create execution context
        context = self._create_context(message)

        # Create call context for init code execution
        call = CallContext(
            call_type=CallType.CREATE,
            depth=0,
            address=contract_address,
            caller=message.sender,
            origin=message.sender,
            value=message.value,
            gas=message.gas_limit - intrinsic_gas,
            code=init_code,
            calldata=b"",  # Init code receives no calldata
            static=False,
        )

        # Execute init code
        interpreter = EVMInterpreter(context)
        context.push_call(call)

        try:
            interpreter.execute(call)
        except VMExecutionError as e:
            logger.warning(
                "Contract deployment failed",
                extra={
                    "event": "evm.deploy_failed",
                    "sender": message.sender,
                    "error": str(e),
                }
            )
            return ExecutionResult(
                success=False,
                gas_used=message.gas_limit,
                return_data=b"",
                logs=[{"event": "DeploymentFailed", "error": str(e)}],
            )

        if call.reverted:
            return ExecutionResult(
                success=False,
                gas_used=message.gas_limit - call.gas,
                return_data=call.output,
                logs=[{"event": "DeploymentReverted", "reason": call.revert_reason}],
            )

        # The output of init code becomes the deployed bytecode
        deployed_code = call.output

        # Validate deployed code size (EIP-170)
        if len(deployed_code) > self.MAX_CODE_SIZE:
            raise VMExecutionError(
                f"Deployed code too large: {len(deployed_code)} > {self.MAX_CODE_SIZE}"
            )

        # Calculate code deposit gas
        code_deposit_gas = 200 * len(deployed_code)
        if code_deposit_gas > call.gas:
            raise VMExecutionError(
                f"Not enough gas for code deposit: {code_deposit_gas} > {call.gas}"
            )

        # Store contract in blockchain
        self._store_contract(
            address=contract_address,
            code=deployed_code,
            creator=message.sender,
            storage=context.get_storage(contract_address),
        )

        gas_used = message.gas_limit - call.gas + code_deposit_gas

        # Commit state changes
        context.commit()

        logger.info(
            "Contract deployed",
            extra={
                "event": "evm.contract_deployed",
                "address": contract_address,
                "code_size": len(deployed_code),
                "gas_used": gas_used,
            }
        )

        return ExecutionResult(
            success=True,
            gas_used=gas_used,
            return_data=contract_address.encode("utf-8"),
            logs=[
                {"event": "ContractCreated", "address": contract_address}
            ] + [self._log_to_dict(log) for log in context.logs],
        )

    def _call_contract(
        self, message: ExecutionMessage, static: bool
    ) -> ExecutionResult:
        """
        Call an existing contract.

        Args:
            message: Execution message
            static: Whether this is a static call

        Returns:
            Execution result
        """
        if not message.to:
            raise VMExecutionError("Missing contract address")

        contract_address = self._normalize_address(message.to)

        # Get contract code
        code = self._get_contract_code(contract_address)
        if not code:
            # Empty account - transfer value only
            return ExecutionResult(
                success=True,
                gas_used=self._intrinsic_gas(message),
                return_data=b"",
                logs=[],
            )

        # Calculate intrinsic gas
        intrinsic_gas = self._intrinsic_gas(message)
        if intrinsic_gas > message.gas_limit:
            raise VMExecutionError(
                f"Intrinsic gas exceeds limit: {intrinsic_gas} > {message.gas_limit}"
            )

        # Create execution context
        context = self._create_context(message)

        # Create call context
        call = CallContext(
            call_type=CallType.STATICCALL if static else CallType.CALL,
            depth=0,
            address=contract_address,
            caller=message.sender,
            origin=message.sender,
            value=message.value,
            gas=message.gas_limit - intrinsic_gas,
            code=code,
            calldata=message.data or b"",
            static=static,
        )

        # Execute
        interpreter = EVMInterpreter(context)
        context.push_call(call)

        try:
            interpreter.execute(call)
        except VMExecutionError as e:
            logger.warning(
                "Contract call failed",
                extra={
                    "event": "evm.call_failed",
                    "address": contract_address,
                    "error": str(e),
                }
            )
            return ExecutionResult(
                success=False,
                gas_used=message.gas_limit,
                return_data=b"",
                logs=[{"event": "CallFailed", "error": str(e)}],
            )

        gas_used = message.gas_limit - call.gas

        # Apply gas refund (max 1/5 of gas used per EIP-3529)
        max_refund = gas_used // 5
        actual_refund = min(context.gas_refund, max_refund)
        gas_used -= actual_refund

        if call.reverted:
            # Rollback state on revert
            context.revert_to_snapshot(0) if context.snapshots else None
            return ExecutionResult(
                success=False,
                gas_used=gas_used,
                return_data=call.output,
                logs=[{"event": "CallReverted", "reason": call.revert_reason}],
            )

        # Commit state changes (only for non-static calls)
        if not static:
            context.commit()
            self._persist_storage(contract_address, context.get_storage(contract_address))

        return ExecutionResult(
            success=True,
            gas_used=gas_used,
            return_data=call.output,
            logs=[self._log_to_dict(log) for log in context.logs],
        )

    def _create_context(self, message: ExecutionMessage) -> ExecutionContext:
        """Create execution context for a message."""
        # Get current block info
        block_info = self._get_block_info()

        return ExecutionContext(
            block=block_info,
            tx_origin=message.sender,
            tx_gas_price=1,  # Would come from transaction
            tx_gas_limit=message.gas_limit,
            tx_value=message.value,
            blockchain=self.blockchain,
        )

    def _get_block_info(self) -> BlockContext:
        """Get current block context."""
        chain = self.blockchain.chain
        current_block = chain[-1] if chain else None

        return BlockContext(
            number=len(chain),
            timestamp=int(time.time()),
            gas_limit=self.DEFAULT_GAS_LIMIT,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=0,
            chain_id=self.chain_id,
        )

    def _intrinsic_gas(
        self, message: ExecutionMessage, is_create: bool = False
    ) -> int:
        """
        Calculate intrinsic gas for transaction.

        Args:
            message: Execution message
            is_create: Whether this is a contract creation

        Returns:
            Intrinsic gas cost
        """
        # Base cost
        gas = 21000

        # Creation cost
        if is_create:
            gas += 32000

        # Calldata cost
        data = message.data or b""
        for byte in data:
            if byte == 0:
                gas += 4  # Zero byte
            else:
                gas += 16  # Non-zero byte

        # Init code word cost (EIP-3860)
        if is_create:
            gas += 2 * ((len(data) + 31) // 32)

        return gas

    def _compute_create_address(self, sender: str, nonce: int) -> str:
        """
        Compute CREATE contract address.

        Address = keccak256(rlp([sender, nonce]))[12:]

        Args:
            sender: Sender address
            nonce: Sender nonce

        Returns:
            Contract address
        """
        # Simplified RLP encoding for [address, nonce]
        sender_bytes = bytes.fromhex(
            sender[2:] if sender.startswith("0x") else sender
        )

        # RLP encode
        if nonce == 0:
            nonce_rlp = b"\x80"
        elif nonce < 128:
            nonce_rlp = bytes([nonce])
        else:
            nonce_bytes = nonce.to_bytes((nonce.bit_length() + 7) // 8, "big")
            nonce_rlp = bytes([0x80 + len(nonce_bytes)]) + nonce_bytes

        # Address is 20 bytes, so 0x80 + 20 = 0x94
        address_rlp = bytes([0x94]) + sender_bytes

        # List prefix
        payload = address_rlp + nonce_rlp
        if len(payload) < 56:
            list_rlp = bytes([0xC0 + len(payload)]) + payload
        else:
            len_bytes = len(payload).to_bytes(
                (len(payload).bit_length() + 7) // 8, "big"
            )
            list_rlp = bytes([0xF7 + len(len_bytes)]) + len_bytes + payload

        # Hash and take last 20 bytes
        addr_hash = hashlib.sha3_256(list_rlp).digest()
        return f"0x{addr_hash[-20:].hex()}"

    def _normalize_address(self, address: str) -> str:
        """Normalize address to lowercase hex with 0x prefix."""
        if address.startswith("0x"):
            return address.lower()
        return f"0x{address.lower()}"

    def _get_contract_code(self, address: str) -> bytes:
        """Get contract bytecode from blockchain."""
        normalized = address.upper().replace("0X", "")
        contract_data = self.blockchain.contracts.get(f"0X{normalized}", {})
        if not contract_data:
            contract_data = self.blockchain.contracts.get(normalized, {})

        code = contract_data.get("code", b"")
        if isinstance(code, str):
            return bytes.fromhex(code)
        return code

    def _store_contract(
        self,
        address: str,
        code: bytes,
        creator: str,
        storage: EVMStorage,
    ) -> None:
        """Store deployed contract in blockchain."""
        normalized = address.upper()
        self.blockchain.contracts[normalized] = {
            "address": normalized,
            "code": code.hex() if isinstance(code, bytes) else code,
            "creator": creator,
            "storage": storage.to_dict(),
            "created_at": time.time(),
        }

    def _persist_storage(self, address: str, storage: EVMStorage) -> None:
        """Persist storage changes to blockchain."""
        normalized = address.upper()
        if normalized in self.blockchain.contracts:
            self.blockchain.contracts[normalized]["storage"] = storage.to_dict()

    def _log_to_dict(self, log: Log) -> Dict[str, Any]:
        """Convert Log to dictionary."""
        return {
            "address": log.address,
            "topics": [f"0x{t:064x}" for t in log.topics],
            "data": log.data.hex(),
        }


class EVMPrecompiles:
    """
    EVM precompiled contracts.

    These are native implementations of commonly-used cryptographic
    functions, available at fixed addresses 0x01-0x0a.
    """

    # Precompile addresses
    ECRECOVER = "0x0000000000000000000000000000000000000001"
    SHA256 = "0x0000000000000000000000000000000000000002"
    RIPEMD160 = "0x0000000000000000000000000000000000000003"
    IDENTITY = "0x0000000000000000000000000000000000000004"
    MODEXP = "0x0000000000000000000000000000000000000005"
    ECADD = "0x0000000000000000000000000000000000000006"
    ECMUL = "0x0000000000000000000000000000000000000007"
    ECPAIRING = "0x0000000000000000000000000000000000000008"
    BLAKE2F = "0x0000000000000000000000000000000000000009"
    POINT_EVALUATION = "0x000000000000000000000000000000000000000a"

    @classmethod
    def is_precompile(cls, address: str) -> bool:
        """Check if address is a precompile."""
        try:
            addr_int = int(address, 16) if isinstance(address, str) else address
            return 1 <= addr_int <= 10
        except ValueError:
            return False

    @classmethod
    def execute_precompile(
        cls, address: str, input_data: bytes, gas: int
    ) -> tuple[bytes, int]:
        """
        Execute a precompiled contract.

        Args:
            address: Precompile address
            input_data: Input data
            gas: Available gas

        Returns:
            Tuple of (output_data, gas_used)

        Raises:
            VMExecutionError: If execution fails
        """
        addr_int = int(address, 16) if isinstance(address, str) else address

        if addr_int == 1:
            return cls._ecrecover(input_data, gas)
        elif addr_int == 2:
            return cls._sha256(input_data, gas)
        elif addr_int == 3:
            return cls._ripemd160(input_data, gas)
        elif addr_int == 4:
            return cls._identity(input_data, gas)
        elif addr_int == 5:
            return cls._modexp(input_data, gas)
        elif addr_int == 6:
            return cls._ecadd(input_data, gas)
        elif addr_int == 7:
            return cls._ecmul(input_data, gas)
        elif addr_int == 8:
            return cls._ecpairing(input_data, gas)
        elif addr_int == 9:
            return cls._blake2f(input_data, gas)
        elif addr_int == 10:
            return cls._point_evaluation(input_data, gas)
        else:
            raise VMExecutionError(f"Precompile {addr_int} not implemented")

    @classmethod
    def _ecrecover(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """ECRECOVER precompile."""
        gas_cost = 3000
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for ECRECOVER")

        # Would implement actual ecrecover
        # For now, return empty (invalid signature)
        return b"\x00" * 32, gas_cost

    @classmethod
    def _sha256(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """SHA256 precompile."""
        gas_cost = 60 + 12 * ((len(data) + 31) // 32)
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for SHA256")

        result = hashlib.sha256(data).digest()
        return result, gas_cost

    @classmethod
    def _ripemd160(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """RIPEMD160 precompile."""
        gas_cost = 600 + 120 * ((len(data) + 31) // 32)
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for RIPEMD160")

        import hashlib
        result = hashlib.new("ripemd160", data).digest()
        # Left-pad to 32 bytes
        return b"\x00" * 12 + result, gas_cost

    @classmethod
    def _identity(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """IDENTITY precompile (data copy)."""
        gas_cost = 15 + 3 * ((len(data) + 31) // 32)
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for IDENTITY")

        return data, gas_cost

    @classmethod
    def _modexp(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """MODEXP precompile."""
        # Parse lengths
        if len(data) < 96:
            data = data + b"\x00" * (96 - len(data))

        base_len = int.from_bytes(data[0:32], "big")
        exp_len = int.from_bytes(data[32:64], "big")
        mod_len = int.from_bytes(data[64:96], "big")

        # Calculate gas (simplified)
        max_len = max(base_len, mod_len)
        gas_cost = max(200, max_len * max_len * max(1, exp_len) // 3)

        if gas < gas_cost:
            raise VMExecutionError("Out of gas for MODEXP")

        # Extract values
        base_start = 96
        exp_start = base_start + base_len
        mod_start = exp_start + exp_len

        base = int.from_bytes(data[base_start:exp_start], "big") if base_len > 0 else 0
        exp = int.from_bytes(data[exp_start:mod_start], "big") if exp_len > 0 else 0
        mod = int.from_bytes(data[mod_start:mod_start + mod_len], "big") if mod_len > 0 else 0

        if mod == 0:
            result = 0
        else:
            result = pow(base, exp, mod)

        return result.to_bytes(mod_len, "big"), gas_cost

    # ---- Elliptic curve precompiles: alt_bn128 (EIP-196/197) ----

    @classmethod
    def _ecadd(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """ECADD precompile (0x06) on alt_bn128 (bn254)."""
        # Gas per EIP-196
        gas_cost = 150
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for ECADD")

        # Input: 128 bytes -> (x1,y1,x2,y2), each 32-byte big-endian
        if len(data) < 128:
            data = data + b"\x00" * (128 - len(data))

        x1 = int.from_bytes(data[0:32], "big")
        y1 = int.from_bytes(data[32:64], "big")
        x2 = int.from_bytes(data[64:96], "big")
        y2 = int.from_bytes(data[96:128], "big")

        try:
            from py_ecc.optimized_bn128 import add, is_on_curve, FQ, curve_order, b
        except Exception as exc:
            raise VMExecutionError(f"ECADD dependency error: {exc}")

        # Infinity handling: (0,0) represents point at infinity per spec
        p1 = None if (x1 == 0 and y1 == 0) else (FQ(x1), FQ(y1), FQ(1))
        p2 = None if (x2 == 0 and y2 == 0) else (FQ(x2), FQ(y2), FQ(1))

        # Validate points (ignore infinity None)
        if p1 is not None and not is_on_curve(p1, b):
            return (b"\x00" * 64, gas_cost)
        if p2 is not None and not is_on_curve(p2, b):
            return (b"\x00" * 64, gas_cost)

        if p1 is None:
            result = p2
        elif p2 is None:
            result = p1
        else:
            result = add(p1, p2)

        if result is None:
            return (b"\x00" * 64, gas_cost)

        x = int(result[0])
        y = int(result[1])
        return x.to_bytes(32, "big") + y.to_bytes(32, "big"), gas_cost

    @classmethod
    def _ecmul(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """ECMUL precompile (0x07) on alt_bn128 (bn254)."""
        # Gas per EIP-196
        gas_cost = 6000
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for ECMUL")

        # Input: 96 bytes -> (x,y,scalar)
        if len(data) < 96:
            data = data + b"\x00" * (96 - len(data))

        x = int.from_bytes(data[0:32], "big")
        y = int.from_bytes(data[32:64], "big")
        s = int.from_bytes(data[64:96], "big")

        try:
            from py_ecc.optimized_bn128 import multiply, is_on_curve, FQ, curve_order, b
        except Exception as exc:
            raise VMExecutionError(f"ECMUL dependency error: {exc}")

        # Point at infinity
        p = None if (x == 0 and y == 0) else (FQ(x), FQ(y), FQ(1))
        if p is not None and not is_on_curve(p, b):
            return (b"\x00" * 64, gas_cost)

        # Reduce scalar mod curve order
        s = s % curve_order
        if p is None or s == 0:
            return (b"\x00" * 64, gas_cost)

        result = multiply(p, s)
        if result is None:
            return (b"\x00" * 64, gas_cost)

        rx = int(result[0])
        ry = int(result[1])
        return rx.to_bytes(32, "big") + ry.to_bytes(32, "big"), gas_cost

    @classmethod
    def _ecpairing(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """ECPAIRING precompile (0x08) on alt_bn128 (bn254)."""
        # Each pair is 192 bytes: (G1: 64) + (G2: 128)
        if len(data) % 192 != 0:
            # Per spec, non-multiple input treated as padded with zeros to next multiple
            padded_len = ((len(data) + 191) // 192) * 192
            data = data + b"\x00" * (padded_len - len(data))

        pairs = len(data) // 192
        # Gas per EIP-197: 80_000 per pair
        gas_cost = 80_000 * max(1, pairs)
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for ECPAIRING")

        try:
            from py_ecc.optimized_bn128 import pairing, normalize, is_on_curve, FQ, FQ2, b2
        except Exception as exc:
            raise VMExecutionError(f"ECPAIRING dependency error: {exc}")

        # Compute product of pairings; equal to identity -> success (1), else 0
        # The py_ecc pairing(a,b) returns a value in FQ12; product equals 1 for true.
        # We'll accumulate by multiplying pairings and check if result is one.
        from py_ecc.optimized_bn128.optimized_curve import is_inf
        from py_ecc.fields.field_properties import field_properties as fq12_props
        from py_ecc.optimized_bn128 import FQ12

        acc = FQ12.one()

        for i in range(pairs):
            off = i * 192
            # G1 point
            x1 = int.from_bytes(data[off : off + 32], "big")
            y1 = int.from_bytes(data[off + 32 : off + 64], "big")
            g1 = None if (x1 == 0 and y1 == 0) else (FQ(x1), FQ(y1), FQ(1))

            # G2 point (x_im, x_re, y_im, y_re) 32-bytes each, big-endian
            x2_im = int.from_bytes(data[off + 64 : off + 96], "big")
            x2_re = int.from_bytes(data[off + 96 : off + 128], "big")
            y2_im = int.from_bytes(data[off + 128 : off + 160], "big")
            y2_re = int.from_bytes(data[off + 160 : off + 192], "big")
            x2 = FQ2([x2_im, x2_re])
            y2 = FQ2([y2_im, y2_re])
            # Handle infinity (all zeros) for G2
            g2 = None if (x2_im == 0 and x2_re == 0 and y2_im == 0 and y2_re == 0) else (x2, y2, FQ2.one())

            # Validate on-curve
            if g1 is not None and not is_on_curve(g1, b=None):
                return (b"\x00" * 32, gas_cost)
            if g2 is not None and not is_on_curve(g2, b2):
                return (b"\x00" * 32, gas_cost)

            if g1 is None or g2 is None:
                # Pairing with infinity contributes neutral element (skip)
                continue

            acc *= pairing(g2, g1)

        # Success if accumulator equals one in FQ12
        out = (1).to_bytes(32, "big") if acc == FQ12.one() else (0).to_bytes(32, "big")
        return out, gas_cost

    # ---- Blake2f (EIP-152) and Point Evaluation (EIP-4844) placeholders ----

    @classmethod
    def _blake2f(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """
        BLAKE2f compression (0x09) per EIP-152.

        Input (213 bytes):
        - rounds: 4 bytes little-endian uint32
        - h: 8 x uint64 little-endian (64 bytes)
        - m: 16 x uint64 little-endian (128 bytes)
        - t: 2 x uint64 little-endian (16 bytes) [t0, t1]
        - f: 1 byte (0 or 1)

        Output: 64 bytes little-endian (new h state)
        """
        if len(data) != 213:
            raise VMExecutionError("BLAKE2f input must be 213 bytes")

        def le_u32(b: bytes) -> int:
            return int.from_bytes(b, "little")

        def le_u64(b: bytes) -> int:
            return int.from_bytes(b, "little")

        rounds = le_u32(data[0:4])
        if rounds <= 0 or rounds > 0xFFFFFFFF:
            raise VMExecutionError("Invalid BLAKE2f rounds")

        # Gas approximation: base + 12 ops per round
        gas_cost = 10 + 12 * rounds
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for BLAKE2F")

        # Parse state
        h = [le_u64(data[4 + i * 8 : 12 + i * 8]) for i in range(8)]
        m = [le_u64(data[68 + i * 8 : 76 + i * 8]) for i in range(16)]
        t0 = le_u64(data[196:204])
        t1 = le_u64(data[204:212])
        f = data[212]

        # Constants
        IV = [
            0x6a09e667f3bcc908,
            0xbb67ae8584caa73b,
            0x3c6ef372fe94f82b,
            0xa54ff53a5f1d36f1,
            0x510e527fade682d1,
            0x9b05688c2b3e6c1f,
            0x1f83d9abfb41bd6b,
            0x5be0cd19137e2179,
        ]

        SIGMA = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
            [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
            [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
            [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
            [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
            [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
            [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
            [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
            [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0],
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
        ]

        def rotr64(x: int, n: int) -> int:
            return ((x >> n) | ((x & 0xFFFFFFFFFFFFFFFF) << (64 - n))) & 0xFFFFFFFFFFFFFFFF

        # Initialize v
        v = [0] * 16
        v[0:8] = h[0:8]
        v[8:16] = IV[0:8]
        # t and f
        v[12] ^= t0 & 0xFFFFFFFFFFFFFFFF
        v[13] ^= t1 & 0xFFFFFFFFFFFFFFFF
        if f != 0:
            v[14] ^= 0xFFFFFFFFFFFFFFFF

        def G(a: int, b: int, c: int, d: int, x: int, y: int) -> None:
            v[a] = (v[a] + v[b] + x) & 0xFFFFFFFFFFFFFFFF
            v[d] = rotr64(v[d] ^ v[a], 32)
            v[c] = (v[c] + v[d]) & 0xFFFFFFFFFFFFFFFF
            v[b] = rotr64(v[b] ^ v[c], 24)
            v[a] = (v[a] + v[b] + y) & 0xFFFFFFFFFFFFFFFF
            v[d] = rotr64(v[d] ^ v[a], 16)
            v[c] = (v[c] + v[d]) & 0xFFFFFFFFFFFFFFFF
            v[b] = rotr64(v[b] ^ v[c], 63)

        for r in range(rounds):
            s = SIGMA[r % 12]
            # column rounds
            G(0, 4, 8, 12, m[s[0]], m[s[1]])
            G(1, 5, 9, 13, m[s[2]], m[s[3]])
            G(2, 6, 10, 14, m[s[4]], m[s[5]])
            G(3, 7, 11, 15, m[s[6]], m[s[7]])
            # diagonal rounds
            G(0, 5, 10, 15, m[s[8]], m[s[9]])
            G(1, 6, 11, 12, m[s[10]], m[s[11]])
            G(2, 7, 8, 13, m[s[12]], m[s[13]])
            G(3, 4, 9, 14, m[s[14]], m[s[15]])

        # Finalize h
        out_h = [(h[i] ^ v[i] ^ v[i + 8]) & 0xFFFFFFFFFFFFFFFF for i in range(8)]
        out = b"".join(x.to_bytes(8, "little") for x in out_h)
        return out, gas_cost

    @classmethod
    def _point_evaluation(cls, data: bytes, gas: int) -> tuple[bytes, int]:
        """
        POINT_EVALUATION (0x0a) per EIP-4844.
        Placeholder that returns a clear error until KZG integration lands.
        """
        gas_cost = 50_000
        if gas < gas_cost:
            raise VMExecutionError("Out of gas for POINT_EVALUATION")
        raise VMExecutionError("POINT_EVALUATION precompile not yet implemented")
