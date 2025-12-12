"""
Mnemonic QR Backup utilities.

Provides production-grade QR code generation for BIP-39 seed phrases so
users can back up their mnemonic in a scannable format with integrity
metadata and explicit warnings.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from mnemonic import Mnemonic

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_Q
except ImportError as exc:  # pragma: no cover - exercised when dependency missing
    qrcode = None  # type: ignore
    QR_IMPORT_ERROR = exc
else:
    QR_IMPORT_ERROR = None


class QRCodeUnavailableError(RuntimeError):
    """Raised when the qrcode dependency is missing from the environment."""


@dataclass
class QRBackupBundle:
    """Represents the full payload of a mnemonic QR export."""

    payload: Dict[str, Any]
    image_base64: str
    ascii_art: str


class MnemonicQRBackupGenerator:
    """
    Generate QR code payloads for mnemonic backups.

    The encoded payload contains enough metadata to verify integrity
    (checksum, timestamp, version, optional passphrase hint).
    """

    FORMAT_NAME = "xai-mnemonic-backup"
    FORMAT_VERSION = 1

    def __init__(self) -> None:
        if qrcode is None:
            raise QRCodeUnavailableError(
                "The 'qrcode' package is required for mnemonic QR backups. "
                "Install optional dependency: pip install 'qrcode[pil]'"
            )

        self._mnemo = Mnemonic("english")

    def _validate_mnemonic(self, mnemonic_phrase: str) -> str:
        normalized = " ".join(mnemonic_phrase.split())
        if not self._mnemo.check(normalized):
            raise ValueError("Invalid BIP-39 mnemonic phrase")
        return normalized

    @staticmethod
    def _build_checksum(mnemonic_phrase: str, passphrase: str) -> str:
        digest = hashlib.sha256(mnemonic_phrase.encode("utf-8"))
        if passphrase:
            digest.update(passphrase.encode("utf-8"))
        return digest.hexdigest()

    def build_payload(
        self,
        mnemonic_phrase: str,
        passphrase: str = "",
        include_passphrase: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct the structured payload that will be encoded in the QR."""
        normalized = self._validate_mnemonic(mnemonic_phrase)
        payload: Dict[str, Any] = {
            "format": self.FORMAT_NAME,
            "version": self.FORMAT_VERSION,
            "mnemonic": normalized,
            "word_count": len(normalized.split()),
            "created_at": int(time.time()),
            "checksum": self._build_checksum(normalized, passphrase),
        }

        if metadata:
            payload["metadata"] = metadata

        if passphrase:
            payload["passphrase_hint"] = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()[:16]
            if include_passphrase:
                payload["passphrase"] = passphrase

        return payload

    def recover_mnemonic(self, payload: Dict[str, Any], passphrase: str = "") -> str:
        """
        Validate a payload produced by generate_bundle and return the mnemonic.

        This defends against corrupted backups by verifying:
            - Format/version identifiers
            - Word count matches mnemonic content
            - SHA-256 checksum (mnemonic [+ passphrase]) matches stored checksum

        Args:
            payload: Structured payload dict (decoded JSON from QR)
            passphrase: Optional BIP-39 passphrase used during backup

        Returns:
            Normalized mnemonic phrase.

        Raises:
            ValueError: If the payload is malformed or checksum validation fails.
        """
        if payload.get("format") != self.FORMAT_NAME:
            raise ValueError("Unsupported mnemonic backup format")
        if payload.get("version") != self.FORMAT_VERSION:
            raise ValueError("Unsupported mnemonic backup version")

        mnemonic_phrase = payload.get("mnemonic", "")
        normalized = self._validate_mnemonic(mnemonic_phrase)

        expected_word_count = payload.get("word_count")
        if expected_word_count is not None and expected_word_count != len(normalized.split()):
            raise ValueError("Mnemonic word count mismatch")

        checksum = payload.get("checksum")
        if not checksum:
            raise ValueError("Backup payload missing checksum")
        computed_checksum = self._build_checksum(normalized, passphrase)
        if checksum != computed_checksum:
            raise ValueError("Mnemonic checksum mismatch")

        return normalized

    def _generate_qr_image(self, data: str) -> qrcode.QRCode:
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_Q,
            box_size=8,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr

    def _encode_png_base64(self, qr_obj: qrcode.QRCode) -> str:
        img = qr_obj.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _render_ascii(qr_obj: qrcode.QRCode) -> str:
        ascii_buffer = io.StringIO()
        qr_obj.print_ascii(out=ascii_buffer, invert=True)
        return ascii_buffer.getvalue()

    def generate_bundle(
        self,
        mnemonic_phrase: str,
        passphrase: str = "",
        include_passphrase: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QRBackupBundle:
        """
        Generate the full QR backup bundle for the supplied mnemonic.

        Returns:
            QRBackupBundle with payload dict, base64 PNG image, and ASCII art.
        """
        payload = self.build_payload(
            mnemonic_phrase,
            passphrase=passphrase,
            include_passphrase=include_passphrase,
            metadata=metadata,
        )
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        qr_obj = self._generate_qr_image(payload_json)
        return QRBackupBundle(
            payload=payload,
            image_base64=self._encode_png_base64(qr_obj),
            ascii_art=self._render_ascii(qr_obj),
        )
