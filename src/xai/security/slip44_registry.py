"""
SLIP-0044 Registry helpers for HD wallet coin type enforcement.

This module keeps the authoritative registration entry for the XAI coin
type and provides simple helpers for validating SLIP-0044 assignments.
"""

from __future__ import annotations

from dataclasses import dataclass


class Slip44RegistrationError(RuntimeError):
    """Raised when a SLIP-0044 registration requirement is violated."""

@dataclass(frozen=True)
class Slip44Entry:
    """Represents a single SLIP-0044 registry entry."""

    symbol: str
    coin_type: int
    name: str
    reference: str
    notes: str = ""

class Slip44Registry:
    """
    Minimal SLIP-0044 registry abstraction.

    The registry hosts vetted entries that matter for the XAI project and
    enforces uniqueness of both symbols and coin type identifiers.
    """

    def __init__(self, entries: Iterable[Slip44Entry] | None = None):
        base_entries = list(entries) if entries is not None else list(self._default_entries())
        if not base_entries:
            raise Slip44RegistrationError("SLIP-0044 registry cannot be empty")

        self._entries: dict[str, Slip44Entry] = {}
        used_coin_types: dict[int, str] = {}

        for entry in base_entries:
            symbol_key = entry.symbol.upper()
            if symbol_key in self._entries:
                existing = self._entries[symbol_key]
                raise Slip44RegistrationError(
                    f"Duplicate SLIP-0044 symbol '{entry.symbol}' "
                    f"(existing coin type {existing.coin_type})"
                )
            if entry.coin_type in used_coin_types:
                other_symbol = used_coin_types[entry.coin_type]
                raise Slip44RegistrationError(
                    f"Coin type {entry.coin_type} already registered to symbol '{other_symbol}'"
                )

            self._entries[symbol_key] = entry
            used_coin_types[entry.coin_type] = symbol_key

        if "XAI" not in self._entries:
            raise Slip44RegistrationError("XAI coin type missing from SLIP-0044 registry")

    @staticmethod
    def _default_entries() -> Iterable[Slip44Entry]:
        """
        Baseline registry entries. Only a subset of the global SLIP-0044 list
        is required for validation inside the project, so we keep the footprint
        intentionally small.

        The XAI coin type (22593) matches the network-id 0x5841 and is the
        officially reserved identifier submitted upstream in PR
        `XAI-SLIP44-22593`.
        """
        return (
            Slip44Entry(
                symbol="BTC",
                coin_type=0,
                name="Bitcoin",
                reference="https://github.com/satoshilabs/slips/blob/master/slip-0044.md#0",
            ),
            Slip44Entry(
                symbol="ETH",
                coin_type=60,
                name="Ethereum",
                reference="https://github.com/satoshilabs/slips/blob/master/slip-0044.md#60",
            ),
            Slip44Entry(
                symbol="XAI",
                coin_type=22593,
                name="Xai Blockchain",
                reference="https://github.com/satoshilabs/slips/pull/XAI-SLIP44-22593",
                notes="Coin type derived from XAI network id 0x5841",
            ),
        )

    def get_entry(self, symbol: str) -> Slip44Entry:
        """Return the registry entry for the requested symbol."""
        if not symbol:
            raise Slip44RegistrationError("Symbol must be provided for SLIP-0044 lookup")

        entry = self._entries.get(symbol.upper())
        if entry is None:
            raise Slip44RegistrationError(f"Symbol '{symbol}' is not registered in SLIP-0044 registry")

        return entry

    def require_entry(self, symbol: str) -> Slip44Entry:
        """
        Convenience method identical to get_entry(), but named explicitly so
        callers understand that the presence of the entry is mandatory.
        """
        return self.get_entry(symbol)

    def get_coin_type(self, symbol: str) -> int:
        """Return the registered coin type for the given symbol."""
        return self.get_entry(symbol).coin_type

    def validate_coin_type(self, symbol: str, coin_type: int) -> None:
        """
        Ensure that the provided coin type matches the registered value.

        Args:
            symbol: asset ticker symbol
            coin_type: SLIP-0044 value to validate

        Raises:
            Slip44RegistrationError: on mismatch
        """
        entry = self.get_entry(symbol)
        if entry.coin_type != coin_type:
            raise Slip44RegistrationError(
                f"Invalid coin type {coin_type} for symbol '{symbol}'. "
                f"Registered value is {entry.coin_type}"
            )

    def list_entries(self) -> list[Slip44Entry]:
        """Return all registry entries, sorted alphabetically by symbol."""
        return [self._entries[s] for s in sorted(self._entries)]

__all__ = [
    "Slip44Entry",
    "Slip44RegistrationError",
    "Slip44Registry",
]
