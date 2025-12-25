"""
Contract Manager - Handles smart contract lifecycle and state management

Extracted from Blockchain god class to improve maintainability and separation of concerns.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class ContractManager:
    """Manages smart contract registration, state, ABIs, and events."""

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize the ContractManager with a reference to the blockchain.

        Args:
            blockchain: The parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = blockchain.logger

    def derive_contract_address(self, sender: str, nonce: int | None) -> str:
        """Deterministically derive a contract address from sender and nonce."""
        # Use network-appropriate prefix
        from xai.core.config import NETWORK
        prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
        base_nonce = nonce if nonce is not None else self.blockchain.nonce_tracker.get_next_nonce(sender)
        digest = hashlib.sha256(f"{sender.lower()}:{base_nonce}".encode("utf-8")).hexdigest()
        return f"{prefix}{digest[:38].upper()}"

    def register_contract(
        self,
        address: str,
        creator: str,
        code: bytes,
        gas_limit: int,
        value: float = 0.0,
    ) -> None:
        """
        Register a new smart contract in the blockchain state.

        Args:
            address: The contract address
            creator: Address of the account that created the contract
            code: Compiled contract bytecode
            gas_limit: Maximum gas allowed for contract execution
            value: Initial ETH/token balance for the contract
        """
        normalized = address.upper()
        self.blockchain.contracts[normalized] = {
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

    def get_contract_state(self, address: str) -> dict[str, Any] | None:
        """
        Retrieve the current state of a smart contract.

        Args:
            address: Contract address to query

        Returns:
            Contract state dictionary or None if contract doesn't exist
        """
        contract = self.blockchain.contracts.get(address.upper())
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

    def normalize_contract_abi(self, abi: Any) -> list[dict[str, Any]] | None:
        """
        Normalize and validate a contract ABI.

        Args:
            abi: ABI specification (can be JSON string, dict, or list)

        Returns:
            Normalized ABI as a list of dictionaries, or None if input is None

        Raises:
            ValueError: If ABI is invalid or exceeds size limits
        """
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

        sanitized: list[dict[str, Any]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                raise ValueError("ABI entries must be JSON objects")
            normalized_entry: dict[str, Any] = {}
            for key, value in entry.items():
                if not isinstance(key, str):
                    raise ValueError("ABI entry keys must be strings")
                normalized_entry[key] = value
            sanitized.append(normalized_entry)

        serialized = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > self.blockchain._max_contract_abi_bytes:
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
        """
        Store or update the ABI for a contract.

        Args:
            address: Contract address
            abi: ABI specification to store
            verified: Whether this ABI has been verified
            source: Source of the ABI (e.g., "deployment", "verification", "manual")

        Returns:
            True if ABI was stored successfully

        Raises:
            ValueError: If contract doesn't exist or ABI is invalid
        """
        normalized = address.upper()
        contract = self.blockchain.contracts.get(normalized)
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

    def get_contract_abi(self, address: str) -> dict[str, Any] | None:
        """
        Retrieve the ABI for a contract.

        Args:
            address: Contract address

        Returns:
            Dictionary containing ABI and metadata, or None if not found
        """
        contract = self.blockchain.contracts.get(address.upper())
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

    def get_contract_interface_metadata(self, address: str) -> dict[str, Any] | None:
        """
        Return cached interface detection metadata, if available.

        Args:
            address: Contract address

        Returns:
            Interface metadata dictionary or None if not available
        """
        contract = self.blockchain.contracts.get(address.upper())
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
        supports: dict[str, bool],
        *,
        source: str = "probe",
    ) -> dict[str, Any]:
        """
        Persist interface detection results for downstream consumers.

        Args:
            address: Contract address
            supports: Dictionary mapping interface IDs to support status
            source: Source of the detection (e.g., "probe", "deployment")

        Returns:
            Updated metadata dictionary

        Raises:
            ValueError: If contract doesn't exist
        """
        normalized = address.upper()
        contract = self.blockchain.contracts.get(normalized)
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

    def get_contract_events(self, address: str, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        """
        Retrieve events emitted by a contract.

        Args:
            address: Contract address
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            Tuple of (list of events, total count)
        """
        normalized = address.upper()
        events: list[dict[str, Any]] = []
        for receipt in reversed(self.blockchain.contract_receipts):
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
        """
        Rebuild contract state from blockchain history.

        This method clears all contract state and replays all blocks
        to reconstruct the current contract state.
        """
        if not self.blockchain.smart_contract_manager:
            return
        self.blockchain.contracts.clear()
        self.blockchain.contract_receipts.clear()
        for header in self.blockchain.chain:
            block = self.blockchain.storage.load_block_from_disk(header.index)
            if block:
                receipts = self.blockchain.smart_contract_manager.process_block(block)
                self.blockchain.contract_receipts.extend(receipts)

    def sync_smart_contract_vm(self) -> None:
        """Ensure the smart-contract manager matches governance + config gates."""
        from xai.core.config import Config
        from xai.core.vm.manager import SmartContractManager

        config_enabled = bool(getattr(Config, "FEATURE_FLAGS", {}).get("vm"))
        governance_enabled = bool(
            self.blockchain.governance_executor and self.blockchain.governance_executor.is_feature_enabled("smart_contracts")
        )
        should_enable = config_enabled and governance_enabled

        if should_enable:
            if self.blockchain.smart_contract_manager is None:
                self.blockchain.smart_contract_manager = SmartContractManager(self.blockchain)
        else:
            self.blockchain.smart_contract_manager = None
