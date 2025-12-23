"""
Watch-Only Wallet Store

Provides persistent tracking for watch-only addresses, including manual entries
and derivations from extended public keys (xpub). Enables operators to monitor
balances and history without storing private keys.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bip_utils import Bip32KeyError, Bip32Slip10Secp256k1

from xai.core.validation import AddressFormatValidator

logger = logging.getLogger(__name__)

DEFAULT_WATCH_STORE = Path(os.getenv("XAI_WATCH_STORE_PATH", Path.home() / ".xai" / "watch_only.json"))

class WatchOnlyWalletError(Exception):
    """Base class for watch-only wallet errors."""

class DuplicateWatchAddressError(WatchOnlyWalletError):
    """Raised when attempting to add an address that already exists."""

class WatchAddressNotFoundError(WatchOnlyWalletError):
    """Raised when attempting to remove or update an address that does not exist."""

class XpubDerivationError(WatchOnlyWalletError):
    """Raised when xpub-based derivation fails."""

def _utc_timestamp() -> str:
    """Return ISO8601 timestamp with Z suffix."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _public_key_hex_to_address(public_key_hex: str) -> str:
    """Convert uncompressed public key hex (without 0x04 prefix) to XAI address."""
    # Use network-appropriate prefix
    from xai.core.config import NETWORK
    prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
    pub_bytes = bytes.fromhex(public_key_hex)
    digest = hashlib.sha256(pub_bytes).hexdigest()
    return f"{prefix}{digest[:40]}"

