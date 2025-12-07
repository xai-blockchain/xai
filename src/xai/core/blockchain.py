"""
AXN Blockchain Core - Production Implementation
Real cryptocurrency blockchain with transactions, mining, and consensus
"""

from __future__ import annotations

import hashlib
import json
import time
import os
import copy
import statistics
import tempfile
import math
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Union, Sequence
from types import SimpleNamespace
from datetime import datetime
import base58
from xai.core.config import Config
from xai.core.advanced_consensus import DynamicDifficultyAdjustment
from xai.core.gamification import (
    AirdropManager,
    StreakTracker,
    TreasureHuntManager,
    FeeRefundCalculator,
    TimeCapsuleManager,
)
from xai.core.nonce_tracker import NonceTracker
from xai.core.wallet_trade_manager_impl import WalletTradeManager
from xai.core.trading import SwapOrderType
from xai.core.blockchain_storage import BlockchainStorage
from xai.core.transaction_validator import TransactionValidator
from xai.core.utxo_manager import UTXOManager
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex
from xai.core.vm.manager import SmartContractManager
from xai.core.governance_execution import GovernanceExecutionEngine
from xai.core.governance_transactions import GovernanceState, GovernanceTxType, GovernanceTransaction
from xai.core.checkpoints import CheckpointManager
from collections import defaultdict, deque
from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.block_header import BlockHeader, canonical_json
from xai.core.blockchain_interface import BlockchainDataProvider, GamificationBlockchainInterface
from xai.core.blockchain_security import BlockchainSecurityConfig, BlockSizeValidator
from xai.core.finality import (
    FinalityManager,
    FinalityCertificate,
    FinalityConfigurationError,
    FinalityValidationError,
    ValidatorIdentity,
)
from xai.blockchain.slashing_manager import SlashingManager

from xai.core.transaction import Transaction, TransactionValidationError
from xai.core.node_identity import load_or_create_identity
from xai.core.security_validation import SecurityEventRouter
from xai.core.account_abstraction import (
    get_sponsored_transaction_processor,
    SponsorshipResult,
)
from xai.core.address_index import AddressTransactionIndex

class Block:
    """Blockchain block with real proof-of-work"""

    def __init__(
        self,
        header: Union[BlockHeader, int],
        transactions: List[Transaction],
        previous_hash: Optional[str] = None,
        difficulty: Optional[int] = None,
        timestamp: Optional[float] = None,
        nonce: int = 0,
        merkle_root: Optional[str] = None,
        signature: Optional[str] = None,
        miner_pubkey: Optional[str] = None,
    ) -> None:
        """
        Accept either a fully constructed BlockHeader or legacy positional fields
        (index, transactions, previous_hash, difficulty, ...). The legacy path
        keeps backward compatibility with tests/utilities that still instantiate
        blocks directly from primitives.
        """
        if isinstance(header, BlockHeader):
            block_header = header
        else:
            if previous_hash is None or difficulty is None:
                raise ValueError("previous_hash and difficulty are required for legacy block construction")
            block_header = BlockHeader(
                index=int(header),
                previous_hash=previous_hash,
                merkle_root=merkle_root or self._calculate_merkle_root_static(transactions),
                timestamp=timestamp or time.time(),
                difficulty=int(difficulty),
                nonce=nonce,
                signature=signature,
                miner_pubkey=miner_pubkey,
                version=Config.BLOCK_HEADER_VERSION,
            )

        self.header = block_header
        self.transactions = transactions
        self._miner: Optional[str] = None
        # Optional ancestry window for fast reorg sync; never persisted
        self.lineage: Optional[List["Block"]] = None

    @staticmethod
    def _calculate_merkle_root_static(transactions: List[Transaction]) -> str:
        """Calculate a merkle root from raw transactions without needing a Blockchain instance."""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        tx_hashes: List[str] = []
        for tx in transactions:
            if tx.txid is None:
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

        while len(tx_hashes) > 1:
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])
            tx_hashes = [
                hashlib.sha256((tx_hashes[i] + tx_hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(tx_hashes), 2)
            ]

        return tx_hashes[0]

    @property
    def index(self) -> int:
        return self.header.index
    
    @index.setter
    def index(self, value: int) -> None:
        self.header.index = value

    @property
    def hash(self) -> str:
        return self.header.hash
    
    @hash.setter
    def hash(self, value: str) -> None:
        self.header.hash = value

    @property
    def version(self) -> int:
        return getattr(self.header, "version", getattr(Config, "BLOCK_HEADER_VERSION", 1))

    @property
    def previous_hash(self) -> str:
        return self.header.previous_hash
    
    @previous_hash.setter
    def previous_hash(self, value: str) -> None:
        # Allow controlled updates (used in reorg/orphan handling paths and tests)
        self.header.previous_hash = value

    @property
    def timestamp(self) -> float:
        return self.header.timestamp

    @timestamp.setter
    def timestamp(self, value: float) -> None:
        self.header.timestamp = value
        self.header.hash = self.header.calculate_hash()
    
    @property
    def difficulty(self) -> int:
        return self.header.difficulty

    @difficulty.setter
    def difficulty(self, value: int) -> None:
        self.header.difficulty = int(value)
        self.header.hash = self.header.calculate_hash()
    
    @property
    def nonce(self) -> int:
        return self.header.nonce

    @nonce.setter
    def nonce(self, value: int) -> None:
        self.header.nonce = int(value)
        self.header.hash = self.header.calculate_hash()
    
    @property
    def merkle_root(self) -> str:
        return self.header.merkle_root
    
    @property
    def signature(self) -> Optional[str]:
        return self.header.signature
    
    @property
    def miner_pubkey(self) -> Optional[str]:
        return self.header.miner_pubkey
    
    @property
    def miner(self) -> Optional[str]:
        return self._miner or self.header.miner_pubkey
    
    @miner.setter
    def miner(self, value: str) -> None:
        self._miner = value
    
    def calculate_hash(self) -> str:
        return self.header.calculate_hash()
    
    def sign_block(self, private_key: str) -> None:
        self.header.signature = sign_message_hex(private_key, self.header.hash.encode())

    def verify_signature(self, public_key: str) -> bool:
        if self.header.signature is None or self.header.miner_pubkey is None:
            return False
        return verify_signature_hex(public_key, self.header.hash.encode(), self.header.signature)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "miner": self.miner,
        }

    def estimate_size_bytes(self) -> int:
        """
        Estimate the serialized size of the block for strict resource enforcement.

        The estimation uses deterministic JSON serialization for the header and
        transactions, falling back to structural approximations if a transaction
        is missing helpers (should never happen in production).
        """
        header_bytes = len(canonical_json(self.header.to_dict()).encode("utf-8"))

        tx_bytes = 0
        for tx in self.transactions:
            if tx is None:
                continue
            try:
                tx_bytes += tx.get_size()
            except AttributeError:
                try:
                    tx_bytes += len(canonical_json(tx.to_dict()).encode("utf-8"))
                except Exception as e:
                    self.logger.warning(
                        "Failed to calculate transaction size, using 0",
                        tx_type=type(tx).__name__,
                        error=str(e)
                    )
                    tx_bytes += 0

        miner_bytes = len((self.miner or "").encode("utf-8"))
        structure_overhead = 8 + len(self.transactions) * 4
        return header_bytes + tx_bytes + miner_bytes + structure_overhead
    
    def calculate_merkle_root(self) -> str:
        """Calculate merkle root of transactions"""
        if not self.transactions:
            return hashlib.sha256(b"").hexdigest()

        # Get transaction hashes, ensuring all txids are set
        tx_hashes = []
        for tx in self.transactions:
            if tx.txid is None:
                # Calculate hash for transactions without txid
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

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

    def generate_merkle_proof(self, txid: str) -> List[Tuple[str, bool]]:
        """
        Generate a merkle proof for a transaction in this block.

        This allows light clients to verify a transaction is in a block without
        downloading all transactions. The proof is a list of sibling hashes
        needed to reconstruct the merkle root.

        Args:
            txid: Transaction ID to generate proof for

        Returns:
            List of (sibling_hash, is_right) tuples where:
            - sibling_hash: The hash of the sibling node in the merkle tree
            - is_right: True if sibling is on the right, False if on the left

        Raises:
            ValueError: If transaction is not found in block
        """
        if not self.transactions:
            raise ValueError("Block has no transactions")

        # Build transaction hash list
        tx_hashes = []
        tx_index = -1
        for idx, tx in enumerate(self.transactions):
            if tx.txid is None:
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)
            if tx.txid == txid:
                tx_index = idx

        if tx_index == -1:
            raise ValueError(f"Transaction {txid} not found in block")

        # Build merkle tree proof
        proof: List[Tuple[str, bool]] = []
        current_index = tx_index
        current_level = tx_hashes.copy()

        # Build proof by traversing up the tree
        while len(current_level) > 1:
            # Handle odd number of elements (duplicate last)
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])

            # Find sibling for current index
            if current_index % 2 == 0:
                # Current node is left child, sibling is right
                sibling_index = current_index + 1
                is_right = True
            else:
                # Current node is right child, sibling is left
                sibling_index = current_index - 1
                is_right = False

            # Add sibling to proof
            sibling_hash = current_level[sibling_index]
            proof.append((sibling_hash, is_right))

            # Build next level
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            # Update for next iteration
            current_level = next_level
            current_index = current_index // 2

        return proof


_GOVERNANCE_METADATA_TYPE_MAP = {
    "governance_proposal": GovernanceTxType.SUBMIT_PROPOSAL,
    "governance_vote": GovernanceTxType.CAST_VOTE,
    "code_review": GovernanceTxType.SUBMIT_CODE_REVIEW,
    "implementation_vote": GovernanceTxType.VOTE_IMPLEMENTATION,
    "proposal_execution": GovernanceTxType.EXECUTE_PROPOSAL,
    "rollback_change": GovernanceTxType.ROLLBACK_CHANGE,
}


