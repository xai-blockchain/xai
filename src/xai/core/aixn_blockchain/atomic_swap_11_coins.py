"""
XAI Atomic Swap Protocol
HTLC-based atomic swaps for cross-chain trading
Free market pricing - no restrictions
"""

import hashlib
import json
import os
import time
from typing import Dict, Optional, Tuple, List
from enum import Enum
import secrets
import threading


class CoinType(Enum):
    """Supported coins for atomic swaps"""

    BTC = "Bitcoin"
    ETH = "Ethereum"
    LTC = "Litecoin"
    DOGE = "Dogecoin"
    XMR = "Monero"
    BCH = "BitcoinCash"
    USDT = "Tether"
    ZEC = "Zcash"
    DASH = "Dash"
    USDC = "USDCoin"
    DAI = "Dai"


class SwapProtocol(Enum):
    """Different protocols for different coin types"""

    HTLC_UTXO = "htlc_utxo"
    HTLC_ETHEREUM = "htlc_ethereum"
    HTLC_MONERO = "htlc_monero"


class SwapState(Enum):
    """States in the atomic swap lifecycle"""

    INITIATED = "initiated"  # Swap contract created
    FUNDED = "funded"  # Funds locked in contract
    COUNTERPARTY_FUNDED = "counterparty_funded"  # Both sides funded
    CLAIMED = "claimed"  # Secret revealed and claimed
    REFUNDED = "refunded"  # Timelock expired, funds returned
    EXPIRED = "expired"  # Contract expired without claim
    FAILED = "failed"  # Swap failed for other reasons


class SwapEvent(Enum):
    """Events that trigger state transitions"""

    CREATE = "create"
    FUND = "fund"
    COUNTERPARTY_FUND = "counterparty_fund"
    REVEAL_SECRET = "reveal_secret"
    CLAIM = "claim"
    REFUND = "refund"
    EXPIRE = "expire"
    FAIL = "fail"


# Map coins to their protocols
COIN_PROTOCOLS = {
    CoinType.BTC: SwapProtocol.HTLC_UTXO,
    CoinType.LTC: SwapProtocol.HTLC_UTXO,
    CoinType.DOGE: SwapProtocol.HTLC_UTXO,
    CoinType.BCH: SwapProtocol.HTLC_UTXO,
    CoinType.ZEC: SwapProtocol.HTLC_UTXO,
    CoinType.DASH: SwapProtocol.HTLC_UTXO,
    CoinType.ETH: SwapProtocol.HTLC_ETHEREUM,
    CoinType.USDT: SwapProtocol.HTLC_ETHEREUM,
    CoinType.USDC: SwapProtocol.HTLC_ETHEREUM,
    CoinType.DAI: SwapProtocol.HTLC_ETHEREUM,
    CoinType.XMR: SwapProtocol.HTLC_MONERO,
}


