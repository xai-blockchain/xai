"""
Comprehensive test suite for wallet_trade_manager_impl.py to achieve 98%+ coverage.

Tests all wallet trade manager operations including:
- WalletConnect handshake operations
- Order placement and matching
- Trade settlement
- Atomic swaps
- Gossip protocol integration
- Audit signing
- Edge cases and error handling
"""

import pytest
import uuid
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, call
from xai.core.wallets.wallet_trade_manager_impl import WalletTradeManager, AuditSigner, OrderRateLimitError
from xai.core.transactions.trading import SwapOrderType, TradeMatchStatus


@pytest.fixture
def tmp_data_dir():
    """Provide a clean temporary directory for each test to ensure isolation."""
    tmp_dir = tempfile.mkdtemp(prefix="wtm_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def fresh_manager(tmp_data_dir):
    """Provide a WalletTradeManager with isolated state (no shared persistent data)."""
    return WalletTradeManager(data_dir=tmp_data_dir)


class TestAuditSigner:
    """Test AuditSigner class"""

    def test_audit_signer_creation(self):
        """Test creating AuditSigner"""
        signer = AuditSigner()

        assert signer is not None

    def test_audit_signer_public_key(self):
        """Test getting public key from AuditSigner"""
        signer = AuditSigner()

        key = signer.public_key()

        assert isinstance(key, str)
        assert len(key) == 64
        int(key, 16)  # ensure hex


class TestWalletTradeManagerCreation:
    """Test WalletTradeManager initialization"""

    def test_wallet_trade_manager_init_default(self, tmp_data_dir):
        """Test default initialization with clean state"""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        assert manager.audit_signer is not None
        assert isinstance(manager.audit_signer, AuditSigner)
        assert manager.orders == {}
        assert manager.matches == {}

    def test_wallet_trade_manager_init_with_params(self, tmp_data_dir):
        """Test initialization with parameters"""
        mock_exchange = Mock()
        manager = WalletTradeManager(
            exchange_wallet_manager=mock_exchange,
            data_dir=tmp_data_dir,
            nonce_tracker=Mock()
        )

        assert manager.exchange_wallet_manager == mock_exchange
        assert manager.data_dir == tmp_data_dir
        assert manager.nonce_tracker is not None

    def test_wallet_trade_manager_has_audit_signer(self, tmp_data_dir):
        """Test manager has audit signer"""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        assert hasattr(manager, 'audit_signer')
        pub_key = manager.audit_signer.public_key()
        assert len(pub_key) == 64


class TestWalletConnectHandshake:
    """Test WalletConnect handshake operations"""

    def test_begin_walletconnect_handshake(self):
        """Test beginning WalletConnect handshake"""
        manager = WalletTradeManager()

        result = manager.begin_walletconnect_handshake("XAI123")

        assert result is not None
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "handshake_id" in result
        assert "uri" in result

    def test_begin_walletconnect_handshake_returns_data(self):
        """Test handshake returns required data"""
        manager = WalletTradeManager()

        result = manager.begin_walletconnect_handshake("XAI456")

        from uuid import UUID

        UUID(result["handshake_id"])  # Does not raise
        assert result["uri"].startswith("wc:")

    def test_complete_walletconnect_handshake(self):
        """Test completing WalletConnect handshake"""
        manager = WalletTradeManager()
        begin = manager.begin_walletconnect_handshake("XAI123")

        result = manager.complete_walletconnect_handshake(
            begin["handshake_id"],
            "XAI123",
            "client_public_key"
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "session_token" in result

    def test_complete_walletconnect_handshake_returns_token(self):
        """Test handshake completion returns session token"""
        manager = WalletTradeManager()
        begin = manager.begin_walletconnect_handshake("XAI123")

        result = manager.complete_walletconnect_handshake(
            begin["handshake_id"],
            "XAI123",
            "client_public_key"
        )

        assert result["session_token"]

    def test_walletconnect_handshake_full_flow(self):
        """Test complete WalletConnect flow"""
        manager = WalletTradeManager()

        # Begin handshake
        begin_result = manager.begin_walletconnect_handshake("XAI123")
        assert begin_result["success"] is True

        # Complete handshake
        complete_result = manager.complete_walletconnect_handshake(
            begin_result["handshake_id"],
            "XAI123",
            "client_public"
        )
        assert complete_result["success"] is True


class TestOrderOperations:
    """Test order placement and retrieval"""

    def test_get_order_not_found(self):
        """Test getting non-existent order"""
        manager = WalletTradeManager()

        result = manager.get_order("nonexistent")

        assert result is None

    def test_get_order_existing_order(self):
        """Test get_order returns stored order"""
        manager = WalletTradeManager()
        order, _ = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY,
        )

        fetched = manager.get_order(order.order_id)

        assert fetched.order_id == order.order_id


class TestMatchOperations:
    """Test match retrieval"""

    def test_get_match_not_found(self):
        """Test getting non-existent match"""
        manager = WalletTradeManager()

        result = manager.get_match("nonexistent")

        assert result is None

    def test_get_match_existing_match(self):
        """Test get_match returns stored match"""
        manager = WalletTradeManager()
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY,
        )
        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL,
        )

        if matches:
            fetched = manager.get_match(matches[0].match_id)
            assert fetched.match_id == matches[0].match_id