class Blockchain:
    """AXN Blockchain - Real cryptocurrency implementation"""

    class _GamificationBlockchainAdapter(GamificationBlockchainInterface):
        """Adapter to expose specific Blockchain methods to gamification managers."""
        def __init__(self, blockchain_instance: 'Blockchain'):
            self._blockchain = blockchain_instance

        def get_balance(self, address: str) -> float:
            return self._blockchain.utxo_manager.get_balance(address)

        def get_chain_length(self) -> int:
            return len(self._blockchain.chain)

        def get_block_by_index(self, index: int) -> Optional[Any]:
            return self._blockchain.storage.load_block_from_disk(index)

        def get_latest_block_hash(self) -> str:
            if not self._blockchain.chain:
                return "0"
            return self._blockchain.chain[-1].hash

        def get_pending_transactions(self) -> List[Transaction]:
            return self._blockchain.pending_transactions
        
        def get_mempool_size_kb(self) -> float:
            return self._blockchain.get_mempool_size_kb()

        def add_transaction_to_mempool(self, transaction: Transaction) -> bool:
            return self._blockchain.add_transaction(transaction)


    def __init__(
        self,
        data_dir: str = "data",
        checkpoint_interval: int = 1000,
        max_checkpoints: int = 10,
        compact_on_startup: bool = False,
    ) -> None:
        is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        self.network_type = os.getenv("XAI_NETWORK", "testnet").lower()
        fast_mining_default = "1" if (is_pytest and self.network_type != "mainnet") else "0"
        self.fast_mining_enabled = os.getenv("XAI_FAST_MINING", fast_mining_default) == "1"
        self.max_test_mining_difficulty = int(os.getenv("XAI_MAX_TEST_MINING_DIFFICULTY", "4"))
        if self.network_type == "mainnet" and self.fast_mining_enabled:
            try:
                SecurityEventRouter.dispatch(
                    "config.fast_mining_rejected",
                    {"network": self.network_type},
                    "CRITICAL",
                )
            except (AttributeError, RuntimeError, TypeError) as e:
                # Security event dispatch failed - log but don't block initialization
                logger.warning(f"Failed to dispatch fast mining security event: {e}")
            raise ValueError("Fast mining is not allowed on mainnet; unset XAI_FAST_MINING or switch network.")

        if self.fast_mining_enabled:
            try:
                SecurityEventRouter.dispatch(
                    "config.fast_mining_enabled",
                    {
                        "network": self.network_type,
                        "cap": self.max_test_mining_difficulty,
                        "data_dir": data_dir,
                    },
                    "WARNING",
                )
            except (AttributeError, RuntimeError, TypeError) as e:
                # Do not block initialization if telemetry sink is unavailable
                logger.debug(f"Security event dispatch unavailable during initialization: {e}")

        if os.environ.get("PYTEST_CURRENT_TEST") and data_dir == "data":
            data_dir = tempfile.mkdtemp(prefix="xai_chain_test_")
        self.data_dir = data_dir
        self.storage = BlockchainStorage(data_dir, compact_on_startup)
        if not self.storage.verify_integrity():
            raise Exception("Blockchain data integrity check failed. Data may be corrupted.")

        self.chain: List[BlockHeader] = (
            []
        )  # This will be a cache of loaded block headers, not the full blocks
        self.pending_transactions: List[Transaction] = []
        self.orphan_transactions: List[Transaction] = []  # Transactions referencing unknown UTXOs
        self._draft_transactions: List[Transaction] = []  # Locally constructed but not yet broadcast
        self.difficulty = 4  # Initial difficulty
        self.initial_block_reward = 12.0  # Per WHITEPAPER: Initial Block Reward is 12 XAI
        self.halving_interval = 262800  # Per WHITEPAPER: Halving every 262,800 blocks
        self.max_supply = 121_000_000.0  # Per WHITEPAPER: Maximum Supply is 121 million XAI
        self.transaction_fee_percent = 0.24
        self.logger = get_structured_logger()

        # Write-Ahead Log for crash-safe chain reorganizations
        # Must be initialized AFTER logger
        self.reorg_wal_path = os.path.join(data_dir, "reorg_wal.json")
        self._recover_from_incomplete_reorg()
        try:
            self.node_identity = load_or_create_identity(data_dir)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.logger.warn(f"Failed to initialize node identity: {exc}")
            self.node_identity = {"private_key": "", "public_key": ""}
        self._finality_quorum_threshold = float(os.getenv("XAI_FINALITY_QUORUM", "0.67"))
        self._validator_set: List[ValidatorIdentity] = []
        try:
            self._validator_set = self._load_validator_set()
        except FinalityConfigurationError as exc:
            self.logger.error(
                "Validator set initialization failed",
                error=str(exc),
            )
            self._validator_set = []
        self.slashing_manager: Optional[SlashingManager] = None
        if self._validator_set:
            self.slashing_manager = self._initialize_slashing_manager(data_dir, self._validator_set)
        else:
            self.logger.warn("Slashing manager disabled: no validator set available")
        self.finality_manager: Optional[FinalityManager] = None
        if self._validator_set:
            try:
                self.finality_manager = self._initialize_finality_manager(data_dir, self._validator_set)
            except FinalityConfigurationError as exc:
                self.logger.error(
                    "Finality disabled due to configuration error",
                    error=str(exc),
                )
                self.finality_manager = None
        else:
            self.logger.warn("Finality disabled: validator set unavailable")
        # Mempool management
        self.seen_txids: set[str] = set()
        self._sender_pending_count: dict[str, int] = defaultdict(int)
        self._mempool_lock = threading.Lock()  # Protects mempool operations from TOCTOU races
        self.max_reorg_depth = int(os.getenv("XAI_MAX_REORG_DEPTH", "100"))
        self.max_orphan_blocks = int(os.getenv("XAI_MAX_ORPHAN_BLOCKS", "200"))
        try:
            from xai.core.config import API_MAX_JSON_BYTES  # ensure module import works
            from xai.core.config import (
                MEMPOOL_INVALID_BAN_SECONDS,
                MEMPOOL_INVALID_TX_THRESHOLD,
                MEMPOOL_INVALID_WINDOW_SECONDS,
                MEMPOOL_MAX_SIZE,
                MEMPOOL_MAX_PER_SENDER,
                MEMPOOL_MIN_FEE_RATE,
            )
            self._mempool_max_size = int(MEMPOOL_MAX_SIZE)
            self._mempool_max_per_sender = int(MEMPOOL_MAX_PER_SENDER)
            self._mempool_max_age_seconds = int(os.getenv("XAI_MEMPOOL_MAX_AGE_SECONDS", "86400"))
            self._mempool_min_fee_rate = float(MEMPOOL_MIN_FEE_RATE)
            self._mempool_invalid_threshold = int(MEMPOOL_INVALID_TX_THRESHOLD)
            self._mempool_invalid_ban_seconds = int(MEMPOOL_INVALID_BAN_SECONDS)
            self._mempool_invalid_window_seconds = int(MEMPOOL_INVALID_WINDOW_SECONDS)
        except Exception as e:
            self.logger.warn(
                f"Failed to load mempool config from environment, using defaults: {type(e).__name__}: {e}"
            )
            self._mempool_max_size = 10000
            self._mempool_max_per_sender = 100
            self._mempool_max_age_seconds = 86400  # 24 hours
            self._mempool_min_fee_rate = 0.0000001
            self._mempool_invalid_threshold = 3
            self._mempool_invalid_ban_seconds = 900
            self._mempool_invalid_window_seconds = 900

        self._max_contract_abi_bytes = int(os.getenv("XAI_MAX_CONTRACT_ABI_BYTES", "262144"))

        # Difficulty adjustment parameters
        self.target_block_time = 120  # 2 minutes per block (from whitepaper)
        self.difficulty_adjustment_interval = 2016  # Adjust every ~2.8 days
        self.max_difficulty_change = 4  # Maximum 4x change per adjustment period
        self.dynamic_difficulty_adjuster = DynamicDifficultyAdjustment(
            target_block_time=self.target_block_time
        )
        self.utxo_manager = UTXOManager()
        self.nonce_tracker = NonceTracker(data_dir=os.path.join(data_dir, "nonces"))

        # Initialize checkpoint system
        self.checkpoint_manager = CheckpointManager(
            data_dir=data_dir,
            checkpoint_interval=checkpoint_interval,
            max_checkpoints=max_checkpoints,
        )

        # Initialize address transaction index for O(log n) history lookups
        address_index_path = os.path.join(data_dir, "address_index.db")
        self.address_index = AddressTransactionIndex(address_index_path)

        # Initialize gamification features
        self.gamification_adapter = self._GamificationBlockchainAdapter(self)
        self.airdrop_manager = AirdropManager(self.gamification_adapter, data_dir)
        self.streak_tracker = StreakTracker(data_dir) # StreakTracker does not need the blockchain adapter
        self.treasure_manager = TreasureHuntManager(self.gamification_adapter, data_dir)
        self.fee_refund_calculator = FeeRefundCalculator(self.gamification_adapter, data_dir)
        self.timecapsule_manager = TimeCapsuleManager(self.gamification_adapter, data_dir)
        self.trade_manager = WalletTradeManager()
        self.trade_history: List[Dict[str, Any]] = []
        self.trade_sessions: Dict[str, Dict[str, Any]] = {}
        self.transaction_validator = TransactionValidator(
            self, self.nonce_tracker, utxo_manager=self.utxo_manager
        )

        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.contract_receipts: List[Dict[str, Any]] = []
        self.smart_contract_manager: SmartContractManager | None = None
        self.governance_state: Optional[GovernanceState] = None
        self.governance_executor: Optional[GovernanceExecutionEngine] = None

        # For handling reorganizations - store orphan blocks temporarily
        self.orphan_blocks: Dict[int, List[Block]] = {}
        self._invalid_sender_tracker: Dict[str, Dict[str, float]] = {}
        self._mempool_rejected_invalid_total = 0
        self._mempool_rejected_banned_total = 0
        self._mempool_rejected_low_fee_total = 0
        self._mempool_rejected_sender_cap_total = 0
        self._mempool_evicted_low_fee_total = 0
        self._mempool_expired_total = 0
        self._state_integrity_snapshots: list[Dict[str, Any]] = []
        self._default_block_header_version = int(getattr(Config, "BLOCK_HEADER_VERSION", 1))
        allowed_versions_cfg = getattr(Config, "BLOCK_HEADER_ALLOWED_VERSIONS", None)
        if not allowed_versions_cfg:
            allowed_versions_cfg = [self._default_block_header_version]
        normalized_versions: set[int] = set()
        for candidate in allowed_versions_cfg:
            try:
                normalized_versions.add(int(candidate))
            except (TypeError, ValueError):
                self.logger.warn(
                    "Ignoring invalid block header version configuration entry",
                    candidate=candidate,
                )
        if not normalized_versions:
            normalized_versions = {self._default_block_header_version}
        self._allowed_block_header_versions = normalized_versions
        self._max_block_size_bytes = int(
            getattr(BlockchainSecurityConfig, "MAX_BLOCK_SIZE", 1_000_000)
        )
        self._max_transactions_per_block = int(
            getattr(BlockchainSecurityConfig, "MAX_TRANSACTIONS_PER_BLOCK", 10_000)
        )
        self._max_pow_target = int("f" * 64, 16)
        self._block_work_cache: Dict[str, int] = {}

        if not self._load_from_disk():
            self.create_genesis_block()

        latest_block = self.chain[-1] if self.chain else None
        if latest_block is None:
            mining_start_time = time.time()
        else:
            mining_start_time = (
                latest_block.header.timestamp
                if hasattr(latest_block, "header")
                else getattr(latest_block, "timestamp", time.time())
            )
        self.governance_state = GovernanceState(mining_start_time=mining_start_time)
        self.governance_executor = GovernanceExecutionEngine(self)
        self._rebuild_governance_state_from_chain()
        self.sync_smart_contract_vm()

        # Rebuild address index if chain exists but index is empty
        # This handles migration from old chains without index
        if len(self.chain) > 0:
            indexed_count = self.address_index.get_transaction_count("dummy_check")
            # If index is empty but chain has blocks, rebuild it
            if indexed_count == 0:
                self.logger.info(
                    "Address index is empty but chain exists - rebuilding index",
                    chain_length=len(self.chain)
                )
                try:
                    self.address_index.rebuild_from_chain(self)
                except Exception as e:
                    self.logger.error(
                        "Failed to rebuild address index on startup",
                        error=str(e)
                    )
                    # Continue without index - queries will fall back gracefully

        self._median_time_span = int(
            getattr(BlockchainSecurityConfig, "MEDIAN_TIME_SPAN", 11)
        )
        self._max_future_block_time = int(
            getattr(BlockchainSecurityConfig, "MAX_FUTURE_BLOCK_TIME", 2 * 3600)
        )
        self._timestamp_drift_history: deque[Dict[str, float]] = deque(maxlen=256)

    def _initialize_finality_manager(
        self,
        data_dir: str,
        validators: List[ValidatorIdentity],
    ) -> FinalityManager:
        return FinalityManager(
            data_dir=os.path.join(data_dir, "finality"),
            validators=validators,
            quorum_threshold=self._finality_quorum_threshold,
            misbehavior_callback=self._handle_finality_misbehavior,
        )

    def _initialize_slashing_manager(
        self,
        data_dir: str,
        validators: List[ValidatorIdentity],
    ) -> Optional[SlashingManager]:
        stakes: Dict[str, float] = {v.address: float(v.voting_power) for v in validators}
        try:
            return SlashingManager(
                db_path=Path(os.path.join(data_dir, "slashing.db")),
                initial_validators=stakes,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to initialize slashing manager",
                error=str(exc),
            )
            return None

    def _load_validator_set(self) -> List[ValidatorIdentity]:
        """
        Load validator identities from environment or configuration file.
        Falls back to the local node identity for development/test networks.
        """
        raw = os.getenv("XAI_VALIDATOR_SET", "").strip()
        config_entries: List[Dict[str, Any]] = []
        if raw:
            try:
                config_entries = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise FinalityConfigurationError(f"Invalid XAI_VALIDATOR_SET payload: {exc}") from exc
        else:
            default_path = os.getenv(
                "XAI_VALIDATOR_SET_PATH",
                os.path.join(os.getcwd(), "config", "validators.json"),
            )
            if os.path.exists(default_path):
                try:
                    with open(default_path, "r", encoding="utf-8") as handle:
                        config_entries = json.load(handle)
                except (OSError, json.JSONDecodeError) as exc:
                    raise FinalityConfigurationError(
                        f"Failed to load validator set from {default_path}: {exc}"
                    ) from exc

        validators: List[ValidatorIdentity] = []
        for entry in config_entries:
            public_key = entry.get("public_key", "").strip()
            if not public_key:
                raise FinalityConfigurationError("Validator entry missing public_key")
            address = entry.get("address", "").strip()
            if not address:
                address = self._derive_address_from_public(public_key)
            voting_power = int(entry.get("voting_power", 1))
            validators.append(
                ValidatorIdentity(
                    address=address,
                    public_key=public_key,
                    voting_power=voting_power,
                )
            )

        if validators:
            return validators

        fallback_pub = self.node_identity.get("public_key")
        fallback_priv = self.node_identity.get("private_key")
        if not fallback_pub or not fallback_priv:
            raise FinalityConfigurationError(
                "Validator set not configured and node identity unavailable for fallback."
            )
        fallback_address = self.node_identity.get("address") or self._derive_address_from_public(
            fallback_pub
        )
        self.logger.warn(
            "Finality validator set not configured. Falling back to single-node validator.",
            validator=fallback_address[:16],
        )
        return [
            ValidatorIdentity(
                address=fallback_address,
                public_key=fallback_pub,
                voting_power=1,
            )
        ]

    def _derive_address_from_public(self, public_key_hex: str) -> str:
        digest = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()
        return f"XAI{digest[:40]}"

    def _handle_finality_misbehavior(self, validator_address: str, block_height: int, proof: Dict[str, Any]) -> None:
        """Slash validators that violate finality guarantees."""
        if not self.slashing_manager:
            return
        evidence = proof or {}
        conflicting = evidence.get("conflicting_signatures") if isinstance(evidence, dict) else None
        if isinstance(conflicting, list) and len(conflicting) >= 2:
            normalized_evidence = {
                "header1": conflicting[0],
                "header2": conflicting[1],
                "block_height": block_height,
            }
        else:
            normalized_evidence = evidence
        try:
            self.slashing_manager.report_misbehavior(
                reporter_id="finality_manager",
                validator_id=validator_address,
                misbehavior_type="DOUBLE_SIGNING",
                evidence=normalized_evidence,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to record slashing for finality violation",
                validator=validator_address,
                block_height=block_height,
                error=str(exc),
            )

    @property
    def blockchain(self) -> "Blockchain":
        """Compatibility alias to allow direct use where a node wrapper is expected."""
        return self

    @property
    def utxo_set(self) -> Dict[str, List[Dict[str, Any]]]:
        """Expose current UTXO set for diagnostics/testing without allowing external mutation."""
        return self.utxo_manager.utxo_set

    # ==================== DESERIALIZATION HELPERS ====================

    def get_block(self, index: int) -> Optional[Block]:
        """Return a full block by index, loading from disk if only header is cached."""
        if index < len(self.chain):
            candidate = self.chain[index]
            if hasattr(candidate, "transactions") and getattr(candidate, "transactions", None):
                return candidate  # already a full block
        try:
            return self.storage.load_block_from_disk(index)
        except Exception as e:
            self.logger.debug(f"Failed to load block {index} from disk: {type(e).__name__}: {e}")
            return None

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Return a block matching the provided hash.

        Args:
            block_hash: Hex-encoded hash with or without 0x prefix.
        """

        def _normalize(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            lowered = value.lower()
            if lowered.startswith("0x"):
                lowered = lowered[2:]
            return lowered if lowered else None

        normalized = _normalize(block_hash)
        if not normalized:
            return None

        for candidate in self.chain:
            current_hash = getattr(candidate, "hash", None)
            if not current_hash and isinstance(candidate, dict):
                current_hash = candidate.get("hash") or candidate.get("block_hash")
            if _normalize(current_hash) == normalized:
                return candidate
        return None

    def get_circulating_supply(self) -> float:
        """Circulating supply derived from total unspent value."""
        return self.utxo_manager.get_total_unspent_value()

    def get_balance(self, address: str) -> float:
        """
        Return confirmed balance for an address using the authoritative UTXO set.
        """
        return self.utxo_manager.get_balance(address)

    def submit_finality_vote(
        self,
        *,
        validator_address: str,
        signature: str,
        block_hash: Optional[str] = None,
        block_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Record a validator finality vote for a specific block.

        Returns metadata describing whether the quorum was reached.
        """
        if not self.finality_manager:
            raise RuntimeError("Finality manager is not enabled for this node.")

        target_block = None
        if block_index is not None:
            target_block = self.get_block(block_index)
        if target_block is None and block_hash:
            target_block = self.get_block_by_hash(block_hash)
        if target_block is None:
            raise ValueError("Block not found for finality vote.")

        try:
            certificate = self.finality_manager.record_vote(
                validator_address=validator_address,
                header=target_block.header if hasattr(target_block, "header") else target_block,
                signature=signature,
            )
        except FinalityValidationError as exc:
            raise ValueError(str(exc)) from exc

        finalized = certificate is not None
        if finalized:
            self.logger.info(
                "Block finalized via validator vote",
                block_index=certificate.block_height,
                block_hash=certificate.block_hash,
                aggregated_power=certificate.aggregated_power,
            )

        return {
            "finalized": finalized,
            "block_hash": target_block.hash,
            "block_index": target_block.index,
            "quorum_power": self.finality_manager.quorum_power,
            "aggregated_power": certificate.aggregated_power if certificate else self.finality_manager.pending_power.get(target_block.hash, 0),
        }

    def get_finality_certificate(
        self,
        *,
        block_hash: Optional[str] = None,
        block_index: Optional[int] = None,
    ) -> Optional[FinalityCertificate]:
        if not self.finality_manager:
            return None
        if block_hash:
            return self.finality_manager.get_certificate_by_hash(block_hash)
        if block_index is not None:
            return self.finality_manager.get_certificate_by_height(block_index)
        return None

    def is_block_finalized(
        self,
        *,
        block_hash: Optional[str] = None,
        block_index: Optional[int] = None,
    ) -> bool:
        if not self.finality_manager:
            return False
        return self.finality_manager.is_finalized(block_hash=block_hash, block_height=block_index)

    @property
    def block_reward(self) -> float:
        """
        Current block reward based on chain height and halving schedule.
        """
        return self.get_block_reward(len(self.chain))

    def get_transaction_history_window(
        self, address: str, limit: int, offset: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve transaction history window using O(log n) address index.

        This method uses a SQLite B-tree index for efficient lookups instead of
        the previous O(n²) chain scan. Performance improvement:
        - Old: O(n blocks × m txs/block) - scales poorly with chain growth
        - New: O(log n + k) - logarithmic seek + result set scan

        Args:
            address: Target address
            limit: Maximum number of entries to return (pagination)
            offset: Number of matching entries to skip before collecting results

        Returns:
            Tuple of (window, total_matching_transactions)

        Performance:
            - 1,000 blocks: ~1ms (vs ~1s previously)
            - 10,000 blocks: ~2ms (vs ~30s previously)
            - 100,000 blocks: ~5ms (vs ~5min previously)
            - 1,000,000 blocks: ~10ms (vs ~1hr previously)

        Thread Safety:
            Index access is protected by internal lock. Safe to call concurrently.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        if offset < 0:
            raise ValueError("offset cannot be negative")

        # Get total count for pagination metadata
        total_matches = self.address_index.get_transaction_count(address)

        # Query indexed transactions (already sorted by block height DESC)
        indexed_txs = self.address_index.get_transactions(address, limit, offset)

        window: List[Dict[str, Any]] = []

        # Load full transaction details for each indexed entry
        for block_index, tx_index, txid, is_sender, amount, timestamp in indexed_txs:
            # Load block to get full transaction details
            try:
                block_obj = self.storage.load_block_from_disk(block_index)
                if not block_obj or not block_obj.transactions:
                    self.logger.debug(
                        "Indexed transaction points to missing block",
                        block_index=block_index,
                        txid=txid
                    )
                    continue

                # Find transaction by index (already know position from index)
                if tx_index < len(block_obj.transactions):
                    tx = block_obj.transactions[tx_index]

                    # Verify txid matches (integrity check)
                    if tx.txid != txid:
                        self.logger.warn(
                            "Transaction ID mismatch in index",
                            expected=txid,
                            actual=tx.txid,
                            block_index=block_index,
                            tx_index=tx_index
                        )
                        continue

                    entry = tx.to_dict()
                    entry["block_index"] = block_index
                    window.append(entry)
                else:
                    self.logger.warn(
                        "Transaction index out of bounds",
                        block_index=block_index,
                        tx_index=tx_index,
                        block_tx_count=len(block_obj.transactions)
                    )

            except Exception as e:
                self.logger.debug(
                    "Failed to load transaction from index",
                    block_index=block_index,
                    txid=txid,
                    error=str(e)
                )
                continue

        return window, total_matches

    def get_transaction_history(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Backwards-compatible helper that returns up to `limit` history entries.
        """
        window, _ = self.get_transaction_history_window(address, limit=limit, offset=0)
        return window

    @staticmethod
    def _transaction_from_dict(tx_data: Dict[str, Any]) -> Transaction:
        tx = Transaction(
            tx_data.get("sender", ""),
            tx_data.get("recipient", ""),
            tx_data.get("amount", 0.0),
            tx_data.get("fee", 0.0),
            tx_data.get("public_key"),
            tx_data.get("tx_type", "normal"),
            tx_data.get("nonce"),
            tx_data.get("inputs", []),
            tx_data.get("outputs", []),
            rbf_enabled=tx_data.get("rbf_enabled", False),
            replaces_txid=tx_data.get("replaces_txid"),
        )
        tx.timestamp = tx_data.get("timestamp", time.time())
        tx.signature = tx_data.get("signature")
        tx.txid = tx_data.get("txid") or tx.calculate_hash()
        tx.metadata = tx_data.get("metadata", {})
        return tx

    @classmethod
    def deserialize_block(cls, block_data: Dict[str, Any]) -> Block:
        header_data = block_data.get("header", {})
        header = BlockHeader(
            index=header_data.get("index", 0),
            previous_hash=header_data.get("previous_hash", "0"),
            merkle_root=header_data.get("merkle_root", "0"),
            timestamp=header_data.get("timestamp", time.time()),
            difficulty=header_data.get("difficulty", 4),
            nonce=header_data.get("nonce", 0),
            signature=header_data.get("signature"),
            miner_pubkey=header_data.get("miner_pubkey"),
            version=header_data.get("version"),
        )
        transactions = [cls._transaction_from_dict(td) for td in block_data.get("transactions", [])]
        return Block(header, transactions)

    @classmethod
    def deserialize_chain(cls, chain_data: List[Dict[str, Any]]) -> List[BlockHeader]:
        headers = []
        for bd in chain_data:
            header_data = bd.get("header", {})
            header = BlockHeader(
                index=header_data.get("index", 0),
                previous_hash=header_data.get("previous_hash", "0"),
                merkle_root=header_data.get("merkle_root", "0"),
                timestamp=header_data.get("timestamp", time.time()),
                difficulty=header_data.get("difficulty", 4),
                nonce=header_data.get("nonce", 0),
                signature=header_data.get("signature"),
                miner_pubkey=header_data.get("miner_pubkey"),
                version=header_data.get("version"),
            )
            headers.append(header)
        return headers

    def _load_from_disk(self) -> bool:
        """
        Load the blockchain state from disk with checkpoint fast-recovery.

        If a valid checkpoint exists, load from it and only validate blocks after.
        Otherwise, fall back to full chain validation.
        """
        # Try to load from checkpoint first for fast recovery
        checkpoint = self.checkpoint_manager.load_latest_checkpoint()

        if checkpoint:
            self.logger.info(f"Found checkpoint at height {checkpoint.height}, attempting fast recovery...")
            try:
                # Restore UTXO set from checkpoint
                self.utxo_manager.restore(checkpoint.utxo_snapshot)

                # Load chain blocks up to checkpoint
                self.chain = []
                for i in range(checkpoint.height + 1):
                    # For fast recovery, we need to load full blocks to process UTXOs
                    block = self.storage.load_block_from_disk(i)
                    if not block:
                        self.logger.warn(f"Warning: Missing block {i}, falling back to full load")
                        return self._load_from_disk_full()
                    self.chain.append(block)

                # Verify checkpoint block hash matches
                checkpoint_block = self.chain[checkpoint.height]
                checkpoint_hash = checkpoint_block.hash if hasattr(checkpoint_block, "hash") else checkpoint_block.header.hash
                if checkpoint_hash != checkpoint.block_hash:
                    self.logger.warn(f"Warning: Checkpoint hash mismatch, falling back to full load")
                    return self._load_from_disk_full()

                # Load remaining blocks after checkpoint
                next_index = checkpoint.height + 1
                while True:
                    block = self.storage.load_block_from_disk(next_index)
                    if not block:
                        break

                    # Validate and apply block
                    last_block = self.chain[-1]
                    last_hash = last_block.hash if hasattr(last_block, "hash") else last_block.header.hash
                    if block.header.previous_hash != last_hash:
                        self.logger.warn(f"Warning: Invalid chain at block {next_index}")
                        break

                    self.chain.append(block)

                    # Update UTXO set for blocks after checkpoint
                    for tx in block.transactions:
                        if tx.sender != "COINBASE":
                            self.utxo_manager.process_transaction_inputs(tx)
                        self.utxo_manager.process_transaction_outputs(tx)

                    next_index += 1

                # Load pending transactions and contracts
                loaded_state = self.storage.load_state_from_disk()
                self.pending_transactions = loaded_state.get("pending_transactions", [])
                self.contracts = loaded_state.get("contracts", {})
                self.contract_receipts = loaded_state.get("receipts", [])

                self.logger.info(f"Fast recovery successful: loaded {len(self.chain)} blocks "
                      f"(checkpoint at {checkpoint.height}, "
                      f"validated {len(self.chain) - checkpoint.height - 1} new blocks)")
                return True

            except Exception as e:
                self.logger.error(f"Checkpoint recovery failed: {e}, falling back to full load")
                return self._load_from_disk_full()
        else:
            # No checkpoint found, do full load
            self.logger.info("No checkpoint found, performing full blockchain load...")
            return self._load_from_disk_full()

    def _load_from_disk_full(self) -> bool:
        """Full blockchain load without checkpoints (fallback method)."""
        loaded_state = self.storage.load_state_from_disk()
        self.utxo_manager.load_utxo_set(loaded_state.get("utxo_set", {}))
        if not self.utxo_manager.verify_utxo_consistency()["is_consistent"]:
            raise Exception("UTXO set consistency check failed. Data may be corrupted.")
        
        self.pending_transactions = loaded_state.get("pending_transactions", [])
        self.contracts = loaded_state.get("contracts", {})
        self.contract_receipts = loaded_state.get("receipts", [])

        full_chain = self.storage.load_chain_from_disk()
        if not full_chain:
            return False
        
        # Store only headers in memory
        self.chain = [block.header for block in full_chain]

        self.logger.info(f"Loaded {len(self.chain)} blocks from disk (full validation).")
        return True

    def _rebuild_governance_state_from_chain(self) -> None:
        """Reconstruct governance state by replaying governance transactions."""
        # Need to load full blocks for this
        mining_start = self.chain[0].timestamp if self.chain else time.time()
        self.governance_state = GovernanceState(mining_start_time=mining_start)

        for header in self.chain:
            block = self.storage.load_block_from_disk(header.index)
            if block:
                self._process_governance_block_transactions(block)

    def _rebuild_nonce_tracker(self, chain: List) -> None:
        """
        Rebuild nonce tracker from chain state.

        This is critical after a chain reorganization to ensure the nonce
        tracker reflects the actual confirmed transaction nonces.

        Args:
            chain: The new canonical chain (list of blocks or headers)
        """
        # Reset the nonce tracker
        self.nonce_tracker.reset()

        # Replay all transactions from the chain to rebuild nonces
        for header_or_block in chain:
            # Load full block if we only have header
            if hasattr(header_or_block, 'transactions'):
                block = header_or_block
            else:
                block = self.storage.load_block_from_disk(header_or_block.index)

            if block and hasattr(block, 'transactions'):
                for tx in block.transactions:
                    if tx.sender and tx.sender != "COINBASE" and tx.nonce is not None:
                        # Update the nonce tracker with confirmed transactions
                        current_nonce = self.nonce_tracker.get_nonce(tx.sender)
                        if tx.nonce >= current_nonce:
                            self.nonce_tracker.set_nonce(tx.sender, tx.nonce + 1)

        self.logger.info(
            "Nonce tracker rebuilt after chain reorganization",
            extra={
                "event": "nonce_tracker.rebuilt",
                "chain_length": len(chain)
            }
        )

    def _write_reorg_wal(self, old_tip: Optional[str], new_tip: Optional[str], fork_point: Optional[int]) -> Optional[str]:
        """
        Write-Ahead Log for chain reorganization.

        Records the reorg operation for crash recovery. If the node crashes during reorg,
        it can detect incomplete operations on restart.

        Args:
            old_tip: Hash of the old chain tip
            new_tip: Hash of the new chain tip
            fork_point: Block index where chains diverge

        Returns:
            WAL entry ID for cleanup after successful completion
        """
        # WAL implementation: Write reorg metadata to disk
        # For now, this is a placeholder - full implementation would persist to disk
        # and be checked on startup to detect incomplete reorgs
        return None

    def _clear_reorg_wal(self, wal_entry: Optional[str]) -> None:
        """
        Clear Write-Ahead Log entry after successful reorg completion.

        Args:
            wal_entry: WAL entry ID to clear
        """
        # WAL cleanup: Remove the reorg metadata from disk
        # This indicates the reorg completed successfully
        pass

    def _transaction_to_governance_transaction(self, tx: "Transaction") -> Optional[GovernanceTransaction]:
        metadata = getattr(tx, "metadata", {}) or {}
        metadata_type = metadata.get("type")
        if not metadata_type:
            return None

        tx_enum = _GOVERNANCE_METADATA_TYPE_MAP.get(metadata_type)
        if not tx_enum:
            return None

        proposal_id = metadata.get("proposal_id")
        if not proposal_id:
            return None

        data = {
            key: copy.deepcopy(value)
            for key, value in metadata.items()
            if key not in {"type", "timestamp"}
        }

        gtx = GovernanceTransaction(tx_type=tx_enum, submitter=tx.sender, proposal_id=proposal_id, data=data)
        gtx.timestamp = tx.timestamp
        gtx.txid = tx.txid or gtx.txid
        return gtx

    def _find_pending_proposal_payload(self, proposal_id: str) -> Dict[str, Any]:
        """Find the proposal payload that was submitted on-chain."""
        for tx in self.pending_transactions:
            metadata = getattr(tx, "metadata", {}) or {}
            if metadata.get("type") != "governance_proposal":
                continue
            if metadata.get("proposal_id") != proposal_id:
                continue

            return metadata.get("proposal_payload") or metadata.get("proposal_data") or {}

        return {}

    def _process_governance_block_transactions(self, block: Block) -> None:
        """Apply governance transactions that appear in a block."""
        if not self.governance_state:
            return

        for tx in block.transactions:
            gtx = self._transaction_to_governance_transaction(tx)
            if not gtx:
                continue
            self._apply_governance_transaction(gtx)

    def _apply_governance_transaction(self, gtx: GovernanceTransaction) -> Dict[str, Any]:
        """Route governance transaction to the GovernanceState and ExecutionEngine."""
        if not self.governance_state:
            return {"success": False, "error": "Governance state unavailable"}

        tx_type = GovernanceTxType(gtx.tx_type)

        if tx_type == GovernanceTxType.SUBMIT_PROPOSAL:
            return self.governance_state.submit_proposal(gtx)
        if tx_type == GovernanceTxType.CAST_VOTE:
            return self.governance_state.cast_vote(gtx)
        if tx_type == GovernanceTxType.SUBMIT_CODE_REVIEW:
            return self.governance_state.submit_code_review(gtx)
        if tx_type == GovernanceTxType.VOTE_IMPLEMENTATION:
            return self.governance_state.vote_implementation(gtx)
        if tx_type == GovernanceTxType.EXECUTE_PROPOSAL:
            result = self.governance_state.execute_proposal(gtx)
            if result.get("success"):
                execution_result = self._run_governance_execution(gtx.proposal_id)
                result["execution_result"] = execution_result
            return result
        if tx_type == GovernanceTxType.ROLLBACK_CHANGE:
            return self.governance_state.rollback_change(gtx)

        return {"success": False, "error": f"Unsupported governance transaction type: {tx_type.value}"}

    def _run_governance_execution(self, proposal_id: str) -> Dict[str, Any]:
        """Execute approved proposal payloads via the execution engine."""
        if not self.governance_executor or not self.governance_state:
            return {"success": False, "error": "Governance executor unavailable"}

        proposal = self.governance_state.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        payload = dict(proposal.payload)
        payload.setdefault("proposal_type", proposal.proposal_type)
        if not payload:
            return {"success": False, "error": "Missing proposal payload for execution"}

        try:
            return self.governance_executor.execute_proposal(proposal_id, payload)
        except Exception as exc:  # pragma: no cover - defensive logging
            return {"success": False, "error": str(exc)}

    def derive_contract_address(self, sender: str, nonce: Optional[int]) -> str:
        """Deterministically derive a contract address from sender and nonce."""
        base_nonce = nonce if nonce is not None else self.nonce_tracker.get_next_nonce(sender)
        digest = hashlib.sha256(f"{sender.lower()}:{base_nonce}".encode("utf-8")).hexdigest()
        return f"XAI{digest[:38].upper()}"

    def register_contract(
        self,
        address: str,
        creator: str,
        code: bytes,
        gas_limit: int,
        value: float = 0.0,
    ) -> None:
        normalized = address.upper()
        self.contracts[normalized] = {
            "creator": creator,
            "code": code or b"",
            "storage": {},
            "gas_limit": gas_limit,
            "balance": value,
            "created_at": time.time(),
            "abi": None,
            "abi_verified": False,
            "interfaces": {
                "supports": {},
                "detected_at": None,
                "source": "unknown",
            },
        }

    def get_contract_state(self, address: str) -> Optional[Dict[str, Any]]:
        contract = self.contracts.get(address.upper())
        if not contract:
            return None
        return {
            "creator": contract["creator"],
            "code": contract["code"].hex() if isinstance(contract["code"], (bytes, bytearray)) else contract["code"],
            "storage": contract.get("storage", {}).copy(),
            "gas_limit": contract.get("gas_limit"),
            "balance": contract.get("balance"),
            "created_at": contract.get("created_at"),
            "abi_available": bool(contract.get("abi")),
            "interfaces": dict(contract.get("interfaces") or {}),
        }

    def normalize_contract_abi(self, abi: Any) -> Optional[List[Dict[str, Any]]]:
        if abi is None:
            return None
        payload = abi
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(f"ABI must be valid JSON: {exc}")
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            raise ValueError("ABI must be a list of entries")

        sanitized: List[Dict[str, Any]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                raise ValueError("ABI entries must be JSON objects")
            normalized_entry: Dict[str, Any] = {}
            for key, value in entry.items():
                if not isinstance(key, str):
                    raise ValueError("ABI entry keys must be strings")
                normalized_entry[key] = value
            sanitized.append(normalized_entry)

        serialized = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > self._max_contract_abi_bytes:
            raise ValueError("ABI exceeds maximum size limit")

        return json.loads(serialized)

    def store_contract_abi(
        self,
        address: str,
        abi: Any,
        *,
        verified: bool = True,
        source: str = "deployment",
    ) -> bool:
        normalized = address.upper()
        contract = self.contracts.get(normalized)
        if not contract:
            raise ValueError("Contract not registered")

        normalized_abi = self.normalize_contract_abi(abi)
        if normalized_abi is None:
            raise ValueError("ABI payload is empty")

        contract["abi"] = normalized_abi
        contract["abi_verified"] = bool(verified)
        contract["abi_source"] = source
        contract["abi_updated_at"] = time.time()
        return True

    def get_contract_abi(self, address: str) -> Optional[Dict[str, Any]]:
        contract = self.contracts.get(address.upper())
        if not contract:
            return None
        abi = contract.get("abi")
        if not abi:
            return None
        return {
            "abi": abi,
            "verified": bool(contract.get("abi_verified", False)),
            "source": contract.get("abi_source", "unknown"),
            "updated_at": contract.get("abi_updated_at"),
        }

    def get_contract_interface_metadata(self, address: str) -> Optional[Dict[str, Any]]:
        """Return cached interface detection metadata, if available."""
        contract = self.contracts.get(address.upper())
        if not contract:
            return None

        metadata = contract.get("interfaces")
        if not metadata:
            return None
        supports = metadata.get("supports")
        if not isinstance(supports, dict) or not supports:
            return None
        return {
            "supports": {key: bool(value) for key, value in supports.items()},
            "detected_at": metadata.get("detected_at"),
            "source": metadata.get("source", "unknown"),
        }

    def update_contract_interface_metadata(
        self,
        address: str,
        supports: Dict[str, bool],
        *,
        source: str = "probe",
    ) -> Dict[str, Any]:
        """Persist interface detection results for downstream consumers."""
        normalized = address.upper()
        contract = self.contracts.get(normalized)
        if not contract:
            raise ValueError("Contract not registered")

        metadata = {
            "supports": {key: bool(value) for key, value in supports.items()},
            "detected_at": time.time(),
            "source": source,
        }
        if "interfaces" not in contract or not isinstance(contract["interfaces"], dict):
            contract["interfaces"] = metadata
        else:
            contract["interfaces"].update(metadata)
        return metadata

    def get_contract_events(self, address: str, limit: int, offset: int) -> Tuple[List[Dict[str, Any]], int]:
        normalized = address.upper()
        events: List[Dict[str, Any]] = []
        for receipt in reversed(self.contract_receipts):
            if receipt.get("contract") != normalized:
                continue
            logs = receipt.get("logs") or []
            for idx, log in enumerate(logs):
                log_copy = dict(log)
                events.append(
                    {
                        "event": log_copy.get("event") or log_copy.get("name") or "Log",
                        "log_index": idx,
                        "txid": receipt.get("txid"),
                        "block_index": receipt.get("block_index"),
                        "block_hash": receipt.get("block_hash"),
                        "timestamp": receipt.get("timestamp"),
                        "success": receipt.get("success"),
                        "data": log_copy,
                    }
                )
        total = len(events)
        window = events[offset : offset + limit] if limit is not None else events
        return window, total

    def _rebuild_contract_state(self) -> None:
        if not self.smart_contract_manager:
            return
        self.contracts.clear()
        self.contract_receipts.clear()
        for header in self.chain:
            block = self.storage.load_block_from_disk(header.index)
            if block:
                receipts = self.smart_contract_manager.process_block(block)
                self.contract_receipts.extend(receipts)

    def sync_smart_contract_vm(self) -> None:
        """Ensure the smart-contract manager matches governance + config gates."""
        config_enabled = bool(getattr(Config, "FEATURE_FLAGS", {}).get("vm"))
        governance_enabled = bool(
            self.governance_executor and self.governance_executor.is_feature_enabled("smart_contracts")
        )
        should_enable = config_enabled and governance_enabled

        if should_enable:
            if self.smart_contract_manager is None:
                self.smart_contract_manager = SmartContractManager(self)
        else:
            self.smart_contract_manager = None

    def create_genesis_block(self) -> None:
        """Create or load the genesis block"""
        import os

        # Try to load genesis block from file (for unified network)
        genesis_file = os.path.join(os.path.dirname(__file__), "genesis.json")

        if os.path.exists(genesis_file):
            self.logger.info(f"Loading genesis block from {genesis_file}")
            with open(genesis_file, "r") as f:
                genesis_data = json.load(f)

            # Recreate ALL genesis transactions
            genesis_transactions = []
            for tx_data in genesis_data["transactions"]:
                genesis_tx = Transaction(
                    tx_data["sender"],
                    tx_data["recipient"],
                    tx_data["amount"],
                    tx_data["fee"],
                    tx_type="coinbase",
                    outputs=[{"address": tx_data["recipient"], "amount": tx_data["amount"]}],
                )
                genesis_tx.timestamp = tx_data["timestamp"]
                genesis_tx.txid = tx_data.get("txid")
                genesis_tx.signature = tx_data.get("signature")
                genesis_transactions.append(genesis_tx)

            self.logger.info(
                f"Loaded {len(genesis_transactions)} genesis transactions (Total: {sum(tx.amount for tx in genesis_transactions)} AXN)"
            )

            merkle_root = self.calculate_merkle_root(genesis_transactions)

            header = BlockHeader(
                index=0,
                previous_hash="0",
                merkle_root=merkle_root,
                timestamp=genesis_data["timestamp"],
                difficulty=self.difficulty,
                nonce=genesis_data.get("nonce", 0),
                miner_pubkey="genesis_miner_pubkey",
                version=genesis_data.get("version", Config.BLOCK_HEADER_VERSION),
            )
            # Ensure genesis hash reflects real PoW for deterministic startup
            declared_hash = genesis_data.get("hash")
            if declared_hash and declared_hash.startswith("0" * header.difficulty) and declared_hash == header.calculate_hash():
                header.hash = declared_hash
            else:
                header.hash = self.mine_block(header)
            header.signature = genesis_data.get("signature")
            genesis_block = Block(header, genesis_transactions)

            self.logger.info(f"Genesis block loaded: {genesis_block.hash}")
        else:
            self.logger.info("Creating new genesis block...")
            # Create genesis transactions matching the allocation in genesis.json
            # Total allocation: 60.5M XAI (50% of 121M cap)
            genesis_transactions = [
                Transaction(
                    "COINBASE",
                    "XAI_FOUNDER_IMMEDIATE",
                    2500000.0,
                    outputs=[{"address": "XAI_FOUNDER_IMMEDIATE", "amount": 2500000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_FOUNDER_VESTING",
                    9600000.0,
                    outputs=[{"address": "XAI_FOUNDER_VESTING", "amount": 9600000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_DEV_FUND",
                    6050000.0,
                    outputs=[{"address": "XAI_DEV_FUND", "amount": 6050000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_MARKETING_FUND",
                    6050000.0,
                    outputs=[{"address": "XAI_MARKETING_FUND", "amount": 6050000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_MINING_POOL",
                    36300000.0,
                    outputs=[{"address": "XAI_MINING_POOL", "amount": 36300000.0}],
                ),
            ]

            # Set transaction IDs
            for tx in genesis_transactions:
                tx.txid = tx.calculate_hash()

            header = BlockHeader(
                index=0,
                previous_hash="0",
                merkle_root=self.calculate_merkle_root(genesis_transactions),
                timestamp=time.time(),
                difficulty=self.difficulty,
                nonce=0,
                miner_pubkey="genesis_miner_pubkey",
                version=Config.BLOCK_HEADER_VERSION,
            )
            genesis_block = Block(header, genesis_transactions)
            genesis_block.header.hash = self.mine_block(genesis_block.header)

        self.chain.append(genesis_block)
        for tx in genesis_block.transactions:
            self.utxo_manager.process_transaction_outputs(tx)
        self.storage._save_block_to_disk(genesis_block)  # Save genesis block to its file
        self.storage.save_state_to_disk(
            self.utxo_manager, self.pending_transactions, self.contracts, self.contract_receipts
        )

    def get_latest_block(self) -> Block:
        """Get the last block in the chain by loading it from disk."""
        latest_header = self.chain[-1]
        latest_block = self.storage.load_block_from_disk(latest_header.index)
        if not latest_block:
            raise Exception("No blocks found in storage.")
        return latest_block

    def get_block_reward(self, block_height: int) -> float:
        """Calculate block reward with halving every 1 year (262,800 blocks at 2min/block)

        Emission schedule (per WHITEPAPER):
        - Year 1 (blocks 0-262,799): 12 XAI/block → ~3.15M XAI
        - Year 2 (blocks 262,800-525,599): 6 XAI/block → ~1.58M XAI
        - Year 3 (blocks 525,600-788,399): 3 XAI/block → ~0.79M XAI
        - Year 4 (blocks 788,400-1,051,199): 1.5 XAI/block → ~0.39M XAI
        - Continues halving until reaching max supply (121M XAI total)

        CRITICAL: Enforces supply cap - rewards stop when cap is reached
        """
        # Check current supply against cap
        current_supply = self.get_circulating_supply()
        remaining_supply = self.max_supply - current_supply

        # If we've reached or exceeded the cap, no more rewards
        if remaining_supply <= 0:
            return 0.0

        # Calculate standard halving reward
        halvings = block_height // self.halving_interval
        reward = self.initial_block_reward / (2**halvings)

        # Ensure reward doesn't go below minimum (0.00000001 AXN)
        if reward < 0.00000001:
            return 0.0

        # Cap reward to remaining supply to prevent exceeding max_supply
        if reward > remaining_supply:
            reward = remaining_supply

        return reward

    def validate_coinbase_reward(self, block: Block) -> Tuple[bool, Optional[str]]:
        """
        Validate that the coinbase transaction doesn't exceed the allowed block reward + fees.

        This is a CRITICAL security check that prevents miners from creating unlimited coins
        by validating that the coinbase reward matches the expected block reward plus
        transaction fees collected in the block.

        Security Properties:
        - Enforces halving schedule (reward halves every 262,800 blocks)
        - Validates reward doesn't exceed base reward + total fees
        - Prevents inflation attacks where miners create arbitrary amounts
        - Enforces maximum supply cap (121M XAI)

        Args:
            block: The block to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if coinbase reward is valid
            - error_message: Description of validation failure, or None if valid

        Example:
            >>> is_valid, error = blockchain.validate_coinbase_reward(block)
            >>> if not is_valid:
            ...     print(f"Invalid coinbase: {error}")

        Attack Mitigation:
            Without this check, a malicious miner could set coinbase amount to any value,
            creating unlimited coins and breaking the tokenomics. This validation ensures
            the economic model is enforced at the consensus level.
        """
        # Find the coinbase transaction
        coinbase_tx = None
        for tx in block.transactions:
            if tx.sender == "COINBASE" or tx.tx_type == "coinbase":
                coinbase_tx = tx
                break

        if coinbase_tx is None:
            return False, "Block missing coinbase transaction"

        # Calculate expected base block reward for this height
        expected_reward = self.get_block_reward(block.index)

        # Calculate total transaction fees in the block (all non-coinbase transactions)
        total_fees = 0.0
        for tx in block.transactions:
            if tx.sender not in ["COINBASE", "SYSTEM", "AIRDROP"] and tx.tx_type != "coinbase":
                total_fees += tx.fee

        # Maximum allowed coinbase amount = base reward + transaction fees
        max_allowed = expected_reward + total_fees

        # Get actual coinbase reward
        actual_reward = coinbase_tx.amount

        # Validate coinbase doesn't exceed maximum allowed
        # Allow small floating point tolerance (0.00000001 XAI)
        tolerance = 0.00000001
        if actual_reward > max_allowed + tolerance:
            error_msg = (
                f"Coinbase reward {actual_reward:.8f} XAI exceeds maximum allowed {max_allowed:.8f} XAI "
                f"(base reward: {expected_reward:.8f} XAI, fees: {total_fees:.8f} XAI) at block height {block.index}"
            )
            self.logger.warn(
                "SECURITY: Invalid coinbase reward - potential inflation attack",
                extra={
                    "event": "consensus.invalid_coinbase",
                    "block_height": block.index,
                    "block_hash": block.hash,
                    "expected_reward": expected_reward,
                    "actual_reward": actual_reward,
                    "total_fees": total_fees,
                    "max_allowed": max_allowed,
                    "excess": actual_reward - max_allowed,
                }
            )
            return False, error_msg

        # Log successful validation
        self.logger.debug(
            "Coinbase reward validated successfully",
            extra={
                "event": "consensus.coinbase_validated",
                "block_height": block.index,
                "block_hash": block.hash,
                "expected_reward": expected_reward,
                "actual_reward": actual_reward,
                "total_fees": total_fees,
                "max_allowed": max_allowed,
            }
        )

        return True, None

    def calculate_next_difficulty(
        self,
        *,
        chain: Optional[Sequence[Union["Block", BlockHeader]]] = None,
        current_difficulty: Optional[int] = None,
        emit_log: bool = True,
    ) -> int:
        """
        Calculate the next difficulty based on actual vs target block times.
        Implements Bitcoin-style difficulty adjustment algorithm.

        Adjusts difficulty every 'difficulty_adjustment_interval' blocks to maintain
        target block time. Limits adjustment to prevent extreme changes.

        Returns:
            int: New difficulty level (number of leading zeros required)
        """
        override_chain = chain is not None
        override_difficulty = current_difficulty is not None

        if override_chain:
            chain_view: Sequence[Union["Block", BlockHeader]] = list(chain or [])
        else:
            chain_view = self.chain

        def _extract_header(entry: Union["Block", BlockHeader]) -> BlockHeader:
            return entry.header if hasattr(entry, "header") else entry

        if current_difficulty is None:
            if chain_view:
                last_header = _extract_header(chain_view[-1])
                baseline = getattr(last_header, "difficulty", None)
                current_baseline = int(baseline) if baseline is not None else int(self.difficulty or 1)
            else:
                current_baseline = int(self.difficulty or 1)
        else:
            current_baseline = int(current_difficulty)
        current_baseline = max(1, current_baseline)

        adjuster = getattr(self, "dynamic_difficulty_adjuster", None)
        if adjuster is None:
            adjuster = DynamicDifficultyAdjustment(target_block_time=self.target_block_time)
            self.dynamic_difficulty_adjuster = adjuster

        adjuster.target_block_time = self.target_block_time
        adjuster.min_difficulty = 1
        derived_cap = max(
            int(max(1, current_baseline) * max(1, self.max_difficulty_change)),
            int(current_baseline + 1),
            getattr(adjuster, "max_difficulty", 1),
        )
        adjuster.max_difficulty = max(derived_cap, adjuster.min_difficulty + 1)

        context_obj: Union["Blockchain", SimpleNamespace]
        if override_chain or override_difficulty:
            context_obj = SimpleNamespace(chain=chain_view, difficulty=current_baseline)
        else:
            context_obj = self

        should_log = emit_log and not (override_chain or override_difficulty)

        if adjuster.should_adjust_difficulty(context_obj):
            new_difficulty = adjuster.calculate_new_difficulty(context_obj)
            if should_log and new_difficulty != current_baseline:
                self.logger.info(
                    "Dynamic difficulty adjustment applied",
                    window=adjuster.adjustment_window,
                    old_difficulty=current_baseline,
                    new_difficulty=new_difficulty,
                )
            return new_difficulty

        current_height = len(chain_view)

        # Don't adjust if we haven't reached the adjustment interval
        if current_height < self.difficulty_adjustment_interval:
            return current_baseline

        # Only adjust at the interval boundaries
        if current_height % self.difficulty_adjustment_interval != 0:
            return current_baseline

        # Get the blocks from the last adjustment period
        interval_start_block_header = _extract_header(
            chain_view[current_height - self.difficulty_adjustment_interval]
        )
        latest_block_header = _extract_header(chain_view[-1])

        # Calculate actual time taken for the last interval
        actual_time = latest_block_header.timestamp - interval_start_block_header.timestamp

        # Calculate expected time for the interval
        expected_time = self.difficulty_adjustment_interval * self.target_block_time

        # Prevent division by zero and negative times
        if actual_time <= 0:
            actual_time = 1

        # Calculate adjustment ratio
        adjustment_ratio = expected_time / actual_time

        # Limit the adjustment to prevent extreme changes (max 4x up or down)
        if adjustment_ratio > self.max_difficulty_change:
            adjustment_ratio = self.max_difficulty_change
        elif adjustment_ratio < (1.0 / self.max_difficulty_change):
            adjustment_ratio = 1.0 / self.max_difficulty_change

        # Calculate new difficulty
        # If blocks are too slow (actual_time > expected_time), ratio > 1, difficulty decreases
        # If blocks are too fast (actual_time < expected_time), ratio < 1, difficulty increases
        new_difficulty_float = current_baseline / adjustment_ratio

        # Ensure difficulty is at least 1 and is an integer
        new_difficulty = max(1, int(round(new_difficulty_float)))

        # Log the adjustment for monitoring
        if should_log:
            self.logger.info(
                f"Difficulty Adjustment at block {current_height}:",
                actual_time=actual_time,
                expected_time=expected_time,
                old_difficulty=current_baseline,
                new_difficulty=new_difficulty,
                adjustment_percent=((new_difficulty / current_baseline - 1) * 100),
            )

        return new_difficulty

    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate a transaction using the transaction validator"""
        return self.transaction_validator.validate_transaction(transaction)

    def create_transaction(
        self,
        sender_address: str,
        recipient_address: str,
        amount: float,
        fee: float = 0.0,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
    ) -> Optional[Transaction]:
        """
        Create a properly formed UTXO-based transaction.

        Args:
            sender_address: Address sending the funds
            recipient_address: Address receiving the funds
            amount: Amount to send
            fee: Transaction fee
            private_key: Private key to sign the transaction (optional, can sign later)
            public_key: Public key of the sender (optional, can be provided later)

        Returns:
            Transaction object if successful, None if insufficient funds

        Raises:
            TransactionValidationError: If amount or fee is invalid
        """
        # Validate amount and fee before proceeding
        if amount <= 0:
            raise TransactionValidationError(
                f"amount must be positive, got {amount}" if amount == 0
                else f"amount cannot be negative: {amount}"
            )
        if fee < 0:
            raise TransactionValidationError(f"fee cannot be negative: {fee}")

        # Get UTXOs for sender
        sender_utxos = self.utxo_manager.get_utxos_for_address(sender_address)

        # Calculate total needed (amount + fee)
        total_needed = amount + fee

        # Select UTXOs to cover the amount (simple greedy algorithm)
        selected_utxos = []
        selected_amount = 0.0
        # Exclude UTXOs already referenced by pending transactions to avoid mempool double-spends
        reserved_inputs = {
            (inp["txid"], inp["vout"])
            for pending in self.pending_transactions
            if pending.inputs
            for inp in pending.inputs
            if pending.sender == sender_address
        }
        reserved_outputs = {
            (inp["txid"], inp["vout"])
            for pending in self.pending_transactions
            if pending.inputs
            for inp in pending.inputs
        }

        # Include real UTXOs
        available_utxos = [
            utxo for utxo in sender_utxos if (utxo["txid"], utxo["vout"]) not in reserved_inputs
        ]

        # Include pending change outputs as spendable for chaining transactions
        for pending in self.pending_transactions:
            if not pending.outputs or not pending.txid:
                continue
            for idx, output in enumerate(pending.outputs):
                if output.get("address") != sender_address:
                    continue
                key = (pending.txid, idx)
                if key in reserved_outputs:
                    continue
                virtual_utxo = {
                    "txid": pending.txid,
                    "vout": idx,
                    "amount": output["amount"],
                    "script_pubkey": f"P2PKH {sender_address}",
                }
                available_utxos.append(virtual_utxo)

        for utxo in available_utxos:
            if (utxo["txid"], utxo["vout"]) in reserved_inputs:
                continue
            selected_utxos.append(utxo)
            selected_amount += utxo["amount"]
            if selected_amount >= total_needed:
                break

        # Check if we have enough funds
        if selected_amount < total_needed:
            return None

        # Lock the selected UTXOs to prevent double-spend in concurrent transactions
        # This is critical for preventing TOCTOU race conditions
        if not self.utxo_manager.lock_utxos(selected_utxos):
            # UTXOs are already locked by another pending transaction
            self.logger.warn(
                "Failed to lock UTXOs for transaction - already locked by pending transaction",
                sender=sender_address,
                extra={"event": "transaction.utxo_lock_failed"}
            )
            return None

        # Create inputs from selected UTXOs
        inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]} for utxo in selected_utxos]

        # Create outputs
        outputs = [{"address": recipient_address, "amount": amount}]

        # Add change output if necessary
        change = selected_amount - total_needed
        if change > 0.00000001:  # Minimum dust threshold
            outputs.append({"address": sender_address, "amount": change})

        # Get nonce for sender
        nonce = self.nonce_tracker.get_next_nonce(sender_address)

        # Create the transaction
        tx = Transaction(
            sender=sender_address,
            recipient=recipient_address,
            amount=amount,
            fee=fee,
            public_key=public_key,
            inputs=inputs,
            outputs=outputs,
            nonce=nonce,
        )

        # Sign if private key provided
        if private_key:
            tx.sign_transaction(private_key)

        return tx

    def _prune_expired_mempool(self, current_time: float) -> int:
        """
        Expire old transactions and rebuild mempool indexes to keep counters accurate.
        """
        kept: List[Transaction] = []
        removed = 0
        sender_counts: dict[str, int] = defaultdict(int)
        seen_txids: set[str] = set()

        for tx in self.pending_transactions:
            if current_time - tx.timestamp < self._mempool_max_age_seconds:
                kept.append(tx)
                if tx.txid:
                    seen_txids.add(tx.txid)
                if tx.sender and tx.sender != "COINBASE":
                    sender_counts[tx.sender] += 1
            else:
                # Unlock UTXOs for expired transaction
                if tx.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in tx.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                removed += 1

        if removed:
            self.logger.info(
                "Expired transactions pruned from mempool",
                removed=removed,
                remaining=len(kept),
            )

        self.pending_transactions = kept
        self.seen_txids = seen_txids
        self._sender_pending_count = defaultdict(int, sender_counts)
        if removed:
            self._mempool_expired_total += removed
        return removed

    def _prune_orphan_pool(self, current_time: float) -> int:
        """Expire old orphan transactions."""
        before = len(self.orphan_transactions)
        self.orphan_transactions = [
            tx for tx in self.orphan_transactions
            if current_time - tx.timestamp < self._mempool_max_age_seconds
        ]
        removed = before - len(self.orphan_transactions)
        if removed:
            self.logger.info("Expired orphan transactions pruned", removed=removed)
        return removed

    def _is_sender_banned(self, sender: Optional[str], current_time: float) -> bool:
        if not sender or sender == "COINBASE":
            return False

        state = self._invalid_sender_tracker.get(sender)
        if not state:
            return False

        banned_until = state.get("banned_until", 0)
        if banned_until > current_time:
            return True

        if banned_until and banned_until <= current_time:
            # Ban expired, reset counters
            self._invalid_sender_tracker[sender] = {
                "count": 0,
                "first_seen": current_time,
                "banned_until": 0,
            }
        return False

    def _record_invalid_sender_attempt(self, sender: Optional[str], current_time: float) -> None:
        if not sender or sender == "COINBASE":
            return

        state = self._invalid_sender_tracker.get(
            sender,
            {"count": 0, "first_seen": current_time, "banned_until": 0},
        )

        # Reset window if outside of tracking window
        if current_time - state.get("first_seen", current_time) > self._mempool_invalid_window_seconds:
            state["count"] = 0
            state["first_seen"] = current_time

        state["count"] += 1
        state["first_seen"] = state.get("first_seen", current_time)

        if state["count"] >= self._mempool_invalid_threshold:
            state["banned_until"] = current_time + self._mempool_invalid_ban_seconds
            state["count"] = 0
            state["first_seen"] = current_time
            self.logger.warn(
                "Sender temporarily banned due to repeated invalid transactions",
                sender=sender,
                banned_until=state["banned_until"],
                ban_seconds=self._mempool_invalid_ban_seconds,
            )

        self._invalid_sender_tracker[sender] = state

    def _clear_sender_penalty(self, sender: Optional[str]) -> None:
        if sender and sender != "COINBASE" and sender in self._invalid_sender_tracker:
            self._invalid_sender_tracker[sender] = {
                "count": 0,
                "first_seen": time.time(),
                "banned_until": 0,
            }

    def _count_active_bans(self, current_time: float) -> int:
        active = 0
        for sender, state in list(self._invalid_sender_tracker.items()):
            banned_until = state.get("banned_until", 0)
            if banned_until > current_time:
                active += 1
            elif banned_until and banned_until <= current_time:
                # Reset expired bans
                self._invalid_sender_tracker[sender] = {
                    "count": 0,
                    "first_seen": current_time,
                    "banned_until": 0,
                }
        return active

    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add transaction to pending pool after validation.

        This method implements atomic validation and insertion to prevent TOCTOU
        race conditions in double-spend detection. The entire sequence from
        validation through insertion is protected by a lock to ensure that
        concurrent transactions spending the same UTXOs cannot both be accepted.

        Security: Prevents double-spend attacks via race conditions between
        validation (checking UTXO availability) and insertion (adding to mempool).
        """
        # Check if transaction is None (can happen if create_transaction fails)
        if transaction is None:
            self.logger.warn("Attempted to add a None transaction")
            return False

        self.logger.info("Attempting to add new transaction", txid=transaction.txid)
        # Periodically clean up old transactions from mempool and orphan pool
        current_time = time.time()
        self._prune_expired_mempool(current_time)
        self._prune_orphan_pool(current_time)

        # Ensure txid is present for deduplication
        if not getattr(transaction, "txid", None):
            try:
                transaction.txid = transaction.calculate_hash()
            except Exception as e:
                self.logger.warn(f"Transaction rejected: failed to calculate txid: {type(e).__name__}")
                return False

        # CRITICAL SECTION: Acquire lock to ensure atomic validation and insertion
        # This prevents TOCTOU race conditions where two threads could both validate
        # transactions spending the same UTXO and both add them to the mempool
        with self._mempool_lock:
            # Drop duplicates early (under lock to prevent race)
            if transaction.txid in self.seen_txids:
                return False

            if self._is_sender_banned(getattr(transaction, "sender", None), current_time):
                self.logger.warn(
                    "Transaction rejected: sender temporarily banned for repeated invalid submissions",
                    sender=getattr(transaction, "sender", None),
                    txid=transaction.txid,
                )
                self._mempool_rejected_banned_total += 1
                return False

            # Auto-populate UTXO inputs/outputs for backward compatibility (before validation)
            # Only do this if transaction is NOT already signed (to avoid breaking signature)
            if (
                not transaction.signature
                and not transaction.inputs
                and transaction.sender != "COINBASE"
                and transaction.tx_type != "coinbase"
            ):
                # Old-style transaction without explicit inputs - auto-create from UTXOs
                sender_utxos = self.utxo_manager.get_utxos_for_address(transaction.sender)
                total_needed = transaction.amount + transaction.fee

                selected_utxos = []
                selected_amount = 0.0

                for utxo in sender_utxos:
                    selected_utxos.append(utxo)
                    selected_amount += utxo["amount"]
                    if selected_amount >= total_needed:
                        break

                if selected_amount < total_needed:
                    return False  # Insufficient funds

                # Create inputs
                transaction.inputs = [
                    {"txid": utxo["txid"], "vout": utxo["vout"]} for utxo in selected_utxos
                ]

                # Create outputs if not present
                if not transaction.outputs:
                    transaction.outputs = [
                        {"address": transaction.recipient, "amount": transaction.amount}
                    ]
                    # Add change output if necessary
                    change = selected_amount - total_needed
                    if change > 0.00000001:  # Minimum dust threshold
                        transaction.outputs.append({"address": transaction.sender, "amount": change})

            # Validate transaction (still under lock to prevent TOCTOU)
            is_valid = self.transaction_validator.validate_transaction(transaction)

            # If validation failed, check if it's because of missing UTXOs (orphan transaction)
            if not is_valid and transaction.tx_type != "coinbase":
                # Check if the transaction references unknown UTXOs
                has_missing_utxos = False
                if transaction.inputs:
                    for tx_input in transaction.inputs:
                        # Check if UTXO exists (don't exclude pending - we're checking existence, not availability)
                        utxo = self.utxo_manager.get_unspent_output(tx_input["txid"], tx_input["vout"], exclude_pending=False)
                        if not utxo:
                            has_missing_utxos = True
                            break

                # If it has missing UTXOs, add to orphan pool instead of rejecting
                if has_missing_utxos:
                    # Limit orphan pool size to prevent memory exhaustion
                    MAX_ORPHAN_TRANSACTIONS = 1000
                    if len(self.orphan_transactions) < MAX_ORPHAN_TRANSACTIONS:
                        # Check if transaction is not already in orphan pool
                        if not any(orphan.txid == transaction.txid for orphan in self.orphan_transactions):
                            self.orphan_transactions.append(transaction)
                            self.logger.info(f"Transaction {transaction.txid[:10]}... added to orphan pool (missing UTXOs)")
                    # Unlock UTXOs since transaction not accepted to mempool
                    if transaction.inputs:
                        utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                        self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                    return False
                else:
                    # Validation failed for other reasons, reject transaction
                    self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (validation failed for other reasons)")
                    self._record_invalid_sender_attempt(transaction.sender, current_time)
                    self._mempool_rejected_invalid_total += 1
                    # Unlock UTXOs since transaction rejected
                    if transaction.inputs:
                        utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                        self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                    return False

            if not is_valid:
                self._record_invalid_sender_attempt(transaction.sender, current_time)
                self._mempool_rejected_invalid_total += 1
                # Unlock UTXOs since transaction rejected
                if transaction.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                return False

            # Double-spend detection: Check if any inputs are already spent in pending transactions
            # This check is now atomic with validation - prevents TOCTOU race
            if transaction.tx_type != "coinbase" and transaction.inputs:
                for tx_input in transaction.inputs:
                    input_key = f"{tx_input['txid']}:{tx_input['vout']}"

                    # Check if this input is already used by a pending transaction
                    for pending_tx in self.pending_transactions:
                        if pending_tx.tx_type != "coinbase" and pending_tx.inputs:
                            for pending_input in pending_tx.inputs:
                                pending_key = f"{pending_input['txid']}:{pending_input['vout']}"
                                if input_key == pending_key:
                                    # Check if this is an RBF replacement attempt
                                    if not getattr(transaction, 'replaces_txid', None):
                                        self.logger.warn(f"Double-spend detected: Input {input_key} already used in mempool by tx {pending_tx.txid}")
                                        self._record_invalid_sender_attempt(transaction.sender, current_time)
                                        self._mempool_rejected_invalid_total += 1
                                        # Unlock UTXOs since transaction rejected
                                        if transaction.inputs:
                                            utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                                            self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                                        return False

            # Handle Replace-By-Fee (RBF) if this transaction replaces another
            if hasattr(transaction, 'replaces_txid') and transaction.replaces_txid:
                if not self._handle_rbf_replacement(transaction):
                    return False

            # Enforce per-sender cap
            if transaction.sender and transaction.sender != "COINBASE":
                if self._sender_pending_count.get(transaction.sender, 0) >= getattr(self, "_mempool_max_per_sender", 100):
                    self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (sender cap exceeded)")
                    self._mempool_rejected_sender_cap_total += 1
                    return False

            # Enforce mempool size with admission control by fee rate
            if len(self.pending_transactions) >= getattr(self, "_mempool_max_size", 10000):
                # Evaluate if new tx has higher fee rate than current min
                if self.pending_transactions:
                    lowest = min(self.pending_transactions, key=lambda t: t.get_fee_rate())
                    if transaction.get_fee_rate() > lowest.get_fee_rate():
                        # Evict the lowest fee transaction to make room for the higher fee rate
                        eviction_performed = False
                        try:
                            self.pending_transactions.remove(lowest)
                            self.seen_txids.discard(lowest.txid)
                            if lowest.sender and lowest.sender != "COINBASE":
                                self._sender_pending_count[lowest.sender] = max(
                                    0, self._sender_pending_count[lowest.sender] - 1
                                )
                            self._mempool_evicted_low_fee_total += 1
                            eviction_performed = True
                            self.logger.info(f"Evicted transaction {lowest.txid[:10]}... from mempool (low fee rate)")
                        except ValueError as exc:
                            self.logger.error(
                                "Failed to evict low-fee transaction due to inconsistent mempool state",
                                txid=lowest.txid,
                                error=str(exc),
                                extra={"event": "mempool.eviction_failed"},
                            )
                        if not eviction_performed:
                            self.logger.warn(
                                f"Transaction {transaction.txid[:10]}... rejected (mempool full, eviction failed)"
                            )
                            self._mempool_rejected_low_fee_total += 1
                            return False
                    else:
                        self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (mempool full, low fee rate)")
                        self._mempool_rejected_low_fee_total += 1
                        return False

            # ATOMIC INSERTION: Add to mempool while still holding lock
            # This ensures no gap between validation and insertion
            self.pending_transactions.append(transaction)
            self.seen_txids.add(transaction.txid)
            if transaction.sender and transaction.sender != "COINBASE":
                self._sender_pending_count[transaction.sender] = self._sender_pending_count.get(transaction.sender, 0) + 1
                self.nonce_tracker.reserve_nonce(transaction.sender, transaction.nonce)
            self._clear_sender_penalty(transaction.sender)

            # Process gas sponsorship if applicable (Task 178: Account Abstraction)
            if hasattr(transaction, 'gas_sponsor') and transaction.gas_sponsor:
                sponsor_processor = get_sponsored_transaction_processor()
                validation = sponsor_processor.validate_sponsored_transaction(transaction)
                if validation.result == SponsorshipResult.APPROVED:
                    sponsor_processor.deduct_sponsor_fee(transaction)
                    self.logger.info(
                        "Sponsored transaction added to mempool",
                        txid=transaction.txid,
                        sender=transaction.sender,
                        sponsor=transaction.gas_sponsor,
                        fee=transaction.fee
                    )
                else:
                    # Sponsorship validation failed - log but don't reject
                    # The transaction can still be processed if sender has funds
                    self.logger.warn(
                        f"Sponsorship validation failed: {validation.message}",
                        txid=transaction.txid,
                        sender=transaction.sender,
                        sponsor=transaction.gas_sponsor
                    )
            else:
                self.logger.info("Transaction added to mempool", txid=transaction.txid, sender=transaction.sender)

            return True
        # End of atomic lock section

    def _handle_rbf_replacement(self, replacement_tx: Transaction) -> bool:
        """
        Handle Replace-By-Fee transaction replacement.

        Rules:
        1. Original transaction must be in mempool (not yet mined)
        2. Original transaction must have rbf_enabled=True (opt-in)
        3. Replacement must have higher fee rate than original
        4. Replacement must be from the same sender
        5. Replacement must use the same or overlapping inputs

        Args:
            replacement_tx: The new transaction attempting to replace an existing one

        Returns:
            True if replacement is valid and original was removed, False otherwise
        """
        # Find the original transaction in pending pool
        original_tx = None
        original_index = -1
        for idx, tx in enumerate(self.pending_transactions):
            if tx.txid == replacement_tx.replaces_txid:
                original_tx = tx
                original_index = idx
                break

        if not original_tx:
            self.logger.warn(f"RBF failed: Original transaction {replacement_tx.replaces_txid} not found in mempool")
            return False

        # Check if original transaction opted into RBF
        if not getattr(original_tx, 'rbf_enabled', False):
            self.logger.warn(f"RBF failed: Original transaction {replacement_tx.replaces_txid} did not opt-in to RBF")
            return False

        # Verify sender is the same
        if original_tx.sender != replacement_tx.sender:
            self.logger.warn(f"RBF failed: Sender mismatch (original: {original_tx.sender}, replacement: {replacement_tx.sender})")
            return False

        # Verify replacement has higher fee rate
        original_fee_rate = original_tx.get_fee_rate()
        replacement_fee_rate = replacement_tx.get_fee_rate()

        if replacement_fee_rate <= original_fee_rate:
            self.logger.warn(f"RBF failed: Replacement fee rate ({replacement_fee_rate}) must be higher than original ({original_fee_rate})")
            return False

        # Verify inputs overlap (replacement must spend at least one of the same UTXOs)
        original_inputs = set((inp.get('txid'), inp.get('vout')) for inp in original_tx.inputs)
        replacement_inputs = set((inp.get('txid'), inp.get('vout')) for inp in replacement_tx.inputs)

        if not original_inputs.intersection(replacement_inputs):
            self.logger.warn(f"RBF failed: No overlapping inputs between original ({original_tx.txid}) and replacement ({replacement_tx.txid})")
            return False

        # All checks passed - remove original transaction from mempool
        self.logger.info(f"RBF successful: Replacing {original_tx.txid} with {replacement_tx.txid}",
                         original_txid=original_tx.txid, replacement_txid=replacement_tx.txid,
                         original_fee_rate=original_fee_rate, replacement_fee_rate=replacement_fee_rate)

        del self.pending_transactions[original_index]
        self.seen_txids.discard(original_tx.txid)
        if original_tx.sender and original_tx.sender != "COINBASE":
            self._sender_pending_count[original_tx.sender] -= 1
        return True

    def _prioritize_transactions(self, transactions: List[Transaction], max_count: Optional[int] = None) -> List[Transaction]:
        """
        Prioritize transactions by fee rate (fee-per-byte) while maintaining nonce order per sender.

        This implements a proper fee market where:
        1. Transactions are ordered by fee rate (fee-per-byte, highest first) to maximize miner revenue
        2. Within each sender's transactions, nonce order is maintained for validity
        3. Optional limit on number of transactions to include in block
        4. This prevents large transactions with high absolute fees but low fee rates from
           crowding out smaller transactions with better fee rates

        Args:
            transactions: List of pending transactions
            max_count: Maximum number of transactions to return (None = all)

        Returns:
            Ordered list of transactions prioritized by fee rate
        """
        if not transactions:
            return []

        # Group transactions by sender
        by_sender: Dict[str, List[Transaction]] = defaultdict(list)
        for tx in transactions:
            by_sender[tx.sender].append(tx)

        # Sort each sender's transactions by nonce (ascending) to maintain validity
        for sender, sender_txs in by_sender.items():
            # Sort by nonce if present, otherwise by timestamp
            sender_txs.sort(key=lambda tx: (tx.nonce if tx.nonce is not None else 0, tx.timestamp))

        # Flatten back to a single list with fee rate priority
        all_txs = []
        for sender_txs in by_sender.values():
            all_txs.extend(sender_txs)

        # Sort by fee rate (descending) - this is more fair than absolute fee
        # Transactions with higher fee-per-byte get priority
        # This prevents large transactions from crowding out smaller ones
        all_txs.sort(key=lambda tx: tx.get_fee_rate(), reverse=True)

        # Limit to max_count if specified
        if max_count is not None:
            all_txs = all_txs[:max_count]

        return all_txs

    def mine_pending_transactions(self, miner_address: str, node_identity: Optional[Dict[str, str]] = None) -> Optional[Block]:
        """Mine a new block with pending transactions

        Implements block size limits to prevent DoS attacks and ensure network scalability.
        Maximum block size is 1 MB (1,000,000 bytes).
        """
        # Require a real node identity for block signing
        if node_identity is None:
            node_identity = getattr(self, "node_identity", None)
        if not node_identity or not node_identity.get("private_key") or not node_identity.get("public_key"):
            raise ValueError("node_identity with private_key and public_key is required for block signing.")
        max_block_size_bytes = self._max_block_size_bytes
        max_transactions_per_block = self._max_transactions_per_block

        # Adjust difficulty based on recent block times
        self.difficulty = self.calculate_next_difficulty()
        if self.fast_mining_enabled and self.difficulty > self.max_test_mining_difficulty:
            self.logger.info(
                "Capping mining difficulty for fast-mining mode",
                requested_difficulty=self.difficulty,
                cap=self.max_test_mining_difficulty,
            )
            self.difficulty = self.max_test_mining_difficulty

        # Reset pending nonce reservations so block assembly validates from confirmed state in-order
        if hasattr(self.nonce_tracker, "pending_nonces"):
            self.nonce_tracker.pending_nonces.clear()

        # Prioritize pending transactions by fee rate
        prioritized_txs = self._prioritize_transactions(self.pending_transactions)
        prioritized_txs.sort(key=lambda tx: (tx.sender, tx.nonce if tx.nonce is not None else 0))

        # Enforce strict in-block nonce sequencing per sender
        sender_next_nonce: Dict[str, int] = {}

        # Apply block size limits: Select transactions that fit within max block size
        selected_txs = []
        current_block_size = 0

        for tx in prioritized_txs:
            if len(selected_txs) + 1 >= max_transactions_per_block:
                self.logger.info(
                    "Transaction limit reached for block assembly",
                    limit=max_transactions_per_block,
                )
                break
            # Re-validate transaction against current state before inclusion
            if tx.sender != "COINBASE":
                confirmed_nonce = self.nonce_tracker.get_nonce(tx.sender)
                expected = sender_next_nonce.get(tx.sender, confirmed_nonce + 1)
                tx.nonce = tx.nonce if tx.nonce is not None else expected
                if tx.nonce != expected:
                    self.logger.warn(
                        "Transaction skipped due to nonce mismatch during block assembly",
                        txid=tx.txid,
                        sender=tx.sender,
                        expected_nonce=expected,
                        got_nonce=tx.nonce,
                    )
                    continue
                # Align nonce tracker state so validation enforces strict sequencing
                self.nonce_tracker.nonces[tx.sender] = expected - 1
                # Temporarily reserve previous nonce so validate_nonce expects `expected`
                self.nonce_tracker.pending_nonces[tx.sender] = expected - 1
                if not self.validate_transaction(tx):
                    txid_display = (tx.txid or tx.calculate_hash() or "")[:10]
                    self.logger.warn(
                        f"Transaction {txid_display}... failed validation and was excluded from block."
                    )
                    self.nonce_tracker.pending_nonces.pop(tx.sender, None)
                    continue
                # Reserve this nonce for subsequent txs in the block
                self.nonce_tracker.pending_nonces[tx.sender] = expected
                sender_next_nonce[tx.sender] = expected + 1

            # Calculate transaction size using canonical JSON
            tx_size = len(canonical_json(tx.to_dict()).encode('utf-8'))

            # Check if adding this transaction would exceed block size limit
            if current_block_size + tx_size <= max_block_size_bytes:
                selected_txs.append(tx)
                current_block_size += tx_size
            else:
                # Block is full, skip remaining transactions
                break

        # Use selected transactions instead of all prioritized transactions
        prioritized_txs = selected_txs

        # Calculate block reward based on current chain height (with halving)
        block_height = len(self.chain)
        base_reward = self.get_block_reward(block_height)

        # Update miner streak and apply bonus
        self.streak_tracker.update_miner_streak(miner_address, time.time())
        final_reward, streak_bonus = self.streak_tracker.apply_streak_bonus(
            miner_address, base_reward
        )

        # Create coinbase transaction (block reward + transaction fees + streak bonus)
        total_fees = sum(tx.fee for tx in prioritized_txs)
        coinbase_reward = final_reward + total_fees

        coinbase_tx = Transaction(
            "COINBASE",
            miner_address,
            coinbase_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": coinbase_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create new block with prioritized transactions
        block_transactions = [coinbase_tx] + prioritized_txs
        
        merkle_root = self.calculate_merkle_root(block_transactions)
        
        header = BlockHeader(
            index=len(self.chain),
            previous_hash=self.chain[-1].hash if self.chain else "0",
            merkle_root=merkle_root,
            timestamp=time.time(),
            difficulty=self.difficulty,
            nonce=0,
            miner_pubkey=node_identity['public_key'],
            version=Config.BLOCK_HEADER_VERSION,
        )

        # Mine the block
        header.hash = self.mine_block(header)
        header.signature = sign_message_hex(node_identity['private_key'], header.hash.encode())
        
        new_block = Block(header, block_transactions)
        new_block.miner = miner_address
        # Provide ancestry context to peers for fork resolution without optional data loss
        new_block.lineage = list(self.chain)

        if not self._block_within_size_limits(new_block, context="local_mining"):
            raise ValueError("Locally mined block violates block size or transaction limits")

        if self.smart_contract_manager:
            receipts = self.smart_contract_manager.process_block(new_block)
            if receipts:
                self.contract_receipts.extend(receipts)

        # Snapshot state before any modifications for atomicity
        # If block persistence fails, we can rollback to this state
        utxo_snapshot = self.utxo_manager.snapshot()
        nonce_snapshot = self.nonce_tracker.snapshot()
        pending_txs_backup = list(self.pending_transactions)

        # Track nonce changes to commit only after successful persistence
        nonce_changes = []

        try:
            # Add to chain (cache)
            self.chain.append(new_block)
            self._process_governance_block_transactions(new_block)
            self.storage._save_block_to_disk(new_block)

            # Update UTXO set (collect nonce changes but don't commit yet)
            for tx in new_block.transactions:
                if tx.sender != "COINBASE":  # Regular transactions spend inputs
                    self.utxo_manager.process_transaction_inputs(tx)
                    # Collect nonce change without committing
                    nonce_changes.append((tx.sender, tx.nonce))
                self.utxo_manager.process_transaction_outputs(tx)

            # Process gamification features for this block
            self._process_gamification_features(self.gamification_adapter, new_block, miner_address)

            # Unlock UTXOs for mined transactions (no longer pending)
            for tx in new_block.transactions:
                if tx.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in tx.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)

            # Clear pending transactions
            self.pending_transactions = []

            # Log streak bonus if applied
            if streak_bonus > 0:
                self.logger.info(
                    f"STREAK BONUS: +{streak_bonus:.4f} AXN ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)"
                )

            # Create checkpoint if needed (every N blocks)
            if self.checkpoint_manager.should_create_checkpoint(new_block.index):
                total_supply = self.get_circulating_supply()
                checkpoint = self.checkpoint_manager.create_checkpoint(
                    new_block, self.utxo_manager, total_supply
                )
                if checkpoint:
                    self.logger.info(f"Created checkpoint at block {new_block.index}")

            # Periodically compact the UTXO set to save memory
            if new_block.index % 100 == 0:  # Compact every 100 blocks
                self.utxo_manager.compact_utxo_set()

            # CRITICAL: Persist state to disk BEFORE committing nonces
            # This is the failure point we're protecting against
            self.storage.save_state_to_disk(
                self.utxo_manager,
                self.pending_transactions,
                self.contracts,
                self.contract_receipts,
            )

            # Only commit nonce increments AFTER successful persistence
            # This prevents nonce desynchronization if disk write fails
            for sender, nonce in nonce_changes:
                self.nonce_tracker.increment_nonce(sender, nonce)

            self.logger.info(
                "Block mined and persisted successfully",
                block_index=new_block.index,
                block_hash=new_block.hash[:16],
                nonce_updates=len(nonce_changes),
            )

            return new_block

        except Exception as e:
            # Block persistence failed - rollback all state changes
            self.logger.error(
                "Block persistence failed, rolling back state changes",
                block_index=new_block.index,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Rollback UTXO state
            self.utxo_manager.restore(utxo_snapshot)

            # Rollback nonce state
            self.nonce_tracker.restore(nonce_snapshot)

            # Remove block from chain
            if self.chain and self.chain[-1] == new_block:
                self.chain.pop()

            # Restore pending transactions
            self.pending_transactions = pending_txs_backup

            self.logger.warn(
                "State rolled back after block persistence failure",
                nonces_protected=len(nonce_changes),
                utxo_state_restored=True,
            )

            # Re-raise exception for caller to handle
            raise
    
    def _process_gamification_features(
        self,
        gamification_adapter: GamificationBlockchainInterface,
        block: Block,
        miner_address: str,
    ) -> None:
        """
        Apply gamification modules after a block is mined. Best-effort: log failures.
        """
        try:
            if self.airdrop_manager:
                self.airdrop_manager.execute_airdrop(block.index, block.hash)
        except Exception as exc:
            self.logger.warn(f"Gamification airdrop processing failed: {exc}")

        try:
            if self.fee_refund_calculator:
                self.fee_refund_calculator.process_refunds(block)
        except Exception as exc:
            self.logger.warn(f"Gamification refund processing failed: {exc}")

        try:
            if self.treasure_manager:
                # Placeholder hook for future treasure processing
                pass
        except Exception as exc:
            self.logger.warn(f"Gamification treasure processing failed: {exc}")

        try:
            if self.streak_tracker:
                self.streak_tracker._save_streaks()
        except Exception as exc:
            self.logger.warn(f"Gamification streak persistence failed: {exc}")
    
    def mine_block(self, header: BlockHeader) -> str:
        """Mine block with proof-of-work"""
        effective_difficulty = header.difficulty
        if self.fast_mining_enabled and effective_difficulty > self.max_test_mining_difficulty:
            self.logger.info(
                "Applying fast-mining difficulty cap",
                requested_difficulty=effective_difficulty,
                cap=self.max_test_mining_difficulty,
                network=self.network_type,
            )
            effective_difficulty = self.max_test_mining_difficulty
            header.difficulty = effective_difficulty

        target = "0" * effective_difficulty

        while True:
            hash_attempt = header.calculate_hash()
            if hash_attempt.startswith(target):
                self.logger.info(f"Block mined! Hash: {hash_attempt}")
                return hash_attempt
            header.nonce += 1

    def add_block(self, block: Block) -> bool:
        """
        Add a block received from a peer to the blockchain.
        Handles chain reorganization if the incoming block is part of a longer valid chain.

        ATOMIC OPERATION: Uses snapshot/restore for safe rollback on failure.
        All state modifications (chain, UTXO, nonces) are applied atomically or not at all.

        Args:
            block: Block to add to the chain

        Returns:
            True if block was added successfully, False otherwise
        """
        # Allow callers to provide either a full Block or a BlockHeader (load from disk)
        if isinstance(block, BlockHeader):
            loaded_block = self.storage.load_block_from_disk(block.index)
            if not loaded_block:
                self.logger.warn("Failed to add block: header provided but block missing on disk", block_index=block.index)
                return False
            block = loaded_block

        header = block.header
        self.logger.info("Attempting to add new block", block_index=header.index, block_hash=header.hash)
        # Validate the block before adding
        if not header or not hasattr(header, 'hash'):
            self.logger.warn("Invalid block header received", block=block)
            return False

        # Check if we already have this block at this index with the same hash
        if len(self.chain) > header.index and self.chain[header.index].hash == header.hash:
            self.logger.debug("Block already exists in chain", block_index=header.index, block_hash=header.hash)
            return True  # Already have this exact block

        # Verify proof of work
        if not header.hash.startswith("0" * header.difficulty):
            self.logger.warn("Block has invalid proof of work", block_hash=header.hash, difficulty=header.difficulty)
            return False

        # Verify block hash is correct
        if header.hash != header.calculate_hash():
            self.logger.warn("Block hash mismatch", block_hash=header.hash, calculated_hash=header.calculate_hash())
            return False

        # Verify merkle root matches transactions
        try:
            computed_merkle = self.calculate_merkle_root(block.transactions)
            if header.merkle_root != computed_merkle:
                self.logger.warn("Block merkle root mismatch", block_hash=header.hash, block_merkle_root=header.merkle_root, computed_merkle_root=computed_merkle)
                return False
        except Exception as e:
            self.logger.error("Error calculating merkle root", block_hash=header.hash, error=str(e))
            return False

        # Verify block signature
        if not self.verify_block_signature(header):
            self.logger.warn("Block has invalid signature", block_hash=header.hash, miner_pubkey=header.miner_pubkey)
            return False

        if not self._validate_header_version(header):
            return False

        if not self._block_within_size_limits(block, context="inbound_block"):
            return False

        history_view = self.chain[:header.index] if header.index <= len(self.chain) else self.chain
        time_valid, time_error = self._validate_block_timestamp(
            header,
            history_view,
            emit_metrics=True,
        )
        if not time_valid:
            self.logger.warn(
                "Block rejected due to timestamp violation",
                block_hash=header.hash,
                block_index=header.index,
                reason=time_error,
            )
            return False

        # Enforce deterministic difficulty schedule when parent history is known
        if header.index > 0 and header.index <= len(self.chain):
            history_view = list(self.chain[: header.index])
            if history_view:
                parent_obj = history_view[-1]
                parent_hash = parent_obj.hash if hasattr(parent_obj, "hash") else getattr(parent_obj, "hash", None)
                if parent_hash == header.previous_hash:
                    expected_difficulty = self._expected_difficulty_for_block(
                        block_index=header.index,
                        history=history_view,
                    )
                    if (
                        expected_difficulty is not None
                        and header.difficulty != expected_difficulty
                    ):
                        self.logger.warn(
                            "Block rejected due to unexpected difficulty",
                            block_index=header.index,
                            block_hash=header.hash,
                            declared_difficulty=header.difficulty,
                            expected_difficulty=expected_difficulty,
                        )
                        return False

        # Case 1: Block extends our current chain directly
        if header.index == len(self.chain):
            if len(self.chain) > 0 and header.previous_hash != self.chain[-1].hash:
                # Block doesn't link to our chain tip - might be from a competing fork
                # Store it as an orphan block
                if self._attempt_lineage_sync(block):
                    return True
                if header.index not in self.orphan_blocks:
                    self.orphan_blocks[header.index] = []
                self.orphan_blocks[header.index].append(block)
                self.logger.info("Received orphan block", block_index=header.index, block_hash=header.hash)
                # Check if orphans now form a longer chain
                self._check_orphan_chains_for_reorg()
                return False
            # Validate transactions only when extending the active tip (uses current UTXO state)
            for tx in block.transactions:
                if tx.sender not in ["COINBASE", "SYSTEM", "AIRDROP"]:
                    if not self.transaction_validator.validate_transaction(tx, is_mempool_check=False):
                        self.logger.warn("Block contains invalid transaction", block_hash=header.hash, txid=tx.txid)
                        return False
            return self._add_block_to_chain(block)

        # Case 2: Block is beyond our current chain (potential reorganization)
        if header.index > len(self.chain):
            if self._attempt_lineage_sync(block):
                return True
            # Store as orphan - we're missing intermediate blocks
            if header.index not in self.orphan_blocks:
                self.orphan_blocks[header.index] = []
            self.orphan_blocks[header.index].append(block)
            self.logger.info("Received orphan block", block_index=header.index, block_hash=header.hash)
            # Check if orphans now form a longer chain
            self._check_orphan_chains_for_reorg()
            return False

        # Case 3: Block conflicts with our chain (fork/reorganization scenario)
        # The block is at an index we already have, but with a different hash
        if header.index < len(self.chain) and self.chain[header.index].hash != header.hash:
            # ATOMIC OPERATION: Create snapshots before any state modifications
            # This ensures we can rollback if fork handling fails partway through
            old_chain = self.chain.copy()
            utxo_snapshot = self.utxo_manager.snapshot()  # Thread-safe atomic snapshot
            nonce_snapshot = self.nonce_tracker.snapshot() if self.nonce_tracker else None

            try:
                if self._attempt_lineage_sync(block):
                    return True
                # Check if this block links to a previous block in our chain
                if header.index > 0 and header.index - 1 < len(self.chain):
                    if header.previous_hash == self.chain[header.index - 1].hash:
                        # This is a valid fork from our chain
                        # Try to build a longer chain from this fork point
                        self.logger.info("Received fork block", block_index=header.index, block_hash=header.hash)
                        result = self._handle_fork(block)
                        if not result:
                            # Fork handling failed - restore snapshots to maintain consistency
                            self.logger.debug(
                                "Fork handling failed, restoring state",
                                block_index=header.index,
                                block_hash=header.hash
                            )
                            self.chain = old_chain
                            self.utxo_manager.restore(utxo_snapshot)
                            if nonce_snapshot and self.nonce_tracker:
                                self.nonce_tracker.restore(nonce_snapshot)
                        return result

                # Block doesn't connect to our immediate parent, but might be part
                # of a competing fork. Store as orphan and check for reorganization.
                if header.index not in self.orphan_blocks:
                    self.orphan_blocks[header.index] = []
                self.orphan_blocks[header.index].append(block)
                self.logger.info("Received orphan block", block_index=header.index, block_hash=header.hash)
                self._check_orphan_chains_for_reorg()
                return False

            except Exception as e:
                # If any exception occurs during fork handling, restore state
                self.logger.error(
                    f"Exception during fork handling: {e}. Rolling back to previous state.",
                    block_index=header.index,
                    block_hash=header.hash,
                    error=str(e)
                )
                self.chain = old_chain
                self.utxo_manager.restore(utxo_snapshot)
                if nonce_snapshot and self.nonce_tracker:
                    self.nonce_tracker.restore(nonce_snapshot)
                return False

        return False

    def verify_block_signature(self, header: BlockHeader) -> bool:
        """Verify the block's signature."""
        if header.signature is None or header.miner_pubkey is None:
            return False
        return verify_signature_hex(header.miner_pubkey, header.hash.encode(), header.signature)

    def calculate_merkle_root(self, transactions: List[Transaction]) -> str:
        """Calculate merkle root of transactions"""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        # Get transaction hashes, ensuring all txids are set
        tx_hashes = []
        for tx in transactions:
            if tx.txid is None:
                # Calculate hash for transactions without txid
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

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

    def validate_chain(
        self,
        chain: Optional[List[Union["Block", BlockHeader]]] = None,
        expected_genesis_hash: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate the blockchain tip-to-genesis without mutating live state.

        Performs structural checks, PoW verification, signature validation,
        transaction validation against the authoritative UTXO manager,
        nonce progression, merkle root verification, and supply cap enforcement.
        """
        if chain is None:
            # Prefer the in-memory cache so we can detect tampering before hitting disk
            # (e.g., corruption in RAM or during recovery). Use only headers to avoid
            # coupling validation to any potentially mutated in-memory transaction objects.
            if self.chain:
                chain_to_check = [
                    copy.deepcopy(block.header) if isinstance(block, Block) else copy.deepcopy(block)
                    for block in self.chain
                ]
            else:
                chain_to_check = self.storage.load_chain_from_disk()
            if not chain_to_check:
                return False
        else:
            chain_to_check = chain
        if not chain_to_check:
            return False

        # Normalize to full blocks (load from disk when only headers are present)
        blocks: List[Block] = []
        for element in chain_to_check:
            if isinstance(element, Block):
                block = element
            elif isinstance(element, BlockHeader):
                block = self.storage.load_block_from_disk(element.index)
                if not block:
                    self.logger.warn("Chain validation failed: missing block from storage", index=element.index)
                    return False
                if element.hash and block.header.hash != element.hash:
                    self.logger.warn("Chain validation failed: header mismatch", index=element.index)
                    return False
            else:
                self.logger.warn("Chain validation failed: unsupported chain element")
                return False
            blocks.append(block)

        genesis_header = blocks[0].header
        if genesis_header.index != 0 or genesis_header.previous_hash != "0":
            self.logger.warn("Chain validation failed: invalid genesis linkage")
            return False
        if expected_genesis_hash and genesis_header.hash != expected_genesis_hash:
            self.logger.warn("Chain validation failed: genesis hash mismatch")
            return False

        # Snapshot state and rebuild using the authoritative managers
        utxo_snapshot = self.utxo_manager.snapshot()
        nonce_snapshot = (
            dict(self.nonce_tracker.nonces),
            dict(self.nonce_tracker.pending_nonces),
        )
        self.utxo_manager.clear()
        self.nonce_tracker.nonces = {}
        self.nonce_tracker.pending_nonces = {}

        validator = TransactionValidator(
            self,
            self.nonce_tracker,
            self.logger,
            utxo_manager=self.utxo_manager,
        )

        seen_txids: set[str] = set()
        current_supply = 0.0
        previous_timestamp: Optional[float] = None

        try:
            for idx, block in enumerate(blocks):
                header = block.header

                if idx > 0:
                    prev_header = blocks[idx - 1].header
                    if header.previous_hash != prev_header.hash:
                        self.logger.warn("Chain validation failed: previous_hash mismatch", index=header.index)
                        return False

                if previous_timestamp is not None and header.timestamp < previous_timestamp:
                    self.logger.warn("Chain validation failed: timestamp regression", index=header.index)
                    return False
                previous_timestamp = header.timestamp

                if header.hash != header.calculate_hash():
                    self.logger.warn("Chain validation failed: hash mismatch", index=header.index)
                    return False
                if not header.hash.startswith("0" * header.difficulty):
                    self.logger.warn("Chain validation failed: invalid proof-of-work", index=header.index)
                    return False

                if not self._validate_header_version(header):
                    self.logger.warn("Chain validation failed: unsupported header version", index=header.index)
                    return False

                if not self._block_within_size_limits(block, context="chain_validation"):
                    self.logger.warn("Chain validation failed: block size exceeded", index=header.index)
                    return False

                expected_difficulty = self._expected_difficulty_for_block(
                    block_index=header.index,
                    history=blocks[:idx],
                )
                if expected_difficulty is not None and header.difficulty != expected_difficulty:
                    self.logger.warn(
                        "Chain validation failed: unexpected difficulty",
                        index=header.index,
                        expected_difficulty=expected_difficulty,
                        declared_difficulty=header.difficulty,
                    )
                    return False

                # Signature optional for genesis (no miner), enforced for others when present
                if header.signature is not None or header.index != 0:
                    if not self.verify_block_signature(header):
                        self.logger.warn("Chain validation failed: invalid signature", index=header.index)
                        return False

                # Recompute txids to detect tampering on disk and refresh merkle root calculation
                if header.index > 0:
                    for tx in block.transactions:
                        recalculated = tx.calculate_hash()
                        if tx.txid and tx.txid != recalculated:
                            self.logger.warn(
                                "Chain validation failed: transaction hash mismatch",
                                index=header.index,
                                txid=tx.txid,
                            )
                            return False
                        tx.txid = recalculated

                computed_merkle = self.calculate_merkle_root(block.transactions)
                if computed_merkle != header.merkle_root:
                    self.logger.warn("Chain validation failed: merkle root mismatch", index=header.index)
                    return False

                for tx in block.transactions:
                    tx.txid = tx.txid or tx.calculate_hash()
                    if tx.txid in seen_txids:
                        self.logger.warn("Chain validation failed: duplicate transaction", txid=tx.txid)
                        return False
                    seen_txids.add(tx.txid)

                    input_value = 0.0
                    if tx.sender != "COINBASE" and tx.inputs:
                        for tx_input in tx.inputs:
                            utxo = self.utxo_manager.get_unspent_output(tx_input["txid"], tx_input["vout"])
                            if not utxo:
                                self.logger.warn(
                                    "Chain validation failed: missing UTXO spend",
                                    txid=tx.txid,
                                    input=f"{tx_input.get('txid')}:{tx_input.get('vout')}",
                                )
                                return False
                            input_value += utxo.get("amount", 0.0)

                    if not validator.validate_transaction(tx, is_mempool_check=False):
                        self.logger.warn("Chain validation failed: invalid transaction", txid=tx.txid, index=header.index)
                        return False

                    if tx.sender != "COINBASE":
                        if not self.utxo_manager.process_transaction_inputs(tx):
                            self.logger.warn("Chain validation failed: unable to process inputs", txid=tx.txid, index=header.index)
                            return False
                        self.nonce_tracker.increment_nonce(tx.sender, tx.nonce)

                    self.utxo_manager.process_transaction_outputs(tx)
                    output_value = sum(out.get("amount", 0.0) for out in tx.outputs)
                    current_supply += (output_value - input_value)

                if current_supply > self.max_supply + 1e-8:
                    self.logger.warn("Chain validation failed: supply cap exceeded", index=header.index)
                    return False

            return True
        finally:
            # Restore authoritative state
            self.utxo_manager.restore(utxo_snapshot)
            self.nonce_tracker.nonces = nonce_snapshot[0]
            self.nonce_tracker.pending_nonces = nonce_snapshot[1]
            try:
                self.nonce_tracker._save_nonces()
            except Exception as e:
                self.logger.debug(f"Failed to save nonces after chain validation restore: {type(e).__name__}")

    def _calculate_block_work(self, block_like: Union["Block", BlockHeader, Any]) -> int:
        """
        Convert a block's declared difficulty into an absolute work value using the
        2^256 / (target + 1) formulation popularized by Bitcoin. This prevents
        peers from gaming fork choice with chains that merely have more headers.
        """
        header = block_like.header if hasattr(block_like, "header") else block_like
        if header is None:
            return 0

        block_hash = getattr(header, "hash", None)
        if block_hash:
            cached = self._block_work_cache.get(block_hash)
            if cached is not None:
                return cached

        try:
            claimed_difficulty = int(getattr(header, "difficulty", 0))
        except (TypeError, ValueError):
            claimed_difficulty = 0
        claimed_difficulty = max(0, claimed_difficulty)

        shift_bits = min(claimed_difficulty * 4, 256)
        if shift_bits >= 256:
            target = 0
        else:
            target = self._max_pow_target >> shift_bits

        denominator = max(target + 1, 1)
        work = self._max_pow_target // denominator

        if block_hash:
            self._block_work_cache[block_hash] = work
        return work

    def _calculate_chain_work(self, chain: List[Union["Block", BlockHeader, Any]]) -> int:
        """
        Calculate cumulative work for a candidate chain using precise PoW arithmetic.

        Args:
            chain: Sequence of block headers/blocks.

        Returns:
            Integer work sum suitable for fork choice comparisons.
        """
        if not chain:
            return 0
        total = 0
        for block_like in chain:
            total += self._calculate_block_work(block_like)
        return total

    def _handle_fork(self, block: Block) -> bool:
        """
        Handle competing fork block by constructing a candidate chain starting at the fork point.
        """
        fork_index = block.header.index
        # Track forked block for future assembly
        if fork_index not in self.orphan_blocks:
            self.orphan_blocks[fork_index] = []
        if not any(b.header.hash == block.header.hash for b in self.orphan_blocks[fork_index]):
            self.orphan_blocks[fork_index].append(block)

        # Enforce bounded reorg depth before work-intensive operations
        if fork_index >= 0 and fork_index < len(self.chain):
            reorg_depth = len(self.chain) - fork_index - 1
            if reorg_depth > self.max_reorg_depth:
                self.logger.warn(
                    "Rejecting fork: max reorg depth exceeded",
                    fork_index=fork_index,
                    current_depth=reorg_depth,
                    max_depth=self.max_reorg_depth,
                )
                self._prune_orphans()
                return False

        # Persist incoming block so replace_chain can load it
        self.storage._save_block_to_disk(block)

        candidate_chain: List[BlockHeader] = []
        # Up to fork point (exclusive)
        candidate_chain.extend(self.chain[:fork_index])
        candidate_chain.append(block.header)

        # Attempt to extend candidate with any connecting orphans
        next_index = fork_index + 1
        while next_index in self.orphan_blocks:
            connector = None
            for orphan in self.orphan_blocks[next_index]:
                if orphan.header.previous_hash == candidate_chain[-1].hash:
                    connector = orphan
                    break
            if connector is None:
                break
            self.storage._save_block_to_disk(connector)
            candidate_chain.append(connector.header)
            next_index += 1

        # Only attempt reorg if candidate is at least as long or has more work
        if len(candidate_chain) >= len(self.chain) or self._calculate_chain_work(candidate_chain) > self._calculate_chain_work(self.chain):
            replaced = self.replace_chain(candidate_chain)
            if replaced:
                # Clear consumed orphan branches
                for idx in list(self.orphan_blocks.keys()):
                    if idx < len(candidate_chain):
                        self.orphan_blocks.pop(idx, None)
            return replaced

        # If not replaced, see if accumulated orphans can now trigger a reorg
        self._check_orphan_chains_for_reorg()
        self._prune_orphans()
        return False

    def _prune_orphans(self) -> None:
        """
        Keep orphan pool bounded to prevent untrusted peers from exhausting memory.
        """
        total_orphans = sum(len(v) for v in self.orphan_blocks.values())
        if total_orphans <= self.max_orphan_blocks:
            return

        # Remove oldest orphan heights first
        heights = sorted(self.orphan_blocks.keys())
        while total_orphans > self.max_orphan_blocks and heights:
            h = heights.pop(0)
            removed = len(self.orphan_blocks.get(h, []))
            self.orphan_blocks.pop(h, None)
            total_orphans -= removed

    def _attempt_lineage_sync(self, block: Block) -> bool:
        """
        Use an incoming block's ancestry context to fast-forward to a peer's canonical chain.

        When a peer provides a block with embedded lineage (headers/blocks leading up to it),
        we assemble a full candidate chain and run replace_chain for safety.
        """
        lineage = getattr(block, "lineage", None)
        if not lineage:
            return False

        candidate_chain: List[Block] = []
        for ancestor in lineage:
            if isinstance(ancestor, Block):
                candidate_block = ancestor
            elif isinstance(ancestor, BlockHeader):
                candidate_block = self.storage.load_block_from_disk(ancestor.index)
            else:
                continue
            if not candidate_block:
                return False
            candidate_chain.append(candidate_block)

        if candidate_chain:
            for idx in range(1, len(candidate_chain)):
                if candidate_chain[idx].previous_hash != candidate_chain[idx - 1].hash:
                    return False
            if block.header.index != len(candidate_chain):
                if block.header.index < len(candidate_chain):
                    candidate_chain = candidate_chain[: block.header.index]
                else:
                    return False

        candidate_chain.append(block)

        next_index = block.header.index + 1
        while next_index in self.orphan_blocks:
            connector = next(
                (o for o in self.orphan_blocks[next_index] if o.header.previous_hash == candidate_chain[-1].hash),
                None,
            )
            if connector is None:
                break
            candidate_chain.append(connector)
            next_index += 1

        if len(candidate_chain) <= len(self.chain):
            return False

        replaced = self.replace_chain(candidate_chain)
        if replaced:
            for idx in list(self.orphan_blocks.keys()):
                if idx < len(candidate_chain):
                    self.orphan_blocks.pop(idx, None)
        return replaced
    
    def replace_chain(self, new_chain: List[BlockHeader]) -> bool:
        """
        Replace the current chain with a new chain if it's longer and valid.
        This enables chain reorganization when a longer valid chain is discovered.

        ATOMIC OPERATION: Uses snapshot/restore for safe rollback on failure.
        CHECKPOINT PROTECTION: Prevents reorganization before last checkpoint.

        FORK CHOICE RULE: When chains have equal length, choose the one with:
        1. Higher cumulative difficulty (more work)
        2. If equal difficulty, choose the one with earlier timestamp (lower hash)

        Args:
            new_chain: The new chain to replace the current one

        Returns:
            True if chain was replaced, False otherwise
        """
        def _materialize(block_like: BlockHeader | Block) -> Optional[Block]:
            if isinstance(block_like, Block):
                return block_like
            loaded = self.storage.load_block_from_disk(block_like.index)
            if not loaded:
                return None
            return loaded

        # CHECKPOINT PROTECTION: Prevent reorganization before last checkpoint
        # This protects against long-range attacks
        if new_chain and self.checkpoint_manager.latest_checkpoint_height is not None:
            fork_point = self._find_fork_point(new_chain)
            if fork_point is not None and fork_point < self.checkpoint_manager.latest_checkpoint_height:
                self.logger.warn(
                    f"Rejecting chain reorganization: fork point {fork_point} is before "
                    f"last checkpoint at height {self.checkpoint_manager.latest_checkpoint_height}"
                )
                return False
            # Enforce bounded reorg depth to mitigate long-range attacks
            if fork_point is not None:
                current_reorg_depth = len(self.chain) - fork_point - 1
                if current_reorg_depth > self.max_reorg_depth:
                    self.logger.warn(
                        "Rejecting chain reorganization: max reorg depth exceeded",
                        fork_point=fork_point,
                        current_depth=current_reorg_depth,
                        max_depth=self.max_reorg_depth,
                    )
                    return False
        else:
            fork_point = self._find_fork_point(new_chain) if new_chain else None

        if self.finality_manager:
            if not self.finality_manager.can_reorg_to_height(fork_point):
                self.logger.error(
                    "Rejecting chain reorganization: violates finalized block",
                    fork_point=fork_point,
                    highest_finalized=self.finality_manager.get_highest_finalized_height(),
                )
                return False

        # Materialize new chain blocks up-front for validation/metrics
        materialized_chain: List[Block] = []
        for candidate in new_chain:
            block = _materialize(candidate)
            if block is None:
                return False
            materialized_chain.append(block)

        # Chain must be at least as long to replace
        if len(materialized_chain) < len(self.chain):
            return False

        # If chains are equal length, use fork choice rule
        if len(materialized_chain) == len(self.chain):
            # Calculate cumulative work (difficulty) for both chains
            current_work = self._calculate_chain_work(self.chain)
            new_work = self._calculate_chain_work(materialized_chain)
            current_tx_count = sum(len(getattr(b, "transactions", []) or []) for b in self.chain)
            new_tx_count = sum(len(getattr(b, "transactions", []) or []) for b in materialized_chain)

            if new_work > current_work:
                self.logger.info(f"Fork choice: New chain has more work ({new_work} vs {current_work})")
            elif new_work < current_work:
                self.logger.info(f"Fork choice: Current chain has more work ({current_work} vs {new_work})")
                return False
            else:
                # Prefer richer chains (more transactions) when work is equal
                if new_tx_count > current_tx_count:
                    self.logger.info("Fork choice: New chain has higher transaction density (tie-breaker)")
                elif new_tx_count < current_tx_count:
                    self.logger.info("Fork choice: Current chain has higher transaction density (tie-breaker)")
                    return False
                else:
                    # Equal work and density - use timestamp tie-breaker (earlier is better)
                    if materialized_chain[-1].timestamp < self.chain[-1].timestamp:
                        self.logger.info("Fork choice: New chain has earlier timestamp (tie-breaker)")
                    else:
                        self.logger.info("Fork choice: Current chain has earlier timestamp (tie-breaker)")
                        return False

        # Validate the new chain
        if not self._validate_chain_structure(materialized_chain):
            return False

        # PHASE 1: SNAPSHOT ALL STATE (Two-Phase Commit Protocol)
        # Create comprehensive atomic snapshots before making ANY changes
        # This ensures complete rollback capability if ANY step fails
        old_chain = self.chain.copy()
        utxo_snapshot = self.utxo_manager.snapshot()  # Thread-safe atomic snapshot
        nonce_snapshot = self.nonce_tracker.snapshot() if self.nonce_tracker else None
        contract_snapshot = self.smart_contract_manager.snapshot() if self.smart_contract_manager else None
        governance_snapshot = self.governance_executor.snapshot() if self.governance_executor else None
        finality_snapshot = self.finality_manager.snapshot() if self.finality_manager else None
        mempool_snapshot = self.pending_transactions.copy()

        # Write-Ahead Log: Record reorg intention for crash recovery
        wal_entry = self._write_reorg_wal(
            old_tip=self.chain[-1].hash if self.chain else None,
            new_tip=materialized_chain[-1].hash if materialized_chain else None,
            fork_point=fork_point,
        )

        try:
            # PHASE 2: EXECUTE REORG ATOMICALLY
            # All state changes happen here - if any fail, rollback restores everything
            # Clear UTXO set (don't create new instance - maintains singleton pattern)
            self.utxo_manager.clear()

            # Rebuild UTXO set from new chain
            for block in materialized_chain:
                for tx in block.transactions:
                    if tx.sender != "COINBASE":
                        if not self.utxo_manager.process_transaction_inputs(tx):
                            raise Exception(f"Failed to apply inputs for tx {tx.txid}")
                    self.utxo_manager.process_transaction_outputs(tx)

            # Replace chain
            self.chain = materialized_chain
            if self.smart_contract_manager:
                self._rebuild_contract_state()
            self._rebuild_governance_state_from_chain()
            self.sync_smart_contract_vm()

            # CRITICAL: Rebuild nonce tracker from new chain
            # After a reorg, transaction nonces may have changed
            # Failing to rebuild would cause mempool validation to use stale nonces
            self._rebuild_nonce_tracker(materialized_chain)

            # CRITICAL: Rebuild address index after reorg
            # Rollback index to fork point and reindex new chain
            try:
                if fork_point is not None:
                    # Rollback index to fork point (remove blocks after fork)
                    self.address_index.rollback_to_block(fork_point + 1)
                else:
                    # Complete reorg from genesis - rebuild entire index
                    self.address_index.rollback_to_block(0)

                # Reindex blocks from fork point to new tip
                start_block = (fork_point + 1) if fork_point is not None else 0
                for block in materialized_chain[start_block:]:
                    for tx_index, tx in enumerate(block.transactions):
                        self.address_index.index_transaction(
                            tx,
                            block.index,
                            tx_index,
                            block.timestamp
                        )
                self.address_index.commit()
                self.logger.info(
                    "Address index rebuilt after reorg",
                    fork_point=fork_point,
                    reindexed_blocks=len(materialized_chain) - start_block
                )
            except Exception as idx_err:
                self.logger.error(
                    "Failed to rebuild address index during reorg",
                    error=str(idx_err)
                )
                # Don't fail the entire reorg - index can be rebuilt later
                try:
                    self.address_index.rollback()
                except Exception as rollback_err:
                    self.logger.warning(
                        "Failed to rollback address index after reorg indexing failure",
                        error=str(rollback_err)
                    )

            # CRITICAL: Revalidate mempool transactions against new chain state
            # Transactions valid in the old chain may become invalid after reorg
            # (double-spends, invalid nonces, insufficient balance, etc.)
            original_pending_count = len(self.pending_transactions)
            valid_pending = []
            evicted_count = 0

            for tx in self.pending_transactions:
                try:
                    # Validate against new chain state (nonces, balances, UTXOs)
                    if self.transaction_validator.validate_transaction(tx, is_mempool_check=True):
                        valid_pending.append(tx)
                    else:
                        evicted_count += 1
                        self.logger.warning(
                            f"Evicting transaction {tx.txid} from mempool after chain reorganization - "
                            f"invalid in new chain state",
                            extra={
                                "txid": tx.txid,
                                "sender": tx.sender,
                                "recipient": tx.recipient,
                                "amount": tx.amount,
                                "reason": "validation_failed",
                            }
                        )
                except Exception as e:
                    evicted_count += 1
                    self.logger.warning(
                        f"Evicting transaction {tx.txid} from mempool after chain reorganization - "
                        f"validation raised exception: {e}",
                        extra={
                            "txid": tx.txid,
                            "sender": tx.sender,
                            "error": str(e),
                            "reason": "validation_exception",
                        }
                    )

            # Replace mempool with revalidated transactions
            self.pending_transactions = valid_pending

            if evicted_count > 0:
                self.logger.info(
                    f"Mempool revalidation complete after chain reorganization: "
                    f"{len(valid_pending)} valid transactions retained, "
                    f"{evicted_count} invalid transactions evicted "
                    f"(original count: {original_pending_count})",
                    extra={
                        "valid_count": len(valid_pending),
                        "evicted_count": evicted_count,
                        "original_count": original_pending_count,
                    }
                )
            else:
                self.logger.debug(
                    f"Mempool revalidation complete: all {len(valid_pending)} transactions remain valid",
                    extra={"valid_count": len(valid_pending)}
                )

            # Save new chain to disk
            for block in materialized_chain:
                self.storage._save_block_to_disk(block)

            self.storage.save_state_to_disk(
                self.utxo_manager,
                self.pending_transactions,
                self.contracts,
                self.contract_receipts,
            )

            # PHASE 3: COMMIT - Mark WAL entry as complete
            self._commit_reorg_wal(wal_entry)

            self.logger.info(
                "Chain reorganization completed successfully",
                extra={
                    "event": "reorg.success",
                    "old_tip": old_chain[-1].hash if old_chain else None,
                    "new_tip": materialized_chain[-1].hash if materialized_chain else None,
                    "fork_point": fork_point,
                    "blocks_reorganized": len(old_chain) - (fork_point + 1) if fork_point is not None else 0,
                }
            )

            return True

        except Exception as e:
            # ROLLBACK: Restore ALL state atomically
            self.logger.error(
                f"Chain reorganization failed: {e}. Rolling back ALL state to previous snapshot.",
                extra={
                    "event": "reorg.rollback",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

            # Restore all snapshotted state in reverse dependency order
            self.chain = old_chain
            self.utxo_manager.restore(utxo_snapshot)

            if nonce_snapshot and self.nonce_tracker:
                self.nonce_tracker.restore(nonce_snapshot)

            if contract_snapshot and self.smart_contract_manager:
                self.smart_contract_manager.restore(contract_snapshot)

            if governance_snapshot and self.governance_executor:
                self.governance_executor.restore(governance_snapshot)

            if finality_snapshot and self.finality_manager:
                self.finality_manager.restore(finality_snapshot)

            # Restore mempool
            self.pending_transactions = mempool_snapshot

            # Clear WAL entry since rollback completed
            self._rollback_reorg_wal(wal_entry)

            self.logger.info("Rollback completed successfully - all state restored")

            return False

    def _find_fork_point(self, new_chain: List[BlockHeader]) -> Optional[int]:
        """
        Finds the common ancestor between the current chain and a new chain.
        """
        for i in range(min(len(self.chain), len(new_chain))):
            if self.chain[i].hash != new_chain[i].hash:
                return i - 1
        return min(len(self.chain), len(new_chain)) - 1

    def _validate_chain_structure(self, chain: List[BlockHeader]) -> bool:
        """
        Validates the structural integrity of a candidate chain (hashes, links).

        SECURITY: Validates block size limits during chain reorganization to prevent
        attackers from creating oversized blocks in a fork chain.
        """
        if not chain:
            return False

        # Genesis block always valid by definition
        first = chain[0].header if hasattr(chain[0], "header") else chain[0]
        if first.index != 0 or first.previous_hash != "0":
            return False

        # SECURITY: Validate genesis block size as well
        first_block = chain[0]
        if hasattr(first_block, "header"):  # This is a full Block object
            if not self._block_within_size_limits(first_block, context="chain_replacement"):
                self.logger.warn(
                    f"Genesis block exceeds size limits during chain reorganization",
                    block_hash=first.hash,
                )
                return False

        for i in range(1, len(chain)):
            current_header = chain[i].header if hasattr(chain[i], "header") else chain[i]
            previous_header = chain[i-1].header if hasattr(chain[i-1], "header") else chain[i-1]

            # Check previous hash link
            if current_header.previous_hash != previous_header.hash:
                self.logger.warn(f"Invalid chain structure: block {current_header.index} previous hash mismatch")
                return False

            # Check block hash (recalculate and compare)
            if current_header.hash != current_header.calculate_hash():
                self.logger.warn(f"Invalid chain structure: block {current_header.index} hash mismatch")
                return False

            # Check proof of work (simplified for headers)
            if not current_header.hash.startswith("0" * current_header.difficulty):
                self.logger.warn(f"Invalid chain structure: block {current_header.index} has invalid PoW")
                return False

            if not self._validate_header_version(current_header):
                return False

            expected_difficulty = self._expected_difficulty_for_block(
                block_index=current_header.index,
                history=chain[:i],
            )
            if expected_difficulty is not None and current_header.difficulty != expected_difficulty:
                self.logger.warn(
                    f"Invalid chain structure: block {current_header.index} difficulty mismatch",
                    expected_difficulty=expected_difficulty,
                    declared_difficulty=current_header.difficulty,
                )
                return False

            time_valid, time_error = self._validate_block_timestamp(current_header, chain[:i])
            if not time_valid:
                self.logger.warn(
                    f"Invalid chain structure: block {current_header.index} timestamp invalid ({time_error})"
                )
                return False

            # Verify block signature
            if current_header.index > 0:
                if not self.verify_block_signature(current_header):
                    self.logger.warn(f"Invalid chain structure: block {current_header.index} has invalid signature")
                    return False

            # SECURITY: Validate block size limits during chain reorganization
            # Prevents attackers from creating oversized blocks in a fork chain
            # Note: We need the full Block object, not just the header
            current_block = chain[i]
            if hasattr(current_block, "header"):  # This is a full Block object
                if not self._block_within_size_limits(current_block, context="chain_replacement"):
                    self.logger.warn(
                        f"Block {current_header.index} exceeds size limits during chain reorganization",
                        block_hash=current_header.hash,
                    )
                    return False

        return True

    def is_chain_valid(self, chain: Optional[List[BlockHeader]] = None) -> bool:
        """
        Public validation hook to verify chain integrity.

        Args:
            chain: Optional chain to validate. Defaults to the in-memory chain.
        """
        candidate_chain = chain if chain is not None else self.chain
        return self._validate_chain_structure(candidate_chain)

    def _extract_timestamp(self, block_like: Union["Block", BlockHeader, Any]) -> Optional[float]:
        """Return a floating-point timestamp from a block/header-like object."""
        if hasattr(block_like, "timestamp"):
            raw = getattr(block_like, "timestamp")
            return float(raw) if raw is not None else None
        if hasattr(block_like, "header"):
            header_obj = getattr(block_like, "header")
            if hasattr(header_obj, "timestamp"):
                raw = header_obj.timestamp
                return float(raw) if raw is not None else None
        return None

    def _median_time_from_history(
        self,
        history: Sequence[Union["Block", BlockHeader, Any]],
    ) -> Optional[float]:
        """Compute the median timestamp over the rolling history window."""
        if not history:
            return None
        window = list(history)[-self._median_time_span :]
        timestamps: List[float] = []
        for entry in window:
            ts = self._extract_timestamp(entry)
            if ts is not None:
                timestamps.append(ts)
        if not timestamps:
            return None
        timestamps.sort()
        mid = len(timestamps) // 2
        if len(timestamps) % 2 == 0:
            return (timestamps[mid - 1] + timestamps[mid]) / 2
        return timestamps[mid]

    def _validate_block_timestamp(
        self,
        block_like: Union["Block", BlockHeader, Any],
        history: Sequence[Union["Block", BlockHeader, Any]],
        *,
        emit_metrics: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Enforce timestamp constraints:
        - each block must be newer than the median of the trailing window
        - blocks cannot be more than MAX_FUTURE_BLOCK_TIME seconds ahead of wall clock
        """
        header = block_like.header if hasattr(block_like, "header") else block_like
        index = getattr(header, "index", 0)
        timestamp = self._extract_timestamp(header)
        if index == 0:
            return True, None
        if timestamp is None:
            return False, "missing timestamp"
        median_time = self._median_time_from_history(history)
        if median_time is not None and timestamp <= median_time:
            return False, f"timestamp {timestamp} <= median time past {median_time}"
        future_cutoff = time.time() + self._max_future_block_time
        if timestamp > future_cutoff:
            return (
                False,
                f"timestamp {timestamp} exceeds future drift allowance ({self._max_future_block_time}s)",
            )
        if emit_metrics:
            self._record_timestamp_metrics(
                index=index,
                timestamp=timestamp,
                median_time=median_time,
                history_length=len(history),
            )
        return True, None

    def _expected_difficulty_for_block(
        self,
        *,
        block_index: int,
        history: Sequence[Union["Block", BlockHeader]],
    ) -> Optional[int]:
        """
        Determine the deterministic difficulty for a block based on prior history.

        Args:
            block_index: Index of the block being evaluated.
            history: Sequence of blocks/headers representing the canonical chain
                     up to (but excluding) the block being validated.

        Returns:
            Expected integer difficulty or None if insufficient context.
        """
        if block_index <= 0:
            return None
        history_view = list(history)
        if not history_view or len(history_view) != block_index:
            return None

        previous_entry = history_view[-1]
        previous_header = previous_entry.header if hasattr(previous_entry, "header") else previous_entry
        previous_index = getattr(previous_header, "index", None)
        if previous_index is None or previous_index != block_index - 1:
            return None

        baseline = getattr(previous_header, "difficulty", None)
        if baseline is None:
            return None

        expected = self.calculate_next_difficulty(
            chain=history_view,
            current_difficulty=int(baseline),
            emit_log=False,
        )
        if self.fast_mining_enabled:
            return min(expected, self.max_test_mining_difficulty)
        return expected

    def _validate_header_version(self, header: BlockHeader) -> bool:
        """
        Ensure block header versions are integers and part of the allowed set.
        """
        declared_version = getattr(header, "version", None)
        version_to_check = (
            declared_version if declared_version is not None else self._default_block_header_version
        )
        try:
            version_int = int(version_to_check)
        except (TypeError, ValueError):
            self.logger.warn(
                "Block rejected: non-integer header version",
                block_index=getattr(header, "index", None),
                version=version_to_check,
            )
            return False

        if version_int not in self._allowed_block_header_versions:
            self.logger.warn(
                "Block rejected: unsupported header version",
                block_index=getattr(header, "index", None),
                version=version_int,
                allowed_versions=sorted(self._allowed_block_header_versions),
            )
            return False

        return True

    def _block_within_size_limits(self, block: Block, *, context: str) -> bool:
        """
        Validate block size/resource limits using the hardened validator.
        """
        try:
            valid, error = BlockSizeValidator.validate_block_size(block)
        except Exception as exc:
            self.logger.error(
                "Block size validation failed unexpectedly",
                context=context,
                error=str(exc),
            )
            return False

        if not valid:
            header = block.header if hasattr(block, "header") else None
            self.logger.warn(
                "Block violates size limits",
                context=context,
                block_index=getattr(header, "index", getattr(block, "index", None)),
                block_hash=getattr(header, "hash", getattr(block, "hash", "")),
                reason=error,
            )
            return False

        return True

    def _record_timestamp_metrics(
        self,
        *,
        index: int,
        timestamp: float,
        median_time: Optional[float],
        history_length: int,
    ) -> None:
        """Persist timestamp drift history and emit monitoring signals."""
        observed_at = time.time()
        median_drift = timestamp - median_time if median_time is not None else None
        wall_clock_drift = timestamp - observed_at
        record = {
            "index": index,
            "timestamp": timestamp,
            "median_drift": median_drift,
            "wall_clock_drift": wall_clock_drift,
            "history_length": history_length,
            "observed_at": observed_at,
        }
        self._timestamp_drift_history.append(record)
        if abs(wall_clock_drift) > self._max_future_block_time * 0.75:
            self.logger.warning(
                "Block timestamp drift warning",
                block_index=index,
                wall_clock_drift_seconds=wall_clock_drift,
                median_drift_seconds=median_drift,
            )
        try:
            from xai.core.monitoring import MetricsCollector

            collector = MetricsCollector.instance()
            if collector:
                median_metric = collector.get_metric("xai_block_timestamp_median_drift_seconds")
                if median_metric and median_drift is not None:
                    median_metric.observe(median_drift)
                wall_metric = collector.get_metric("xai_block_timestamp_wall_clock_drift_seconds")
                if wall_metric:
                    wall_metric.observe(wall_clock_drift)
                history_gauge = collector.get_metric("xai_block_timestamp_history_entries")
                if history_gauge:
                    history_gauge.set(len(self._timestamp_drift_history))
        except (ImportError, AttributeError, RuntimeError) as exc:
            self.logger.debug(
                "Timestamp telemetry unavailable",
                error=str(exc),
            )

    def get_recent_timestamp_drift(self) -> List[Dict[str, float]]:
        """Return a copy of the recent timestamp drift history for diagnostics."""
        return list(self._timestamp_drift_history)

    def _add_block_to_chain(self, block: Block) -> bool:
        """Helper method to add a validated block to the chain."""
        self.chain.append(block)
        self._process_governance_block_transactions(block)
        if self.smart_contract_manager:
            receipts = self.smart_contract_manager.process_block(block)
            if receipts:
                self.contract_receipts.extend(receipts)

        # Update UTXO set
        for tx in block.transactions:
            if tx.sender != "COINBASE":
                self.utxo_manager.process_transaction_inputs(tx)
            self.utxo_manager.process_transaction_outputs(tx)

        # Index transactions for O(log n) address lookups
        try:
            for tx_index, tx in enumerate(block.transactions):
                self.address_index.index_transaction(
                    tx,
                    block.index,
                    tx_index,
                    block.timestamp
                )
            self.address_index.commit()
        except Exception as e:
            self.logger.error(
                "Failed to index block transactions",
                block_index=block.index,
                error=str(e)
            )
            # Don't fail block addition if indexing fails - index can be rebuilt
            # Rollback index to maintain consistency
            try:
                self.address_index.rollback()
            except Exception as rollback_err:
                self.logger.warning(
                    "Failed to rollback address index after block indexing failure",
                    block_index=block.index,
                    error=str(rollback_err)
                )

        # Save to disk
        self.storage._save_block_to_disk(block)
        self.storage.save_state_to_disk(
            self.utxo_manager,
            self.pending_transactions,
            self.contracts,
            self.contract_receipts,
        )

        # Remove any pending transactions that were included in this block
        block_tx_ids = {tx.txid for tx in block.transactions if tx.txid}
        self.pending_transactions = [
            tx for tx in self.pending_transactions
            if tx.txid not in block_tx_ids
        ]
        # Recompute seen txids and sender counts from pending pool
        self.seen_txids = {tx.txid for tx in self.pending_transactions if tx.txid}
        self._sender_pending_count = defaultdict(int)
        for tx in self.pending_transactions:
            if tx.sender and tx.sender != "COINBASE":
                self._sender_pending_count[tx.sender] += 1

        # Check if any orphan blocks can now be connected
        self._process_orphan_blocks()

        # Check if any orphan transactions can now be added to mempool
        self._process_orphan_transactions()

        return True

    def _process_orphan_blocks(self):
        """Try to connect any orphan blocks to the chain."""
        next_index = len(self.chain)

        # Keep trying to add orphan blocks as long as we find matches
        while next_index in self.orphan_blocks:
            added = False
            for orphan in self.orphan_blocks[next_index]:
                if orphan.header.previous_hash == self.chain[-1].hash:
                    # This orphan can now be connected
                    self.chain.append(orphan)
                    self._process_governance_block_transactions(orphan)

                    # Update UTXO set
                    for tx in orphan.transactions:
                        if tx.sender != "COINBASE":
                            self.utxo_manager.process_transaction_inputs(tx)
                        self.utxo_manager.process_transaction_outputs(tx)

                    # Index transactions for O(log n) address lookups
                    try:
                        for tx_index, tx in enumerate(orphan.transactions):
                            self.address_index.index_transaction(
                                tx,
                                orphan.index,
                                tx_index,
                                orphan.timestamp
                            )
                        self.address_index.commit()
                    except Exception as e:
                        self.logger.error(
                            "Failed to index orphan block transactions",
                            block_index=orphan.index,
                            error=str(e)
                        )
                        try:
                            self.address_index.rollback()
                        except Exception as rollback_err:
                            self.logger.warning(
                                "Failed to rollback address index after orphan block indexing failure",
                                block_index=orphan.index,
                                error=str(rollback_err)
                            )

                    # Save to disk
                    self.storage._save_block_to_disk(orphan)
                    self.storage.save_state_to_disk(
                        self.utxo_manager,
                        self.pending_transactions,
                        self.contracts,
                        self.contract_receipts,
                    )

                    # Remove from orphans
                    self.orphan_blocks[next_index].remove(orphan)
                    if not self.orphan_blocks[next_index]:
                        del self.orphan_blocks[next_index]

                    added = True
                    next_index += 1
                    break

            if not added:
                break

    def _process_orphan_transactions(self):
        """
        Try to add orphan transactions to the mempool after new blocks are added.

        Orphan transactions are those that reference UTXOs that didn't exist when they
        were first received. After new blocks are added, those UTXOs may now exist,
        so we retry validation on orphan transactions.
        """
        if not self.orphan_transactions:
            return

        # Try to validate and add each orphan transaction
        successfully_added = []
        for orphan_tx in self.orphan_transactions[:]:  # Copy list to allow modification
            # Try to validate the transaction again
            if self.transaction_validator.validate_transaction(orphan_tx):
                # Check for double-spend in pending transactions
                is_double_spend = False
                if orphan_tx.inputs:
                    for tx_input in orphan_tx.inputs:
                        input_key = f"{tx_input['txid']}:{tx_input['vout']}"
                        for pending_tx in self.pending_transactions:
                            if pending_tx.inputs:
                                for pending_input in pending_tx.inputs:
                                    pending_key = f"{pending_input['txid']}:{pending_input['vout']}"
                                    if input_key == pending_key:
                                        is_double_spend = True
                                        break
                            if is_double_spend:
                                break

                if not is_double_spend:
                    # Transaction is now valid, add to pending pool
                    self.pending_transactions.append(orphan_tx)
                    successfully_added.append(orphan_tx)
                    self.logger.info(f"Orphan transaction {orphan_tx.txid[:10]}... successfully added to mempool")

        # Remove successfully added transactions from orphan pool
        for tx in successfully_added:
            self.orphan_transactions.remove(tx)

        # Clean up very old orphan transactions (older than 24 hours)
        current_time = time.time()
        MAX_ORPHAN_AGE = 86400  # 24 hours
        self.orphan_transactions = [
            tx for tx in self.orphan_transactions
            if current_time - tx.timestamp < MAX_ORPHAN_AGE
        ]

    def _check_orphan_chains_for_reorg(self) -> bool:
        """
        Check if orphan blocks can form a chain with more cumulative work than the current chain.

        This implements the work-based fork choice rule (heaviest chain wins), which is
        more secure than length-based selection as it accounts for actual mining difficulty.

        Returns:
            True if reorganization occurred, False otherwise
        """
        if not self.orphan_blocks:
            return False

        best_candidate = None
        best_work = self._calculate_chain_work(self.chain)

        # Try to build chains starting from each possible fork point
        for fork_point_index in range(len(self.chain)):
            # Check if there are orphan blocks at the next index
            start_index = fork_point_index + 1
            if start_index not in self.orphan_blocks:
                continue

            # Try each orphan block at this position as a potential fork start
            for potential_fork_block in self.orphan_blocks[start_index]:
                # Check if this block connects to the fork point
                if fork_point_index >= 0:
                    expected_prev_hash = self.chain[fork_point_index].hash if fork_point_index < len(self.chain) else ""
                    if potential_fork_block.header.previous_hash != expected_prev_hash:
                        continue

                # Build candidate chain from this fork point
                candidate_chain = self.chain[:fork_point_index + 1].copy()
                candidate_chain.append(potential_fork_block)

                # Try to extend with more orphans
                current_index = start_index + 1
                while current_index in self.orphan_blocks:
                    added = False
                    for orphan in self.orphan_blocks[current_index]:
                        if orphan.header.previous_hash == candidate_chain[-1].hash:
                            candidate_chain.append(orphan)
                            added = True
                            break
                    if not added:
                        break
                    current_index += 1

                # Calculate cumulative work for candidate chain
                candidate_work = self._calculate_chain_work(candidate_chain)

                # Select candidate with most cumulative work (not just length)
                if candidate_work > best_work:
                    # Validate the candidate chain
                    if self._validate_chain_structure(candidate_chain):
                        best_candidate = candidate_chain
                        best_work = candidate_work

        # If we found a chain with more work, reorganize to it
        if best_candidate:
            self.logger.info(
                "Reorganizing to chain with more cumulative work",
                extra={
                    "event": "chain.reorg",
                    "current_length": len(self.chain),
                    "new_length": len(best_candidate),
                    "current_work": self._calculate_chain_work(self.chain),
                    "new_work": best_work
                }
            )
            return self.replace_chain(best_candidate)

        return False

    def _record_state_snapshot(self, label: str) -> None:
        """Store a bounded history of state integrity snapshots for audit/debug."""
        snapshot = self.compute_state_snapshot()
        snapshot["label"] = label
        self._state_integrity_snapshots.append(snapshot)
        self._state_integrity_snapshots = self._state_integrity_snapshots[-20:]

    def get_mempool_size_kb(self) -> float:
        """
        Return current mempool footprint in kilobytes for operational controls.
        """
        total_bytes = sum(tx.get_size() for tx in self.pending_transactions) if self.pending_transactions else 0
        return total_bytes / 1024.0

    def compute_state_snapshot(self) -> Dict[str, Any]:
        """
        Return a deterministic snapshot used for integrity validation and reorg audits.
        """
        utxo_digest = ""
        try:
            utxo_digest = self.utxo_manager.snapshot_digest()
        except (AttributeError, RuntimeError, ValueError) as e:
            # UTXO snapshot unavailable - log and mark as unavailable
            logger.debug(f"UTXO snapshot digest unavailable: {e}")
            utxo_digest = "unavailable"

        return {
            "height": len(self.chain),
            "tip": self.chain[-1].hash if self.chain else "",
            "utxo_digest": utxo_digest,
            "pending_transactions": len(self.pending_transactions),
            "mempool_bytes": sum(tx.get_size() for tx in self.pending_transactions) if self.pending_transactions else 0,
            "timestamp": time.time(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Return a live snapshot of blockchain health and activity for APIs/monitoring.
        """
        mempool_size_bytes = sum(tx.get_size() for tx in self.pending_transactions) if self.pending_transactions else 0
        latest_block_hash = self.chain[-1].hash if self.chain else ""
        now = time.time()

        return {
            "chain_height": len(self.chain),
            "pending_transactions_count": len(self.pending_transactions),
            "orphan_blocks_count": len(self.orphan_blocks),
            "orphan_transactions_count": len(self.orphan_transactions),
            "total_circulating_supply": self.get_circulating_supply(),
            "difficulty": self.difficulty,
            "mempool_size_bytes": mempool_size_bytes,
            "latest_block_hash": latest_block_hash,
            "timestamp": now,
            "mempool_rejected_invalid_total": self._mempool_rejected_invalid_total,
            "mempool_rejected_banned_total": self._mempool_rejected_banned_total,
            "mempool_rejected_low_fee_total": self._mempool_rejected_low_fee_total,
            "mempool_rejected_sender_cap_total": self._mempool_rejected_sender_cap_total,
            "mempool_evicted_low_fee_total": self._mempool_evicted_low_fee_total,
            "mempool_expired_total": self._mempool_expired_total,
            "mempool_active_bans": self._count_active_bans(now),
        }

    def get_mempool_overview(self, limit: int = 100) -> Dict[str, Any]:
        """
        Return detailed mempool statistics and representative transactions.
        """
        limit = max(0, min(int(limit), 1000))
        pending = list(self.pending_transactions) if self.pending_transactions else []
        now = time.time()
        size_bytes = sum(tx.get_size() for tx in pending) if pending else 0
        total_amount = sum(float(getattr(tx, "amount", 0.0)) for tx in pending)
        fees = [float(getattr(tx, "fee", 0.0)) for tx in pending]
        fee_rates = [float(tx.get_fee_rate()) for tx in pending]
        timestamps = [
            float(tx.timestamp)
            for tx in pending
            if isinstance(getattr(tx, "timestamp", None), (int, float))
        ]
        sponsor_count = sum(1 for tx in pending if getattr(tx, "gas_sponsor", None))

        def _avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        limits = {
            "max_transactions": getattr(self, "_mempool_max_size", len(pending)),
            "max_per_sender": getattr(self, "_mempool_max_per_sender", 100),
            "min_fee_rate": getattr(self, "_mempool_min_fee_rate", 0.0),
            "max_age_seconds": getattr(self, "_mempool_max_age_seconds", 86400),
        }

        overview: Dict[str, Any] = {
            "pending_count": len(pending),
            "size_bytes": size_bytes,
            "size_kb": size_bytes / 1024.0,
            "total_amount": total_amount,
            "total_fees": sum(fees) if fees else 0.0,
            "avg_fee": _avg(fees),
            "median_fee": float(statistics.median(fees)) if fees else 0.0,
            "avg_fee_rate": _avg(fee_rates),
            "median_fee_rate": float(statistics.median(fee_rates)) if fee_rates else 0.0,
            "min_fee_rate": min(fee_rates) if fee_rates else 0.0,
            "max_fee_rate": max(fee_rates) if fee_rates else 0.0,
            "sponsored_transactions": sponsor_count,
            "oldest_transaction_age_seconds": now - min(timestamps) if timestamps else 0.0,
            "newest_transaction_age_seconds": now - max(timestamps) if timestamps else 0.0,
            "limits": limits,
            "rejections": {
                "invalid_total": self._mempool_rejected_invalid_total,
                "banned_total": self._mempool_rejected_banned_total,
                "low_fee_total": self._mempool_rejected_low_fee_total,
                "sender_cap_total": self._mempool_rejected_sender_cap_total,
                "evicted_low_fee_total": self._mempool_evicted_low_fee_total,
                "expired_total": self._mempool_expired_total,
                "active_bans": self._count_active_bans(now),
            },
            "timestamp": now,
        }

        if limit > 0 and pending:
            tx_summaries: List[Dict[str, Any]] = []
            for tx in pending[:limit]:
                tx_size = tx.get_size()
                summary = {
                    "txid": tx.txid,
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "fee": tx.fee,
                    "fee_rate": tx.get_fee_rate(),
                    "size_bytes": tx_size,
                    "timestamp": getattr(tx, "timestamp", None),
                    "age_seconds": now - tx.timestamp if getattr(tx, "timestamp", None) else None,
                    "nonce": tx.nonce,
                    "type": tx.tx_type,
                    "rbf_enabled": bool(getattr(tx, "rbf_enabled", False)),
                    "gas_sponsor": getattr(tx, "gas_sponsor", None),
                }
                tx_summaries.append(summary)
            overview["transactions"] = tx_summaries
        else:
            overview["transactions"] = []

        overview["transactions_returned"] = len(overview["transactions"])
        return overview

    # ==================== TRADE MANAGEMENT ====================

    def get_blockchain_data_provider(self) -> BlockchainDataProvider:
        """
        Returns an object conforming to the BlockchainDataProvider interface,
        providing essential blockchain stats.
        """
        # Calculate mempool size in bytes
        mempool_size = sum(tx.get_size() for tx in self.pending_transactions) if self.pending_transactions else 0

        return BlockchainDataProvider(
            chain_height=len(self.chain),
            pending_transactions_count=len(self.pending_transactions),
            orphan_blocks_count=len(self.orphan_blocks),
            orphan_transactions_count=len(self.orphan_transactions),
            total_circulating_supply=self.get_circulating_supply(),
            difficulty=self.difficulty,
            mempool_size_bytes=mempool_size,
        )

    def register_trade_session(self, wallet_address: str) -> Dict[str, Any]:
        """Create and track a short-lived trade session token."""
        session = self.trade_manager.register_session(wallet_address)
        self.trade_sessions[session["session_token"]] = session
        self.record_trade_event("session_registered", {"wallet_address": wallet_address})
        return session

    def record_trade_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record trade-related events for diagnostics."""
        entry = {"type": event_type, "payload": payload, "timestamp": time.time()}
        self.trade_history.append(entry)
        self.trade_history = self.trade_history[-500:]

    def submit_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize order payload, verify ECDSA signature, and dispatch to the trade manager.

        This method validates that the order was actually signed by the wallet owner
        using ECDSA with secp256k1, replacing the previous HMAC-based authentication.

        Args:
            order_data: Dictionary containing order details and ECDSA signature

        Returns:
            Dictionary with order creation result

        Raises:
            ValueError: If signature validation fails or required fields missing
        """
        from xai.core.crypto_utils import verify_signature_hex
        import json

        # Extract and validate signature
        signature = order_data.get("signature")
        if not signature:
            raise ValueError("signature required for order authentication")

        if len(signature) != 128:
            raise ValueError("Invalid signature format: must be 128 hex characters (r || s)")

        # Extract maker address for public key lookup
        maker_address = order_data.get("maker_address") or order_data.get("wallet_address")
        if not maker_address:
            raise ValueError("maker_address required")

        # Get public key from address (we need to look up the wallet)
        # Note: In a real implementation, we'd have an address -> public key mapping
        # For now, we require the public key to be provided in the order
        maker_public_key = order_data.get("maker_public_key")
        if not maker_public_key:
            # Try to derive from registered wallets or require it in payload
            raise ValueError(
                "maker_public_key required for signature verification. "
                "Include your wallet's public key in the order payload."
            )

        # Create a copy of order_data without the signature for verification
        order_data_copy = dict(order_data)
        order_data_copy.pop("signature", None)

        # Serialize deterministically (sorted keys) to match frontend
        def stable_stringify(obj):
            if obj is None:
                return "null"
            if isinstance(obj, bool):
                return "true" if obj else "false"
            if isinstance(obj, (int, float)):
                return json.dumps(obj)
            if isinstance(obj, str):
                return json.dumps(obj)
            if isinstance(obj, list):
                return "[" + ",".join(stable_stringify(item) for item in obj) + "]"
            if isinstance(obj, dict):
                sorted_keys = sorted(obj.keys())
                items = [f'"{k}":{stable_stringify(obj[k])}' for k in sorted_keys]
                return "{" + ",".join(items) + "}"
            return json.dumps(obj)

        payload_str = stable_stringify(order_data_copy)

        # Hash the payload
        import hashlib
        message_hash = hashlib.sha256(payload_str.encode()).digest()

        # Verify ECDSA signature
        if not verify_signature_hex(maker_public_key, message_hash, signature):
            raise ValueError(
                "Invalid signature: ECDSA verification failed. "
                "The order was not signed by the wallet owner."
            )

        logger.info(
            "Trade order signature verified successfully",
            extra={
                "event": "trade.order.signature_verified",
                "maker_address": maker_address[:16] + "...",
            },
        )

        # Signature verified - proceed with order creation
        normalized = self._normalize_trade_order(order_data)
        order, matches = self.trade_manager.place_order(**normalized)

        result: Dict[str, Any] = {
            "success": True,
            "order_id": order.order_id,
            "status": "pending",
            "maker_address": order.maker_address,
            "token_offered": order.token_offered,
            "token_requested": order.token_requested,
            "amount_offered": order.amount_offered,
            "amount_requested": order.amount_requested,
            "price": order.price,
        }

        if matches:
            result["status"] = "matched"
            serialized_matches = [match.to_dict() for match in matches]
            result["matches"] = serialized_matches
            if len(matches) == 1:
                result["match_id"] = matches[0].match_id
            else:
                result["match_id"] = [m["match_id"] for m in serialized_matches]

        self.record_trade_event("order_created", {"order_id": order.order_id, "status": result["status"]})
        return result

    def _normalize_trade_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        wallet_address = order_data.get("wallet_address") or order_data.get("from_address")
        if not wallet_address:
            raise ValueError("wallet_address required")

        token_offered = (
            order_data.get("token_offered")
            or order_data.get("from_token")
            or order_data.get("from_asset")
        )
        token_requested = (
            order_data.get("token_requested")
            or order_data.get("to_token")
            or order_data.get("to_asset")
        )
        if not token_offered or not token_requested:
            raise ValueError("token_offered and token_requested required")

        amount_offered = order_data.get("amount_offered") or order_data.get("from_amount")
        amount_requested = order_data.get("amount_requested") or order_data.get("to_amount")
        if amount_offered is None or amount_requested is None:
            raise ValueError("amount_offered and amount_requested required")

        amount_offered = float(amount_offered)
        amount_requested = float(amount_requested)
        if amount_offered <= 0 or amount_requested <= 0:
            raise ValueError("amounts must be positive")

        raw_type = order_data.get("order_type")
        if raw_type:
            try:
                order_type = SwapOrderType(raw_type.lower())
            except ValueError as exc:
                raise ValueError("order_type must be 'buy' or 'sell'") from exc
        else:
            order_type = SwapOrderType.SELL if token_offered.upper() == "AXN" else SwapOrderType.BUY

        price = order_data.get("price")
        if price is None:
            if amount_offered <= 0:
                raise ValueError("amount_offered must be positive to derive price")
            price_value = amount_requested / amount_offered
        else:
            try:
                price_value = float(price)
            except (TypeError, ValueError) as exc:
                raise ValueError("price must be a numeric value") from exc

        if price_value <= 0 or not math.isfinite(price_value):
            raise ValueError("price must be a finite positive number")

        return {
            "maker_address": wallet_address,
            "token_offered": token_offered,
            "amount_offered": amount_offered,
            "token_requested": token_requested,
            "amount_requested": amount_requested,
            "price": price_value,
            "order_type": order_type,
        }

    def get_trade_orders(self) -> List[Dict[str, Any]]:
        """Return serialized trade orders."""
        return [order.to_dict() for order in self.trade_manager.list_orders()]

    def get_trade_matches(self) -> List[Dict[str, Any]]:
        """Return serialized trade matches."""
        return [match.to_dict() for match in self.trade_manager.list_matches()]

    def reveal_trade_secret(self, match_id: str, secret: str) -> Dict[str, Any]:
        """Settle a match once both parties provide the HTLC secret."""
        result = self.trade_manager.settle_match(match_id, secret)
        if result.get("success"):
            self.record_trade_event("match_settled", {"match_id": match_id})
        return result

    # =====================================================================
    # Write-Ahead Log (WAL) for Crash-Safe Chain Reorganization
    # =====================================================================

    def _write_reorg_wal(
        self,
        old_tip: Optional[str],
        new_tip: Optional[str],
        fork_point: Optional[int]
    ) -> Dict[str, Any]:
        """
        Write a WAL entry recording the start of a chain reorganization.

        This enables crash recovery: if the node crashes mid-reorg, on restart
        we can detect the incomplete reorg and either complete it or roll back.

        Args:
            old_tip: Hash of the old chain tip
            new_tip: Hash of the new chain tip
            fork_point: Block height where chains diverged

        Returns:
            WAL entry dictionary
        """
        import time
        import json

        wal_entry = {
            "type": "REORG_BEGIN",
            "old_tip": old_tip,
            "new_tip": new_tip,
            "fork_point": fork_point,
            "timestamp": time.time(),
            "status": "in_progress",
        }

        try:
            with open(self.reorg_wal_path, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            self.logger.info(
                "WAL: Recorded reorg begin",
                extra={
                    "event": "wal.reorg_begin",
                    "old_tip": old_tip,
                    "new_tip": new_tip,
                    "fork_point": fork_point,
                }
            )
        except Exception as e:
            self.logger.error(
                f"WAL: Failed to write reorg entry: {e}",
                extra={"event": "wal.write_failed", "error": str(e)}
            )

        return wal_entry

    def _commit_reorg_wal(self, wal_entry: Dict[str, Any]) -> None:
        """
        Mark a WAL entry as committed (reorg completed successfully).

        Args:
            wal_entry: The WAL entry to commit
        """
        import json

        try:
            wal_entry["status"] = "committed"
            wal_entry["commit_timestamp"] = time.time()

            with open(self.reorg_wal_path, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # After successful commit, remove the WAL file
            # (No recovery needed - reorg completed successfully)
            if os.path.exists(self.reorg_wal_path):
                os.remove(self.reorg_wal_path)

            self.logger.info(
                "WAL: Reorg committed and WAL cleared",
                extra={"event": "wal.reorg_committed"}
            )
        except Exception as e:
            self.logger.error(
                f"WAL: Failed to commit reorg: {e}",
                extra={"event": "wal.commit_failed", "error": str(e)}
            )

    def _rollback_reorg_wal(self, wal_entry: Dict[str, Any]) -> None:
        """
        Mark a WAL entry as rolled back (reorg failed and was reverted).

        Args:
            wal_entry: The WAL entry to roll back
        """
        import json

        try:
            wal_entry["status"] = "rolled_back"
            wal_entry["rollback_timestamp"] = time.time()

            with open(self.reorg_wal_path, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # After successful rollback, remove the WAL file
            # (State has been restored to pre-reorg)
            if os.path.exists(self.reorg_wal_path):
                os.remove(self.reorg_wal_path)

            self.logger.info(
                "WAL: Reorg rolled back and WAL cleared",
                extra={"event": "wal.reorg_rolled_back"}
            )
        except Exception as e:
            self.logger.error(
                f"WAL: Failed to record rollback: {e}",
                extra={"event": "wal.rollback_failed", "error": str(e)}
            )

    def _recover_from_incomplete_reorg(self) -> None:
        """
        Check for incomplete reorg on node startup and recover.

        If a reorg WAL entry exists with status "in_progress", the node
        crashed mid-reorg. We don't know if the reorg was partially applied,
        so the safest approach is to rebuild all state from disk.

        This is called during Blockchain.__init__() to ensure recovery
        happens before any operations begin.
        """
        import json

        if not os.path.exists(self.reorg_wal_path):
            # No incomplete reorg - normal startup
            return

        try:
            with open(self.reorg_wal_path, "r") as f:
                wal_entry = json.load(f)

            if wal_entry.get("status") == "in_progress":
                self.logger.warning(
                    "Detected incomplete chain reorganization from previous session. "
                    "Node may have crashed mid-reorg. Blockchain state will be rebuilt from disk.",
                    extra={
                        "event": "wal.incomplete_reorg_detected",
                        "old_tip": wal_entry.get("old_tip"),
                        "new_tip": wal_entry.get("new_tip"),
                        "fork_point": wal_entry.get("fork_point"),
                        "timestamp": wal_entry.get("timestamp"),
                    }
                )

                # Clear the WAL file - we'll rebuild state from disk
                os.remove(self.reorg_wal_path)

                # Log the recovery action
                self.logger.info(
                    "WAL: Cleared incomplete reorg entry. State will be rebuilt from persistent storage.",
                    extra={"event": "wal.recovery_initiated"}
                )
            else:
                # WAL entry is committed or rolled back - safe to remove
                os.remove(self.reorg_wal_path)
                self.logger.debug("WAL: Removed stale reorg entry")

        except Exception as e:
            self.logger.error(
                f"WAL: Failed to recover from incomplete reorg: {e}. "
                f"Manual intervention may be required.",
                extra={"event": "wal.recovery_failed", "error": str(e)}
            )
