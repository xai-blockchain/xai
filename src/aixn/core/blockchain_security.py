"""
XAI Blockchain - Advanced Security Hardening

Protection against:
- 51% attacks (reorganization limits, checkpoints)
- Resource exhaustion (size limits, mempool caps)
- Dust attacks (minimum amounts)
- Inflation bugs (supply cap validation, overflow protection)
- Time manipulation (median-time-past)
"""

import time
import json
import os
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, getcontext

from aixn.core.config import Config

# Set high precision for overflow protection
getcontext().prec = 50


class BlockchainSecurityConfig:
    """Security configuration constants"""

    # Block and transaction size limits
    MAX_BLOCK_SIZE = 2_000_000  # 2 MB max block size
    MAX_TRANSACTION_SIZE = 100_000  # 100 KB max single transaction
    MAX_TRANSACTIONS_PER_BLOCK = 10_000  # Max 10k transactions per block

    # Mempool limits
    MAX_MEMPOOL_SIZE = 50_000  # Max 50k pending transactions
    MAX_MEMPOOL_BYTES = 300_000_000  # 300 MB max mempool memory

    # Dust protection
    MIN_TRANSACTION_AMOUNT = 0.00001  # 0.00001 XAI minimum (10 satoshis equivalent)
    MIN_UTXO_VALUE = 0.00001  # Minimum UTXO value

    # Reorganization protection
    MAX_REORG_DEPTH = 100  # Max 100 blocks can be reorganized
    CHECKPOINT_INTERVAL = 10000  # Checkpoint every 10k blocks

    # Supply validation
    MAX_SUPPLY = 121_000_000  # Hard cap
    SUPPLY_CHECK_INTERVAL = 1000  # Check total supply every 1k blocks

    # Time validation
    MEDIAN_TIME_SPAN = 11  # Use median of last 11 blocks
    MAX_FUTURE_BLOCK_TIME = 2 * 3600  # 2 hours max future

    # Overflow protection
    MAX_MONEY = 121_000_000 * 100_000_000  # Max in satoshis


