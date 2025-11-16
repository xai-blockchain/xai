"""
XAI Token Burning Engine

Implements utility token consumption and burning mechanics.
Services consume XAI, which is then distributed:
- 50% BURNED (deflationary)
- 30% to MINERS (security incentive)
- 20% to TREASURY (development fund)

ANONYMITY PROTECTION:
- No personal identifiers (no names, emails, IPs)
- UTC timestamps only (no timezone leakage)
- Wallet addresses only (already anonymous)
- No geographic data
- No device fingerprinting
- Statistics are aggregated and anonymous
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from enum import Enum


class ServiceType(Enum):
    """Types of services that consume XAI"""

    # AI Services
    AI_QUERY_SIMPLE = "ai_query_simple"
    AI_QUERY_COMPLEX = "ai_query_complex"
    AI_CODE_REVIEW = "ai_code_review"
    AI_SECURITY_AUDIT = "ai_security_audit"
    AI_CODE_GENERATION = "ai_code_generation"

    # Governance
    GOVERNANCE_VOTE = "governance_vote"
    GOVERNANCE_PROPOSAL = "governance_proposal"
    GOVERNANCE_SECURITY_REVIEW = "governance_security_review"

    # Trading
    TRADING_BOT_DAILY = "trading_bot_daily"
    TRADING_BOT_STRATEGY = "trading_bot_strategy"
    DEX_TRADING_FEE = "dex_trading_fee"

    # Special
    TIME_CAPSULE_FEE = "time_capsule_fee"
    TRANSACTION_FEE = "transaction_fee"


# Service pricing in USD (converted to XAI dynamically)
SERVICE_PRICES_USD = {
    # AI Services (affordable for all users)
    ServiceType.AI_QUERY_SIMPLE: 0.10,  # $0.10 per simple query
    ServiceType.AI_QUERY_COMPLEX: 0.50,  # $0.50 per complex analysis
    ServiceType.AI_CODE_REVIEW: 5.00,  # $5 per file review
    ServiceType.AI_SECURITY_AUDIT: 25.00,  # $25 per security audit
    ServiceType.AI_CODE_GENERATION: 10.00,  # $10 per code generation
    # Governance (stake to participate)
    ServiceType.GOVERNANCE_VOTE: 1.00,  # $1 per vote (prevents spam)
    ServiceType.GOVERNANCE_PROPOSAL: 100.00,  # $100 deposit (refunded if approved)
    ServiceType.GOVERNANCE_SECURITY_REVIEW: 50.00,  # $50 for AI security review
    # Trading (subscription model)
    ServiceType.TRADING_BOT_DAILY: 10.00,  # $10/day subscription
    ServiceType.TRADING_BOT_STRATEGY: 50.00,  # $50 per custom strategy
    ServiceType.DEX_TRADING_FEE: 0.003,  # 0.3% of trade value
    # Special
    ServiceType.TIME_CAPSULE_FEE: 10.00,  # $10 protocol fee
    ServiceType.TRANSACTION_FEE: 0.24,  # 0.24% of transaction
}


class BurnTransaction:
    """
    Anonymous burn transaction record

    Contains ONLY:
    - Wallet address (already anonymous)
    - Service type
    - Amount burned
    - UTC timestamp

    NO personal data, NO identifying information!
    """

    def __init__(
        self,
        wallet_address: str,
        service_type: ServiceType,
        xai_amount: float,
        burn_amount: float,
        miner_amount: float,
        treasury_amount: float,
    ):

        self.wallet_address = wallet_address  # Anonymous address only
        self.service_type = service_type.value
        self.xai_amount = xai_amount
        self.burn_amount = burn_amount
        self.miner_amount = miner_amount
        self.treasury_amount = treasury_amount
        self.timestamp_utc = datetime.now(timezone.utc).timestamp()  # UTC only!
        self.burn_id = self._generate_burn_id()

    def _generate_burn_id(self) -> str:
        """Generate anonymous burn transaction ID"""
        import hashlib

        data = f"{self.wallet_address}{self.service_type}{self.timestamp_utc}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        """Convert to anonymous dictionary (UTC timestamp only!)"""
        return {
            "burn_id": self.burn_id,
            "wallet_address": self.wallet_address,  # Anonymous only
            "service_type": self.service_type,
            "xai_amount": self.xai_amount,
            "burn_amount": self.burn_amount,
            "miner_amount": self.miner_amount,
            "treasury_amount": self.treasury_amount,
            "timestamp_utc": self.timestamp_utc,
            "date_utc": datetime.fromtimestamp(self.timestamp_utc, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
        }


class TokenBurningEngine:
    """
    XAI Token Burning Engine

    Handles service payments and token burning with complete anonymity.

    ANONYMITY GUARANTEES:
    - No personal identifiers stored
    - UTC timestamps only
    - Wallet addresses only (anonymous)
    - No IP addresses
    - No geographic data
    - No session tracking
    - Anonymous statistics only
    """

    def __init__(self, blockchain=None, data_dir=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.blockchain = blockchain
        self.data_dir = data_dir

        # Anonymous burn records
        self.burn_history_file = os.path.join(data_dir, "burn_history.json")
        self.burn_stats_file = os.path.join(data_dir, "burn_statistics.json")

        # Distribution percentages (NO TREASURY - dev funded by pre-mine + AI donations!)
        self.burn_percentage = 0.50  # 50% burned (deflationary)
        self.miner_percentage = 0.50  # 50% to miners (security incentive)

        # NOTE: Development is funded by:
        # 1. Genesis pre-mine: 10M XAI dev fund + 6M marketing + 400K liquidity
        # 2. AI Development Pool: Donated API minutes from miners
        # NO need for additional treasury allocation from burns!

        # Oracle price (USD per XAI)
        # In production, this would come from DEX or oracle
        self.xai_price_usd = 1.0  # Default $1/XAI

        self._load_burn_history()
        self._load_burn_stats()

    def _load_burn_history(self):
        """Load anonymous burn history"""
        if os.path.exists(self.burn_history_file):
            with open(self.burn_history_file, "r") as f:
                self.burn_history = json.load(f)
        else:
            self.burn_history = []

    def _save_burn_history(self):
        """Save anonymous burn history (UTC timestamps only)"""
        with open(self.burn_history_file, "w") as f:
            json.dump(self.burn_history, f, indent=2)

    def _load_burn_stats(self):
        """Load anonymous burn statistics"""
        if os.path.exists(self.burn_stats_file):
            with open(self.burn_stats_file, "r") as f:
                self.burn_stats = json.load(f)
        else:
            self.burn_stats = {
                "total_burned": 0.0,
                "total_to_miners": 0.0,
                "total_services_used": 0,
                "service_usage": {},
                "last_updated_utc": datetime.now(timezone.utc).timestamp(),
                "note": "Development funded by 10M XAI pre-mine + donated AI API minutes",
            }

    def _save_burn_stats(self):
        """Save anonymous burn statistics (UTC only)"""
        self.burn_stats["last_updated_utc"] = datetime.now(timezone.utc).timestamp()
        with open(self.burn_stats_file, "w") as f:
            json.dump(self.burn_stats, f, indent=2)

    def update_xai_price(self, price_usd: float):
        """
        Update XAI price from oracle/DEX

        Anonymous price update - no tracking of who/when
        """
        self.xai_price_usd = price_usd

    def calculate_service_cost(self, service_type: ServiceType) -> float:
        """
        Calculate service cost in XAI (USD-pegged, dynamic)

        This keeps services affordable regardless of XAI price!

        Example:
            Service costs $0.10
            XAI = $1.00 → Cost = 0.1 XAI
            XAI = $10.00 → Cost = 0.01 XAI
            XAI = $100.00 → Cost = 0.001 XAI
        """
        usd_price = SERVICE_PRICES_USD.get(service_type, 0.0)
        xai_cost = usd_price / self.xai_price_usd
        return xai_cost

    def consume_service(
        self, wallet_address: str, service_type: ServiceType, custom_amount: Optional[float] = None
    ) -> dict:
        """
        Consume XAI for service usage

        Process:
        1. Calculate cost (USD-pegged)
        2. Verify wallet has sufficient XAI
        3. Distribute: 50% burn, 30% miners, 20% treasury
        4. Create anonymous burn record (UTC only)
        5. Update anonymous statistics

        Args:
            wallet_address: Anonymous wallet address (no personal data!)
            service_type: Type of service being consumed
            custom_amount: Optional custom XAI amount (for variable services)

        Returns:
            dict with burn details (anonymous, UTC timestamps only)
        """

        # Calculate cost
        if custom_amount:
            xai_amount = custom_amount
        else:
            xai_amount = self.calculate_service_cost(service_type)

        # Verify wallet has sufficient balance
        if self.blockchain:
            balance = self.blockchain.get_balance(wallet_address)
            if balance < xai_amount:
                return {
                    "success": False,
                    "error": f"Insufficient balance. Required: {xai_amount} XAI, Available: {balance} XAI",
                }

        # Calculate distribution (50/50 split - NO treasury!)
        burn_amount = xai_amount * self.burn_percentage
        miner_amount = xai_amount * self.miner_percentage

        # Create anonymous burn transaction
        burn_tx = BurnTransaction(
            wallet_address=wallet_address,
            service_type=service_type,
            xai_amount=xai_amount,
            burn_amount=burn_amount,
            miner_amount=miner_amount,
            treasury_amount=0.0,  # No treasury - dev funded separately!
        )

        # Execute burn (if blockchain available)
        if self.blockchain:
            # This would create actual blockchain transactions
            # For now, track it in burn history
            pass

        # Record anonymous burn (UTC timestamp only!)
        self.burn_history.append(burn_tx.to_dict())
        self._save_burn_history()

        # Update anonymous statistics (NO treasury stats!)
        self.burn_stats["total_burned"] += burn_amount
        self.burn_stats["total_to_miners"] += miner_amount
        self.burn_stats["total_services_used"] += 1

        # Track service usage (anonymous aggregation)
        service_key = service_type.value
        if service_key not in self.burn_stats["service_usage"]:
            self.burn_stats["service_usage"][service_key] = {"count": 0, "total_burned": 0.0}

        self.burn_stats["service_usage"][service_key]["count"] += 1
        self.burn_stats["service_usage"][service_key]["total_burned"] += burn_amount

        self._save_burn_stats()

        return {
            "success": True,
            "burn_id": burn_tx.burn_id,
            "service_type": service_type.value,
            "total_cost_xai": xai_amount,
            "burned_xai": burn_amount,
            "to_miners_xai": miner_amount,
            "timestamp_utc": burn_tx.timestamp_utc,
            "message": f"Service consumed. {burn_amount} XAI burned (deflationary), {miner_amount} XAI to miners (security).",
        }

    def get_anonymous_stats(self) -> dict:
        """
        Get anonymous burn statistics

        Returns aggregated data ONLY - no personal information!
        All timestamps in UTC!
        """

        circulating_supply = 121000000.0  # Will be dynamic from blockchain
        if self.blockchain:
            circulating_supply = self.blockchain.get_total_circulating_supply()

        total_burned = self.burn_stats["total_burned"]
        burn_percentage = (total_burned / circulating_supply) * 100 if circulating_supply > 0 else 0

        return {
            "total_burned": total_burned,
            "total_to_miners": self.burn_stats["total_to_miners"],
            "total_services_used": self.burn_stats["total_services_used"],
            "circulating_supply": circulating_supply,
            "burn_percentage_of_supply": burn_percentage,
            "service_usage": self.burn_stats["service_usage"],
            "distribution": "50% burn (deflationary) + 50% miners (security)",
            "development_funding": "Pre-mine (10M XAI) + AI API donations (encrypted keys)",
            "last_updated_utc": self.burn_stats["last_updated_utc"],
            "last_updated_date_utc": datetime.fromtimestamp(
                self.burn_stats["last_updated_utc"], tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

    def get_recent_burns(self, limit: int = 100) -> List[dict]:
        """
        Get recent anonymous burn transactions

        Returns ONLY:
        - Wallet addresses (anonymous)
        - Service types
        - Amounts
        - UTC timestamps

        NO personal data!
        """
        return self.burn_history[-limit:]

    def get_burn_by_service(self, service_type: ServiceType) -> dict:
        """Get anonymous burn statistics for specific service"""
        service_key = service_type.value

        if service_key in self.burn_stats["service_usage"]:
            return self.burn_stats["service_usage"][service_key]
        else:
            return {"count": 0, "total_burned": 0.0}
