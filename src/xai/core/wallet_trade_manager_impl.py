"""Fully featured wallet trade manager implementation."""

from __future__ import annotations

import json
import os
import time
import uuid
import secrets
import threading
import hmac
import hashlib
import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Tuple, Optional, List, Sequence

from xai.core.trading import SwapOrderType, TradeMatchStatus
from xai.core.nonce_tracker import NonceTracker
from xai.core.margin_engine import MarginEngine, MarginException, Position


DATA_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "data", "wallet_trades")
STATE_FILE = "state.json"
AUDIT_SECRET_FILE = "audit_secret"
MAX_HISTORY = 500
MATCH_STATUS_OPEN = "open"


def _ensure_directory(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _now() -> float:
    return time.time()


@dataclass
class WalletTradeOrder:
    """Represents a wallet-level peer trade order."""

    order_id: str
    maker_address: str
    token_offered: str
    amount_offered: float
    token_requested: str
    amount_requested: float
    price: float
    order_type: SwapOrderType
    stop_price: Optional[float] = None
    max_slippage_bps: Optional[int] = None
    trail_amount: Optional[float] = None
    iceberg_total: Optional[float] = None
    iceberg_peak: Optional[float] = None
    status: str = MATCH_STATUS_OPEN
    remaining_offered: float = field(default=0.0)
    remaining_requested: float = field(default=0.0)
    displayed_offered: float = field(default=0.0)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    stop_triggered: bool = field(default=True, init=False)
    highest_price_seen: Optional[float] = field(default=None, init=False)
    lowest_price_seen: Optional[float] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.amount_offered <= 0:
            raise ValueError("amount_offered must be greater than zero")
        if self.amount_requested <= 0:
            raise ValueError("amount_requested must be greater than zero")
        if self.remaining_offered == 0:
            self.remaining_offered = self.amount_offered
        if self.remaining_requested == 0:
            self.remaining_requested = self.amount_requested
        if self.iceberg_total is not None or self.iceberg_peak is not None:
            if self.iceberg_total is None or self.iceberg_peak is None:
                raise ValueError("iceberg_total and iceberg_peak must both be provided")
            self.iceberg_total = float(self.iceberg_total)
            self.iceberg_peak = float(self.iceberg_peak)
            if self.iceberg_total <= 0 or self.iceberg_peak <= 0:
                raise ValueError("iceberg settings must be positive")
            if self.iceberg_peak > self.iceberg_total:
                raise ValueError("iceberg_peak cannot exceed iceberg_total")
            if self.iceberg_total > self.amount_offered + 1e-12:
                raise ValueError("iceberg_total cannot exceed amount_offered")
            self.displayed_offered = min(self.iceberg_peak, self.remaining_offered)
        else:
            self.displayed_offered = self.remaining_offered
        self.price = float(self.price)
        if self.price <= 0 or not math.isfinite(self.price):
            raise ValueError("price must be a finite positive number")
        if self.stop_price is not None:
            self.stop_price = float(self.stop_price)
            if self.stop_price <= 0 or not math.isfinite(self.stop_price):
                raise ValueError("stop_price must be a finite positive number")
            if self.order_type == SwapOrderType.BUY and self.stop_price < self.price:
                raise ValueError("BUY stop price must be >= limit price")
            if self.order_type == SwapOrderType.SELL and self.stop_price > self.price:
                raise ValueError("SELL stop price must be <= limit price")
            # Determine if already triggered based on current limit price
            if self.order_type == SwapOrderType.BUY:
                self.stop_triggered = self.price >= self.stop_price
            else:
                self.stop_triggered = self.price <= self.stop_price
        else:
            self.stop_triggered = True
        if self.max_slippage_bps is not None:
            try:
                normalized_slippage = int(self.max_slippage_bps)
            except (TypeError, ValueError) as exc:
                raise ValueError("max_slippage_bps must be an integer") from exc
            if normalized_slippage <= 0:
                raise ValueError("max_slippage_bps must be greater than zero")
            self.max_slippage_bps = normalized_slippage
        if self.trail_amount is not None:
            if self.stop_price is None:
                raise ValueError("trail_amount requires stop_price")
            self.trail_amount = float(self.trail_amount)
            if self.trail_amount <= 0 or not math.isfinite(self.trail_amount):
                raise ValueError("trail_amount must be a positive finite number")
            if self.order_type == SwapOrderType.BUY:
                self.lowest_price_seen = self.price
            else:
                self.highest_price_seen = self.price

    @property
    def exchange_rate(self) -> float:
        if self.amount_offered == 0:
            return 0.0
        return self.amount_requested / self.amount_offered

    def fill(self, offered_delta: float, requested_delta: float) -> None:
        self.remaining_offered = max(self.remaining_offered - offered_delta, 0.0)
        self.remaining_requested = max(self.remaining_requested - requested_delta, 0.0)
        self.updated_at = _now()
        if self.remaining_offered <= 1e-9 or self.remaining_requested <= 1e-9:
            self.status = "filled"
        else:
            self.status = "partial"
        if self.iceberg_total is not None:
            hidden_left = max(self.remaining_offered - self.displayed_offered, 0.0)
            if hidden_left > 0:
                replenish = min(self.iceberg_peak, self.remaining_offered)
                self.displayed_offered = replenish

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "maker_address": self.maker_address,
            "token_offered": self.token_offered,
            "amount_offered": self.amount_offered,
            "token_requested": self.token_requested,
            "amount_requested": self.amount_requested,
            "price": self.price,
            "stop_price": self.stop_price,
            "max_slippage_bps": self.max_slippage_bps,
            "trail_amount": self.trail_amount,
            "iceberg_total": self.iceberg_total,
            "iceberg_peak": self.iceberg_peak,
            "displayed_offered": self.displayed_offered,
            "stop_triggered": self.stop_triggered,
            "order_type": self.order_type.value,
            "status": self.status,
            "remaining_offered": self.remaining_offered,
            "remaining_requested": self.remaining_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletTradeOrder":
        order = cls(
            order_id=data["order_id"],
            maker_address=data["maker_address"],
            token_offered=data["token_offered"],
            amount_offered=data["amount_offered"],
            token_requested=data["token_requested"],
            amount_requested=data["amount_requested"],
            price=data["price"],
            stop_price=data.get("stop_price"),
            max_slippage_bps=data.get("max_slippage_bps"),
            trail_amount=data.get("trail_amount"),
            iceberg_total=data.get("iceberg_total"),
            iceberg_peak=data.get("iceberg_peak"),
            order_type=SwapOrderType(data["order_type"]),
            status=data.get("status", MATCH_STATUS_OPEN),
            remaining_offered=data.get("remaining_offered", data["amount_offered"]),
            remaining_requested=data.get("remaining_requested", data["amount_requested"]),
            created_at=data.get("created_at", _now()),
            updated_at=data.get("updated_at", _now()),
        )
        order.stop_triggered = data.get("stop_triggered", order.stop_price is None or order.stop_triggered)
        order.displayed_offered = data.get("displayed_offered", order.displayed_offered)
        order.highest_price_seen = data.get("highest_price_seen")
        order.lowest_price_seen = data.get("lowest_price_seen")
        return order


@dataclass
class WalletTradeMatch:
    """Represents a matched trade awaiting settlement."""

    match_id: str
    maker_order_id: str
    taker_order_id: str
    maker_amount: float
    taker_amount: float
    maker_token: str
    taker_token: str
    secret: str
    status: TradeMatchStatus = TradeMatchStatus.MATCHED
    created_at: float = field(default_factory=_now)
    settled_at: Optional[float] = None
    maker_fee: float = 0.0
    taker_fee: float = 0.0
    maker_net_amount: float = 0.0
    taker_net_amount: float = 0.0
    maker_fee_bps: int = 0
    taker_fee_bps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "maker_amount": self.maker_amount,
            "taker_amount": self.taker_amount,
            "maker_token": self.maker_token,
            "taker_token": self.taker_token,
            "secret": self.secret,
            "status": self.status.value,
            "created_at": self.created_at,
            "settled_at": self.settled_at,
            "maker_fee": self.maker_fee,
            "taker_fee": self.taker_fee,
            "maker_net_amount": self.maker_net_amount,
            "taker_net_amount": self.taker_net_amount,
            "maker_fee_bps": self.maker_fee_bps,
            "taker_fee_bps": self.taker_fee_bps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletTradeMatch":
        return cls(
            match_id=data["match_id"],
            maker_order_id=data["maker_order_id"],
            taker_order_id=data["taker_order_id"],
            maker_amount=data["maker_amount"],
            taker_amount=data["taker_amount"],
            maker_token=data["maker_token"],
            taker_token=data["taker_token"],
            secret=data["secret"],
            status=TradeMatchStatus(data.get("status", TradeMatchStatus.MATCHED.value)),
            created_at=data.get("created_at", _now()),
            settled_at=data.get("settled_at"),
            maker_fee=data.get("maker_fee", 0.0),
            taker_fee=data.get("taker_fee", 0.0),
            maker_net_amount=data.get("maker_net_amount", 0.0),
            taker_net_amount=data.get("taker_net_amount", 0.0),
            maker_fee_bps=int(data.get("maker_fee_bps", 0)),
            taker_fee_bps=int(data.get("taker_fee_bps", 0)),
        )


class SettlementResult(dict):
    """Dictionary-like response that exposes settlement status as an attribute."""

    def __init__(self, payload: Dict[str, Any], status: TradeMatchStatus):
        super().__init__(payload)
        self._status = status

    @property
    def status(self) -> TradeMatchStatus:
        return self._status


class AuditSigner:
    """Provides deterministic signing for gossip batches."""

    def __init__(self, secret: Optional[str] = None):
        self._secret = secret or secrets.token_hex(32)
        self._public = hashlib.sha256(self._secret.encode()).hexdigest()

    def public_key(self) -> str:
        return self._public

    def sign(self, payload: Dict[str, Any]) -> str:
        message = json.dumps(payload, sort_keys=True).encode()
        digest = hmac.new(self._secret.encode(), message, hashlib.sha256).hexdigest()
        return digest

    def serialize(self) -> str:
        return self._secret

    @classmethod
    def from_file(cls, path: str) -> "AuditSigner":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                secret = handle.read().strip()
                if secret:
                    return cls(secret)
        signer = cls()
        _ensure_directory(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(signer.serialize())
        return signer


class OrderRateLimitError(Exception):
    """Raised when a wallet exceeds the configured order submission rate."""


class WalletTradeManager:
    """Stateful trade manager used by wallet APIs."""

    def __init__(
        self,
        exchange_wallet_manager: Optional[Any] = None,
        data_dir: Optional[str] = None,
        nonce_tracker: Optional[NonceTracker] = None,
        margin_engine: Optional[MarginEngine] = None,
        *,
        maker_fee_bps: int = 10,
        taker_fee_bps: int = 20,
        fee_collector_address: str = "XAI_FEE_TREASURY",
        order_limit_per_minute: int = 30,
        order_limit_window_seconds: int = 60,
    ) -> None:
        self.data_dir = _ensure_directory(data_dir or DATA_DIR_DEFAULT)
        self.state_file = os.path.join(self.data_dir, STATE_FILE)
        self.audit_signer = AuditSigner.from_file(os.path.join(self.data_dir, AUDIT_SECRET_FILE))
        self.exchange_wallet_manager = exchange_wallet_manager
        self.nonce_tracker = nonce_tracker or NonceTracker()
        self.margin_engine = margin_engine
        self.maker_fee_bps = int(maker_fee_bps) if maker_fee_bps is not None else 0
        self.taker_fee_bps = int(taker_fee_bps) if taker_fee_bps is not None else 0
        if self.maker_fee_bps < 0 or self.taker_fee_bps < 0:
            raise ValueError("maker_fee_bps and taker_fee_bps must be non-negative")
        self.fee_collector_address = fee_collector_address
        self.order_limit_per_minute = int(order_limit_per_minute) if order_limit_per_minute is not None else 0
        self.order_limit_window_seconds = int(order_limit_window_seconds) if order_limit_window_seconds is not None else 60
        if self.order_limit_per_minute < 0:
            raise ValueError("order_limit_per_minute must be non-negative")
        if self.order_limit_window_seconds <= 0:
            raise ValueError("order_limit_window_seconds must be positive")
        self.orders: Dict[str, WalletTradeOrder] = {}
        self.matches: Dict[str, WalletTradeMatch] = {}
        self.event_log: List[Dict[str, Any]] = []
        self.handshakes: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.twap_schedules: Dict[str, Dict[str, Any]] = {}
        self._order_activity: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.RLock()
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            self.orders = {}
            for item in data.get("orders", []):
                try:
                    order = WalletTradeOrder.from_dict(item)
                except (KeyError, ValueError) as exc:
                    logger.warning(
                        "Skipping invalid wallet trade order during load",
                        extra={"event": "wallet_trade.invalid_order", "error": str(exc)},
                    )
                    continue
                self.orders[order.order_id] = order

            self.matches = {
                item["match_id"]: WalletTradeMatch.from_dict(item)
                for item in data.get("matches", [])
            }
            self.event_log = data.get("events", [])[-MAX_HISTORY:]
            self.handshakes = data.get("handshakes", {})
            self.sessions = data.get("sessions", {})
            self.twap_schedules = {
                entry["schedule_id"]: entry
                for entry in data.get("twap_schedules", [])
                if "schedule_id" in entry
            }
        except (json.JSONDecodeError, OSError):
            self.orders = {}
            self.matches = {}
            self.event_log = []
            self.handshakes = {}
            self.sessions = {}
            self.twap_schedules = {}

    def _save_state(self) -> None:
        data = {
            "orders": [order.to_dict() for order in self.orders.values()],
            "matches": [match.to_dict() for match in self.matches.values()],
            "events": self.event_log[-MAX_HISTORY:],
            "handshakes": self.handshakes,
            "sessions": self.sessions,
            "twap_schedules": list(self.twap_schedules.values()),
        }
        with open(self.state_file, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    # ------------------------------------------------------------------
    # Session / handshake lifecycle
    # ------------------------------------------------------------------
    def begin_walletconnect_handshake(self, wallet_address: str) -> Dict[str, Any]:
        with self.lock:
            handshake_id = str(uuid.uuid4())
            uri_key = secrets.token_hex(16)
            record = {
                "wallet_address": wallet_address,
                "handshake_id": handshake_id,
                "uri": f"wc:{handshake_id}@1?bridge=https://bridge.xai.io&key={uri_key}",
                "created_at": _now(),
            }
            self.handshakes[handshake_id] = record
            self._save_state()
            return {"success": True, **record}

    def complete_walletconnect_handshake(
        self, handshake_id: str, wallet_address: str, client_public: str
    ) -> Dict[str, Any]:
        with self.lock:
            record = self.handshakes.get(handshake_id)
            if not record or record["wallet_address"] != wallet_address:
                return {"success": False, "error": "invalid_handshake"}

            session_token = secrets.token_urlsafe(32)
            session = {
                "session_token": session_token,
                "wallet_address": wallet_address,
                "client_public": client_public,
                "created_at": _now(),
                "expires_at": _now() + 3600,
            }
            self.sessions[session_token] = session
            self.handshakes.pop(handshake_id, None)
            self._save_state()
            return {"success": True, **session}

    def register_session(self, wallet_address: str) -> Dict[str, Any]:
        with self.lock:
            session_token = secrets.token_urlsafe(24)
            session = {
                "session_token": session_token,
                "wallet_address": wallet_address,
                "created_at": _now(),
                "expires_at": _now() + 900,
            }
            self.sessions[session_token] = session
            self._save_state()
            return session

    # ------------------------------------------------------------------
    # Order workflow
    # ------------------------------------------------------------------
    def attach_exchange_manager(self, manager: Any) -> None:
        with self.lock:
            self.exchange_wallet_manager = manager

    def attach_margin_engine(self, engine: MarginEngine) -> None:
        with self.lock:
            self.margin_engine = engine

    def place_order(
        self,
        maker_address: str,
        token_offered: str,
        amount_offered: float,
        token_requested: str,
        amount_requested: float,
        price: float,
        order_type: SwapOrderType,
        stop_price: Optional[float] = None,
        max_slippage_bps: Optional[int] = None,
        trail_amount: Optional[float] = None,
        iceberg_total: Optional[float] = None,
        iceberg_peak: Optional[float] = None,
    ) -> Tuple[WalletTradeOrder, List[WalletTradeMatch]]:
        order = WalletTradeOrder(
            order_id=str(uuid.uuid4()),
            maker_address=maker_address,
            token_offered=token_offered,
            amount_offered=float(amount_offered),
            token_requested=token_requested,
            amount_requested=float(amount_requested),
            price=float(price),
            order_type=order_type,
            stop_price=stop_price,
            max_slippage_bps=max_slippage_bps,
            trail_amount=trail_amount,
            iceberg_total=iceberg_total,
            iceberg_peak=iceberg_peak,
        )
        matches: List[WalletTradeMatch] = []
        with self.lock:
            self._enforce_rate_limit(order.maker_address)
            self.orders[order.order_id] = order
            matches = self._match_order(order)
            self._save_state()
        return order, matches

    def _enforce_rate_limit(self, maker_address: str) -> None:
        if self.order_limit_per_minute == 0:
            return
        now = _now()
        activity = self._order_activity[maker_address]
        window_start = now - self.order_limit_window_seconds
        while activity and activity[0] < window_start:
            activity.popleft()
        if len(activity) >= self.order_limit_per_minute:
            logger.warning(
                "wallet order rate limit exceeded",
                extra={
                    "event": "wallet_trade.rate_limit_hit",
                    "maker_address": maker_address,
                    "limit_per_minute": self.order_limit_per_minute,
                },
            )
            raise OrderRateLimitError("order_rate_limit_exceeded")
        activity.append(now)

    def _match_order(self, taker_order: WalletTradeOrder) -> List[WalletTradeMatch]:
        matched: List[WalletTradeMatch] = []
        for candidate in self.orders.values():
            if candidate.order_id == taker_order.order_id:
                continue
            if candidate.status != MATCH_STATUS_OPEN:
                continue
            if not self._orders_compatible(candidate, taker_order):
                continue
            if not self._slippage_respected(candidate, taker_order.price):
                continue
            if not self._slippage_respected(taker_order, candidate.price):
                continue

            maker_depth = candidate.displayed_offered if candidate.iceberg_total else candidate.remaining_offered
            maker_token_amount = min(maker_depth, taker_order.remaining_requested)
            if maker_token_amount <= 0:
                continue

            quote_needed = maker_token_amount * candidate.exchange_rate
            if taker_order.remaining_offered < quote_needed:
                scale = taker_order.remaining_offered / quote_needed
                maker_token_amount *= scale
                quote_needed = maker_token_amount * candidate.exchange_rate

            if maker_token_amount <= 0 or quote_needed <= 0:
                continue

            candidate.fill(maker_token_amount, quote_needed)
            taker_order.fill(quote_needed, maker_token_amount)

            maker_fee = self._calculate_fee_amount(maker_token_amount, self.maker_fee_bps)
            taker_fee = self._calculate_fee_amount(quote_needed, self.taker_fee_bps)
            maker_net = max(maker_token_amount - maker_fee, 0.0)
            taker_net = max(quote_needed - taker_fee, 0.0)

            match = WalletTradeMatch(
                match_id=str(uuid.uuid4()),
                maker_order_id=candidate.order_id,
                taker_order_id=taker_order.order_id,
                maker_amount=maker_token_amount,
                taker_amount=quote_needed,
                maker_token=candidate.token_offered,
                taker_token=taker_order.token_offered,
                secret=secrets.token_hex(32),
                maker_fee=maker_fee,
                taker_fee=taker_fee,
                maker_net_amount=maker_net,
                taker_net_amount=taker_net,
                maker_fee_bps=self.maker_fee_bps,
                taker_fee_bps=self.taker_fee_bps,
            )
            self.matches[match.match_id] = match
            matched.append(match)
            self._record_event(
                "match_created",
                {
                    "match_id": match.match_id,
                    "maker_order_id": candidate.order_id,
                    "taker_order_id": taker_order.order_id,
                    "maker_fee": match.maker_fee,
                    "taker_fee": match.taker_fee,
                },
            )

            if taker_order.status == "filled":
                break
        return matched

    def _orders_compatible(self, maker: WalletTradeOrder, taker: WalletTradeOrder) -> bool:
        if maker.token_offered != taker.token_requested:
            return False
        if maker.token_requested != taker.token_offered:
            return False
        if not self._ensure_stop_triggered(maker, taker.price):
            return False
        if not self._ensure_stop_triggered(taker, maker.price):
            return False
        if maker.order_type == taker.order_type:
            return False
        maker_rate = maker.exchange_rate
        taker_rate = taker.exchange_rate
        if maker_rate <= 0 or taker_rate <= 0:
            return False
        if maker.max_slippage_bps is None and taker.max_slippage_bps is None:
            price_tolerance = max(1e-8, maker.price * 0.0001)
            if abs(maker.price - taker.price) > price_tolerance:
                return False
        tolerance = 0.0001
        reciprocal = 1 / taker_rate
        return abs(maker_rate - reciprocal) <= tolerance

    def _slippage_respected(self, order: WalletTradeOrder, execution_price: Optional[float]) -> bool:
        if order.max_slippage_bps is None:
            return True
        if execution_price is None or not math.isfinite(execution_price):
            return False
        reference = order.price
        if reference <= 0:
            return True
        delta = abs(execution_price - reference)
        observed_bps = (delta / reference) * 10000
        return observed_bps <= order.max_slippage_bps

    def _ensure_stop_triggered(self, order: WalletTradeOrder, observed_price: Optional[float]) -> bool:
        if order.stop_price is None:
            return True
        if order.stop_triggered:
            return True
        if observed_price is None or not math.isfinite(observed_price):
            return False
        if order.trail_amount is not None:
            if order.order_type == SwapOrderType.BUY:
                if order.lowest_price_seen is None or observed_price < order.lowest_price_seen:
                    order.lowest_price_seen = observed_price
                order.stop_price = (order.lowest_price_seen or order.stop_price) + order.trail_amount
            else:
                if order.highest_price_seen is None or observed_price > order.highest_price_seen:
                    order.highest_price_seen = observed_price
                order.stop_price = max(0.0, (order.highest_price_seen or order.stop_price) - order.trail_amount)
        if order.order_type == SwapOrderType.BUY and observed_price >= order.stop_price:
            order.stop_triggered = True
            return True
        if order.order_type == SwapOrderType.SELL and observed_price <= order.stop_price:
            order.stop_triggered = True
            return True
        return False

    def _calculate_fee_amount(self, amount: float, fee_bps: int) -> float:
        if amount <= 0 or fee_bps <= 0:
            return 0.0
        return amount * (fee_bps / 10000.0)

    def _require_margin_engine(self) -> MarginEngine:
        if not self.margin_engine:
            raise MarginException("margin_engine_unavailable")
        return self.margin_engine

    @staticmethod
    def _decimal_to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    def _serialize_margin_position(self, position: Position) -> Dict[str, Any]:
        return {
            "asset": position.asset,
            "size": self._decimal_to_float(position.size),
            "entry_price": self._decimal_to_float(position.entry_price),
            "isolated": position.isolated,
            "leverage": self._decimal_to_float(position.leverage),
            "margin": self._decimal_to_float(position.margin),
            "realized_pnl": self._decimal_to_float(position.realized_pnl),
        }

    def _serialize_margin_overview(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        return {key: self._decimal_to_float(val) for key, val in overview.items()}

    def margin_deposit(self, account_id: str, amount: float) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                engine.deposit(account_id, amount)
                overview = self._serialize_margin_overview(engine.account_overview(account_id))
                return {"success": True, "overview": overview}
            except MarginException as exc:
                logger.warning(
                    "MarginException in margin_deposit",
                    error_type="MarginException",
                    error=str(exc),
                    function="margin_deposit",
                )
                return {"success": False, "error": str(exc)}

    def margin_withdraw(self, account_id: str, amount: float) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                engine.withdraw(account_id, amount)
                overview = self._serialize_margin_overview(engine.account_overview(account_id))
                return {"success": True, "overview": overview}
            except MarginException as exc:
                logger.warning(
                    "MarginException in margin_withdraw",
                    error_type="MarginException",
                    error=str(exc),
                    function="margin_withdraw",
                )
                return {"success": False, "error": str(exc)}

    def open_margin_position(
        self,
        account_id: str,
        asset: str,
        size: float,
        *,
        isolated: bool = False,
        leverage: Optional[float] = None,
        mark_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                position = engine.open_position(
                    account_id,
                    asset,
                    size,
                    isolated=isolated,
                    leverage=leverage,
                    mark_price=mark_price,
                )
                return {
                    "success": True,
                    "position": self._serialize_margin_position(position),
                }
            except MarginException as exc:
                logger.warning(
                    "MarginException in open_margin_position",
                    error_type="MarginException",
                    error=str(exc),
                    function="open_margin_position",
                )
                return {"success": False, "error": str(exc)}

    def close_margin_position(
        self,
        account_id: str,
        asset: str,
        size: Optional[float] = None,
        mark_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                result = engine.close_position(
                    account_id,
                    asset,
                    size=size,
                    mark_price=mark_price,
                )
                return {
                    "success": True,
                    "result": {k: self._decimal_to_float(v) for k, v in result.items()},
                }
            except MarginException as exc:
                logger.warning(
                    "MarginException in close_margin_position",
                    error_type="MarginException",
                    error=str(exc),
                    function="close_margin_position",
                )
                return {"success": False, "error": str(exc)}

    def get_margin_overview(self, account_id: str) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                overview = engine.account_overview(account_id)
                positions = [
                    self._serialize_margin_position(position)
                    for position in engine.get_positions(account_id).values()
                ]
                return {
                    "success": True,
                    "overview": self._serialize_margin_overview(overview),
                    "positions": positions,
                }
            except MarginException as exc:
                logger.warning(
                    "MarginException in get_margin_overview",
                    error_type="MarginException",
                    error=str(exc),
                    function="get_margin_overview",
                )
                return {"success": False, "error": str(exc)}

    def perform_margin_liquidations(self) -> Dict[str, Any]:
        with self.lock:
            try:
                engine = self._require_margin_engine()
                liquidated = engine.perform_liquidations()
                return {"success": True, "liquidated_accounts": liquidated}
            except MarginException as exc:
                logger.warning(
                    "MarginException in perform_margin_liquidations",
                    error_type="MarginException",
                    error=str(exc),
                    function="perform_margin_liquidations",
                )
                return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Advanced order types (TWAP / VWAP)
    # ------------------------------------------------------------------
    def create_twap_order(
        self,
        maker_address: str,
        token_offered: str,
        amount_offered: float,
        token_requested: str,
        amount_requested: float,
        price: float,
        order_type: SwapOrderType,
        *,
        slice_count: int,
        duration_seconds: float,
        stop_price: Optional[float] = None,
        max_slippage_bps: Optional[int] = None,
    ) -> Dict[str, Any]:
        if slice_count <= 0:
            raise ValueError("slice_count must be positive")
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        interval = duration_seconds / slice_count
        slice_offered = amount_offered / slice_count
        if slice_offered <= 0:
            raise ValueError("slice amount must be positive")
        ratio = amount_requested / amount_offered
        schedule_id = str(uuid.uuid4())
        schedule = {
            "schedule_id": schedule_id,
            "maker_address": maker_address,
            "token_offered": token_offered,
            "token_requested": token_requested,
            "price": price,
            "order_type": order_type.value if isinstance(order_type, SwapOrderType) else order_type,
            "stop_price": stop_price,
            "max_slippage_bps": max_slippage_bps,
            "remaining_slices": slice_count,
            "interval_seconds": interval,
            "next_execution": _now(),
            "slice_offered": slice_offered,
            "remaining_offered": amount_offered,
            "price_ratio": ratio,
        }
        with self.lock:
            self.twap_schedules[schedule_id] = schedule
            self._save_state()
        return {"success": True, "schedule_id": schedule_id, "remaining_slices": slice_count}

    def process_twap_schedules(self, limit: Optional[int] = None) -> List[str]:
        due_slices: List[Dict[str, Any]] = []
        with self.lock:
            now = _now()
            scheduled_ids = sorted(
                self.twap_schedules.keys(),
                key=lambda sid: self.twap_schedules[sid]["next_execution"],
            )
            for schedule_id in scheduled_ids:
                if limit is not None and len(due_slices) >= limit:
                    break
                schedule = self.twap_schedules.get(schedule_id)
                if not schedule or schedule["next_execution"] > now:
                    continue
                remaining_slices = schedule["remaining_slices"]
                if remaining_slices <= 0:
                    self.twap_schedules.pop(schedule_id, None)
                    continue
                offered = schedule["slice_offered"]
                if remaining_slices == 1:
                    offered = schedule["remaining_offered"]
                schedule["remaining_offered"] = max(schedule["remaining_offered"] - offered, 0.0)
                requested = offered * schedule["price_ratio"]
                payload = {
                    "maker_address": schedule["maker_address"],
                    "token_offered": schedule["token_offered"],
                    "amount_offered": offered,
                    "token_requested": schedule["token_requested"],
                    "amount_requested": requested,
                    "price": schedule["price"],
                    "order_type": SwapOrderType(schedule["order_type"]),
                    "stop_price": schedule.get("stop_price"),
                    "max_slippage_bps": schedule.get("max_slippage_bps"),
                }
                due_slices.append(payload)
                schedule["remaining_slices"] -= 1
                if schedule["remaining_slices"] <= 0:
                    self.twap_schedules.pop(schedule_id, None)
                else:
                    schedule["next_execution"] = schedule["next_execution"] + schedule["interval_seconds"]
            self._save_state()

        executed_order_ids: List[str] = []
        for payload in due_slices:
            order, _matches = self.place_order(**payload)
            executed_order_ids.append(order.order_id)
        return executed_order_ids

    def create_vwap_order(
        self,
        maker_address: str,
        token_offered: str,
        amount_offered: float,
        token_requested: str,
        amount_requested: float,
        *,
        order_type: SwapOrderType,
        volume_profile: Sequence[Dict[str, float]],
        stop_price: Optional[float] = None,
        max_slippage_bps: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not volume_profile:
            raise ValueError("volume_profile required for VWAP order")
        weights = [entry.get("weight") or entry.get("volume") for entry in volume_profile]
        total_weight = sum(weight for weight in weights if weight and weight > 0)
        if total_weight <= 0:
            raise ValueError("volume_profile weights must be positive")

        order_ids: List[str] = []
        matches: List[str] = []
        for entry, raw_weight in zip(volume_profile, weights):
            if not raw_weight or raw_weight <= 0:
                continue
            portion = raw_weight / total_weight
            slice_offered = amount_offered * portion
            slice_requested = amount_requested * portion
            slice_price = entry.get("price", None)
            exec_price = slice_price if slice_price else (slice_requested / slice_offered)
            order, order_matches = self.place_order(
                maker_address=maker_address,
                token_offered=token_offered,
                amount_offered=slice_offered,
                token_requested=token_requested,
                amount_requested=slice_requested,
                price=exec_price,
                order_type=order_type,
                stop_price=stop_price,
                max_slippage_bps=max_slippage_bps,
            )
            order_ids.append(order.order_id)
            matches.extend(match.match_id for match in order_matches)
        return {"success": True, "orders": order_ids, "matches": matches}

    def get_order(self, order_id: str) -> Optional[WalletTradeOrder]:
        return self.orders.get(order_id)

    def get_match(self, match_id: str) -> Optional[WalletTradeMatch]:
        return self.matches.get(match_id)

    def list_orders(self) -> List[WalletTradeOrder]:
        return sorted(self.orders.values(), key=lambda o: o.created_at, reverse=True)

    def list_matches(self) -> List[WalletTradeMatch]:
        return sorted(self.matches.values(), key=lambda m: m.created_at, reverse=True)

    def settle_match(self, match_id: str, secret: str) -> Dict[str, Any]:
        with self.lock:
            match = self.matches.get(match_id)
            if not match:
                return {"success": False, "error": "match_not_found"}
            if match.status != TradeMatchStatus.MATCHED:
                return {"success": False, "error": "match_not_settleable"}
            if match.secret != secret:
                return {"success": False, "error": "invalid_secret"}
            if not self.exchange_wallet_manager:
                return {"success": False, "error": "exchange_manager_unavailable"}

            maker_order = self.orders.get(match.maker_order_id)
            taker_order = self.orders.get(match.taker_order_id)
            maker_address = maker_order.maker_address if maker_order else None
            taker_address = taker_order.maker_address if taker_order else None
            if not maker_address or not taker_address:
                return {"success": False, "error": "order_not_found"}

            # Execute simulated escrow release
            self.exchange_wallet_manager.withdraw(
                maker_address,
                match.maker_token,
                match.maker_amount,
                destination=taker_address,
            )
            maker_net = max(match.maker_net_amount or (match.maker_amount - match.maker_fee), 0.0)
            taker_net = max(match.taker_net_amount or (match.taker_amount - match.taker_fee), 0.0)
            if maker_net > 0:
                self.exchange_wallet_manager.deposit(
                    taker_address, match.maker_token, maker_net, deposit_type="trade"
                )
            if match.maker_fee > 0:
                self.exchange_wallet_manager.deposit(
                    self.fee_collector_address,
                    match.maker_token,
                    match.maker_fee,
                    deposit_type="trade_fee",
                )
            self.exchange_wallet_manager.withdraw(
                taker_address,
                match.taker_token,
                match.taker_amount,
                destination=maker_address,
            )
            if taker_net > 0:
                self.exchange_wallet_manager.deposit(
                    maker_address, match.taker_token, taker_net, deposit_type="trade"
                )
            if match.taker_fee > 0:
                self.exchange_wallet_manager.deposit(
                    self.fee_collector_address,
                    match.taker_token,
                    match.taker_fee,
                    deposit_type="trade_fee",
                )

            match.status = TradeMatchStatus.SETTLED
            match.settled_at = _now()
            self._record_event(
                "match_settled",
                {
                    "match_id": match.match_id,
                    "maker_order_id": match.maker_order_id,
                    "taker_order_id": match.taker_order_id,
                    "maker_fee": match.maker_fee,
                    "taker_fee": match.taker_fee,
                },
            )
            self._save_state()
            return SettlementResult(
                {
                    "success": True,
                    "match": match.to_dict(),
                    "match_obj": match,
                    "fees": {
                        "maker_fee": match.maker_fee,
                        "taker_fee": match.taker_fee,
                    },
                },
                match.status,
            )

    # ------------------------------------------------------------------
    # Gossip & diagnostics
    # ------------------------------------------------------------------
    def ingest_gossip(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            normalized = {
                "received_at": _now(),
                "event": event,
            }
            self.event_log.append(normalized)
            self.event_log = self.event_log[-MAX_HISTORY:]
            self._save_state()
        return {"success": True, "message": "event_ingested"}

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "orders": [order.to_dict() for order in self.list_orders()],
                "matches": [match.to_dict() for match in self.list_matches()],
                "active_sessions": len(self.sessions),
                "pending_handshakes": len(self.handshakes),
            }

    def signed_event_batch(self, limit: int) -> List[Dict[str, Any]]:
        with self.lock:
            events = self.event_log[-limit:]
            batches = []
            for entry in events:
                payload = entry["event"]
                batches.append(
                    {
                        "event": payload,
                        "signature": self.audit_signer.sign(payload),
                        "public_key": self.audit_signer.public_key(),
                    }
                )
            return batches

    def _record_event(self, event_type: str, details: Dict[str, Any]) -> None:
        entry = {"type": event_type, "details": details, "timestamp": _now()}
        self.event_log.append({"event": entry, "received_at": _now()})
        self.event_log = self.event_log[-MAX_HISTORY:]

    # ------------------------------------------------------------------
    # Atomic Swap Coordination (Multi-party)
    # ------------------------------------------------------------------
    def initiate_atomic_swap(
        self,
        participants: List[Dict[str, Any]],
        timeout_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Initiate a multi-party atomic swap with state synchronization.

        Args:
            participants: List of participant dictionaries with
                         {address, token, amount, public_key}
            timeout_seconds: Swap timeout duration

        Returns:
            Atomic swap coordination data
        """
        if len(participants) < 2:
            return {"success": False, "error": "At least 2 participants required"}

        with self.lock:
            swap_id = str(uuid.uuid4())
            swap_secret = secrets.token_hex(32)
            swap_hash = hashlib.sha256(swap_secret.encode()).hexdigest()

            # Initialize swap state
            swap_state = {
                "swap_id": swap_id,
                "participants": participants,
                "swap_hash": swap_hash,
                "status": "initiated",
                "created_at": _now(),
                "expires_at": _now() + timeout_seconds,
                "timeout_seconds": timeout_seconds,
                "participant_states": {
                    p["address"]: {
                        "status": "pending",
                        "committed": False,
                        "revealed": False,
                        "hash_lock_created": False,
                        "timeout_set": False
                    }
                    for p in participants
                },
                "coordination_log": []
            }

            # Store in sessions for coordination
            self.sessions[f"atomic_swap_{swap_id}"] = swap_state

            self._record_event("atomic_swap_initiated", {
                "swap_id": swap_id,
                "participant_count": len(participants),
                "expires_at": swap_state["expires_at"]
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "swap_hash": swap_hash,
                "expires_at": swap_state["expires_at"],
                "participants": participants,
                "message": "Atomic swap initiated. Participants must commit within timeout."
            }

    def commit_to_swap(
        self,
        swap_id: str,
        participant_address: str,
        hash_lock: str,
        signature: str
    ) -> Dict[str, Any]:
        """
        Participant commits to atomic swap by creating hash lock.

        Args:
            swap_id: Swap identifier
            participant_address: Committing participant
            hash_lock: Hash lock for this participant's funds
            signature: Signature proving commitment

        Returns:
            Commitment status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] not in ["initiated", "committing"]:
                return {"success": False, "error": f"swap_not_committable, status: {swap_state['status']}"}

            if _now() > swap_state["expires_at"]:
                return self._timeout_swap(swap_id, "commitment_timeout")

            if participant_address not in swap_state["participant_states"]:
                return {"success": False, "error": "participant_not_found"}

            p_state = swap_state["participant_states"][participant_address]

            if p_state["committed"]:
                return {"success": False, "error": "already_committed"}

            # Record commitment
            p_state["committed"] = True
            p_state["hash_lock"] = hash_lock
            p_state["commit_signature"] = signature
            p_state["hash_lock_created"] = True
            p_state["committed_at"] = _now()

            swap_state["coordination_log"].append({
                "event": "commitment",
                "participant": participant_address,
                "timestamp": _now()
            })

            # Check if all committed
            all_committed = all(
                s["committed"] for s in swap_state["participant_states"].values()
            )

            if all_committed:
                swap_state["status"] = "committed"
                swap_state["all_committed_at"] = _now()

            swap_state["status"] = "committing" if not all_committed else "committed"

            self._record_event("swap_commitment", {
                "swap_id": swap_id,
                "participant": participant_address,
                "all_committed": all_committed
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "participant": participant_address,
                "all_committed": all_committed,
                "committed_count": sum(1 for s in swap_state["participant_states"].values() if s["committed"]),
                "total_participants": len(swap_state["participants"])
            }

    def reveal_swap_secret(
        self,
        swap_id: str,
        participant_address: str,
        secret: str
    ) -> Dict[str, Any]:
        """
        Reveal secret to complete atomic swap.

        Args:
            swap_id: Swap identifier
            participant_address: Revealing participant
            secret: The swap secret

        Returns:
            Reveal status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] != "committed":
                return {"success": False, "error": f"swap_not_ready_for_reveal, status: {swap_state['status']}"}

            # Verify secret matches hash
            secret_hash = hashlib.sha256(secret.encode()).hexdigest()
            if secret_hash != swap_state["swap_hash"]:
                return {"success": False, "error": "invalid_secret"}

            if participant_address not in swap_state["participant_states"]:
                return {"success": False, "error": "participant_not_found"}

            p_state = swap_state["participant_states"][participant_address]

            if p_state["revealed"]:
                return {"success": False, "error": "already_revealed"}

            # Record reveal
            p_state["revealed"] = True
            p_state["revealed_at"] = _now()
            p_state["status"] = "completed"

            swap_state["coordination_log"].append({
                "event": "secret_revealed",
                "participant": participant_address,
                "timestamp": _now()
            })

            # Check if all revealed
            all_revealed = all(
                s["revealed"] for s in swap_state["participant_states"].values()
            )

            if all_revealed:
                swap_state["status"] = "completed"
                swap_state["completed_at"] = _now()
                swap_state["swap_secret"] = secret  # Store for audit

            self._record_event("swap_secret_revealed", {
                "swap_id": swap_id,
                "participant": participant_address,
                "all_revealed": all_revealed
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "participant": participant_address,
                "all_revealed": all_revealed,
                "swap_completed": all_revealed,
                "revealed_count": sum(1 for s in swap_state["participant_states"].values() if s["revealed"])
            }

    def rollback_swap(
        self,
        swap_id: str,
        reason: str,
        initiator_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback atomic swap on failure.

        Args:
            swap_id: Swap identifier
            reason: Reason for rollback
            initiator_address: Who initiated rollback

        Returns:
            Rollback status
        """
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            if swap_state["status"] == "completed":
                return {"success": False, "error": "cannot_rollback_completed_swap"}

            if swap_state["status"] == "rolled_back":
                return {"success": False, "error": "already_rolled_back"}

            # Execute rollback
            swap_state["status"] = "rolled_back"
            swap_state["rollback_reason"] = reason
            swap_state["rollback_initiator"] = initiator_address
            swap_state["rolled_back_at"] = _now()

            # Mark all participants as rolled back
            for p_address, p_state in swap_state["participant_states"].items():
                if p_state["committed"] and not p_state["revealed"]:
                    p_state["status"] = "rolled_back"
                    p_state["funds_returned"] = True

            swap_state["coordination_log"].append({
                "event": "rollback",
                "reason": reason,
                "initiator": initiator_address,
                "timestamp": _now()
            })

            self._record_event("swap_rolled_back", {
                "swap_id": swap_id,
                "reason": reason,
                "initiator": initiator_address
            })

            self._save_state()

            return {
                "success": True,
                "swap_id": swap_id,
                "status": "rolled_back",
                "reason": reason,
                "participants_refunded": len(swap_state["participants"])
            }

    def _timeout_swap(self, swap_id: str, reason: str) -> Dict[str, Any]:
        """Internal method to handle swap timeout."""
        return self.rollback_swap(swap_id, f"timeout: {reason}", initiator_address="system")

    def get_swap_status(self, swap_id: str) -> Dict[str, Any]:
        """Get current status of atomic swap."""
        with self.lock:
            swap_key = f"atomic_swap_{swap_id}"
            swap_state = self.sessions.get(swap_key)

            if not swap_state:
                return {"success": False, "error": "swap_not_found"}

            return {
                "success": True,
                "swap_id": swap_id,
                "status": swap_state["status"],
                "created_at": swap_state["created_at"],
                "expires_at": swap_state["expires_at"],
                "time_remaining": max(0, swap_state["expires_at"] - _now()),
                "participants": swap_state["participants"],
                "participant_states": swap_state["participant_states"],
                "coordination_log": swap_state["coordination_log"]
            }
logger = logging.getLogger(__name__)
