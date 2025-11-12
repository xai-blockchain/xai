"""
XAI Blockchain Core - Production Implementation
Real cryptocurrency blockchain with transactions, mining, and consensus
"""

import hashlib
import json
import time
import logging
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime
import ecdsa
import base58
import sys
import os
from typing import Any, List, Dict, Optional, Set, Union

logger = logging.getLogger(__name__)


_cached_genesis_hash: Optional[str] = None
_cached_genesis_nonce: Optional[int] = None

# Add aixn-blockchain directory to path for AI development pool import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'aixn-blockchain'))

# Import configuration (testnet/mainnet)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
from security_validation import SecurityValidator, ValidationError

from config import Config

from gamification import (
    AirdropManager, StreakTracker, TreasureHuntManager,
    FeeRefundCalculator
)
from ai_development_pool import AIDevelopmentPool, AIModel
from nonce_tracker import NonceTracker
from trading import TradeOrder, OrderStatus, TradeMatch, TradeMatchStatus, TradeManager
from aml_compliance import TransactionRiskScore
from time_capsule import TimeCapsuleManager as CoreTimeCapsuleManager
from anonymous_logger import log_info, log_warning
from treasury_metrics import record_fee_collection, update_fee_treasury_balance

class Transaction:
    """Real cryptocurrency transaction with ECDSA signatures"""

    def __init__(self, sender: str, recipient: str, amount: float, fee: float = 0.0, public_key: str = None, tx_type: str = "normal", nonce: int = None, metadata: Optional[Dict[str, Any]] = None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.signature = None
        self.txid = None
        self.public_key = public_key  # Store sender's public key for signature verification
        self.tx_type = tx_type  # Transaction type: normal, airdrop, treasure, refund, time_capsule_lock, time_capsule_claim
        self.nonce = nonce  # Transaction nonce for replay protection
        self.metadata = metadata or {}
        self.risk_score = 0.0
        self.risk_level = 'clean'
        self.flag_reasons: List[str] = []

    def calculate_hash(self) -> str:
        """Calculate transaction hash (TXID)"""
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'tx_type': self.tx_type,
            'metadata': self.metadata
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def sign_transaction(self, private_key: str):
        """Sign transaction with sender's private key"""
        if self.sender == "COINBASE":
            # Coinbase transactions don't need signatures
            self.txid = self.calculate_hash()
            return

        try:
            sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
            vk = sk.get_verifying_key()
            self.public_key = vk.to_string().hex()
            message = self.calculate_hash().encode()
            signature = sk.sign(message)
            self.signature = signature.hex()
            self.txid = self.calculate_hash()
        except Exception as e:
            raise ValueError(f"Failed to sign transaction: {e}")

    def verify_signature(self) -> bool:
        """Verify transaction signature"""
        if self.sender == "COINBASE":
            return True

        if not self.signature or not self.public_key:
            return False

        try:
            # Use the provided public key for verification
            vk = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(self.public_key),
                curve=ecdsa.SECP256k1
            )

            # Verify the address matches this public key
            pub_hash = hashlib.sha256(self.public_key.encode()).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"
            if expected_address != self.sender:
                print(f"Address mismatch: expected {expected_address}, got {self.sender}")
                return False

            message = self.calculate_hash().encode()
            signature = bytes.fromhex(self.signature)
            return vk.verify(signature, message)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'txid': self.txid,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'public_key': self.public_key,
            'tx_type': self.tx_type,
            'nonce': self.nonce,
            'metadata': self.metadata,
            'risk_score': getattr(self, 'risk_score', 0.0),
            'risk_level': getattr(self, 'risk_level', 'clean'),
            'flag_reasons': getattr(self, 'flag_reasons', [])
        }


class NonceReplayTracker:
    """Lightweight nonce tracker used for historical chain validation."""

    def __init__(self):
        self.nonces: Dict[str, int] = {}

    def get_nonce(self, address: str) -> int:
        return self.nonces.get(address, -1)

    def get_next_nonce(self, address: str) -> int:
        return self.get_nonce(address) + 1

    def validate_nonce(self, address: str, nonce: int) -> bool:
        expected = self.get_next_nonce(address)
        return nonce == expected

    def increment_nonce(self, address: str, nonce: Optional[int] = None):
        current = self.get_nonce(address)
        next_nonce = nonce if nonce is not None else current + 1
        if next_nonce < current:
            next_nonce = current
        self.nonces[address] = next_nonce