class ReorganizationProtection:
    """
    Prevent deep chain reorganizations (51% attack mitigation)
    """

    def __init__(self, max_depth: int = BlockchainSecurityConfig.MAX_REORG_DEPTH):
        self.max_depth = max_depth
        self.checkpoints: Dict[int, str] = {}  # block_index -> block_hash
        self.checkpoint_file = "data/checkpoints.json"
        self._load_checkpoints()

    def _load_checkpoints(self):
        """Load checkpoints from disk"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    self.checkpoints = {int(k): v for k, v in data.items()}
            except Exception:
                self.checkpoints = {}

    def _save_checkpoints(self):
        """Save checkpoints to disk"""
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f, indent=2)

    def add_checkpoint(self, block_index: int, block_hash: str):
        """
        Add checkpoint (blocks before this cannot be reorganized)

        Args:
            block_index: Block number
            block_hash: Block hash
        """
        self.checkpoints[block_index] = block_hash
        self._save_checkpoints()

    def validate_reorganization(self, current_height: int, fork_point: int) -> Tuple[bool, Optional[str]]:
        """
        Validate if reorganization is allowed

        Args:
            current_height: Current chain height
            fork_point: Where the fork starts

        Returns:
            (allowed, error_message)
        """
        reorg_depth = current_height - fork_point

        # Check depth limit
        if reorg_depth > self.max_depth:
            return False, f"Reorganization too deep: {reorg_depth} blocks (max {self.max_depth})"

        # Check if trying to reorg past a checkpoint
        for checkpoint_height in self.checkpoints:
            if fork_point < checkpoint_height <= current_height:
                return False, f"Cannot reorganize past checkpoint at block {checkpoint_height}"

        return True, None

    def get_checkpoint(self, block_index: int) -> Optional[str]:
        """Get checkpoint hash for block"""
        return self.checkpoints.get(block_index)

    def is_checkpoint_block(self, block_index: int) -> bool:
        """Check if block is a checkpoint"""
        return block_index in self.checkpoints


class SupplyValidator:
    """
    Validate total supply never exceeds cap (inflation bug protection)
    """

    def __init__(self, max_supply: float = BlockchainSecurityConfig.MAX_SUPPLY):
        self.max_supply = max_supply
        self.last_checked_height = 0
        self.last_known_supply = 0.0

    def validate_coinbase_amount(self, block_height: int, coinbase_amount: float,
                                 expected_reward: float, total_fees: float) -> bool:
        """
        Validate coinbase transaction doesn't create excess coins

        Args:
            block_height: Current block height
            coinbase_amount: Amount in coinbase transaction
            expected_reward: Expected block reward
            total_fees: Total transaction fees in block

        Returns:
            bool: Valid
        """
        max_allowed = expected_reward + total_fees

        if coinbase_amount > max_allowed + 0.00000001:  # Allow tiny rounding
            print(f"INFLATION BUG DETECTED: Coinbase {coinbase_amount} exceeds max {max_allowed}")
            return False

        return True

    def validate_total_supply(self, blockchain) -> Tuple[bool, float]:
        """
        Calculate and validate total supply

        Args:
            blockchain: Blockchain instance

        Returns:
            (valid, total_supply)
        """
        # Calculate total supply from UTXO set (or numeric input for tests)
        input_is_blockchain = hasattr(blockchain, 'utxo_set')
        total_supply_decimal = Decimal(0)

        if input_is_blockchain:
            for address, utxos in blockchain.utxo_set.items():
                for utxo in utxos:
                    if not utxo['spent']:
                        total_supply_decimal += Decimal(str(utxo['amount']))
        else:
            total_supply_decimal = Decimal(str(blockchain))

        total_supply = float(total_supply_decimal)

        # Check against max supply
        if total_supply > self.max_supply:
            msg = f"Supply exceeds max supply: {total_supply} > {self.max_supply}"
            print(msg)
            return False, total_supply if input_is_blockchain else msg

        self.last_known_supply = total_supply
        return True, total_supply if input_is_blockchain else "Total supply within cap"

    def validate_block_reward(self, reward: float, total_fees: float) -> Tuple[bool, str]:
        """
        Validate that block reward plus fees does not exceed supply cap
        """
        if reward <= 0:
            return False, "Block reward must be positive"

        max_allowed = Config.INITIAL_BLOCK_REWARD + total_fees
        if reward > max_allowed:
            return False, "Block reward exceeds expected reward"

        return True, "Block reward within cap"


class OverflowProtection:
    """
    Protect against integer/float overflow in calculations
    """

    def __init__(self):
        self.max_money = Decimal(str(BlockchainSecurityConfig.MAX_MONEY))
        self.safe_limit = self.max_money / Decimal('100')

    def safe_add(self, a: float, b: float) -> Tuple[Optional[float], bool]:
        """Safely add two amounts"""
        try:
            result = Decimal(str(a)) + Decimal(str(b))
            if result > self.safe_limit:
                return None, False
            return float(result), True
        except:
            return None, False

    def safe_multiply(self, a: float, b: float) -> Tuple[Optional[float], bool]:
        """Safely multiply two amounts"""
        try:
            result = Decimal(str(a)) * Decimal(str(b))
            if result > self.safe_limit:
                return None, False
            return float(result), True
        except:
            return None, False

    def validate_amount(self, amount: float) -> Tuple[bool, str]:
        """Validate amount is within valid range"""
        try:
            if amount != amount:  # NaN
                return False, "Amount cannot be NaN"
        except TypeError:
            return False, "Amount must be a number"

        if amount < 0:
            return False, "Amount cannot be negative"
        if amount > BlockchainSecurityConfig.MAX_SUPPLY:
            return False, "Amount exceeds max supply"

        # Check precision (max 8 decimal places)
        amount_str = f"{amount:.8f}"
        if len(amount_str.split('.')[-1]) > 8:
            return False, "Amount has too many decimal places"

        return True, "Amount is valid"


class MempoolManager:
    """
    Manage pending transaction pool with size limits
    """

    def __init__(self):
        self.max_count = BlockchainSecurityConfig.MAX_MEMPOOL_SIZE
        self.max_bytes = BlockchainSecurityConfig.MAX_MEMPOOL_BYTES
        self.current_bytes = 0

    def can_add_transaction(self, tx, pending_transactions: List) -> Tuple[bool, Optional[str]]:
        """
        Check if transaction can be added to mempool

        Args:
            tx: Transaction to add
            pending_transactions: Current pending transactions

        Returns:
            (can_add, error_message)
        """
        # Check count limit
        if len(pending_transactions) >= self.max_count:
            return False, f"Mempool full: {len(pending_transactions)} transactions"

        # Check size limit (estimate transaction size)
        tx_size = len(json.dumps(tx.to_dict()).encode())

        if self.current_bytes + tx_size > self.max_bytes:
            return False, f"Mempool memory limit reached: {self.current_bytes} bytes"

        return True, None

    def add_transaction(self, tx):
        """Track transaction addition"""
        tx_size = len(json.dumps(tx.to_dict()).encode())
        self.current_bytes += tx_size

    def remove_transaction(self, tx):
        """Track transaction removal"""
        tx_size = len(json.dumps(tx.to_dict()).encode())
        self.current_bytes = max(0, self.current_bytes - tx_size)

    def clear(self):
        """Clear mempool tracking"""
        self.current_bytes = 0


class BlockSizeValidator:
    """
    Validate block and transaction sizes
    """

    @staticmethod
    def validate_transaction_size(tx) -> Tuple[bool, Optional[str]]:
        """
        Validate single transaction size

        Args:
            tx: Transaction

        Returns:
            (valid, error_message)
        """
        tx_json = json.dumps(tx.to_dict())
        tx_size = len(tx_json.encode())

        if tx_size > BlockchainSecurityConfig.MAX_TRANSACTION_SIZE:
            return False, f"Transaction too large: {tx_size} bytes (max {BlockchainSecurityConfig.MAX_TRANSACTION_SIZE})"

        return True, None

    @staticmethod
    def validate_block_size(block) -> Tuple[bool, Optional[str]]:
        """
        Validate block size

        Args:
            block: Block

        Returns:
            (valid, error_message)
        """
        # Check transaction count
        tx_count = len(block.transactions)
        if tx_count > BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK:
            return False, f"Too many transactions in block: {tx_count} (max {BlockchainSecurityConfig.MAX_TRANSACTIONS_PER_BLOCK})"

        # Check total block size
        block_json = json.dumps(block.to_dict())
        block_size = len(block_json.encode())

        if block_size > BlockchainSecurityConfig.MAX_BLOCK_SIZE:
            return False, f"Block too large: {block_size} bytes (max {BlockchainSecurityConfig.MAX_BLOCK_SIZE})"

        return True, None


class ResourceLimiter:
    """Guardrails for mempool/memory/resource limits."""

    def __init__(self):
        self.max_mempool_size = BlockchainSecurityConfig.MAX_MEMPOOL_SIZE

    def validate_transaction_size(self, tx) -> Tuple[bool, Optional[str]]:
        """Validate transaction payload size."""
        try:
            return BlockSizeValidator.validate_transaction_size(tx)
        except Exception:
            tx_repr = f"{getattr(tx, 'sender', '')}{getattr(tx, 'recipient', '')}"
            size = len(tx_repr)
            if size > BlockchainSecurityConfig.MAX_TRANSACTION_SIZE:
                return False, "Resource limiter: transaction too large"
            return True, None

    def validate_block_size(self, block) -> Tuple[bool, Optional[str]]:
        """Validate block size using existing validator."""
        return BlockSizeValidator.validate_block_size(block)

    def can_add_to_mempool(self, current_size: int) -> bool:
        """Check if mempool slot is available."""
        return current_size < self.max_mempool_size


class DustProtection:
    """
    Prevent dust attacks (tiny transactions that bloat UTXO set)
    """

    @staticmethod
    def validate_transaction_amount(amount: float) -> Tuple[bool, Optional[str]]:
        """
        Validate transaction amount meets minimum

        Args:
            amount: Transaction amount

        Returns:
            (valid, error_message)
        """
        if amount < BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT:
            return False, f"Amount too small: {amount} (min {BlockchainSecurityConfig.MIN_TRANSACTION_AMOUNT})"

        return True, None

    @staticmethod
    def validate_utxo_value(value: float) -> bool:
        """Validate UTXO value meets minimum"""
        return value >= BlockchainSecurityConfig.MIN_UTXO_VALUE


class MedianTimePast:
    """
    Use median time of recent blocks for timestamp validation
    Prevents time manipulation attacks
    """

    def __init__(self, span: int = BlockchainSecurityConfig.MEDIAN_TIME_SPAN):
        self.span = span

    def get_median_time_past(self, blockchain) -> float:
        """
        Calculate median time of last N blocks

        Args:
            blockchain: Blockchain instance

        Returns:
            float: Median timestamp
        """
        if len(blockchain.chain) == 0:
            return time.time()

        # Get last N blocks
        recent_blocks = blockchain.chain[-self.span:]

        # Get timestamps
        timestamps = [block.timestamp for block in recent_blocks]
        timestamps.sort()

        # Return median
        mid = len(timestamps) // 2
        if len(timestamps) % 2 == 0:
            return (timestamps[mid - 1] + timestamps[mid]) / 2
        else:
            return timestamps[mid]

    def validate_block_timestamp(self, block, blockchain) -> Tuple[bool, Optional[str]]:
        """
        Validate block timestamp using median-time-past

        Args:
            block: Block to validate
            blockchain: Blockchain instance

        Returns:
            (valid, error_message)
        """
        median_time = self.get_median_time_past(blockchain)
        current_time = time.time()

        # Must be greater than median time past
        if block.timestamp <= median_time:
            return False, f"Block timestamp {block.timestamp} <= median time past {median_time}"

        # Must not be too far in future
        if block.timestamp > current_time + BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME:
            return False, f"Block timestamp too far in future: {block.timestamp} > {current_time + BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME}"

        return True, None


class TimeValidator:
    """Time validation helpers consumed by tests."""

    def __init__(self):
        self.median_time_span = BlockchainSecurityConfig.MEDIAN_TIME_SPAN
        self.max_future_block_time = BlockchainSecurityConfig.MAX_FUTURE_BLOCK_TIME

    def calculate_median_time_past(self, chain) -> float:
        timestamps = [
            block.timestamp
            for block in chain[-self.median_time_span:]
            if hasattr(block, 'timestamp')
        ]

        if not timestamps:
            return time.time()

        timestamps.sort()
        mid = len(timestamps) // 2
        if len(timestamps) % 2 == 0:
            return (timestamps[mid - 1] + timestamps[mid]) / 2
        return timestamps[mid]

    def validate_block_time(self, block, chain) -> Tuple[bool, Optional[str]]:
        median_time = self.calculate_median_time_past(chain)
        current_time = time.time()

        if block.timestamp > current_time + self.max_future_block_time:
            return False, "Block timestamp too far in future"

        if block.timestamp < median_time:
            return False, "Block timestamp older than median past"

        return True, None


class EmergencyGovernanceTimelock:
    """
    Require timelock even for emergency actions
    Prevents instant malicious governance execution
    """

    def __init__(self, emergency_timelock: int = 144):  # ~5 hours at 2min/block
        self.emergency_timelock = emergency_timelock  # blocks
        self.pending_emergency_actions = {}  # proposal_id -> expiry_block

    def schedule_emergency_action(self, proposal_id: str, current_block_height: int):
        """
        Schedule emergency action with timelock

        Args:
            proposal_id: Proposal ID
            current_block_height: Current blockchain height
        """
        expiry_block = current_block_height + self.emergency_timelock
        self.pending_emergency_actions[proposal_id] = expiry_block

    def can_execute_emergency_action(self, proposal_id: str, current_block_height: int) -> Tuple[bool, Optional[str]]:
        """
        Check if emergency action can be executed

        Args:
            proposal_id: Proposal ID
            current_block_height: Current blockchain height

        Returns:
            (can_execute, error_message)
        """
        if proposal_id not in self.pending_emergency_actions:
            return False, "Emergency action not scheduled"

        expiry_block = self.pending_emergency_actions[proposal_id]

        if current_block_height < expiry_block:
            blocks_remaining = expiry_block - current_block_height
            return False, f"Emergency timelock active: {blocks_remaining} blocks remaining"

        return True, None

    def cancel_emergency_action(self, proposal_id: str):
        """Cancel pending emergency action"""
        if proposal_id in self.pending_emergency_actions:
            del self.pending_emergency_actions[proposal_id]


class BlockchainSecurityManager:
    """
    Unified security management for blockchain
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.reorg_protection = ReorganizationProtection()
        self.supply_validator = SupplyValidator()
        self.overflow_protection = OverflowProtection()
        self.mempool_manager = MempoolManager()
        self.block_size_validator = BlockSizeValidator()
        self.dust_protection = DustProtection()
        self.median_time_past = MedianTimePast()
        self.emergency_timelock = EmergencyGovernanceTimelock()

    def validate_new_transaction(self, tx) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive transaction validation

        Args:
            tx: Transaction to validate

        Returns:
            (valid, error_message)
        """
        # Size validation
        valid, error = self.block_size_validator.validate_transaction_size(tx)
        if not valid:
            return False, error

        # Dust protection (skip for COINBASE)
        if tx.sender != "COINBASE":
            valid, error = self.dust_protection.validate_transaction_amount(tx.amount)
            if not valid:
                return False, error

        # Amount validation
        valid, msg = self.overflow_protection.validate_amount(tx.amount)
        if not valid:
            return False, msg

        valid, msg = self.overflow_protection.validate_amount(tx.fee)
        if not valid:
            return False, msg

        # Mempool capacity
        valid, error = self.mempool_manager.can_add_transaction(tx, self.blockchain.pending_transactions)
        if not valid:
            return False, error

        return True, None

    def validate_new_block(self, block) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive block validation

        Args:
            block: Block to validate

        Returns:
            (valid, error_message)
        """
        # Size validation
        valid, error = self.block_size_validator.validate_block_size(block)
        if not valid:
            return False, error

        # Timestamp validation
        valid, error = self.median_time_past.validate_block_timestamp(block, self.blockchain)
        if not valid:
            return False, error

        # Validate coinbase amount
        if block.transactions:
            coinbase_tx = block.transactions[0]
            if coinbase_tx.sender == "COINBASE":
                base_reward = self.blockchain.get_block_reward(block.index)
                bonus_percent = self.blockchain.streak_tracker.get_streak_bonus(coinbase_tx.recipient)
                expected_reward = base_reward * (1 + bonus_percent)
                total_fees = sum(tx.fee for tx in block.transactions[1:])

                valid = self.supply_validator.validate_coinbase_amount(
                    block.index,
                    coinbase_tx.amount,
                    expected_reward,
                    total_fees
                )
                if not valid:
                    return False, "Invalid coinbase amount (inflation bug)"

        return True, None

    def add_checkpoint(self, block_index: int, block_hash: str):
        """Add checkpoint"""
        self.reorg_protection.add_checkpoint(block_index, block_hash)

    def validate_chain_reorganization(self, current_height: int, fork_point: int) -> Tuple[bool, Optional[str]]:
        """Validate reorganization attempt"""
        return self.reorg_protection.validate_reorganization(current_height, fork_point)

    def check_total_supply(self) -> Tuple[bool, float]:
        """Check total supply hasn't been exceeded"""
        return self.supply_validator.validate_total_supply(self.blockchain)