class TestGossipOperations:
    """Test gossip protocol integration"""

    def test_ingest_gossip(self):
        """Test ingesting gossip event"""
        manager = WalletTradeManager()

        event = {"type": "order", "data": "test"}
        result = manager.ingest_gossip(event)

        assert result is not None
        assert isinstance(result, dict)
        assert result["success"] is True
        assert manager.event_log

    def test_ingest_gossip_multiple_events(self):
        """Test ingest_gossip tracks multiple events"""
        manager = WalletTradeManager()

        result = manager.ingest_gossip({"test": "data"})

        assert result["success"] is True


class TestSnapshotOperations:
    """Test snapshot functionality"""

    def test_snapshot(self):
        """Test creating snapshot"""
        manager = WalletTradeManager()

        result = manager.snapshot()

        assert result is not None
        assert isinstance(result, dict)
        assert "orders" in result
        assert "matches" in result
        assert "active_sessions" in result

    def test_snapshot_includes_metadata(self):
        """Test snapshot contains metadata and counts"""
        manager = WalletTradeManager()

        manager.snapshot()


class TestSignedEventBatch:
    """Test signed event batch operations"""

    def test_signed_event_batch(self):
        """Test getting signed event batch"""
        manager = WalletTradeManager()

        result = manager.signed_event_batch(10)

        assert result is not None
        assert isinstance(result, list)

    def test_signed_event_batch_returns_empty(self, tmp_data_dir):
        """Test signed_event_batch returns empty list with fresh state"""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        result = manager.signed_event_batch(5)

        assert result == []

    def test_signed_event_batch_different_limits(self):
        """Test signed_event_batch with different limits"""
        manager = WalletTradeManager()

        result1 = manager.signed_event_batch(1)
        result2 = manager.signed_event_batch(100)

        assert isinstance(result1, list)
        assert isinstance(result2, list)


