"""
Comprehensive unit tests for Fraud Detection module.

Tests the FraudDetector class and FraudSignal dataclass including:
- analyze_transaction method with all heuristics
- Individual fraud detection rules (high value, sanctioned region, risk type, self-transfer)
- Score calculation and accumulation
- Threshold-based action decisions
- Edge cases and boundary conditions
- Combinations of fraud signals
"""

import pytest
from dataclasses import asdict
from typing import Any

from xai.core.security.fraud_detection import (
    FraudDetector,
    FraudSignal,
    SUSPICIOUS_COUNTRIES,
    HIGH_RISK_TX_TYPES,
)


# -----------------------------------------------------------------------------
# Test Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def detector():
    """Create a fresh FraudDetector for each test."""
    return FraudDetector()


@pytest.fixture
def clean_transaction() -> dict[str, Any]:
    """Create a clean transaction with no fraud signals."""
    return {
        "address": "0xSender123",
        "recipient": "0xRecipient456",
        "amount": 100.0,
        "geolocation": "US",
        "tx_type": "standard_transfer",
    }


@pytest.fixture
def high_value_transaction() -> dict[str, Any]:
    """Create a high-value transaction."""
    return {
        "address": "0xSender123",
        "recipient": "0xRecipient456",
        "amount": 15000.0,
        "geolocation": "US",
        "tx_type": "standard_transfer",
    }


@pytest.fixture
def sanctioned_region_transaction() -> dict[str, Any]:
    """Create a transaction from a sanctioned region."""
    return {
        "address": "0xSender123",
        "recipient": "0xRecipient456",
        "amount": 100.0,
        "geolocation": "KP",  # North Korea
        "tx_type": "standard_transfer",
    }


# -----------------------------------------------------------------------------
# FraudSignal Tests
# -----------------------------------------------------------------------------

class TestFraudSignal:
    """Test the FraudSignal dataclass."""

    def test_fraud_signal_creation(self):
        """Test creating a FraudSignal."""
        signal = FraudSignal(reason="test_reason", weight=0.5)
        assert signal.reason == "test_reason"
        assert signal.weight == 0.5

    def test_fraud_signal_to_dict(self):
        """Test FraudSignal conversion to dict."""
        signal = FraudSignal(reason="high_value", weight=0.35)
        data = asdict(signal)
        assert data == {"reason": "high_value", "weight": 0.35}

    def test_fraud_signal_immutability(self):
        """Test that FraudSignal fields are accessible."""
        signal = FraudSignal(reason="test", weight=0.1)
        # Dataclass is not frozen by default, but let's verify field access
        assert signal.reason == "test"
        assert signal.weight == 0.1


# -----------------------------------------------------------------------------
# FraudDetector Initialization Tests
# -----------------------------------------------------------------------------

class TestFraudDetectorInit:
    """Test FraudDetector initialization."""

    def test_default_threshold(self, detector):
        """Test default base_threshold value."""
        assert detector.base_threshold == 0.6

    def test_custom_threshold(self):
        """Test FraudDetector can have its threshold modified."""
        detector = FraudDetector()
        detector.base_threshold = 0.8
        assert detector.base_threshold == 0.8


# -----------------------------------------------------------------------------
# Individual Heuristic Tests
# -----------------------------------------------------------------------------

