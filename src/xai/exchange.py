from __future__ import annotations

"""
XAI Exchange - Decentralized Order Book and Matching Engine

Handles limit orders, market orders, and trade execution with atomic settlement.

Features:
- Price-time priority order matching
- Atomic fund settlement with rollback on failure
- Trading fee calculation with XAI discount
- Order book depth and spread tracking
- Trade history and user order management

Security:
- All settlements are atomic (both sides execute or neither)
- Balance verification before trade execution
- Fee deduction from trade proceeds
- Structured logging for audit trail
"""

import hashlib
import hmac
import json
import logging
import math
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable

from xai.core.wallets.exchange_wallet import ExchangeWalletManager
from xai.core.transaction import Transaction

logger = logging.getLogger(__name__)

class ExchangeError(Exception):
    """Base exception for exchange errors."""
    pass

class InsufficientBalanceError(ExchangeError):
    """Raised when user has insufficient balance for trade."""
    pass

class SettlementError(ExchangeError):
    """Raised when trade settlement fails."""
    pass

class OrderValidationError(ExchangeError):
    """Raised when order validation fails."""
    pass

class OrderType(Enum):
    """Order types"""

    LIMIT = "limit"
    MARKET = "market"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """Order sides"""

    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status"""

    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"

@dataclass
class Order:
    """Represents a trading order"""

    id: str
    user_address: str
    pair: str  # e.g., "AXN/USD", "BTC/USD"
    side: OrderSide
    order_type: OrderType
    price: Decimal  # Limit price (0 for market orders)
    amount: Decimal  # Amount to buy/sell
    filled: Decimal = Decimal("0")  # Amount filled
    status: OrderStatus = OrderStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    pay_fee_with_axn: bool = False
    stop_price: Decimal | None = None
    triggered: bool = False
    triggered_at: float | None = None
    slippage_bps: int | None = None
    reference_price: Decimal | None = None

    def remaining(self) -> Decimal:
        """Get remaining unfilled amount"""
        return self.amount - self.filled

    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.filled >= self.amount

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_address": self.user_address,
            "pair": self.pair,
            "side": self.side.value,
            "type": self.order_type.value,
            "price": float(self.price),
            "amount": float(self.amount),
            "filled": float(self.filled),
            "remaining": float(self.remaining()),
            "status": self.status.value,
            "timestamp": self.timestamp,
            "pay_fee_with_axn": self.pay_fee_with_axn,
            "stop_price": float(self.stop_price) if self.stop_price is not None else None,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at,
            "slippage_bps": self.slippage_bps,
            "reference_price": float(self.reference_price) if self.reference_price is not None else None,
        }

class SettlementStatus(Enum):
    """Settlement status for trades."""
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class Trade:
    """
    Represents an executed trade with settlement tracking.

    A trade is only considered complete when settlement_status is SETTLED,
    indicating that funds have been atomically transferred between parties.
    """

    id: str
    pair: str
    buy_order_id: str
    sell_order_id: str
    buyer_address: str
    seller_address: str
    price: Decimal
    amount: Decimal
    timestamp: float = field(default_factory=time.time)
    settlement_status: SettlementStatus = SettlementStatus.PENDING
    buyer_fee: Decimal = Decimal("0")
    seller_fee: Decimal = Decimal("0")
    settlement_txid: str | None = None
    settlement_error: str | None = None
    maker_address: str | None = None
    taker_address: str | None = None
    maker_order_id: str | None = None
    taker_order_id: str | None = None
    maker_fee: Decimal = Decimal("0")
    taker_fee: Decimal = Decimal("0")

    @property
    def total_value(self) -> Decimal:
        """Total value of the trade (price * amount)."""
        return self.price * self.amount

    @property
    def is_settled(self) -> bool:
        """Check if trade has been settled."""
        return self.settlement_status == SettlementStatus.SETTLED

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "pair": self.pair,
            "buy_order_id": self.buy_order_id,
            "sell_order_id": self.sell_order_id,
            "buyer": self.buyer_address,
            "seller": self.seller_address,
            "price": float(self.price),
            "amount": float(self.amount),
            "total": float(self.total_value),
            "buyer_fee": float(self.buyer_fee),
            "seller_fee": float(self.seller_fee),
            "settlement_status": self.settlement_status.value,
            "settlement_txid": self.settlement_txid,
            "timestamp": self.timestamp,
            "maker_address": self.maker_address,
            "taker_address": self.taker_address,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "maker_fee": float(self.maker_fee),
            "taker_fee": float(self.taker_fee),
        }

class OrderBook:
    """Order book for a single trading pair"""

    def __init__(self, pair: str):
        self.pair = pair
        self.buy_orders: list[Order] = []  # Sorted by price (highest first)
        self.sell_orders: list[Order] = []  # Sorted by price (lowest first)

    def add_order(self, order: Order):
        """Add order to the book"""
        if order.side == OrderSide.BUY:
            self.buy_orders.append(order)
            # Sort buy orders: highest price first
            self.buy_orders.sort(key=lambda o: (-float(o.price), o.timestamp))
        else:
            self.sell_orders.append(order)
            # Sort sell orders: lowest price first
            self.sell_orders.sort(key=lambda o: (float(o.price), o.timestamp))

    def remove_order(self, order_id: str):
        """Remove order from the book"""
        self.buy_orders = [o for o in self.buy_orders if o.id != order_id]
        self.sell_orders = [o for o in self.sell_orders if o.id != order_id]

    def get_order(self, order_id: str) -> Order | None:
        """Get order by ID"""
        for order in self.buy_orders + self.sell_orders:
            if order.id == order_id:
                return order
        return None

    def get_best_bid(self) -> Decimal | None:
        """Get highest buy price"""
        if self.buy_orders:
            return self.buy_orders[0].price
        return None

    def get_best_ask(self) -> Decimal | None:
        """Get lowest sell price"""
        if self.sell_orders:
            return self.sell_orders[0].price
        return None

    def get_spread(self) -> Decimal | None:
        """Get bid-ask spread"""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return ask - bid
        return None

    def to_dict(self) -> dict:
        """Convert order book to dictionary"""
        return {
            "pair": self.pair,
            "bids": [
                {
                    "price": float(o.price),
                    "amount": float(o.remaining()),
                    "total": float(o.price * o.remaining()),
                }
                for o in self.buy_orders[:20]  # Top 20 bids
            ],
            "asks": [
                {
                    "price": float(o.price),
                    "amount": float(o.remaining()),
                    "total": float(o.price * o.remaining()),
                }
                for o in self.sell_orders[:20]  # Top 20 asks
            ],
            "best_bid": float(self.get_best_bid()) if self.get_best_bid() else None,
            "best_ask": float(self.get_best_ask()) if self.get_best_ask() else None,
            "spread": float(self.get_spread()) if self.get_spread() else None,
        }

class BalanceProvider(ABC):
    """
    Interface for balance management.

    Implementations must provide atomic balance operations for settlement.
    """

    @abstractmethod
    def get_balance(self, address: str, asset: str) -> Decimal:
        """Get balance for an address and asset."""

    @abstractmethod
    def reserve_balance(self, address: str, asset: str, amount: Decimal) -> bool:
        """
        Reserve balance for a pending trade.

        Returns True if reservation succeeded, False if insufficient balance.
        """

    @abstractmethod
    def release_reservation(self, address: str, asset: str, amount: Decimal) -> bool:
        """Release a previous reservation (on trade cancellation/rollback)."""

    @abstractmethod
    def transfer(
        self,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        *,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Execute atomic transfer between addresses.

        Returns transaction ID if successful, None if failed.
        """

    @abstractmethod
    def verify_transfer(self, txid: str, *, timeout_seconds: int = 0) -> bool:
        """Verify that a transfer with the specified txid has been confirmed."""

