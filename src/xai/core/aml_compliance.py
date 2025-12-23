from __future__ import annotations

"""
XAI AML Compliance System

Transaction monitoring, risk scoring, and regulatory reporting
Makes suspicious activity highly visible while separating normal transactions
"""

import hashlib
import time
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    """Risk level classifications"""

    CLEAN = "clean"  # 0-20
    LOW = "low"  # 21-40
    MEDIUM = "medium"  # 41-60
    HIGH = "high"  # 61-80
    CRITICAL = "critical"  # 81-100

class FlagReason(Enum):
    """Reasons for transaction flagging"""

    LARGE_AMOUNT = "large_amount"
    RAPID_SUCCESSION = "rapid_succession"
    STRUCTURING = "structuring"
    BLACKLISTED_ADDRESS = "blacklisted_address"
    SANCTIONED_COUNTRY = "sanctioned_country"
    MIXING_SERVICE = "mixing_service"
    NEW_ACCOUNT_LARGE_TX = "new_account_large_transaction"
    ROUND_AMOUNT = "round_amount_pattern"
    VELOCITY_SPIKE = "velocity_spike"

class TransactionRiskScore:
    """Calculate risk score for transactions"""

    # Thresholds
    LARGE_AMOUNT_USD = 10000
    RAPID_TX_WINDOW = 3600  # 1 hour
    RAPID_TX_COUNT = 10
    STRUCTURING_THRESHOLD = 9000  # Just under $10k
    NEW_ACCOUNT_DAYS = 7

    def __init__(self):
        self.transaction_history = {}  # address -> list of recent txs
        self.blacklisted_addresses = set()
        self.sanctioned_addresses = set()

    def calculate_risk_score(
        self, transaction: Dict, sender_history: list[Dict] = None
    ) -> tuple[int, list[str]]:
        """
        Calculate risk score (0-100) and flag reasons

        Returns:
            (risk_score, list_of_reasons)
        """

        score = 0
        reasons = []

        # Check 1: Large amount
        if transaction.get("amount_usd", 0) >= self.LARGE_AMOUNT_USD:
            score += 30
            reasons.append(FlagReason.LARGE_AMOUNT.value)

        # Check 2: Blacklisted address
        sender = transaction.get("sender")
        recipient = transaction.get("recipient")

        if sender in self.blacklisted_addresses or recipient in self.blacklisted_addresses:
            score += 50
            reasons.append(FlagReason.BLACKLISTED_ADDRESS.value)

        # Check 3: Sanctioned address
        if sender in self.sanctioned_addresses or recipient in self.sanctioned_addresses:
            score += 60
            reasons.append(FlagReason.SANCTIONED_COUNTRY.value)

        # Check 4: Structuring (multiple txs just under reporting threshold)
        if sender_history:
            recent = self._get_recent_transactions(sender_history, window=86400)
            if self._detect_structuring(recent, transaction):
                score += 40
                reasons.append(FlagReason.STRUCTURING.value)

        # Check 5: Rapid succession
        if sender_history:
            recent = self._get_recent_transactions(sender_history, window=self.RAPID_TX_WINDOW)
            if len(recent) >= self.RAPID_TX_COUNT:
                score += 25
                reasons.append(FlagReason.RAPID_SUCCESSION.value)

        # Check 6: New account with large transaction
        if sender_history and len(sender_history) < 5:
            account_age_days = (
                time.time() - sender_history[0].get("timestamp", time.time())
            ) / 86400
            if account_age_days < self.NEW_ACCOUNT_DAYS and transaction.get("amount_usd", 0) > 5000:
                score += 35
                reasons.append(FlagReason.NEW_ACCOUNT_LARGE_TX.value)

        # Check 7: Round amount pattern (common in money laundering)
        amount = transaction.get("amount", 0)
        if self._is_round_amount(amount):
            score += 10
            reasons.append(FlagReason.ROUND_AMOUNT.value)

        # Check 8: Velocity spike
        if sender_history:
            if self._detect_velocity_spike(sender_history, transaction):
                score += 30
                reasons.append(FlagReason.VELOCITY_SPIKE.value)

        # Cap at 100
        score = min(score, 100)

        return score, reasons

    def _get_recent_transactions(self, history: list[Dict], window: int) -> list[Dict]:
        """Get transactions within time window"""
        cutoff = time.time() - window
        return [tx for tx in history if tx.get("timestamp", 0) > cutoff]

    def _detect_structuring(self, recent_txs: list[Dict], current_tx: Dict) -> bool:
        """Detect structuring pattern (multiple txs just under threshold)"""
        # Multiple transactions just under $10k in 24 hours
        near_threshold = [
            tx for tx in recent_txs if 8000 <= tx.get("amount_usd", 0) <= self.STRUCTURING_THRESHOLD
        ]

        if len(near_threshold) >= 3:
            return True

        return False

    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is suspiciously round"""
        # Exactly 1000, 5000, 10000, 50000, 100000, etc.
        round_amounts = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
        return amount in round_amounts

    def _detect_velocity_spike(self, history: list[Dict], current_tx: Dict) -> bool:
        """Detect sudden spike in transaction velocity"""
        if len(history) < 10:
            return False

        # Average transaction frequency
        time_diffs = []
        for i in range(1, len(history)):
            diff = history[i]["timestamp"] - history[i - 1]["timestamp"]
            time_diffs.append(diff)

        if not time_diffs:
            return False

        avg_diff = sum(time_diffs) / len(time_diffs)

        # Current transaction is 10x faster than average
        last_diff = current_tx["timestamp"] - history[-1]["timestamp"]
        if last_diff < avg_diff / 10:
            return True

        return False

    def get_risk_level(self, score: int) -> RiskLevel:
        """Convert score to risk level"""
        if score <= 20:
            return RiskLevel.CLEAN
        elif score <= 40:
            return RiskLevel.LOW
        elif score <= 60:
            return RiskLevel.MEDIUM
        elif score <= 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def add_to_blacklist(self, address: str, reason: str = ""):
        """Add address to blacklist"""
        self.blacklisted_addresses.add(address)

    def add_to_sanctions_list(self, address: str, country: str = ""):
        """Add address to sanctions list"""
        self.sanctioned_addresses.add(address)

class AddressBlacklist:
    """Manage blacklisted and sanctioned addresses"""

    def __init__(self):
        self.blacklist = {}  # address -> reason
        self.sanctions = {}  # address -> country

    def add_blacklist(self, address: str, reason: str, added_by: str = "protocol"):
        """Add address to blacklist"""
        self.blacklist[address] = {"reason": reason, "added_by": added_by, "timestamp": time.time()}

    def add_sanction(self, address: str, country: str):
        """Add sanctioned address"""
        self.sanctions[address] = {"country": country, "timestamp": time.time()}

    def is_blacklisted(self, address: str) -> bool:
        """Check if address is blacklisted"""
        return address in self.blacklist

    def is_sanctioned(self, address: str) -> bool:
        """Check if address is sanctioned"""
        return address in self.sanctions

    def get_blacklist(self) -> Dict:
        """Get full blacklist"""
        return self.blacklist

    def get_sanctions_list(self) -> Dict:
        """Get full sanctions list"""
        return self.sanctions

class RegulatorDashboard:
    """
    API and reporting for regulatory agencies
    Makes compliance monitoring easy
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.risk_scorer = TransactionRiskScore()

    def get_flagged_transactions(self, min_score: int = 61, limit: int = 1000) -> list[Dict]:
        """Get all flagged transactions above risk threshold"""

        flagged = []

        # Scan blockchain for flagged transactions
        for block in self.blockchain.chain:
            for tx in block.get("transactions", []):
                score = tx.get("risk_score", 0)
                if score >= min_score:
                    flagged.append(
                        {
                            "transaction_hash": tx.get("hash"),
                            "block": block.get("index"),
                            "timestamp": tx.get("timestamp"),
                            "sender": tx.get("sender"),
                            "recipient": tx.get("recipient"),
                            "amount": tx.get("amount"),
                            "amount_usd": tx.get("amount_usd"),
                            "risk_score": score,
                            "risk_level": tx.get("risk_level"),
                            "flag_reasons": tx.get("flag_reasons", []),
                        }
                    )

        # Return most recent first
        flagged.sort(key=lambda x: x["timestamp"], reverse=True)
        return flagged[:limit]

    def get_high_risk_addresses(self, min_score: int = 70) -> list[Dict]:
        """Get addresses with consistently high risk scores"""

        address_scores = {}

        for block in self.blockchain.chain:
            for tx in block.get("transactions", []):
                score = tx.get("risk_score", 0)
                if score >= min_score:
                    sender = tx.get("sender")
                    if sender not in address_scores:
                        address_scores[sender] = []
                    address_scores[sender].append(score)

        # Calculate average score per address
        high_risk = []
        for address, scores in address_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score >= min_score:
                high_risk.append(
                    {
                        "address": address,
                        "average_risk_score": round(avg_score, 2),
                        "flagged_transaction_count": len(scores),
                        "max_risk_score": max(scores),
                    }
                )

        # Sort by average score
        high_risk.sort(key=lambda x: x["average_risk_score"], reverse=True)
        return high_risk

    def get_address_risk_profile(self, address: str) -> dict[str, Any]:
        """Return the latest risk snapshot for a specific address."""
        if not address:
            return {
                "address": "",
                "risk_score": 0,
                "risk_level": RiskLevel.CLEAN.value,
                "flag_reasons": [],
                "last_seen": None,
            }

        best = {
            "address": address,
            "risk_score": 0,
            "risk_level": RiskLevel.CLEAN.value,
            "flag_reasons": [],
            "last_seen": None,
        }

        for block in reversed(self.blockchain.chain):
            for tx in block.get("transactions", []):
                if tx.get("sender") != address and tx.get("recipient") != address:
                    continue
                score = tx.get("risk_score", 0)
                if score >= best["risk_score"]:
                    best.update(
                        {
                            "risk_score": score,
                            "risk_level": tx.get("risk_level", RiskLevel.CLEAN.value),
                            "flag_reasons": tx.get("flag_reasons", []),
                            "last_seen": tx.get("timestamp"),
                        }
                    )

        return best

    def export_compliance_report(self, start_date: int, end_date: int) -> Dict:
        """Export full compliance report for date range"""

        report = {
            "report_generated": time.time(),
            "period_start": start_date,
            "period_end": end_date,
            "summary": {},
            "flagged_transactions": [],
            "high_risk_addresses": [],
            "blacklisted_addresses": [],
        }

        total_txs = 0
        flagged_txs = 0
        total_volume = 0
        flagged_volume = 0

        for block in self.blockchain.chain:
            block_time = block.get("timestamp", 0)
            if start_date <= block_time <= end_date:
                for tx in block.get("transactions", []):
                    total_txs += 1
                    total_volume += tx.get("amount_usd", 0)

                    score = tx.get("risk_score", 0)
                    if score >= 61:
                        flagged_txs += 1
                        flagged_volume += tx.get("amount_usd", 0)
                        report["flagged_transactions"].append(tx)

        report["summary"] = {
            "total_transactions": total_txs,
            "flagged_transactions": flagged_txs,
            "flag_percentage": round(flagged_txs / total_txs * 100, 2) if total_txs > 0 else 0,
            "total_volume_usd": total_volume,
            "flagged_volume_usd": flagged_volume,
        }

        report["high_risk_addresses"] = self.get_high_risk_addresses()

        return report

    def search_transactions(
        self, address: str = None, min_amount: float = None, risk_level: RiskLevel = None
    ) -> list[Dict]:
        """Search transactions with filters"""

        results = []

        for block in self.blockchain.chain:
            for tx in block.get("transactions", []):
                match = True

                if address and tx.get("sender") != address and tx.get("recipient") != address:
                    match = False

                if min_amount and tx.get("amount_usd", 0) < min_amount:
                    match = False

                if risk_level and tx.get("risk_level") != risk_level.value:
                    match = False

                if match:
                    results.append(tx)

        return results

