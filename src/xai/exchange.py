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

import logging
import time
import uuid
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import json

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
    settlement_txid: Optional[str] = None
    settlement_error: Optional[str] = None

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
        }


class OrderBook:
    """Order book for a single trading pair"""

    def __init__(self, pair: str):
        self.pair = pair
        self.buy_orders: List[Order] = []  # Sorted by price (highest first)
        self.sell_orders: List[Order] = []  # Sorted by price (lowest first)

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

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        for order in self.buy_orders + self.sell_orders:
            if order.id == order_id:
                return order
        return None

    def get_best_bid(self) -> Optional[Decimal]:
        """Get highest buy price"""
        if self.buy_orders:
            return self.buy_orders[0].price
        return None

    def get_best_ask(self) -> Optional[Decimal]:
        """Get lowest sell price"""
        if self.sell_orders:
            return self.sell_orders[0].price
        return None

    def get_spread(self) -> Optional[Decimal]:
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


class BalanceProvider:
    """
    Interface for balance management.

    Implementations must provide atomic balance operations for settlement.
    """

    def get_balance(self, address: str, asset: str) -> Decimal:
        """Get balance for an address and asset."""
        raise NotImplementedError

    def reserve_balance(self, address: str, asset: str, amount: Decimal) -> bool:
        """
        Reserve balance for a pending trade.

        Returns True if reservation succeeded, False if insufficient balance.
        """
        raise NotImplementedError

    def release_reservation(self, address: str, asset: str, amount: Decimal) -> bool:
        """Release a previous reservation (on trade cancellation/rollback)."""
        raise NotImplementedError

    def transfer(
        self, from_address: str, to_address: str, asset: str, amount: Decimal
    ) -> Optional[str]:
        """
        Execute atomic transfer between addresses.

        Returns transaction ID if successful, None if failed.
        """
        raise NotImplementedError


