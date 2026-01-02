from __future__ import annotations

"""
XAI Atomic Swap Protocol
HTLC-based atomic swaps for cross-chain trading
Free market pricing - no restrictions
"""

import hashlib
import json
import logging
import os
import secrets
import threading
import time
from decimal import ROUND_UP, Decimal, InvalidOperation
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

import requests

from xai.core.transactions import htlc_deployer, htlc_p2wsh
from xai.core.config import Config
from xai.core.p2p.spv_header_ingestor import SPVHeaderIngestor


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
        SwapState.FAILED: [SwapState.CLAIMED, SwapState.REFUNDED],  # Allow recovery
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
        self.swaps: dict[str, dict] = {}
        self.lock = threading.RLock()

        # Load existing swaps from storage
        self._load_swaps()

    def create_swap(self, swap_id: str, swap_data: dict) -> bool:
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
        self, swap_id: str, new_state: SwapState, event: SwapEvent, data: dict | None = None
    ) -> tuple[bool, str]:
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

            if data:
                swap.setdefault("data", {}).update(data)

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

    def get_swap(self, swap_id: str) -> dict | None:
        """Get swap data by ID"""
        with self.lock:
            return self.swaps.get(swap_id)

    def get_swap_state(self, swap_id: str) -> SwapState | None:
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
        ]

    def get_active_swaps(self) -> dict[str, dict]:
        """Get all non-terminal swaps"""
        with self.lock:
            return {
                swap_id: swap
                for swap_id, swap in self.swaps.items()
                if not self.is_terminal_state(swap_id)
            }

    def iter_swaps(self) -> list[tuple[str, dict]]:
        """Return list of (swap_id, swap_data) for all swaps."""
        with self.lock:
            return list(self.swaps.items())

    def update_swap_data(self, swap_id: str, patch: dict[str, Any]) -> bool:
        """Merge additional metadata into stored swap data."""
        with self.lock:
            swap = self.swaps.get(swap_id)
            if not swap:
                return False
            swap.setdefault("data", {}).update(patch)
            self._persist_swap(swap_id)
            return True

    def check_timeouts(self) -> list[str]:
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

        except KeyError as e:
            logger.error(
                "Missing swap data in _persist_swap",
                extra={
                    "error_type": "KeyError",
                    "error": str(e),
                    "swap_id": swap_id,
                    "function": "_persist_swap"
                }
            )
        except (OSError, IOError) as e:
            logger.error(
                "File system error in _persist_swap",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "swap_id": swap_id,
                    "function": "_persist_swap"
                }
            )
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(
                "Serialization error in _persist_swap",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "swap_id": swap_id,
                    "function": "_persist_swap"
                }
            )
        except Exception as e:
            # Unexpected error - log with full context for debugging
            logger.error(
                "Unexpected error in _persist_swap",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "swap_id": swap_id,
                    "function": "_persist_swap"
                },
                exc_info=True
            )

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

        except (OSError, IOError) as e:
            logger.error(
                "File system error in _load_swaps",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "function": "_load_swaps"
                }
            )
        except json.JSONDecodeError as e:
            logger.error(
                "JSON decode error in _load_swaps - possibly corrupted swap file",
                extra={
                    "error_type": "JSONDecodeError",
                    "error": str(e),
                    "function": "_load_swaps"
                }
            )
        except (KeyError, ValueError) as e:
            logger.error(
                "Invalid swap data in _load_swaps",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "function": "_load_swaps"
                }
            )
        except Exception as e:
            # Unexpected error - log with full context for debugging
            logger.error(
                "Unexpected error in _load_swaps",
                extra={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "function": "_load_swaps"
                },
                exc_info=True
            )

    def get_swap_history(self, swap_id: str) -> list[dict]:
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
        secret_bytes: bytes | None = None,
        deployment_config: dict[str, Any] | None = None,
    ) -> dict:
        """
        Create a new atomic swap contract

        Args:
            axn_amount: Amount of XAI to swap
            other_coin_amount: Amount of other coin to receive
            counterparty_address: Address of trading partner
            timelock_hours: Hours until refund becomes available
            secret_bytes: Optional externally supplied 32-byte secret for cross-chain parity

        Returns:
            dict: Swap contract details
        """

        # Generate secret for HTLC
        secret = secret_bytes or secrets.token_bytes(32)
        secret_hash = hashlib.sha256(secret).hexdigest()

        # Calculate timelock (Unix timestamp)
        timelock = int(time.time()) + (timelock_hours * 3600)

        # Create contract based on protocol
        deployment_config = deployment_config or {}
        if self.protocol == SwapProtocol.HTLC_UTXO:
            contract = self._create_utxo_htlc(
                secret_hash,
                timelock,
                counterparty_address,
                other_coin_amount,
                deployment_config,
            )
        elif self.protocol == SwapProtocol.HTLC_ETHEREUM:
            contract = self._create_ethereum_htlc(
                secret_hash,
                timelock,
                counterparty_address,
                other_coin_amount,
                deployment_config,
            )
        elif self.protocol == SwapProtocol.HTLC_MONERO:
            contract = self._create_monero_htlc(
                secret_hash,
                timelock,
                counterparty_address,
                other_coin_amount,
                deployment_config,
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
        self,
        secret_hash: str,
        timelock: int,
        recipient: str,
        amount: float,
        deployment_config: dict[str, Any] | None = None,
    ) -> dict:
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

        contract: dict[str, Any] = {
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
        contract["recommended_fee"] = self._recommended_utxo_fee(amount)
        cfg = self._extract_protocol_config(deployment_config, "utxo")
        if not cfg:
            contract["deployment_ready"] = False
            return contract

        recipient_pubkey = cfg.get("recipient_pubkey") or cfg.get("counterparty_pubkey")
        sender_pubkey = cfg.get("sender_pubkey")
        hrp = cfg.get("hrp", cfg.get("network_hrp", "bc"))
        missing: list[str] = []
        if not recipient_pubkey:
            missing.append("recipient_pubkey")
        if not sender_pubkey:
            missing.append("sender_pubkey")
        if missing:
            contract["deployment_ready"] = False
            contract["deployment_missing_fields"] = missing
            return contract

        try:
            script_payload = htlc_p2wsh.build_utxo_contract(
                secret_hash_hex=secret_hash,
                timelock=timelock,
                recipient_pubkey=recipient_pubkey,
                sender_pubkey=sender_pubkey,
                hrp=hrp,
            )
            funding_sats = self._convert_to_base_units(amount, cfg.get("decimals", 8))
            contract.update(
                {
                    "deployment_ready": True,
                    "redeem_script_hex": script_payload["redeem_script_hex"],
                    "witness_program": script_payload["witness_program"],
                    "script_pubkey": script_payload["script_pubkey"],
                    "p2wsh_address": script_payload["p2wsh_address"],
                    "funding_amount_sats": funding_sats,
                    "network": cfg.get("network", "bitcoin"),
                    "funding_template": {
                        "address": script_payload["p2wsh_address"],
                        "amount_sats": funding_sats,
                        "suggested_fee_sats": cfg.get("suggested_fee_sats"),
                        "change_address": cfg.get("change_address"),
                    },
                }
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in _create_utxo_htlc",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "_create_utxo_htlc"
                }
            )
            contract["deployment_ready"] = False
            contract["deployment_error"] = str(exc)
        return contract

    @staticmethod
    def build_utxo_redeem_script(secret_hash: str, recipient_pubkey: str, sender_pubkey: str, timelock: int) -> str:
        """
        Construct a standard P2WSH-compatible HTLC redeem script.

        Returns a string representation suitable for hashing/encoding.
        """
        return (
            "OP_IF "
            f"OP_SHA256 {secret_hash} OP_EQUALVERIFY "
            f"{recipient_pubkey} OP_CHECKSIG "
            "OP_ELSE "
            f"{timelock} OP_CHECKLOCKTIMEVERIFY OP_DROP "
            f"{sender_pubkey} OP_CHECKSIG "
            "OP_ENDIF"
        )

    @staticmethod
    def witness_script_hash(redeem_script: str) -> str:
        """
        Return the SHA256 witness script hash (hex) for a redeem script.
        """
        return hashlib.sha256(redeem_script.encode("utf-8")).hexdigest()

    def _recommended_utxo_fee(self, amount: float) -> dict[str, Any]:
        fee_rate = Decimal(str(getattr(Config, "ATOMIC_SWAP_FEE_RATE", 0.0000005)))
        tx_size = int(getattr(Config, "ATOMIC_SWAP_UTXO_TX_SIZE", 300))

        # For zero amounts, calculate network fee only (no safety buffer)
        if amount == 0:
            network_fee = (fee_rate * Decimal(tx_size)).quantize(Decimal("0.00000001"), rounding=ROUND_UP)
            fee = float(network_fee)
        else:
            fee = CrossChainVerifier.calculate_atomic_swap_fee(
                amount,
                fee_rate,
                tx_size_bytes=tx_size,
            )

        return {
            "total_fee": float(fee),
            "unit": self.coin_type.name,
            "fee_rate_per_byte": float(fee_rate),
            "tx_size_bytes": tx_size,
        }

    def _recommended_eth_fee(self) -> dict[str, Any]:
        gas_limit = int(getattr(Config, "ATOMIC_SWAP_ETH_GAS_LIMIT", 200000))
        max_fee_gwei = Decimal(str(getattr(Config, "ATOMIC_SWAP_ETH_MAX_FEE_GWEI", 60)))
        priority_gwei = Decimal(str(getattr(Config, "ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI", 2)))
        total_fee_eth = (max_fee_gwei * Decimal(gas_limit)) / Decimal("1000000000")
        return {
            "gas_limit": gas_limit,
            "max_fee_per_gas_gwei": float(max_fee_gwei),
            "priority_fee_gwei": float(priority_gwei),
            "estimated_total_fee_eth": float(total_fee_eth),
        }

    def _create_ethereum_htlc(
        self,
        secret_hash: str,
        timelock: int,
        recipient: str,
        amount: float,
        deployment_config: dict[str, Any] | None = None,
    ) -> dict:
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

        contract: dict[str, Any] = {
            "contract_type": "HTLC_ETHEREUM",
            "smart_contract": solidity_contract,
            "claim_method": "Call claim(secret) function",
            "refund_method": f"Call refund() after {timelock}",
            "supported_tokens": ["ETH", "USDT", "USDC", "DAI"],
            "gas_estimate": "~150,000 gas for claim, ~50,000 for refund",
        }
        contract["recommended_gas"] = self._recommended_eth_fee()
        cfg = self._extract_protocol_config(deployment_config, "ethereum")
        if not cfg:
            contract["deployment_ready"] = False
            return contract

        if not cfg.get("auto_deploy", True):
            contract["deployment_ready"] = False
            return contract

        sender = cfg.get("sender") or cfg.get("funding_address")
        web3_obj = cfg.get("web3")
        if not sender or not web3_obj:
            missing_fields = []
            if not sender:
                missing_fields.append("sender")
            if not web3_obj:
                missing_fields.append("web3")
            contract["deployment_ready"] = False
            contract["deployment_missing_fields"] = missing_fields
            return contract

        decimals = int(cfg.get("decimals", 18))
        value_wei = cfg.get("value_wei")
        try:
            if value_wei is None:
                value_wei = self._convert_to_base_units(amount, decimals)
        except (ValueError, InvalidOperation) as exc:
            contract["deployment_ready"] = False
            contract["deployment_error"] = f"invalid_amount: {exc}"
            return contract

        try:
            deployed_contract = htlc_deployer.deploy_htlc(
                web3_obj,
                secret_hash=secret_hash,
                recipient=recipient,
                timelock_unix=timelock,
                value_wei=value_wei,
                sender=sender,
                gas=cfg.get("gas"),
                max_fee_per_gas=cfg.get("max_fee_per_gas"),
                max_priority_fee_per_gas=cfg.get("max_priority_fee_per_gas"),
                solc_version=cfg.get("solc_version", "0.8.21"),
            )
        except Exception as exc:  # pragma: no cover - defensive network handling
            logger.warning(
                "Exception in _create_ethereum_htlc",
                extra={
                    "error_type": "Exception",
                    "error": str(exc),
                    "function": "_create_ethereum_htlc"
                }
            )
            contract["deployment_ready"] = False
            contract["deployment_error"] = str(exc)
            return contract

        contract.update(
            {
                "deployment_ready": True,
                "contract_address": getattr(deployed_contract, "address", None),
                "chain_id": getattr(getattr(web3_obj, "eth", None), "chain_id", None),
                "htlc_abi": getattr(deployed_contract, "abi", None),
            }
        )
        return contract

    def _create_monero_htlc(
        self,
        secret_hash: str,
        timelock: int,
        recipient: str,
        amount: float,
        deployment_config: dict[str, Any] | None = None,
    ) -> dict:
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
            "deployment_ready": False,
        }

    @staticmethod
    def _extract_protocol_config(config: dict[str, Any] | None, key: str) -> dict[str, Any]:
        """Return protocol-specific deployment config if provided."""
        if not isinstance(config, dict):
            return {}
        if key in config and isinstance(config[key], dict):
            return config[key]
        fallback_keys = {
            "utxo": {"sender_pubkey", "recipient_pubkey", "counterparty_pubkey", "hrp", "network"},
            "ethereum": {"web3", "sender", "funding_address", "value_wei"},
            "monero": {"daemon_rpc", "view_key"},
        }
        expected = fallback_keys.get(key, set())
        if expected and any(k in config for k in expected):
            return config
        return {}

    @staticmethod
    def _convert_to_base_units(amount: float, decimals: int) -> int:
        """
        Convert a human-readable amount into protocol base units (integer).
        """
        dec_value = Decimal(str(amount))
        multiplier = Decimal(10) ** Decimal(decimals)
        scaled = (dec_value * multiplier).quantize(Decimal("1"), rounding=ROUND_UP)
        return int(scaled)

    @staticmethod
    def _reconstruct_merkle_root(tx_hash: str, merkle_proof: list[str], tx_index: int) -> str:
        """
        Reconstruct the merkle root from a transaction hash and sibling hashes.
        All inputs/outputs are big-endian hex strings; internal hashing uses the
        Bitcoin-style little-endian double-SHA256 concatenation.
        """
        if not isinstance(merkle_proof, list):
            raise ValueError("merkle_proof must be a list of sibling hashes")

        try:
            current = bytes.fromhex(tx_hash)[::-1]
        except ValueError as exc:
            raise ValueError("invalid transaction hash") from exc

        position = int(tx_index)
        for sibling_hex in merkle_proof:
            try:
                sibling = bytes.fromhex(sibling_hex)[::-1]
            except ValueError as exc:
                raise ValueError("invalid sibling hash") from exc
            if position & 1:
                concat = sibling + current
            else:
                concat = current + sibling
            current = hashlib.sha256(hashlib.sha256(concat).digest()).digest()
            position >>= 1

        return current[::-1].hex()

    def verify_swap_claim(
        self, secret: str, secret_hash: str, contract_data: dict
    ) -> tuple[bool, str]:
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
        self, secret: str, contract_data: dict
    ) -> tuple[bool, str, dict | None]:
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

    def refund_swap(self, contract_data: dict) -> tuple[bool, str, dict | None]:
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

    def verify_refund_eligibility(self, contract_data: dict) -> tuple[bool, str]:
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

    def get_supported_coins(self) -> dict:
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

    DEFAULT_TIMEOUT = 8.0
    CACHE_TTL_SECONDS = 300

    def __init__(self, session: requests.Session | None = None, header_store: Any | None = None):
        """Initialize cross-chain verifier"""
        self.verified_transactions: dict[str, dict] = {}
        self.lock = threading.RLock()
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "xai-atomic-swap-verifier/1.0"})
        self.header_store = header_store
        self.header_ingestor = SPVHeaderIngestor(self.header_store) if self.header_store else None

        # Providers must return deterministic JSON structures; tests patch _http_get_json
        self.oracle_endpoints: dict[str, dict[str, Any]] = {
            "BTC": {
                "type": "utxo",
                "tx_url": "https://blockstream.info/api/tx/{txid}",
                "tip_url": "https://blockstream.info/api/blocks/tip/height",
                "merkle_url": "https://blockstream.info/api/tx/{txid}/merkle-proof",
                "block_hash_url": "https://blockstream.info/api/block-height/{height}",
                "block_header_url": "https://blockstream.info/api/block/{block_hash}/header",
                "value_is_base_units": True,
                "decimals": 8,
            },
            "LTC": {
                "type": "utxo",
                "tx_url": "https://api.blockcypher.com/v1/ltc/main/txs/{txid}",
                "tip_url": "https://api.blockcypher.com/v1/ltc/main",
                "value_is_base_units": True,
                "decimals": 8,
            },
            "DOGE": {
                "type": "utxo",
                "tx_url": "https://dogechain.info/api/v1/transaction/{txid}",
                "tip_url": "https://dogechain.info/api/v1/block/latest",
                "value_is_base_units": True,
                "decimals": 8,
            },
            "ETH": {
                "type": "account",
                "tx_url": "https://api.etherscan.io/api",
                "tip_url": "https://api.etherscan.io/api",
                "value_is_base_units": True,  # wei
                "decimals": 18,
                "api_key_env": "XAI_ETHERSCAN_API_KEY",
            },
        }

    @staticmethod
    def calculate_atomic_swap_fee(
        amount: Decimal | float | str,
        fee_rate_per_byte: Decimal | float | str,
        *,
        tx_size_bytes: int = 300,
        safety_buffer_bps: int = 15,
        min_fee: Decimal = Decimal("0.0001"),
        max_fee: Decimal = Decimal("0.25"),
    ) -> Decimal:
        """
        Calculate a conservative fee for HTLC funding/claim transactions.

        The calculation combines a network fee estimate (fee rate * tx size)
        with a safety buffer (basis points on amount) and clamps the result
        between sensible minimum/maximum bounds to avoid dust rejection or
        runaway fee selection during congestion.
        """
        try:
            amount_dec = Decimal(str(amount))
            rate_dec = Decimal(str(fee_rate_per_byte))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Invalid amount or fee rate") from exc

        if amount_dec <= 0 or rate_dec <= 0:
            raise ValueError("Amount and fee rate must be positive")

        network_fee = (rate_dec * Decimal(tx_size_bytes)).quantize(Decimal("0.00000001"), rounding=ROUND_UP)
        safety_fee = (amount_dec * Decimal(safety_buffer_bps) / Decimal(10000)).quantize(
            Decimal("0.00000001"), rounding=ROUND_UP
        )
        total_fee = network_fee + safety_fee

        if total_fee < min_fee:
            total_fee = min_fee
        if total_fee > max_fee:
            total_fee = max_fee
        return total_fee

    def verify_spv_proof(
        self,
        coin_type: str,
        tx_hash: str,
        merkle_proof: list[str],
        block_header: dict,
        tx_index: int = 0,
    ) -> tuple[bool, str]:
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
            reconstructed = self._reconstruct_merkle_root(tx_hash, merkle_proof, tx_index)
        except ValueError as exc:
            logger.warning(
                "ValueError in verify_spv_proof",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "verify_spv_proof"
                }
            )
            return False, f"SPV verification error: {exc}"

        merkle_root = (block_header.get("merkle_root") or "").lower()
        if not merkle_root:
            return False, "SPV verification error: block header missing merkle_root"

        if reconstructed == merkle_root:
            return True, "SPV proof verified successfully"
        return False, "SPV proof verification failed: merkle root mismatch"

    def verify_transaction_on_chain(
        self,
        coin_type: str,
        tx_hash: str,
        expected_amount: float,
        recipient: str,
        *,
        min_confirmations: int = 1,
        amount_tolerance: Decimal = Decimal("0.00000001"),
    ) -> tuple[bool, str, dict | None]:
        """
        Verify a transaction on an external blockchain using oracle/API

        Args:
            coin_type: Coin type (BTC, ETH, etc.)
            tx_hash: Transaction hash
            expected_amount: Expected transaction amount
            recipient: Expected recipient address
            min_confirmations: Minimum confirmations required for acceptance
            amount_tolerance: Allowed underflow tolerance when comparing amounts

        Returns:
            tuple: (is_valid, message, transaction_data)
        """
        normalized_coin = coin_type.upper()
        min_confirmations = max(1, int(min_confirmations))

        if not self._is_supported_coin(normalized_coin):
            return False, f"Unsupported coin type: {coin_type}", None

        if not self._is_valid_tx_hash(tx_hash):
            return False, "Invalid transaction hash format", None

        try:
            expected_amount_dec = Decimal(str(expected_amount))
        except (InvalidOperation, ValueError):
            return False, "Invalid expected amount", None

        if expected_amount_dec <= 0:
            return False, "Expected amount must be positive", None

        cache_key = f"{normalized_coin}:{tx_hash}:{min_confirmations}"
        with self.lock:
            if cache_key in self.verified_transactions:
                cached = self.verified_transactions[cache_key]
                if time.time() - cached.get("timestamp", 0) < self.CACHE_TTL_SECONDS:
                    return cached["valid"], cached["message"], cached.get("data")

        provider = self.oracle_endpoints[normalized_coin]
        try:
            tx_data = self._fetch_transaction(provider, normalized_coin, tx_hash)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Exception in verify_transaction_on_chain",
                extra={
                    "error_type": "Exception",
                    "error": str(exc),
                    "function": "verify_transaction_on_chain"
                }
            )
            return False, f"Verification failed: {exc}", None

        if not tx_data:
            result = {"valid": False, "message": "Transaction not found", "data": None}
            self._cache_result(cache_key, result)
            return False, result["message"], None

        confirmations = tx_data.get("confirmations", 0)
        if self.header_store and tx_data.get("block_height") is not None:
            header_confirmations = self._confirmations_from_header_store(tx_data["block_height"])
            if header_confirmations is not None and header_confirmations > confirmations:
                confirmations = header_confirmations
        tx_data["confirmations"] = confirmations
        if confirmations < min_confirmations:
            result = {
                "valid": False,
                "message": f"Insufficient confirmations: {confirmations}/{min_confirmations}",
                "data": tx_data,
            }
            self._cache_result(cache_key, result)
            return False, result["message"], tx_data

        amount_received = self._calculate_amount_to_recipient(
            tx_data, recipient, normalized_coin
        )
        tx_data["amount_to_recipient"] = float(amount_received)
        if amount_received + amount_tolerance < expected_amount_dec:
            result = {
                "valid": False,
                "message": (
                    f"Amount mismatch. Expected {expected_amount_dec} "
                    f"received {amount_received}"
                ),
                "data": tx_data,
            }
            self._cache_result(cache_key, result)
            return False, result["message"], tx_data

        result = {
            "valid": True,
            "message": f"Transaction verified on {normalized_coin} blockchain",
            "data": {
                **tx_data,
                "amount_to_recipient": float(amount_received),
                "recipient": recipient,
                "expected_amount": float(expected_amount_dec),
                "coin": normalized_coin,
            },
        }
        self._cache_result(cache_key, result)
        return True, result["message"], result["data"]

    def verify_transaction_spv(
        self,
        coin_type: str,
        tx_hash: str,
    ) -> tuple[bool, str, dict | None]:
        """
        Fetch merkle proof + block header from external APIs and verify SPV inclusion.
        """
        normalized_coin = coin_type.upper()
        provider = self.oracle_endpoints.get(normalized_coin)
        if not provider or not provider.get("merkle_url"):
            return False, f"SPV verification not supported for {coin_type}", None

        try:
            proof = self._fetch_merkle_proof(provider, tx_hash)
        except Exception as exc:
            logger.warning(
                "Exception in verify_transaction_spv",
                extra={
                    "error_type": "Exception",
                    "error": str(exc),
                    "function": "verify_transaction_spv"
                }
            )
            return False, f"Failed to fetch merkle proof: {exc}", None
        if not proof or not proof.get("hashes"):
            return False, "Merkle proof unavailable", None

        try:
            block_header = self._fetch_block_header(
                provider,
                proof.get("block_height"),
                proof.get("block_hash"),
            )
        except Exception as exc:
            logger.warning(
                "Exception in verify_transaction_spv",
                extra={
                    "error_type": "Exception",
                    "error": str(exc),
                    "function": "verify_transaction_spv"
                }
            )
            return False, f"Failed to fetch block header: {exc}", None

        ok, message = self.verify_spv_proof(
            normalized_coin,
            tx_hash,
            proof["hashes"],
            block_header,
            tx_index=proof.get("tx_index", 0),
        )
        if ok:
            return True, message, {
                "block_height": block_header.get("block_height"),
                "block_hash": block_header.get("block_hash"),
                "merkle_root": block_header.get("merkle_root"),
                "tx_index": proof.get("tx_index", 0),
            }
        return False, message, None

    def ingest_headers(self, headers: list[dict[str, Any]]) -> tuple[int, list[str]]:
        """
        Ingest validated headers into the SPV header store for confirmation calculation.
        """
        if not self.header_ingestor:
            return 0, []
        return self.header_ingestor.ingest(headers)

    def _is_supported_coin(self, coin_type: str) -> bool:
        return coin_type in self.oracle_endpoints

    @staticmethod
    def _is_valid_tx_hash(tx_hash: str) -> bool:
        if not isinstance(tx_hash, str):
            return False
        tx_hash = tx_hash.strip()
        if len(tx_hash) != 64:
            return False
        try:
            int(tx_hash, 16)
            return True
        except ValueError:
            return False

    def _confirmations_from_header_store(self, block_height: int) -> int | None:
        """
        Derive confirmations using validated headers when available.
        """
        if not self.header_store:
            return None
        tip = getattr(self.header_store, "get_best_tip", lambda: None)()
        if not tip or getattr(tip, "height", None) is None:
            return None
        if hasattr(self.header_store, "has_height") and not self.header_store.has_height(block_height):
            return None
        if tip.height < block_height:
            return None
        return (tip.height - block_height) + 1

    def _cache_result(self, cache_key: str, result: dict[str, Any]) -> None:
        with self.lock:
            self.verified_transactions[cache_key] = {
                **result,
                "timestamp": time.time(),
            }

    def _fetch_merkle_proof(
        self,
        provider: dict[str, Any],
        tx_hash: str,
    ) -> dict[str, Any] | None:
        merkle_url = provider.get("merkle_url")
        if not merkle_url:
            return None
        proof_json = self._http_get_json(
            merkle_url.format(txid=tx_hash),
            timeout=provider.get("timeout", self.DEFAULT_TIMEOUT),
        )
        merkle_hashes = proof_json.get("merkle") or proof_json.get("hashes")
        if not isinstance(merkle_hashes, list):
            return None
        tx_index = proof_json.get("pos", proof_json.get("position", 0))
        block_height = proof_json.get("block_height")
        block_hash = proof_json.get("block_hash")
        return {
            "hashes": [str(h).strip() for h in merkle_hashes],
            "tx_index": int(tx_index or 0),
            "block_height": block_height,
            "block_hash": block_hash,
        }

    def _fetch_block_header(
        self,
        provider: dict[str, Any],
        block_height: int | None,
        block_hash: str | None = None,
    ) -> dict[str, Any]:
        if block_hash:
            normalized_hash = str(block_hash).strip()
        else:
            if block_height is None:
                raise ValueError("block_height required to fetch block hash")
            height_url = provider.get("block_hash_url")
            if not height_url:
                raise ValueError("Provider missing block_hash_url")
            normalized_hash = self._http_get_text(
                height_url.format(height=block_height),
                timeout=provider.get("timeout", self.DEFAULT_TIMEOUT),
            ).strip()
        header_url = provider.get("block_header_url")
        if not header_url:
            raise ValueError("Provider missing block_header_url")
        header_hex = self._http_get_text(
            header_url.format(block_hash=normalized_hash),
            timeout=provider.get("timeout", self.DEFAULT_TIMEOUT),
        ).strip()
        header = self._decode_block_header(header_hex, block_height)
        header["block_hash"] = normalized_hash
        return header

    def _fetch_transaction(
        self, provider: dict[str, Any], coin_type: str, tx_hash: str
    ) -> dict[str, Any] | None:
        fetch_type = provider.get("type")
        if fetch_type == "utxo":
            return self._fetch_utxo_transaction(provider, coin_type, tx_hash)
        if fetch_type == "account":
            return self._fetch_account_transaction(provider, coin_type, tx_hash)
        raise ValueError(f"Unsupported provider type: {fetch_type}")

    def _fetch_utxo_transaction(
        self, provider: dict[str, Any], coin_type: str, tx_hash: str
    ) -> dict[str, Any] | None:
        tx_url = provider["tx_url"].format(txid=tx_hash)
        tx_json = self._http_get_json(tx_url, timeout=provider.get("timeout", self.DEFAULT_TIMEOUT))
        if not tx_json:
            return None

        block_height = self._extract_block_height(tx_json)
        confirmations = self._extract_confirmations(tx_json)
        if confirmations is None and block_height is not None and provider.get("tip_url"):
            tip_json = self._http_get_json(
                provider["tip_url"], timeout=provider.get("timeout", self.DEFAULT_TIMEOUT)
            )
            tip_height = self._extract_tip_height(tip_json)
            if tip_height and tip_height >= block_height:
                confirmations = (tip_height - block_height) + 1

        outputs = self._parse_utxo_outputs(
            tx_json,
            coin_type,
            value_is_base_units=provider.get("value_is_base_units", True),
        )
        if confirmations is None:
            confirmations = 0

        return {
            "txid": tx_hash,
            "confirmations": confirmations,
            "block_height": block_height,
            "outputs": outputs,
            "raw": tx_json,
        }

    def _fetch_account_transaction(
        self, provider: dict[str, Any], coin_type: str, tx_hash: str
    ) -> dict[str, Any] | None:
        api_key = os.getenv(provider.get("api_key_env", ""), "")
        params = {
            "module": "proxy",
            "action": "eth_getTransactionByHash",
            "txhash": tx_hash,
        }
        if api_key:
            params["apikey"] = api_key

        response = self._http_get_json(
            provider["tx_url"], params=params, timeout=provider.get("timeout", self.DEFAULT_TIMEOUT)
        )
        result = response.get("result") if isinstance(response, dict) else None
        if not result:
            return None

        to_address = str(result.get("to") or "").lower()
        value_hex = result.get("value", "0x0")
        block_hex = result.get("blockNumber")

        try:
            value_wei = Decimal(int(value_hex, 16))
        except (ValueError, InvalidOperation):
            return None

        decimals = provider.get("decimals", 18)
        amount = self._normalize_amount(value_wei, coin_type, decimals, in_base_units=True)

        confirmations = 0
        block_number = None
        if block_hex:
            try:
                block_number = int(block_hex, 16)
            except ValueError:
                block_number = None

        if block_number is not None:
            tip_params = {"module": "proxy", "action": "eth_blockNumber"}
            if api_key:
                tip_params["apikey"] = api_key
            tip_response = self._http_get_json(
                provider["tip_url"],
                params=tip_params,
                timeout=provider.get("timeout", self.DEFAULT_TIMEOUT),
            )
            tip_hex = tip_response.get("result") if isinstance(tip_response, dict) else None
            try:
                tip_number = int(tip_hex, 16) if tip_hex else None
            except ValueError:
                tip_number = None
            if tip_number is not None and block_number is not None and tip_number >= block_number:
                confirmations = (tip_number - block_number) + 1

        outputs = [{"address": to_address, "amount": amount}]
        return {
            "txid": tx_hash,
            "confirmations": confirmations,
            "block_height": block_number,
            "outputs": outputs,
            "raw": result,
        }

    def _http_get_json(
        self, url: str, params: dict[str, Any] | None = None, *, timeout: float = DEFAULT_TIMEOUT
    ) -> dict[str, Any]:
        response = self.session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def _http_get_text(
        self, url: str, params: dict[str, Any] | None = None, *, timeout: float = DEFAULT_TIMEOUT
    ) -> str:
        response = self.session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _extract_block_height(tx_json: dict[str, Any]) -> int | None:
        status = tx_json.get("status") or {}
        for key in ("block_height", "blockHeight"):
            height = status.get(key) if isinstance(status, dict) else None
            if height is None:
                height = tx_json.get(key)
            if height is not None:
                try:
                    return int(height)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _extract_confirmations(tx_json: dict[str, Any]) -> int | None:
        confirmations = tx_json.get("confirmations")
        if confirmations is None and isinstance(tx_json.get("status"), dict):
            confirmations = tx_json["status"].get("confirmations")
        if confirmations is None:
            return None
        try:
            return int(confirmations)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _decode_block_header(header_hex: str, block_height: int | None) -> dict[str, Any]:
        header_hex = header_hex.strip()
        header_bytes = bytes.fromhex(header_hex)
        if len(header_bytes) < 80:
            raise ValueError("header too short")
        version = int.from_bytes(header_bytes[0:4], "little")
        prev_hash = header_bytes[4:36][::-1].hex()
        merkle_root = header_bytes[36:68][::-1].hex()
        timestamp = int.from_bytes(header_bytes[68:72], "little")
        bits = int.from_bytes(header_bytes[72:76], "little")
        nonce = int.from_bytes(header_bytes[76:80], "little")
        return {
            "version": version,
            "previous_hash": prev_hash,
            "merkle_root": merkle_root,
            "timestamp": timestamp,
            "bits": bits,
            "nonce": nonce,
            "block_height": block_height,
        }

    @staticmethod
    def _extract_tip_height(tip_json: Any) -> int | None:
        if isinstance(tip_json, dict):
            for key in ("height", "block_height", "latest_height"):
                height = tip_json.get(key)
                if height is not None:
                    try:
                        return int(height)
                    except (TypeError, ValueError):
                        continue
        else:
            try:
                return int(tip_json)
            except (TypeError, ValueError):
                return None
        return None

    def _normalize_amount(
        self, raw_value: Any, coin_type: str, decimals: int, *, in_base_units: bool
    ) -> Decimal:
        value = Decimal(str(raw_value))
        if in_base_units:
            scale = Decimal(10) ** decimals
            return value / scale
        return value

    def _parse_utxo_outputs(
        self, tx_json: dict[str, Any], coin_type: str, *, value_is_base_units: bool
    ) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []
        candidates = tx_json.get("vout") or tx_json.get("outputs") or []
        decimals = self.oracle_endpoints.get(coin_type, {}).get("decimals", 8)

        for output in candidates:
            address = self._extract_output_address(output)
            raw_value = self._extract_output_value(output)
            if address is None or raw_value is None:
                continue
            try:
                amount = self._normalize_amount(raw_value, coin_type, decimals, in_base_units=value_is_base_units)
            except (InvalidOperation, ValueError):
                continue
            outputs.append({"address": address, "amount": amount})
        return outputs

    @staticmethod
    def _extract_output_address(output: dict[str, Any]) -> str | None:
        address_fields = [
            output.get("scriptpubkey_address"),
            output.get("address"),
        ]
        script_pubkey = output.get("scriptPubKey") or {}
        if isinstance(script_pubkey, dict):
            address_fields.extend(script_pubkey.get("addresses", []))
        address_fields.extend(output.get("addresses", []))
        for candidate in address_fields:
            if candidate:
                return str(candidate)
        return None

    @staticmethod
    def _extract_output_value(output: dict[str, Any]) -> Any | None:
        for key in ("value", "valueSat", "satoshis", "amount"):
            if key in output and output[key] is not None:
                return output[key]
        return None

    @staticmethod
    def _normalize_address(address: str, coin_type: str) -> str:
        if coin_type == "ETH":
            return address.lower()
        return address

    def _calculate_amount_to_recipient(
        self, tx_data: dict[str, Any], recipient: str, coin_type: str
    ) -> Decimal:
        normalized_recipient = self._normalize_address(recipient, coin_type)
        total = Decimal("0")
        outputs = tx_data.get("outputs") or []
        if not outputs and tx_data.get("vout"):
            # Fallback parse when raw vout data is provided without normalized outputs
            outputs = self._parse_utxo_outputs(
                tx_data,
                coin_type,
                value_is_base_units=self.oracle_endpoints.get(coin_type, {}).get("value_is_base_units", True),
            )
        for output in outputs:
            address = output.get("address")
            amount = output.get("amount")
            if address is None or amount is None:
                continue
            if self._normalize_address(str(address), coin_type) == normalized_recipient:
                total += Decimal(str(amount))
        return total

    def verify_minimum_confirmations(
        self, coin_type: str, tx_hash: str, min_confirmations: int = 6
    ) -> tuple[bool, int]:
        """
        Verify a transaction has minimum confirmations

        Args:
            coin_type: Blockchain type
            tx_hash: Transaction hash
            min_confirmations: Minimum required confirmations

        Returns:
            tuple: (has_confirmations, actual_confirmations)
        """
        # Reuse the full verification path to obtain validated confirmation counts.
        valid, _msg, data = self.verify_transaction_on_chain(
            coin_type,
            tx_hash,
            expected_amount=Decimal("0.00000001"),  # minimal positive sentinel
            recipient="",  # recipient ignored in confirmation-only check
            min_confirmations=min_confirmations,
            amount_tolerance=Decimal("1000000"),  # bypass amount comparison for this path
        )
        confirmations = data.get("confirmations", 0) if data else 0
        return valid, confirmations

    def create_spv_proof(
        self, coin_type: str, tx_hash: str, block_hash: str
    ) -> dict | None:
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

    def verify_oracle_signature(self, oracle_data: dict, signature: str) -> bool:
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

    def get_verification_status(self, coin_type: str, tx_hash: str) -> dict | None:
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

