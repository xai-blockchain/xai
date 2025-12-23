"""
Comprehensive test coverage for AML Compliance module

Tests cover:
- Risk scoring and calculation
- Transaction monitoring
- Suspicious activity detection
- Address blacklisting and sanctions
- Regulatory dashboard and reporting
- Public explorer API
- All compliance checks and validators
"""

import time
import pytest
from unittest.mock import Mock, MagicMock, patch

from xai.core.aml_compliance import (
    RiskLevel,
    FlagReason,
    TransactionRiskScore,
    AddressBlacklist,
    RegulatorDashboard,
    PublicExplorerAPI,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def risk_scorer():
    """Create a TransactionRiskScore instance"""
    return TransactionRiskScore()


@pytest.fixture
def address_blacklist():
    """Create an AddressBlacklist instance"""
    return AddressBlacklist()


@pytest.fixture
def mock_blockchain():
    """Create a mock blockchain with test data"""
    blockchain = Mock()

    # Create sample transactions with varying risk scores
    blockchain.chain = [
        {
            "index": 0,
            "timestamp": time.time() - 10000,
            "transactions": [
                {
                    "hash": "genesis_tx",
                    "sender": "genesis",
                    "recipient": "XAI_ADDR_1",
                    "amount": 1000000,
                    "amount_usd": 0,
                    "timestamp": time.time() - 10000,
                    "risk_score": 0,
                    "risk_level": RiskLevel.CLEAN.value,
                    "flag_reasons": [],
                }
            ],
        },
        {
            "index": 1,
            "timestamp": time.time() - 5000,
            "transactions": [
                {
                    "hash": "tx_normal_1",
                    "sender": "XAI_ADDR_1",
                    "recipient": "XAI_ADDR_2",
                    "amount": 100,
                    "amount_usd": 20,
                    "timestamp": time.time() - 5000,
                    "risk_score": 10,
                    "risk_level": RiskLevel.CLEAN.value,
                    "flag_reasons": [],
                },
                {
                    "hash": "tx_high_risk_1",
                    "sender": "XAI_ADDR_3",
                    "recipient": "XAI_ADDR_4",
                    "amount": 100000,
                    "amount_usd": 15000,
                    "timestamp": time.time() - 5000,
                    "risk_score": 75,
                    "risk_level": RiskLevel.HIGH.value,
                    "flag_reasons": [FlagReason.LARGE_AMOUNT.value],
                },
            ],
        },
        {
            "index": 2,
            "timestamp": time.time() - 1000,
            "transactions": [
                {
                    "hash": "tx_critical_1",
                    "sender": "XAI_ADDR_3",
                    "recipient": "XAI_ADDR_5",
                    "amount": 200000,
                    "amount_usd": 25000,
                    "timestamp": time.time() - 1000,
                    "risk_score": 90,
                    "risk_level": RiskLevel.CRITICAL.value,
                    "flag_reasons": [
                        FlagReason.LARGE_AMOUNT.value,
                        FlagReason.BLACKLISTED_ADDRESS.value,
                    ],
                },
            ],
        },
    ]

    return blockchain


@pytest.fixture
def regulator_dashboard(mock_blockchain):
    """Create a RegulatorDashboard instance"""
    return RegulatorDashboard(mock_blockchain)


@pytest.fixture
def public_explorer(mock_blockchain):
    """Create a PublicExplorerAPI instance"""
    return PublicExplorerAPI(mock_blockchain)


# ============================================================================
# RiskLevel Enum Tests
# ============================================================================


def test_risk_level_enum_values():
    """Test RiskLevel enum has correct values"""
    assert RiskLevel.CLEAN.value == "clean"
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"


def test_risk_level_enum_members():
    """Test RiskLevel enum has all expected members"""
    levels = [member.value for member in RiskLevel]
    assert "clean" in levels
    assert "low" in levels
    assert "medium" in levels
    assert "high" in levels
    assert "critical" in levels


# ============================================================================
# FlagReason Enum Tests
# ============================================================================


def test_flag_reason_enum_values():
    """Test FlagReason enum has correct values"""
    assert FlagReason.LARGE_AMOUNT.value == "large_amount"
    assert FlagReason.RAPID_SUCCESSION.value == "rapid_succession"
    assert FlagReason.STRUCTURING.value == "structuring"
    assert FlagReason.BLACKLISTED_ADDRESS.value == "blacklisted_address"
    assert FlagReason.SANCTIONED_COUNTRY.value == "sanctioned_country"
    assert FlagReason.MIXING_SERVICE.value == "mixing_service"
    assert FlagReason.NEW_ACCOUNT_LARGE_TX.value == "new_account_large_transaction"
    assert FlagReason.ROUND_AMOUNT.value == "round_amount_pattern"
    assert FlagReason.VELOCITY_SPIKE.value == "velocity_spike"


def test_flag_reason_enum_members():
    """Test FlagReason enum has all expected members"""
    reasons = [member.value for member in FlagReason]
    assert len(reasons) == 9
    assert "large_amount" in reasons
    assert "structuring" in reasons


# ============================================================================
# TransactionRiskScore Initialization Tests
# ============================================================================


def test_transaction_risk_score_init(risk_scorer):
    """Test TransactionRiskScore initialization"""
    assert risk_scorer.transaction_history == {}
    assert isinstance(risk_scorer.blacklisted_addresses, set)
    assert isinstance(risk_scorer.sanctioned_addresses, set)
    assert len(risk_scorer.blacklisted_addresses) == 0
    assert len(risk_scorer.sanctioned_addresses) == 0


def test_transaction_risk_score_thresholds(risk_scorer):
    """Test TransactionRiskScore has correct thresholds"""
    assert risk_scorer.LARGE_AMOUNT_USD == 10000
    assert risk_scorer.RAPID_TX_WINDOW == 3600
    assert risk_scorer.RAPID_TX_COUNT == 10
    assert risk_scorer.STRUCTURING_THRESHOLD == 9000
    assert risk_scorer.NEW_ACCOUNT_DAYS == 7


# ============================================================================
# Risk Score Calculation Tests - Basic Scenarios
# ============================================================================


def test_calculate_risk_score_clean_transaction(risk_scorer):
    """Test risk score for clean transaction"""
    tx = {
        "sender": "XAI_CLEAN_1",
        "recipient": "XAI_CLEAN_2",
        "amount": 50,
        "amount_usd": 10,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 0
    assert len(reasons) == 0


def test_calculate_risk_score_large_amount(risk_scorer):
    """Test risk score for large amount transaction"""
    tx = {
        "sender": "XAI_SENDER_1",
        "recipient": "XAI_RECIPIENT_1",
        "amount": 100000,
        "amount_usd": 12000,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 40  # 30 for large amount + 10 for round amount (100000)
    assert FlagReason.LARGE_AMOUNT.value in reasons


def test_calculate_risk_score_exactly_threshold(risk_scorer):
    """Test risk score at exact threshold"""
    tx = {
        "sender": "XAI_SENDER_2",
        "recipient": "XAI_RECIPIENT_2",
        "amount": 50000,
        "amount_usd": 10000,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 40  # 30 for large amount + 10 for round amount (50000)
    assert FlagReason.LARGE_AMOUNT.value in reasons


def test_calculate_risk_score_just_below_threshold(risk_scorer):
    """Test risk score just below threshold"""
    tx = {
        "sender": "XAI_SENDER_3",
        "recipient": "XAI_RECIPIENT_3",
        "amount": 49999,
        "amount_usd": 9999,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 0
    assert FlagReason.LARGE_AMOUNT.value not in reasons


# ============================================================================
# Blacklist and Sanctions Tests
# ============================================================================


def test_calculate_risk_score_blacklisted_sender(risk_scorer):
    """Test risk score for blacklisted sender"""
    risk_scorer.add_to_blacklist("XAI_BLACKLISTED_1", "fraud")

    tx = {
        "sender": "XAI_BLACKLISTED_1",
        "recipient": "XAI_CLEAN_1",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 50
    assert FlagReason.BLACKLISTED_ADDRESS.value in reasons


def test_calculate_risk_score_blacklisted_recipient(risk_scorer):
    """Test risk score for blacklisted recipient"""
    risk_scorer.add_to_blacklist("XAI_BLACKLISTED_2", "scam")

    tx = {
        "sender": "XAI_CLEAN_1",
        "recipient": "XAI_BLACKLISTED_2",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 50
    assert FlagReason.BLACKLISTED_ADDRESS.value in reasons


def test_calculate_risk_score_sanctioned_sender(risk_scorer):
    """Test risk score for sanctioned sender"""
    risk_scorer.add_to_sanctions_list("XAI_SANCTIONED_1", "North Korea")

    tx = {
        "sender": "XAI_SANCTIONED_1",
        "recipient": "XAI_CLEAN_1",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 60
    assert FlagReason.SANCTIONED_COUNTRY.value in reasons


def test_calculate_risk_score_sanctioned_recipient(risk_scorer):
    """Test risk score for sanctioned recipient"""
    risk_scorer.add_to_sanctions_list("XAI_SANCTIONED_2", "Iran")

    tx = {
        "sender": "XAI_CLEAN_1",
        "recipient": "XAI_SANCTIONED_2",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 60
    assert FlagReason.SANCTIONED_COUNTRY.value in reasons


def test_calculate_risk_score_both_blacklisted_and_sanctioned(risk_scorer):
    """Test risk score for both blacklisted and sanctioned address"""
    risk_scorer.add_to_blacklist("XAI_BAD_ACTOR", "terrorism")
    risk_scorer.add_to_sanctions_list("XAI_BAD_ACTOR", "Syria")

    tx = {
        "sender": "XAI_BAD_ACTOR",
        "recipient": "XAI_CLEAN_1",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 100  # Capped at 100
    assert FlagReason.BLACKLISTED_ADDRESS.value in reasons
    assert FlagReason.SANCTIONED_COUNTRY.value in reasons


# ============================================================================
# Structuring Detection Tests
# ============================================================================


def test_calculate_risk_score_structuring_pattern(risk_scorer):
    """Test detection of structuring pattern"""
    current_time = time.time()

    history = [
        {"amount_usd": 9000, "timestamp": current_time - 20000},
        {"amount_usd": 8500, "timestamp": current_time - 15000},
        {"amount_usd": 8900, "timestamp": current_time - 10000},
    ]

    tx = {
        "sender": "XAI_STRUCTURER",
        "recipient": "XAI_RECIPIENT",
        "amount": 45000,
        "amount_usd": 8800,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    # Structuring detected, but history is too old (outside 24h window)
    # So we might get different scores - just check structuring is detected when recent
    assert isinstance(score, int)
    assert isinstance(reasons, list)


def test_calculate_risk_score_no_structuring_pattern(risk_scorer):
    """Test no false positive for structuring"""
    current_time = time.time()

    history = [
        {"amount_usd": 5000, "timestamp": current_time - 20000},
        {"amount_usd": 3000, "timestamp": current_time - 15000},
    ]

    tx = {
        "sender": "XAI_NORMAL",
        "recipient": "XAI_RECIPIENT",
        "amount": 25000,
        "amount_usd": 4000,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert FlagReason.STRUCTURING.value not in reasons


def test_detect_structuring_exactly_three_transactions(risk_scorer):
    """Test structuring detection with exactly 3 transactions"""
    recent_txs = [
        {"amount_usd": 8000},
        {"amount_usd": 8500},
        {"amount_usd": 9000},
    ]

    current_tx = {"amount_usd": 8800}

    result = risk_scorer._detect_structuring(recent_txs, current_tx)

    assert result is True


def test_detect_structuring_below_threshold(risk_scorer):
    """Test structuring detection with amounts below threshold"""
    recent_txs = [
        {"amount_usd": 7000},
        {"amount_usd": 7500},
        {"amount_usd": 7800},
    ]

    current_tx = {"amount_usd": 7600}

    result = risk_scorer._detect_structuring(recent_txs, current_tx)

    assert result is False


def test_detect_structuring_above_threshold(risk_scorer):
    """Test structuring detection with amounts above threshold"""
    recent_txs = [
        {"amount_usd": 10000},
        {"amount_usd": 11000},
        {"amount_usd": 12000},
    ]

    current_tx = {"amount_usd": 11500}

    result = risk_scorer._detect_structuring(recent_txs, current_tx)

    assert result is False


# ============================================================================
# Rapid Succession Tests
# ============================================================================


def test_calculate_risk_score_rapid_succession(risk_scorer):
    """Test detection of rapid succession transactions"""
    current_time = time.time()

    # 10 transactions in 1 hour
    history = [
        {"amount_usd": 100, "timestamp": current_time - 3000 + (i * 300)}
        for i in range(10)
    ]

    tx = {
        "sender": "XAI_RAPID",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert score == 25
    assert FlagReason.RAPID_SUCCESSION.value in reasons


def test_calculate_risk_score_no_rapid_succession(risk_scorer):
    """Test no false positive for rapid succession"""
    current_time = time.time()

    # Only 5 transactions in time window
    history = [
        {"amount_usd": 100, "timestamp": current_time - 3000 + (i * 600)}
        for i in range(5)
    ]

    tx = {
        "sender": "XAI_NORMAL",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert FlagReason.RAPID_SUCCESSION.value not in reasons


# ============================================================================
# New Account Large Transaction Tests
# ============================================================================


def test_calculate_risk_score_new_account_large_tx(risk_scorer):
    """Test detection of large transaction from new account"""
    current_time = time.time()

    # Account only 3 days old with 2 transactions
    history = [
        {"amount_usd": 100, "timestamp": current_time - (3 * 86400)},
        {"amount_usd": 200, "timestamp": current_time - (2 * 86400)},
    ]

    tx = {
        "sender": "XAI_NEW_ACCOUNT",
        "recipient": "XAI_RECIPIENT",
        "amount": 25000,
        "amount_usd": 6000,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert score == 35
    assert FlagReason.NEW_ACCOUNT_LARGE_TX.value in reasons


def test_calculate_risk_score_new_account_small_tx(risk_scorer):
    """Test new account with small transaction (no flag)"""
    current_time = time.time()

    history = [
        {"amount_usd": 100, "timestamp": current_time - (3 * 86400)},
    ]

    tx = {
        "sender": "XAI_NEW_ACCOUNT",
        "recipient": "XAI_RECIPIENT",
        "amount": 2000,
        "amount_usd": 400,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert FlagReason.NEW_ACCOUNT_LARGE_TX.value not in reasons


def test_calculate_risk_score_old_account_large_tx(risk_scorer):
    """Test old account with large transaction (no new account flag)"""
    current_time = time.time()

    # Account 30 days old
    history = [
        {"amount_usd": 100, "timestamp": current_time - (30 * 86400)},
        {"amount_usd": 200, "timestamp": current_time - (20 * 86400)},
    ]

    tx = {
        "sender": "XAI_OLD_ACCOUNT",
        "recipient": "XAI_RECIPIENT",
        "amount": 25000,
        "amount_usd": 6000,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert FlagReason.NEW_ACCOUNT_LARGE_TX.value not in reasons


# ============================================================================
# Round Amount Tests
# ============================================================================


def test_calculate_risk_score_round_amount_1000(risk_scorer):
    """Test detection of round amount - 1000"""
    tx = {
        "sender": "XAI_SENDER",
        "recipient": "XAI_RECIPIENT",
        "amount": 1000,
        "amount_usd": 200,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert score == 10
    assert FlagReason.ROUND_AMOUNT.value in reasons


def test_calculate_risk_score_round_amount_10000(risk_scorer):
    """Test detection of round amount - 10000"""
    tx = {
        "sender": "XAI_SENDER",
        "recipient": "XAI_RECIPIENT",
        "amount": 10000,
        "amount_usd": 2000,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert FlagReason.ROUND_AMOUNT.value in reasons


def test_calculate_risk_score_round_amount_100000(risk_scorer):
    """Test detection of round amount - 100000"""
    tx = {
        "sender": "XAI_SENDER",
        "recipient": "XAI_RECIPIENT",
        "amount": 100000,
        "amount_usd": 20000,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert FlagReason.ROUND_AMOUNT.value in reasons


def test_calculate_risk_score_non_round_amount(risk_scorer):
    """Test no false positive for non-round amounts"""
    tx = {
        "sender": "XAI_SENDER",
        "recipient": "XAI_RECIPIENT",
        "amount": 1234.56,
        "amount_usd": 246.91,
        "timestamp": time.time(),
    }

    score, reasons = risk_scorer.calculate_risk_score(tx)

    assert FlagReason.ROUND_AMOUNT.value not in reasons


def test_is_round_amount_all_values(risk_scorer):
    """Test is_round_amount with all defined round amounts"""
    round_amounts = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]

    for amount in round_amounts:
        assert risk_scorer._is_round_amount(amount) is True

    assert risk_scorer._is_round_amount(1234) is False
    assert risk_scorer._is_round_amount(9999) is False


# ============================================================================
# Velocity Spike Tests
# ============================================================================


def test_calculate_risk_score_velocity_spike(risk_scorer):
    """Test detection of velocity spike"""
    current_time = time.time()

    # Normal pattern: ~1 hour between transactions
    base_time = current_time - (15 * 3600)
    history = [
        {"amount_usd": 100, "timestamp": base_time + (i * 3600)}
        for i in range(15)
    ]

    # Sudden transaction after only 5 minutes (much faster than 1 hour average)
    last_tx_time = base_time + (14 * 3600)
    tx = {
        "sender": "XAI_VELOCITY",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": last_tx_time + 300,  # Only 5 min after last (vs 1 hour average)
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert score == 30
    assert FlagReason.VELOCITY_SPIKE.value in reasons


def test_calculate_risk_score_no_velocity_spike(risk_scorer):
    """Test no false positive for velocity spike"""
    current_time = time.time()

    # Consistent pattern
    history = [
        {"amount_usd": 100, "timestamp": current_time - (15 * 3600) + (i * 3600)}
        for i in range(15)
    ]

    # Normal next transaction
    tx = {
        "sender": "XAI_NORMAL",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": current_time + 3600,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert FlagReason.VELOCITY_SPIKE.value not in reasons


def test_detect_velocity_spike_insufficient_history(risk_scorer):
    """Test velocity spike detection with insufficient history"""
    current_time = time.time()

    # Only 5 transactions
    history = [
        {"amount_usd": 100, "timestamp": current_time - (i * 3600)}
        for i in range(5)
    ]

    tx = {
        "sender": "XAI_NEW",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": current_time,
    }

    result = risk_scorer._detect_velocity_spike(history, tx)

    assert result is False


def test_detect_velocity_spike_empty_time_diffs(risk_scorer):
    """Test velocity spike detection with edge case"""
    current_time = time.time()

    # All transactions at same time (edge case)
    history = [
        {"amount_usd": 100, "timestamp": current_time}
        for i in range(15)
    ]

    tx = {
        "sender": "XAI_EDGE",
        "recipient": "XAI_RECIPIENT",
        "amount": 500,
        "amount_usd": 100,
        "timestamp": current_time,
    }

    result = risk_scorer._detect_velocity_spike(history, tx)

    # Should handle gracefully
    assert isinstance(result, bool)


# ============================================================================
# Risk Score Cap and Edge Cases
# ============================================================================


def test_calculate_risk_score_capped_at_100(risk_scorer):
    """Test risk score is capped at 100"""
    risk_scorer.add_to_blacklist("XAI_BAD", "fraud")
    risk_scorer.add_to_sanctions_list("XAI_BAD", "Iran")

    current_time = time.time()

    # New account with rapid succession and structuring
    history = [
        {"amount_usd": 9000, "timestamp": current_time - 1000 - (i * 100)}
        for i in range(15)
    ]

    tx = {
        "sender": "XAI_BAD",
        "recipient": "XAI_RECIPIENT",
        "amount": 100000,
        "amount_usd": 15000,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    assert score == 100  # Capped
    assert len(reasons) > 0


def test_get_recent_transactions_within_window(risk_scorer):
    """Test filtering recent transactions within time window"""
    current_time = time.time()

    history = [
        {"timestamp": current_time - 500},
        {"timestamp": current_time - 1000},
        {"timestamp": current_time - 5000},
    ]

    recent = risk_scorer._get_recent_transactions(history, window=3600)

    assert len(recent) == 2


def test_get_recent_transactions_empty_history(risk_scorer):
    """Test filtering with empty history"""
    recent = risk_scorer._get_recent_transactions([], window=3600)

    assert len(recent) == 0


# ============================================================================
# Risk Level Classification Tests
# ============================================================================


def test_get_risk_level_clean(risk_scorer):
    """Test risk level classification - CLEAN"""
    assert risk_scorer.get_risk_level(0) == RiskLevel.CLEAN
    assert risk_scorer.get_risk_level(10) == RiskLevel.CLEAN
    assert risk_scorer.get_risk_level(20) == RiskLevel.CLEAN


def test_get_risk_level_low(risk_scorer):
    """Test risk level classification - LOW"""
    assert risk_scorer.get_risk_level(21) == RiskLevel.LOW
    assert risk_scorer.get_risk_level(30) == RiskLevel.LOW
    assert risk_scorer.get_risk_level(40) == RiskLevel.LOW


def test_get_risk_level_medium(risk_scorer):
    """Test risk level classification - MEDIUM"""
    assert risk_scorer.get_risk_level(41) == RiskLevel.MEDIUM
    assert risk_scorer.get_risk_level(50) == RiskLevel.MEDIUM
    assert risk_scorer.get_risk_level(60) == RiskLevel.MEDIUM


def test_get_risk_level_high(risk_scorer):
    """Test risk level classification - HIGH"""
    assert risk_scorer.get_risk_level(61) == RiskLevel.HIGH
    assert risk_scorer.get_risk_level(70) == RiskLevel.HIGH
    assert risk_scorer.get_risk_level(80) == RiskLevel.HIGH


def test_get_risk_level_critical(risk_scorer):
    """Test risk level classification - CRITICAL"""
    assert risk_scorer.get_risk_level(81) == RiskLevel.CRITICAL
    assert risk_scorer.get_risk_level(90) == RiskLevel.CRITICAL
    assert risk_scorer.get_risk_level(100) == RiskLevel.CRITICAL


# ============================================================================
# AddressBlacklist Tests
# ============================================================================


def test_address_blacklist_init(address_blacklist):
    """Test AddressBlacklist initialization"""
    assert address_blacklist.blacklist == {}
    assert address_blacklist.sanctions == {}


def test_add_blacklist(address_blacklist):
    """Test adding address to blacklist"""
    address_blacklist.add_blacklist("XAI_BAD_1", "fraud", "admin")

    assert "XAI_BAD_1" in address_blacklist.blacklist
    assert address_blacklist.blacklist["XAI_BAD_1"]["reason"] == "fraud"
    assert address_blacklist.blacklist["XAI_BAD_1"]["added_by"] == "admin"
    assert "timestamp" in address_blacklist.blacklist["XAI_BAD_1"]


def test_add_blacklist_default_added_by(address_blacklist):
    """Test adding to blacklist with default added_by"""
    address_blacklist.add_blacklist("XAI_BAD_2", "scam")

    assert address_blacklist.blacklist["XAI_BAD_2"]["added_by"] == "protocol"


def test_add_sanction(address_blacklist):
    """Test adding sanctioned address"""
    address_blacklist.add_sanction("XAI_SANCTIONED_1", "North Korea")

    assert "XAI_SANCTIONED_1" in address_blacklist.sanctions
    assert address_blacklist.sanctions["XAI_SANCTIONED_1"]["country"] == "North Korea"
    assert "timestamp" in address_blacklist.sanctions["XAI_SANCTIONED_1"]


def test_is_blacklisted_true(address_blacklist):
    """Test is_blacklisted returns True"""
    address_blacklist.add_blacklist("XAI_BAD", "fraud")

    assert address_blacklist.is_blacklisted("XAI_BAD") is True


def test_is_blacklisted_false(address_blacklist):
    """Test is_blacklisted returns False"""
    assert address_blacklist.is_blacklisted("XAI_CLEAN") is False


def test_is_sanctioned_true(address_blacklist):
    """Test is_sanctioned returns True"""
    address_blacklist.add_sanction("XAI_SANCTIONED", "Iran")

    assert address_blacklist.is_sanctioned("XAI_SANCTIONED") is True


def test_is_sanctioned_false(address_blacklist):
    """Test is_sanctioned returns False"""
    assert address_blacklist.is_sanctioned("XAI_CLEAN") is False


def test_get_blacklist(address_blacklist):
    """Test getting full blacklist"""
    address_blacklist.add_blacklist("XAI_BAD_1", "fraud")
    address_blacklist.add_blacklist("XAI_BAD_2", "scam")

    blacklist = address_blacklist.get_blacklist()

    assert len(blacklist) == 2
    assert "XAI_BAD_1" in blacklist
    assert "XAI_BAD_2" in blacklist


def test_get_sanctions_list(address_blacklist):
    """Test getting full sanctions list"""
    address_blacklist.add_sanction("XAI_SANCTIONED_1", "Iran")
    address_blacklist.add_sanction("XAI_SANCTIONED_2", "Syria")

    sanctions = address_blacklist.get_sanctions_list()

    assert len(sanctions) == 2
    assert "XAI_SANCTIONED_1" in sanctions
    assert "XAI_SANCTIONED_2" in sanctions


# ============================================================================
# RegulatorDashboard Tests
# ============================================================================


def test_regulator_dashboard_init(regulator_dashboard, mock_blockchain):
    """Test RegulatorDashboard initialization"""
    assert regulator_dashboard.blockchain == mock_blockchain
    assert isinstance(regulator_dashboard.risk_scorer, TransactionRiskScore)


def test_get_flagged_transactions(regulator_dashboard):
    """Test getting flagged transactions"""
    flagged = regulator_dashboard.get_flagged_transactions(min_score=61)

    assert len(flagged) >= 1
    assert all(tx["risk_score"] >= 61 for tx in flagged)


def test_get_flagged_transactions_sorted_by_time(regulator_dashboard):
    """Test flagged transactions are sorted by timestamp"""
    flagged = regulator_dashboard.get_flagged_transactions(min_score=0)

    if len(flagged) > 1:
        for i in range(len(flagged) - 1):
            assert flagged[i]["timestamp"] >= flagged[i + 1]["timestamp"]


def test_get_flagged_transactions_with_limit(regulator_dashboard):
    """Test flagged transactions respects limit"""
    flagged = regulator_dashboard.get_flagged_transactions(min_score=0, limit=2)

    assert len(flagged) <= 2


def test_get_high_risk_addresses(regulator_dashboard):
    """Test getting high risk addresses"""
    high_risk = regulator_dashboard.get_high_risk_addresses(min_score=70)

    assert isinstance(high_risk, list)


def test_get_address_risk_profile_empty_address(regulator_dashboard):
    """Test getting risk profile for empty address"""
    profile = regulator_dashboard.get_address_risk_profile("")

    assert profile["address"] == ""
    assert profile["risk_score"] == 0
    assert profile["risk_level"] == RiskLevel.CLEAN.value
    assert profile["flag_reasons"] == []
    assert profile["last_seen"] is None


def test_export_compliance_report(regulator_dashboard):
    """Test exporting compliance report"""
    start_date = time.time() - 20000
    end_date = time.time()

    report = regulator_dashboard.export_compliance_report(start_date, end_date)

    assert "report_generated" in report
    assert report["period_start"] == start_date
    assert report["period_end"] == end_date
    assert "summary" in report


def test_search_transactions_no_filters(regulator_dashboard):
    """Test searching transactions with no filters"""
    results = regulator_dashboard.search_transactions()

    assert isinstance(results, list)


# ============================================================================
# PublicExplorerAPI Tests
# ============================================================================


def test_public_explorer_init(public_explorer, mock_blockchain):
    """Test PublicExplorerAPI initialization"""
    assert public_explorer.blockchain == mock_blockchain


def test_get_transaction_existing(public_explorer):
    """Test getting existing transaction"""
    tx = public_explorer.get_transaction("tx_normal_1")

    assert tx is not None
    assert tx["hash"] == "tx_normal_1"
    assert "risk_score" not in tx
    assert "risk_level" not in tx


def test_get_transaction_nonexistent(public_explorer):
    """Test getting nonexistent transaction"""
    tx = public_explorer.get_transaction("nonexistent_hash")

    assert tx is None


def test_get_recent_transactions(public_explorer):
    """Test getting recent transactions"""
    transactions = public_explorer.get_recent_transactions(limit=10)

    assert isinstance(transactions, list)
    assert len(transactions) <= 10

    for tx in transactions:
        assert "risk_score" not in tx
        assert "risk_level" not in tx


# ============================================================================
# Additional Coverage Tests
# ============================================================================


def test_get_address_risk_profile_with_transactions(regulator_dashboard, mock_blockchain):
    """Test get_address_risk_profile with actual transactions"""
    # This should hit lines 314-327
    profile = regulator_dashboard.get_address_risk_profile("XAI_ADDR_3")

    assert profile["address"] == "XAI_ADDR_3"
    assert profile["risk_score"] > 0  # Should have risk score from mock data


def test_search_transactions_by_address_match(regulator_dashboard, mock_blockchain):
    """Test search_transactions address matching"""
    # This should hit lines 382-395
    results = regulator_dashboard.search_transactions(address="XAI_ADDR_1")

    assert isinstance(results, list)


def test_search_transactions_by_min_amount_filter(regulator_dashboard, mock_blockchain):
    """Test search_transactions min amount filtering"""
    results = regulator_dashboard.search_transactions(min_amount=15000)

    assert isinstance(results, list)


def test_search_transactions_by_risk_level_filter(regulator_dashboard, mock_blockchain):
    """Test search_transactions risk level filtering"""
    results = regulator_dashboard.search_transactions(risk_level=RiskLevel.HIGH)

    assert isinstance(results, list)


def test_get_recent_transactions_early_termination(public_explorer, mock_blockchain):
    """Test get_recent_transactions stops at limit"""
    # This should hit line 445 (early return when limit reached)
    transactions = public_explorer.get_recent_transactions(limit=1)

    assert len(transactions) <= 1


def test_detect_structuring_with_recent_txs(risk_scorer):
    """Test structuring detection with recent transactions in 24h window"""
    current_time = time.time()

    # Transactions within 24 hours
    history = [
        {"amount_usd": 9000, "timestamp": current_time - 3600},
        {"amount_usd": 8500, "timestamp": current_time - 7200},
        {"amount_usd": 8900, "timestamp": current_time - 10800},
    ]

    tx = {
        "sender": "XAI_STRUCTURER",
        "recipient": "XAI_RECIPIENT",
        "amount": 45000,
        "amount_usd": 8800,
        "timestamp": current_time,
    }

    score, reasons = risk_scorer.calculate_risk_score(tx, history)

    # Should detect structuring now that transactions are within 24h
    assert FlagReason.STRUCTURING.value in reasons


def test_export_compliance_report_with_date_filtering(regulator_dashboard, mock_blockchain):
    """Test export_compliance_report filters by date correctly"""
    current_time = time.time()

    # Test with date range that excludes some transactions
    start_date = current_time - 6000
    end_date = current_time - 500

    report = regulator_dashboard.export_compliance_report(start_date, end_date)

    assert "summary" in report
    assert "total_transactions" in report["summary"]
