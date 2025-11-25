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
from typing import List, Dict, Optional, Tuple, Any, Union
from datetime import datetime
import base58
from xai.core.config import Config
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


class Transaction:
    """Real cryptocurrency transaction with ECDSA signatures, supporting UTXO model."""

    def __init__(
        self,
        sender: str,
        recipient: str,
        amount: float,
        fee: float = 0.0,
        public_key: Optional[str] = None,
        tx_type: str = "normal",
        nonce: Optional[int] = None,
        inputs: Optional[List[Dict[str, Any]]] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.sender = sender
        self.recipient = recipient  # For simplicity, still keep a primary recipient, but outputs will define actual distribution
        self.amount = amount  # This will represent the primary output amount
        self.fee = fee
        self.timestamp = time.time()
        self.signature = None
        self.txid = None
        self.public_key = public_key  # Store sender's public key for signature verification
        self.tx_type = tx_type  # Transaction type: normal, airdrop, treasure, refund, timecapsule
        self.nonce = nonce
        self.metadata: Dict[str, Any] = metadata or {}
        self.inputs = (
            inputs if inputs is not None else []
        )  # List of {'txid': str, 'vout': int, 'signature': str}
        self.outputs = (
            outputs if outputs is not None else []
        )  # List of {'address': str, 'amount': float}

        # If no explicit outputs are provided, create a default one for the recipient
        if not self.outputs and self.recipient and self.amount > 0:
            self.outputs.append({"address": self.recipient, "amount": self.amount})

    def calculate_hash(self) -> str:
        """Calculate transaction hash (TXID)"""
        tx_data = {
            "sender": self.sender,
            "recipient": self.recipient,  # Keep for backward compatibility/simplicity in some places
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

    def sign_transaction(self, private_key: str) -> None:
        """Sign transaction with sender's private key"""
        if self.sender == "COINBASE":
            # Coinbase transactions don't need signatures
            self.txid = self.calculate_hash()
            return

        try:
            message = self.calculate_hash().encode()
            self.signature = sign_message_hex(private_key, message)
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
            # Verify the address matches this public key
            pub_hash = hashlib.sha256(self.public_key.encode()).hexdigest()
            expected_address = f"XAI{pub_hash[:40]}"
            if expected_address != self.sender:
                print(f"Address mismatch: expected {expected_address}, got {self.sender}")
                return False

            # Recalculate hash to verify against the signature
            message = self.calculate_hash().encode()
            return verify_signature_hex(self.public_key, message, self.signature)
        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "txid": self.txid,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "public_key": self.public_key,
            "tx_type": self.tx_type,
            "nonce": self.nonce,
            "metadata": self.metadata,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }


class Block:
    """Blockchain block with real proof-of-work"""

    def __init__(
        self, index: int, transactions: List[Transaction], previous_hash: str, difficulty: int = 4
    ) -> None:
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.difficulty = difficulty
        self.nonce = 0
        self.hash = None
        self.merkle_root = self.calculate_merkle_root()

        # Extract miner address from coinbase transaction
        self.miner = None
        if transactions and transactions[0].sender == "COINBASE":
            self.miner = transactions[0].recipient

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

    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self) -> str:
        """Mine block with proof-of-work"""
        target = "0" * self.difficulty

        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target):
                print(f"Block mined! Hash: {self.hash}")
                return self.hash
            self.nonce += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "hash": self.hash,
            "difficulty": self.difficulty,
        }

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

    def __init__(self, data_dir: str = "data") -> None:
        self.storage = BlockchainStorage(data_dir)
        self.chain: List[Block] = (
            []
        )  # This will be a cache of loaded blocks, not the primary storage
        self.pending_transactions: List[Transaction] = []
        self.difficulty = 4
        self.initial_block_reward = 12.0  # Per WHITEPAPER: Initial Block Reward is 12 XAI
        self.halving_interval = 262800  # Per WHITEPAPER: Halving every 262,800 blocks
        self.max_supply = 121_000_000.0  # Per WHITEPAPER: Maximum Supply is 121 million XAI
        self.transaction_fee_percent = 0.24
        self.utxo_manager = UTXOManager()

        # Initialize gamification features
        self.airdrop_manager = AirdropManager()
        self.streak_tracker = StreakTracker()
        self.treasure_manager = TreasureHuntManager()
        self.fee_refund_calculator = FeeRefundCalculator()
        self.timecapsule_manager = TimeCapsuleManager()
        self.nonce_tracker = NonceTracker()
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

        if not self._load_from_disk():
            self.create_genesis_block()

        latest_block = self.chain[-1] if self.chain else None
        mining_start_time = latest_block.timestamp if latest_block else time.time()
        self.governance_state = GovernanceState(mining_start_time=mining_start_time)
        self.governance_executor = GovernanceExecutionEngine(self)
        self._rebuild_governance_state_from_chain()
        self.sync_smart_contract_vm()

    # ==================== DESERIALIZATION HELPERS ====================

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
        )
        tx.timestamp = tx_data.get("timestamp", time.time())
        tx.signature = tx_data.get("signature")
        tx.txid = tx_data.get("txid") or tx.calculate_hash()
        tx.metadata = tx_data.get("metadata", {})
        return tx

    @classmethod
    def deserialize_block(cls, block_data: Dict[str, Any]) -> Block:
        transactions = [cls._transaction_from_dict(td) for td in block_data.get("transactions", [])]
        block = Block(
            block_data.get("index", 0),
            transactions,
            block_data.get("previous_hash", "0"),
            block_data.get("difficulty", 4),
        )
        block.timestamp = block_data.get("timestamp", time.time())
        block.nonce = block_data.get("nonce", 0)
        block.hash = block_data.get("hash")
        block.merkle_root = block_data.get("merkle_root", block.calculate_merkle_root())
        return block

    @classmethod
    def deserialize_chain(cls, chain_data: List[Dict[str, Any]]) -> List[Block]:
        return [cls.deserialize_block(bd) for bd in chain_data]

    def _load_from_disk(self) -> bool:
        """Load the blockchain state from disk (blocks, UTXO set, pending transactions)."""
        loaded_state = self.storage.load_state_from_disk()
        self.utxo_manager.load_utxo_set(loaded_state.get("utxo_set", {}))
        self.pending_transactions = loaded_state.get("pending_transactions", [])
        self.contracts = loaded_state.get("contracts", {})
        self.contract_receipts = loaded_state.get("receipts", [])

        self.chain = self.storage.load_chain_from_disk()
        if not self.chain:
            return False

        print(f"Loaded {len(self.chain)} blocks from disk.")
        return True

    def _rebuild_governance_state_from_chain(self) -> None:
        """Reconstruct governance state by replaying governance transactions."""
        mining_start = self.chain[0].timestamp if self.chain else time.time()
        self.governance_state = GovernanceState(mining_start_time=mining_start)

        for block in self.chain:
            self._process_governance_block_transactions(block)

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
        }

    def _rebuild_contract_state(self) -> None:
        if not self.smart_contract_manager:
            return
        self.contracts.clear()
        self.contract_receipts.clear()
        for block in self.chain:
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
            print(f"Loading genesis block from {genesis_file}")
            with open(genesis_file, "r") as f:
                genesis_data = json.load(f)

            # Recreate ALL genesis transactions
            genesis_transactions = []
            for tx_data in genesis_data["transactions"]:
                genesis_tx = Transaction(
                    tx_data["sender"], tx_data["recipient"], tx_data["amount"], tx_data["fee"]
                )
                genesis_tx.timestamp = tx_data["timestamp"]
                genesis_tx.txid = tx_data["txid"]
                genesis_tx.signature = tx_data["signature"]
                genesis_transactions.append(genesis_tx)

            print(
                f"Loaded {len(genesis_transactions)} genesis transactions (Total: {sum(tx.amount for tx in genesis_transactions)} AXN)"
            )

            # Create genesis block with pre-defined values
            genesis_block = Block(0, genesis_transactions, "0", self.difficulty)
            genesis_block.timestamp = genesis_data["timestamp"]
            genesis_block.nonce = genesis_data["nonce"]
            genesis_block.merkle_root = genesis_data["merkle_root"]
            genesis_block.hash = genesis_data["hash"]

            # Mine it to get proper PoW hash
            print("Mining unified genesis block...")
            genesis_block.hash = genesis_block.mine_block()

            print(f"Genesis block loaded: {genesis_block.hash}")
        else:
            print("Creating new genesis block...")
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

            genesis_block = Block(0, genesis_transactions, "0", self.difficulty)
            genesis_block.hash = genesis_block.mine_block()

        self.chain.append(genesis_block)
        for tx in genesis_block.transactions:
            self.utxo_manager.process_transaction_outputs(tx)
        self.storage._save_block_to_disk(genesis_block)  # Save genesis block to its file
        self.storage.save_state_to_disk(
            self.utxo_manager, self.pending_transactions
        )  # Save UTXO and pending TXs

    def get_latest_block(self) -> Block:
        """Get the last block in the chain by loading it from disk."""
        latest_block = self.storage.get_latest_block_from_disk()
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
        """
        # Get UTXOs for sender
        sender_utxos = self.utxo_manager.get_utxos_for_address(sender_address)

        # Calculate total needed (amount + fee)
        total_needed = amount + fee

        # Select UTXOs to cover the amount (simple greedy algorithm)
        selected_utxos = []
        selected_amount = 0.0

        for utxo in sender_utxos:
            selected_utxos.append(utxo)
            selected_amount += utxo["amount"]
            if selected_amount >= total_needed:
                break

        # Check if we have enough funds
        if selected_amount < total_needed:
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

    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pending pool after validation"""
        # Check if transaction is None (can happen if create_transaction fails)
        if transaction is None:
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

        # Validate transaction
        if not self.transaction_validator.validate_transaction(transaction):
            return False

        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Optional[Block]:
        """Mine a new block with pending transactions"""
        # Calculate block reward based on current chain height (with halving)
        block_height = len(self.chain)
        base_reward = self.get_block_reward(block_height)

        # Update miner streak and apply bonus
        self.streak_tracker.update_miner_streak(miner_address, time.time())
        final_reward, streak_bonus = self.streak_tracker.apply_streak_bonus(
            miner_address, base_reward
        )

        # Create coinbase transaction (block reward + transaction fees + streak bonus)
        total_fees = sum(tx.fee for tx in self.pending_transactions)
        coinbase_reward = final_reward + total_fees

        coinbase_tx = Transaction(
            "COINBASE",
            miner_address,
            coinbase_reward,
            outputs=[{"address": miner_address, "amount": coinbase_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create new block
        block_transactions = [coinbase_tx] + self.pending_transactions
        new_block = Block(
            len(self.chain), block_transactions, self.get_latest_block().hash, self.difficulty
        )

        # Mine the block
        new_block.hash = new_block.mine_block()

        if self.smart_contract_manager:
            receipts = self.smart_contract_manager.process_block(new_block)
            if receipts:
                self.contract_receipts.extend(receipts)

        # Add to chain (cache)
        self.chain.append(new_block)
        self._process_governance_block_transactions(new_block)
        self.storage._save_block_to_disk(new_block)

        # Update UTXO set
        for tx in new_block.transactions:
            if tx.sender != "COINBASE":  # Regular transactions spend inputs
                self.utxo_manager.process_transaction_inputs(tx)
            self.utxo_manager.process_transaction_outputs(tx)

        # Process gamification features for this block
        self._process_gamification_features(new_block, miner_address)

        # Clear pending transactions
        self.pending_transactions = []

        # Log streak bonus if applied
        if streak_bonus > 0:
            print(
                f"STREAK BONUS: +{streak_bonus:.4f} AXN ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)"
            )

        self.storage.save_state_to_disk(
            self.utxo_manager,
            self.pending_transactions,
            self.contracts,
            self.contract_receipts,
        )
        return new_block

    def _process_gamification_features(self, block: Block, miner_address: str) -> None:
        """Process all gamification features after mining a block"""
        block_height = block.index

        # 1. Check for airdrop (every 100th block)
        if self.airdrop_manager.should_trigger_airdrop(block_height):
            airdrop_amounts = self.airdrop_manager.execute_airdrop(block_height, block.hash, self)
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
        unlockable_capsules = self.timecapsule_manager.get_unlockable_capsules()
        for capsule in unlockable_capsules:
            # Create time capsule release transaction
            capsule_tx = Transaction(
                capsule["sender"], capsule["recipient"], capsule["amount"], tx_type="timecapsule"
            )
            capsule_tx.txid = capsule_tx.calculate_hash()
            self.timecapsule_manager.release_capsule(capsule["id"], capsule_tx.txid)
            self.pending_transactions.append(capsule_tx)

    def get_balance(self, address: str) -> float:
        """Get balance of an address"""
        return self.utxo_manager.get_balance(address)

    @property
    def utxo_set(self) -> Dict[str, List[Dict[str, Any]]]:
        """Expose UTXO set for tests and external access"""
        return self.utxo_manager.utxo_set

    def get_circulating_supply(self) -> float:
        """Calculate current circulating supply of AXN tokens"""
        # Sum all unspent UTXOs (all coins currently in circulation)
        total = 0.0
        for address, utxos in self.utxo_manager.utxo_set.items():
            for utxo in utxos:
                # Only count unspent UTXOs
                if not utxo.get("spent", False):
                    total += utxo.get("amount", 0.0)
        return total

    def get_total_supply(self) -> float:
        """Get total supply (same as circulating supply for now)"""
        return self.get_circulating_supply()

    def add_block(self, block: Block) -> bool:
        """
        Add a block received from a peer to the blockchain.
        Handles chain reorganization if the incoming block is part of a longer valid chain.

        Args:
            block: Block to add to the chain

        Returns:
            True if block was added successfully, False otherwise
        """
        # Validate the block before adding
        if not block or not hasattr(block, 'hash'):
            return False

        # Check if we already have this block at this index with the same hash
        if len(self.chain) > block.index and self.chain[block.index].hash == block.hash:
            return True  # Already have this exact block

        # Verify proof of work
        if not block.hash.startswith("0" * block.difficulty):
            return False

        # Verify block hash is correct
        if block.hash != block.calculate_hash():
            return False

        # Verify transactions
        for tx in block.transactions:
            if tx.sender not in ["COINBASE", "SYSTEM", "AIRDROP"]:
                if hasattr(tx, 'verify_signature') and not tx.verify_signature():
                    return False

        # Case 1: Block extends our current chain directly
        if block.index == len(self.chain):
            if len(self.chain) > 0 and block.previous_hash != self.chain[-1].hash:
                # Block doesn't link to our chain tip - might be from a competing fork
                # Store it as an orphan block
                if block.index not in self.orphan_blocks:
                    self.orphan_blocks[block.index] = []
                self.orphan_blocks[block.index].append(block)
                # Check if orphans now form a longer chain
                self._check_orphan_chains_for_reorg()
                return False

            return self._add_block_to_chain(block)

        # Case 2: Block is beyond our current chain (potential reorganization)
        if block.index > len(self.chain):
            # Store as orphan - we're missing intermediate blocks
            if block.index not in self.orphan_blocks:
                self.orphan_blocks[block.index] = []
            self.orphan_blocks[block.index].append(block)
            # Check if orphans now form a longer chain
            self._check_orphan_chains_for_reorg()
            return False

        # Case 3: Block conflicts with our chain (fork/reorganization scenario)
        # The block is at an index we already have, but with a different hash
        if block.index < len(self.chain) and self.chain[block.index].hash != block.hash:
            # Check if this block links to a previous block in our chain
            if block.index > 0 and block.index - 1 < len(self.chain):
                if block.previous_hash == self.chain[block.index - 1].hash:
                    # This is a valid fork from our chain
                    # Try to build a longer chain from this fork point
                    return self._handle_fork(block)

            # Block doesn't connect to our immediate parent, but might be part
            # of a competing fork. Store as orphan and check for reorganization.
            if block.index not in self.orphan_blocks:
                self.orphan_blocks[block.index] = []
            self.orphan_blocks[block.index].append(block)
            self._check_orphan_chains_for_reorg()
            return False

        return False

    def _handle_fork(self, fork_block: Block) -> bool:
        """
        Handle a forking block by attempting to build a longer chain.

        Args:
            fork_block: The block that creates a fork from our current chain

        Returns:
            True if reorganization occurred, False otherwise
        """
        # Build a candidate chain starting from the fork point
        fork_point = fork_block.index - 1
        candidate_chain = self.chain[:fork_point + 1].copy()
        candidate_chain.append(fork_block)

        # Try to extend with orphan blocks
        current_index = fork_block.index + 1
        while current_index in self.orphan_blocks:
            added = False
            for orphan in self.orphan_blocks[current_index]:
                if orphan.previous_hash == candidate_chain[-1].hash:
                    candidate_chain.append(orphan)
                    added = True
                    break
            if not added:
                break
            current_index += 1

        # Only reorganize if the candidate chain is longer
        if len(candidate_chain) > len(self.chain):
            return self.replace_chain(candidate_chain)

        # Store fork block as orphan for potential future reorganization
        if fork_block.index not in self.orphan_blocks:
            self.orphan_blocks[fork_block.index] = []
        self.orphan_blocks[fork_block.index].append(fork_block)

        # Check if orphans now form a longer chain (this might happen
        # if we just received a block that completes a competing fork)
        self._check_orphan_chains_for_reorg()

        return False

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

        # Check if any orphan blocks can now be connected
        self._process_orphan_blocks()

        return True

    def _process_orphan_blocks(self):
        """Try to connect any orphan blocks to the chain."""
        next_index = len(self.chain)

        # Keep trying to add orphan blocks as long as we find matches
        while next_index in self.orphan_blocks:
            added = False
            for orphan in self.orphan_blocks[next_index]:
                if orphan.previous_hash == self.chain[-1].hash:
                    # This orphan can now be connected
                    self.chain.append(orphan)
                    self._process_governance_block_transactions(orphan)

                    # Update UTXO set
                    for tx in orphan.transactions:
                        if tx.sender != "COINBASE":
                            self.utxo_manager.process_transaction_inputs(tx)
                        self.utxo_manager.process_transaction_outputs(tx)

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

    def _check_orphan_chains_for_reorg(self) -> bool:
        """
        Check if orphan blocks can form a longer valid chain than the current chain.
        This handles the case where blocks from a competing fork arrive sequentially.

        Returns:
            True if reorganization occurred, False otherwise
        """
        if not self.orphan_blocks:
            return False

        best_candidate = None
        best_length = 0

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
                    if potential_fork_block.previous_hash != expected_prev_hash:
                        continue

                # Build candidate chain from this fork point
                candidate_chain = self.chain[:fork_point_index + 1].copy()
                candidate_chain.append(potential_fork_block)

                # Try to extend with more orphans
                current_index = start_index + 1
                while current_index in self.orphan_blocks:
                    added = False
                    for orphan in self.orphan_blocks[current_index]:
                        if orphan.previous_hash == candidate_chain[-1].hash:
                            candidate_chain.append(orphan)
                            added = True
                            break
                    if not added:
                        break
                    current_index += 1

                # Check if this candidate is the longest we've found and at least as long as current chain
                if len(candidate_chain) >= len(self.chain) and len(candidate_chain) > best_length:
                    # Validate the candidate chain
                    if self._validate_chain_structure(candidate_chain):
                        best_candidate = candidate_chain
                        best_length = len(candidate_chain)

        # If we found a longer or equal valid chain, reorganize to it
        # Equal-length reorganization allows accepting competing chains that arrive together
        if best_candidate and len(best_candidate) >= len(self.chain):
            return self.replace_chain(best_candidate)

        return False

    # ==================== TRADE MANAGEMENT ====================

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
        """Normalize order payload and dispatch to the trade manager."""
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
        price_value = float(price) if price is not None else (amount_requested / amount_offered)

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

    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Replace the current chain with a new chain if it's longer and valid.
        This enables chain reorganization when a longer valid chain is discovered.

        Args:
            new_chain: The new chain to replace the current one

        Returns:
            True if chain was replaced, False otherwise
        """
        # Chain must be at least as long to replace (equal length allowed for fork resolution)
        if len(new_chain) < len(self.chain):
            return False

        # Validate the new chain
        if not self._validate_chain_structure(new_chain):
            return False

        # Backup current state
        old_chain = self.chain.copy()
        old_utxo_set = self.utxo_manager.get_utxo_set().copy()

        try:
            # Reset UTXO set
            self.utxo_manager = UTXOManager()

            # Rebuild UTXO set from new chain
            for block in new_chain:
                for tx in block.transactions:
                    if tx.sender != "COINBASE":
                        self.utxo_manager.process_transaction_inputs(tx)
                    self.utxo_manager.process_transaction_outputs(tx)

            # Replace chain
            self.chain = new_chain
            if self.smart_contract_manager:
                self._rebuild_contract_state()
            self._rebuild_governance_state_from_chain()
            self.sync_smart_contract_vm()

            # Save new chain to disk
            for i, block in enumerate(new_chain):
                self.storage._save_block_to_disk(block)

            self.storage.save_state_to_disk(
                self.utxo_manager,
                self.pending_transactions,
                self.contracts,
                self.contract_receipts,
            )

            # Clean up orphan blocks that are now part of the main chain
            # Keep track of block hashes in the new chain
            new_chain_hashes = {block.hash for block in new_chain}

            # Remove orphans that are now in the main chain
            indices_to_remove = []
            for index, orphan_list in self.orphan_blocks.items():
                orphans_to_keep = [
                    orphan for orphan in orphan_list
                    if orphan.hash not in new_chain_hashes
                ]
                if orphans_to_keep:
                    self.orphan_blocks[index] = orphans_to_keep
                else:
                    indices_to_remove.append(index)

            # Remove empty orphan lists
            for index in indices_to_remove:
                del self.orphan_blocks[index]

            print(f"Chain reorganized: {len(old_chain)} -> {len(new_chain)} blocks")
            return True

        except Exception as e:
            # Rollback on failure
            print(f"Chain replacement failed: {e}")
            self.chain = old_chain
            self.utxo_manager.load_utxo_set(old_utxo_set)
            return False

    def _validate_chain_structure(self, chain: List[Block]) -> bool:
        """
        Validate the structure of a chain without modifying state.

        Args:
            chain: The chain to validate

        Returns:
            True if chain is valid, False otherwise
        """
        if not chain:
            return False

        # Check genesis block
        if chain[0].index != 0:
            return False

        # Validate each block
        for i in range(len(chain)):
            block = chain[i]

            # Verify index
            if block.index != i:
                return False

            # Verify proof of work
            if not block.hash.startswith("0" * block.difficulty):
                return False

            # Verify hash
            if block.hash != block.calculate_hash():
                return False

            # Verify previous hash (except genesis)
            if i > 0:
                if block.previous_hash != chain[i - 1].hash:
                    return False

            # Verify transactions
            for tx in block.transactions:
                if tx.sender not in ["COINBASE", "SYSTEM", "AIRDROP"]:
                    if hasattr(tx, 'verify_signature') and not tx.verify_signature():
                        return False

        return True

    def validate_chain(self) -> bool:
        """Validate entire blockchain by loading blocks from disk."""
        block_files = sorted(
            [
                f
                for f in os.listdir(self.storage.blocks_dir)
                if f.startswith("block_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        if not block_files:
            return False  # No blocks to validate

        # Load genesis block separately
        previous_block = self.storage._load_block_from_disk(0)
        if not previous_block:
            print("Failed to load genesis block for validation.")
            return False

        for i in range(1, len(block_files)):
            current_block = self.storage._load_block_from_disk(i)
            if not current_block:
                print(f"Failed to load block {i} for validation.")
                return False

            # Verify hash
            if current_block.hash != current_block.calculate_hash():
                print(f"Block {i} has invalid hash")
                return False

            # Verify previous hash
            if current_block.previous_hash != previous_block.hash:
                print(f"Block {i} has invalid previous hash")
                return False

            # Verify proof of work
            if not current_block.hash.startswith("0" * current_block.difficulty):
                print(f"Block {i} doesn't meet difficulty requirement")
                return False

            # Verify all transactions (simplified for now, full validation would require UTXO tracking)
            # For now, just check transaction signatures if applicable
            for tx in current_block.transactions:
                if tx.sender != "COINBASE" and not tx.verify_signature():
                    print(f"Block {i} has invalid transaction signature")
                    return False

            previous_block = current_block
        return True

    def get_transaction_history(self, address: str) -> List[Dict[str, Any]]:
        """Get all transactions involving an address by iterating through blocks on disk."""
        history = []
        block_files = sorted(
            [
                f
                for f in os.listdir(self.storage.blocks_dir)
                if f.startswith("block_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        for block_file in block_files:
            block_index = int(block_file.split("_")[1].split(".")[0])
            block = self.storage._load_block_from_disk(block_index)
            if block:
                for tx in block.transactions:
                    if tx.sender == address or tx.recipient == address:
                        history.append(
                            {
                                "block": block.index,
                                "txid": tx.txid,
                                "sender": tx.sender,
                                "recipient": tx.recipient,
                                "amount": tx.amount,
                                "fee": tx.fee,
                                "timestamp": tx.timestamp,
                                "type": "sent" if tx.sender == address else "received",
                            }
                        )
        return history

    def get_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics."""
        block_files = [
            f
            for f in os.listdir(self.storage.blocks_dir)
            if f.startswith("block_") and f.endswith(".json")
        ]
        num_blocks = len(block_files)

        total_transactions = 0
        # This is inefficient, but for stats, we might need to iterate through blocks
        # A more optimized solution would cache this or store it separately
        for i in range(num_blocks):
            block = self.storage._load_block_from_disk(i)
            if block:
                total_transactions += len(block.transactions)

        total_supply = self.utxo_manager.get_total_unspent_value()

        return {
            "blocks": num_blocks,
            "total_transactions": total_transactions,
            "pending_transactions": len(self.pending_transactions),
            "difficulty": self.difficulty,
            "total_supply": total_supply,
            "unique_addresses": self.utxo_manager.get_unique_addresses_count(),
            "latest_block_hash": self.get_latest_block().hash,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export entire blockchain by loading blocks from disk."""
        block_files = sorted(
            [
                f
                for f in os.listdir(self.storage.blocks_dir)
                if f.startswith("block_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        chain_data = []
        for block_file in block_files:
            block_index = int(block_file.split("_")[1].split(".")[0])
            block = self.storage._load_block_from_disk(block_index)
            if block:
                chain_data.append(block.to_dict())

        pending_tx_data = [tx.to_dict() for tx in self.pending_transactions]

        return {
            "chain": chain_data,
            "pending_transactions": pending_tx_data,
            "difficulty": self.difficulty,
            "stats": self.get_stats(),
        }

    def submit_governance_proposal(
        self,
        submitter: str,
        title: str,
        description: str,
        proposal_type: str,
        proposal_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Submit a governance proposal on-chain.

        Args:
            submitter: Address submitting the proposal
            title: Proposal title
            description: Detailed description
            proposal_type: Type of proposal (ai_improvement, parameter_change, etc.)
            proposal_data: Additional proposal data

        Returns:
            dict with proposal_id, txid, and status
        """
        import hashlib
        import time

        # Generate proposal ID
        proposal_id = hashlib.sha256(f"{submitter}{title}{time.time()}".encode()).hexdigest()[:16]

        # Create a transaction to record the proposal
        tx_data = {
            "type": "governance_proposal",
            "proposal_id": proposal_id,
            "submitter": submitter,
            "title": title,
            "description": description,
            "proposal_type": proposal_type,
            "proposal_data": proposal_data,
            "proposal_payload": proposal_data,
            "timestamp": time.time(),
        }

        # Create transaction
        tx = Transaction(submitter, "GOVERNANCE", 0.0, fee=0.1)
        tx.metadata = tx_data
        tx.txid = tx.calculate_hash()

        # Add to pending transactions
        self.pending_transactions.append(tx)

        return {"proposal_id": proposal_id, "txid": tx.txid, "status": "pending"}

    def cast_governance_vote(
        self, voter: str, proposal_id: str, vote: str, voting_power: float
    ) -> Dict[str, Any]:
        """
        Cast a vote on a governance proposal.

        Args:
            voter: Address casting the vote
            proposal_id: ID of the proposal
            vote: Vote choice (yes/no/abstain)
            voting_power: Voting power of the voter

        Returns:
            dict with vote confirmation
        """
        import time

        # Create vote transaction
        tx_data = {
            "type": "governance_vote",
            "proposal_id": proposal_id,
            "voter": voter,
            "vote": vote,
            "voting_power": voting_power,
            "timestamp": time.time(),
        }

        tx = Transaction(voter, "GOVERNANCE", 0.0, fee=0.05)
        tx.metadata = tx_data
        tx.txid = tx.calculate_hash()

        # Add to pending transactions
        self.pending_transactions.append(tx)

        # Count existing votes (simplified)
        vote_count = sum(
            1
            for t in self.pending_transactions
            if hasattr(t, "metadata")
            and t.metadata.get("type") == "governance_vote"
            and t.metadata.get("proposal_id") == proposal_id
        )

        return {"txid": tx.txid, "status": "recorded", "vote_count": vote_count}

    def submit_code_review(
        self, reviewer: str, proposal_id: str, review_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit a code review for a governance proposal.

        Args:
            reviewer: Address of the code reviewer
            proposal_id: ID of the proposal being reviewed
            review_data: Review details

        Returns:
            dict with review confirmation
        """
        import time

        # Create review transaction
        tx_data = {
            "type": "code_review",
            "proposal_id": proposal_id,
            "reviewer": reviewer,
            **review_data,
            "timestamp": time.time(),
        }

        tx = Transaction(reviewer, "GOVERNANCE", 0.0, fee=0.05)
        tx.metadata = tx_data
        tx.txid = tx.calculate_hash()

        # Add to pending transactions
        self.pending_transactions.append(tx)

        return {"txid": tx.txid, "status": "submitted", "proposal_id": proposal_id}

    def vote_implementation(
        self, voter: str, proposal_id: str, approved: bool, voting_power: float = 0.0
    ) -> Dict[str, Any]:
        """
        Vote on implementation readiness for a proposal.
        """
        import time

        tx_data = {
            "type": "implementation_vote",
            "proposal_id": proposal_id,
            "voter": voter,
            "approved": approved,
            "voting_power": voting_power,
            "timestamp": time.time(),
        }

        tx = Transaction(voter, "GOVERNANCE", 0.0, fee=0.05)
        tx.metadata = tx_data
        tx.txid = tx.calculate_hash()

        self.pending_transactions.append(tx)

        return {"txid": tx.txid, "status": "submitted", "proposal_id": proposal_id}

    def execute_proposal(self, executor: str, proposal_id: str) -> Dict[str, Any]:
        """
        Execute an approved governance proposal.

        Args:
            executor: Address executing the proposal
            proposal_id: ID of the proposal to execute

        Returns:
            dict with execution status
        """
        import time

        # Check if proposal has enough votes (simplified validation)
        proposal_votes = [
            t
            for t in self.pending_transactions
            if hasattr(t, "metadata")
            and t.metadata.get("type") == "governance_vote"
            and t.metadata.get("proposal_id") == proposal_id
        ]

        total_voters = len(set(t.metadata.get("voter") for t in proposal_votes))

        governance_rules = self.governance_state
        min_voters_required = governance_rules.min_voters if governance_rules else 250
        required_percent = governance_rules.approval_percent if governance_rules else 66

        yes_power = sum(
            float(t.metadata.get("voting_power", 0)) for t in proposal_votes if t.metadata.get("vote") == "yes"
        )
        total_power = sum(float(t.metadata.get("voting_power", 0)) for t in proposal_votes)
        approval_pct = (yes_power / total_power * 100) if total_power > 0 else 0

        # Require at least min voters (configurable) and approval percentage
        if total_voters < min_voters_required:
            return {
                "success": False,
                "error": f"Insufficient voters. Need {min_voters_required}+, got {total_voters}",
                "proposal_id": proposal_id,
            }

        if approval_pct < required_percent:
            return {
                "success": False,
                "error": f"Approval percent too low. Need {required_percent}%+, got {approval_pct:.1f}%",
                "proposal_id": proposal_id,
            }

        proposal_payload = self._find_pending_proposal_payload(proposal_id)

        # Create execution transaction
        tx_data = {
            "type": "proposal_execution",
            "proposal_id": proposal_id,
            "executor": executor,
            "voters": total_voters,
            "timestamp": time.time(),
            "proposal_payload": proposal_payload,
        }

        tx = Transaction(executor, "GOVERNANCE", 0.0, fee=0.1)
        tx.metadata = tx_data
        tx.txid = tx.calculate_hash()

        # Add to pending transactions
        self.pending_transactions.append(tx)

        return {
            "success": True,
            "txid": tx.txid,
            "proposal_id": proposal_id,
            "voters": total_voters,
        }