class Block:
    """Blockchain block with real proof-of-work"""

    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, difficulty: int = 4):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.hash = None
        self.merkle_root = self.calculate_merkle_root()
        coinbase_tx = transactions[0] if transactions else None
        self.miner = (
            coinbase_tx.recipient
            if coinbase_tx and coinbase_tx.sender == "COINBASE"
            else None
        )

    def calculate_merkle_root(self) -> str:
        """Calculate merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b"").hexdigest()

        tx_hashes = [tx.txid for tx in self.transactions]

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self) -> str:
        """Mine block with proof-of-work"""
        target = '0' * self.difficulty

        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target):
                print(f"Block mined! Hash: {self.hash}")
                return self.hash
            self.nonce += 1

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'merkle_root': self.merkle_root,
            'nonce': self.nonce,
            'hash': self.hash,
            'difficulty': self.difficulty
        }


class Blockchain:
    """XAI Blockchain - Real cryptocurrency implementation"""

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = Config.INITIAL_DIFFICULTY  # Testnet: 2, Mainnet: 4
        self.initial_block_reward = Config.INITIAL_BLOCK_REWARD  # 12.0 XAI
        self.halving_interval = Config.HALVING_INTERVAL  # 262800 blocks (1 year)
        self.max_supply = Config.MAX_SUPPLY  # 121M cap - Bitcoin tribute (21M × 5 + 1M)
        self.transaction_fee_percent = 0.24
        self.utxo_set = {}  # Unspent transaction outputs
        self.reserved_utxos: Dict[str, Dict[str, Decimal]] = {}

        # Protected addresses (reserve wallets)
        self.protected_addresses = set()
        self.time_capsule_reserve_address = None

        # Initialize gamification features
        self.airdrop_manager = AirdropManager()
        self.streak_tracker = StreakTracker()
        self.treasure_manager = TreasureHuntManager()
        self.fee_refund_calculator = FeeRefundCalculator()
        self.time_capsule_manager = CoreTimeCapsuleManager(self)

        # Initialize nonce tracker
        self.nonce_tracker = NonceTracker()

        # Initialize AI Development Pool
        self.ai_pool = AIDevelopmentPool()

        # Initialize On-Chain Governance
        from governance_transactions import GovernanceState
        self.governance_state = None  # Will be initialized after genesis block
        self.governance_transactions = []  # All governance transactions

        # Create genesis block
        self.create_genesis_block()

        # Initialize governance with mining start time (genesis block timestamp)
        mining_start_time = self.get_latest_block().timestamp
        self.governance_state = GovernanceState(mining_start_time=mining_start_time)

        # Initialize governance execution engine
        from governance_execution import GovernanceExecutionEngine
        self.governance_executor = GovernanceExecutionEngine(self)

        # Transaction pause flag (for emergency actions)
        self.transactions_paused = False

        # Initialize advanced security
        from blockchain_security import BlockchainSecurityManager
        self.security_manager = BlockchainSecurityManager(self)
        self.security_validator = SecurityValidator()

        # AML compliance helpers
        self.aml_scorer = TransactionRiskScore()
        self.address_tx_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Initialize advanced consensus features
        from advanced_consensus import AdvancedConsensusManager
        self.consensus_manager = AdvancedConsensusManager(self)

        # Trading subsystem
        self.trade_manager = TradeManager(self)
        self.pending_trade_settlements: List[TradeMatch] = []
        self.trade_history: List[Dict[str, Any]] = []
        self._last_fee_audit: Optional[float] = None

    def create_genesis_block(self):
        """Create or load the genesis block"""
        import os

        # Try to load genesis block from file (for unified network)
        # Use testnet or mainnet genesis based on config
        genesis_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), Config.GENESIS_FILE)

        file_exists = os.path.exists(genesis_file)
        if file_exists:
            self._validate_genesis_file(genesis_file)
            print(f"Loading genesis block from {genesis_file}")
            with open(genesis_file, 'r') as f:
                genesis_data = json.load(f)

            # Recreate ALL genesis transactions
            genesis_transactions = []
            for tx_data in genesis_data['transactions']:
                genesis_tx = Transaction(
                    tx_data['sender'],
                    tx_data['recipient'],
                    tx_data['amount'],
                    tx_data.get('fee', 0.0)
                )
                genesis_tx.timestamp = tx_data.get('timestamp', time.time())
                genesis_tx.txid = tx_data.get('txid', genesis_tx.calculate_hash())
                genesis_tx.signature = tx_data.get('signature')
                genesis_transactions.append(genesis_tx)

            print(f"Loaded {len(genesis_transactions)} genesis transactions (Total: {sum(tx.amount for tx in genesis_transactions)} XAI)")

            # Create genesis block with pre-defined values
            genesis_block = Block(0, genesis_transactions, "0", self.difficulty)
            genesis_block.timestamp = genesis_data.get('timestamp', genesis_block.timestamp)
            genesis_block.nonce = genesis_data.get('nonce', genesis_block.nonce)
            genesis_block.merkle_root = genesis_data.get('merkle_root', genesis_block.merkle_root)
            genesis_block.hash = genesis_data.get('hash', genesis_block.hash)
            global _cached_genesis_hash, _cached_genesis_nonce
            if _cached_genesis_hash is not None and _cached_genesis_nonce is not None:
                genesis_block.hash = _cached_genesis_hash
                genesis_block.nonce = _cached_genesis_nonce
            else:
                genesis_block.hash = genesis_block.mine_block()
                _cached_genesis_hash = genesis_block.hash
                _cached_genesis_nonce = genesis_block.nonce

            print(f"Genesis block loaded: {genesis_block.hash}")
        else:
            print("Creating new genesis block...")
            genesis_tx = Transaction("COINBASE", "GENESIS", 1000000000.0)  # 1 billion XAI pre-mine
            genesis_tx.txid = genesis_tx.calculate_hash()

            genesis_block = Block(0, [genesis_tx], "0", self.difficulty)
            genesis_block.hash = genesis_block.mine_block()

        self.chain.append(genesis_block)
        self.update_utxo_set(genesis_block)

        # Protect time capsule reserve wallet (414,000 XAI)
        self._protect_time_capsule_reserve(genesis_block)

    def _validate_genesis_file(self, path: str):
        """Ensure the genesis file hash matches the vetted consensus hash."""
        expected_hash = Config.SAFE_GENESIS_HASHES.get(Config.NETWORK_TYPE)
        if not expected_hash:
            return

        with open(path, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        if actual_hash != expected_hash:
            raise ValueError("Genesis file hash mismatch; aborting startup to prevent tampering.")

    def _protect_time_capsule_reserve(self, genesis_block: Block):
        """
        Identify and protect the time capsule reserve wallet

        Args:
            genesis_block: Genesis block containing reserve wallet
        """
        RESERVE_AMOUNT = 414000.0  # 920 wallets × 450 XAI bonus

        # Find wallet with exact reserve amount
        for tx in genesis_block.transactions:
            if abs(tx.amount - RESERVE_AMOUNT) < 0.01:  # Allow small floating point error
                print(f"Time capsule reserve wallet protected: {tx.recipient}")
                self.protect_address(tx.recipient, "time_capsule")
                break

    def get_latest_block(self) -> Block:
        """Get the last block in the chain"""
        return self.chain[-1]

    def get_block_reward(self, block_height: int) -> float:
        """Calculate block reward with halving every 1 year (262,800 blocks at 2min/block)

        Emission schedule (121M cap - Bitcoin tribute: 21M × 5 + 1M):
        - Pre-mine: 22.4M XAI (genesis block)
        - Mineable: 98.6M XAI (over ~16 years)
        - Year 1 (blocks 0-262,799): 12 XAI/block → ~3.15M XAI
        - Year 2 (blocks 262,800-525,599): 6 XAI/block → ~1.58M XAI
        - Year 3 (blocks 525,600-788,399): 3 XAI/block → ~0.79M XAI
        - Year 4+: Continues halving...
        - Cap reached: ~Year 16, then only transaction fees for miners
        """
        # Check if we've reached the supply cap (121M XAI maximum)
        current_supply = self.get_total_circulating_supply()
        if current_supply >= self.max_supply:
            return 0.0  # No more mining rewards after cap reached - only tx fees

        halvings = block_height // self.halving_interval
        reward = self.initial_block_reward / (2 ** halvings)

        # Ensure reward doesn't go below minimum (0.00000001 XAI)
        min_reward = Decimal('0.00000001')
        if Decimal(str(reward)) < min_reward:
            reward = float(min_reward)

        # Ensure we don't exceed max supply with this reward
        if current_supply + reward > self.max_supply:
            reward = self.max_supply - current_supply
            if reward < 0:
                return 0.0

        return reward

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool after validation"""
        # Security validation (size, dust, overflow, mempool)
        valid, error = self.security_manager.validate_new_transaction(transaction)
        if not valid:
            print(f"Security validation failed: {error}")
            return False

        # Validate transaction
        if not self.validate_transaction(transaction):
            return False

        amount_needed = Decimal(str(transaction.amount)) + Decimal(str(transaction.fee))
        utxos = getattr(transaction, '_selected_utxos', None)
        if utxos:
            self._reserve_utxos_for_transaction(transaction, utxos)
        else:
            transaction._reserved_utxos = None

        self._score_transaction(transaction)
        self.pending_transactions.append(transaction)
        if transaction.sender != "COINBASE" and transaction.nonce is not None:
            self.nonce_tracker.reserve_nonce(transaction.sender, transaction.nonce)
        self.security_manager.mempool_manager.add_transaction(transaction)
        return True

    def _score_transaction(self, transaction: Transaction):
        """Assign AML risk metadata before the transaction enters the mempool."""
        sender = transaction.sender
        amount_usd = transaction.metadata.get('amount_usd', transaction.amount)
        history = self.address_tx_history[sender]

        tx_snapshot = {
            'sender': sender,
            'recipient': transaction.recipient,
            'amount': transaction.amount,
            'amount_usd': amount_usd,
            'timestamp': transaction.timestamp,
            'tx_type': transaction.tx_type
        }

        score, reasons = self.aml_scorer.calculate_risk_score(tx_snapshot, history)
        level = self.aml_scorer.get_risk_level(score)
        transaction.risk_score = score
        transaction.risk_level = level.value
        transaction.flag_reasons = reasons

        history.append(tx_snapshot)
        if len(history) > 200:
            history.pop(0)

        self.address_tx_history[sender] = history

    def protect_address(self, address: str, reserve_type: str = "time_capsule"):
        """
        Protect an address from unauthorized transactions

        Args:
            address: Address to protect
            reserve_type: Type of reserve (time_capsule, etc.)
        """
        self.protected_addresses.add(address)
        if reserve_type == "time_capsule":
            self.time_capsule_reserve_address = address

    def is_protected_address(self, address: str) -> bool:
        """
        Check if address is protected

        Args:
            address: Address to check

        Returns:
            bool: True if protected
        """
        return address in self.protected_addresses

    def validate_transaction(self, transaction: Transaction, nonce_tracker: Optional[NonceTracker] = None,
                             skip_balance_validation: bool = False) -> bool:
        """Validate a transaction"""
        # Coinbase transactions are always valid
        if transaction.sender == "COINBASE":
            return True

        # Check if transactions are paused (emergency action)
        if self.transactions_paused:
            print("Transactions are paused by governance emergency action")
            return False

        # Check if sender is a protected address
        if self.is_protected_address(transaction.sender):
            # Only allow timecapsule transactions from time capsule reserve
            if transaction.sender == self.time_capsule_reserve_address:
                if transaction.tx_type not in {"time_capsule_lock", "time_capsule_claim"}:
                    print(f"Unauthorized transaction from time capsule reserve. Only time capsule transactions allowed.")
                    return False
            else:
                print(f"Transaction from protected address {transaction.sender} is not allowed")
                return False

        # Validate inputs first
        try:
            self.security_validator.validate_address(transaction.sender, "sender")
            self.security_validator.validate_address(transaction.recipient, "recipient")
            transaction.amount = self.security_validator.validate_amount(transaction.amount, "amount")
            transaction.fee = self.security_validator.validate_amount(transaction.fee, "fee")
        except ValidationError as exc:
            print(f"Input validation failed: {exc}")
            return False

        # Dust protection (already skipped for coinbase)
        dust_valid, dust_error = self.security_manager.dust_protection.validate_transaction_amount(transaction.amount)
        if not dust_valid:
            print(f"Dust validation failed: {dust_error}")
            return False

        # Verify nonce (if present)
        tracker = nonce_tracker or self.nonce_tracker

        if transaction.nonce is not None:
            if not tracker.validate_nonce(transaction.sender, transaction.nonce):
                expected = tracker.get_next_nonce(transaction.sender)
                print(f"Invalid nonce. Expected: {expected}, Got: {transaction.nonce}")
                return False

        # Verify signature
        if not transaction.verify_signature():
            print("Invalid signature")
            return False

        if transaction.tx_type == "time_capsule_lock":
            capsule_id = transaction.metadata.get('capsule_id')
            unlock_time = int(transaction.metadata.get('unlock_time', 0))
            beneficiary = transaction.metadata.get('beneficiary')
            if not capsule_id or unlock_time <= int(time.time()) or not beneficiary:
                print("Time capsule metadata invalid")
                return False
            expected_recipient = self.time_capsule_manager.capsule_address(capsule_id)
            if transaction.recipient != expected_recipient:
                print("Time capsule recipient mismatch")
                return False

        if transaction.tx_type == "time_capsule_claim":
            if not transaction.metadata.get('capsule_id'):
                print("Time capsule claim missing capsule_id")
                return False

        # Check sender has sufficient balance
        if not skip_balance_validation:
            balance = self.get_balance(transaction.sender)
            total_needed = Decimal(str(transaction.amount)) + Decimal(str(transaction.fee))

            if balance < float(total_needed):
                print(f"Insufficient balance. Has: {balance}, Needs: {float(total_needed)}")
                return False

            utxos = self._select_utxos_for_amount(transaction.sender, total_needed)
            if not utxos:
                print("Insufficient spendable UTXOs after selection")
                return False

            transaction._selected_utxos = utxos

        return True

    def validate_block_timestamp(self, block: Block) -> bool:
        """
        Validate block timestamp

        Args:
            block: Block to validate

        Returns:
            bool: True if timestamp is valid
        """
        current_time = time.time()
        max_future_drift = 2 * 3600  # 2 hours

        # Reject blocks with timestamps too far in the future
        if block.timestamp > current_time + max_future_drift:
            print(f"Block timestamp too far in future: {block.timestamp} > {current_time + max_future_drift}")
            return False

        # Reject blocks with timestamps older than previous block
        if len(self.chain) > 0:
            previous_block = self.get_latest_block()
            if block.timestamp < previous_block.timestamp:
                print(f"Block timestamp older than previous block: {block.timestamp} < {previous_block.timestamp}")
                return False

        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        """Mine a new block with pending transactions"""
        # Calculate block reward based on current chain height (with halving)
        block_height = len(self.chain)
        base_reward = self.get_block_reward(block_height)

        # Update miner streak and apply bonus
        self.streak_tracker.update_miner_streak(miner_address, time.time())
        final_reward, streak_bonus = self.streak_tracker.apply_streak_bonus(miner_address, base_reward)
        final_reward = round(final_reward, 8)
        streak_bonus = round(streak_bonus, 8)

        # Create coinbase transaction (block reward + transaction fees + streak bonus)
        trade_settlements = self._process_pending_trade_settlements(block_height)
        trade_fee_total = sum(item['fee'] for item in trade_settlements)
        total_fees = sum(tx.fee for tx in self.pending_transactions) + trade_fee_total
        coinbase_reward = round(final_reward + total_fees, 8)

        coinbase_tx = Transaction("COINBASE", miner_address, coinbase_reward)
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Order transactions deterministically
        ordered_pending = self.consensus_manager.order_pending_transactions()

        # Create new block with ordered transactions
        block_transactions = [coinbase_tx] + ordered_pending
        new_block = Block(
            len(self.chain),
            block_transactions,
            self.get_latest_block().hash,
            self.difficulty
        )
        new_block.trade_settlements = trade_settlements

        # Mine the block
        new_block.hash = new_block.mine_block()

        # Validate block timestamp
        if not self.validate_block_timestamp(new_block):
            raise ValueError("Invalid block timestamp")

        # Advanced security validation
        valid, error = self.security_manager.validate_new_block(new_block)
        if not valid:
            raise ValueError(f"Block security validation failed: {error}")

        # Add to chain
        self.chain.append(new_block)
        self._audit_fee_treasury()

        # Add checkpoint every N blocks
        from blockchain_security import BlockchainSecurityConfig
        if new_block.index % BlockchainSecurityConfig.CHECKPOINT_INTERVAL == 0:
            self.security_manager.add_checkpoint(new_block.index, new_block.hash)
            print(f"Checkpoint added at block {new_block.index}")

        # Validate total supply periodically
        if new_block.index % BlockchainSecurityConfig.SUPPLY_CHECK_INTERVAL == 0:
            valid, total_supply = self.security_manager.check_total_supply()
            if not valid:
                raise ValueError(f"Supply cap exceeded: {total_supply}")
            print(f"Supply check passed: {total_supply:,.0f} XAI")

        # Advanced consensus: Adjust difficulty if needed
        self.consensus_manager.adjust_difficulty_if_needed()

        # Advanced consensus: Mark finalized blocks
        self.consensus_manager.mark_finalized_blocks()

        # Advanced consensus: Process any orphan blocks
        self.consensus_manager.process_orphans_after_block(new_block.hash)

        # Increment nonces for confirmed transactions
        for tx in block_transactions:
            if tx.sender != "COINBASE" and tx.nonce is not None:
                self.nonce_tracker.increment_nonce(tx.sender, tx.nonce)

            if hasattr(tx, '_reserved_utxos'):
                self._release_utxos_for_transaction(tx)

        # Update UTXO set
        self.update_utxo_set(new_block)

        # Process gamification features for this block
        self._process_gamification_features(new_block, miner_address)

        # Clear pending transactions
        self.pending_transactions = []

        # Log streak bonus if applied
        if streak_bonus > 0:
            print(f"STREAK BONUS: +{streak_bonus:.4f} XAI ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)")

        time.sleep(0.001 * self.difficulty)

        return new_block

    def _process_gamification_features(self, block: Block, miner_address: str):
        """Process all gamification features after mining a block"""
        block_height = block.index

        # 1. Check for airdrop (every 100th block)
        if self.airdrop_manager.should_trigger_airdrop(block_height):
            airdrop_amounts = self.airdrop_manager.execute_airdrop(
                block_height, block.hash, self
            )
            if airdrop_amounts:
                # Create airdrop transactions and add to next block pending
                for recipient, amount in airdrop_amounts.items():
                    airdrop_tx = Transaction("COINBASE", recipient, amount, tx_type="airdrop")
                    airdrop_tx.txid = airdrop_tx.calculate_hash()
                    self.pending_transactions.append(airdrop_tx)

        # 2. Process fee refunds based on congestion
        pending_count = len(self.pending_transactions)
        refunds = self.fee_refund_calculator.process_refunds(block, pending_count)
        if refunds:
            # Create refund transactions
            for recipient, amount in refunds.items():
                refund_tx = Transaction("COINBASE", recipient, amount, tx_type="refund")
                refund_tx.txid = refund_tx.calculate_hash()
                self.pending_transactions.append(refund_tx)

        # 3. Check for unlockable time capsules
        unlockable_capsules = self.time_capsule_manager.get_unlockable_capsules(block.timestamp)
        for capsule in unlockable_capsules:
            claim_tx = self.time_capsule_manager.build_claim_transaction(capsule)
            if claim_tx:
                self.pending_transactions.append(claim_tx)

        # 4. Process AI Development Pool tasks
        # Check if there are pending AI tasks and sufficient donated credits
        if len(self.ai_pool.task_queue) > 0:
            # Attempt to process queued tasks with available AI credits
            self.ai_pool._process_task_queue()

    def update_utxo_set(self, block: Block):
        """Update unspent transaction outputs"""
        block_height = block.index

        for tx in block.transactions:
            # Add new outputs
            if tx.recipient not in self.utxo_set:
                self.utxo_set[tx.recipient] = []

            self.utxo_set[tx.recipient].append({
                'txid': tx.txid,
                'amount': round(tx.amount, 8),
                'spent': False,
                'unlock_height': block_height
            })

            if tx.tx_type == "time_capsule_lock":
                self.time_capsule_manager.register_lock_transaction(tx, block_height, block.timestamp)
            elif tx.tx_type == "time_capsule_claim":
                self.time_capsule_manager.register_claim_transaction(tx, block.timestamp)

            if tx.sender == "COINBASE":
                continue

            self._consume_utxos(tx, block_height)

    def _select_utxos_for_amount(self, sender: str, amount_needed: Decimal) -> Optional[List[dict]]:
        """Select unspent, unreserved UTXOs that cover the amount needed."""
        selected = []
        total = Decimal('0')
        reserved = self.reserved_utxos.get(sender, {})

        for utxo in self.utxo_set.get(sender, []):
            if utxo['spent']:
                continue

            txid = utxo['txid']
            if reserved.get(txid, Decimal('0')) > Decimal('0'):
                continue

            utxo_amount = Decimal(str(utxo['amount']))
            selected.append({'utxo': utxo, 'reserved': utxo_amount})
            total += utxo_amount
            if total >= amount_needed:
                return selected

        return None

    def _reserve_utxos_for_transaction(self, transaction: Transaction, utxos: List[dict]):
        """Mark UTXOs as reserved for a pending transaction."""
        sender = transaction.sender
        if sender not in self.reserved_utxos:
            self.reserved_utxos[sender] = {}

        for allocation in utxos:
            utxo = allocation['utxo']
            amount = allocation['reserved']
            txid = utxo['txid']
            current = self.reserved_utxos[sender].get(txid, Decimal('0'))
            self.reserved_utxos[sender][txid] = current + amount

        transaction._reserved_allocations = utxos
        transaction._reserved_utxos = [allocation['utxo'] for allocation in utxos]

    def _release_utxos_for_transaction(self, transaction: Transaction):
        """Release reserved UTXOs after a transaction is mined."""
        sender = transaction.sender
        allocations = getattr(transaction, '_reserved_allocations', []) or []
        for allocation in allocations:
            utxo = allocation['utxo']
            amount = allocation['reserved']
            txid = utxo['txid']

            if sender in self.reserved_utxos:
                current = self.reserved_utxos[sender].get(txid, Decimal('0'))
                remaining = current - amount
                if remaining <= Decimal('0'):
                    self.reserved_utxos[sender].pop(txid, None)
                else:
                    self.reserved_utxos[sender][txid] = remaining

        transaction._reserved_utxos = None

    def _consume_utxos(self, tx: Transaction, block_height: int):
        """Consume sender UTXOs when applying a transaction."""
        sender = tx.sender
        spent_amount = Decimal(str(tx.amount)) + Decimal(str(tx.fee))
        remaining = spent_amount

        if sender not in self.utxo_set:
            return

        utxos_to_use = getattr(tx, '_reserved_utxos', None) or self.utxo_set[sender]

        for utxo in utxos_to_use:
            if not utxo['spent'] and remaining > 0:
                utxo_amt = Decimal(str(utxo['amount']))

                if utxo_amt <= remaining:
                    utxo['spent'] = True
                    remaining = (remaining - utxo_amt).quantize(
                        Decimal('0.00000001'), rounding=ROUND_HALF_EVEN
                    )
                else:
                    utxo['spent'] = True
                    change_amount = (utxo_amt - remaining).quantize(
                        Decimal('0.00000001'), rounding=ROUND_HALF_EVEN
                    )
                    if change_amount > Decimal('0'):
                        change_txid = f"{tx.txid}_change_{utxo['txid']}"
                        self.utxo_set[sender].append({
                            'txid': change_txid,
                            'amount': float(change_amount),
                            'spent': False,
                            'unlock_height': block_height
                        })
                    remaining = Decimal('0')

    def get_balance(self, address: str) -> float:
        """Get balance of an address"""
        if address not in self.utxo_set:
            return 0.0

        current_height = len(self.chain) - 1
        total = Decimal('0')
        for utxo in self.utxo_set[address]:
            unlock = utxo.get('unlock_height', current_height)
            if not utxo['spent'] and unlock <= current_height:
                total += Decimal(str(utxo['amount']))

        total = total.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_EVEN)
        return float(total)

    def _process_pending_trade_settlements(self, block_height: int) -> List[Dict[str, Any]]:
        """Apply any ready trade matches before mining a block"""
        completed = []
        while self.pending_trade_settlements:
            match = self.pending_trade_settlements.pop(0)
            settlement = self._settle_trade_match(match, block_height)
            if settlement:
                completed.append(settlement)
        return completed

    def _settle_trade_match(self, match: TradeMatch, block_height: int) -> Optional[Dict[str, Any]]:
        """Atomically move funds for a matched trade pair"""
        maker_order = self.trade_manager.get_order(match.maker_order_id)
        taker_order = self.trade_manager.get_order(match.taker_order_id)
        if not maker_order or not taker_order:
            return None

        fee_address = getattr(Config, 'TRADE_FEE_ADDRESS', f"{Config.ADDRESS_PREFIX}FEEPOOL")
        maker_fee = float(match.metadata.get('maker_fee', 0.0))
        taker_fee = float(match.metadata.get('taker_fee', 0.0))
        maker_net = max(0.0, maker_order.amount_offered - maker_fee)
        taker_net = max(0.0, taker_order.amount_offered - taker_fee)

        def record_transfer(sender, recipient, amount, transfer_type, currency='XAI'):
            if amount <= 0:
                return None
            txid = self._apply_trade_transfer(sender, recipient, amount, block_height)
            event = {
                'txid': txid,
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
                'type': transfer_type
            }
            if transfer_type == 'fee':
                record_fee_collection(currency, amount)
                log_info(f"Fee treasury credit: {amount:.8f} {currency} from {sender} → {recipient}")
            else:
                log_info(f"Trade transfer: {amount:.8f} {currency} from {sender} → {recipient}")
            return event

        try:
            transfer_events = []
            maker_trade_transfer = record_transfer(
                maker_order.maker_address,
                taker_order.maker_address,
                maker_net,
                'trade',
                maker_order.token_offered
            )
            if maker_trade_transfer:
                transfer_events.append(maker_trade_transfer)

            taker_trade_transfer = record_transfer(
                taker_order.maker_address,
                maker_order.maker_address,
                taker_net,
                'trade',
                taker_order.token_offered
            )
            if taker_trade_transfer:
                transfer_events.append(taker_trade_transfer)

            maker_fee_transfer = record_transfer(
                maker_order.maker_address,
                fee_address,
                maker_fee,
                'fee',
                maker_order.token_offered
            )
            if maker_fee_transfer:
                transfer_events.append(maker_fee_transfer)

            taker_fee_transfer = record_transfer(
                taker_order.maker_address,
                fee_address,
                taker_fee,
                'fee',
                taker_order.token_offered
            )
            if taker_fee_transfer:
                transfer_events.append(taker_fee_transfer)
        except ValueError as exc:
            match.status = TradeMatchStatus.FAILED
            match.metadata['failure'] = str(exc)
            return None

        match.status = TradeMatchStatus.SETTLED
        maker_order.status = OrderStatus.COMPLETED
        taker_order.status = OrderStatus.COMPLETED
        match.metadata['settled_at'] = time.time()

        fee_amount = match.metadata.get('fee', 0.0)
        if not fee_amount:
            fee_amount = match.metadata.get('fee_total', maker_fee + taker_fee)

        settlement = {
            'match_id': match.match_id,
            'block_height': block_height,
            'fee': float(fee_amount),
            'maker_fee': maker_fee,
            'taker_fee': taker_fee,
            'fee_address': fee_address,
            'transfers': transfer_events
        }
        self.trade_history.append(settlement)
        self.record_trade_event('trade_settled', settlement)
        update_fee_treasury_balance(self, fee_address, 'XAI')
        return settlement

    def get_expected_fee_total(self) -> float:
        return sum(settlement.get('fee', 0.0) for settlement in self.trade_history)

    def _audit_fee_treasury(self) -> Dict[str, float]:
        fee_address = getattr(Config, 'TRADE_FEE_ADDRESS', None)
        if not fee_address:
            return {}

        actual_balance = float(self.get_balance(fee_address))
        expected = self.get_expected_fee_total()
        diff = actual_balance - expected
        update_fee_treasury_balance(self, fee_address, 'XAI')

        if abs(diff) > 1e-4:
            log_warning(
                f"Fee treasury audit mismatch for {fee_address}: actual={actual_balance:.8f}, expected={expected:.8f}, diff={diff:.8f}"
            )

        self._last_fee_audit = actual_balance
        return {
            'actual_balance': actual_balance,
            'expected_balance': expected,
            'difference': diff,
        }

    def audit_fee_treasury(self) -> Dict[str, float]:
        return self._audit_fee_treasury()

    def _apply_trade_transfer(self, sender: str, recipient: str, amount: float, block_height: int) -> str:
        """Consume sender UTXOs and credit the recipient for a trade transfer"""
        total_needed = Decimal(str(amount))
        tx = Transaction(sender, recipient, amount, 0.0, tx_type="trade_settlement")
        tx.signature = "TRADE"
        tx.public_key = ""
        tx.txid = tx.calculate_hash()

        utxos = self._select_utxos_for_amount(sender, total_needed)
        if not utxos:
            raise ValueError(f"Insufficient funds for trade transfer from {sender}")

        tx._selected_utxos = utxos
        self._reserve_utxos_for_transaction(tx, utxos)
        self._consume_utxos(tx, block_height)
        self._release_utxos_for_transaction(tx)

        self.utxo_set.setdefault(recipient, []).append({
            'txid': tx.txid,
            'amount': float(amount),
            'spent': False,
            'unlock_height': block_height
        })

        return tx.txid

    def submit_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a new wallet trade order"""
        session_token = order_data.pop('session_token', None)
        signature = order_data.pop('signature', None)
        order = TradeOrder.from_dict(order_data)
        success, message, match = self.trade_manager.place_order(
            order,
            session_token=session_token,
            signature=signature
        )
        response = {
            'success': success,
            'message': message,
            'order_id': order.order_id,
            'status': order.status.value,
        }
        if match:
            response['match'] = match.to_dict()
        self.record_trade_event('order_submitted', {
            'order_id': order.order_id,
            'status': order.status.value,
            'success': success,
            'message': message
        })
        return response

    def reveal_trade_secret(self, match_id: str, secret: str) -> Dict[str, Any]:
        """Reveal a trade secret so a matched swap can settle"""
        success, message = self.trade_manager.reveal_secret(match_id, secret)
        return {'success': success, 'message': message}

    def get_trade_orders(self, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """List orders optionally filtered by status"""
        return [order.to_dict() for order in self.trade_manager.list_orders(status)]

    def get_trade_matches(self) -> List[Dict[str, Any]]:
        """List current trade matches"""
        return [match.to_dict() for match in self.trade_manager.list_matches()]

    def enqueue_trade_settlement(self, match: TradeMatch):
        """Mark a match for settlement in the next block"""
        if match not in self.pending_trade_settlements:
            self.pending_trade_settlements.append(match)

    def register_trade_session(self, wallet_address: str) -> Dict[str, str]:
        """Create a session token/secret for WalletConnect-style access"""
        return self.trade_manager.register_session(wallet_address)

    def record_trade_event(self, event_type: str, payload: Dict[str, Any]):
        entry = {
            'type': event_type,
            'timestamp': time.time(),
            'payload': payload
        }
        self.trade_history.append(entry)
        logger.info(json.dumps(entry))

    def get_total_circulating_supply(self) -> float:
        """Get total circulating supply across UTXO set"""
        total = Decimal('0')
        for utxos in self.utxo_set.values():
            for utxo in utxos:
                if not utxo['spent']:
                    total += Decimal(str(utxo['amount']))

        total = total.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_EVEN)
        return float(total)

    def get_circulating_supply(self) -> float:
        """Legacy alias for total circulating supply"""
        return self.get_total_circulating_supply()

    def execute_approved_proposal(self, proposal_id: str) -> Dict:
        """
        Execute an approved governance proposal

        This actually applies the approved changes to the blockchain.

        Args:
            proposal_id: ID of approved proposal

        Returns:
            dict: Execution result
        """
        if proposal_id not in self.governance_state.proposals:
            return {
                'success': False,
                'error': 'Proposal not found'
            }

        proposal = self.governance_state.proposals[proposal_id]

        # Verify proposal is approved
        if proposal.status != 'executed':
            return {
                'success': False,
                'error': f'Proposal not ready for execution. Status: {proposal.status}'
            }

        # Execute via governance executor
        result = self.governance_executor.execute_proposal(
            proposal_id,
            proposal.to_dict()
        )

        return result

    def validate_chain(self) -> bool:
        """Validate entire blockchain"""
        replay_tracker = NonceReplayTracker()
        if self.chain:
            for tx in self.chain[0].transactions:
                if tx.sender != "COINBASE" and tx.nonce is not None:
                    replay_tracker.increment_nonce(tx.sender, tx.nonce)

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Verify hash
            if current_block.hash != current_block.calculate_hash():
                print(f"Block {i} has invalid hash")
                return False

            # Verify previous hash
            if current_block.previous_hash != previous_block.hash:
                print(f"Block {i} has invalid previous hash")
                return False

            # Verify proof of work
            if not current_block.hash.startswith('0' * current_block.difficulty):
                print(f"Block {i} doesn't meet difficulty requirement")
                return False

            # Verify all transactions
            for tx in current_block.transactions:
                if not self.validate_transaction(tx, nonce_tracker=replay_tracker, skip_balance_validation=True):
                    print(f"Block {i} has invalid transaction")
                    return False

                if tx.sender != "COINBASE" and tx.nonce is not None:
                    replay_tracker.increment_nonce(tx.sender, tx.nonce)

        return True

    def get_transaction_history(self, address: str) -> List[dict]:
        """Get all transactions involving an address"""
        history = []

        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address or tx.recipient == address:
                    history.append({
                    'block': block.index,
                    'txid': tx.txid,
                    'sender': tx.sender,
                    'recipient': tx.recipient,
                    'amount': tx.amount,
                    'fee': tx.fee,
                    'timestamp': tx.timestamp,
                    'type': 'sent' if tx.sender == address else 'received',
                    'risk_score': getattr(tx, 'risk_score', 0.0),
                    'risk_level': getattr(tx, 'risk_level', 'clean'),
                    'flag_reasons': getattr(tx, 'flag_reasons', [])
                })

        return history

    def get_stats(self) -> dict:
        """Get blockchain statistics"""
        total_transactions = sum(len(block.transactions) for block in self.chain)
        total_supply = sum(self.get_balance(addr) for addr in self.utxo_set)

        return {
            'blocks': len(self.chain),
            'total_transactions': total_transactions,
            'pending_transactions': len(self.pending_transactions),
            'difficulty': self.difficulty,
            'total_supply': total_supply,
            'unique_addresses': len(self.utxo_set),
            'latest_block_hash': self.get_latest_block().hash
        }

    # AI Development Pool Methods

    def donate_ai_credits(self, donor_address: str, ai_model: AIModel,
                         api_key: str, token_amount: int) -> Dict:
        """
        Donate AI API credits to the development pool

        Args:
            donor_address: XAI wallet address of donor
            ai_model: Which AI model (Claude, GPT-4, etc.)
            api_key: API key for the model
            token_amount: Number of tokens to donate

        Returns:
            dict: Donation receipt
        """
        # Use the AI pool to process the donation
        result = self.ai_pool.donate_ai_credits(
            donor_address, ai_model, api_key, token_amount
        )

        # Create a special transaction to record the donation on-chain
        if result['success']:
            # Create AI donation transaction (tx_type = "ai_donation")
            donation_tx = Transaction(
                sender=donor_address,
                recipient="AI_DEVELOPMENT_POOL",
                amount=0.0,  # No XAI transferred, just recording the donation
                fee=0.0,
                tx_type="ai_donation"
            )
            donation_tx.txid = donation_tx.calculate_hash()

            # Add donation metadata to transaction
            donation_tx.ai_model = ai_model.value
            donation_tx.token_amount = token_amount
            donation_tx.usd_value = result['usd_value']
            donation_tx.donation_id = result['donation_id']

            # Add to pending transactions
            self.pending_transactions.append(donation_tx)

        return result

    def get_ai_pool_stats(self) -> Dict:
        """Get AI Development Pool statistics"""
        return self.ai_pool.get_pool_stats()

    def get_ai_donor_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """Get top AI credit donors"""
        return self.ai_pool.get_donor_leaderboard(top_n)

    def get_ai_model_leaderboard(self) -> List[Dict]:
        """Get AI model competition leaderboard"""
        return self.ai_pool.get_model_leaderboard()

    def create_ai_development_task(self, task_type: str, description: str,
                                   estimated_tokens: int, priority: int = 5) -> Dict:
        """
        Create a new development task for AI to complete

        Args:
            task_type: Type of task (code_generation, bug_fixing, etc.)
            description: What needs to be done
            estimated_tokens: Estimated token cost
            priority: 1-10, higher = more urgent

        Returns:
            dict: Task details
        """
        return self.ai_pool.create_development_task(
            task_type, description, estimated_tokens, priority
        )

    # ========================================================================
    # ON-CHAIN GOVERNANCE METHODS
    # ========================================================================

    def submit_governance_proposal(self, submitter: str, title: str,
                                   description: str, proposal_type: str,
                                   proposal_data: Dict) -> Dict:
        """
        Submit governance proposal (on-chain transaction)

        Args:
            submitter: Address submitting proposal
            title: Proposal title
            description: Proposal description
            proposal_type: ai_improvement, parameter_change, emergency
            proposal_data: Proposal-specific data

        Returns:
            dict: Result with proposal_id and txid
        """
        from governance_transactions import GovernanceTransaction, GovernanceTxType
        import hashlib

        # Generate proposal ID
        proposal_id = hashlib.sha256(f"{title}{time.time()}".encode()).hexdigest()[:16]

        # Create on-chain governance transaction
        gov_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter=submitter,
            proposal_id=proposal_id,
            data={
                'title': title,
                'description': description,
                'proposal_type': proposal_type,
                **proposal_data
            }
        )

        # Add to governance transactions
        self.governance_transactions.append(gov_tx)

        # Process in governance state
        result = self.governance_state.submit_proposal(gov_tx)

        return {
            'success': True,
            'proposal_id': proposal_id,
            'txid': gov_tx.txid,
            'status': result['status']
        }

    def cast_governance_vote(self, voter: str, proposal_id: str,
                            vote: str, voting_power: float) -> Dict:
        """
        Cast vote on proposal (on-chain transaction)

        Args:
            voter: Voter address
            proposal_id: Proposal to vote on
            vote: yes, no, abstain
            voting_power: Voter's voting power

        Returns:
            dict: Result with txid
        """
        from governance_transactions import GovernanceTransaction, GovernanceTxType

        gov_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter=voter,
            proposal_id=proposal_id,
            data={
                'vote': vote,
                'voting_power': voting_power
            }
        )

        self.governance_transactions.append(gov_tx)
        result = self.governance_state.cast_vote(gov_tx)

        return {
            'success': True,
            'txid': gov_tx.txid,
            'vote_count': result['vote_count']
        }

    def submit_code_review(self, reviewer: str, proposal_id: str,
                          approved: bool, comments: str,
                          voting_power: float) -> Dict:
        """
        Submit code review (on-chain transaction)

        Args:
            reviewer: Reviewer address
            proposal_id: Proposal being reviewed
            approved: Review approval
            comments: Review comments
            voting_power: Reviewer's voting power

        Returns:
            dict: Result with txid
        """
        from governance_transactions import GovernanceTransaction, GovernanceTxType

        gov_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_CODE_REVIEW,
            submitter=reviewer,
            proposal_id=proposal_id,
            data={
                'approved': approved,
                'comments': comments,
                'voting_power': voting_power
            }
        )

        self.governance_transactions.append(gov_tx)
        result = self.governance_state.submit_code_review(gov_tx)

        return {
            'success': True,
            'txid': gov_tx.txid,
            'review_count': result['review_count']
        }

    def vote_implementation(self, voter: str, proposal_id: str,
                           approved: bool) -> Dict:
        """
        Vote on implementation approval (on-chain transaction)

        Args:
            voter: Voter address (must be original approver)
            proposal_id: Proposal to approve implementation
            approved: Implementation approval

        Returns:
            dict: Result with txid
        """
        from governance_transactions import GovernanceTransaction, GovernanceTxType

        gov_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.VOTE_IMPLEMENTATION,
            submitter=voter,
            proposal_id=proposal_id,
            data={'approved': approved}
        )

        self.governance_transactions.append(gov_tx)
        result = self.governance_state.vote_implementation(gov_tx)

        # Pass through the result (may include validation errors)
        if result['success']:
            result['txid'] = gov_tx.txid

        return result

    def execute_proposal(self, proposal_id: str, execution_data: Dict) -> Dict:
        """
        Execute approved proposal after timelock (on-chain transaction)

        Args:
            proposal_id: Proposal to execute
            execution_data: Execution details

        Returns:
            dict: Result with execution txid
        """
        from governance_transactions import GovernanceTransaction, GovernanceTxType

        gov_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.EXECUTE_PROPOSAL,
            submitter="PROTOCOL",
            proposal_id=proposal_id,
            data=execution_data
        )

        self.governance_transactions.append(gov_tx)
        result = self.governance_state.execute_proposal(gov_tx)

        # Pass through the result from governance_state (includes validation failures)
        result['txid'] = gov_tx.txid
        if 'status' not in result:
            result['status'] = 'executed' if result.get('success') else 'failed'

        return result

    def get_governance_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get proposal state from blockchain"""
        return self.governance_state.get_proposal_state(proposal_id)

    def get_all_governance_proposals(self) -> List[Dict]:
        """Get all governance proposals"""
        return [
            self.governance_state.get_proposal_state(pid)
            for pid in self.governance_state.proposals.keys()
        ]

    def rebuild_governance_state(self):
        """
        Rebuild governance state from blockchain
        Replays all governance transactions
        """
        self.governance_state.reconstruct_from_blockchain(self.governance_transactions)

    def get_block_finality(self, block_index: int) -> dict:
        """
        Get finality information for a block

        Args:
            block_index: Block index

        Returns:
            dict: Finality information
        """
        chain_height = len(self.chain)
        return self.consensus_manager.finality_tracker.get_block_finality(block_index, chain_height)

    def get_consensus_stats(self) -> dict:
        """Get advanced consensus statistics"""
        return self.consensus_manager.get_consensus_stats()

    def to_dict(self) -> dict:
        """Export entire blockchain"""
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'difficulty': self.difficulty,
            'stats': self.get_stats(),
            'governance_proposals': len(self.governance_state.proposals),
            'governance_transactions': len(self.governance_transactions)
        }