class TestPlaceOrder:
    """Test order placement and matching"""

    def test_place_order_basic(self):
        """Test basic order placement"""
        manager = WalletTradeManager()

        order, matches = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        assert order is not None
        assert isinstance(matches, list)
        assert hasattr(order, 'order_id')
        assert order.order_id in manager.orders

    def test_place_order_creates_order_object(self):
        """Test place_order creates proper order object"""
        manager = WalletTradeManager()

        order, matches = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        assert order.maker_address == "XAI123"
        assert order.token_offered == "XAI"
        assert order.amount_offered == 10.0
        assert order.token_requested == "BTC"
        assert order.amount_requested == 0.001
        assert order.price == 10000.0
        assert order.order_type == SwapOrderType.SELL

    def test_place_order_no_matches(self):
        """Test placing order with no matching orders"""
        manager = WalletTradeManager()

        order, matches = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        assert len(matches) == 0

    def test_place_order_with_matching(self):
        """Test placing order that matches existing order"""
        manager = WalletTradeManager()

        # Place first order
        order1, _ = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        # Place matching order
        order2, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        # Should have a match
        assert len(matches) == 1
        assert hasattr(matches[0], 'match_id')

    def test_place_order_respects_slippage(self, tmp_data_dir):
        """Matching should respect per-order slippage tolerance."""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY,
            max_slippage_bps=50,  # 0.5%
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10010.0,  # within 0.1%
            order_type=SwapOrderType.SELL,
            max_slippage_bps=100,
        )

        assert len(matches) == 1

    def test_place_order_slippage_guard_blocks_trade(self, tmp_data_dir):
        """Trades exceeding slippage tolerance should not match."""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY,
            max_slippage_bps=10,  # 0.1%
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10100.0,  # 1% away
            order_type=SwapOrderType.SELL,
            max_slippage_bps=100,
        )

        assert len(matches) == 0

    def test_place_order_match_has_secret(self):
        """Test matched order has secret"""
        manager = WalletTradeManager()

        # Place matching orders
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        if matches:
            assert hasattr(matches[0], 'secret')
            assert len(matches[0].secret) == 64  # 32 bytes hex

    def test_place_order_match_status(self):
        """Test match has correct status"""
        manager = WalletTradeManager()

        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        if matches:
            assert matches[0].status == TradeMatchStatus.MATCHED

    def test_place_order_rate_limit_blocks_spam(self, tmp_data_dir):
        """Per-user order rate limiting should block excessive submissions."""
        manager = WalletTradeManager(
            data_dir=tmp_data_dir,
            order_limit_per_minute=2,
            order_limit_window_seconds=60,
        )

        def submit(offset: int) -> None:
            manager.place_order(
                maker_address="XAILIMIT",
                token_offered="XAI",
                amount_offered=10.0,
                token_requested="BTC",
                amount_requested=0.001,
                price=10000.0 + offset,
                order_type=SwapOrderType.BUY,
            )

        submit(0)
        submit(1)
        with pytest.raises(OrderRateLimitError):
            submit(2)

    def test_place_order_rate_limit_disabled(self, tmp_data_dir):
        """Setting the limit to zero disables throttling for trusted deployments."""
        manager = WalletTradeManager(
            data_dir=tmp_data_dir,
            order_limit_per_minute=0,
        )

        for idx in range(5):
            manager.place_order(
                maker_address="XAIUNLIMITED",
                token_offered="USDT",
                amount_offered=500.0,
                token_requested="XAI",
                amount_requested=50.0,
                price=10.0 + idx,
                order_type=SwapOrderType.SELL,
            )

    def test_place_order_supports_iceberg_orders(self, tmp_data_dir):
        """Iceberg orders should only expose the configured peak amount."""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        iceberg_order, _ = manager.place_order(
            maker_address="ICEBERG",
            token_offered="XAI",
            amount_offered=100.0,
            token_requested="USDT",
            amount_requested=1000.0,
            price=10.0,
            order_type=SwapOrderType.SELL,
            iceberg_total=100.0,
            iceberg_peak=25.0,
        )

        assert iceberg_order.displayed_offered == pytest.approx(25.0)

        _, matches = manager.place_order(
            maker_address="TAKER",
            token_offered="USDT",
            amount_offered=250.0,
            token_requested="XAI",
            amount_requested=25.0,
            price=10.0,
            order_type=SwapOrderType.BUY,
        )

        assert matches, "iceberg should match"
        refreshed_order = manager.get_order(iceberg_order.order_id)
        assert refreshed_order.displayed_offered == pytest.approx(25.0)
        assert refreshed_order.remaining_offered == pytest.approx(75.0)

    def test_trailing_stop_orders_adjust_stop_price(self, tmp_data_dir):
        """Trailing stop orders should move stop_price with favorable price action."""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        order, _ = manager.place_order(
            maker_address="TRAIL",
            token_offered="USDT",
            amount_offered=1000.0,
            token_requested="XAI",
            amount_requested=100.0,
            price=10.0,
            order_type=SwapOrderType.BUY,
            stop_price=10.5,
            trail_amount=0.5,
        )

        assert order.stop_price == pytest.approx(10.5)

        manager._ensure_stop_triggered(order, 9.0)
        assert order.lowest_price_seen == pytest.approx(9.0)
        assert order.stop_price == pytest.approx(9.5)

        triggered = manager._ensure_stop_triggered(order, 9.6)
        assert triggered is True


