"""
EVM Execution Context.

The execution context contains all information needed to execute a contract,
including caller information, call data, gas tracking, and state access.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING
from enum import Enum

from .memory import EVMMemory
from .stack import EVMStack
from .storage import EVMStorage, TransientStorage

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class CallType(Enum):
    """Type of contract call."""

    CALL = "CALL"
    CALLCODE = "CALLCODE"
    DELEGATECALL = "DELEGATECALL"
    STATICCALL = "STATICCALL"
    CREATE = "CREATE"
    CREATE2 = "CREATE2"


@dataclass
class Log:
    """EVM log entry (event)."""

    address: str
    topics: List[int]
    data: bytes


@dataclass
class CallContext:
    """
    Context for a single contract call.

    This represents one frame in the call stack, containing:
    - Code being executed
    - Memory (local to this call)
    - Stack (local to this call)
    - Gas available
    - Call parameters
    """

    # Call identification
    call_type: CallType
    depth: int

    # Addresses
    address: str  # Contract being executed
    caller: str  # Immediate caller
    origin: str  # Transaction originator

    # Value transfer
    value: int  # Wei sent with call
    gas: int  # Gas available

    # Code and data
    code: bytes  # Bytecode being executed
    calldata: bytes  # Input data

    # Execution state
    pc: int = 0  # Program counter
    stack: EVMStack = field(default_factory=EVMStack)
    memory: EVMMemory = field(default_factory=EVMMemory)
    return_data: bytes = b""  # Return data from last call

    # Static mode (no state modifications)
    static: bool = False

    # Output
    output: bytes = b""
    logs: List[Log] = field(default_factory=list)

    # Execution status
    halted: bool = False
    reverted: bool = False
    revert_reason: str = ""

    def use_gas(self, amount: int) -> bool:
        """
        Consume gas from available gas.

        Args:
            amount: Gas to consume

        Returns:
            True if gas available, False if out of gas
        """
        if amount > self.gas:
            return False
        self.gas -= amount
        return True

    def refund_gas(self, amount: int) -> None:
        """
        Refund gas (limited by rules).

        Args:
            amount: Gas to refund
        """
        self.gas += amount

    @property
    def remaining_gas(self) -> int:
        """Get remaining gas."""
        return self.gas


@dataclass
class BlockContext:
    """
    Block-level context information.

    Contains information about the block being processed,
    used by opcodes like TIMESTAMP, NUMBER, etc.
    """

    number: int  # Block number
    timestamp: int  # Block timestamp
    gas_limit: int  # Block gas limit
    coinbase: str  # Miner/validator address
    prevrandao: int  # Previous randao (was difficulty pre-merge)
    base_fee: int  # EIP-1559 base fee
    chain_id: int  # Chain ID (EIP-155)
    blob_base_fee: int = 0  # EIP-4844 blob base fee

    def get_block_hash(self, block_number: int) -> int:
        """
        Get hash of a recent block.

        Only last 256 blocks available.

        Args:
            block_number: Block number to get hash for

        Returns:
            Block hash as 256-bit integer, or 0 if not available
        """
        # Will be implemented via blockchain reference
        return 0


@dataclass
class ExecutionContext:
    """
    Full execution context for EVM execution.

    This is the top-level context containing:
    - All call contexts (call stack)
    - Persistent storage access
    - Block context
    - Transaction-level state
    """

    # Block information
    block: BlockContext

    # Transaction information
    tx_origin: str  # Transaction sender
    tx_gas_price: int  # Gas price
    tx_gas_limit: int  # Transaction gas limit
    tx_value: int  # Value sent

    # Blockchain reference
    blockchain: Optional["Blockchain"] = None

    # Call stack
    call_stack: List[CallContext] = field(default_factory=list)
    max_call_depth: int = 1024

    # Storage (contract address -> storage)
    storage: Dict[str, EVMStorage] = field(default_factory=dict)
    transient_storage: TransientStorage = field(default_factory=TransientStorage)

    # Account state changes
    balance_changes: Dict[str, int] = field(default_factory=dict)
    created_accounts: Set[str] = field(default_factory=set)
    destroyed_accounts: Set[str] = field(default_factory=set)

    # Gas accounting
    gas_used: int = 0
    gas_refund: int = 0

    # Logs (events)
    logs: List[Log] = field(default_factory=list)

    # Access lists (EIP-2929)
    accessed_addresses: Set[str] = field(default_factory=set)
    accessed_storage_keys: Dict[str, Set[int]] = field(default_factory=dict)

    # State snapshots for revert
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def current_call(self) -> Optional[CallContext]:
        """Get current call context."""
        return self.call_stack[-1] if self.call_stack else None

    @property
    def call_depth(self) -> int:
        """Get current call depth."""
        return len(self.call_stack)

    def push_call(self, call: CallContext) -> bool:
        """
        Push a new call onto the stack.

        Args:
            call: Call context to push

        Returns:
            True if pushed, False if max depth exceeded
        """
        if len(self.call_stack) >= self.max_call_depth:
            return False
        self.call_stack.append(call)
        return True

    def pop_call(self) -> Optional[CallContext]:
        """
        Pop the current call from the stack.

        Returns:
            Popped call context, or None if stack empty
        """
        if self.call_stack:
            return self.call_stack.pop()
        return None

    def get_storage(self, address: str) -> EVMStorage:
        """
        Get or create storage for a contract.

        Args:
            address: Contract address

        Returns:
            Storage instance for the contract
        """
        if address not in self.storage:
            self.storage[address] = EVMStorage(address=address)
            # Load from blockchain if available
            if self.blockchain:
                self._load_storage_from_chain(address)
        return self.storage[address]

    def _load_storage_from_chain(self, address: str) -> None:
        """Load storage from blockchain."""
        if not self.blockchain:
            return

        contract_data = self.blockchain.contracts.get(address.upper(), {})
        storage_data = contract_data.get("storage", {})

        storage = self.storage[address]
        for key, value in storage_data.items():
            if isinstance(key, str):
                key = int(key, 16) if key.startswith("0x") else int(key)
            storage.set_raw(key, value)

    def get_balance(self, address: str) -> int:
        """
        Get account balance.

        Args:
            address: Account address

        Returns:
            Balance in wei
        """
        # Check pending changes first
        if address in self.balance_changes:
            return self.balance_changes[address]

        # Fall back to blockchain
        if self.blockchain:
            return int(self.blockchain.get_balance(address))
        return 0

    def set_balance(self, address: str, balance: int) -> None:
        """
        Set account balance.

        Args:
            address: Account address
            balance: New balance
        """
        self.balance_changes[address] = balance

    def transfer(self, sender: str, recipient: str, amount: int) -> bool:
        """
        Transfer value between accounts.

        Args:
            sender: Sender address
            recipient: Recipient address
            amount: Amount to transfer

        Returns:
            True if transfer successful, False if insufficient balance
        """
        sender_balance = self.get_balance(sender)
        if sender_balance < amount:
            return False

        self.set_balance(sender, sender_balance - amount)
        self.set_balance(recipient, self.get_balance(recipient) + amount)
        return True

    def get_code(self, address: str) -> bytes:
        """
        Get contract code.

        Args:
            address: Contract address

        Returns:
            Contract bytecode
        """
        if self.blockchain:
            contract_data = self.blockchain.contracts.get(address.upper(), {})
            code = contract_data.get("code", b"")
            if isinstance(code, str):
                return bytes.fromhex(code)
            return code
        return b""

    def get_code_hash(self, address: str) -> int:
        """
        Get hash of contract code.

        Args:
            address: Contract address

        Returns:
            Keccak256 hash of code as integer
        """
        import hashlib

        code = self.get_code(address)
        if not code:
            # Empty account has specific hash
            return 0xC5D2460186F7233C927E7DB2DCC703C0E500B653CA82273B7BFAD8045D85A470
        return int.from_bytes(hashlib.sha3_256(code).digest(), "big")

    def set_code(self, address: str, code: bytes) -> None:
        """
        Set contract code.

        Args:
            address: Contract address
            code: Bytecode to set
        """
        if self.blockchain:
            normalized = address.upper()
            if normalized not in self.blockchain.contracts:
                self.blockchain.contracts[normalized] = {}
            # Convert bytes to hex string for storage
            self.blockchain.contracts[normalized]["code"] = code.hex() if code else ""
            self.created_accounts.add(address)

    def get_nonce(self, address: str) -> int:
        """
        Get account nonce.

        Args:
            address: Account address

        Returns:
            Current nonce
        """
        if self.blockchain:
            return self.blockchain.nonce_tracker.get_nonce(address)
        return 0

    def increment_nonce(self, address: str) -> None:
        """
        Increment account nonce.

        Args:
            address: Account address
        """
        if self.blockchain:
            current = self.blockchain.nonce_tracker.get_nonce(address)
            self.blockchain.nonce_tracker.set_nonce(address, current + 1)

    def warm_address(self, address: str) -> int:
        """
        Warm an address (EIP-2929).

        Args:
            address: Address to warm

        Returns:
            Gas cost (2600 if cold, 0 if already warm)
        """
        if address in self.accessed_addresses:
            return 0
        self.accessed_addresses.add(address)
        return 2600

    def warm_storage_key(self, address: str, key: int) -> int:
        """
        Warm a storage key (EIP-2929).

        Args:
            address: Contract address
            key: Storage key

        Returns:
            Gas cost (2100 if cold, 0 if already warm)
        """
        if address not in self.accessed_storage_keys:
            self.accessed_storage_keys[address] = set()

        if key in self.accessed_storage_keys[address]:
            return 0

        self.accessed_storage_keys[address].add(key)
        return 2100

    def is_warm_address(self, address: str) -> bool:
        """Check if address is warm."""
        return address in self.accessed_addresses

    def is_warm_storage(self, address: str, key: int) -> bool:
        """Check if storage key is warm."""
        return (
            address in self.accessed_storage_keys
            and key in self.accessed_storage_keys[address]
        )

    def take_snapshot(self) -> int:
        """
        Take a state snapshot for potential revert.

        Returns:
            Snapshot ID
        """
        snapshot = {
            "balance_changes": dict(self.balance_changes),
            "created_accounts": set(self.created_accounts),
            "destroyed_accounts": set(self.destroyed_accounts),
            "storage_snapshots": {
                addr: dict(storage._slots)
                for addr, storage in self.storage.items()
            },
            "logs_count": len(self.logs),
            "gas_refund": self.gas_refund,
        }
        self.snapshots.append(snapshot)
        return len(self.snapshots) - 1

    def revert_to_snapshot(self, snapshot_id: int) -> None:
        """
        Revert state to a snapshot.

        Args:
            snapshot_id: Snapshot to revert to
        """
        if snapshot_id >= len(self.snapshots):
            return

        snapshot = self.snapshots[snapshot_id]
        self.balance_changes = dict(snapshot["balance_changes"])
        self.created_accounts = set(snapshot["created_accounts"])
        self.destroyed_accounts = set(snapshot["destroyed_accounts"])
        self.gas_refund = snapshot["gas_refund"]

        # Truncate logs
        self.logs = self.logs[: snapshot["logs_count"]]

        # Discard newer snapshots
        self.snapshots = self.snapshots[:snapshot_id]

    def commit(self) -> None:
        """Commit all state changes to blockchain."""
        # Storage commits
        for addr, storage in self.storage.items():
            storage.commit()

        # Clear transient storage
        self.transient_storage.clear()

        # Clear snapshots
        self.snapshots.clear()

    def add_log(self, log: Log) -> None:
        """
        Add a log entry.

        Args:
            log: Log to add
        """
        self.logs.append(log)
        if self.current_call:
            self.current_call.logs.append(log)