@dataclass
class WatchAddressEntry:
    """Represents a single watch-only address entry."""

    address: str
    label: str | None = None
    notes: str | None = None
    tags: list[str] = field(default_factory=list)
    source: str = "manual"
    added_at: str = field(default_factory=_utc_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize entry to native dict."""
        return {
            "address": self.address,
            "label": self.label,
            "notes": self.notes,
            "tags": list(self.tags),
            "source": self.source,
            "added_at": self.added_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WatchAddressEntry":
        """Build entry from dictionary data."""
        return cls(
            address=payload["address"],
            label=payload.get("label"),
            notes=payload.get("notes"),
            tags=list(payload.get("tags", [])),
            source=payload.get("source", "manual"),
            added_at=payload.get("added_at", _utc_timestamp()),
            metadata=dict(payload.get("metadata", {})),
        )

class WatchOnlyWalletStore:
    """Persistent storage for watch-only addresses."""

    def __init__(
        self,
        store_path: Path | None = None,
        *,
        validator: AddressFormatValidator | None = None,
    ) -> None:
        self.store_path = Path(store_path or DEFAULT_WATCH_STORE).expanduser()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.validator = validator or AddressFormatValidator()
        self._entries: dict[str, WatchAddressEntry] = {}
        self._load()

    # ------------------------------------------------------------------ I/O --
    def _load(self) -> None:
        """Load store from disk."""
        if not self.store_path.exists():
            logger.debug("Watch-only store not found; initializing empty store at %s", self.store_path)
            self._entries = {}
            return
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WatchOnlyWalletError(f"Failed to read watch-only store: {exc}") from exc
        entries = data.get("addresses", [])
        loaded: dict[str, WatchAddressEntry] = {}
        for entry_data in entries:
            try:
                entry = WatchAddressEntry.from_dict(entry_data)
                normalized = self.validator.validate(entry.address)
                entry.address = normalized
                loaded[normalized] = entry
            except ValueError as exc:
                logger.warning("Skipping invalid watch-only entry: %s", exc)
        self._entries = loaded

    def _persist(self) -> None:
        """Persist the current store to disk atomically."""
        payload = {"version": 1, "addresses": [entry.to_dict() for entry in self._entries.values()]}
        tmp_path = self.store_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.store_path)

    # ------------------------------------------------------------- operations --
    def list_addresses(self, *, tags: Sequence[str] | None = None) -> list[WatchAddressEntry]:
        """Return all watch-only addresses, optionally filtered by tags."""
        entries = list(self._entries.values())
        if tags:
            normalized = {tag.lower() for tag in tags}
            entries = [
                entry for entry in entries if normalized.intersection({t.lower() for t in entry.tags})
            ]
        return sorted(entries, key=lambda e: e.added_at)

    def add_address(
        self,
        address: str,
        *,
        label: str | None = None,
        notes: str | None = None,
        tags: Iterable[str] | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "manual",
    ) -> WatchAddressEntry:
        """Add a watch-only address to the store."""
        normalized = self.validator.validate(address)
        if normalized in self._entries:
            raise DuplicateWatchAddressError(f"Address {normalized} already present in watch-only store")
        entry = WatchAddressEntry(
            address=normalized,
            label=label,
            notes=notes,
            tags=list(tags or []),
            source=source,
            metadata=dict(metadata or {}),
        )
        self._entries[normalized] = entry
        self._persist()
        logger.info("Added watch-only address %s (source=%s)", normalized, source)
        return entry

    def remove_address(self, address: str) -> WatchAddressEntry:
        """Remove an address from the store."""
        normalized = self.validator.validate(address)
        try:
            entry = self._entries.pop(normalized)
        except KeyError:
            raise WatchAddressNotFoundError(f"Address {normalized} not found in watch-only store") from None
        self._persist()
        logger.info("Removed watch-only address %s", normalized)
        return entry

    def add_addresses(self, entries: Sequence[WatchAddressEntry]) -> list[WatchAddressEntry]:
        """Bulk add addresses (assumes each entry already validated)."""
        added: list[WatchAddressEntry] = []
        for entry in entries:
            normalized = self.validator.validate(entry.address)
            if normalized in self._entries:
                logger.info("Skipping duplicate watch-only address %s", normalized)
                continue
            entry.address = normalized
            self._entries[normalized] = entry
            added.append(entry)
        if added:
            self._persist()
        return added

    # --------------------------------------------------------- xpub support --
    def add_from_xpub(
        self,
        xpub: str,
        *,
        change: int = 0,
        start_index: int = 0,
        count: int = 5,
        label: str | None = None,
        notes: str | None = None,
        tags: Iterable[str] | None = None,
    ) -> list[WatchAddressEntry]:
        """
        Derive watch-only addresses from an extended public key.

        Args:
            xpub: Extended public key (BIP32)
            change: Change chain (0=receiving, 1=change)
            start_index: Starting address index
            count: Number of sequential addresses to derive
            label: Optional label applied to each entry
            notes: Optional notes metadata
            tags: Optional set of tags

        Returns:
            List of newly added entries
        """
        if change not in (0, 1):
            raise ValueError("Change must be 0 (receiving) or 1 (change)")
        if start_index < 0 or count <= 0:
            raise ValueError("start_index must be >=0 and count must be >0")

        try:
            account_node = Bip32Slip10Secp256k1.FromExtendedKey(xpub)
        except (ValueError, Bip32KeyError) as exc:
            raise XpubDerivationError(f"Invalid xpub provided: {exc}") from exc

        derived_entries: list[WatchAddressEntry] = []
        try:
            change_node = account_node.ChildKey(change)
        except Bip32KeyError as exc:
            raise XpubDerivationError(f"Unable to derive change chain {change}: {exc}") from exc

        for offset in range(count):
            index = start_index + offset
            try:
                child = change_node.ChildKey(index)
            except Bip32KeyError as exc:
                raise XpubDerivationError(f"Unable to derive child {index}: {exc}") from exc
            pub_hex = child.PublicKey().RawUncompressed().ToHex()
            if pub_hex.startswith("04"):
                pub_hex = pub_hex[2:]
            address = _public_key_hex_to_address(pub_hex)
            metadata = {
                "xpub": xpub,
                "change": change,
                "index": index,
                "derivation_path": f"{change}/{index}",
            }
            entry = WatchAddressEntry(
                address=address,
                label=label,
                notes=notes,
                tags=list(tags or []),
                source="xpub",
                metadata=metadata,
            )
            derived_entries.append(entry)

        added = self.add_addresses(derived_entries)
        if not added:
            logger.info("No new addresses derived from xpub (all duplicates)")
        return added

__all__ = [
    "WatchOnlyWalletStore",
    "WatchOnlyWalletError",
    "DuplicateWatchAddressError",
    "WatchAddressNotFoundError",
    "XpubDerivationError",
    "WatchAddressEntry",
]