class SwapStateMachine:
    """
    State machine for atomic swap lifecycle management.
    Handles state transitions, persistence, and recovery.
    """

    # Valid state transitions
    STATE_TRANSITIONS = {
        SwapState.INITIATED: [SwapState.FUNDED, SwapState.FAILED, SwapState.EXPIRED],
        SwapState.FUNDED: [
            SwapState.COUNTERPARTY_FUNDED,
            SwapState.REFUNDED,
            SwapState.EXPIRED,
            SwapState.FAILED,
        ],
        SwapState.COUNTERPARTY_FUNDED: [
            SwapState.CLAIMED,
            SwapState.REFUNDED,
            SwapState.EXPIRED,
        ],
        SwapState.CLAIMED: [],  # Terminal state
        SwapState.REFUNDED: [],  # Terminal state
        SwapState.EXPIRED: [],  # Terminal state
        SwapState.FAILED: [],  # Terminal state
    }

    def __init__(self, storage_dir: str = "data/swaps"):
        """
        Initialize the swap state machine

        Args:
            storage_dir: Directory for persisting swap state
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        # In-memory swap state tracking
        self.swaps: Dict[str, Dict] = {}
        self.lock = threading.RLock()

        # Load existing swaps from storage
        self._load_swaps()

    def create_swap(self, swap_id: str, swap_data: Dict) -> bool:
        """
        Create a new swap in INITIATED state

        Args:
            swap_id: Unique identifier for the swap
            swap_data: Swap contract data

        Returns:
            True if successful
        """
        with self.lock:
            if swap_id in self.swaps:
                return False

            self.swaps[swap_id] = {
                "state": SwapState.INITIATED,
                "data": swap_data,
                "created_at": time.time(),
                "updated_at": time.time(),
                "history": [
                    {
                        "state": SwapState.INITIATED.value,
                        "timestamp": time.time(),
                        "event": SwapEvent.CREATE.value,
                    }
                ],
            }

            self._persist_swap(swap_id)
            return True

    def transition(
        self, swap_id: str, new_state: SwapState, event: SwapEvent, data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Transition a swap to a new state

        Args:
            swap_id: Swap identifier
            new_state: Target state
            event: Event triggering transition
            data: Additional data for the transition

        Returns:
            tuple: (success, message)
        """
        with self.lock:
            if swap_id not in self.swaps:
                return False, f"Swap {swap_id} not found"

            swap = self.swaps[swap_id]
            current_state = swap["state"]

            # Check if transition is valid
            if new_state not in self.STATE_TRANSITIONS.get(current_state, []):
                return (
                    False,
                    f"Invalid transition from {current_state.value} to {new_state.value}",
                )

            # Update state
            swap["state"] = new_state
            swap["updated_at"] = time.time()

            # Record in history
            history_entry = {
                "state": new_state.value,
                "timestamp": time.time(),
                "event": event.value,
            }
            if data:
                history_entry["data"] = data

            swap["history"].append(history_entry)

            # Persist changes
            self._persist_swap(swap_id)

            return True, f"Transitioned to {new_state.value}"

    def get_swap(self, swap_id: str) -> Optional[Dict]:
        """Get swap data by ID"""
        with self.lock:
            return self.swaps.get(swap_id)

    def get_swap_state(self, swap_id: str) -> Optional[SwapState]:
        """Get current state of a swap"""
        with self.lock:
            swap = self.swaps.get(swap_id)
            return swap["state"] if swap else None

    def is_terminal_state(self, swap_id: str) -> bool:
        """Check if swap is in a terminal state"""
        state = self.get_swap_state(swap_id)
        if not state:
            return False

        return state in [
            SwapState.CLAIMED,
            SwapState.REFUNDED,
            SwapState.EXPIRED,
            SwapState.FAILED,
        ]

    def get_active_swaps(self) -> Dict[str, Dict]:
        """Get all non-terminal swaps"""
        with self.lock:
            return {
                swap_id: swap
                for swap_id, swap in self.swaps.items()
                if not self.is_terminal_state(swap_id)
            }

    def check_timeouts(self) -> List[str]:
        """
        Check for swaps that have exceeded their timelock and should be refunded

        Returns:
            List of swap IDs that can be refunded
        """
        refundable = []
        current_time = time.time()

        with self.lock:
            for swap_id, swap in self.swaps.items():
                if self.is_terminal_state(swap_id):
                    continue

                timelock = swap["data"].get("timelock", 0)
                if current_time >= timelock:
                    state = swap["state"]
                    if state in [SwapState.FUNDED, SwapState.COUNTERPARTY_FUNDED]:
                        refundable.append(swap_id)

        return refundable

    def _persist_swap(self, swap_id: str) -> None:
        """Persist swap state to disk"""
        try:
            swap = self.swaps[swap_id]
            file_path = os.path.join(self.storage_dir, f"{swap_id}.json")

            # Convert enums to strings for JSON serialization
            serializable_swap = {
                "state": swap["state"].value,
                "data": swap["data"],
                "created_at": swap["created_at"],
                "updated_at": swap["updated_at"],
                "history": swap["history"],
            }

            with open(file_path, "w") as f:
                json.dump(serializable_swap, f, indent=2)

        except Exception as e:
            print(f"Error persisting swap {swap_id}: {e}")

    def _load_swaps(self) -> None:
        """Load all swaps from storage"""
        if not os.path.exists(self.storage_dir):
            return

        try:
            for filename in os.listdir(self.storage_dir):
                if not filename.endswith(".json"):
                    continue

                swap_id = filename[:-5]  # Remove .json extension
                file_path = os.path.join(self.storage_dir, filename)

                with open(file_path, "r") as f:
                    swap_data = json.load(f)

                # Convert state string back to enum
                swap_data["state"] = SwapState(swap_data["state"])

                self.swaps[swap_id] = swap_data

        except Exception as e:
            print(f"Error loading swaps: {e}")

    def get_swap_history(self, swap_id: str) -> List[Dict]:
        """Get complete history of state transitions for a swap"""
        with self.lock:
            swap = self.swaps.get(swap_id)
            return swap["history"] if swap else []


