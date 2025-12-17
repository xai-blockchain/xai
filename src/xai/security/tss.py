from abc import ABC, abstractmethod
import hashlib
import logging
from typing import Dict, List, Optional, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from xai.security.tss_production import (
    ProductionTSS,
    TSSKeyShare,
)

logger = logging.getLogger(__name__)


class TSSInterface(ABC):
    """
    Abstract Base Class for a Threshold Signature Scheme (TSS).
    Defines the interface for distributed key generation, signing, and verification.
    """

    @abstractmethod
    def generate_distributed_keys(self, num_participants: int, threshold: int) -> List[TSSKeyShare]:
        """
        Generates key shares for multiple participants such that a threshold
        number of shares can reconstruct the signing key or produce a signature.
        """
        raise NotImplementedError

    @abstractmethod
    def distributed_sign(
        self,
        message: bytes,
        participant_key_shares: Sequence[TSSKeyShare],
        threshold: Optional[int] = None,
    ) -> bytes:
        """
        Collects partial signatures from participants and combines them to produce
        a final threshold signature.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_threshold_signature(
        self, message: bytes, signature: bytes, public_key: bytes
    ) -> bool:
        """
        Verifies a threshold signature against a message hash and the combined public key.
        """
        raise NotImplementedError


class MockTSS(TSSInterface):
    """
    A hardened mock Threshold Signature Scheme for fast local testing.

    This mock keeps the legacy interface but now enforces strict key tracking,
    signature verification, and threshold checks so that misuse is surfaced
    immediately instead of silently succeeding.
    """

    def __init__(self) -> None:
        self._master_public_key: Optional[bytes] = None
        self._participants_keys: Dict[str, Tuple[str, str]] = {}
        self._threshold: Optional[int] = None

    def generate_distributed_keys(self, num_participants: int, threshold: int) -> List[TSSKeyShare]:
        if threshold > num_participants:
            raise ValueError("Threshold cannot be greater than number of participants.")
        if threshold < 1:
            raise ValueError("Threshold must be at least 1.")

        participant_key_shares: List[TSSKeyShare] = []
        for i in range(num_participants):
            private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
            public_key = private_key.public_key()

            priv_hex = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).hex()
            pub_hex = public_key.public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            ).hex()

            participant_id = f"participant_{i+1}"
            self._participants_keys[participant_id] = (priv_hex, pub_hex)
            participant_key_shares.append(
                TSSKeyShare(
                    participant_id=participant_id,
                    share_index=i + 1,
                    private_share=int.from_bytes(hashlib.sha256(priv_hex.encode()).digest(), "big"),
                    public_key=bytes.fromhex(pub_hex),
                    verification_point=public_key.public_bytes(
                        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
                    ),
                )
            )

        # Treat first participant's public key as reference for mock verification
        self._master_public_key = participant_key_shares[0].public_key
        self._threshold = threshold

        logger.info(
            "Generated mock participant keys",
            extra={
                "event": "tss.mock_keys_generated",
                "participants": num_participants,
                "threshold": threshold,
            },
        )
        return participant_key_shares

    def _require_threshold(self, provided: Optional[int]) -> int:
        threshold = provided or self._threshold
        if threshold is None:
            raise ValueError("Threshold not initialized for signing.")
        return threshold

    def distributed_sign(
        self,
        message: bytes,
        participant_key_shares: Sequence[TSSKeyShare],
        threshold: Optional[int] = None,
    ) -> bytes:
        """
        Simulates distributed signing by verifying a threshold of individual signatures.
        Returns a concatenated string of valid signatures if threshold is met.
        """
        required = self._require_threshold(threshold)
        if len(participant_key_shares) < required:
            raise ValueError(
                f"Insufficient signatures collected. Required: {required}, Got: {len(participant_key_shares)}"
            )

        valid_signatures: List[bytes] = []
        for share in participant_key_shares:
            stored = self._participants_keys.get(share.participant_id)
            if not stored:
                logger.warning(
                    "Unknown participant tried to sign",
                    extra={"event": "tss.unknown_participant", "participant": share.participant_id},
                )
                continue
            priv_hex, pub_hex = stored
            try:
                private_key = serialization.load_pem_private_key(
                    bytes.fromhex(priv_hex), password=None, backend=default_backend()
                )
                signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
                public_key = serialization.load_pem_public_key(
                    bytes.fromhex(pub_hex), backend=default_backend()
                )
                public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
                valid_signatures.append(signature)
            except (ValueError, InvalidSignature) as exc:
                logger.warning(
                    "MockTSS rejected invalid participant signature",
                    extra={
                        "event": "tss.invalid_signature",
                        "participant": share.participant_id,
                        "error": str(exc),
                    },
                )

        if len(valid_signatures) >= required:
            # In a real TSS, partial signatures are combined cryptographically.
            # Here, we just concatenate them for a mock "threshold signature".
            return b"".join(sorted(valid_signatures))
        raise ValueError(
            f"Failed to collect enough valid signatures. Valid: {len(valid_signatures)}, Required: {required}"
        )

    def verify_threshold_signature(self, message: bytes, combined_signature: bytes, public_key: bytes) -> bool:
        """
        In a real TSS, this would verify the combined signature against the master public key.
        Here, we just check if the combined_signature is non-empty (meaning threshold was met).
        """
        return bool(combined_signature) and public_key == self._master_public_key


class SecureTSS(TSSInterface):
    """
    Production wrapper around the fully implemented TSS with Shamir shares.

    This class upgrades the public interface used throughout the codebase to
    route through the hardened `ProductionTSS` implementation while keeping
    the same ergonomic API expected by tests and integrations.
    """

    def __init__(self, curve: ec.EllipticCurve = ec.SECP256K1()) -> None:
        self.curve = curve
        self._impl = ProductionTSS(curve)
        self._key_shares: List[TSSKeyShare] = []
        self._master_public_key: Optional[bytes] = None
        self._threshold: Optional[int] = None

    def generate_distributed_keys(self, num_participants: int, threshold: int) -> List[TSSKeyShare]:
        key_shares, master_public_key = self._impl.generate_distributed_keys(
            num_participants=num_participants, threshold=threshold
        )
        self._key_shares = key_shares
        self._master_public_key = master_public_key
        self._threshold = threshold
        return key_shares

    def distributed_sign(
        self,
        message: bytes,
        participant_key_shares: Sequence[TSSKeyShare],
        threshold: Optional[int] = None,
    ) -> bytes:
        required = threshold or self._threshold
        if required is None:
            raise ValueError("Threshold not initialized for signing.")
        if len(participant_key_shares) < required:
            raise ValueError(
                f"Insufficient partial signatures: {len(participant_key_shares)} provided, {required} required"
            )

        partials = []
        for share in participant_key_shares[:required]:
            r_s = self._impl.create_partial_signature(share, message)
            partials.append((share.share_index, share, r_s))
        return self._impl.combine_partial_signatures(partials, required)

    def verify_threshold_signature(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        if not public_key:
            raise ValueError("Public key is required for verification.")
        return self._impl.verify_threshold_signature(public_key, message, signature)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    raise SystemExit("TSS demo removed; use unit tests instead.")
