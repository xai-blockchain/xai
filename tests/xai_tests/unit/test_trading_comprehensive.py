"""
Comprehensive test suite for trading.py to achieve 98%+ coverage.

Tests all trading operations including:
- Trade orders (creation, management, status)
- Trade matches (creation, matching logic)
- Order types and statuses
- Trade manager operations
- Serialization and conversion
- Edge cases and validation
"""

import pytest
import time
from xai.core.transactions.trading import (
    SwapOrderType,
    OrderStatus,
    TradeMatchStatus,
    TradeOrder,
    TradeMatch,
    TradeManager
)


class TestSwapOrderType:
    """Test SwapOrderType enum"""

    def test_swap_order_type_buy(self):
        """Test BUY order type"""
        order_type = SwapOrderType.BUY

        assert order_type.value == "buy"

    def test_swap_order_type_sell(self):
        """Test SELL order type"""
        order_type = SwapOrderType.SELL

        assert order_type.value == "sell"

    def test_swap_order_type_enum_values(self):
        """Test all enum values exist"""
        types = [e.value for e in SwapOrderType]

        assert "buy" in types
        assert "sell" in types
        assert len(types) == 2


class TestOrderStatus:
    """Test OrderStatus enum"""

    def test_order_status_pending(self):
        """Test PENDING status"""
        status = OrderStatus.PENDING

        assert status.value == "pending"

    def test_order_status_matched(self):
        """Test MATCHED status"""
        status = OrderStatus.MATCHED

        assert status.value == "matched"

    def test_order_status_completed(self):
        """Test COMPLETED status"""
        status = OrderStatus.COMPLETED

        assert status.value == "completed"

    def test_order_status_cancelled(self):
        """Test CANCELLED status"""
        status = OrderStatus.CANCELLED

        assert status.value == "cancelled"

    def test_order_status_expired(self):
        """Test EXPIRED status"""
        status = OrderStatus.EXPIRED

        assert status.value == "expired"

    def test_order_status_all_values(self):
        """Test all order status values"""
        statuses = [e.value for e in OrderStatus]

        assert "pending" in statuses
        assert "matched" in statuses
        assert "completed" in statuses
        assert "cancelled" in statuses
        assert "expired" in statuses
        assert len(statuses) == 5


class TestTradeMatchStatus:
    """Test TradeMatchStatus enum"""

    def test_trade_match_status_pending(self):
        """Test PENDING match status"""
        status = TradeMatchStatus.PENDING

        assert status.value == "pending"

    def test_trade_match_status_matched(self):
        """Test MATCHED match status"""
        status = TradeMatchStatus.MATCHED

        assert status.value == "matched"

    def test_trade_match_status_confirmed(self):
        """Test CONFIRMED match status"""
        status = TradeMatchStatus.CONFIRMED

        assert status.value == "confirmed"

    def test_trade_match_status_settled(self):
        """Test SETTLED match status"""
        status = TradeMatchStatus.SETTLED

        assert status.value == "settled"

    def test_trade_match_status_failed(self):
        """Test FAILED match status"""
        status = TradeMatchStatus.FAILED

        assert status.value == "failed"

    def test_trade_match_status_all_values(self):
        """Test all match status values"""
        statuses = [e.value for e in TradeMatchStatus]

        assert "pending" in statuses
        assert "matched" in statuses
        assert "confirmed" in statuses
        assert "settled" in statuses
        assert "failed" in statuses
        assert len(statuses) == 5


class TestTradeOrderCreation:
    """Test TradeOrder dataclass creation"""

    def test_trade_order_basic_creation(self):
        """Test basic trade order creation"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.order_id == "order1"
        assert order.order_type == SwapOrderType.BUY
        assert order.amount == 10.0
        assert order.price == 100.0
        assert order.user_address == "XAI123"
        assert order.status == OrderStatus.PENDING

    def test_trade_order_with_timestamp(self):
        """Test trade order with explicit timestamp"""
        timestamp = time.time()
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.SELL,
            amount=5.0,
            price=50.0,
            user_address="XAI456",
            timestamp=timestamp
        )

        assert order.timestamp == timestamp

    def test_trade_order_auto_timestamp(self):
        """Test trade order auto-generates timestamp"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.timestamp is not None
        assert isinstance(order.timestamp, float)
        assert order.timestamp <= time.time()

    def test_trade_order_with_custom_status(self):
        """Test trade order with custom status"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123",
            status=OrderStatus.COMPLETED
        )

        assert order.status == OrderStatus.COMPLETED

    def test_trade_order_buy_type(self):
        """Test creating BUY order"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.order_type == SwapOrderType.BUY

    def test_trade_order_sell_type(self):
        """Test creating SELL order"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.SELL,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.order_type == SwapOrderType.SELL


class TestTradeOrderConversion:
    """Test TradeOrder to_dict conversion"""

    def test_trade_order_to_dict(self):
        """Test converting order to dictionary"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        data = order.to_dict()

        assert isinstance(data, dict)
        assert data["order_id"] == "order1"
        assert data["order_type"] == "buy"
        assert data["amount"] == 10.0
        assert data["price"] == 100.0
        assert data["user_address"] == "XAI123"
        assert data["status"] == "pending"
        assert "timestamp" in data

    def test_trade_order_to_dict_all_fields(self):
        """Test to_dict includes all fields"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.SELL,
            amount=5.0,
            price=50.0,
            user_address="XAI456",
            status=OrderStatus.MATCHED
        )

        data = order.to_dict()

        assert "order_id" in data
        assert "order_type" in data
        assert "amount" in data
        assert "price" in data
        assert "user_address" in data
        assert "timestamp" in data
        assert "status" in data

    def test_trade_order_to_dict_enum_serialization(self):
        """Test enums are serialized to strings"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123",
            status=OrderStatus.COMPLETED
        )

        data = order.to_dict()

        assert isinstance(data["order_type"], str)
        assert isinstance(data["status"], str)