class PublicExplorerAPI:
    """
    Public-facing API for blockchain explorer
    NO public risk scores - community friendly
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def get_transaction(self, tx_hash: str) -> Dict:
        """Get transaction (no risk info shown publicly)"""

        for block in self.blockchain.chain:
            for tx in block.get("transactions", []):
                if tx.get("hash") == tx_hash:
                    # Return transaction without risk scores
                    return {
                        "hash": tx.get("hash"),
                        "sender": tx.get("sender"),
                        "recipient": tx.get("recipient"),
                        "amount": tx.get("amount"),
                        "timestamp": tx.get("timestamp"),
                        "block": block.get("index"),
                    }

        return None

    def get_recent_transactions(self, limit: int = 100) -> list[Dict]:
        """Get recent transactions (no filtering by risk)"""

        transactions = []

        for block in reversed(self.blockchain.chain):
            for tx in block.get("transactions", []):
                transactions.append(
                    {
                        "hash": tx.get("hash"),
                        "sender": tx.get("sender"),
                        "recipient": tx.get("recipient"),
                        "amount": tx.get("amount"),
                        "timestamp": tx.get("timestamp"),
                        "block": block.get("index"),
                    }
                )
                if len(transactions) >= limit:
                    return transactions

        return transactions

# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI AML COMPLIANCE SYSTEM")
    print("=" * 70)

    # Test risk scoring
    scorer = TransactionRiskScore()

    # Normal transaction
    normal_tx = {
        "sender": "XAI123",
        "recipient": "XAI456",
        "amount": 100,
        "amount_usd": 20,
        "timestamp": time.time(),
    }

    score, reasons = scorer.calculate_risk_score(normal_tx)
    print(f"\nNormal Transaction:")
    print(f"  Risk Score: {score}")
    print(f"  Risk Level: {scorer.get_risk_level(score).value}")
    print(f"  Reasons: {reasons}")

    # Large transaction
    large_tx = {
        "sender": "XAI789",
        "recipient": "XAI012",
        "amount": 50000,
        "amount_usd": 11500,
        "timestamp": time.time(),
    }

    score, reasons = scorer.calculate_risk_score(large_tx)
    print(f"\nLarge Transaction:")
    print(f"  Risk Score: {score}")
    print(f"  Risk Level: {scorer.get_risk_level(score).value}")
    print(f"  Reasons: {reasons}")

    # Structuring pattern
    history = [
        {"amount_usd": 9000, "timestamp": time.time() - 3600},
        {"amount_usd": 8900, "timestamp": time.time() - 1800},
        {"amount_usd": 9100, "timestamp": time.time() - 900},
    ]

    structuring_tx = {
        "sender": "XAI345",
        "recipient": "XAI678",
        "amount": 9000,
        "amount_usd": 8950,
        "timestamp": time.time(),
    }

    score, reasons = scorer.calculate_risk_score(structuring_tx, history)
    print(f"\nStructuring Pattern:")
    print(f"  Risk Score: {score}")
    print(f"  Risk Level: {scorer.get_risk_level(score).value}")
    print(f"  Reasons: {reasons}")

    print("\n" + "=" * 70)