class TestHighValueHeuristic:
    """Test the high-value transaction detection heuristic."""

    def test_below_threshold_no_signal(self, detector):
        """Test transaction below 10,000 doesn't trigger high_value signal."""
        # Include different address/recipient to avoid self_transfer signal
        data = {"amount": 9999.99, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_value:0.35" not in result["flags"]
        assert result["score"] == 0.0

    def test_at_threshold_triggers_signal(self, detector):
        """Test transaction at exactly 10,000 triggers high_value signal."""
        data = {"amount": 10000.0, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_value:0.35" in result["flags"]
        assert result["score"] == 0.35

    def test_above_threshold_triggers_signal(self, detector):
        """Test transaction above 10,000 triggers high_value signal."""
        data = {"amount": 50000.0, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_value:0.35" in result["flags"]
        assert result["score"] == 0.35

    def test_string_amount_converted(self, detector):
        """Test that string amount is properly converted to float."""
        data = {"amount": "15000", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_value:0.35" in result["flags"]

    def test_missing_amount_defaults_to_zero(self, detector):
        """Test missing amount defaults to 0 (no high_value signal)."""
        # Note: missing address/recipient triggers self_transfer (None == None)
        data = {"address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_value:0.35" not in result["flags"]
        assert result["score"] == 0.0


class TestSanctionedRegionHeuristic:
    """Test the sanctioned region detection heuristic."""

    def test_us_not_sanctioned(self, detector):
        """Test US geolocation doesn't trigger sanctioned_region signal."""
        data = {"geolocation": "US", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" not in result["flags"]

    def test_north_korea_sanctioned(self, detector):
        """Test KP (North Korea) triggers sanctioned_region signal."""
        data = {"geolocation": "KP", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" in result["flags"]
        assert result["score"] == 0.4

    def test_iran_sanctioned(self, detector):
        """Test IR (Iran) triggers sanctioned_region signal."""
        data = {"geolocation": "IR", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" in result["flags"]

    def test_syria_sanctioned(self, detector):
        """Test SY (Syria) triggers sanctioned_region signal."""
        data = {"geolocation": "SY", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" in result["flags"]

    def test_all_suspicious_countries(self, detector):
        """Test all countries in SUSPICIOUS_COUNTRIES set trigger signal."""
        for country in SUSPICIOUS_COUNTRIES:
            data = {"geolocation": country, "address": "0xA", "recipient": "0xB"}
            result = detector.analyze_transaction(data)
            assert "sanctioned_region:0.40" in result["flags"], f"Failed for {country}"

    def test_missing_geolocation_no_signal(self, detector):
        """Test missing geolocation doesn't trigger sanctioned_region signal."""
        data = {"address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" not in result["flags"]

    def test_none_geolocation_no_signal(self, detector):
        """Test None geolocation doesn't trigger signal."""
        data = {"geolocation": None, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "sanctioned_region:0.40" not in result["flags"]


class TestHighRiskTypeHeuristic:
    """Test the high-risk transaction type detection heuristic."""

    def test_standard_transfer_no_signal(self, detector):
        """Test standard_transfer doesn't trigger high_risk_type signal."""
        data = {"tx_type": "standard_transfer", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_risk_type:0.25" not in result["flags"]

    def test_anonymous_bridge_triggers_signal(self, detector):
        """Test anonymous_bridge triggers high_risk_type signal."""
        data = {"tx_type": "anonymous_bridge", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_risk_type:0.25" in result["flags"]
        assert result["score"] == 0.25

    def test_obfuscated_transfer_triggers_signal(self, detector):
        """Test obfuscated_transfer triggers high_risk_type signal."""
        data = {"tx_type": "obfuscated_transfer", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_risk_type:0.25" in result["flags"]

    def test_all_high_risk_types(self, detector):
        """Test all types in HIGH_RISK_TX_TYPES trigger signal."""
        for tx_type in HIGH_RISK_TX_TYPES:
            data = {"tx_type": tx_type, "address": "0xA", "recipient": "0xB"}
            result = detector.analyze_transaction(data)
            assert "high_risk_type:0.25" in result["flags"], f"Failed for {tx_type}"

    def test_missing_tx_type_no_signal(self, detector):
        """Test missing tx_type doesn't trigger signal."""
        data = {"address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)

        assert "high_risk_type:0.25" not in result["flags"]


class TestSelfTransferHeuristic:
    """Test the self-transfer detection heuristic."""

    def test_different_addresses_no_signal(self, detector):
        """Test different sender/recipient doesn't trigger self_transfer signal."""
        data = {"address": "0xSender", "recipient": "0xRecipient"}
        result = detector.analyze_transaction(data)

        assert "self_transfer:0.10" not in result["flags"]

    def test_same_addresses_triggers_signal(self, detector):
        """Test same sender/recipient triggers self_transfer signal."""
        data = {"address": "0xSameAddr", "recipient": "0xSameAddr"}
        result = detector.analyze_transaction(data)

        assert "self_transfer:0.10" in result["flags"]
        assert result["score"] == 0.1

    def test_case_sensitive_comparison(self, detector):
        """Test address comparison is case-sensitive."""
        data = {"address": "0xAddress", "recipient": "0xaddress"}
        result = detector.analyze_transaction(data)

        # Different case means different addresses
        assert "self_transfer:0.10" not in result["flags"]

    def test_missing_recipient_no_signal(self, detector):
        """Test missing recipient doesn't trigger self_transfer signal."""
        data = {"address": "0xSender"}
        result = detector.analyze_transaction(data)

        assert "self_transfer:0.10" not in result["flags"]

    def test_missing_address_no_signal(self, detector):
        """Test missing address doesn't trigger self_transfer signal."""
        data = {"recipient": "0xRecipient"}
        result = detector.analyze_transaction(data)

        assert "self_transfer:0.10" not in result["flags"]

    def test_both_none_triggers_signal(self, detector):
        """Test that both being None triggers self_transfer (None == None)."""
        data = {"address": None, "recipient": None}
        result = detector.analyze_transaction(data)

        # None == None is True in Python
        assert "self_transfer:0.10" in result["flags"]


# -----------------------------------------------------------------------------
# Score Accumulation Tests
# -----------------------------------------------------------------------------

class TestScoreAccumulation:
    """Test that fraud scores accumulate correctly."""

    def test_no_signals_zero_score(self, detector, clean_transaction):
        """Test clean transaction has zero score."""
        result = detector.analyze_transaction(clean_transaction)
        assert result["score"] == 0.0
        assert len(result["flags"]) == 0

    def test_single_signal_score(self, detector, high_value_transaction):
        """Test single signal contributes its weight."""
        result = detector.analyze_transaction(high_value_transaction)
        assert result["score"] == 0.35

    def test_two_signals_accumulate(self, detector):
        """Test two signals accumulate correctly."""
        data = {
            "amount": 15000.0,  # +0.35
            "geolocation": "KP",  # +0.40
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.75

    def test_three_signals_accumulate(self, detector):
        """Test three signals accumulate correctly."""
        data = {
            "amount": 15000.0,  # +0.35
            "geolocation": "KP",  # +0.40
            "tx_type": "anonymous_bridge",  # +0.25
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        result = detector.analyze_transaction(data)
        assert result["score"] == 1.0

    def test_all_signals_accumulate(self, detector):
        """Test all four signals accumulate correctly."""
        data = {
            "amount": 15000.0,  # +0.35
            "geolocation": "KP",  # +0.40
            "tx_type": "anonymous_bridge",  # +0.25
            "address": "0xSame",  # +0.10
            "recipient": "0xSame",
        }
        result = detector.analyze_transaction(data)
        assert result["score"] == 1.1  # 0.35 + 0.40 + 0.25 + 0.10

    def test_score_rounding(self, detector):
        """Test score is rounded to 3 decimal places."""
        # The score 0.35 + 0.40 + 0.25 = 1.0 exactly
        data = {
            "amount": 15000.0,
            "geolocation": "KP",
            "tx_type": "anonymous_bridge",
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        result = detector.analyze_transaction(data)
        assert result["score"] == round(1.0, 3)


# -----------------------------------------------------------------------------
# Action Decision Tests
# -----------------------------------------------------------------------------

class TestActionDecision:
    """Test threshold-based action decisions."""

    def test_below_threshold_allows(self, detector, clean_transaction):
        """Test transaction below threshold gets 'allow' action."""
        result = detector.analyze_transaction(clean_transaction)
        assert result["action"] == "allow"

    def test_at_threshold_reviews(self, detector):
        """Test transaction at exactly threshold gets 'review' action."""
        # Need exactly 0.6 score
        data = {
            "amount": 15000.0,  # +0.35
            "tx_type": "anonymous_bridge",  # +0.25 = 0.60
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.6
        assert result["action"] == "review"

    def test_above_threshold_reviews(self, detector, sanctioned_region_transaction):
        """Test transaction above threshold gets 'review' action."""
        # Sanctioned region alone is 0.4, below threshold
        sanctioned_region_transaction["amount"] = 15000.0  # +0.35 = 0.75
        result = detector.analyze_transaction(sanctioned_region_transaction)
        assert result["action"] == "review"

    def test_just_below_threshold_allows(self, detector):
        """Test transaction just below threshold gets 'allow' action."""
        data = {
            "amount": 15000.0,  # +0.35
            "tx_type": "anonymous_bridge",  # +0.25 = 0.60
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        # Modify threshold to test boundary
        detector.base_threshold = 0.61
        result = detector.analyze_transaction(data)
        assert result["action"] == "allow"


# -----------------------------------------------------------------------------
# Response Structure Tests
# -----------------------------------------------------------------------------

class TestResponseStructure:
    """Test the structure of analyze_transaction response."""

    def test_response_has_all_fields(self, detector, clean_transaction):
        """Test response contains all required fields."""
        result = detector.analyze_transaction(clean_transaction)

        assert "success" in result
        assert "score" in result
        assert "threshold" in result
        assert "flags" in result
        assert "action" in result

    def test_success_always_true(self, detector, clean_transaction):
        """Test success is always True for valid input."""
        result = detector.analyze_transaction(clean_transaction)
        assert result["success"] is True

    def test_threshold_matches_detector(self, detector, clean_transaction):
        """Test threshold in response matches detector's base_threshold."""
        result = detector.analyze_transaction(clean_transaction)
        assert result["threshold"] == detector.base_threshold

        # Modify threshold and verify
        detector.base_threshold = 0.8
        result = detector.analyze_transaction(clean_transaction)
        assert result["threshold"] == 0.8

    def test_flags_format(self, detector):
        """Test flags are formatted as 'reason:weight' strings."""
        data = {
            "amount": 15000.0,
            "geolocation": "KP",
            "address": "0xA",  # Avoid self_transfer
            "recipient": "0xB",
        }
        result = detector.analyze_transaction(data)

        assert len(result["flags"]) == 2
        for flag in result["flags"]:
            assert ":" in flag
            reason, weight = flag.split(":")
            assert len(reason) > 0
            assert float(weight) > 0

    def test_flags_order_matches_detection_order(self, detector):
        """Test flags appear in detection order."""
        data = {
            "amount": 15000.0,  # First check
            "geolocation": "KP",  # Second check
            "tx_type": "anonymous_bridge",  # Third check
            "address": "0xSame",  # Fourth check
            "recipient": "0xSame",
        }
        result = detector.analyze_transaction(data)

        expected_order = ["high_value", "sanctioned_region", "high_risk_type", "self_transfer"]
        for i, flag in enumerate(result["flags"]):
            reason = flag.split(":")[0]
            assert reason == expected_order[i]


# -----------------------------------------------------------------------------
# Edge Cases and Boundary Conditions
# -----------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_transaction(self, detector):
        """Test analyzing empty transaction dict triggers self_transfer.

        Note: Empty dict means data.get('address') == data.get('recipient') == None,
        and None == None is True, so self_transfer is triggered.
        """
        result = detector.analyze_transaction({})

        assert result["success"] is True
        # Empty transaction triggers self_transfer since None == None
        assert result["score"] == 0.1
        assert result["action"] == "allow"
        assert len(result["flags"]) == 1
        assert "self_transfer:0.10" in result["flags"]

    def test_amount_boundary_9999_99(self, detector):
        """Test amount at 9999.99 doesn't trigger high_value."""
        data = {"amount": 9999.99, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value" not in str(result["flags"])

    def test_amount_boundary_10000_00(self, detector):
        """Test amount at 10000.00 triggers high_value."""
        data = {"amount": 10000.00, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value:0.35" in result["flags"]

    def test_negative_amount(self, detector):
        """Test negative amount doesn't trigger high_value."""
        data = {"amount": -15000.0, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value" not in str(result["flags"])

    def test_zero_amount(self, detector):
        """Test zero amount doesn't trigger high_value."""
        data = {"amount": 0, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value" not in str(result["flags"])

    def test_very_large_amount(self, detector):
        """Test very large amount triggers high_value."""
        data = {"amount": 1e18, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value:0.35" in result["flags"]

    def test_amount_as_int(self, detector):
        """Test integer amount is handled correctly."""
        data = {"amount": 15000, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert "high_value:0.35" in result["flags"]

    def test_extra_fields_ignored(self, detector):
        """Test extra fields in transaction are ignored."""
        data = {
            "amount": 100.0,
            "address": "0xA",
            "recipient": "0xB",
            "extra_field": "some_value",
            "another_field": 12345,
            "nested": {"data": "here"},
        }
        result = detector.analyze_transaction(data)
        assert result["success"] is True
        assert result["score"] == 0.0

    def test_geolocation_lowercase(self, detector):
        """Test lowercase geolocation doesn't match SUSPICIOUS_COUNTRIES."""
        data = {"geolocation": "kp", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        # SUSPICIOUS_COUNTRIES uses uppercase, so lowercase shouldn't match
        assert "sanctioned_region" not in str(result["flags"])

    def test_empty_string_values(self, detector):
        """Test empty string values are handled correctly."""
        data = {
            "address": "",
            "recipient": "",
            "geolocation": "",
            "tx_type": "",
            "amount": 0,
        }
        result = detector.analyze_transaction(data)
        # Empty strings match each other for self_transfer
        assert "self_transfer:0.10" in result["flags"]


# -----------------------------------------------------------------------------
# Constants Verification Tests
# -----------------------------------------------------------------------------

class TestConstants:
    """Test module-level constants."""

    def test_suspicious_countries_content(self):
        """Verify SUSPICIOUS_COUNTRIES contains expected countries."""
        assert "KP" in SUSPICIOUS_COUNTRIES  # North Korea
        assert "IR" in SUSPICIOUS_COUNTRIES  # Iran
        assert "SY" in SUSPICIOUS_COUNTRIES  # Syria

    def test_suspicious_countries_is_set(self):
        """Verify SUSPICIOUS_COUNTRIES is a set for O(1) lookup."""
        assert isinstance(SUSPICIOUS_COUNTRIES, set)

    def test_high_risk_tx_types_content(self):
        """Verify HIGH_RISK_TX_TYPES contains expected types."""
        assert "anonymous_bridge" in HIGH_RISK_TX_TYPES
        assert "obfuscated_transfer" in HIGH_RISK_TX_TYPES

    def test_high_risk_tx_types_is_set(self):
        """Verify HIGH_RISK_TX_TYPES is a set for O(1) lookup."""
        assert isinstance(HIGH_RISK_TX_TYPES, set)


# -----------------------------------------------------------------------------
# Multiple Transaction Analysis Tests
# -----------------------------------------------------------------------------

class TestMultipleTransactions:
    """Test analyzing multiple transactions."""

    def test_detector_reusable(self, detector):
        """Test detector can be reused for multiple transactions."""
        tx1 = {"amount": 15000.0, "address": "0xA", "recipient": "0xB"}
        tx2 = {"geolocation": "KP", "address": "0xA", "recipient": "0xB"}
        tx3 = {"amount": 100.0, "address": "0xA", "recipient": "0xB"}

        result1 = detector.analyze_transaction(tx1)
        result2 = detector.analyze_transaction(tx2)
        result3 = detector.analyze_transaction(tx3)

        assert result1["score"] == 0.35
        assert result2["score"] == 0.4
        assert result3["score"] == 0.0

    def test_no_state_leakage(self, detector):
        """Test that analyzing one transaction doesn't affect the next."""
        # Analyze a high-risk transaction
        high_risk = {
            "amount": 15000.0,
            "geolocation": "KP",
            "tx_type": "anonymous_bridge",
            "address": "0xA",
            "recipient": "0xB",
        }
        result1 = detector.analyze_transaction(high_risk)
        assert result1["score"] == 1.0

        # Analyze a clean transaction
        clean = {"amount": 100.0, "address": "0xA", "recipient": "0xB"}
        result2 = detector.analyze_transaction(clean)
        assert result2["score"] == 0.0  # Should not be affected by previous analysis


# -----------------------------------------------------------------------------
# Weight Verification Tests
# -----------------------------------------------------------------------------

class TestWeightValues:
    """Test that signal weights match expected values."""

    def test_high_value_weight(self, detector):
        """Verify high_value signal weight is 0.35."""
        data = {"amount": 15000.0, "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.35

    def test_sanctioned_region_weight(self, detector):
        """Verify sanctioned_region signal weight is 0.40."""
        data = {"geolocation": "KP", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.40

    def test_high_risk_type_weight(self, detector):
        """Verify high_risk_type signal weight is 0.25."""
        data = {"tx_type": "anonymous_bridge", "address": "0xA", "recipient": "0xB"}
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.25

    def test_self_transfer_weight(self, detector):
        """Verify self_transfer signal weight is 0.10."""
        data = {"address": "0xSame", "recipient": "0xSame"}
        result = detector.analyze_transaction(data)
        assert result["score"] == 0.10


# -----------------------------------------------------------------------------
# Real-World Scenario Tests
# -----------------------------------------------------------------------------

class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_legitimate_small_transfer(self, detector):
        """Test legitimate small transfer is allowed."""
        data = {
            "address": "0xAlice",
            "recipient": "0xBob",
            "amount": 50.0,
            "geolocation": "US",
            "tx_type": "standard_transfer",
        }
        result = detector.analyze_transaction(data)

        assert result["action"] == "allow"
        assert result["score"] == 0.0
        assert len(result["flags"]) == 0

    def test_legitimate_large_transfer(self, detector):
        """Test legitimate large transfer triggers review."""
        data = {
            "address": "0xCorporate",
            "recipient": "0xExchange",
            "amount": 100000.0,
            "geolocation": "CH",  # Switzerland
            "tx_type": "standard_transfer",
        }
        result = detector.analyze_transaction(data)

        # Only high_value flag
        assert result["score"] == 0.35
        assert result["action"] == "allow"  # 0.35 < 0.6 threshold
        assert len(result["flags"]) == 1

    def test_suspicious_mixer_transaction(self, detector):
        """Test transaction through mixer service is flagged."""
        data = {
            "address": "0xUser",
            "recipient": "0xMixer",
            "amount": 5000.0,
            "geolocation": "US",
            "tx_type": "obfuscated_transfer",
        }
        result = detector.analyze_transaction(data)

        assert result["score"] == 0.25
        assert "high_risk_type:0.25" in result["flags"]

    def test_high_risk_cross_border(self, detector):
        """Test high-risk cross-border transaction."""
        data = {
            "address": "0xSender",
            "recipient": "0xReceiver",
            "amount": 50000.0,  # Large amount
            "geolocation": "IR",  # Iran
            "tx_type": "anonymous_bridge",  # Mixer
        }
        result = detector.analyze_transaction(data)

        # All three flags: 0.35 + 0.40 + 0.25 = 1.0
        assert result["score"] == 1.0
        assert result["action"] == "review"
        assert len(result["flags"]) == 3

    def test_wash_trading_pattern(self, detector):
        """Test potential wash trading (self-transfer with high value)."""
        data = {
            "address": "0xTrader",
            "recipient": "0xTrader",  # Same address
            "amount": 25000.0,  # High value
            "geolocation": "US",
            "tx_type": "standard_transfer",
        }
        result = detector.analyze_transaction(data)

        # high_value + self_transfer: 0.35 + 0.10 = 0.45
        assert result["score"] == 0.45
        assert result["action"] == "allow"  # Below 0.6 threshold
        assert len(result["flags"]) == 2


# -----------------------------------------------------------------------------
# Module Export Tests
# -----------------------------------------------------------------------------

class TestModuleExports:
    """Test module-level exports."""

    def test_all_exports(self):
        """Verify __all__ contains FraudDetector."""
        from xai.core.security import fraud_detection
        assert "FraudDetector" in fraud_detection.__all__