class TestTradeMatchCreation:
    """Test TradeMatch dataclass creation"""

    def test_trade_match_basic_creation(self):
        """Test basic trade match creation"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )

        assert match.match_id == "match1"
        assert match.buy_order_id == "order1"
        assert match.sell_order_id == "order2"
        assert match.amount == 10.0
        assert match.price == 100.0
        assert match.status == TradeMatchStatus.PENDING

    def test_trade_match_with_timestamp(self):
        """Test trade match with explicit timestamp"""
        timestamp = time.time()
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0,
            timestamp=timestamp
        )

        assert match.timestamp == timestamp

    def test_trade_match_auto_timestamp(self):
        """Test trade match auto-generates timestamp"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )

        assert match.timestamp is not None
        assert isinstance(match.timestamp, float)
        assert match.timestamp <= time.time()

    def test_trade_match_with_custom_status(self):
        """Test trade match with custom status"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0,
            status=TradeMatchStatus.SETTLED
        )

        assert match.status == TradeMatchStatus.SETTLED

    def test_trade_match_fractional_amounts(self):
        """Test trade match with fractional amounts"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=0.123456,
            price=99.999
        )

        assert match.amount == 0.123456
        assert match.price == 99.999


class TestTradeMatchConversion:
    """Test TradeMatch to_dict conversion"""

    def test_trade_match_to_dict(self):
        """Test converting match to dictionary"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )

        data = match.to_dict()

        assert isinstance(data, dict)
        assert data["match_id"] == "match1"
        assert data["buy_order_id"] == "order1"
        assert data["sell_order_id"] == "order2"
        assert data["amount"] == 10.0
        assert data["price"] == 100.0
        assert data["status"] == "pending"
        assert "timestamp" in data

    def test_trade_match_to_dict_all_fields(self):
        """Test to_dict includes all fields"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=5.0,
            price=50.0,
            status=TradeMatchStatus.CONFIRMED
        )

        data = match.to_dict()

        assert "match_id" in data
        assert "buy_order_id" in data
        assert "sell_order_id" in data
        assert "amount" in data
        assert "price" in data
        assert "timestamp" in data
        assert "status" in data

    def test_trade_match_to_dict_enum_serialization(self):
        """Test status enum is serialized to string"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0,
            status=TradeMatchStatus.MATCHED
        )

        data = match.to_dict()

        assert isinstance(data["status"], str)
        assert data["status"] == "matched"


class TestTradeManagerCreation:
    """Test TradeManager initialization"""

    def test_trade_manager_init(self):
        """Test TradeManager initialization"""
        manager = TradeManager()

        assert manager.orders == {}
        assert manager.matches == {}

    def test_trade_manager_empty_on_init(self):
        """Test manager starts empty"""
        manager = TradeManager()

        assert len(manager.orders) == 0
        assert len(manager.matches) == 0


class TestTradeManagerOrderOperations:
    """Test TradeManager order operations"""

    def test_create_order(self):
        """Test creating an order"""
        manager = TradeManager()

        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        order_id = manager.create_order(order)

        assert order_id == "order1"
        assert "order1" in manager.orders
        assert manager.orders["order1"] == order

    def test_create_multiple_orders(self):
        """Test creating multiple orders"""
        manager = TradeManager()

        for i in range(5):
            order = TradeOrder(
                order_id=f"order{i}",
                order_type=SwapOrderType.BUY if i % 2 == 0 else SwapOrderType.SELL,
                amount=10.0 * (i + 1),
                price=100.0,
                user_address=f"XAI{i}"
            )
            manager.create_order(order)

        assert len(manager.orders) == 5

    def test_get_order_exists(self):
        """Test getting existing order"""
        manager = TradeManager()

        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )
        manager.create_order(order)

        retrieved = manager.get_order("order1")

        assert retrieved is not None
        assert retrieved.order_id == "order1"

    def test_get_order_not_exists(self):
        """Test getting non-existent order"""
        manager = TradeManager()

        retrieved = manager.get_order("nonexistent")

        assert retrieved is None

    def test_get_order_returns_none_empty_manager(self):
        """Test getting order from empty manager"""
        manager = TradeManager()

        result = manager.get_order("order1")

        assert result is None


class TestTradeManagerMatchOperations:
    """Test TradeManager match operations"""

    def test_create_match(self):
        """Test creating a match"""
        manager = TradeManager()

        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )

        match_id = manager.create_match(match)

        assert match_id == "match1"
        assert "match1" in manager.matches
        assert manager.matches["match1"] == match

    def test_create_multiple_matches(self):
        """Test creating multiple matches"""
        manager = TradeManager()

        for i in range(5):
            match = TradeMatch(
                match_id=f"match{i}",
                buy_order_id=f"order{i}",
                sell_order_id=f"order{i+100}",
                amount=10.0,
                price=100.0
            )
            manager.create_match(match)

        assert len(manager.matches) == 5

    def test_get_match_exists(self):
        """Test getting existing match"""
        manager = TradeManager()

        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )
        manager.create_match(match)

        retrieved = manager.get_match("match1")

        assert retrieved is not None
        assert retrieved.match_id == "match1"

    def test_get_match_not_exists(self):
        """Test getting non-existent match"""
        manager = TradeManager()

        retrieved = manager.get_match("nonexistent")

        assert retrieved is None

    def test_get_match_returns_none_empty_manager(self):
        """Test getting match from empty manager"""
        manager = TradeManager()

        result = manager.get_match("match1")

        assert result is None


class TestTradeManagerIntegration:
    """Test integrated TradeManager operations"""

    def test_full_order_lifecycle(self):
        """Test complete order lifecycle"""
        manager = TradeManager()

        # Create order
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )
        manager.create_order(order)

        # Verify order exists
        retrieved = manager.get_order("order1")
        assert retrieved is not None

        # Create match for this order
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order2",
            amount=10.0,
            price=100.0
        )
        manager.create_match(match)

        # Verify match exists
        match_retrieved = manager.get_match("match1")
        assert match_retrieved is not None

    def test_multiple_orders_and_matches(self):
        """Test managing multiple orders and matches"""
        manager = TradeManager()

        # Create multiple orders
        for i in range(10):
            order = TradeOrder(
                order_id=f"order{i}",
                order_type=SwapOrderType.BUY if i % 2 == 0 else SwapOrderType.SELL,
                amount=10.0,
                price=100.0,
                user_address=f"XAI{i}"
            )
            manager.create_order(order)

        # Create matches
        for i in range(5):
            match = TradeMatch(
                match_id=f"match{i}",
                buy_order_id=f"order{i*2}",
                sell_order_id=f"order{i*2+1}",
                amount=10.0,
                price=100.0
            )
            manager.create_match(match)

        assert len(manager.orders) == 10
        assert len(manager.matches) == 5


class TestTradeEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_order_with_zero_amount(self):
        """Test order with zero amount"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=0.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.amount == 0.0

    def test_order_with_zero_price(self):
        """Test order with zero price"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=0.0,
            user_address="XAI123"
        )

        assert order.price == 0.0

    def test_order_with_very_large_amount(self):
        """Test order with very large amount"""
        order = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=1_000_000_000.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.amount == 1_000_000_000.0

    def test_match_with_same_buy_sell_order(self):
        """Test match where buy and sell are same order ID"""
        match = TradeMatch(
            match_id="match1",
            buy_order_id="order1",
            sell_order_id="order1",  # Same as buy
            amount=10.0,
            price=100.0
        )

        assert match.buy_order_id == match.sell_order_id

    def test_order_id_empty_string(self):
        """Test order with empty string ID"""
        order = TradeOrder(
            order_id="",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )

        assert order.order_id == ""

    def test_duplicate_order_ids(self):
        """Test creating orders with duplicate IDs"""
        manager = TradeManager()

        order1 = TradeOrder(
            order_id="order1",
            order_type=SwapOrderType.BUY,
            amount=10.0,
            price=100.0,
            user_address="XAI123"
        )
        order2 = TradeOrder(
            order_id="order1",  # Same ID
            order_type=SwapOrderType.SELL,
            amount=5.0,
            price=50.0,
            user_address="XAI456"
        )

        manager.create_order(order1)
        manager.create_order(order2)

        # Second order should overwrite first
        retrieved = manager.get_order("order1")
        assert retrieved.order_type == SwapOrderType.SELL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
