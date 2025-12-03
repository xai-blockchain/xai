"""
Mining Bonus and Reward Tracking System for AXN Blockchain
Manages early adopter bonuses, achievements, referrals, and social bonuses
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from xai.core.blockchain_security import BlockchainSecurityConfig
from xai.core.config import Config

logger = logging.getLogger(__name__)


class BonusSupplyExceededError(RuntimeError):
    """Raised when awarding a bonus would exceed the configured supply cap."""

    def __init__(self, requested: float, remaining: float, cap: float):
        super().__init__(
            f"Cannot award {requested} tokens. Remaining bonus pool {remaining}, cap {cap}"
        )
        self.requested = requested
        self.remaining = remaining
        self.cap = cap


DEFAULT_EARLY_ADOPTER_TIERS: Dict[int, float] = {
    100: 100,  # First 100 miners: 100 AXN
    1000: 50,  # First 1,000 miners: 50 AXN
    10000: 10,  # First 10,000 miners: 10 AXN
}

DEFAULT_ACHIEVEMENT_BONUSES: Dict[str, float] = {
    "first_block": 5,
    "10_blocks": 25,
    "100_blocks": 250,
    "7day_streak": 100,
}

DEFAULT_REFERRAL_BONUSES: Dict[str, float] = {
    "refer_friend": 10,  # Per referral
    "friend_10_blocks": 25,  # When referred friend mines 10 blocks
}

DEFAULT_SOCIAL_BONUSES: Dict[str, float] = {
    "tweet_verification": 5,
    "discord_join": 2,
}


class MiningBonusManager:
    """Manages all mining bonuses, rewards, and referral system"""

    def __init__(self, data_dir: str = "mining_data", max_bonus_supply: Optional[float] = None):
        """Initialize the mining bonus manager

        Args:
            data_dir: Directory to store mining bonus data files
        """
        self.data_dir = data_dir
        self.miners_file = os.path.join(data_dir, "miners.json")
        self.bonuses_file = os.path.join(data_dir, "bonuses.json")
        self.referrals_file = os.path.join(data_dir, "referrals.json")
        self.achievements_file = os.path.join(data_dir, "achievements.json")
        self.config_file = os.path.join(data_dir, "bonus_config.json")

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        absolute_cap = float(getattr(Config, "MAX_SUPPLY", BlockchainSecurityConfig.MAX_SUPPLY))
        if max_bonus_supply is None:
            resolved_cap = absolute_cap
        else:
            resolved_cap = float(max_bonus_supply)
        if resolved_cap <= 0:
            raise ValueError("max_bonus_supply must be positive.")
        self.max_bonus_supply = min(resolved_cap, absolute_cap)
        threshold_env = os.getenv("XAI_MINING_BONUS_ALERT_THRESHOLD", "0.9")
        try:
            threshold_value = float(threshold_env)
        except ValueError:
            threshold_value = 0.9
        self.bonus_alert_threshold = min(max(threshold_value, 0.0), 1.0)
        self._bonus_alert_emitted = False

        # Bonus configuration (can be overridden via mining_data/bonus_config.json)
        overrides = self._load_bonus_configuration()
        self.early_adopter_tiers = self._configure_early_adopter_tiers(overrides.get("early_adopter_tiers"))
        self.achievement_bonuses = self._configure_bonus_map(
            overrides.get("achievement_bonuses"),
            DEFAULT_ACHIEVEMENT_BONUSES,
            "achievement",
        )
        self.referral_bonuses = self._configure_bonus_map(
            overrides.get("referral_bonuses"),
            DEFAULT_REFERRAL_BONUSES,
            "referral",
        )
        self.social_bonuses = self._configure_bonus_map(
            overrides.get("social_bonuses"),
            DEFAULT_SOCIAL_BONUSES,
            "social",
        )

        self._reserved_bonus_budget = self._calculate_reserved_bonus_budget()
        if self._reserved_bonus_budget > self.max_bonus_supply:
            raise ValueError(
                f"Configured mining bonuses ({self._reserved_bonus_budget}) exceed bonus cap {self.max_bonus_supply}"
            )

        # Load existing data
        self.miners = self._load_json(self.miners_file)
        self.bonuses = self._load_json(self.bonuses_file)
        self.referrals = self._load_json(self.referrals_file)
        self.achievements = self._load_json(self.achievements_file)

    def _load_bonus_configuration(self) -> Dict[str, Any]:
        """Load optional bonus configuration overrides from disk."""
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                if not isinstance(data, dict):
                    raise ValueError("Configuration root must be a JSON object")
                return data
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning(
                "Ignoring invalid mining bonus configuration at %s: %s",
                self.config_file,
                exc,
            )
            return {}

    def _configure_early_adopter_tiers(self, overrides: Optional[Dict[str, Any]]) -> Dict[int, float]:
        """Build sanitized early adopter tier configuration."""
        tiers: Dict[int, float] = dict(DEFAULT_EARLY_ADOPTER_TIERS)
        if not overrides:
            return tiers

        parsed: Dict[int, float] = {}
        for raw_key, raw_value in overrides.items():
            try:
                tier_cap = int(raw_key)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid early adopter tier '{raw_key}': must be an integer") from exc
            if tier_cap <= 0:
                raise ValueError(f"Invalid early adopter tier '{tier_cap}': must be positive")

            bonus_amount = self._validate_positive_amount(raw_value, f"tier_{tier_cap}")
            parsed[tier_cap] = bonus_amount

        # Merge overrides and ensure ordering
        tiers.update(parsed)
        ordered: Dict[int, float] = {}
        previous_cap = 0
        for tier_cap in sorted(tiers):
            if tier_cap <= previous_cap:
                raise ValueError("Early adopter tiers must be strictly increasing")
            ordered[tier_cap] = float(tiers[tier_cap])
            previous_cap = tier_cap
        return ordered

    def _configure_bonus_map(
        self,
        overrides: Optional[Dict[str, Any]],
        defaults: Dict[str, float],
        category: str,
    ) -> Dict[str, float]:
        """Return sanitized bonus definitions for non-tier categories."""
        values = dict(defaults)
        if not overrides:
            return values
        for key, raw_value in overrides.items():
            bonus_amount = self._validate_positive_amount(raw_value, f"{category}:{key}")
            values[str(key)] = bonus_amount
        return values

    def _validate_positive_amount(self, raw_value: Any, context: str) -> float:
        """Ensure configured bonus amounts are valid floats within the supply cap."""
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid bonus value for {context}: {raw_value}") from exc
        if value <= 0:
            raise ValueError(f"Bonus value for {context} must be positive (got {value})")
        if value > self.max_bonus_supply:
            raise ValueError(
                f"Bonus value for {context} ({value}) exceeds available bonus cap {self.max_bonus_supply}"
            )
        return value

    def _load_json(self, filepath: str) -> dict:
        """Load JSON data from file"""
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_json(self, filepath: str, data: dict) -> None:
        """Save data to JSON file"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving to {filepath}: {e}")

    def register_miner(self, address: str) -> Dict:
        """Register a new miner and check for early adopter bonus

        Args:
            address: Miner wallet address

        Returns:
            Dictionary with registration status and any early adopter bonus
        """
        if address in self.miners:
            return {"success": False, "message": "Miner already registered", "address": address}

        # Register the miner
        miner_count = len(self.miners)
        self.miners[address] = {
            "registered_at": datetime.now().isoformat(),
            "registration_number": miner_count + 1,
            "blocks_mined": 0,
            "total_earnings": 0,
            "last_block_timestamp": None,
            "streak_start": None,
            "current_streak": 0,
            "max_streak": 0,
        }
        self._save_json(self.miners_file, self.miners)

        # Check for early adopter bonus
        registration_num = miner_count + 1
        early_adopter_bonus = 0
        bonus_tier = None

        for tier, bonus in sorted(self.early_adopter_tiers.items()):
            if registration_num <= tier:
                early_adopter_bonus = bonus
                bonus_tier = tier
                break

        result = {
            "success": True,
            "message": "Miner registered successfully",
            "address": address,
            "registration_number": registration_num,
            "early_adopter_bonus": early_adopter_bonus,
        }

        if early_adopter_bonus > 0:
            result["bonus_tier"] = f"First {bonus_tier} miners"
            awarded, error = self._attempt_award_bonus(
                address,
                "early_adopter",
                early_adopter_bonus,
                f"Early adopter bonus - tier {bonus_tier}",
                context="early_adopter",
            )
            if not awarded:
                result["early_adopter_bonus"] = 0
                result["bonus_error"] = error

        return result

    def check_achievements(self, address: str, blocks_mined: int, streak_days: int) -> Dict:
        """Check and award achievements based on mining stats

        Args:
            address: Miner address
            blocks_mined: Total blocks mined by this miner
            streak_days: Current mining streak in days

        Returns:
            Dictionary with newly earned achievements and bonuses
        """
        if address not in self.miners:
            return {"error": "Miner not registered"}

        if address not in self.achievements:
            self.achievements[address] = {"earned": [], "total_bonus": 0}

        earned_achievements = []
        total_new_bonus = 0

        # Check block count achievements
        if blocks_mined >= 1 and "first_block" not in [
            a["type"] for a in self.achievements[address]["earned"]
        ]:
            bonus = self.achievement_bonuses["first_block"]
            success, error = self._attempt_award_bonus(
                address,
                "achievement",
                bonus,
                "First block mined",
                context="achievement:first_block",
            )
            if not success:
                return {
                    "success": False,
                    "error": error,
                    "new_achievements": earned_achievements,
                    "total_new_bonus": total_new_bonus,
                }
            earned_achievements.append(
                {
                    "type": "first_block",
                    "description": "First block mined",
                    "bonus": bonus,
                    "earned_at": datetime.now().isoformat(),
                }
            )
            total_new_bonus += bonus

        if blocks_mined >= 10 and "ten_blocks" not in [
            a["type"] for a in self.achievements[address]["earned"]
        ]:
            bonus = self.achievement_bonuses["10_blocks"]
            success, error = self._attempt_award_bonus(
                address,
                "achievement",
                bonus,
                "10 blocks mined",
                context="achievement:ten_blocks",
            )
            if not success:
                return {
                    "success": False,
                    "error": error,
                    "new_achievements": earned_achievements,
                    "total_new_bonus": total_new_bonus,
                }
            earned_achievements.append(
                {
                    "type": "ten_blocks",
                    "description": "10 blocks mined",
                    "bonus": bonus,
                    "earned_at": datetime.now().isoformat(),
                }
            )
            total_new_bonus += bonus

        if blocks_mined >= 100 and "hundred_blocks" not in [
            a["type"] for a in self.achievements[address]["earned"]
        ]:
            bonus = self.achievement_bonuses["100_blocks"]
            success, error = self._attempt_award_bonus(
                address,
                "achievement",
                bonus,
                "100 blocks mined",
                context="achievement:hundred_blocks",
            )
            if not success:
                return {
                    "success": False,
                    "error": error,
                    "new_achievements": earned_achievements,
                    "total_new_bonus": total_new_bonus,
                }
            earned_achievements.append(
                {
                    "type": "hundred_blocks",
                    "description": "100 blocks mined",
                    "bonus": bonus,
                    "earned_at": datetime.now().isoformat(),
                }
            )
            total_new_bonus += bonus

        # Check streak achievements
        if streak_days >= 7 and "seven_day_streak" not in [
            a["type"] for a in self.achievements[address]["earned"]
        ]:
            bonus = self.achievement_bonuses["7day_streak"]
            success, error = self._attempt_award_bonus(
                address,
                "achievement",
                bonus,
                "7-day mining streak",
                context="achievement:seven_day_streak",
            )
            if not success:
                return {
                    "success": False,
                    "error": error,
                    "new_achievements": earned_achievements,
                    "total_new_bonus": total_new_bonus,
                }
            earned_achievements.append(
                {
                    "type": "seven_day_streak",
                    "description": "7-day mining streak",
                    "bonus": bonus,
                    "earned_at": datetime.now().isoformat(),
                }
            )
            total_new_bonus += bonus

        # Update achievements file
        for achievement in earned_achievements:
            self.achievements[address]["earned"].append(achievement)
            self.achievements[address]["total_bonus"] += achievement["bonus"]

        self._save_json(self.achievements_file, self.achievements)

        return {
            "success": True,
            "address": address,
            "blocks_mined": blocks_mined,
            "streak_days": streak_days,
            "new_achievements": earned_achievements,
            "total_new_bonus": total_new_bonus,
            "all_achievements": self.achievements[address]["earned"],
        }

    def claim_bonus(self, address: str, bonus_type: str) -> Dict:
        """Claim a bonus (verification step)

        Args:
            address: Miner address
            bonus_type: Type of bonus to claim (tweet_verification, discord_join, etc.)

        Returns:
            Dictionary with claim status and amount
        """
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}

        if address not in self.bonuses:
            self.bonuses[address] = {"total_awarded": 0, "bonuses": [], "claimed": []}
        elif "claimed" not in self.bonuses[address]:
            # Handle legacy data that doesn't have "claimed" key
            self.bonuses[address]["claimed"] = []

        # Check if already claimed
        claimed_bonuses = [b["type"] for b in self.bonuses[address]["claimed"]]
        if bonus_type in claimed_bonuses:
            return {
                "success": False,
                "error": f"Bonus {bonus_type} already claimed",
                "address": address,
            }

        # Validate bonus type and award
        if bonus_type == "tweet_verification":
            bonus_amount = self.social_bonuses["tweet_verification"]
            description = "Tweet verification bonus"
        elif bonus_type == "discord_join":
            bonus_amount = self.social_bonuses["discord_join"]
            description = "Discord join bonus"
        else:
            return {
                "success": False,
                "error": f"Unknown bonus type: {bonus_type}",
                "address": address,
            }

        # Award the bonus
        success, error = self._attempt_award_bonus(
            address,
            bonus_type,
            bonus_amount,
            description,
            context=f"social:{bonus_type}",
        )
        if not success:
            return {
                "success": False,
                "error": error,
                "address": address,
                "bonus_type": bonus_type,
            }

        # Record claim
        self.bonuses[address]["claimed"].append(
            {
                "type": bonus_type,
                "amount": bonus_amount,
                "claimed_at": datetime.now().isoformat(),
                "description": description,
            }
        )
        self._save_json(self.bonuses_file, self.bonuses)

        return {
            "success": True,
            "address": address,
            "bonus_type": bonus_type,
            "amount": bonus_amount,
            "message": f"{description} claimed successfully",
            "claimed_at": datetime.now().isoformat(),
        }

    def create_referral_code(self, address: str) -> Dict:
        """Create a unique referral code for a miner

        Args:
            address: Miner wallet address

        Returns:
            Dictionary with referral code
        """
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}

        if address not in self.referrals:
            self.referrals[address] = {
                "referral_code": str(uuid.uuid4())[:8].upper(),
                "referred_miners": [],
                "total_referral_bonus": 0,
                "created_at": datetime.now().isoformat(),
            }
        else:
            # Check if code already exists
            if "referral_code" in self.referrals[address]:
                return {
                    "success": True,
                    "address": address,
                    "referral_code": self.referrals[address]["referral_code"],
                    "message": "Referral code already exists",
                }

        self._save_json(self.referrals_file, self.referrals)

        return {
            "success": True,
            "address": address,
            "referral_code": self.referrals[address]["referral_code"],
            "message": "Referral code created successfully",
            "bonus_per_referral": self.referral_bonuses["refer_friend"],
            "bonus_when_friend_mines_10": self.referral_bonuses["friend_10_blocks"],
        }

    def use_referral_code(self, new_address: str, referral_code: str) -> Dict:
        """Use a referral code when registering

        Args:
            new_address: New miner's wallet address
            referral_code: Referral code from existing miner

        Returns:
            Dictionary with referral status and bonuses awarded
        """
        # Find the referrer
        referrer_address = None
        for addr, ref_data in self.referrals.items():
            if ref_data.get("referral_code") == referral_code:
                referrer_address = addr
                break

        if not referrer_address:
            return {"success": False, "error": "Invalid referral code", "new_address": new_address}

        # Register new miner if not already registered
        if new_address not in self.miners:
            self.register_miner(new_address)

        # Award referral bonus to referrer
        referral_bonus = self.referral_bonuses["refer_friend"]
        success, error = self._attempt_award_bonus(
            referrer_address,
            "referral",
            referral_bonus,
            f"Referred new miner: {new_address}",
            context="referral:new_miner",
        )
        if not success:
            return {
                "success": False,
                "error": error,
                "message": "Referral bonus pool exhausted",
                "referrer_address": referrer_address,
            }

        # Record the referral
        self.referrals[referrer_address]["referred_miners"].append(
            {
                "address": new_address,
                "referred_at": datetime.now().isoformat(),
                "blocks_mined": 0,
                "milestone_bonus_claimed": False,
            }
        )
        self.referrals[referrer_address]["total_referral_bonus"] += referral_bonus

        # Set referrer link for new miner
        if new_address not in self.referrals:
            self.referrals[new_address] = {"referred_by": referrer_address}
        else:
            self.referrals[new_address]["referred_by"] = referrer_address

        self._save_json(self.referrals_file, self.referrals)

        return {
            "success": True,
            "new_address": new_address,
            "referrer_address": referrer_address,
            "referrer_bonus": referral_bonus,
            "message": f"Successfully registered with referral code",
        }

    def check_referral_milestone(
        self, referrer_address: str, referred_address: str, blocks_mined: int
    ) -> Dict:
        """Check if a referred friend has reached 10 blocks milestone

        Args:
            referrer_address: Address of the referrer
            referred_address: Address of the referred miner
            blocks_mined: Number of blocks mined by referred friend

        Returns:
            Dictionary with milestone bonus if earned
        """
        if referrer_address not in self.referrals:
            return {"success": False, "error": "Referrer not found"}

        referred_list = self.referrals[referrer_address].get("referred_miners", [])
        referred_record = None

        for ref in referred_list:
            if ref["address"] == referred_address:
                referred_record = ref
                break

        if not referred_record:
            return {"success": False, "error": "Referred miner not found in records"}

        if blocks_mined >= 10 and not referred_record.get("milestone_bonus_claimed", False):
            milestone_bonus = self.referral_bonuses["friend_10_blocks"]
            success, error = self._attempt_award_bonus(
                referrer_address,
                "referral_milestone",
                milestone_bonus,
                f"Friend {referred_address} mined 10 blocks",
                context="referral:milestone",
            )
            if not success:
                return {
                    "success": False,
                    "error": error,
                    "referrer_address": referrer_address,
                    "referred_address": referred_address,
                }

            referred_record["milestone_bonus_claimed"] = True
            referred_record["blocks_mined"] = blocks_mined
            self.referrals[referrer_address]["total_referral_bonus"] += milestone_bonus

            self._save_json(self.referrals_file, self.referrals)

            return {
                "success": True,
                "referrer_bonus": milestone_bonus,
                "message": f"Milestone bonus awarded for friend reaching 10 blocks",
                "total_bonus": self.referrals[referrer_address]["total_referral_bonus"],
            }

        return {"success": False, "message": "Milestone not yet reached or already claimed"}

    def get_user_bonuses(self, address: str) -> Dict:
        """Get all bonuses for a miner

        Args:
            address: Miner wallet address

        Returns:
            Dictionary with all bonuses and rewards
        """
        if address not in self.miners:
            return {"error": "Miner not registered"}

        miner_data = self.miners[address]
        bonuses_data = self.bonuses.get(address, {"claimed": []})
        achievements_data = self.achievements.get(address, {"earned": [], "total_bonus": 0})
        referrals_data = self.referrals.get(address, {})

        total_bonus = 0
        claimed_bonuses = bonuses_data.get("claimed", [])
        for bonus in claimed_bonuses:
            total_bonus += bonus.get("amount", 0)

        total_bonus += achievements_data.get("total_bonus", 0)
        total_bonus += referrals_data.get("total_referral_bonus", 0)

        return {
            "success": True,
            "address": address,
            "miner_stats": {
                "registered_at": miner_data["registered_at"],
                "registration_number": miner_data["registration_number"],
                "blocks_mined": miner_data["blocks_mined"],
                "current_streak": miner_data["current_streak"],
                "max_streak": miner_data["max_streak"],
            },
            "social_bonuses": claimed_bonuses,
            "achievements": achievements_data["earned"],
            "referral_info": {
                "referral_code": referrals_data.get("referral_code"),
                "referred_by": referrals_data.get("referred_by"),
                "referred_miners": referrals_data.get("referred_miners", []),
                "total_referral_bonus": referrals_data.get("total_referral_bonus", 0),
            },
            "summary": {
                "total_earned_bonus": total_bonus,
                "social_bonuses_earned": sum(b.get("amount", 0) for b in claimed_bonuses),
                "achievement_bonuses_earned": achievements_data.get("total_bonus", 0),
                "referral_bonuses_earned": referrals_data.get("total_referral_bonus", 0),
                "mining_rewards": miner_data.get("total_earnings", 0),
            },
        }

    def _award_bonus(self, address: str, bonus_type: str, amount: float, description: str) -> None:
        """Internal method to award a bonus

        Args:
            address: Miner address
            bonus_type: Type of bonus
            amount: Bonus amount in AXN
            description: Description of the bonus
        """
        if amount <= 0:
            raise ValueError("Bonus amount must be positive.")

        remaining = self._get_bonus_supply_remaining()
        if amount > remaining + 1e-9:
            raise BonusSupplyExceededError(amount, remaining, self.max_bonus_supply)

        if address not in self.bonuses:
            self.bonuses[address] = {"total_awarded": 0, "bonuses": [], "claimed": []}

        self.bonuses[address]["bonuses"].append(
            {
                "type": bonus_type,
                "amount": amount,
                "description": description,
                "awarded_at": datetime.now().isoformat(),
            }
        )

        if "total_awarded" not in self.bonuses[address]:
            self.bonuses[address]["total_awarded"] = 0

        self.bonuses[address]["total_awarded"] += amount

        total_awarded = self._get_total_awarded()
        usage_ratio = total_awarded / self.max_bonus_supply if self.max_bonus_supply else 1.0
        if (
            not self._bonus_alert_emitted
            and self.bonus_alert_threshold > 0
            and usage_ratio >= self.bonus_alert_threshold
        ):
            logger.warning(
                "Mining bonus pool usage at %.2f%% of cap",
                usage_ratio * 100,
                extra={
                    "event": "mining_bonus.cap_threshold",
                    "total_awarded": total_awarded,
                    "cap": self.max_bonus_supply,
                },
            )
            self._bonus_alert_emitted = True

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get bonus leaderboard

        Args:
            limit: Number of top miners to return

        Returns:
            List of top miners by total bonus earned
        """
        leaderboard_data = []

        for address, bonus_data in self.bonuses.items():
            total = bonus_data.get("total_awarded", 0)
            leaderboard_data.append(
                {
                    "address": address,
                    "total_bonus": total,
                    "bonus_count": len(bonus_data.get("bonuses", [])),
                }
            )

        # Sort by total bonus
        leaderboard_data.sort(key=lambda x: x["total_bonus"], reverse=True)

        return leaderboard_data[:limit]

    def get_stats(self) -> Dict:
        """Get overall system statistics

        Returns:
            Dictionary with system statistics
        """
        total_miners = len(self.miners)
        total_bonuses_awarded = self._get_total_awarded()

        active_referrals = sum(1 for data in self.referrals.values() if data.get("referral_code"))

        return {
            "total_registered_miners": total_miners,
            "total_bonuses_awarded": total_bonuses_awarded,
            "active_referral_codes": active_referrals,
            "early_adopter_tiers": self.early_adopter_tiers,
            "achievement_bonuses": self.achievement_bonuses,
            "referral_bonuses": self.referral_bonuses,
            "social_bonuses": self.social_bonuses,
            "bonus_cap": self.max_bonus_supply,
            "bonus_remaining": self._get_bonus_supply_remaining(),
        }

    def get_total_awarded_amount(self) -> float:
        """Return the total bonus amount ever awarded."""
        return self._get_total_awarded()

    def get_bonus_supply_remaining(self) -> float:
        """Return remaining capacity for new bonuses."""
        return self._get_bonus_supply_remaining()

    def _get_bonus_supply_remaining(self) -> float:
        remaining = self.max_bonus_supply - self._get_total_awarded()
        return remaining if remaining > 0 else 0.0

    def _calculate_reserved_bonus_budget(self) -> float:
        """Compute the maximum configured payout for static bonus categories."""
        total = 0.0

        # Early adopter tiers are bounded by tier thresholds
        prev_cap = 0
        for tier_cap in sorted(self.early_adopter_tiers):
            tier_bonus = float(self.early_adopter_tiers[tier_cap])
            eligible = max(0, tier_cap - prev_cap)
            total += eligible * tier_bonus
            prev_cap = tier_cap

        # Achievement, referral, and social bonuses are single-shot per type
        total += sum(float(v) for v in self.achievement_bonuses.values())
        total += sum(float(v) for v in self.referral_bonuses.values())
        total += sum(float(v) for v in self.social_bonuses.values())
        return total

    def _attempt_award_bonus(
        self,
        address: str,
        bonus_type: str,
        amount: float,
        description: str,
        context: str,
    ) -> Tuple[bool, Optional[str]]:
        try:
            self._award_bonus(address, bonus_type, amount, description)
            return True, None
        except BonusSupplyExceededError as exc:
            logger.warning(
                "Bonus award skipped: %s",
                str(exc),
                extra={
                    "event": "mining_bonus.cap_exceeded",
                    "context": context,
                    "address": address,
                    "bonus_type": bonus_type,
                },
            )
            return False, str(exc)

    def _get_total_awarded(self) -> float:
        total = 0.0
        for data in self.bonuses.values():
            awarded = data.get("total_awarded", 0)
            if isinstance(awarded, (int, float)):
                total += float(awarded)
        return total

    def update_miner_stats(
        self, address: str, blocks_mined: int, streak_days: int, mining_reward: float
    ) -> None:
        """Update miner statistics

        Args:
            address: Miner address
            blocks_mined: Total blocks mined
            streak_days: Current streak in days
            mining_reward: Rewards earned from mining
        """
        if address in self.miners:
            self.miners[address]["blocks_mined"] = blocks_mined
            self.miners[address]["current_streak"] = streak_days
            self.miners[address]["total_earnings"] = mining_reward
            self.miners[address]["last_block_timestamp"] = datetime.now().isoformat()

            if streak_days > self.miners[address].get("max_streak", 0):
                self.miners[address]["max_streak"] = streak_days

            self._save_json(self.miners_file, self.miners)


if __name__ == "__main__":
    # Example usage
    manager = MiningBonusManager()

    # Register miners
    print("Registering miners...")
    result1 = manager.register_miner("AXN123abc")
    print(result1)

    result2 = manager.register_miner("AXN456def")
    print(result2)

    # Create referral code
    print("\nCreating referral code...")
    ref_result = manager.create_referral_code("AXN123abc")
    print(ref_result)

    # Use referral code
    print("\nUsing referral code...")
    use_ref_result = manager.use_referral_code("AXN789ghi", ref_result["referral_code"])
    print(use_ref_result)

    # Check achievements
    print("\nChecking achievements...")
    achievement_result = manager.check_achievements("AXN123abc", 100, 7)
    print(achievement_result)

    # Claim social bonus
    print("\nClaiming social bonus...")
    claim_result = manager.claim_bonus("AXN456def", "tweet_verification")
    print(claim_result)

    # Get user bonuses
    print("\nUser bonuses summary...")
    bonuses = manager.get_user_bonuses("AXN123abc")
    print(json.dumps(bonuses, indent=2))

    # Get leaderboard
    print("\nLeaderboard...")
    leaderboard = manager.get_leaderboard()
    print(json.dumps(leaderboard, indent=2))

    # Get stats
    print("\nSystem stats...")
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2))
