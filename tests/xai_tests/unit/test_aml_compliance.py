"""
Unit tests for AML Compliance module

Tests transaction risk scoring, blacklist management, and regulatory reporting
"""

import pytest
import time
from xai.core.security.aml_compliance import (
    RiskLevel,
    FlagReason,
    TransactionRiskScore,
    AddressBlacklist,
    RegulatorDashboard,
    PublicExplorerAPI,
)


class TestTransactionRiskScore:
    """Test transaction risk scoring system"""

    def test_init(self):
        """Test TransactionRiskScore initialization"""
        scorer = TransactionRiskScore()
        assert scorer.LARGE_AMOUNT_USD == 10000
        assert scorer.RAPID_TX_WINDOW == 3600
        assert len(scorer.blacklisted_addresses) == 0
        assert len(scorer.sanctioned_addresses) == 0

    def test_normal_transaction(self):
        """Test normal transaction has low risk score"""
        scorer = TransactionRiskScore()
        tx = {
            "sender": "XAI123",
            "recipient": "XAI456",
            "amount": 100,
            "amount_usd": 20,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert score == 0
        assert len(reasons) == 0

    def test_large_amount_flag(self):
        """Test large amount triggers risk flag"""
        scorer = TransactionRiskScore()
        tx = {
            "sender": "XAI789",
            "recipient": "XAI012",
            "amount": 50000,
            "amount_usd": 11500,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert score >= 30
        assert FlagReason.LARGE_AMOUNT.value in reasons

    def test_blacklisted_address(self):
        """Test blacklisted address detection"""
        scorer = TransactionRiskScore()
        scorer.blacklisted_addresses.add("XAI_BLACKLISTED")

        tx = {
            "sender": "XAI_BLACKLISTED",
            "recipient": "XAI456",
            "amount": 100,
            "amount_usd": 20,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert score >= 50
        assert FlagReason.BLACKLISTED_ADDRESS.value in reasons

    def test_sanctioned_address(self):
        """Test sanctioned address detection"""
        scorer = TransactionRiskScore()
        scorer.sanctioned_addresses.add("XAI_SANCTIONED")

        tx = {
            "sender": "XAI_SANCTIONED",
            "recipient": "XAI456",
            "amount": 100,
            "amount_usd": 20,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert score >= 60
        assert FlagReason.SANCTIONED_COUNTRY.value in reasons

    def test_structuring_detection(self):
        """Test structuring pattern detection"""
        scorer = TransactionRiskScore()
        
        # Create history of transactions just under $10k
        current_time = time.time()
        history = [
            {"amount_usd": 9000, "timestamp": current_time - 3600},
            {"amount_usd": 8900, "timestamp": current_time - 1800},
            {"amount_usd": 9100, "timestamp": current_time - 900},
        ]

        tx = {
            "sender": "XAI345",
            "recipient": "XAI678",
            "amount": 9000,
            "amount_usd": 8950,
            "timestamp": current_time,
        }

        score, reasons = scorer.calculate_risk_score(tx, history)
        assert score >= 40
        assert FlagReason.STRUCTURING.value in reasons

    def test_rapid_succession(self):
        """Test rapid transaction succession detection"""
        scorer = TransactionRiskScore()
        
        current_time = time.time()
        # Create 10 transactions in last hour
        history = [
            {"amount_usd": 100, "timestamp": current_time - (i * 300)}
            for i in range(10)
        ]

        tx = {
            "sender": "XAI999",
            "recipient": "XAI888",
            "amount": 100,
            "amount_usd": 100,
            "timestamp": current_time,
        }

        score, reasons = scorer.calculate_risk_score(tx, history)
        assert score >= 25
        assert FlagReason.RAPID_SUCCESSION.value in reasons

    def test_new_account_large_transaction(self):
        """Test new account with large transaction"""
        scorer = TransactionRiskScore()
        
        current_time = time.time()
        # New account (2 days old)
        history = [
            {"amount_usd": 50, "timestamp": current_time - (2 * 86400)},
        ]

        tx = {
            "sender": "XAI_NEW",
            "recipient": "XAI456",
            "amount": 5000,
            "amount_usd": 6000,
            "timestamp": current_time,
        }

        score, reasons = scorer.calculate_risk_score(tx, history)
        assert score >= 35
        assert FlagReason.NEW_ACCOUNT_LARGE_TX.value in reasons

    def test_round_amount_detection(self):
        """Test round amount pattern detection"""
        scorer = TransactionRiskScore()
        
        tx = {
            "sender": "XAI111",
            "recipient": "XAI222",
            "amount": 10000,
            "amount_usd": 10000,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert FlagReason.ROUND_AMOUNT.value in reasons

    def test_velocity_spike_detection(self):
        """Test velocity spike detection"""
        scorer = TransactionRiskScore()
        
        current_time = time.time()
        # Normal: 1 tx per day, then sudden spike
        history = [
            {"timestamp": current_time - (i * 86400), "amount_usd": 100}
            for i in range(1, 11)
        ]

        tx = {
            "sender": "XAI_SPIKE",
            "recipient": "XAI456",
            "amount": 100,
            "amount_usd": 100,
            "timestamp": current_time,
        }

        score, reasons = scorer.calculate_risk_score(tx, history)
        # Should detect velocity spike
        if FlagReason.VELOCITY_SPIKE.value in reasons:
            assert score >= 30

    def test_get_risk_level(self):
        """Test risk level classification"""
        scorer = TransactionRiskScore()
        
        assert scorer.get_risk_level(10) == RiskLevel.CLEAN
        assert scorer.get_risk_level(30) == RiskLevel.LOW
        assert scorer.get_risk_level(50) == RiskLevel.MEDIUM
        assert scorer.get_risk_level(70) == RiskLevel.HIGH
        assert scorer.get_risk_level(90) == RiskLevel.CRITICAL

    def test_score_capped_at_100(self):
        """Test that risk score is capped at 100"""
        scorer = TransactionRiskScore()
        scorer.blacklisted_addresses.add("XAI_BAD")
        scorer.sanctioned_addresses.add("XAI_BAD")
        
        tx = {
            "sender": "XAI_BAD",
            "recipient": "XAI456",
            "amount": 100000,
            "amount_usd": 50000,
            "timestamp": time.time(),
        }

        score, reasons = scorer.calculate_risk_score(tx)
        assert score <= 100

    def test_add_to_blacklist(self):
        """Test adding address to blacklist"""
        scorer = TransactionRiskScore()
        scorer.add_to_blacklist("XAI_EVIL", "Fraud")
        
        assert "XAI_EVIL" in scorer.blacklisted_addresses

    def test_add_to_sanctions_list(self):
        """Test adding address to sanctions list"""
        scorer = TransactionRiskScore()
        scorer.add_to_sanctions_list("XAI_SANCTIONED", "North Korea")
        
        assert "XAI_SANCTIONED" in scorer.sanctioned_addresses


class TestAddressBlacklist:
    """Test address blacklist management"""

    def test_init(self):
        """Test AddressBlacklist initialization"""
        blacklist = AddressBlacklist()
        assert len(blacklist.blacklist) == 0
        assert len(blacklist.sanctions) == 0

    def test_add_blacklist(self):
        """Test adding address to blacklist"""
        blacklist = AddressBlacklist()
        blacklist.add_blacklist("XAI_BAD", "Phishing attack", "security_team")
        
        assert blacklist.is_blacklisted("XAI_BAD")
        assert blacklist.blacklist["XAI_BAD"]["reason"] == "Phishing attack"
        assert blacklist.blacklist["XAI_BAD"]["added_by"] == "security_team"

    def test_add_sanction(self):
        """Test adding sanctioned address"""
        blacklist = AddressBlacklist()
        blacklist.add_sanction("XAI_SANCTIONED", "Iran")
        
        assert blacklist.is_sanctioned("XAI_SANCTIONED")
        assert blacklist.sanctions["XAI_SANCTIONED"]["country"] == "Iran"

    def test_is_blacklisted(self):
        """Test checking if address is blacklisted"""
        blacklist = AddressBlacklist()
        blacklist.add_blacklist("XAI_BAD", "Fraud")
        
        assert blacklist.is_blacklisted("XAI_BAD") is True
        assert blacklist.is_blacklisted("XAI_GOOD") is False

    def test_is_sanctioned(self):
        """Test checking if address is sanctioned"""
        blacklist = AddressBlacklist()
        blacklist.add_sanction("XAI_SANCTIONED", "Cuba")
        
        assert blacklist.is_sanctioned("XAI_SANCTIONED") is True
        assert blacklist.is_sanctioned("XAI_NORMAL") is False

    def test_get_blacklist(self):
        """Test getting full blacklist"""
        blacklist = AddressBlacklist()
        blacklist.add_blacklist("XAI_BAD1", "Fraud")
        blacklist.add_blacklist("XAI_BAD2", "Money laundering")
        
        full_list = blacklist.get_blacklist()
        assert len(full_list) == 2
        assert "XAI_BAD1" in full_list
        assert "XAI_BAD2" in full_list

    def test_get_sanctions_list(self):
        """Test getting full sanctions list"""
        blacklist = AddressBlacklist()
        blacklist.add_sanction("XAI_S1", "Iran")
        blacklist.add_sanction("XAI_S2", "North Korea")
        
        sanctions = blacklist.get_sanctions_list()
        assert len(sanctions) == 2
        assert "XAI_S1" in sanctions
        assert "XAI_S2" in sanctions


class MockBlockchain:
    """Mock blockchain for testing"""
    
    def __init__(self):
        self.chain = []
    
    def add_block(self, transactions):
        """Add a mock block with transactions"""
        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "transactions": transactions,
            "hash": f"block_{len(self.chain)}",
        }
        self.chain.append(block)


class TestRegulatorDashboard:
    """Test regulatory dashboard and reporting"""

    def test_init(self):
        """Test RegulatorDashboard initialization"""
        blockchain = MockBlockchain()
        dashboard = RegulatorDashboard(blockchain)
        
        assert dashboard.blockchain == blockchain
        assert isinstance(dashboard.risk_scorer, TransactionRiskScore)

    def test_get_flagged_transactions(self):
        """Test getting flagged transactions"""
        blockchain = MockBlockchain()
        
        # Add transactions with risk scores
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_A",
                "recipient": "XAI_B",
                "amount": 100,
                "amount_usd": 100,
                "timestamp": time.time(),
                "risk_score": 70,
                "risk_level": "high",
                "flag_reasons": ["large_amount"],
            },
            {
                "hash": "tx2",
                "sender": "XAI_C",
                "recipient": "XAI_D",
                "amount": 50,
                "amount_usd": 50,
                "timestamp": time.time(),
                "risk_score": 20,
                "risk_level": "clean",
                "flag_reasons": [],
            },
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        flagged = dashboard.get_flagged_transactions(min_score=61)
        
        assert len(flagged) == 1
        assert flagged[0]["transaction_hash"] == "tx1"
        assert flagged[0]["risk_score"] == 70

    def test_get_high_risk_addresses(self):
        """Test getting high-risk addresses"""
        blockchain = MockBlockchain()
        
        # Add transactions from same sender with high risk
        transactions = [
            {
                "hash": f"tx{i}",
                "sender": "XAI_RISKY",
                "recipient": f"XAI_{i}",
                "amount": 1000,
                "amount_usd": 1000,
                "timestamp": time.time(),
                "risk_score": 75,
                "risk_level": "high",
                "flag_reasons": ["large_amount"],
            }
            for i in range(3)
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        high_risk = dashboard.get_high_risk_addresses(min_score=70)
        
        assert len(high_risk) > 0
        assert high_risk[0]["address"] == "XAI_RISKY"
        assert high_risk[0]["flagged_transaction_count"] == 3

    def test_get_address_risk_profile(self):
        """Test getting risk profile for specific address"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_TEST",
                "recipient": "XAI_B",
                "amount": 100,
                "amount_usd": 100,
                "timestamp": time.time(),
                "risk_score": 65,
                "risk_level": "high",
                "flag_reasons": ["large_amount"],
            },
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        profile = dashboard.get_address_risk_profile("XAI_TEST")
        
        assert profile["address"] == "XAI_TEST"
        assert profile["risk_score"] == 65
        assert profile["risk_level"] == "high"

    def test_get_address_risk_profile_not_found(self):
        """Test getting risk profile for address not found"""
        blockchain = MockBlockchain()
        dashboard = RegulatorDashboard(blockchain)
        
        profile = dashboard.get_address_risk_profile("XAI_NOTFOUND")
        assert profile["risk_score"] == 0
        assert profile["risk_level"] == RiskLevel.CLEAN.value

    def test_export_compliance_report(self):
        """Test exporting compliance report"""
        blockchain = MockBlockchain()
        
        current_time = time.time()
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_A",
                "recipient": "XAI_B",
                "amount": 1000,
                "amount_usd": 1000,
                "timestamp": current_time,
                "risk_score": 70,
                "risk_level": "high",
                "flag_reasons": ["large_amount"],
            },
            {
                "hash": "tx2",
                "sender": "XAI_C",
                "recipient": "XAI_D",
                "amount": 50,
                "amount_usd": 50,
                "timestamp": current_time,
                "risk_score": 20,
                "risk_level": "clean",
                "flag_reasons": [],
            },
        ]
        
        block = {
            "index": 0,
            "timestamp": current_time,
            "transactions": transactions,
            "hash": "block_0",
        }
        blockchain.chain.append(block)
        
        dashboard = RegulatorDashboard(blockchain)
        report = dashboard.export_compliance_report(
            start_date=current_time - 3600,
            end_date=current_time + 3600
        )
        
        assert report["summary"]["total_transactions"] == 2
        assert report["summary"]["flagged_transactions"] == 1
        assert "report_generated" in report

    def test_search_transactions_by_address(self):
        """Test searching transactions by address"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_TARGET",
                "recipient": "XAI_B",
                "amount": 100,
                "amount_usd": 100,
                "timestamp": time.time(),
            },
            {
                "hash": "tx2",
                "sender": "XAI_C",
                "recipient": "XAI_TARGET",
                "amount": 50,
                "amount_usd": 50,
                "timestamp": time.time(),
            },
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        results = dashboard.search_transactions(address="XAI_TARGET")
        
        assert len(results) == 2

    def test_search_transactions_by_min_amount(self):
        """Test searching transactions by minimum amount"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_A",
                "recipient": "XAI_B",
                "amount": 1000,
                "amount_usd": 1000,
                "timestamp": time.time(),
            },
            {
                "hash": "tx2",
                "sender": "XAI_C",
                "recipient": "XAI_D",
                "amount": 50,
                "amount_usd": 50,
                "timestamp": time.time(),
            },
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        results = dashboard.search_transactions(min_amount=500)
        
        assert len(results) == 1
        assert results[0]["hash"] == "tx1"

    def test_search_transactions_by_risk_level(self):
        """Test searching transactions by risk level"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": "tx1",
                "sender": "XAI_A",
                "recipient": "XAI_B",
                "amount": 1000,
                "amount_usd": 1000,
                "timestamp": time.time(),
                "risk_level": "high",
            },
            {
                "hash": "tx2",
                "sender": "XAI_C",
                "recipient": "XAI_D",
                "amount": 50,
                "amount_usd": 50,
                "timestamp": time.time(),
                "risk_level": "clean",
            },
        ]
        blockchain.add_block(transactions)
        
        dashboard = RegulatorDashboard(blockchain)
        results = dashboard.search_transactions(risk_level=RiskLevel.HIGH)
        
        assert len(results) == 1
        assert results[0]["hash"] == "tx1"


class TestPublicExplorerAPI:
    """Test public blockchain explorer API"""

    def test_init(self):
        """Test PublicExplorerAPI initialization"""
        blockchain = MockBlockchain()
        api = PublicExplorerAPI(blockchain)
        
        assert api.blockchain == blockchain

    def test_get_transaction(self):
        """Test getting transaction without risk info"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": "tx_public",
                "sender": "XAI_A",
                "recipient": "XAI_B",
                "amount": 100,
                "timestamp": time.time(),
                "risk_score": 70,  # Should not be returned
                "risk_level": "high",
                "flag_reasons": ["test"],
            },
        ]
        blockchain.add_block(transactions)
        
        api = PublicExplorerAPI(blockchain)
        tx = api.get_transaction("tx_public")
        
        assert tx is not None
        assert tx["hash"] == "tx_public"
        assert tx["sender"] == "XAI_A"
        assert "risk_score" not in tx
        assert "risk_level" not in tx

    def test_get_transaction_not_found(self):
        """Test getting non-existent transaction"""
        blockchain = MockBlockchain()
        api = PublicExplorerAPI(blockchain)
        
        tx = api.get_transaction("nonexistent")
        assert tx is None

    def test_get_recent_transactions(self):
        """Test getting recent transactions without risk info"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": f"tx{i}",
                "sender": f"XAI_{i}",
                "recipient": f"XAI_{i+1}",
                "amount": 100,
                "timestamp": time.time(),
                "risk_score": 50,
            }
            for i in range(5)
        ]
        blockchain.add_block(transactions)
        
        api = PublicExplorerAPI(blockchain)
        recent = api.get_recent_transactions(limit=3)
        
        assert len(recent) == 3
        for tx in recent:
            assert "risk_score" not in tx
            assert "hash" in tx
            assert "sender" in tx

    def test_get_recent_transactions_respects_limit(self):
        """Test that recent transactions respects limit parameter"""
        blockchain = MockBlockchain()
        
        transactions = [
            {
                "hash": f"tx{i}",
                "sender": f"XAI_{i}",
                "recipient": f"XAI_{i+1}",
                "amount": 100,
                "timestamp": time.time(),
            }
            for i in range(150)
        ]
        blockchain.add_block(transactions)
        
        api = PublicExplorerAPI(blockchain)
        recent = api.get_recent_transactions(limit=50)
        
        assert len(recent) == 50
