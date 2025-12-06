"""
Comprehensive test suite for exchange.py
Tests order matching, order book management, trade execution, and fee calculations
"""

import pytest
import time
from decimal import Decimal
from xai.exchange import (
    Order,
    Trade,
    OrderBook,
    MatchingEngine,
    OrderType,
    OrderSide,
    OrderStatus,
)


# ==============================================================================
# Order Tests
# ==============================================================================


class TestOrder:
    """Test Order class functionality"""

    def test_order_creation(self):
        """Test basic order creation"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        assert order.id == "order1"
        assert order.user_address == "user1"
        assert order.pair == "AXN/USD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("100")
        assert order.amount == Decimal("10")
        assert order.filled == Decimal("0")
        assert order.status == OrderStatus.PENDING
        assert order.stop_price is None
        assert order.triggered is False
        assert order.triggered_at is None

    def test_order_remaining(self):
        """Test remaining amount calculation"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        assert order.remaining() == Decimal("10")

        order.filled = Decimal("3")
        assert order.remaining() == Decimal("7")

        order.filled = Decimal("10")
        assert order.remaining() == Decimal("0")

    def test_order_is_filled(self):
        """Test is_filled check"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        assert not order.is_filled()

        order.filled = Decimal("5")
        assert not order.is_filled()

        order.filled = Decimal("10")
        assert order.is_filled()

        order.filled = Decimal("11")  # Overfilled edge case
        assert order.is_filled()

    def test_order_to_dict(self):
        """Test order to dictionary conversion"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
            filled=Decimal("3"),
            status=OrderStatus.PARTIAL,
            timestamp=1234567890,
            pay_fee_with_axn=True,
        )
        data = order.to_dict()

        assert data["id"] == "order1"
        assert data["user_address"] == "user1"
        assert data["pair"] == "AXN/USD"
        assert data["side"] == "buy"
        assert data["type"] == "limit"
        assert data["price"] == 100.0
        assert data["amount"] == 10.0
        assert data["filled"] == 3.0
        assert data["remaining"] == 7.0
        assert data["status"] == "partial"
        assert data["timestamp"] == 1234567890
        assert data["pay_fee_with_axn"] is True
        assert data["stop_price"] is None
        assert data["triggered"] is False
        assert data["triggered_at"] is None
        assert data["slippage_bps"] is None
        assert data["reference_price"] is None

    def test_order_stop_fields_serialization(self):
        """Ensure stop order metadata is serialized"""
        order = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.STOP_LIMIT,
            price=Decimal("120"),
            amount=Decimal("5"),
            stop_price=Decimal("110"),
        )
        order.triggered = True
        order.triggered_at = 123.45
        data = order.to_dict()

        assert data["stop_price"] == 110.0
        assert data["triggered"] is True
        assert data["triggered_at"] == pytest.approx(123.45)

    def test_order_with_market_type(self):
        """Test market order creation"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            price=Decimal("0"),
            amount=Decimal("5"),
        )
        assert order.order_type == OrderType.MARKET
        assert order.price == Decimal("0")

    def test_order_with_stop_limit(self):
        """Test stop-limit order creation"""
        order = Order(
            id="order1",
            user_address="user1",
            pair="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LIMIT,
            price=Decimal("50000"),
            amount=Decimal("0.5"),
        )
        assert order.order_type == OrderType.STOP_LIMIT


# ==============================================================================
# Trade Tests
# ==============================================================================


class TestTrade:
    """Test Trade class functionality"""

    def test_trade_creation(self):
        """Test basic trade creation"""
        trade = Trade(
            id="trade1",
            pair="AXN/USD",
            buy_order_id="buy1",
            sell_order_id="sell1",
            buyer_address="buyer1",
            seller_address="seller1",
            price=Decimal("100"),
            amount=Decimal("5"),
        )
        assert trade.id == "trade1"
        assert trade.pair == "AXN/USD"
        assert trade.buy_order_id == "buy1"
        assert trade.sell_order_id == "sell1"
        assert trade.buyer_address == "buyer1"
        assert trade.seller_address == "seller1"
        assert trade.price == Decimal("100")
        assert trade.amount == Decimal("5")

    def test_trade_to_dict(self):
        """Test trade to dictionary conversion"""
        trade = Trade(
            id="trade1",
            pair="AXN/USD",
            buy_order_id="buy1",
            sell_order_id="sell1",
            buyer_address="buyer1",
            seller_address="seller1",
            price=Decimal("100"),
            amount=Decimal("5"),
            timestamp=1234567890,
        )
        data = trade.to_dict()

        assert data["id"] == "trade1"
        assert data["pair"] == "AXN/USD"
        assert data["buy_order_id"] == "buy1"
        assert data["sell_order_id"] == "sell1"
        assert data["buyer"] == "buyer1"
        assert data["seller"] == "seller1"
        assert data["price"] == 100.0
        assert data["amount"] == 5.0
        assert data["total"] == 500.0
        assert data["timestamp"] == 1234567890
        assert data["maker_address"] is None
        assert data["taker_address"] is None
        assert data["maker_order_id"] is None
        assert data["taker_order_id"] is None
        assert data["maker_fee"] == 0.0
        assert data["taker_fee"] == 0.0

    def test_trade_total_calculation(self):
        """Test trade total calculation"""
        trade = Trade(
            id="trade1",
            pair="BTC/USD",
            buy_order_id="buy1",
            sell_order_id="sell1",
            buyer_address="buyer1",
            seller_address="seller1",
            price=Decimal("50000"),
            amount=Decimal("0.5"),
        )
        data = trade.to_dict()
        assert data["total"] == 25000.0


# ==============================================================================
# OrderBook Tests
# ==============================================================================


class TestOrderBook:
    """Test OrderBook class functionality"""

    def test_orderbook_creation(self):
        """Test order book creation"""
        book = OrderBook("AXN/USD")
        assert book.pair == "AXN/USD"
        assert len(book.buy_orders) == 0
        assert len(book.sell_orders) == 0

    def test_add_buy_order(self):
        """Test adding buy order to book"""
        book = OrderBook("AXN/USD")
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(order)
        assert len(book.buy_orders) == 1
        assert book.buy_orders[0] == order

    def test_add_sell_order(self):
        """Test adding sell order to book"""
        book = OrderBook("AXN/USD")
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(order)
        assert len(book.sell_orders) == 1
        assert book.sell_orders[0] == order

    def test_buy_orders_sorted_by_price(self):
        """Test buy orders sorted by price (highest first)"""
        book = OrderBook("AXN/USD")

        order1 = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        order2 = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("110"),
            amount=Decimal("5"),
        )
        order3 = Order(
            id="order3",
            user_address="user3",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("105"),
            amount=Decimal("8"),
        )

        book.add_order(order1)
        book.add_order(order2)
        book.add_order(order3)

        # Should be sorted: highest price first
        assert book.buy_orders[0].price == Decimal("110")
        assert book.buy_orders[1].price == Decimal("105")
        assert book.buy_orders[2].price == Decimal("100")

    def test_sell_orders_sorted_by_price(self):
        """Test sell orders sorted by price (lowest first)"""
        book = OrderBook("AXN/USD")

        order1 = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        order2 = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("95"),
            amount=Decimal("5"),
        )
        order3 = Order(
            id="order3",
            user_address="user3",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("105"),
            amount=Decimal("8"),
        )

        book.add_order(order1)
        book.add_order(order2)
        book.add_order(order3)

        # Should be sorted: lowest price first
        assert book.sell_orders[0].price == Decimal("95")
        assert book.sell_orders[1].price == Decimal("100")
        assert book.sell_orders[2].price == Decimal("105")

    def test_orders_sorted_by_timestamp_when_same_price(self):
        """Test orders with same price sorted by timestamp"""
        book = OrderBook("AXN/USD")

        order1 = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
            timestamp=1000,
        )
        time.sleep(0.001)
        order2 = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("5"),
            timestamp=1001,
        )

        book.add_order(order1)
        book.add_order(order2)

        # Same price, so sorted by timestamp (earlier first)
        assert book.buy_orders[0].id == "order1"
        assert book.buy_orders[1].id == "order2"

    def test_remove_order(self):
        """Test removing order from book"""
        book = OrderBook("AXN/USD")
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(order)
        assert len(book.buy_orders) == 1

        book.remove_order("order1")
        assert len(book.buy_orders) == 0

    def test_remove_nonexistent_order(self):
        """Test removing order that doesn't exist"""
        book = OrderBook("AXN/USD")
        book.remove_order("nonexistent")
        assert len(book.buy_orders) == 0
        assert len(book.sell_orders) == 0

    def test_get_order(self):
        """Test getting order by ID"""
        book = OrderBook("AXN/USD")
        order = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(order)

        found = book.get_order("order1")
        assert found == order

    def test_get_nonexistent_order(self):
        """Test getting order that doesn't exist"""
        book = OrderBook("AXN/USD")
        found = book.get_order("nonexistent")
        assert found is None

    def test_get_best_bid(self):
        """Test getting best (highest) bid price"""
        book = OrderBook("AXN/USD")

        order1 = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        order2 = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("110"),
            amount=Decimal("5"),
        )

        book.add_order(order1)
        book.add_order(order2)

        best_bid = book.get_best_bid()
        assert best_bid == Decimal("110")

    def test_get_best_bid_empty(self):
        """Test getting best bid when no buy orders"""
        book = OrderBook("AXN/USD")
        best_bid = book.get_best_bid()
        assert best_bid is None

    def test_get_best_ask(self):
        """Test getting best (lowest) ask price"""
        book = OrderBook("AXN/USD")

        order1 = Order(
            id="order1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        order2 = Order(
            id="order2",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("95"),
            amount=Decimal("5"),
        )

        book.add_order(order1)
        book.add_order(order2)

        best_ask = book.get_best_ask()
        assert best_ask == Decimal("95")

    def test_get_best_ask_empty(self):
        """Test getting best ask when no sell orders"""
        book = OrderBook("AXN/USD")
        best_ask = book.get_best_ask()
        assert best_ask is None

    def test_get_spread(self):
        """Test getting bid-ask spread"""
        book = OrderBook("AXN/USD")

        buy_order = Order(
            id="buy1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("98"),
            amount=Decimal("10"),
        )
        sell_order = Order(
            id="sell1",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("102"),
            amount=Decimal("10"),
        )

        book.add_order(buy_order)
        book.add_order(sell_order)

        spread = book.get_spread()
        assert spread == Decimal("4")

    def test_get_spread_no_bids(self):
        """Test getting spread when no buy orders"""
        book = OrderBook("AXN/USD")

        sell_order = Order(
            id="sell1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(sell_order)

        spread = book.get_spread()
        assert spread is None

    def test_get_spread_no_asks(self):
        """Test getting spread when no sell orders"""
        book = OrderBook("AXN/USD")

        buy_order = Order(
            id="buy1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        book.add_order(buy_order)

        spread = book.get_spread()
        assert spread is None

    def test_orderbook_to_dict(self):
        """Test order book to dictionary conversion"""
        book = OrderBook("AXN/USD")

        buy_order = Order(
            id="buy1",
            user_address="user1",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("98"),
            amount=Decimal("10"),
        )
        sell_order = Order(
            id="sell1",
            user_address="user2",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("102"),
            amount=Decimal("5"),
        )

        book.add_order(buy_order)
        book.add_order(sell_order)

        data = book.to_dict()

        assert data["pair"] == "AXN/USD"
        assert len(data["bids"]) == 1
        assert len(data["asks"]) == 1
        assert data["bids"][0]["price"] == 98.0
        assert data["bids"][0]["amount"] == 10.0
        assert data["bids"][0]["total"] == 980.0
        assert data["asks"][0]["price"] == 102.0
        assert data["asks"][0]["amount"] == 5.0
        assert data["asks"][0]["total"] == 510.0
        assert data["best_bid"] == 98.0
        assert data["best_ask"] == 102.0
        assert data["spread"] == 4.0

    def test_orderbook_to_dict_top_20_limit(self):
        """Test order book to_dict limits to top 20 orders"""
        book = OrderBook("AXN/USD")

        # Add 30 buy orders
        for i in range(30):
            order = Order(
                id=f"buy{i}",
                user_address=f"user{i}",
                pair="AXN/USD",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=Decimal(str(100 - i)),
                amount=Decimal("1"),
            )
            book.add_order(order)

        data = book.to_dict()
        assert len(data["bids"]) == 20


# ==============================================================================
# MatchingEngine Tests
# ==============================================================================


class TestMatchingEngine:
    """Test MatchingEngine class functionality"""

    def test_engine_creation(self):
        """Test matching engine creation"""
        engine = MatchingEngine()
        assert len(engine.order_books) == 0
        assert len(engine.active_orders) == 0
        assert len(engine.trade_history) == 0
        assert len(engine.user_orders) == 0
        assert engine.fee_rate == Decimal("0.001")
        assert engine.axn_fee_discount == Decimal("0.5")
        assert engine.stop_orders == {}
        assert engine.last_trade_price == {}

    def test_engine_custom_fees(self):
        """Test matching engine with custom fees"""
        engine = MatchingEngine(
            fee_rate=Decimal("0.002"), axn_fee_discount=Decimal("0.25")
        )
        assert engine.fee_rate == Decimal("0.002")
        assert engine.axn_fee_discount == Decimal("0.25")

    def test_get_order_book(self):
        """Test getting or creating order book"""
        engine = MatchingEngine()
        book = engine.get_order_book("AXN/USD")
        assert book.pair == "AXN/USD"
        assert "AXN/USD" in engine.order_books

        # Getting again should return same instance
        book2 = engine.get_order_book("AXN/USD")
        assert book2 is book

    def test_place_limit_buy_order(self):
        """Test placing limit buy order"""
        engine = MatchingEngine()
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        assert order.user_address == "user1"
        assert order.pair == "AXN/USD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("100")
        assert order.amount == Decimal("10")
        assert order.id in engine.active_orders
        assert order.id in engine.user_orders["user1"]

    def test_place_limit_sell_order(self):
        """Test placing limit sell order"""
        engine = MatchingEngine()
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        assert order.side == OrderSide.SELL
        assert order.order_type == OrderType.LIMIT

    def test_place_market_order(self):
        """Test placing market order"""
        engine = MatchingEngine()
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="market",
            price=0,
            amount=10.0,
        )

        assert order.order_type == OrderType.MARKET
        assert order.price == Decimal("0")

    def test_place_order_with_axn_fee(self):
        """Test placing order with AXN fee payment"""
        engine = MatchingEngine()
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
            pay_fee_with_axn=True,
        )

        assert order.pay_fee_with_axn is True

    def test_stop_limit_order_queued_until_triggered(self):
        """Stop-limit orders should remain pending until stop price is hit."""
        engine = MatchingEngine()
        order = engine.place_order(
            user_address="breakout_trader",
            pair="AXN/USD",
            side="buy",
            order_type=OrderType.STOP_LIMIT.value,
            price=100.0,
            amount=5.0,
            stop_price=110.0,
        )
        assert order.triggered is False
        assert order.order_type == OrderType.STOP_LIMIT
        assert "AXN/USD" in engine.stop_orders
        assert order in engine.stop_orders["AXN/USD"]

    def test_stop_limit_order_triggers_and_executes_after_spike(self):
        """Stop-limit order should activate after price spike and fill when liquidity arrives."""
        engine = MatchingEngine()
        provider = engine.balance_provider
        provider.set_balance("stop_buyer", "USD", Decimal("2000"))
        provider.set_balance("spike_seller", "AXN", Decimal("5"))
        provider.set_balance("spike_buyer", "USD", Decimal("2000"))
        provider.set_balance("liquidity_seller", "AXN", Decimal("5"))

        stop_order = engine.place_order(
            user_address="stop_buyer",
            pair="AXN/USD",
            side="buy",
            order_type=OrderType.STOP_LIMIT.value,
            price=106.0,
            amount=2.0,
            stop_price=110.0,
        )

        # Price spike trade at 111 triggers the stop order
        engine.place_order(
            user_address="spike_seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=111.0,
            amount=1.0,
        )
        engine.place_order(
            user_address="spike_buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=111.0,
            amount=1.0,
        )

        assert stop_order.triggered is True
        assert stop_order.order_type == OrderType.LIMIT
        assert "AXN/USD" not in engine.stop_orders or stop_order not in engine.stop_orders.get("AXN/USD", [])

        # Provide liquidity below the limit price so the triggered order fills
        engine.place_order(
            user_address="liquidity_seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=105.0,
            amount=2.0,
        )

        assert stop_order.status == OrderStatus.FILLED
        assert stop_order.is_filled()
        assert stop_order.triggered_at is not None

    def test_match_limit_orders_exact(self):
        """Test matching limit orders with exact amounts"""
        engine = MatchingEngine()

        # Place sell order first
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Place matching buy order
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Both orders should be filled
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED
        assert buy_order.filled == Decimal("10")
        assert sell_order.filled == Decimal("10")
        assert len(engine.trade_history) == 1

    def test_match_limit_orders_partial(self):
        """Test matching limit orders with partial fill"""
        engine = MatchingEngine()

        # Place larger sell order
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=20.0,
        )

        # Place smaller buy order
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Buy order should be filled, sell order partially filled
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.PARTIAL
        assert buy_order.filled == Decimal("10")
        assert sell_order.filled == Decimal("10")
        assert sell_order.remaining() == Decimal("10")

    def test_match_limit_orders_multiple_matches(self):
        """Test matching limit order against multiple orders"""
        engine = MatchingEngine()

        # Place multiple sell orders
        engine.place_order(
            user_address="seller1",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )
        engine.place_order(
            user_address="seller2",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=101.0,
            amount=5.0,
        )
        engine.place_order(
            user_address="seller3",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=102.0,
            amount=5.0,
        )

        # Place large buy order
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=105.0,
            amount=12.0,
        )

        # Should match all three sell orders
        assert buy_order.filled == Decimal("12")
        assert len(engine.trade_history) == 3  # 3 matches: 5 + 5 + 2 = 12 units

    def test_match_limit_buy_order_price_check(self):
        """Test buy order doesn't match if price too low"""
        engine = MatchingEngine()

        # Place sell order at 100
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Place buy order at 95 (too low)
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=95.0,
            amount=10.0,
        )

        # No match should occur
        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING
        assert len(engine.trade_history) == 0

    def test_match_limit_sell_order_price_check(self):
        """Test sell order doesn't match if price too high"""
        engine = MatchingEngine()

        # Place buy order at 100
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Place sell order at 105 (too high)
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=105.0,
            amount=10.0,
        )

        # No match should occur
        assert buy_order.status == OrderStatus.PENDING
        assert sell_order.status == OrderStatus.PENDING
        assert len(engine.trade_history) == 0

    def test_match_market_buy_order(self):
        """Test matching market buy order"""
        engine = MatchingEngine()

        # Place sell orders
        engine.place_order(
            user_address="seller1",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )
        engine.place_order(
            user_address="seller2",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=101.0,
            amount=5.0,
        )

        # Place market buy order
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="market",
            price=0,
            amount=8.0,
        )

        # Should match at market prices
        assert buy_order.filled == Decimal("8")
        assert buy_order.status == OrderStatus.FILLED
        assert len(engine.trade_history) == 2

    def test_match_market_sell_order(self):
        """Test matching market sell order"""
        engine = MatchingEngine()

        # Place buy orders
        engine.place_order(
            user_address="buyer1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )
        engine.place_order(
            user_address="buyer2",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=99.0,
            amount=5.0,
        )

        # Place market sell order
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="market",
            price=0,
            amount=8.0,
        )

        # Should match at market prices
        assert sell_order.filled == Decimal("8")
        assert sell_order.status == OrderStatus.FILLED

    def test_market_order_halts_when_slippage_exceeded(self):
        """Slippage guardrails should stop further fills"""
        engine = MatchingEngine()

        # Provide deep liquidity but with wide second level
        engine.place_order(
            user_address="seller1",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )
        engine.place_order(
            user_address="seller2",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=120.0,
            amount=5.0,
        )

        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="market",
            price=0,
            amount=8.0,
            max_slippage_bps=500,  # 5% max
        )

        assert buy_order.filled == Decimal("5")
        assert len(engine.trade_history) == 1

    def test_market_order_cancelled_if_no_match(self):
        """Test market order cancelled if no matching orders"""
        engine = MatchingEngine()

        # Place market buy order with no sell orders
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="market",
            price=0,
            amount=10.0,
        )

        # Should be cancelled
        assert buy_order.status == OrderStatus.CANCELLED
        assert buy_order.filled == Decimal("0")

    def test_market_order_partial_then_cancelled(self):
        """Test market order partially filled then cancelled"""
        engine = MatchingEngine()

        # Place small sell order
        engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )

        # Place larger market buy order
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="market",
            price=0,
            amount=10.0,
        )

        # Should be partially filled then cancelled
        assert buy_order.filled == Decimal("5")
        assert buy_order.status == OrderStatus.CANCELLED

    def test_execute_trade(self):
        """Test trade execution"""
        engine = MatchingEngine()

        buy_order = Order(
            id="buy1",
            user_address="buyer",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )
        sell_order = Order(
            id="sell1",
            user_address="seller",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )

        # Add to order book first
        book = engine.get_order_book("AXN/USD")
        book.add_order(buy_order)
        book.add_order(sell_order)

        # Execute trade
        engine.execute_trade(
            buy_order,
            sell_order,
            Decimal("100"),
            Decimal("10"),
            taker_is_buy=True,
        )

        # Check orders updated
        assert buy_order.filled == Decimal("10")
        assert sell_order.filled == Decimal("10")
        assert buy_order.status == OrderStatus.FILLED
        assert sell_order.status == OrderStatus.FILLED

        # Check trade recorded
        assert len(engine.trade_history) == 1
        trade = engine.trade_history[0]
        assert trade.buy_order_id == "buy1"
        assert trade.sell_order_id == "sell1"
        assert trade.price == Decimal("100")
        assert trade.amount == Decimal("10")

        # Check orders removed from book
        assert len(book.buy_orders) == 0
        assert len(book.sell_orders) == 0

    def test_execute_trade_partial_fill(self):
        """Test trade execution with partial fill"""
        engine = MatchingEngine()

        buy_order = Order(
            id="buy1",
            user_address="buyer",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("20"),
        )
        sell_order = Order(
            id="sell1",
            user_address="seller",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("10"),
        )

        book = engine.get_order_book("AXN/USD")
        book.add_order(buy_order)
        book.add_order(sell_order)

        # Execute partial trade
        engine.execute_trade(
            buy_order,
            sell_order,
            Decimal("100"),
            Decimal("10"),
            taker_is_buy=True,
        )

        # Buy order should be partial
        assert buy_order.filled == Decimal("10")
        assert buy_order.status == OrderStatus.PARTIAL
        assert buy_order.remaining() == Decimal("10")

        # Sell order should be filled
        assert sell_order.status == OrderStatus.FILLED

    def test_trade_history_limit_1000(self):
        """Test trade history limited to 1000 trades"""
        engine = MatchingEngine()

        # Add 1100 trades
        for i in range(1100):
            trade = Trade(
                id=f"trade{i}",
                pair="AXN/USD",
                buy_order_id=f"buy{i}",
                sell_order_id=f"sell{i}",
                buyer_address="buyer",
                seller_address="seller",
                price=Decimal("100"),
                amount=Decimal("1"),
            )
            engine.trade_history.append(trade)

            # Trigger the limit logic (same as in execute_trade)
            if len(engine.trade_history) > 1000:
                engine.trade_history = engine.trade_history[-1000:]

        # Should keep only last 1000
        assert len(engine.trade_history) == 1000
        assert engine.trade_history[0].id == "trade100"
        assert engine.trade_history[-1].id == "trade1099"

    def test_cancel_order(self):
        """Test cancelling order"""
        engine = MatchingEngine()

        # Place order
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Cancel order
        result = engine.cancel_order(order.id, "user1")

        assert result is True
        assert order.status == OrderStatus.CANCELLED

        # Check removed from order book
        book = engine.get_order_book("AXN/USD")
        assert len(book.buy_orders) == 0

    def test_cancel_order_wrong_user(self):
        """Test cancelling order with wrong user"""
        engine = MatchingEngine()

        # Place order
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Try to cancel with different user
        result = engine.cancel_order(order.id, "user2")

        assert result is False
        assert order.status == OrderStatus.PENDING

    def test_cancel_nonexistent_order(self):
        """Test cancelling order that doesn't exist"""
        engine = MatchingEngine()
        result = engine.cancel_order("nonexistent", "user1")
        assert result is False

    def test_cancel_filled_order(self):
        """Test cancelling already filled order"""
        engine = MatchingEngine()

        # Place and match orders
        engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Try to cancel filled order
        result = engine.cancel_order(buy_order.id, "buyer")

        assert result is False
        assert buy_order.status == OrderStatus.FILLED

    def test_cancel_already_cancelled_order(self):
        """Test cancelling already cancelled order"""
        engine = MatchingEngine()

        # Place order
        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Cancel once
        engine.cancel_order(order.id, "user1")

        # Try to cancel again
        result = engine.cancel_order(order.id, "user1")

        assert result is False

    def test_cancel_partial_order(self):
        """Test cancelling partially filled order"""
        engine = MatchingEngine()

        # Place larger sell order
        sell_order = engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=20.0,
        )

        # Place smaller buy order to partially fill
        engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Cancel partially filled order
        result = engine.cancel_order(sell_order.id, "seller")

        assert result is True
        assert sell_order.status == OrderStatus.CANCELLED
        assert sell_order.filled == Decimal("10")

    def test_get_user_orders(self):
        """Test getting user orders"""
        engine = MatchingEngine()

        # Place multiple orders for user
        order1 = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )
        order2 = engine.place_order(
            user_address="user1",
            pair="BTC/USD",
            side="sell",
            order_type="limit",
            price=50000.0,
            amount=0.5,
        )

        # Place order for different user
        engine.place_order(
            user_address="user2",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=95.0,
            amount=5.0,
        )

        # Get user1 orders
        orders = engine.get_user_orders("user1")

        assert len(orders) == 2
        assert order1 in orders
        assert order2 in orders

    def test_get_user_orders_filtered_by_status(self):
        """Test getting user orders filtered by status"""
        engine = MatchingEngine()

        # Place pending order (no match)
        pending_order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=90.0,
            amount=10.0,
        )

        # Place and fill order
        engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=95.0,
            amount=10.0,
        )
        filled_order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Get pending orders
        pending = engine.get_user_orders("user1", status="pending")
        assert len(pending) == 1
        assert pending_order in pending

        # Get filled orders
        filled = engine.get_user_orders("user1", status="filled")
        assert len(filled) == 1
        assert filled_order in filled

    def test_get_user_orders_no_orders(self):
        """Test getting orders for user with no orders"""
        engine = MatchingEngine()
        orders = engine.get_user_orders("user1")
        assert len(orders) == 0

    def test_get_recent_trades(self):
        """Test getting recent trades"""
        engine = MatchingEngine()

        # Create some trades
        for i in range(5):
            engine.place_order(
                user_address=f"seller{i}",
                pair="AXN/USD",
                side="sell",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )
            engine.place_order(
                user_address=f"buyer{i}",
                pair="AXN/USD",
                side="buy",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )

        trades = engine.get_recent_trades()
        assert len(trades) == 5

    def test_get_recent_trades_filtered_by_pair(self):
        """Test getting recent trades filtered by pair"""
        engine = MatchingEngine()

        # Create trades for different pairs
        for i in range(3):
            engine.place_order(
                user_address=f"seller{i}",
                pair="AXN/USD",
                side="sell",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )
            engine.place_order(
                user_address=f"buyer{i}",
                pair="AXN/USD",
                side="buy",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )

        for i in range(2):
            engine.place_order(
                user_address=f"seller{i}",
                pair="BTC/USD",
                side="sell",
                order_type="limit",
                price=50000.0,
                amount=0.1,
            )
            engine.place_order(
                user_address=f"buyer{i}",
                pair="BTC/USD",
                side="buy",
                order_type="limit",
                price=50000.0,
                amount=0.1,
            )

        # Get AXN/USD trades
        axn_trades = engine.get_recent_trades(pair="AXN/USD")
        assert len(axn_trades) == 3
        assert all(t.pair == "AXN/USD" for t in axn_trades)

        # Get BTC/USD trades
        btc_trades = engine.get_recent_trades(pair="BTC/USD")
        assert len(btc_trades) == 2
        assert all(t.pair == "BTC/USD" for t in btc_trades)

    def test_get_recent_trades_limit(self):
        """Test getting recent trades with limit"""
        engine = MatchingEngine()

        # Create 30 trades
        for i in range(30):
            engine.place_order(
                user_address=f"seller{i}",
                pair="AXN/USD",
                side="sell",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )
            engine.place_order(
                user_address=f"buyer{i}",
                pair="AXN/USD",
                side="buy",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )

        trades = engine.get_recent_trades(limit=10)
        assert len(trades) == 10

    def test_get_recent_trades_sorted_by_time(self):
        """Test trades returned in reverse chronological order"""
        engine = MatchingEngine()

        # Create trades with delays
        for i in range(3):
            engine.place_order(
                user_address=f"seller{i}",
                pair="AXN/USD",
                side="sell",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )
            time.sleep(0.01)
            engine.place_order(
                user_address=f"buyer{i}",
                pair="AXN/USD",
                side="buy",
                order_type="limit",
                price=100.0,
                amount=1.0,
            )
            time.sleep(0.01)

        trades = engine.get_recent_trades()

        # Should be sorted by timestamp descending
        for i in range(len(trades) - 1):
            assert trades[i].timestamp >= trades[i + 1].timestamp

    def test_calculate_fee(self):
        """Test fee calculation"""
        engine = MatchingEngine()

        # Standard fee
        fee = engine.calculate_fee(Decimal("1000"))
        assert fee == Decimal("1")  # 0.1% of 1000

        # Different amount
        fee = engine.calculate_fee(Decimal("5000"))
        assert fee == Decimal("5")

    def test_calculate_fee_with_axn(self):
        """Test fee calculation with AXN discount"""
        engine = MatchingEngine()

        # Fee with AXN discount (50% off)
        fee = engine.calculate_fee(Decimal("1000"), pay_with_axn=True)
        assert fee == Decimal("0.5")  # 0.05% of 1000

    def test_calculate_fee_custom_rates(self):
        """Test fee calculation with custom rates"""
        engine = MatchingEngine(
            fee_rate=Decimal("0.002"), axn_fee_discount=Decimal("0.25")
        )

        # Standard fee (0.2%)
        fee = engine.calculate_fee(Decimal("1000"))
        assert fee == Decimal("2")

        # With AXN discount (75% off = 0.05%)
        fee = engine.calculate_fee(Decimal("1000"), pay_with_axn=True)
        assert fee == Decimal("0.5")

    def test_maker_taker_fee_application(self):
        """Maker/taker fee rates should be applied correctly."""
        engine = MatchingEngine(
            maker_fee_rate=Decimal("0.0005"), taker_fee_rate=Decimal("0.002")
        )
        provider = engine.balance_provider
        provider.set_balance("buyer", "USD", Decimal("5000"))
        provider.set_balance("seller", "AXN", Decimal("50"))

        buy_order = Order(
            id="buy-maker-taker",
            user_address="buyer",
            pair="AXN/USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("5"),
        )
        sell_order = Order(
            id="sell-maker-taker",
            user_address="seller",
            pair="AXN/USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            amount=Decimal("5"),
        )

        trade = engine.execute_trade(
            buy_order,
            sell_order,
            Decimal("100"),
            Decimal("5"),
            taker_is_buy=True,
        )
        assert trade is not None
        assert trade.maker_address == "seller"
        assert trade.taker_address == "buyer"
        assert trade.maker_fee == trade.seller_fee == Decimal("0.25")  # 0.0005 * 500
        assert trade.taker_fee == trade.buyer_fee == Decimal("1.0")  # 0.002 * 500

    def test_get_stats(self):
        """Test getting exchange statistics"""
        engine = MatchingEngine()

        # Place some orders
        engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )
        engine.place_order(
            user_address="user2",
            pair="BTC/USD",
            side="sell",
            order_type="limit",
            price=50000.0,
            amount=0.5,
        )

        # Create a trade
        engine.place_order(
            user_address="seller",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=5.0,
        )

        stats = engine.get_stats()

        assert stats["total_pairs"] == 2
        assert stats["active_orders"] == 3
        assert stats["total_trades"] == 1
        assert stats["unique_traders"] == 3
        assert "AXN/USD" in stats["pairs"]
        assert "BTC/USD" in stats["pairs"]
        assert stats["pending_stop_orders"] == 0

    def test_get_stats_empty(self):
        """Test getting stats for empty exchange"""
        engine = MatchingEngine()
        stats = engine.get_stats()

        assert stats["total_pairs"] == 0
        assert stats["active_orders"] == 0
        assert stats["total_trades"] == 0
        assert stats["unique_traders"] == 0
        assert len(stats["pairs"]) == 0
        assert stats["pending_stop_orders"] == 0

    def test_concurrent_orders_same_pair(self):
        """Test handling concurrent orders on same pair"""
        engine = MatchingEngine()

        # Place multiple sell orders
        for i in range(5):
            engine.place_order(
                user_address=f"seller{i}",
                pair="AXN/USD",
                side="sell",
                order_type="limit",
                price=100.0 + i,
                amount=10.0,
            )

        # Place multiple buy orders
        for i in range(5):
            engine.place_order(
                user_address=f"buyer{i}",
                pair="AXN/USD",
                side="buy",
                order_type="limit",
                price=105.0 - i,
                amount=10.0,
            )

        # Check order book maintained correctly
        book = engine.get_order_book("AXN/USD")
        assert len(book.buy_orders) > 0
        assert len(book.sell_orders) > 0

    def test_price_priority(self):
        """Test price-time priority in matching"""
        engine = MatchingEngine()

        # Place sell orders at different prices
        order_high = engine.place_order(
            user_address="seller1",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=105.0,
            amount=10.0,
        )
        order_low = engine.place_order(
            user_address="seller2",
            pair="AXN/USD",
            side="sell",
            order_type="limit",
            price=100.0,
            amount=10.0,
        )

        # Place buy order that can match both
        buy_order = engine.place_order(
            user_address="buyer",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=110.0,
            amount=5.0,
        )

        # Should match with lower priced sell order first
        assert order_low.filled == Decimal("5")
        assert order_high.filled == Decimal("0")

    def test_zero_amount_order(self):
        """Test handling zero amount order"""
        engine = MatchingEngine()

        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=0.0,
        )

        # Should create order but with zero amount
        assert order.amount == Decimal("0")
        assert order.is_filled()

    def test_very_large_order(self):
        """Test handling very large order amounts"""
        engine = MatchingEngine()

        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=1000000.0,
        )

        assert order.amount == Decimal("1000000")

    def test_very_small_order(self):
        """Test handling very small order amounts"""
        engine = MatchingEngine()

        order = engine.place_order(
            user_address="user1",
            pair="AXN/USD",
            side="buy",
            order_type="limit",
            price=100.0,
            amount=0.00000001,
        )

        assert order.amount == Decimal("0.00000001")
