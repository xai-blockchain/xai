from xai.blockchain.order_book_manipulation_detection import (
    OrderBook,
    OrderBookManipulationDetector,
)
from xai.security.circuit_breaker import CircuitBreaker, CircuitBreakerState


def test_spoofing_detection_trips_breaker():
    order_book = OrderBook()
    circuit_breaker = CircuitBreaker("spoof", failure_threshold=1, recovery_timeout_seconds=10)
    detector = OrderBookManipulationDetector(
        order_book,
        circuit_breaker,
        spoofing_threshold_percentage=10.0,
        spoofing_cancel_time_seconds=5,
    )

    order_book.place_order("buy", price=101.0, amount=10.0, timestamp=900)
    order_id = order_book.place_order("buy", price=100.0, amount=100.0, timestamp=1000)
    order_book.cancel_order(order_id)
    order_book.buy_orders[order_id]["timestamp"] = 1000
    assert detector.detect_spoofing(current_time=1002) is True
    assert circuit_breaker.state == CircuitBreakerState.OPEN


def test_layering_detection():
    order_book = OrderBook()
    circuit_breaker = CircuitBreaker("layer", failure_threshold=1, recovery_timeout_seconds=10)
    detector = OrderBookManipulationDetector(
        order_book,
        circuit_breaker,
        layering_min_orders=3,
        layering_price_increment_percentage=0.2,
    )

    order_book.place_order("sell", price=100.0, amount=1.0)
    order_book.place_order("sell", price=100.1, amount=1.0)
    order_book.place_order("sell", price=100.2, amount=1.0)
    assert detector.detect_layering() is True
    assert circuit_breaker.state == CircuitBreakerState.OPEN