class InMemoryBalanceProvider(BalanceProvider):
    """
    In-memory balance provider for testing and development.

    WARNING: This is NOT suitable for production. Use a proper
    blockchain-backed implementation for mainnet.
    """

    def __init__(self):
        self.balances: Dict[str, Dict[str, Decimal]] = {}  # address -> {asset -> balance}
        self.reservations: Dict[str, Dict[str, Decimal]] = {}  # address -> {asset -> reserved}
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
        self, from_address: str, to_address: str, asset: str, amount: Decimal
    ) -> Optional[str]:
        """Execute atomic transfer."""
        # Check balance
        from_balance = self.balances.get(from_address, {}).get(asset, Decimal("0"))
        if from_balance < amount:
            return None

        # Execute transfer
        self.balances[from_address][asset] = from_balance - amount
        if to_address not in self.balances:
            self.balances[to_address] = {}
        to_balance = self.balances[to_address].get(asset, Decimal("0"))
        self.balances[to_address][asset] = to_balance + amount

        # Generate transaction ID
        self._tx_counter += 1
        return f"TX{self._tx_counter:08d}"


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
        balance_provider: Optional[BalanceProvider] = None,
        fee_collector_address: str = "XAI_FEE_COLLECTOR",
    ):
        """
        Initialize matching engine.

        Args:
            fee_rate: Trading fee rate (default 0.1%)
            xai_fee_discount: Discount when paying fees with XAI (default 50%)
            balance_provider: Provider for balance operations (uses in-memory for dev if None)
            fee_collector_address: Address to receive trading fees
        """
        self.order_books: Dict[str, OrderBook] = {}
        self.active_orders: Dict[str, Order] = {}
        self.trade_history: List[Trade] = []
        self.user_orders: Dict[str, List[str]] = {}
        self.fee_rate = fee_rate
        self.xai_fee_discount = xai_fee_discount
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
                "xai_discount": float(xai_fee_discount)
            }
        )

    def get_order_book(self, pair: str) -> OrderBook:
        """Get or create order book for pair"""
        if pair not in self.order_books:
            self.order_books[pair] = OrderBook(pair)
        return self.order_books[pair]

    def place_order(
        self,
        user_address: str,
        pair: str,
        side: str,
        order_type: str,
        price: float,
        amount: float,
        pay_fee_with_axn: bool = False,
    ) -> Order:
        """Place a new order"""
        # Generate order ID
        order_id = str(uuid.uuid4())

        # Create order
        order = Order(
            id=order_id,
            user_address=user_address,
            pair=pair,
            side=OrderSide(side.lower()),
            order_type=OrderType(order_type.lower()),
            price=Decimal(str(price)) if price > 0 else Decimal("0"),
            amount=Decimal(str(amount)),
            pay_fee_with_axn=pay_fee_with_axn,
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
        else:
            self.match_limit_order(order)

        # If order still has remaining amount, add to order book
        if not order.is_filled() and order.status != OrderStatus.CANCELLED:
            order_book = self.get_order_book(pair)
            order_book.add_order(order)

        return order

    def match_market_order(self, order: Order):
        """Match a market order immediately"""
        order_book = self.get_order_book(order.pair)

        if order.side == OrderSide.BUY:
            # Match with sell orders (take from lowest price)
            for sell_order in order_book.sell_orders[:]:
                if order.is_filled():
                    break

                # Execute trade
                trade_amount = min(order.remaining(), sell_order.remaining())
                self.execute_trade(order, sell_order, sell_order.price, trade_amount)

        else:  # SELL
            # Match with buy orders (take from highest price)
            for buy_order in order_book.buy_orders[:]:
                if order.is_filled():
                    break

                # Execute trade
                trade_amount = min(order.remaining(), buy_order.remaining())
                self.execute_trade(buy_order, order, buy_order.price, trade_amount)

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
                    self.execute_trade(order, sell_order, sell_order.price, trade_amount)
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
                    self.execute_trade(buy_order, order, buy_order.price, trade_amount)
                else:
                    break  # No more matches

    def execute_trade(self, buy_order: Order, sell_order: Order, price: Decimal, amount: Decimal) -> Optional[Trade]:
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
        buyer_fee = self.calculate_fee(trade_value, buy_order.pay_fee_with_axn)
        seller_fee = self.calculate_fee(trade_value, sell_order.pay_fee_with_axn)

        # Total buyer needs: trade_value + buyer_fee (in quote currency)
        buyer_total = trade_value + buyer_fee
        # Seller needs: amount (in base currency)

        # Create trade record (pending settlement)
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
        )

        logger.info(
            "Executing trade settlement",
            extra={
                "event": "exchange.settlement_start",
                "trade_id": trade.id,
                "buyer": buy_order.user_address[:16] + "...",
                "seller": sell_order.user_address[:16] + "...",
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
        completed_transfers: List[Tuple[str, str, str, Decimal]] = []

        try:
            # Transfer 1: Buyer sends quote currency to seller (minus seller fee)
            seller_receives = trade_value - seller_fee
            tx1 = self.balance_provider.transfer(
                buy_order.user_address, sell_order.user_address, quote_asset, seller_receives
            )
            if not tx1:
                raise SettlementError("Failed to transfer quote currency to seller")
            completed_transfers.append((buy_order.user_address, sell_order.user_address, quote_asset, seller_receives))

            # Transfer 2: Seller sends base currency to buyer
            tx2 = self.balance_provider.transfer(
                sell_order.user_address, buy_order.user_address, base_asset, amount
            )
            if not tx2:
                raise SettlementError("Failed to transfer base currency to buyer")
            completed_transfers.append((sell_order.user_address, buy_order.user_address, base_asset, amount))

            # Transfer 3: Buyer fee to fee collector
            if buyer_fee > 0:
                tx3 = self.balance_provider.transfer(
                    buy_order.user_address, self.fee_collector_address, quote_asset, buyer_fee
                )
                if not tx3:
                    raise SettlementError("Failed to transfer buyer fee")
                completed_transfers.append((buy_order.user_address, self.fee_collector_address, quote_asset, buyer_fee))

            # Transfer 4: Seller fee to fee collector (from buyer's payment)
            if seller_fee > 0:
                tx4 = self.balance_provider.transfer(
                    buy_order.user_address, self.fee_collector_address, quote_asset, seller_fee
                )
                if not tx4:
                    raise SettlementError("Failed to transfer seller fee")
                completed_transfers.append((buy_order.user_address, self.fee_collector_address, quote_asset, seller_fee))

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

            for from_addr, to_addr, asset, amt in reversed(completed_transfers):
                # Reverse the transfer
                self.balance_provider.transfer(to_addr, from_addr, asset, amt)

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

        # Remove from order book
        order_book = self.get_order_book(order.pair)
        order_book.remove_order(order_id)

        return True

    def get_user_orders(self, user_address: str, status: Optional[str] = None) -> List[Order]:
        """Get all orders for a user"""
        order_ids = self.user_orders.get(user_address, [])
        orders = [self.active_orders[oid] for oid in order_ids if oid in self.active_orders]

        if status:
            orders = [o for o in orders if o.status.value == status]

        return orders

    def get_recent_trades(self, pair: Optional[str] = None, limit: int = 20) -> List[Trade]:
        """Get recent trades"""
        trades = self.trade_history

        if pair:
            trades = [t for t in trades if t.pair == pair]

        # Return most recent first
        return sorted(trades, key=lambda t: -t.timestamp)[:limit]

    def calculate_fee(self, total: Decimal, pay_with_xai: bool = False) -> Decimal:
        """
        Calculate trading fee.

        Args:
            total: Trade value in quote currency
            pay_with_xai: If True, apply XAI discount

        Returns:
            Fee amount in quote currency
        """
        fee = total * self.fee_rate

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
        }
