"""
XAI token unit helpers.

These helpers standardize 18-decimal XAI amounts and provide base-unit
(axai) conversions without relying on floats.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any

from xai.core.constants import TOKEN_DECIMALS, WEI_PER_TOKEN

_QUANTIZER = Decimal(f"1e-{TOKEN_DECIMALS}")


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float, str)):
        return Decimal(str(value))
    raise ValueError("Amount must be int, float, str, or Decimal")


def quantize_xai(value: Any) -> Decimal:
    """Convert to a Decimal XAI amount with 18-decimal precision."""
    try:
        dec = _to_decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid amount value: {value}") from exc

    if dec.is_nan():
        raise ValueError("Amount cannot be NaN")
    if dec.is_infinite():
        raise ValueError("Amount cannot be infinite")

    return dec.quantize(_QUANTIZER, rounding=ROUND_DOWN)


def to_base_units(value: Any) -> int:
    """Convert an XAI amount to base units (axai) as int."""
    dec = quantize_xai(value)
    if dec < 0:
        raise ValueError("Amount cannot be negative")
    return int((dec * Decimal(WEI_PER_TOKEN)).to_integral_value(rounding=ROUND_DOWN))


def from_base_units(value: int) -> Decimal:
    """Convert base units (axai) int to Decimal XAI amount."""
    if not isinstance(value, int):
        raise ValueError("Base units must be an int")
    return (Decimal(value) / Decimal(WEI_PER_TOKEN)).quantize(_QUANTIZER, rounding=ROUND_DOWN)


def format_xai(value: Any) -> str:
    """Format an amount as a fixed-precision XAI string."""
    return f"{quantize_xai(value):f}"
