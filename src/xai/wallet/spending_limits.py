"""
Per-address daily spending limits for non-AA wallets.

This module persists spend history under ~/.xai/spending_limits.json and enforces
configurable daily caps. It complements the account-abstraction session key
spending limits by protecting simple wallet flows at the API layer.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_LIMIT_PER_DAY = float(os.getenv("XAI_DAILY_SPEND_LIMIT", "1000000"))  # 1,000,000 units default
STATE_PATH = os.path.expanduser("~/.xai/spending_limits.json")

def _today_key(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts or datetime.now(tz=timezone.utc).timestamp(), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")

@dataclass
class SpendingState:
    limits: dict[str, float]
    usage: dict[str, dict[str, float]]  # address -> {YYYY-MM-DD: amount}

class SpendingLimitManager:
    def __init__(self, path: str = STATE_PATH, default_limit: float = DEFAULT_LIMIT_PER_DAY) -> None:
        self.path = path
        self.default_limit = float(default_limit)
        self.state = self._load()

    def _load(self) -> SpendingState:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return SpendingState(limits=data.get("limits", {}), usage=data.get("usage", {}))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "Failed to load spending limits state, using defaults",
                    extra={"error": str(e), "path": self.path, "event": "spending_limits.load_failed", "error_type": type(e).__name__}
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    "Invalid spending limits data format, using defaults",
                    extra={"error": str(e), "path": self.path, "event": "spending_limits.invalid_format", "error_type": type(e).__name__}
                )
        return SpendingState(limits={}, usage={})

    def _save(self) -> None:
        data = {"limits": self.state.limits, "usage": self.state.usage}
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except OSError as e:
            # File I/O failures should not crash API
            logger.warning(
                "Failed to persist spending limits to disk",
                extra={
                    "path": self.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event": "spending_limits.save_failed"
                }
            )
        except (TypeError, ValueError) as e:
            # Data serialization failures
            logger.error(
                "Invalid data format for spending limits persistence",
                extra={
                    "path": self.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event": "spending_limits.serialization_error"
                }
            )

    def set_limit(self, address: str, amount_per_day: float) -> None:
        self.state.limits[address.lower()] = float(amount_per_day)
        self._save()

    def get_limit(self, address: str) -> float:
        return float(self.state.limits.get(address.lower(), self.default_limit))

    def get_usage(self, address: str, day_key: str | None = None) -> float:
        day = day_key or _today_key(None)
        return float(self.state.usage.get(address.lower(), {}).get(day, 0.0))

    def can_spend(self, address: str, amount: float, ts: float | None = None) -> tuple[bool, float, float]:
        day = _today_key(ts)
        limit = self.get_limit(address)
        used = float(self.state.usage.get(address.lower(), {}).get(day, 0.0))
        return (used + amount) <= limit, used, limit

    def record_spend(self, address: str, amount: float, ts: float | None = None) -> None:
        day = _today_key(ts)
        addr = address.lower()
        if addr not in self.state.usage:
            self.state.usage[addr] = {}
        self.state.usage[addr][day] = float(self.state.usage[addr].get(day, 0.0)) + float(amount)
        self._save()

