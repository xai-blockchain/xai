"""
XAI Wallet-to-Wallet Trade Engine

Coordinates multi-currency orders, matches, and HTLC settlement
"""

import hashlib
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

from config import Config
from exchange_wallet import ExchangeWalletManager, SUPPORTED_TOKENS
from nonce_tracker import NonceTracker, get_nonce_tracker
from trading import (
    OrderStatus,
    SwapOrderType,
    TradeMatch,
    TradeMatchStatus,
    TradeOrder,
)


HTLC_TIMEOUT_SECONDS = 60 * 60  # 1 hour default


def _normalize_currency(currency: str) -> str:
    return currency.strip().upper()


class WalletTradeManager:
    """Manage wallets, trade orders, and HTLC-backed matches"""

    def __init__(
        self,
        exchange_wallet_manager: ExchangeWalletManager,
        data_dir: str,
        nonce_tracker: Optional[NonceTracker] = None,
    ):
        self.exchange_wallet_manager = exchange_wallet_manager
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.nonce_tracker = nonce_tracker or get_nonce_tracker()
        self.htlc_timeout = HTLC_TIMEOUT_SECONDS
        self.orders: Dict[str, TradeOrder] = {}
        self.matches: Dict[str, TradeMatch] = {}
        self._load_orders()
        self._load_matches()

    def _order_path(self) -> str:
        return os.path.join(self.data_dir, 'wallet_trade_orders.json')

    def _match_path(self) -> str:
        return os.path.join(self.data_dir, 'wallet_trade_matches.json')

    def _load_orders(self):
        path = self._order_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for order_id, value in data.items():
                self.orders[order_id] = TradeOrder.from_dict(value)
        except Exception:
            self.orders = {}

    def _load_matches(self):
        path = self._match_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            for match_id, value in data.items():
                self.matches[match_id] = TradeMatch.from_dict(value)
        except Exception:
            self.matches = {}

    def _save_orders(self):
        with open(self._order_path(), 'w') as f:
            json.dump({oid: order.to_dict() for oid, order in self.orders.items()}, f, indent=2)

    def _save_matches(self):
        with open(self._match_path(), 'w') as f:
            json.dump({mid: match.to_dict() for mid, match in self.matches.items()}, f, indent=2)

    def cleanup_expired_matches(self):
        now = time.time()
        expired = [m for m in self.matches.values() if m.status == TradeMatchStatus.MATCHED and m.expires_at <= now]
        for match in expired:
            try:
                self.refund_match(match.match_id)
            except Exception:
                continue

    def place_order(
        self,
        maker_address: str,
        token_offered: str,
        amount_offered: float,
        token_requested: str,
        amount_requested: Optional[float] = None,
        price: float = 1.0,
        order_type: SwapOrderType = SwapOrderType.SELL,
        expiry: Optional[float] = None,
        fee: float = 0.0,
        maker_public_key: str = '',
        metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[TradeOrder, List[TradeMatch]]:
        self.cleanup_expired_matches()

        token_offered = self._coerce_token(token_offered)
        token_requested = self._coerce_token(token_requested)
        if token_offered == token_requested:
            raise ValueError('Offers must involve two different assets')

        amount_offered = float(amount_offered)
        if amount_requested is None:
            amount_requested = amount_offered * float(price)
        amount_requested = float(amount_requested)
        if amount_offered <= 0 or amount_requested <= 0:
            raise ValueError('Amounts must be positive')

        expiry_ts = float(expiry) if expiry else time.time() + self.htlc_timeout
        if expiry_ts <= time.time():
            raise ValueError('Expiry must be in the future')

        order_type = self._coerce_order_type(order_type)

        nonce = self.nonce_tracker.get_next_nonce(maker_address)
        if not self.exchange_wallet_manager.lock_for_order(maker_address, token_offered, amount_offered):
            raise ValueError(f'Insufficient {token_offered} to lock')

        order = TradeOrder(
            maker_address=maker_address,
            maker_public_key=maker_public_key,
            token_offered=token_offered,
            amount_offered=amount_offered,
            token_requested=token_requested,
            amount_requested=amount_requested,
            price=float(price),
            expiry=expiry_ts,
            nonce=nonce,
            order_type=order_type,
            fee=float(fee),
            metadata=metadata or {},
        )

        self.orders[order.order_id] = order
        self._save_orders()
        self.nonce_tracker.increment_nonce(maker_address, nonce)

        matches = self._match_order(order)
        return order, matches

    def _match_order(self, new_order: TradeOrder) -> List[TradeMatch]:
        matches: List[TradeMatch] = []
        for order in self.orders.values():
            if order.order_id == new_order.order_id or order.status != OrderStatus.PENDING:
                continue
            if not self._orders_are_compatible(new_order, order):
                continue
            match = self._create_match(new_order, order)
            matches.append(match)
            break

        if matches:
            self._save_orders()
            self._save_matches()

        return matches

    def _orders_are_compatible(self, a: TradeOrder, b: TradeOrder) -> bool:
        if a.order_type == b.order_type:
            return False
        if a.token_offered != b.token_requested or a.token_requested != b.token_offered:
            return False
        if a.amount_offered != b.amount_requested or a.amount_requested != b.amount_offered:
            return False
        if a.is_expired() or b.is_expired():
            return False
        counterparty_a = a.metadata.get('counterparty') if a.metadata else None
        if counterparty_a and counterparty_a != b.maker_address:
            return False
        counterparty_b = b.metadata.get('counterparty') if b.metadata else None
        if counterparty_b and counterparty_b != a.maker_address:
            return False
        return True

    def _create_match(self, maker: TradeOrder, taker: TradeOrder) -> TradeMatch:
        secret = secrets.token_hex(32)
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        now = time.time()
        match_id = hashlib.sha256(f"{maker.order_id}{taker.order_id}{now}".encode()).hexdigest()[:20]

        maker_fee = maker.amount_offered * getattr(Config, 'TRADE_FEE_PERCENT', 0.001)
        taker_fee = taker.amount_offered * getattr(Config, 'TRADE_FEE_PERCENT', 0.001)
        total_fee = maker_fee + taker_fee

        match = TradeMatch(
            match_id=match_id,
            maker_order_id=maker.order_id,
            taker_order_id=taker.order_id,
            secret_hash=secret_hash,
            created_at=now,
            expires_at=now + self.htlc_timeout,
            status=TradeMatchStatus.MATCHED,
            metadata={
                'pair': f"{maker.token_offered}/{maker.token_requested}",
                'maker_type': maker.order_type.value,
                'price': maker.price,
                'ttl': self.htlc_timeout,
                'fee': total_fee,
                'fee_total': total_fee,
                'maker_fee': maker_fee,
                'taker_fee': taker_fee,
            },
            secret=secret,
        )

        maker.status = OrderStatus.MATCHED
        taker.status = OrderStatus.MATCHED
        maker.matched_order_id = taker.order_id
        taker.matched_order_id = maker.order_id

        self.matches[match.match_id] = match
        return match

    def settle_match(self, match_id: str, secret: str) -> TradeMatch:
        match = self.matches.get(match_id)
        if not match or match.status != TradeMatchStatus.MATCHED:
            raise ValueError('Match is not available for settlement')
        if hashlib.sha256(secret.encode()).hexdigest() != match.secret_hash:
            raise ValueError('Secret mismatch')

        maker = self.orders.get(match.maker_order_id)
        taker = self.orders.get(match.taker_order_id)
        if not maker or not taker:
            raise ValueError('Related orders missing')

        self._unlock_for_settlement(maker)
        self._unlock_for_settlement(taker)

        self.exchange_wallet_manager.withdraw(
            maker.maker_address, maker.token_offered, maker.amount_offered, destination=taker.maker_address
        )
        self.exchange_wallet_manager.deposit(
            taker.maker_address, maker.token_offered, maker.amount_offered
        )

        self.exchange_wallet_manager.withdraw(
            taker.maker_address, taker.token_offered, taker.amount_offered, destination=maker.maker_address
        )
        self.exchange_wallet_manager.deposit(
            maker.maker_address, taker.token_offered, taker.amount_offered
        )

        maker.status = OrderStatus.COMPLETED
        taker.status = OrderStatus.COMPLETED
        match.status = TradeMatchStatus.SETTLED
        match.secret = secret

        self._save_orders()
        self._save_matches()
        return match

    def refund_match(self, match_id: str) -> TradeMatch:
        match = self.matches.get(match_id)
        if not match or match.status != TradeMatchStatus.MATCHED:
            raise ValueError('Match cannot be refunded')

        maker = self.orders.get(match.maker_order_id)
        taker = self.orders.get(match.taker_order_id)
        if maker:
            maker.status = OrderStatus.EXPIRED
            self._unlock_for_settlement(maker)
        if taker:
            taker.status = OrderStatus.EXPIRED
            self._unlock_for_settlement(taker)

        match.status = TradeMatchStatus.REFUNDED
        self._save_orders()
        self._save_matches()
        return match

    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        return self.orders.get(order_id)

    def get_match(self, match_id: str) -> Optional[TradeMatch]:
        return self.matches.get(match_id)

    def list_open_orders(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        self.cleanup_expired_matches()
        orders = [order.to_dict() for order in self.orders.values() if order.status == OrderStatus.PENDING]
        return orders[:limit] if limit else orders

    def get_wallet_orders(self, address: str) -> List[Dict[str, Any]]:
        self.cleanup_expired_matches()
        return [order.to_dict() for order in self.orders.values() if order.maker_address == address]

    def get_wallet_matches(self, address: str) -> List[Dict[str, Any]]:
        self.cleanup_expired_matches()
        wallet_matches = []
        for match in self.matches.values():
            maker = self.orders.get(match.maker_order_id)
            taker = self.orders.get(match.taker_order_id)
            if maker and maker.maker_address == address:
                wallet_matches.append(match.to_dict())
            elif taker and taker.maker_address == address:
                wallet_matches.append(match.to_dict())
        return wallet_matches

    def list_matches(self, status: Optional[TradeMatchStatus] = None) -> List[Dict[str, Any]]:
        matches = self.matches.values()
        if status:
            matches = [m for m in matches if m.status == status]
        return [m.to_dict() for m in matches]

    def _unlock_for_settlement(self, order: TradeOrder):
        self.exchange_wallet_manager.unlock_from_order(
            order.maker_address, order.token_offered, order.amount_offered
        )

    def _coerce_token(self, currency: str) -> str:
        normalized = _normalize_currency(currency)
        if normalized not in SUPPORTED_TOKENS:
            raise ValueError(f'Unsupported currency: {normalized}')
        return normalized

    def _coerce_order_type(self, value: SwapOrderType) -> SwapOrderType:
        if isinstance(value, str):
            return SwapOrderType(value.lower())
        return value
