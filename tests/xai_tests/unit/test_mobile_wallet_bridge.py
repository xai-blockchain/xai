from types import SimpleNamespace

from xai.core.mobile_wallet_bridge import MobileWalletBridge
from xai.core.validation import validate_address, validate_amount


class DummyValidator:
    """Validator using centralized validation functions"""
    def validate_address(self, address: str, _: str) -> str:
        return validate_address(address, allow_special=True)

    def validate_amount(self, amount: float, _: str) -> float:
        return validate_amount(amount, allow_zero=False)


class DummyNonceTracker:
    def __init__(self):
        self._nonce = 0

    def get_next_nonce(self, _: str) -> int:
        self._nonce += 1
        return self._nonce


class DummyBlockchain:
    def __init__(self):
        self.pending_transactions = []
        self.nonce_tracker = DummyNonceTracker()


class DummyFeeOptimizer:
    def __init__(self, congestion: str = "moderate"):
        self._congestion = congestion

    def predict_optimal_fee(self, pending_tx_count: int, priority: str = "normal", **_kwargs):
        return {
            "success": True,
            "recommended_fee": 0.0125,
            "priority": priority,
            "pending_transactions": pending_tx_count,
            "congestion_level": self._congestion,
            "fee_percentiles": {"p50": 0.01},
            "pressure": {"backlog_ratio": 0.25, "block_capacity": 500},
            "mempool_bytes": 2048,
            "estimated_confirmation_blocks": 2,
            "confidence": 0.9,
        }


def _new_bridge(congestion: str = "moderate"):
    blockchain = DummyBlockchain()
    validator = DummyValidator()
    optimizer = DummyFeeOptimizer(congestion=congestion)
    return MobileWalletBridge(blockchain, validator, fee_optimizer=optimizer)


def test_fee_quote_returns_telemetry():
    bridge = _new_bridge(congestion="high")
    quote = bridge._get_fee_quote("fast")

    assert quote["recommended_fee"] == 0.0125
    assert quote["telemetry"]["congestion_level"] == "high"
    assert quote["telemetry"]["fee_percentiles"]["p50"] == 0.01
    assert quote["conditions"]["priority"] == "fast"


def test_create_draft_embeds_fee_telemetry():
    bridge = _new_bridge()
    payload = {
        "sender": "XAI" + "1" * 40,
        "recipient": "XAI" + "2" * 40,
        "amount": "5.5",
        "priority": "normal",
    }

    draft = bridge.create_draft(payload)

    telemetry = draft["fee_quote"]["telemetry"]
    assert telemetry["congestion_level"] == "moderate"
    assert draft["unsigned_transaction"]["fee_telemetry"] == telemetry
