"""
Validator-signature based block finality.

This module implements cryptographic finality certificates that require a
weighted quorum of validator signatures. Validators sign a deterministic
payload derived from the block header, and once the threshold is met the
block becomes irrevocable for fork-choice purposes.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from xai.blockchain.double_sign_detector import DoubleSignDetector
from xai.core.crypto_utils import verify_signature_hex
from xai.core.structured_logger import get_structured_logger
from xai.core.block_header import BlockHeader


class FinalityError(Exception):
    """Base class for finality related errors."""


class FinalityConfigurationError(FinalityError):
    """Raised when validator configuration is invalid."""


class FinalityValidationError(FinalityError):
    """Raised for invalid votes or signatures."""


@dataclass(frozen=True)
class ValidatorIdentity:
    """Validator metadata required for verifying finality votes."""

    address: str
    public_key: str
    voting_power: int = 1

    def normalized_id(self) -> str:
        return self.address.lower()


@dataclass
class FinalityCertificate:
    """Aggregated proof that a block reached the required quorum."""

    block_hash: str
    block_height: int
    signatures: Dict[str, str] = field(default_factory=dict)
    aggregated_power: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, object]:
        return {
            "block_hash": self.block_hash,
            "block_height": self.block_height,
            "signatures": self.signatures,
            "aggregated_power": self.aggregated_power,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "FinalityCertificate":
        return cls(
            block_hash=str(payload["block_hash"]),
            block_height=int(payload["block_height"]),
            signatures=dict(payload.get("signatures", {})),
            aggregated_power=int(payload.get("aggregated_power", 0)),
            created_at=float(payload.get("created_at", time.time())),
        )


class FinalityManager:
    """Coordinator that tracks validator votes and issues finality certificates."""

    SIGNING_DOMAIN = "XAI_FINALITY_V1"

    def __init__(
        self,
        *,
        data_dir: str,
        validators: Sequence[ValidatorIdentity],
        quorum_threshold: float = 2.0 / 3.0,
        misbehavior_callback: Optional[Callable[[str, int, Dict[str, Any]], None]] = None,
    ) -> None:
        if quorum_threshold <= 0 or quorum_threshold > 1:
            raise FinalityConfigurationError("Finality quorum threshold must be between 0 and 1.")
        if not validators:
            raise FinalityConfigurationError("At least one validator is required for finality.")

        self.logger = get_structured_logger()
        self._lock = threading.RLock()
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "finality_certificates.json")
        self.validators: Dict[str, ValidatorIdentity] = {}
        self.total_power = 0
        self._misbehavior_callback = misbehavior_callback
        for validator in validators:
            if validator.voting_power <= 0:
                raise FinalityConfigurationError(
                    f"Validator {validator.address} must have positive voting power."
                )
            validator_id = validator.normalized_id()
            if validator_id in self.validators:
                raise FinalityConfigurationError(f"Duplicate validator address: {validator.address}")
            self.validators[validator_id] = validator
            self.total_power += validator.voting_power

        if self.total_power <= 0:
            raise FinalityConfigurationError("Total validator voting power must be positive.")

        self.quorum_power = math.ceil(self.total_power * quorum_threshold)
        self.detector = DoubleSignDetector()
        self.pending_votes: Dict[str, Dict[str, str]] = {}
        self.pending_power: Dict[str, int] = {}
        self.certificates_by_hash: Dict[str, FinalityCertificate] = {}
        self.certificates_by_height: Dict[int, FinalityCertificate] = {}
        self.state_path = os.path.join(self.data_dir, "finality_state.json")
        self._load_certificates()
        self._load_state()

    def build_vote_payload(self, header: BlockHeader) -> bytes:
        """Return the canonical message that validators must sign."""
        return f"{self.SIGNING_DOMAIN}|{header.hash}|{header.index}".encode("utf-8")

    def record_vote(
        self,
        *,
        validator_address: str,
        header: BlockHeader,
        signature: str,
    ) -> Optional[FinalityCertificate]:
        """Record a validator vote. Returns a certificate when quorum is met."""
        validator_id = validator_address.lower()
        with self._lock:
            validator = self.validators.get(validator_id)
            if not validator:
                raise FinalityValidationError(f"Unknown validator: {validator_address}")

            message = self.build_vote_payload(header)
            if not verify_signature_hex(validator.public_key, message, signature):
                raise FinalityValidationError("Invalid finality signature.")

            is_double, proof = self.detector.process_signed_block(
                validator_id=validator.address,
                block_height=header.index,
                signed_block_hash=header.hash,
            )
            if is_double:
                self.logger.error(
                    "Validator double-sign detected",
                    validator=validator.address,
                    block_height=header.index,
                    proof=proof,
                )
                if self._misbehavior_callback:
                    try:
                        self._misbehavior_callback(validator.address, header.index, proof or {})
                    except Exception as exc:  # pragma: no cover - defensive logging
                        self.logger.error(
                            "Finality misbehavior callback failed",
                            validator=validator.address,
                            error=str(exc),
                        )
                raise FinalityValidationError(
                    f"Validator {validator.address} produced conflicting signatures for height {header.index}"
                )

            if header.hash in self.certificates_by_hash:
                return self.certificates_by_hash[header.hash]

            votes = self.pending_votes.setdefault(header.hash, {})
            if validator.address in votes:
                raise FinalityValidationError("Validator has already voted for this block.")

            votes[validator.address] = signature
            accumulated_power = self.pending_power.get(header.hash, 0) + validator.voting_power
            self.pending_power[header.hash] = accumulated_power

            if accumulated_power < self.quorum_power:
                return None

            certificate = FinalityCertificate(
                block_hash=header.hash,
                block_height=header.index,
                signatures=votes.copy(),
                aggregated_power=accumulated_power,
            )
            self._finalize_block(certificate)
            self._persist_certificates()
            return certificate

    def _finalize_block(self, certificate: FinalityCertificate) -> None:
        self.certificates_by_hash[certificate.block_hash] = certificate
        self.certificates_by_height[certificate.block_height] = certificate
        self.pending_votes.pop(certificate.block_hash, None)
        self.pending_power.pop(certificate.block_hash, None)
        self.logger.info(
            "Block finalized via validator quorum",
            block_hash=certificate.block_hash,
            block_height=certificate.block_height,
            aggregated_power=certificate.aggregated_power,
            quorum_power=self.quorum_power,
        )

    def _load_certificates(self) -> None:
        if not os.path.exists(self.store_path):
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.error("Failed to load finality certificates", error=str(exc))
            return

        for entry in payload:
            try:
                certificate = FinalityCertificate.from_dict(entry)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Invalid certificate entry", error=str(exc))
                continue
            self.certificates_by_hash[certificate.block_hash] = certificate
            self.certificates_by_height[certificate.block_height] = certificate

    def _load_state(self) -> None:
        """
        Load persisted finality state (metadata only). Certificates contain the actual
        votes; this file records summary metadata to make restarts deterministic.
        """
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self.logger.error("Failed to load finality state", error=str(exc))
            return

        # Sanity checks: ensure validator set matches what we booted with
        persisted_validators = state.get("validators", [])
        persisted_addresses = {str(v.get("address", "")).lower() for v in persisted_validators}
        current_addresses = set(self.validators.keys())
        if persisted_addresses and persisted_addresses != current_addresses:
            self.logger.warning(
                "Finality state validator set mismatch; ignoring persisted state",
                persisted=len(persisted_addresses),
                current=len(current_addresses),
            )
            return

        persisted_quorum = state.get("quorum_power")
        if isinstance(persisted_quorum, (int, float)) and persisted_quorum > 0:
            if int(persisted_quorum) != self.quorum_power:
                self.logger.warning(
                    "Finality state quorum mismatch; using in-memory quorum",
                    persisted=persisted_quorum,
                    current=self.quorum_power,
                )


    def _persist_certificates(self) -> None:
        serialized = [cert.to_dict() for cert in self.certificates_by_hash.values()]
        tmp_path = f"{self.store_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(serialized, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, self.store_path)
        self._persist_state()

    def _persist_state(self) -> None:
        """Persist finality metadata (quorum, validator set, latest finalized)."""
        state_payload = {
            "quorum_power": self.quorum_power,
            "total_power": self.total_power,
            "validators": [
                {"address": v.address, "public_key": v.public_key, "voting_power": v.voting_power}
                for v in self.validators.values()
            ],
            "highest_finalized_height": self.get_highest_finalized_height(),
            "certificate_count": len(self.certificates_by_hash),
            "persisted_at": time.time(),
        }
        tmp_path = f"{self.state_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(state_payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, self.state_path)

    def get_certificate_by_hash(self, block_hash: str) -> Optional[FinalityCertificate]:
        return self.certificates_by_hash.get(block_hash)

    def get_certificate_by_height(self, block_height: int) -> Optional[FinalityCertificate]:
        return self.certificates_by_height.get(block_height)

    def is_finalized(self, *, block_hash: Optional[str] = None, block_height: Optional[int] = None) -> bool:
        if block_hash is not None and block_hash in self.certificates_by_hash:
            return True
        if block_height is not None and block_height in self.certificates_by_height:
            return True
        return False

    def get_highest_finalized_height(self) -> Optional[int]:
        if not self.certificates_by_height:
            return None
        return max(self.certificates_by_height.keys())

    def can_reorg_to_height(self, fork_point: Optional[int]) -> bool:
        """Return True if reorganizing up to fork_point is allowed under finality."""
        highest_finalized = self.get_highest_finalized_height()
        if highest_finalized is None:
            return True
        fork_index = -1 if fork_point is None else fork_point
        return fork_index >= highest_finalized

    def summarize(self) -> Dict[str, object]:
        highest = self.get_highest_finalized_height()
        return {
            "total_validators": len(self.validators),
            "quorum_power": self.quorum_power,
            "highest_finalized_height": highest,
            "finalized_blocks": len(self.certificates_by_hash),
        }

    def snapshot(self) -> Dict[str, Any]:
        """
        Create a complete snapshot of the current finality state.
        Thread-safe atomic operation for chain reorganization rollback.

        Returns:
            A deep copy of the finality state including certificates and pending votes
        """
        import copy
        with self._lock:
            return {
                "pending_votes": copy.deepcopy(self.pending_votes),
                "pending_power": copy.deepcopy(self.pending_power),
                "certificates_by_hash": {
                    k: {
                        "block_hash": v.block_hash,
                        "block_height": v.block_height,
                        "signatures": copy.deepcopy(v.signatures),
                        "timestamp": v.timestamp,
                    }
                    for k, v in self.certificates_by_hash.items()
                },
                "certificates_by_height": copy.deepcopy(self.certificates_by_height),
                "detector_state": self.detector.get_state(),
            }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore finality state from a snapshot.
        Thread-safe atomic operation for chain reorganization rollback.

        Args:
            snapshot: Snapshot created by snapshot() method
        """
        import copy
        with self._lock:
            # Restore pending votes and power
            self.pending_votes = copy.deepcopy(snapshot.get("pending_votes", {}))
            self.pending_power = copy.deepcopy(snapshot.get("pending_power", {}))

            # Restore certificates
            self.certificates_by_hash = {}
            for block_hash, cert_data in snapshot.get("certificates_by_hash", {}).items():
                self.certificates_by_hash[block_hash] = FinalityCertificate(
                    block_hash=cert_data["block_hash"],
                    block_height=cert_data["block_height"],
                    signatures=copy.deepcopy(cert_data["signatures"]),
                    timestamp=cert_data["timestamp"],
                )

            self.certificates_by_height = {}
            for height_str, cert in self.certificates_by_hash.items():
                self.certificates_by_height[cert.block_height] = cert

            # Restore detector state
            detector_state = snapshot.get("detector_state")
            if detector_state:
                self.detector.restore_state(detector_state)

            # Persist restored state to disk
            self._save_certificates()
            self._save_state()

            self.logger.info(
                "Finality state restored from snapshot",
                extra={
                    "event": "finality.restore",
                    "certificate_count": len(self.certificates_by_hash),
                    "pending_vote_count": len(self.pending_votes),
                }
            )