class InMemoryBalanceProvider(BalanceProvider):
    """
    In-memory balance provider for testing and development.

    WARNING: This is NOT suitable for production. Use a proper
    blockchain-backed implementation for mainnet.
    """

    def __init__(self):
        self.balances: dict[str, dict[str, Decimal]] = {}  # address -> {asset -> balance}
        self.reservations: dict[str, dict[str, Decimal]] = {}  # address -> {asset -> reserved}
        self._tx_counter = 0

    def set_balance(self, address: str, asset: str, amount: Decimal):
        """Set balance for testing."""
        if address not in self.balances:
            self.balances[address] = {}
        self.balances[address][asset] = amount

    def get_balance(self, address: str, asset: str) -> Decimal:
        """Get available balance (total - reserved)."""
        total = self.balances.get(address, {}).get(asset, Decimal("0"))
        reserved = self.reservations.get(address, {}).get(asset, Decimal("0"))
        return total - reserved

    def reserve_balance(self, address: str, asset: str, amount: Decimal) -> bool:
        """Reserve balance for pending trade."""
        available = self.get_balance(address, asset)
        if available < amount:
            return False

        if address not in self.reservations:
            self.reservations[address] = {}
        current_reserved = self.reservations[address].get(asset, Decimal("0"))
        self.reservations[address][asset] = current_reserved + amount
        return True

    def release_reservation(self, address: str, asset: str, amount: Decimal) -> bool:
        """Release reserved balance."""
        if address not in self.reservations:
            return False
        current_reserved = self.reservations[address].get(asset, Decimal("0"))
        if current_reserved < amount:
            return False
        self.reservations[address][asset] = current_reserved - amount
        return True

    def transfer(
        self,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        *,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """Execute atomic transfer."""
        accounts = self.balances.setdefault(from_address, {})
        from_balance = accounts.get(asset, Decimal("0"))
        if from_balance < amount:
            logger.debug(
                "Auto-minting dev balance for in-memory provider transfer",
                extra={
                    "event": "exchange.dev_balance_topup",
                    "address": from_address[:12] + "...",
                    "asset": asset,
                    "required": float(amount),
                },
            )
            from_balance = amount
        accounts[asset] = from_balance

        # Execute transfer
        self.balances[from_address][asset] = from_balance - amount
        if to_address not in self.balances:
            self.balances[to_address] = {}
        to_balance = self.balances[to_address].get(asset, Decimal("0"))
        self.balances[to_address][asset] = to_balance + amount

        # Generate transaction ID
        self._tx_counter += 1
        return f"TX{self._tx_counter:08d}"

    def verify_transfer(self, txid: str, *, timeout_seconds: int = 0) -> bool:
        return True

class BlockchainBalanceProvider(BalanceProvider):
    """
    Blockchain-backed provider that records settlement receipts on-chain while
    using the exchange wallet manager for custody.
    """

    def __init__(
        self,
        wallet_manager: ExchangeWalletManager,
        blockchain,
        *,
        attestor_address: str = "XAI0000000000000000000000000000000000000000",
        attestor_secret: str | None = None,
        confirmations_required: int = 1,
        settlement_fee: float = 0.0,
    ) -> None:
        self.wallet_manager = wallet_manager
        self.blockchain = blockchain
        self.attestor_address = attestor_address
        secret = attestor_secret or secrets.token_hex(32)
        self._attestor_secret = secret.encode("utf-8")
        self.confirmations_required = max(0, confirmations_required)
        self.settlement_fee = float(settlement_fee)

    def get_balance(self, address: str, asset: str) -> Decimal:
        summary = self.wallet_manager.get_balance(address, asset)
        return Decimal(str(summary.get("available", 0.0)))

    def reserve_balance(self, address: str, asset: str, amount: Decimal) -> bool:
        return self.wallet_manager.lock_for_order(address, asset, float(amount))

    def release_reservation(self, address: str, asset: str, amount: Decimal) -> bool:
        return self.wallet_manager.unlock_from_order(address, asset, float(amount))

    def transfer(
        self,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        *,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        context = context or {}
        amount_decimal = Decimal(str(amount))

        if not self._apply_ledger_transfer(from_address, to_address, asset, amount_decimal, record_entry=not context.get("rollback_of")):
            return None

        if context.get("rollback_of"):
            # Rollback adjustments should not emit settlement receipts
            return f"rollback-{context['rollback_of']}"

        txid = self._record_settlement_receipt(
            from_address=from_address,
            to_address=to_address,
            asset=asset,
            amount=amount_decimal,
            context=context,
        )
        if not txid:
            # Revert ledger if blockchain receipt fails
            self._apply_ledger_transfer(to_address, from_address, asset, amount_decimal, record_entry=False)
            return None
        return txid

    def verify_transfer(self, txid: str, *, timeout_seconds: int = 0) -> bool:
        deadline = time.time() + max(0, timeout_seconds)
        while True:
            tx, block_index = self._locate_transaction(txid)
            if tx:
                if self.confirmations_required <= 1 or block_index is None:
                    return True
                chain_length = len(getattr(self.blockchain, "chain", []))
                if block_index is not None and chain_length - block_index >= self.confirmations_required:
                    return True
            if time.time() >= deadline:
                return False
            time.sleep(0.25)

    def _apply_ledger_transfer(
        self,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        *,
        record_entry: bool = True,
    ) -> bool:
        with self.wallet_manager.lock:
            from_wallet = self.wallet_manager.get_wallet(from_address)
            if from_wallet.get_available_balance(asset) < amount:
                return False
            if not from_wallet.withdraw(asset, amount):
                return False
            to_wallet = self.wallet_manager.get_wallet(to_address)
            to_wallet.deposit(asset, amount)
            if record_entry:
                entry = {
                    "id": self.wallet_manager._generate_tx_id(),
                    "type": "trade_settlement_internal",
                    "from": from_address,
                    "to": to_address,
                    "asset": asset,
                    "amount": float(amount),
                    "timestamp": time.time(),
                }
                self.wallet_manager.transactions.append(entry)
            self.wallet_manager.save_wallets()
            return True

    def _record_settlement_receipt(
        self,
        *,
        from_address: str,
        to_address: str,
        asset: str,
        amount: Decimal,
        context: dict[str, Any],
    ) -> str | None:
        payload = {
            "type": "exchange_settlement",
            "from": from_address,
            "to": to_address,
            "asset": asset,
            "amount": float(amount),
            "context": context,
            "timestamp": time.time(),
        }
        tx = Transaction(
            sender=self.attestor_address,
            recipient=self.attestor_address,
            amount=0.0,
            fee=self.settlement_fee,
            tx_type="trade_settlement",
            metadata=payload,
        )
        signature = hmac.new(
            self._attestor_secret,
            json.dumps(payload, sort_keys=True).encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()
        tx.signature = signature
        tx.txid = tx.calculate_hash()
        if not self.blockchain.add_transaction(tx):
            return None
        return tx.txid

    def _locate_transaction(self, txid: str) -> tuple[Any | None, int | None]:
        pending = getattr(self.blockchain, "pending_transactions", []) or []
        for tx in pending:
            candidate = getattr(tx, "txid", None)
            if not candidate and isinstance(tx, dict):
                candidate = tx.get("txid")
            if candidate == txid:
                return tx, None
        chain = getattr(self.blockchain, "chain", []) or []
        for index, block in enumerate(chain):
            txs = getattr(block, "transactions", None)
            if txs is None and isinstance(block, dict):
                txs = block.get("transactions")
            if not isinstance(txs, (list, tuple)):
                continue
            for tx in txs:
                candidate = getattr(tx, "txid", None)
                if not candidate and isinstance(tx, dict):
                    candidate = tx.get("txid")
                if candidate == txid:
                    return tx, index
        return None, None

class MatchingEngine:
    """
    Order matching engine with atomic settlement.

    Implements price-time priority matching with proper fund settlement.
    All trades are settled atomically - either both sides execute or neither.

    Security:
    - Balance verification before order placement
    - Atomic settlement with rollback on failure
    - Fee deduction from trade proceeds
    - Structured logging for audit trail
    """

    def __init__(
        self,
        fee_rate: Decimal = Decimal("0.001"),
        xai_fee_discount: Decimal = Decimal("0.5"),
        axn_fee_discount: Decimal | None = None,
        balance_provider: BalanceProvider | None = None,
        fee_collector_address: str = "XAI_FEE_COLLECTOR",
        maker_fee_rate: Decimal | None = None,
        taker_fee_rate: Decimal | None = None,
    ):
        """
        Initialize matching engine.

        Args:
            fee_rate: Trading fee rate (default 0.1%)
            xai_fee_discount: Discount when paying fees with XAI (default 50%)
            axn_fee_discount: Legacy alias for xai_fee_discount
            balance_provider: Provider for balance operations (uses in-memory for dev if None)
            fee_collector_address: Address to receive trading fees
        """
        if axn_fee_discount is not None:
            xai_fee_discount = axn_fee_discount
        self.order_books: dict[str, OrderBook] = {}
        self.active_orders: dict[str, Order] = {}
        self.trade_history: list[Trade] = []
        self.user_orders: dict[str, list[str]] = {}
        self.stop_orders: dict[str, list[Order]] = {}
        self.last_trade_price: dict[str, Decimal] = {}
        self.fee_rate = fee_rate
        self.xai_fee_discount = xai_fee_discount
        self.maker_fee_rate = maker_fee_rate if maker_fee_rate is not None else fee_rate
        self.taker_fee_rate = taker_fee_rate if taker_fee_rate is not None else fee_rate
        self.fee_collector_address = fee_collector_address

        # Use provided balance provider or create in-memory for development
        if balance_provider is None:
            logger.warning(
                "Using in-memory balance provider - NOT SUITABLE FOR PRODUCTION",
                extra={"event": "exchange.dev_mode"}
            )
            self.balance_provider = InMemoryBalanceProvider()
        else:
            self.balance_provider = balance_provider

        logger.info(
            "Matching engine initialized",
            extra={
                "event": "exchange.init",
                "fee_rate": float(fee_rate),
                "xai_discount": float(xai_fee_discount),
                "maker_fee_rate": float(self.maker_fee_rate),
                "taker_fee_rate": float(self.taker_fee_rate),
            }
        )

    @property
    def axn_fee_discount(self) -> Decimal:
        """
        Backwards compatible accessor for historical spelling.

        Legacy tests referenced axn_fee_discount; keep alias while the
        canonical attribute remains xai_fee_discount internally.
        """
        return self.xai_fee_discount

    def _verify_settlement_tx(self, txid: str | None, leg: str) -> None:
        if not txid:
            raise SettlementError(f"Missing settlement transaction for {leg}")
        verifier = getattr(self.balance_provider, "verify_transfer", None)
        if not verifier:
            return
        if not verifier(txid):
            raise SettlementError(f"Unable to verify settlement transaction for {leg}")

    def get_order_book(self, pair: str) -> OrderBook:
        """Get or create order book for pair"""
        if pair not in self.order_books:
            self.order_books[pair] = OrderBook(pair)
        return self.order_books[pair]

    def _market_reference_price(self, pair: str, side: OrderSide) -> Decimal | None:
        """Return the best available price for slippage calculations."""
        book = self.get_order_book(pair)
        if side == OrderSide.BUY:
            return book.get_best_ask()
        return book.get_best_bid()

    def _validate_order_inputs(
        self,
        pair: str,
        side: str,
        order_type: str,
        price: float,
        amount: float,
        stop_price: float | None = None,
    ) -> tuple[OrderSide, OrderType, Decimal, Decimal, Decimal | None]:
        """
        Validate order placement parameters and return parsed enums/decimals.

        Enforces production-grade constraints so attackers cannot submit NaN,
        infinite, or negative pricing.
        """
        if not pair or "/" not in pair:
            raise OrderValidationError("Invalid trading pair format. Use BASE/QUOTE.")

        try:
            side_enum = OrderSide(side.lower())
        except ValueError as exc:
            raise OrderValidationError(f"Unsupported order side '{side}'") from exc

        try:
            type_enum = OrderType(order_type.lower())
        except ValueError as exc:
            raise OrderValidationError(f"Unsupported order type '{order_type}'") from exc

        if not math.isfinite(amount) or amount <= 0:
            raise OrderValidationError("Order amount must be a positive, finite number.")

        if not math.isfinite(price):
            raise OrderValidationError("Order price must be a finite number.")

        if type_enum == OrderType.MARKET:
            if price not in (0, 0.0):
                raise OrderValidationError("Market orders must use price=0.")
            price = 0.0
        else:
            if price <= 0:
                raise OrderValidationError("Limit/stop orders require a positive price.")

        try:
            price_decimal = Decimal(str(price))
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc:
            raise OrderValidationError("Invalid numeric precision for price or amount.") from exc

        if price_decimal.is_nan() or price_decimal.is_infinite():
            raise OrderValidationError("Order price must be finite.")
        if amount_decimal.is_nan() or amount_decimal.is_infinite():
            raise OrderValidationError("Order amount must be finite.")

        stop_decimal: Decimal | None = None
        if type_enum == OrderType.STOP_LIMIT:
            if stop_price is None:
                raise OrderValidationError("Stop-limit orders require a stop_price.")
            if not math.isfinite(stop_price) or stop_price <= 0:
                raise OrderValidationError("Stop price must be a positive, finite number.")
            try:
                stop_decimal = Decimal(str(stop_price))
            except (InvalidOperation, ValueError) as exc:
                raise OrderValidationError("Invalid numeric precision for stop price.") from exc
            if stop_decimal.is_nan() or stop_decimal.is_infinite():
                raise OrderValidationError("Stop price must be finite.")
            if side_enum == OrderSide.BUY and stop_decimal < price_decimal:
                raise OrderValidationError("Buy stop price must be >= limit price.")
            if side_enum == OrderSide.SELL and stop_decimal > price_decimal:
                raise OrderValidationError("Sell stop price must be <= limit price.")
        elif stop_price is not None:
            raise OrderValidationError("stop_price is only supported for stop-limit orders.")

        return side_enum, type_enum, price_decimal, amount_decimal, stop_decimal

    def place_order(
        self,
        user_address: str,
        pair: str,
        side: str,
        order_type: str,
        price: float,
        amount: float,
        stop_price: float | None = None,
        max_slippage_bps: int | None = None,
        pay_fee_with_axn: bool = False,
    ) -> Order:
        """Place a new order"""
        (
            side_enum,
            type_enum,
            price_decimal,
            amount_decimal,
            stop_decimal,
        ) = self._validate_order_inputs(
            pair, side, order_type, price, amount, stop_price=stop_price
        )

        slippage_limit = None
        reference_price = None
        if max_slippage_bps is not None:
            if type_enum != OrderType.MARKET:
                raise OrderValidationError("Slippage limit only applies to market orders.")
            try:
                slippage_limit = int(max_slippage_bps)
            except (TypeError, ValueError) as exc:
                raise OrderValidationError("max_slippage_bps must be a positive integer.") from exc
            if slippage_limit <= 0:
                raise OrderValidationError("max_slippage_bps must be greater than zero.")
            reference_price = self._market_reference_price(pair, side_enum)
            if reference_price is None or reference_price <= 0:
                raise OrderValidationError(
                    "Cannot enforce slippage without available market liquidity."
                )

        # Generate order ID
        order_id = str(uuid.uuid4())

        # Create order
        order = Order(
            id=order_id,
            user_address=user_address,
            pair=pair,
            side=side_enum,
            order_type=type_enum,
            price=price_decimal,
            amount=amount_decimal,
            pay_fee_with_axn=pay_fee_with_axn,
            stop_price=stop_decimal,
            slippage_bps=slippage_limit,
            reference_price=reference_price,
        )

        # Add to active orders
        self.active_orders[order_id] = order

        # Track user orders
        if user_address not in self.user_orders:
            self.user_orders[user_address] = []
        self.user_orders[user_address].append(order_id)

        # Try to match order
        if order.order_type == OrderType.MARKET:
            self.match_market_order(order)
            self._add_order_to_book_if_open(order)
        elif order.order_type == OrderType.STOP_LIMIT:
            self._handle_stop_limit_order(order)
        else:
            self.match_limit_order(order)
            self._add_order_to_book_if_open(order)

        return order

    def _add_order_to_book_if_open(self, order: Order) -> None:
        """Add an order to its order book if it still has remaining volume."""
        if order.is_filled() or order.status == OrderStatus.CANCELLED:
            return
        self.get_order_book(order.pair).add_order(order)

    def _slippage_exceeded(self, order: Order, price: Decimal) -> bool:
        """Determine whether executing at price violates slippage guardrails."""
        if not order.slippage_bps or order.reference_price is None:
            return False
        if order.reference_price <= 0:
            return False
        difference = abs(price - order.reference_price)
        slippage_bps = (difference / order.reference_price) * Decimal("10000")
        if slippage_bps > order.slippage_bps:
            logger.warning(
                "Slippage limit exceeded; cancelling remaining market order volume",
                extra={
                    "event": "exchange.slippage_guard",
                    "order_id": order.id,
                    "limit_bps": order.slippage_bps,
                    "observed_bps": float(slippage_bps),
                    "reference_price": float(order.reference_price),
                    "attempt_price": float(price),
                },
            )
            return True
        return False

    def _handle_stop_limit_order(self, order: Order) -> None:
        """Queue or trigger a stop-limit order based on current market price."""
        if order.stop_price is None:
            raise OrderValidationError("Stop-limit order missing stop price.")

        if self._should_trigger_stop(order):
            self._activate_stop_order(order)
        else:
            queue = self.stop_orders.setdefault(order.pair, [])
            queue.append(order)
            logger.info(
                "Queued stop-limit order",
                extra={
                    "event": "exchange.stop_order_queued",
                    "order_id": order.id,
                    "pair": order.pair,
                    "side": order.side.value,
                    "stop_price": float(order.stop_price),
                    "limit_price": float(order.price),
                },
            )

    def _current_price_for_side(self, pair: str, side: OrderSide) -> Decimal | None:
        """Get the current reference price used for stop order triggering."""
        last_trade = self.last_trade_price.get(pair)
        if last_trade is not None:
            return last_trade
        book = self.get_order_book(pair)
        return book.get_best_ask() if side == OrderSide.BUY else book.get_best_bid()

    def _should_trigger_stop(self, order: Order) -> bool:
        """Determine if the stop condition has been met for an order."""
        if order.stop_price is None:
            return False
        reference_price = self._current_price_for_side(order.pair, order.side)
        if reference_price is None:
            return False
        if order.side == OrderSide.BUY:
            return reference_price >= order.stop_price
        return reference_price <= order.stop_price

    def _activate_stop_order(self, order: Order) -> None:
        """Convert a queued stop-limit order into an active limit order."""
        order.triggered = True
        order.triggered_at = time.time()
        if order.order_type == OrderType.STOP_LIMIT:
            order.order_type = OrderType.LIMIT
        logger.info(
            "Activated stop-limit order",
            extra={
                "event": "exchange.stop_order_triggered",
                "order_id": order.id,
                "pair": order.pair,
                "trigger_price": float(order.stop_price or order.price),
            },
        )
        self.match_limit_order(order)
        self._add_order_to_book_if_open(order)

    def _check_stop_orders(self, pair: str) -> None:
        """Re-evaluate queued stop orders for a trading pair."""
        pending = self.stop_orders.get(pair)
        if not pending:
            return

        remaining: list[Order] = []
        for order in pending:
            if self._should_trigger_stop(order):
                self._activate_stop_order(order)
            else:
                remaining.append(order)

        if remaining:
            self.stop_orders[pair] = remaining
        else:
            self.stop_orders.pop(pair, None)

    def _remove_stop_order(self, order_id: str) -> None:
        """Remove a stop order from the pending queue if present."""
        for pair, orders in list(self.stop_orders.items()):
            filtered = [order for order in orders if order.id != order_id]
            if len(filtered) != len(orders):
                if filtered:
                    self.stop_orders[pair] = filtered
                else:
                    self.stop_orders.pop(pair, None)
                break

    def match_market_order(self, order: Order):
        """Match a market order immediately"""
        order_book = self.get_order_book(order.pair)

        if order.side == OrderSide.BUY:
            # Match with sell orders (take from lowest price)
            for sell_order in order_book.sell_orders[:]:
                if order.is_filled():
                    break

                if self._slippage_exceeded(order, sell_order.price):
                    break

                # Execute trade
                trade_amount = min(order.remaining(), sell_order.remaining())
                self.execute_trade(
                    order,
                    sell_order,
                    sell_order.price,
                    trade_amount,
                    taker_is_buy=True,
                )

        else:  # SELL
            # Match with buy orders (take from highest price)
            for buy_order in order_book.buy_orders[:]:
                if order.is_filled():
                    break

                if self._slippage_exceeded(order, buy_order.price):
                    break

                # Execute trade
                trade_amount = min(order.remaining(), buy_order.remaining())
                self.execute_trade(
                    buy_order,
                    order,
                    buy_order.price,
                    trade_amount,
                    taker_is_buy=False,
                )

        # Market orders that can't be filled are cancelled
        if not order.is_filled():
            order.status = OrderStatus.CANCELLED

    def match_limit_order(self, order: Order):
        """Match a limit order"""
        order_book = self.get_order_book(order.pair)

        if order.side == OrderSide.BUY:
            # Match with sell orders if sell price <= buy price
            for sell_order in order_book.sell_orders[:]:
                if order.is_filled():
                    break

                # Check if prices match
                if order.price >= sell_order.price:
                    # Execute trade at sell order price
                    trade_amount = min(order.remaining(), sell_order.remaining())
                    self.execute_trade(
                        order,
                        sell_order,
                        sell_order.price,
                        trade_amount,
                        taker_is_buy=True,
                    )
                else:
                    break  # No more matches (orders are sorted)

        else:  # SELL
            # Match with buy orders if buy price >= sell price
            for buy_order in order_book.buy_orders[:]:
                if order.is_filled():
                    break

                # Check if prices match
                if order.price <= buy_order.price:
                    # Execute trade at buy order price
                    trade_amount = min(order.remaining(), buy_order.remaining())
                    self.execute_trade(
                        buy_order,
                        order,
                        buy_order.price,
                        trade_amount,
                        taker_is_buy=False,
                    )
                else:
                    break  # No more matches

    def execute_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        price: Decimal,
        amount: Decimal,
        *,
        taker_is_buy: bool,
    ) -> Trade | None:
        """
        Execute a trade between two orders with atomic settlement.

        Settlement flow:
        1. Calculate fees for both parties
        2. Verify buyer has sufficient quote currency (price * amount + fees)
        3. Verify seller has sufficient base currency (amount)
        4. Execute atomic transfers:
           - Buyer sends quote currency to seller
           - Seller sends base currency to buyer
           - Fees sent to fee collector
        5. On any failure, rollback all transfers

        Args:
            buy_order: The buy order
            sell_order: The sell order
            price: Execution price
            amount: Trade amount (in base currency)
            taker_is_buy: True if the buy order initiated the match (taker), False otherwise

        Returns:
            Trade object if successful, None if settlement failed
        """
        # Parse trading pair (e.g., "XAI/USD" -> base="XAI", quote="USD")
        try:
            base_asset, quote_asset = buy_order.pair.split("/")
        except ValueError:
            logger.error(
                "Invalid trading pair format",
                extra={"event": "exchange.invalid_pair", "pair": buy_order.pair}
            )
            return None

        # Calculate trade value and fees
        trade_value = price * amount  # Quote currency amount
        buyer_is_maker = not taker_is_buy
        seller_is_maker = taker_is_buy
        buyer_fee = self.calculate_fee(
            trade_value,
            pay_with_axn=buy_order.pay_fee_with_axn,
            is_maker=buyer_is_maker,
        )
        seller_fee = self.calculate_fee(
            trade_value,
            pay_with_axn=sell_order.pay_fee_with_axn,
            is_maker=seller_is_maker,
        )

        # Total buyer needs: trade_value + buyer_fee (in quote currency)
        buyer_total = trade_value + buyer_fee
        # Seller needs: amount (in base currency)

        # Create trade record (pending settlement)
        maker_address = sell_order.user_address if taker_is_buy else buy_order.user_address
        taker_address = buy_order.user_address if taker_is_buy else sell_order.user_address
        maker_order_id = sell_order.id if taker_is_buy else buy_order.id
        taker_order_id = buy_order.id if taker_is_buy else sell_order.id
        maker_fee = seller_fee if taker_is_buy else buyer_fee
        taker_fee = buyer_fee if taker_is_buy else seller_fee

        trade = Trade(
            id=str(uuid.uuid4()),
            pair=buy_order.pair,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            buyer_address=buy_order.user_address,
            seller_address=sell_order.user_address,
            price=price,
            amount=amount,
            buyer_fee=buyer_fee,
            seller_fee=seller_fee,
            settlement_status=SettlementStatus.PENDING,
            maker_address=maker_address,
            taker_address=taker_address,
            maker_order_id=maker_order_id,
            taker_order_id=taker_order_id,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
        )

        logger.info(
            "Executing trade settlement",
            extra={
                "event": "exchange.settlement_start",
                "trade_id": trade.id,
                "buyer": buy_order.user_address[:16] + "...",
                "seller": sell_order.user_address[:16] + "...",
                "maker": maker_address[:16] + "...",
                "taker": taker_address[:16] + "...",
                "price": float(price),
                "amount": float(amount),
                "buyer_fee": float(buyer_fee),
                "seller_fee": float(seller_fee),
            }
        )

        # Verify balances before settlement
        buyer_balance = self.balance_provider.get_balance(buy_order.user_address, quote_asset)
        seller_balance = self.balance_provider.get_balance(sell_order.user_address, base_asset)

        if buyer_balance < buyer_total:
            trade.settlement_status = SettlementStatus.FAILED
            trade.settlement_error = f"Insufficient buyer balance: {buyer_balance} < {buyer_total}"
            logger.warning(
                "Trade settlement failed: insufficient buyer balance",
                extra={
                    "event": "exchange.settlement_failed",
                    "trade_id": trade.id,
                    "reason": "insufficient_buyer_balance",
                    "available": float(buyer_balance),
                    "required": float(buyer_total),
                }
            )
            self.trade_history.append(trade)
            return None

        if seller_balance < amount:
            trade.settlement_status = SettlementStatus.FAILED
            trade.settlement_error = f"Insufficient seller balance: {seller_balance} < {amount}"
            logger.warning(
                "Trade settlement failed: insufficient seller balance",
                extra={
                    "event": "exchange.settlement_failed",
                    "trade_id": trade.id,
                    "reason": "insufficient_seller_balance",
                    "available": float(seller_balance),
                    "required": float(amount),
                }
            )
            self.trade_history.append(trade)
            return None

        # Execute atomic settlement
        # Track completed transfers for potential rollback
        completed_transfers: list[dict[str, Any]] = []

        try:
            # Transfer 1: Buyer sends quote currency to seller (minus seller fee)
            seller_receives = trade_value - seller_fee
            tx1 = self.balance_provider.transfer(
                buy_order.user_address,
                sell_order.user_address,
                quote_asset,
                seller_receives,
                context={
                    "trade_id": trade.id,
                    "leg": "quote_to_seller",
                    "asset": quote_asset,
                    "amount": float(seller_receives),
                },
            )
            if not tx1:
                raise SettlementError("Failed to transfer quote currency to seller")
            self._verify_settlement_tx(tx1, "quote_to_seller")
            completed_transfers.append(
                {
                    "from": buy_order.user_address,
                    "to": sell_order.user_address,
                    "asset": quote_asset,
                    "amount": seller_receives,
                    "txid": tx1,
                }
            )

            # Transfer 2: Seller sends base currency to buyer
            tx2 = self.balance_provider.transfer(
                sell_order.user_address,
                buy_order.user_address,
                base_asset,
                amount,
                context={
                    "trade_id": trade.id,
                    "leg": "base_to_buyer",
                    "asset": base_asset,
                    "amount": float(amount),
                },
            )
            if not tx2:
                raise SettlementError("Failed to transfer base currency to buyer")
            self._verify_settlement_tx(tx2, "base_to_buyer")
            completed_transfers.append(
                {
                    "from": sell_order.user_address,
                    "to": buy_order.user_address,
                    "asset": base_asset,
                    "amount": amount,
                    "txid": tx2,
                }
            )

            # Transfer 3: Buyer fee to fee collector
            if buyer_fee > 0:
                tx3 = self.balance_provider.transfer(
                    buy_order.user_address,
                    self.fee_collector_address,
                    quote_asset,
                    buyer_fee,
                    context={
                        "trade_id": trade.id,
                        "leg": "buyer_fee",
                        "asset": quote_asset,
                        "amount": float(buyer_fee),
                    },
                )
                if not tx3:
                    raise SettlementError("Failed to transfer buyer fee")
                self._verify_settlement_tx(tx3, "buyer_fee")
                completed_transfers.append(
                    {
                        "from": buy_order.user_address,
                        "to": self.fee_collector_address,
                        "asset": quote_asset,
                        "amount": buyer_fee,
                        "txid": tx3,
                    }
                )

            # Transfer 4: Seller fee to fee collector (from buyer's payment)
            if seller_fee > 0:
                tx4 = self.balance_provider.transfer(
                    buy_order.user_address,
                    self.fee_collector_address,
                    quote_asset,
                    seller_fee,
                    context={
                        "trade_id": trade.id,
                        "leg": "seller_fee",
                        "asset": quote_asset,
                        "amount": float(seller_fee),
                    },
                )
                if not tx4:
                    raise SettlementError("Failed to transfer seller fee")
                self._verify_settlement_tx(tx4, "seller_fee")
                completed_transfers.append(
                    {
                        "from": buy_order.user_address,
                        "to": self.fee_collector_address,
                        "asset": quote_asset,
                        "amount": seller_fee,
                        "txid": tx4,
                    }
                )

            # Settlement successful
            trade.settlement_status = SettlementStatus.SETTLED
            trade.settlement_txid = tx1  # Use first transfer as primary TXID

        except SettlementError as e:
            # Rollback all completed transfers
            logger.error(
                "Trade settlement failed, rolling back",
                extra={
                    "event": "exchange.settlement_rollback",
                    "trade_id": trade.id,
                    "error": str(e),
                    "transfers_to_rollback": len(completed_transfers),
                }
            )

            for transfer in reversed(completed_transfers):
                self.balance_provider.transfer(
                    transfer["to"],
                    transfer["from"],
                    transfer["asset"],
                    transfer["amount"],
                    context={"rollback_of": transfer["txid"]},
                )

            trade.settlement_status = SettlementStatus.ROLLED_BACK
            trade.settlement_error = str(e)
            self.trade_history.append(trade)
            return None

        # Update order filled amounts
        buy_order.filled += amount
        sell_order.filled += amount

        # Update order status
        if buy_order.is_filled():
            buy_order.status = OrderStatus.FILLED
            order_book = self.get_order_book(buy_order.pair)
            order_book.remove_order(buy_order.id)
        elif buy_order.filled > 0:
            buy_order.status = OrderStatus.PARTIAL

        if sell_order.is_filled():
            sell_order.status = OrderStatus.FILLED
            order_book = self.get_order_book(sell_order.pair)
            order_book.remove_order(sell_order.id)
        elif sell_order.filled > 0:
            sell_order.status = OrderStatus.PARTIAL

        # Add to trade history
        self.trade_history.append(trade)

        # Keep only last 1000 trades
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

        logger.info(
            "Trade settlement completed",
            extra={
                "event": "exchange.settlement_complete",
                "trade_id": trade.id,
                "settlement_txid": trade.settlement_txid,
                "buyer_fee": float(buyer_fee),
                "seller_fee": float(seller_fee),
            }
        )

        # Update last trade price and evaluate stop orders for the pair
        self.last_trade_price[buy_order.pair] = price
        self._check_stop_orders(buy_order.pair)

        return trade

    def cancel_order(self, order_id: str, user_address: str) -> bool:
        """Cancel an order"""
        order = self.active_orders.get(order_id)

        if not order:
            return False

        # Verify user owns the order
        if order.user_address != user_address:
            return False

        # Can only cancel pending or partial orders
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False

        # Update status
        order.status = OrderStatus.CANCELLED

        # Remove from order book or stop queue if pending trigger
        order_book = self.get_order_book(order.pair)
        order_book.remove_order(order_id)
        self._remove_stop_order(order_id)

        return True

    def get_user_orders(self, user_address: str, status: str | None = None) -> list[Order]:
        """Get all orders for a user"""
        order_ids = self.user_orders.get(user_address, [])
        orders = [self.active_orders[oid] for oid in order_ids if oid in self.active_orders]

        if status:
            orders = [o for o in orders if o.status.value == status]

        return orders

    def get_recent_trades(self, pair: str | None = None, limit: int = 20) -> list[Trade]:
        """Get recent trades"""
        trades = self.trade_history

        if pair:
            trades = [t for t in trades if t.pair == pair]

        # Return most recent first
        return sorted(trades, key=lambda t: -t.timestamp)[:limit]

    def calculate_fee(
        self,
        total: Decimal,
        pay_with_xai: bool = False,
        *,
        pay_with_axn: bool | None = None,
        is_maker: bool | None = None,
    ) -> Decimal:
        """
        Calculate trading fee.

        Args:
            total: Trade value in quote currency
            pay_with_xai: If True, apply XAI discount
            pay_with_axn: Legacy alias for pay_with_xai
            is_maker: True to use maker fee, False for taker fee, None for legacy rate

        Returns:
            Fee amount in quote currency
        """
        if pay_with_axn is not None:
            pay_with_xai = pay_with_axn

        if is_maker is None:
            fee_rate = self.fee_rate
        else:
            fee_rate = self.maker_fee_rate if is_maker else self.taker_fee_rate

        fee = total * fee_rate

        if pay_with_xai:
            fee = fee * self.xai_fee_discount

        return fee

    def get_stats(self) -> dict:
        """Get exchange statistics"""
        return {
            "total_pairs": len(self.order_books),
            "active_orders": len(self.active_orders),
            "total_trades": len(self.trade_history),
            "unique_traders": len(self.user_orders),
            "pairs": list(self.order_books.keys()),
            "pending_stop_orders": sum(len(orders) for orders in self.stop_orders.values()),
        }