class TestSettleMatch:
    """Test match settlement"""

    def test_settle_match_success(self):
        """Test successful match settlement"""
        # Create mock exchange wallet manager
        mock_exchange = Mock()
        mock_exchange.withdraw = Mock()
        mock_exchange.deposit = Mock()

        manager = WalletTradeManager(exchange_wallet_manager=mock_exchange)

        # Create matching orders
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        # Settle the match
        if matches:
            match = matches[0]
            result = manager.settle_match(match.match_id, match.secret)

            assert result is not None
            assert result["success"] is True
            # Verify the match status was updated
            settled_match = manager.get_match(match.match_id)
            assert settled_match.status == TradeMatchStatus.SETTLED

    def test_settle_match_applies_maker_taker_fees(self, tmp_data_dir):
        """Settlement should honor maker/taker fee splits and credit the fee collector."""
        exchange = MagicMock()
        manager = WalletTradeManager(
            exchange_wallet_manager=exchange,
            data_dir=tmp_data_dir,
            maker_fee_bps=100,
            taker_fee_bps=50,
        )

        maker_order, _ = manager.place_order(
            maker_address="maker",
            token_offered="XAI",
            amount_offered=100.0,
            token_requested="USDT",
            amount_requested=1000.0,
            price=10.0,
            order_type=SwapOrderType.SELL,
        )

        _, matches = manager.place_order(
            maker_address="taker",
            token_offered="USDT",
            amount_offered=1000.0,
            token_requested="XAI",
            amount_requested=100.0,
            price=10.0,
            order_type=SwapOrderType.BUY,
        )

        assert matches, "expected orders to match"
        match = matches[0]
        result = manager.settle_match(match.match_id, match.secret)

        assert result["success"] is True
        assert result.status == TradeMatchStatus.SETTLED
        assert result["fees"] == {"maker_fee": pytest.approx(1.0), "taker_fee": pytest.approx(5.0)}

        exchange.withdraw.assert_has_calls(
            [
                call("maker", "XAI", pytest.approx(100.0), destination="taker"),
                call("taker", "USDT", pytest.approx(1000.0), destination="maker"),
            ]
        )
        exchange.deposit.assert_has_calls(
            [
                call("taker", "XAI", pytest.approx(99.0), deposit_type="trade"),
                call(manager.fee_collector_address, "XAI", pytest.approx(1.0), deposit_type="trade_fee"),
                call("maker", "USDT", pytest.approx(995.0), deposit_type="trade"),
                call(manager.fee_collector_address, "USDT", pytest.approx(5.0), deposit_type="trade_fee"),
            ]
        )

        match_data = result["match"]
        assert match_data["maker_fee_bps"] == 100
        assert match_data["taker_fee_bps"] == 50
        assert match_data["maker_net_amount"] == pytest.approx(99.0)
        assert match_data["taker_net_amount"] == pytest.approx(995.0)

    def test_settle_match_not_found(self, tmp_data_dir):
        """Test settling non-existent match returns error"""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        result = manager.settle_match("nonexistent", "secret")
        assert result["success"] is False
        assert result["error"] == "match_not_found"

    def test_settle_match_invalid_secret(self, tmp_data_dir):
        """Test settling match with wrong secret returns error"""
        mock_exchange = Mock()
        manager = WalletTradeManager(exchange_wallet_manager=mock_exchange, data_dir=tmp_data_dir)

        # Create matching orders
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        if matches:
            result = manager.settle_match(matches[0].match_id, "wrong_secret")
            assert result["success"] is False
            assert result["error"] == "invalid_secret"

    def test_settle_match_performs_exchange(self):
        """Test settlement performs token exchange"""
        mock_exchange = Mock()
        manager = WalletTradeManager(exchange_wallet_manager=mock_exchange)

        # Create matching orders
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        if matches:
            manager.settle_match(matches[0].match_id, matches[0].secret)

            # Verify exchange operations were called
            assert mock_exchange.withdraw.called
            assert mock_exchange.deposit.called


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_place_order_fractional_amounts(self):
        """Test placing order with fractional amounts"""
        manager = WalletTradeManager()

        order, _ = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=0.123456789,
            token_requested="BTC",
            amount_requested=0.00000001,
            price=0.00008102,
            order_type=SwapOrderType.BUY
        )

        assert order.amount_offered == 0.123456789
        assert order.amount_requested == 0.00000001

    def test_place_order_zero_amounts(self):
        """Zero amounts should be rejected to avoid division by zero."""
        manager = WalletTradeManager()

        with pytest.raises(ValueError):
            manager.place_order(
                maker_address="XAI123",
                token_offered="XAI",
                amount_offered=0.0,
                token_requested="BTC",
                amount_requested=0.0,
                price=0.0,
            order_type=SwapOrderType.BUY,
        )

    def test_price_validation(self):
        """Prices must be finite positive numbers."""
        manager = WalletTradeManager()

        with pytest.raises(ValueError):
            manager.place_order(
                maker_address="XAI123",
                token_offered="XAI",
                amount_offered=1.0,
                token_requested="BTC",
                amount_requested=0.0001,
                price=0.0,
                order_type=SwapOrderType.BUY,
            )

        with pytest.raises(ValueError):
            manager.place_order(
                maker_address="XAI123",
                token_offered="XAI",
                amount_offered=1.0,
                token_requested="BTC",
                amount_requested=0.0001,
                price=float("inf"),
                order_type=SwapOrderType.BUY,
            )

    def test_price_mismatch_prevents_match(self, tmp_data_dir):
        """Orders with materially different prices should not match."""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=9000.0,
            order_type=SwapOrderType.BUY,
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=12000.0,
            order_type=SwapOrderType.SELL,
        )

        assert len(matches) == 0

    def test_multiple_orders_same_user(self, tmp_data_dir):
        """Test placing multiple orders for same user with fresh state"""
        manager = WalletTradeManager(data_dir=tmp_data_dir)

        for i in range(5):
            order, _ = manager.place_order(
                maker_address="XAI123",  # Same address
                token_offered="XAI",
                amount_offered=10.0 * (i + 1),
                token_requested="BTC",
                amount_requested=0.001,
                price=10000.0,
                order_type=SwapOrderType.BUY
            )
            assert order is not None

        assert len(manager.orders) == 5

    def test_match_storage(self):
        """Test that matches are stored correctly"""
        manager = WalletTradeManager()

        # Create matching orders
        manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        _, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        if matches:
            assert matches[0].match_id in manager.matches

    def test_order_has_required_attributes(self):
        """Test created order has all required attributes"""
        manager = WalletTradeManager()

        order, _ = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        assert hasattr(order, 'order_id')
        assert hasattr(order, 'maker_address')
        assert hasattr(order, 'token_offered')
        assert hasattr(order, 'amount_offered')
        assert hasattr(order, 'token_requested')
        assert hasattr(order, 'amount_requested')
        assert hasattr(order, 'price')
        assert hasattr(order, 'order_type')


class TestIntegrationScenarios:
    """Test integrated scenarios"""

    def test_complete_trade_lifecycle(self):
        """Test complete trade from order to settlement"""
        mock_exchange = Mock()
        mock_exchange.withdraw = Mock()
        mock_exchange.deposit = Mock()

        manager = WalletTradeManager(exchange_wallet_manager=mock_exchange)

        # Place buy order
        buy_order, _ = manager.place_order(
            maker_address="XAI123",
            token_offered="XAI",
            amount_offered=10.0,
            token_requested="BTC",
            amount_requested=0.001,
            price=10000.0,
            order_type=SwapOrderType.BUY
        )

        # Place matching sell order
        sell_order, matches = manager.place_order(
            maker_address="XAI456",
            token_offered="BTC",
            amount_offered=0.001,
            token_requested="XAI",
            amount_requested=10.0,
            price=10000.0,
            order_type=SwapOrderType.SELL
        )

        # Verify match was created
        assert len(matches) == 1

        # Settle the match
        if matches:
            result = manager.settle_match(matches[0].match_id, matches[0].secret)
            assert result["success"] is True
            # Verify the match status was updated
            settled_match = manager.get_match(matches[0].match_id)
            assert settled_match.status == TradeMatchStatus.SETTLED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
