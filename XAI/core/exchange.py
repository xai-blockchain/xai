"""
AXN Exchange - Decentralized Order Book and Matching Engine
Handles limit orders, market orders, and trade execution
"""

import time
import uuid
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from trading_fees import fee_manager

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
    filled: Decimal = Decimal('0')  # Amount filled
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
            'id': self.id,
            'user_address': self.user_address,
            'pair': self.pair,
            'side': self.side.value,
            'type': self.order_type.value,
            'price': float(self.price),
            'amount': float(self.amount),
            'filled': float(self.filled),
            'remaining': float(self.remaining()),
            'status': self.status.value,
            'timestamp': self.timestamp,
            'pay_fee_with_axn': self.pay_fee_with_axn
        }

@dataclass
class Trade:
    """Represents an executed trade"""
    id: str
    pair: str
    buy_order_id: str
    sell_order_id: str
    buyer_address: str
    seller_address: str
    price: Decimal
    amount: Decimal
    buyer_fee: Decimal = Decimal('0')
    seller_fee: Decimal = Decimal('0')
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'pair': self.pair,
            'buy_order_id': self.buy_order_id,
            'sell_order_id': self.sell_order_id,
            'buyer': self.buyer_address,
            'seller': self.seller_address,
            'price': float(self.price),
            'amount': float(self.amount),
            'total': float(self.price * self.amount),
            'buyer_fee': float(self.buyer_fee),
            'seller_fee': float(self.seller_fee),
            'timestamp': self.timestamp
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
            'pair': self.pair,
            'bids': [
                {
                    'price': float(o.price),
                    'amount': float(o.remaining()),
                    'total': float(o.price * o.remaining())
                }
                for o in self.buy_orders[:20]  # Top 20 bids
            ],
            'asks': [
                {
                    'price': float(o.price),
                    'amount': float(o.remaining()),
                    'total': float(o.price * o.remaining())
                }
                for o in self.sell_orders[:20]  # Top 20 asks
            ],
            'best_bid': float(self.get_best_bid()) if self.get_best_bid() else None,
            'best_ask': float(self.get_best_ask()) if self.get_best_ask() else None,
            'spread': float(self.get_spread()) if self.get_spread() else None
        }

class MatchingEngine:
    """Order matching engine"""

    def __init__(self, fee_rate: Decimal = Decimal('0.001'), axn_fee_discount: Decimal = Decimal('0.5')):
        self.order_books: Dict[str, OrderBook] = {}
        self.active_orders: Dict[str, Order] = {}  # All active orders
        self.trade_history: List[Trade] = []
        self.user_orders: Dict[str, List[str]] = {}  # user_address -> [order_ids]
        self.fee_rate = fee_rate  # 0.1% default fee
        self.axn_fee_discount = axn_fee_discount  # 50% discount when paying with AXN

    def get_order_book(self, pair: str) -> OrderBook:
        """Get or create order book for pair"""
        if pair not in self.order_books:
            self.order_books[pair] = OrderBook(pair)
        return self.order_books[pair]

    def place_order(self, user_address: str, pair: str, side: str, order_type: str,
                   price: float, amount: float, pay_fee_with_axn: bool = False) -> Order:
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
            price=Decimal(str(price)) if price > 0 else Decimal('0'),
            amount=Decimal(str(amount)),
            pay_fee_with_axn=pay_fee_with_axn
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

    def execute_trade(self, buy_order: Order, sell_order: Order, price: Decimal, amount: Decimal):
        """Execute a trade between two orders"""
        # Calculate trading fees
        trade_value = float(price * amount)

        # Determine if orders are maker or taker
        # Existing order in book = maker, incoming order = taker
        # For simplicity, assume buy order is taker and sell order is maker
        # (In production, track order timestamps to determine this properly)
        buyer_is_maker = False  # Buyer is typically taker (takes liquidity)
        seller_is_maker = True   # Seller order was waiting in book (provides liquidity)

        # Calculate fees based on pair and maker/taker status
        buyer_fee = Decimal(str(fee_manager.calculate_fee(
            buy_order.pair,
            trade_value,
            buyer_is_maker
        )))

        seller_fee = Decimal(str(fee_manager.calculate_fee(
            sell_order.pair,
            trade_value,
            seller_is_maker
        )))

        # Create trade record with fees
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
            seller_fee=seller_fee
        )

        # Update order filled amounts
        buy_order.filled += amount
        sell_order.filled += amount

        # Update order status
        if buy_order.is_filled():
            buy_order.status = OrderStatus.FILLED
            # Remove from order book
            order_book = self.get_order_book(buy_order.pair)
            order_book.remove_order(buy_order.id)
        elif buy_order.filled > 0:
            buy_order.status = OrderStatus.PARTIAL

        if sell_order.is_filled():
            sell_order.status = OrderStatus.FILLED
            # Remove from order book
            order_book = self.get_order_book(sell_order.pair)
            order_book.remove_order(sell_order.id)
        elif sell_order.filled > 0:
            sell_order.status = OrderStatus.PARTIAL

        # Add to trade history
        self.trade_history.append(trade)

        # Keep only last 1000 trades
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

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

    def calculate_fee(self, total: Decimal, pay_with_axn: bool = False) -> Decimal:
        """Calculate trading fee"""
        fee = total * self.fee_rate

        if pay_with_axn:
            fee = fee * self.axn_fee_discount

        return fee

    def get_stats(self) -> dict:
        """Get exchange statistics"""
        return {
            'total_pairs': len(self.order_books),
            'active_orders': len(self.active_orders),
            'total_trades': len(self.trade_history),
            'unique_traders': len(self.user_orders),
            'pairs': list(self.order_books.keys())
        }