class SwapRefundPlanner:
    """
    Plan refundable atomic swaps by combining timelock checks with SPV-backed
    confirmation verification.
    """

    REFUNDABLE_STATES = {
        SwapState.FUNDED.value,
        SwapState.COUNTERPARTY_FUNDED.value,
        SwapState.FUNDED,
        SwapState.COUNTERPARTY_FUNDED,
    }

    def __init__(self, verifier: CrossChainVerifier, now_fn=time.time):
        self.verifier = verifier
        self._now = now_fn

    def plan_refunds(self, swaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Return swaps that are eligible for refund execution.

        Expected swap fields:
        - swap_id: unique identifier
        - coin: coin symbol (e.g., BTC)
        - funding_txid: on-chain funding transaction hash
        - timelock: unix timestamp when refund becomes valid
        - min_confirmations: minimum confirmations required before refund
        - state: current swap state (string or SwapState)
        """
        refundable: list[dict[str, Any]] = []
        now = self._now()
        for swap in swaps:
            state = swap.get("state")
            if state not in self.REFUNDABLE_STATES:
                continue
            timelock = swap.get("timelock")
            if timelock is None or now < float(timelock):
                continue
            txid = swap.get("funding_txid")
            coin = swap.get("coin")
            min_conf = int(swap.get("min_confirmations", 1))
            if not txid or not coin:
                continue
            try:
                has_conf, confirmations = self.verifier.verify_minimum_confirmations(coin, txid, min_conf)
            except Exception:
                continue
            if not has_conf:
                continue
            enriched = dict(swap)
            enriched["confirmations"] = confirmations
            refundable.append(enriched)
        return refundable

class SwapRecoveryService:
    """
    High-level recovery orchestrator that surfaces refundable swaps using the planner.
    """

    def __init__(
        self,
        state_machine: SwapStateMachine,
        planner: SwapRefundPlanner,
        claim_service: "SwapClaimRecoveryService" | None = None,
    ):
        self.state_machine = state_machine
        self.planner = planner
        self.claim_service = claim_service

    def find_refundable_swaps(self) -> list[dict[str, Any]]:
        """Return refundable swaps enriched with confirmations."""
        candidates: list[dict[str, Any]] = []
        for swap_id, swap in self.state_machine.iter_swaps():
            data = swap.get("data", {}) if isinstance(swap, dict) else {}
            try:
                candidates.append(
                    {
                        "swap_id": swap_id,
                        "coin": data.get("coin"),
                        "funding_txid": data.get("funding_txid"),
                        "timelock": data.get("timelock"),
                        "min_confirmations": data.get("min_confirmations", 1),
                        "state": swap.get("state") if isinstance(swap.get("state"), SwapState) else swap.get("state"),
                    }
                )
            except Exception:
                continue
        refundable = self.planner.plan_refunds(candidates)
        return refundable

    def auto_transition_refunds(self) -> list[str]:
        """
        Identify refundable swaps and transition them to REFUNDED state.
        Returns list of swap_ids transitioned.
        """
        transitioned: list[str] = []
        refundable = self.find_refundable_swaps()
        for swap in refundable:
            swap_id = swap["swap_id"]
            ok, _ = self.state_machine.transition(swap_id, SwapState.REFUNDED, SwapEvent.REFUND, data=swap)
            if ok:
                transitioned.append(swap_id)
        return transitioned

    def auto_recover_failed_claims(self) -> list[str]:
        """Attempt automatic claim recovery when a claim previously failed."""
        if not self.claim_service:
            return []
        return self.claim_service.recover_failed_claims()

class SwapClaimRecoveryService:
    """
    Automatically attempt to recover swaps that failed during claim execution.
    """

    def __init__(self, state_machine: SwapStateMachine, max_attempts: int = 3, now_fn=time.time):
        self.state_machine = state_machine
        self.max_attempts = max_attempts
        self._now = now_fn

    def recover_failed_claims(self) -> list[str]:
        """
        Iterate through failed swaps and attempt to re-run the claim path or fall back to refunds.
        Returns list of swap_ids that were auto-recovered (claimed or refunded).
        """
        recovered: list[str] = []
        for swap_id, swap in self.state_machine.iter_swaps():
            state = swap.get("state")
            if state != SwapState.FAILED:
                continue
            payload = dict(swap.get("data", {}))
            attempts = int(payload.get("auto_recovery_attempts", 0))
            if attempts >= self.max_attempts:
                continue
            payload["auto_recovery_attempts"] = attempts + 1
            if not self.state_machine.update_swap_data(swap_id, {"auto_recovery_attempts": attempts + 1}):
                continue

            # Timelock safety - if expired, skip directly to refund
            if self._timelock_expired(payload):
                ok, _ = self.state_machine.transition(
                    swap_id,
                    SwapState.REFUNDED,
                    SwapEvent.REFUND,
                    data={"recovery_reason": "timelock_expired"},
                )
                if ok:
                    recovered.append(swap_id)
                continue

            secret = payload.get("secret")
            secret_hash = payload.get("secret_hash")
            if not secret or not secret_hash:
                self.state_machine.update_swap_data(
                    swap_id,
                    {"last_recovery_error": "missing_secret"},
                )
                continue

            htlc = self._create_htlc(payload)
            if not htlc:
                self.state_machine.update_swap_data(
                    swap_id,
                    {"last_recovery_error": "unsupported_coin"},
                )
                continue

            valid, validation_msg = htlc.verify_swap_claim(secret, secret_hash, payload)
            if not valid:
                # If timelock expired between earlier check and verification, refund.
                if "Timelock" in validation_msg:
                    ok, _ = self.state_machine.transition(
                        swap_id,
                        SwapState.REFUNDED,
                        SwapEvent.REFUND,
                        data={"recovery_reason": "timelock_expired"},
                    )
                    if ok:
                        recovered.append(swap_id)
                else:
                    errors = list(payload.get("recovery_errors", []))
                    errors.append(validation_msg)
                    self.state_machine.update_swap_data(
                        swap_id,
                        {
                            "last_recovery_error": validation_msg,
                            "recovery_errors": errors[-5:],
                        },
                    )
                continue

            success, claim_message, claim_tx = htlc.claim_swap(secret, payload)
            if success:
                patch = {
                    "auto_recovered": True,
                    "recovery_claim": claim_tx,
                    "recovery_claim_message": claim_message,
                    "recovery_claimed_at": self._now(),
                    "last_recovery_error": None,
                    "failure_reason": None,
                }
                ok, _ = self.state_machine.transition(swap_id, SwapState.CLAIMED, SwapEvent.CLAIM, data=patch)
                if ok:
                    recovered.append(swap_id)
            else:
                errors = list(payload.get("recovery_errors", []))
                errors.append(claim_message)
                self.state_machine.update_swap_data(
                    swap_id,
                    {
                        "last_recovery_error": claim_message,
                        "recovery_errors": errors[-5:],
                    },
                )
        return recovered

    def _timelock_expired(self, payload: dict[str, Any]) -> bool:
        timelock = payload.get("timelock")
        if timelock is None:
            return False
        try:
            return self._now() >= float(timelock)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _create_htlc(payload: dict[str, Any]) -> AtomicSwapHTLC | None:
        symbol = (payload.get("other_coin") or payload.get("coin") or "").upper()
        if not symbol:
            return None
        try:
            coin = CoinType[symbol]
        except KeyError:
            return None
        return AtomicSwapHTLC(coin)

# Trading pair manager
class MeshDEXPairManager:
    """Manages trading pairs"""

    def __init__(self):
        self.supported_pairs = self._initialize_pairs()

    def _initialize_pairs(self) -> dict:
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
    ) -> dict:
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

    def get_all_pairs(self) -> dict:
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