class AtomicSwapHTLC:
    """
    Hash Time Locked Contract for Atomic Swaps
    """

    def __init__(self, coin_type: CoinType):
        self.coin_type = coin_type
        self.protocol = COIN_PROTOCOLS[coin_type]

    def create_swap_contract(
        self,
        axn_amount: float,
        other_coin_amount: float,
        counterparty_address: str,
        timelock_hours: int = 24,
    ) -> Dict:
        """
        Create a new atomic swap contract

        Args:
            axn_amount: Amount of XAI to swap
            other_coin_amount: Amount of other coin to receive
            counterparty_address: Address of trading partner
            timelock_hours: Hours until refund becomes available

        Returns:
            dict: Swap contract details
        """

        # Generate secret for HTLC
        secret = secrets.token_bytes(32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Calculate timelock (Unix timestamp)
        timelock = int(time.time()) + (timelock_hours * 3600)

        # Create contract based on protocol
        if self.protocol == SwapProtocol.HTLC_UTXO:
            contract = self._create_utxo_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )
        elif self.protocol == SwapProtocol.HTLC_ETHEREUM:
            contract = self._create_ethereum_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )
        elif self.protocol == SwapProtocol.HTLC_MONERO:
            contract = self._create_monero_htlc(
                secret_hash, timelock, counterparty_address, other_coin_amount
            )

        contract.update(
            {
                "success": True,
                "secret": secret.hex(),  # Sender keeps this secret
                "secret_hash": secret_hash,
                "axn_amount": axn_amount,
                "other_coin": self.coin_type.name,
                "other_coin_amount": other_coin_amount,
                "timelock": timelock,
                "timelock_hours": timelock_hours,
            }
        )

        return contract

    def _create_utxo_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for UTXO-based coins
        (BTC, LTC, DOGE, BCH, ZEC, DASH)

        Bitcoin Script pseudocode:
        OP_IF
            OP_SHA256 <secret_hash> OP_EQUALVERIFY
            <recipient_pubkey> OP_CHECKSIG
        OP_ELSE
            <timelock> OP_CHECKLOCKTIMEVERIFY OP_DROP
            <sender_pubkey> OP_CHECKSIG
        OP_ENDIF
        """

        return {
            "contract_type": "HTLC_UTXO",
            "script_template": f"""
                OP_IF
                    OP_SHA256 {secret_hash} OP_EQUALVERIFY
                    {recipient} OP_CHECKSIG
                OP_ELSE
                    {timelock} OP_CHECKLOCKTIMEVERIFY OP_DROP
                    <sender_address> OP_CHECKSIG
                OP_ENDIF
            """,
            "claim_method": "Reveal secret to claim",
            "refund_method": f"Wait until {timelock} then claim refund",
            "supported_coins": ["BTC", "LTC", "DOGE", "BCH", "ZEC", "DASH"],
        }

    def _create_ethereum_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for Ethereum-based tokens
        (ETH, USDT, USDC, DAI)

        Solidity smart contract required
        """

        solidity_contract = f"""
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;

        contract AtomicSwapETH {{
            bytes32 public secretHash = 0x{secret_hash};
            address public recipient = {recipient};
            uint256 public timelock = {timelock};
            uint256 public amount = {amount} ether;

            function claim(bytes32 secret) external {{
                require(sha256(abi.encodePacked(secret)) == secretHash, "Invalid secret");
                require(msg.sender == recipient, "Not recipient");
                payable(recipient).transfer(amount);
            }}

            function refund() external {{
                require(block.timestamp >= timelock, "Timelock not expired");
                payable(msg.sender).transfer(amount);
            }}
        }}
        """

        return {
            "contract_type": "HTLC_ETHEREUM",
            "smart_contract": solidity_contract,
            "claim_method": "Call claim(secret) function",
            "refund_method": f"Call refund() after {timelock}",
            "supported_tokens": ["ETH", "USDT", "USDC", "DAI"],
            "gas_estimate": "~150,000 gas for claim, ~50,000 for refund",
        }

    def _create_monero_htlc(
        self, secret_hash: str, timelock: int, recipient: str, amount: float
    ) -> Dict:
        """
        Create HTLC for Monero (XMR)

        Monero requires special protocol:
        1. Use view keys for verification
        2. Adaptor signatures for atomicity
        3. Different cryptography (Ed25519)

        This is complex and requires Monero-specific implementation
        """

        return {
            "contract_type": "HTLC_MONERO",
            "protocol": "Adaptor Signatures + View Keys",
            "claim_method": "Submit adaptor signature with secret",
            "refund_method": f"Reclaim after timelock {timelock}",
            "supported_coins": ["XMR"],
            "complexity": "HIGH - Requires Monero daemon integration",
            "note": "Privacy-preserving atomic swaps using ring signatures",
        }

    def verify_swap_claim(
        self, secret: str, secret_hash: str, contract_data: Dict
    ) -> Tuple[bool, str]:
        """
        Verify that counterparty can claim their side of swap

        Args:
            secret: Revealed secret (hex string)
            secret_hash: Expected hash of secret
            contract_data: Contract details

        Returns:
            tuple: (is_valid, message)
        """

        # Verify secret matches hash
        revealed_hash = hashlib.sha256(bytes.fromhex(secret)).hexdigest()

        if revealed_hash != secret_hash:
            return False, "Secret does not match hash"

        # Check if timelock expired
        if time.time() > contract_data["timelock"]:
            return False, "Timelock expired - refund period active"

        return True, "Valid claim - swap can proceed"

    def claim_swap(
        self, secret: str, contract_data: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Claim the counterparty's funds by revealing the secret

        Args:
            secret: The secret that hashes to the contract's secret_hash
            contract_data: The swap contract details

        Returns:
            tuple: (success, message, claim_transaction)
        """
        # Verify the claim is valid
        is_valid, message = self.verify_swap_claim(
            secret, contract_data["secret_hash"], contract_data
        )

        if not is_valid:
            return False, message, None

        # Create claim transaction
        claim_tx = {
            "type": "atomic_swap_claim",
            "contract_hash": contract_data["secret_hash"],
            "secret": secret,
            "recipient": contract_data.get("counterparty_address", ""),
            "amount": contract_data["other_coin_amount"],
            "coin_type": contract_data["other_coin"],
            "timestamp": time.time(),
            "status": "claimed",
        }

        return True, "Swap claimed successfully", claim_tx

    def refund_swap(self, contract_data: Dict) -> Tuple[bool, str, Optional[Dict]]:
        """
        Refund the swap after timelock expires

        Args:
            contract_data: The swap contract details

        Returns:
            tuple: (success, message, refund_transaction)
        """
        current_time = time.time()

        # Check if timelock has expired
        if current_time < contract_data["timelock"]:
            time_remaining = contract_data["timelock"] - current_time
            return (
                False,
                f"Timelock not expired. {time_remaining:.0f} seconds remaining",
                None,
            )

        # Create refund transaction
        refund_tx = {
            "type": "atomic_swap_refund",
            "contract_hash": contract_data["secret_hash"],
            "original_sender": contract_data.get("sender_address", ""),
            "amount": contract_data["axn_amount"],
            "coin_type": "XAI",
            "timestamp": current_time,
            "status": "refunded",
            "reason": "timelock_expired",
        }

        return True, "Swap refunded successfully", refund_tx

    def verify_refund_eligibility(self, contract_data: Dict) -> Tuple[bool, str]:
        """
        Verify if a swap is eligible for refund

        Args:
            contract_data: The swap contract details

        Returns:
            tuple: (is_eligible, message)
        """
        current_time = time.time()

        # Check if timelock has expired
        if current_time < contract_data["timelock"]:
            time_remaining = contract_data["timelock"] - current_time
            hours_remaining = time_remaining / 3600
            return (
                False,
                f"Timelock not expired. {hours_remaining:.2f} hours remaining",
            )

        # Check if swap already claimed
        if contract_data.get("status") == "claimed":
            return False, "Swap already claimed by counterparty"

        return True, "Eligible for refund"

    def get_supported_coins(self) -> Dict:
        """Get all supported coins"""

        return {
            "BTC": {"name": "Bitcoin", "protocol": "HTLC_UTXO"},
            "ETH": {"name": "Ethereum", "protocol": "HTLC_ETHEREUM"},
            "LTC": {"name": "Litecoin", "protocol": "HTLC_UTXO"},
            "DOGE": {"name": "Dogecoin", "protocol": "HTLC_UTXO"},
            "XMR": {"name": "Monero", "protocol": "HTLC_MONERO"},
            "BCH": {"name": "Bitcoin Cash", "protocol": "HTLC_UTXO"},
            "USDT": {"name": "Tether", "protocol": "HTLC_ETHEREUM"},
            "ZEC": {"name": "Zcash", "protocol": "HTLC_UTXO"},
            "DASH": {"name": "Dash", "protocol": "HTLC_UTXO"},
            "USDC": {"name": "USD Coin", "protocol": "HTLC_ETHEREUM"},
            "DAI": {"name": "Dai", "protocol": "HTLC_ETHEREUM"},
        }


class CrossChainVerifier:
    """
    Cross-chain verification for atomic swaps.
    Uses SPV (Simplified Payment Verification) proofs and oracle integration
    to verify transactions on external blockchains.
    """

    def __init__(self):
        """Initialize cross-chain verifier"""
        self.verified_transactions: Dict[str, Dict] = {}
        self.oracle_endpoints: Dict[str, str] = {
            "BTC": "https://blockstream.info/api",
            "ETH": "https://api.etherscan.io/api",
            "LTC": "https://api.blockcypher.com/v1/ltc/main",
            "DOGE": "https://dogechain.info/api/v1",
            # Add more as needed
        }
        self.lock = threading.RLock()

    def verify_spv_proof(
        self, coin_type: str, tx_hash: str, merkle_proof: List[str], block_header: Dict
    ) -> Tuple[bool, str]:
        """
        Verify a transaction using SPV (Simplified Payment Verification)

        Args:
            coin_type: Blockchain coin type (BTC, LTC, etc.)
            tx_hash: Transaction hash to verify
            merkle_proof: Merkle branch proving inclusion
            block_header: Block header containing merkle root

        Returns:
            tuple: (is_valid, message)
        """
        try:
            # Reconstruct merkle root from proof
            current_hash = tx_hash

            for proof_hash in merkle_proof:
                # Combine hashes (order matters for merkle trees)
                combined = current_hash + proof_hash
                current_hash = hashlib.sha256(
                    hashlib.sha256(combined.encode()).digest()
                ).hexdigest()

            # Verify against block header merkle root
            merkle_root = block_header.get("merkle_root", "")

            if current_hash == merkle_root:
                return True, "SPV proof verified successfully"
            else:
                return False, "SPV proof verification failed: merkle root mismatch"

        except Exception as e:
            return False, f"SPV verification error: {str(e)}"

    def verify_transaction_on_chain(
        self, coin_type: str, tx_hash: str, expected_amount: float, recipient: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify a transaction on an external blockchain using oracle/API

        Args:
            coin_type: Coin type (BTC, ETH, etc.)
            tx_hash: Transaction hash
            expected_amount: Expected transaction amount
            recipient: Expected recipient address

        Returns:
            tuple: (is_valid, message, transaction_data)
        """
        # Check cache first
        cache_key = f"{coin_type}:{tx_hash}"
        with self.lock:
            if cache_key in self.verified_transactions:
                cached = self.verified_transactions[cache_key]
                return cached["valid"], cached["message"], cached.get("data")

        # In production, this would make actual API calls to blockchain explorers
        # For now, we'll simulate the verification
        verification_result = self._simulate_blockchain_verification(
            coin_type, tx_hash, expected_amount, recipient
        )

        # Cache the result
        with self.lock:
            self.verified_transactions[cache_key] = verification_result

        return (
            verification_result["valid"],
            verification_result["message"],
            verification_result.get("data"),
        )

    def _simulate_blockchain_verification(
        self, coin_type: str, tx_hash: str, expected_amount: float, recipient: str
    ) -> Dict:
        """
        Simulate blockchain verification (in production, use real APIs)

        Args:
            coin_type: Coin type
            tx_hash: Transaction hash
            expected_amount: Expected amount
            recipient: Expected recipient

        Returns:
            Verification result dictionary
        """
        # Production implementation would:
        # 1. Query blockchain API/oracle for transaction
        # 2. Verify transaction exists and is confirmed
        # 3. Check amount matches
        # 4. Check recipient matches
        # 5. Verify sufficient confirmations

        # Simulated verification
        tx_data = {
            "txid": tx_hash,
            "confirmations": 6,  # Simulated confirmations
            "amount": expected_amount,
            "recipient": recipient,
            "timestamp": time.time(),
            "block_height": 700000,  # Simulated
        }

        # Simple validation
        if len(tx_hash) != 64:
            return {
                "valid": False,
                "message": "Invalid transaction hash format",
                "data": None,
            }

        # In production, verify actual transaction details
        return {
            "valid": True,
            "message": f"Transaction verified on {coin_type} blockchain",
            "data": tx_data,
        }

    def verify_minimum_confirmations(
        self, coin_type: str, tx_hash: str, min_confirmations: int = 6
    ) -> Tuple[bool, int]:
        """
        Verify a transaction has minimum confirmations

        Args:
            coin_type: Blockchain type
            tx_hash: Transaction hash
            min_confirmations: Minimum required confirmations

        Returns:
            tuple: (has_confirmations, actual_confirmations)
        """
        # Production: Query actual blockchain
        # For now, simulate
        cache_key = f"{coin_type}:{tx_hash}"

        with self.lock:
            if cache_key in self.verified_transactions:
                confirmations = self.verified_transactions[cache_key].get("data", {}).get(
                    "confirmations", 0
                )
                return confirmations >= min_confirmations, confirmations

        # Not verified yet
        return False, 0

    def create_spv_proof(
        self, coin_type: str, tx_hash: str, block_hash: str
    ) -> Optional[Dict]:
        """
        Create an SPV proof for a transaction (for the counterparty to verify)

        Args:
            coin_type: Blockchain type
            tx_hash: Transaction hash
            block_hash: Block containing the transaction

        Returns:
            SPV proof data
        """
        # Production: Generate actual merkle proof
        # Simulation:
        return {
            "tx_hash": tx_hash,
            "block_hash": block_hash,
            "merkle_proof": [
                hashlib.sha256(b"proof1").hexdigest(),
                hashlib.sha256(b"proof2").hexdigest(),
            ],
            "block_header": {
                "version": 1,
                "merkle_root": hashlib.sha256(b"merkle_root").hexdigest(),
                "timestamp": int(time.time()),
                "bits": "1a0ffff0",
            },
            "position": 5,  # Position in block
        }

    def verify_oracle_signature(self, oracle_data: Dict, signature: str) -> bool:
        """
        Verify oracle data signature for trusted third-party verification

        Args:
            oracle_data: Data from oracle
            signature: Oracle's signature

        Returns:
            True if signature is valid
        """
        # Production: Verify actual cryptographic signature
        # For now, basic validation
        return len(signature) == 128  # Simulate signature validation

    def get_verification_status(self, coin_type: str, tx_hash: str) -> Optional[Dict]:
        """
        Get the verification status of a transaction

        Args:
            coin_type: Blockchain type
            tx_hash: Transaction hash

        Returns:
            Verification status or None if not found
        """
        cache_key = f"{coin_type}:{tx_hash}"
        with self.lock:
            return self.verified_transactions.get(cache_key)


# Trading pair manager
class MeshDEXPairManager:
    """Manages trading pairs"""

    def __init__(self):
        self.supported_pairs = self._initialize_pairs()

    def _initialize_pairs(self) -> Dict:
        """Initialize trading pairs"""

        pairs = {}
        for coin in CoinType:
            pair_name = f"XAI/{coin.name}"
            pairs[pair_name] = {
                "coin_type": coin,
                "protocol": COIN_PROTOCOLS[coin],
                "atomic_swap": AtomicSwapHTLC(coin),
                "active": True,
                "launch_phase": self._get_launch_phase(coin),
            }

        return pairs

    def _get_launch_phase(self, coin: CoinType) -> str:
        """Determine launch phase for each coin"""

        # Phase 1: UTXO coins (easiest to implement)
        phase1 = [
            CoinType.BTC,
            CoinType.LTC,
            CoinType.DOGE,
            CoinType.BCH,
            CoinType.ZEC,
            CoinType.DASH,
        ]

        # Phase 2: Ethereum tokens (requires bridge)
        phase2 = [CoinType.ETH, CoinType.USDT, CoinType.USDC, CoinType.DAI]

        # Phase 3: Monero (complex)
        phase3 = [CoinType.XMR]

        if coin in phase1:
            return "PHASE_1_LAUNCH"
        elif coin in phase2:
            return "PHASE_2_MONTH_3"
        elif coin in phase3:
            return "PHASE_3_MONTH_6"

    def create_swap(
        self, pair: str, axn_amount: float, other_amount: float, counterparty: str
    ) -> Dict:
        """
        Create atomic swap for any of the 11 pairs

        Args:
            pair: Trading pair (e.g., "XAI/BTC")
            axn_amount: Amount of XAI
            other_amount: Amount of other coin
            counterparty: Counterparty address

        Returns:
            dict: Swap contract details
        """

        if pair not in self.supported_pairs:
            return {
                "success": False,
                "error": "UNSUPPORTED_PAIR",
                "message": f"Pair {pair} not supported. Supported: {list(self.supported_pairs.keys())}",
            }

        pair_data = self.supported_pairs[pair]

        if not pair_data["active"]:
            return {
                "success": False,
                "error": "PAIR_INACTIVE",
                "message": f'Pair {pair} is not yet active. Launch phase: {pair_data["launch_phase"]}',
            }

        # Create atomic swap
        swap = pair_data["atomic_swap"].create_swap_contract(
            axn_amount=axn_amount, other_coin_amount=other_amount, counterparty_address=counterparty
        )

        return swap

    def get_all_pairs(self) -> Dict:
        """Get information about all 11 trading pairs"""

        result = {}
        for pair_name, pair_data in self.supported_pairs.items():
            coin = pair_data["coin_type"]
            result[pair_name] = {
                "coin": coin.value,
                "protocol": pair_data["protocol"].value,
                "active": pair_data["active"],
                "launch_phase": pair_data["launch_phase"],
            }

        return result


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("XAI Atomic Swap System")
    print("=" * 70)

    # Initialize DEX
    dex = MeshDEXPairManager()

    # Show supported pairs
    print("\nSupported Trading Pairs:")
    print("-" * 70)

    for pair, info in dex.get_all_pairs().items():
        status = "ACTIVE" if info["active"] else "INACTIVE"
        print(f"{pair:15} | {info['coin']:20} | {info['protocol']:20} | {status}")

    # Show supported coins
    print("\n\nSupported Coins:")
    print("-" * 70)

    btc_swap = AtomicSwapHTLC(CoinType.BTC)
    all_coins = btc_swap.get_supported_coins()

    for symbol, coin_data in all_coins.items():
        print(f"{symbol}: {coin_data['name']} ({coin_data['protocol']})")

    # Test creating a swap
    print("\n\nExample: Creating XAI/BTC Atomic Swap")
    print("-" * 70)

    swap_result = dex.create_swap(
        pair="XAI/BTC",
        axn_amount=1000,
        other_amount=0.005,
        counterparty="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    )

    if swap_result["success"]:
        print("Swap created successfully")
        print(f"Secret Hash: {swap_result['secret_hash'][:32]}...")
        print(f"Timelock: {swap_result['timelock_hours']} hours")
    else:
        print(f"Swap failed: {swap_result['message']}")

    # Test another swap (free market - no restrictions)
    print("\n\nSecond Swap Test (Free Market)")
    print("-" * 70)

    test_swap = dex.create_swap(
        pair="XAI/BTC",
        axn_amount=1000,
        other_amount=0.0038,
        counterparty="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    )

    if test_swap["success"]:
        print("Swap created successfully (no price restrictions)")
        print(f"Secret Hash: {test_swap['secret_hash'][:32]}...")
    else:
        print(f"Swap failed: {test_swap.get('message', 'Unknown error')}")
