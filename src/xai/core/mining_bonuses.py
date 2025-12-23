from __future__ import annotations

"""
Mining Bonus and Reward Tracking System for AXN Blockchain
Manages early adopter bonuses, achievements, referrals, and social bonuses
"""

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

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

DEFAULT_EARLY_ADOPTER_TIERS: dict[int, float] = {
    100: 100,  # First 100 miners: 100 AXN
    1000: 50,  # First 1,000 miners: 50 AXN
    10000: 10,  # First 10,000 miners: 10 AXN
}

DEFAULT_ACHIEVEMENT_BONUSES: dict[str, float] = {
    "first_block": 5,
    "10_blocks": 25,
    "100_blocks": 250,
    "7day_streak": 100,
}

DEFAULT_REFERRAL_BONUSES: dict[str, float] = {
    "refer_friend": 10,  # Per referral
    "friend_10_blocks": 25,  # When referred friend mines 10 blocks
}

DEFAULT_SOCIAL_BONUSES: dict[str, float] = {
    "tweet_verification": 5,
    "discord_join": 2,
}

DEFAULT_PROGRESS_REWARDS: dict[str, float] = {
    "registration": 150.0,
}

XP_CONTEXT_MULTIPLIERS: dict[str, float] = {
    "early_adopter": 1.15,
    "achievement": 3.5,
    "referral": 2.5,
    "referral_milestone": 3.75,
    "social": 1.5,
    "default": 1.0,
}

@dataclass(frozen=True)
class AchievementDefinition:
    """Structured definition for a gamified achievement milestone."""

    id: str
    description: str
    category: str
    condition: dict[str, Any]
    bonus: float = 0.0
    xp: float = 0.0
    tags: tuple[str, ...] = field(default_factory=tuple)
    reward_badge: str | None = None

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "category": self.category,
            "condition": self.condition,
            "bonus": self.bonus,
            "xp": self.xp,
            "tags": list(self.tags),
            "reward_badge": self.reward_badge,
        }

PROGRESSION_ENGINE_DEFAULTS: dict[str, float] = {
    "base_xp_per_level": 150.0,
    "level_growth_rate": 1.18,
    "max_xp_per_level": 4000.0,
    "xp_per_token": 1.0,
    "min_event_xp": 8.0,
    "history_limit": 50,
}

REFERRAL_DAILY_LIMIT = 25
RECENT_REFERRAL_WINDOW_SECONDS = 120
RECENT_REFERRAL_BURST_LIMIT = 3

DAILY_CHALLENGE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "daily_blocks_5",
        "description": "Mine 5 blocks today",
        "condition": {"type": "blocks_mined", "threshold": 5},
        "bonus": 4.0,
        "xp": 45.0,
        "tags": ["daily", "mining"],
    },
    {
        "id": "daily_streak_guardian",
        "description": "Maintain a 3 day streak",
        "condition": {"type": "streak_days", "threshold": 3},
        "bonus": 0.0,
        "xp": 55.0,
        "tags": ["daily", "streak"],
    },
    {
        "id": "daily_socializer",
        "description": "Complete one social action",
        "condition": {"type": "social_actions", "threshold": 1},
        "bonus": 2.5,
        "xp": 35.0,
        "tags": ["daily", "social"],
    },
    {
        "id": "daily_referral_ping",
        "description": "Register one new referral today",
        "condition": {"type": "referral_count_daily", "threshold": 1},
        "bonus": 6.0,
        "xp": 60.0,
        "tags": ["daily", "referral"],
    },
]

TROPHY_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "triple_crown",
        "description": "Hold gold_pickaxe, eternal_flame, and alliance_seal badges",
        "required_badges": ["gold_pickaxe", "eternal_flame", "alliance_seal"],
        "bonus": 25.0,
        "xp": 350.0,
    },
    {
        "id": "social_vanguard",
        "description": "Earn social_star badge plus complete three daily social challenges",
        "required_badges": ["social_star"],
        "daily_requirement": {"id": "daily_socializer", "count": 3},
        "bonus": 0.0,
        "xp": 180.0,
    },
]

class MiningBonusManager:
    """Manages all mining bonuses, rewards, and referral system"""

    def __init__(
        self,
        data_dir: str = "mining_data",
        max_bonus_supply: float | None = None,
        time_provider: Callable[[], datetime] | None = None,
    ):
        """Initialize the mining bonus manager

        Args:
            data_dir: Directory to store mining bonus data files
        """
        self._time_provider = time_provider or datetime.utcnow
        self.data_dir = data_dir
        self.miners_file = os.path.join(data_dir, "miners.json")
        self.bonuses_file = os.path.join(data_dir, "bonuses.json")
        self.referrals_file = os.path.join(data_dir, "referrals.json")
        self.achievements_file = os.path.join(data_dir, "achievements.json")
        self.achievement_rules_file = os.path.join(data_dir, "achievements_config.json")
        self.config_file = os.path.join(data_dir, "bonus_config.json")
        self.progression_file = os.path.join(data_dir, "progression.json")
        self.badges_file = os.path.join(data_dir, "badges.json")
        self.daily_challenges_file = os.path.join(data_dir, "daily_challenges.json")
        self.referral_guardian_file = os.path.join(data_dir, "referral_guardian.json")

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
        self.progression_rewards = self._configure_progression_rewards(overrides.get("progression_rewards"))
        self.progression_config = dict(PROGRESSION_ENGINE_DEFAULTS)
        self._configure_progression_settings(overrides.get("progression_config"))

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
        self.progression = self._load_json(self.progression_file)
        self.achievement_definitions = self._load_achievement_definitions()
        self.badges = self._load_json(self.badges_file)
        self.daily_challenges_state = self._load_json(self.daily_challenges_file)
        self.referral_guardian = self._load_json(self.referral_guardian_file)
        if not isinstance(self.badges, dict):
            self.badges = {}
        if not isinstance(self.daily_challenges_state, dict):
            self.daily_challenges_state = {}
        if not isinstance(self.referral_guardian, dict):
            self.referral_guardian = {}
        self.referral_guardian.setdefault("identities", {})
        self.referral_guardian.setdefault("referrers", {})
        self._refresh_daily_challenges_if_needed()

    def _load_bonus_configuration(self) -> dict[str, Any]:
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

    def _configure_early_adopter_tiers(self, overrides: dict[str, Any] | None) -> dict[int, float]:
        """Build sanitized early adopter tier configuration."""
        tiers: dict[int, float] = dict(DEFAULT_EARLY_ADOPTER_TIERS)
        if not overrides:
            return tiers

        parsed: dict[int, float] = {}
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
        ordered: dict[int, float] = {}
        previous_cap = 0
        for tier_cap in sorted(tiers):
            if tier_cap <= previous_cap:
                raise ValueError("Early adopter tiers must be strictly increasing")
            ordered[tier_cap] = float(tiers[tier_cap])
            previous_cap = tier_cap
        return ordered

    def _configure_bonus_map(
        self,
        overrides: dict[str, Any] | None,
        defaults: dict[str, float],
        category: str,
    ) -> dict[str, float]:
        """Return sanitized bonus definitions for non-tier categories."""
        values = dict(defaults)
        if not overrides:
            return values
        for key, raw_value in overrides.items():
            bonus_amount = self._validate_positive_amount(raw_value, f"{category}:{key}")
            values[str(key)] = bonus_amount
        return values

    def _configure_progression_rewards(self, overrides: dict[str, Any] | None) -> dict[str, float]:
        """Sanitize optional XP rewards for non-bonus events (e.g., registration)."""
        rewards = dict(DEFAULT_PROGRESS_REWARDS)
        if not overrides:
            return rewards
        for key, raw_value in overrides.items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid progression reward for {key}: {raw_value}") from exc
            if value < 0:
                raise ValueError(f"Progression reward for {key} must be non-negative")
            rewards[str(key)] = value
        return rewards

    def _configure_progression_settings(self, overrides: dict[str, Any] | None) -> None:
        """Apply optional progression engine overrides."""
        if not overrides or not isinstance(overrides, dict):
            return
        float_keys = {"base_xp_per_level", "level_growth_rate", "max_xp_per_level", "xp_per_token", "min_event_xp"}
        int_like = {"history_limit"}
        for key, raw_value in overrides.items():
            if key in float_keys:
                try:
                    value = float(raw_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid progression config {key}: {raw_value}") from exc
                if value <= 0:
                    raise ValueError(f"Progression config {key} must be positive")
                self.progression_config[key] = value
            elif key in int_like:
                try:
                    int_value = int(raw_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid progression config {key}: {raw_value}") from exc
                self.progression_config[key] = max(10, int_value)

    def _load_achievement_definitions(self) -> dict[str, AchievementDefinition]:
        """Load structured achievement rules from disk or fall back to defaults."""
        payload: list[dict[str, Any]] = []
        if os.path.exists(self.achievement_rules_file):
            data = self._load_json(self.achievement_rules_file)
            if isinstance(data, dict):
                payload = data.get("definitions") or []
        if not payload:
            payload = self._default_achievement_payloads()

        definitions: dict[str, AchievementDefinition] = {}
        for entry in payload:
            try:
                definition = AchievementDefinition(
                    id=entry["id"],
                    description=entry.get("description", entry["id"]),
                    category=entry.get("category", "general"),
                    condition=entry.get("condition", {}),
                    bonus=float(entry.get("bonus", 0.0)),
                    xp=float(entry.get("xp", 0.0)),
                    tags=tuple(entry.get("tags", [])),
                    reward_badge=entry.get("reward_badge"),
                )
            except (KeyError, TypeError, ValueError):
                continue
            definitions[definition.id] = definition
        return definitions

    def _default_achievement_payloads(self) -> list[dict[str, Any]]:
        """Return built-in achievements when no overrides are provided."""
        return [
            {
                "id": "first_block",
                "description": "Mine your first block",
                "category": "mining",
                "bonus": self.achievement_bonuses.get("first_block", 5),
                "xp": 50,
                "condition": {"type": "blocks_mined", "threshold": 1},
                "tags": ["milestone", "early"],
                "reward_badge": "bronze_pickaxe",
            },
            {
                "id": "ten_blocks",
                "description": "Reach 10 mined blocks",
                "category": "mining",
                "bonus": self.achievement_bonuses.get("10_blocks", 25),
                "xp": 85,
                "condition": {"type": "blocks_mined", "threshold": 10},
                "tags": ["milestone"],
                "reward_badge": "silver_pickaxe",
            },
            {
                "id": "hundred_blocks",
                "description": "Reach 100 mined blocks",
                "category": "mining",
                "bonus": self.achievement_bonuses.get("100_blocks", 250),
                "xp": 220,
                "condition": {"type": "blocks_mined", "threshold": 100},
                "tags": ["milestone", "prestige"],
                "reward_badge": "gold_pickaxe",
            },
            {
                "id": "seven_day_streak",
                "description": "Maintain a 7-day mining streak",
                "category": "consistency",
                "bonus": self.achievement_bonuses.get("7day_streak", 100),
                "xp": 150,
                "condition": {"type": "streak_days", "threshold": 7},
                "tags": ["streak"],
                "reward_badge": "ember_chain",
            },
            {
                "id": "thirty_day_streak",
                "description": "Mine every day for 30 consecutive days",
                "category": "consistency",
                "bonus": 0.0,
                "xp": 400,
                "condition": {"type": "streak_days", "threshold": 30},
                "tags": ["streak", "rare"],
                "reward_badge": "eternal_flame",
            },
            {
                "id": "referral_champion",
                "description": "Successfully refer five new miners",
                "category": "community",
                "bonus": self.referral_bonuses.get("refer_friend", 10),
                "xp": 180,
                "condition": {"type": "referral_count", "threshold": 5},
                "tags": ["social"],
                "reward_badge": "alliance_seal",
            },
            {
                "id": "veteran_miner",
                "description": "Accumulate 2,500 XP from participation",
                "category": "progression",
                "bonus": 0.0,
                "xp": 250,
                "condition": {"type": "xp_total", "threshold": 2500},
                "tags": ["progression"],
                "reward_badge": "veteran_banner",
            },
            {
                "id": "community_supporter",
                "description": "Complete three social engagement bonuses",
                "category": "community",
                "bonus": 0.0,
                "xp": 120,
                "condition": {"type": "social_actions", "threshold": 3},
                "tags": ["social"],
                "reward_badge": "social_star",
            },
        ]

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
            logger.error(
                "IOError in _save_json",
                extra={
                    "error_type": "IOError",
                    "error": str(e),
                    "function": "_save_json"
                }
            )
            print(f"Error saving to {filepath}: {e}")

    def _now(self) -> datetime:
        """Return the current UTC timestamp supplied by the manager."""
        return self._time_provider()

    def _current_date_str(self) -> str:
        """Return ISO date string for deterministic daily scheduling."""
        return self._now().strftime("%Y-%m-%d")

    def _save_progression(self) -> None:
        """Persist progression state to disk."""
        self._save_json(self.progression_file, self.progression)

    def _save_badges(self) -> None:
        """Persist badge/trophy assignments."""
        self._save_json(self.badges_file, self.badges)

    def _save_daily_challenges(self) -> None:
        """Persist the current daily challenge rotation."""
        self._save_json(self.daily_challenges_file, self.daily_challenges_state)

    def _save_referral_guardian(self) -> None:
        """Persist the referral guardian/anti-sybil state."""
        self._save_json(self.referral_guardian_file, self.referral_guardian)

    def _get_badge_record(self, address: str) -> dict[str, Any]:
        """Return mutable badge/trophy record for an address."""
        record = self.badges.get(address)
        if record is None:
            record = {"badges": [], "trophies": [], "daily_challenge_counts": {}}
            self.badges[address] = record
        record.setdefault("badges", [])
        record.setdefault("trophies", [])
        record.setdefault("daily_challenge_counts", {})
        return record

    def _refresh_daily_challenges_if_needed(self) -> None:
        """Ensure the current rotation of daily challenges is generated."""
        today = self._current_date_str()
        state = self.daily_challenges_state
        rotation_date = state.get("rotation_date")
        if rotation_date == today and state.get("challenges"):
            state.setdefault("completions", {})
            return

        challenges = self._generate_daily_challenges(today)
        self.daily_challenges_state = {
            "rotation_date": today,
            "challenges": challenges,
            "completions": {},
        }
        self._save_daily_challenges()

    def _generate_daily_challenges(self, date_key: str) -> list[dict[str, Any]]:
        """Generate deterministic daily challenges based on the date."""
        if not DAILY_CHALLENGE_CATALOG:
            return []

        selected: list[dict[str, Any]] = []
        used_indices: set = set()
        target_count = min(3, len(DAILY_CHALLENGE_CATALOG))

        for salt in range(target_count * 3):
            digest = hashlib.sha256(f"{date_key}:{salt}".encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], byteorder="big") % len(DAILY_CHALLENGE_CATALOG)
            if idx in used_indices:
                continue
            used_indices.add(idx)
            selected.append(dict(DAILY_CHALLENGE_CATALOG[idx]))
            if len(selected) == target_count:
                break
        return selected

    def _get_daily_completion_book(self, address: str) -> dict[str, Any]:
        """Return completion tracking dictionary for address."""
        self.daily_challenges_state.setdefault("completions", {})
        state = self.daily_challenges_state["completions"]
        book = state.get(address)
        if book is None:
            book = {}
            state[address] = book
        return book

    def _award_badge(
        self,
        address: str,
        badge_name: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Assign a badge to an address if not already granted."""
        record = self._get_badge_record(address)
        badges = record["badges"]
        if any(badge.get("name") == badge_name for badge in badges):
            return

        entry = {
            "name": badge_name,
            "awarded_at": self._now().isoformat(),
            "source": source,
        }
        if metadata:
            entry["metadata"] = metadata
        badges.append(entry)
        self._save_badges()
        self._evaluate_trophies(address)

    def _evaluate_trophies(self, address: str) -> None:
        """Check trophy definitions and award trophies atomically."""
        record = self._get_badge_record(address)
        owned_badges = {badge["name"] for badge in record.get("badges", [])}
        trophies = record.get("trophies", [])
        owned_trophies = {trophy["id"] for trophy in trophies}

        for definition in TROPHY_DEFINITIONS:
            trophy_id = definition["id"]
            if trophy_id in owned_trophies:
                continue

            required_badges = set(definition.get("required_badges", []))
            if required_badges and not required_badges.issubset(owned_badges):
                continue

            daily_requirement = definition.get("daily_requirement")
            if daily_requirement:
                challenge_id = daily_requirement.get("id")
                count_required = daily_requirement.get("count", 0)
                challenge_counts = record["daily_challenge_counts"].get(challenge_id, {})
                if challenge_counts.get("total", 0) < count_required:
                    continue

            token_awarded = 0.0
            if definition.get("bonus", 0.0) > 0:
                success, error = self._attempt_award_bonus(
                    address,
                    "trophy",
                    float(definition["bonus"]),
                    f"Trophy unlocked: {trophy_id}",
                    context=f"trophy:{trophy_id}",
                )
                if not success:
                    logger.warning("Unable to award trophy bonus: %s", error)
                else:
                    token_awarded = float(definition["bonus"])

            xp_awarded = 0.0
            if definition.get("xp", 0.0) > 0:
                xp_result = self._award_xp(
                    address,
                    float(definition["xp"]),
                    reason=f"trophy:{trophy_id}",
                    context=f"trophy:{trophy_id}",
                )
                xp_awarded = xp_result.get("xp_awarded", definition["xp"])

            trophies.append(
                {
                    "id": trophy_id,
                    "awarded_at": self._now().isoformat(),
                    "description": definition["description"],
                    "bonus": token_awarded,
                    "xp": xp_awarded,
                }
            )
            self._save_badges()

    def _is_challenge_completed(
        self,
        challenge: dict[str, Any],
        metrics: dict[str, Any],
        daily_activity: dict[str, Any],
    ) -> bool:
        """Evaluate whether a challenge condition is met."""
        condition = challenge.get("condition", {})
        condition_type = condition.get("type")
        comparator = condition.get("comparison", ">=")
        threshold = condition.get("threshold", 0)

        if condition_type == "referral_count_daily":
            value = daily_activity.get("referrals_today", 0)
        else:
            value = metrics.get(condition_type, 0)
        return self._compare_metric(value, threshold, comparator)

    def _record_daily_challenge_completion(
        self,
        address: str,
        challenge_id: str,
        daily_book: dict[str, Any],
    ) -> bool:
        """Record completion for a challenge; return True if newly completed."""
        today = self._current_date_str()
        challenge_status = daily_book.setdefault(today, {})
        entry = challenge_status.setdefault(challenge_id, {"completed": False, "awarded": False})
        if entry["completed"]:
            return False
        entry["completed"] = True
        return True

    def _update_daily_challenge_counter(self, address: str, challenge_id: str) -> None:
        """Track how often an address completed a given challenge."""
        record = self._get_badge_record(address)
        counters = record.setdefault("daily_challenge_counts", {})
        entry = counters.setdefault(challenge_id, {"total": 0, "dates": []})
        entry["total"] += 1
        today = self._current_date_str()
        if today not in entry["dates"]:
            entry["dates"].append(today)
            entry["dates"] = entry["dates"][-30:]
        self._save_badges()

    def _extract_identity_hash(self, metadata: dict[str, Any] | None) -> str | None:
        """Return sanitized identity hash metadata used for anti-sybil checks."""
        if not metadata:
            return None
        identity_hash = metadata.get("identity_hash")
        if not identity_hash or not isinstance(identity_hash, str):
            return None
        sanitized = identity_hash.strip()
        if len(sanitized) < 32:
            return None
        return sanitized

    def _validate_referral_request(
        self,
        referrer_address: str,
        new_address: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Validate referral to mitigate Sybil attacks."""
        if referrer_address == new_address:
            return {
                "success": False,
                "error": "Self-referrals are not permitted",
                "referrer_address": referrer_address,
            }

        guardian = self.referral_guardian.setdefault("referrers", {})
        entry = guardian.setdefault(
            referrer_address,
            {"recent": [], "daily_counts": {}, "flagged": False},
        )
        today = self._current_date_str()
        daily_counts = entry.setdefault("daily_counts", {})
        if daily_counts.get(today, 0) >= REFERRAL_DAILY_LIMIT:
            return {
                "success": False,
                "error": "Daily referral limit reached",
                "limit": REFERRAL_DAILY_LIMIT,
            }

        now_ts = self._now().timestamp()
        recent = [timestamp for timestamp in entry["recent"] if now_ts - timestamp <= RECENT_REFERRAL_WINDOW_SECONDS]
        if len(recent) >= RECENT_REFERRAL_BURST_LIMIT:
            entry["flagged"] = True
            self._save_referral_guardian()
            return {
                "success": False,
                "error": "Referral burst detected. Try again later.",
                "cooldown_seconds": RECENT_REFERRAL_WINDOW_SECONDS,
            }
        entry["recent"] = recent

        identity_hash = self._extract_identity_hash(metadata)
        if identity_hash:
            identities = self.referral_guardian.setdefault("identities", {})
            existing = identities.get(identity_hash)
            if existing and existing != new_address:
                return {
                    "success": False,
                    "error": "Identity already registered with another address",
                    "address": existing,
                }

        return None

    def _record_referral_activity(
        self,
        referrer_address: str,
        metadata: dict[str, Any] | None,
        new_address: str,
    ) -> None:
        """Persist anti-sybil tracking metadata after a referral."""
        guardian = self.referral_guardian.setdefault("referrers", {})
        entry = guardian.setdefault(
            referrer_address,
            {"recent": [], "daily_counts": {}, "flagged": False},
        )
        today = self._current_date_str()
        entry["recent"].append(self._now().timestamp())
        entry["daily_counts"][today] = entry["daily_counts"].get(today, 0) + 1

        identity_hash = self._extract_identity_hash(metadata)
        if identity_hash:
            identities = self.referral_guardian.setdefault("identities", {})
            identities[identity_hash] = new_address

        self._save_referral_guardian()

    def _evaluate_daily_challenges(
        self,
        address: str,
        metrics: dict[str, Any],
        daily_activity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate active daily challenges for the user."""
        self._refresh_daily_challenges_if_needed()
        state = self.daily_challenges_state
        challenges = state.get("challenges", [])
        book = self._get_daily_completion_book(address)
        daily_activity = daily_activity or {}

        completions: list[dict[str, Any]] = []
        for challenge in challenges:
            challenge_id = challenge.get("id")
            if not challenge_id:
                continue
            already_done = book.get(self._current_date_str(), {}).get(challenge_id, {}).get("completed")
            if already_done:
                continue
            if not self._is_challenge_completed(challenge, metrics, daily_activity):
                continue

            if not self._record_daily_challenge_completion(address, challenge_id, book):
                continue

            awarded_tokens = 0.0
            if challenge.get("bonus", 0.0) > 0:
                success, error = self._attempt_award_bonus(
                    address,
                    "daily_challenge",
                    float(challenge["bonus"]),
                    f"Daily challenge completed: {challenge_id}",
                    context=f"daily_challenge:{challenge_id}",
                )
                if not success:
                    logger.warning("Failed awarding daily challenge bonus: %s", error)
                else:
                    awarded_tokens = float(challenge["bonus"])
            awarded_xp = 0.0
            if challenge.get("xp", 0.0) > 0:
                xp_result = self._award_xp(
                    address,
                    float(challenge["xp"]),
                    reason=f"daily_challenge:{challenge_id}",
                    context=f"daily_challenge:{challenge_id}",
                )
                awarded_xp = xp_result.get("xp_awarded", challenge["xp"])

            completion_entry = {
                "challenge_id": challenge_id,
                "awarded_tokens": awarded_tokens,
                "awarded_xp": awarded_xp,
                "completed_at": self._now().isoformat(),
            }
            completions.append(completion_entry)
            self._update_daily_challenge_counter(address, challenge_id)

        if completions:
            self._save_daily_challenges()
            self._evaluate_trophies(address)

        return {
            "rotation_date": state.get("rotation_date"),
            "completed_today": completions,
            "active_challenges": challenges,
        }

    def _get_progression_record(self, address: str) -> dict[str, Any]:
        """Ensure a progression record exists for the given address."""
        record = self.progression.get(address)
        if record is None:
            record = {
                "address": address,
                "total_xp": 0.0,
                "lifetime_xp": 0.0,
                "history": [],
                "last_reason": None,
                "last_updated": None,
            }
            self.progression[address] = record
        return record

    def _calculate_level_state(self, total_xp: float) -> dict[str, float]:
        """Derive level, xp progress, and next threshold based on total XP."""
        base = self.progression_config["base_xp_per_level"]
        growth = self.progression_config["level_growth_rate"]
        max_threshold = self.progression_config["max_xp_per_level"]
        remaining = max(0.0, float(total_xp))
        level = 1
        xp_threshold = base

        while remaining >= xp_threshold:
            remaining -= xp_threshold
            level += 1
            xp_threshold = min(max_threshold, xp_threshold * growth)

        progress_percent = 0.0 if xp_threshold <= 0 else round((remaining / xp_threshold) * 100, 2)
        return {
            "level": level,
            "xp_into_level": remaining,
            "xp_to_next_level": xp_threshold,
            "progress_percent": progress_percent,
        }

    def _xp_from_context(self, context: str, amount: float) -> float:
        """Map a bonus context and amount to an XP award."""
        prefix = context.split(":", 1)[0] if context else "default"
        multiplier = XP_CONTEXT_MULTIPLIERS.get(prefix, XP_CONTEXT_MULTIPLIERS["default"])
        xp = float(amount) * multiplier * self.progression_config["xp_per_token"]
        xp = max(self.progression_config["min_event_xp"], xp)
        return round(xp, 2)

    def _award_xp(
        self,
        address: str,
        xp_amount: float,
        reason: str,
        context: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Award XP to an address and track level progression."""
        xp = max(0.0, float(xp_amount))
        if xp == 0:
            return {"xp_awarded": 0.0, "level_up": False}

        record = self._get_progression_record(address)
        before = self._calculate_level_state(record.get("total_xp", 0.0))
        record["total_xp"] = record.get("total_xp", 0.0) + xp
        record["lifetime_xp"] = record.get("lifetime_xp", 0.0) + xp
        after = self._calculate_level_state(record["total_xp"])
        history = record.setdefault("history", [])

        event = {
            "timestamp": datetime.now().isoformat(),
            "xp": xp,
            "reason": reason,
            "context": context or reason,
            "level_after": after["level"],
        }
        if metadata:
            event["metadata"] = metadata
        history.append(event)
        limit = int(self.progression_config.get("history_limit", 50))
        excess = len(history) - limit
        if excess > 0:
            del history[:excess]

        record["last_reason"] = reason
        record["last_updated"] = event["timestamp"]
        self._save_progression()

        return {
            "xp_awarded": xp,
            "level_up": after["level"] > before["level"],
            "level": after["level"],
            "progress_percent": after["progress_percent"],
        }

    def _record_progression_event(self, address: str, context: str, amount: float, bonus_type: str) -> None:
        """Convert a token bonus event into XP progression."""
        xp_amount = self._xp_from_context(context, amount)
        metadata = {"bonus_amount": float(amount), "bonus_type": bonus_type, "context": context}
        self._award_xp(address, xp_amount, reason=context.split(":", 1)[0] if context else "bonus", context=context, metadata=metadata)

    def get_progression_summary(self, address: str) -> dict[str, Any]:
        """Return XP/level summary for a miner."""
        record = self._get_progression_record(address)
        state = self._calculate_level_state(record.get("total_xp", 0.0))
        history = list(record.get("history", []))
        recent_events = list(reversed(history[-5:]))
        return {
            "address": address,
            "level": state["level"],
            "total_xp": round(record.get("total_xp", 0.0), 2),
            "lifetime_xp": round(record.get("lifetime_xp", 0.0), 2),
            "xp_into_level": round(state["xp_into_level"], 2),
            "xp_to_next_level": round(state["xp_to_next_level"], 2),
            "progress_percent": state["progress_percent"],
            "last_updated": record.get("last_updated"),
            "last_reason": record.get("last_reason"),
            "recent_events": recent_events,
        }

    def get_badges_summary(self, address: str) -> dict[str, Any]:
        """Return badges and trophies for an address."""
        record = self._get_badge_record(address)
        return {
            "badges": list(record.get("badges", [])),
            "trophies": list(record.get("trophies", [])),
            "daily_challenge_counts": dict(record.get("daily_challenge_counts", {})),
        }

    def _build_progression_stats(self) -> dict[str, Any]:
        """Aggregate progression metrics for stats endpoint."""
        if not self.progression:
            return {
                "tracked_players": 0,
                "average_level": 1.0,
                "top_level": 1,
                "total_tracked_xp": 0.0,
            }

        totals = []
        levels = []
        for record in self.progression.values():
            total_xp = float(record.get("total_xp", 0.0))
            totals.append(total_xp)
            levels.append(self._calculate_level_state(total_xp)["level"])

        tracked = len(levels)
        avg_level = round(sum(levels) / tracked, 2) if tracked else 1.0
        return {
            "tracked_players": tracked,
            "average_level": avg_level,
            "top_level": max(levels),
            "total_tracked_xp": round(sum(totals), 2),
        }

    def _build_achievement_metrics(
        self,
        address: str,
        blocks_mined: int,
        streak_days: int,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Collect metrics required to evaluate available achievements."""
        record = self.progression.get(address) or {}
        referral_data = self.referrals.get(address, {})
        social_claims = self.bonuses.get(address, {}).get("claimed", [])
        guardian_entry = self.referral_guardian.get("referrers", {}).get(address, {})
        daily_counts = guardian_entry.get("daily_counts", {})
        today = self._current_date_str()
        metrics = {
            "blocks_mined": max(0, int(blocks_mined)),
            "streak_days": max(0, int(streak_days)),
            "referral_count": len(referral_data.get("referred_miners", [])),
            "referral_count_daily": int(daily_counts.get(today, 0)),
            "xp_total": float(record.get("total_xp", 0.0)),
            "social_actions": len(social_claims),
        }
        if overrides:
            metrics.update(overrides)
        return metrics

    def _achievement_condition_met(
        self, definition: AchievementDefinition, metrics: dict[str, Any]
    ) -> bool:
        """Check if a metric snapshot satisfies an achievement definition."""
        condition = definition.condition or {}
        condition_type = condition.get("type")
        threshold = condition.get("threshold", 0)
        comparator = condition.get("comparison", ">=")
        if condition_type == "blocks_mined":
            value = metrics.get("blocks_mined", 0)
        elif condition_type == "streak_days":
            value = metrics.get("streak_days", 0)
        elif condition_type == "referral_count":
            value = metrics.get("referral_count", 0)
        elif condition_type == "xp_total":
            value = metrics.get("xp_total", 0.0)
        elif condition_type == "social_actions":
            value = metrics.get("social_actions", 0)
        else:
            return False
        return self._compare_metric(value, threshold, comparator)

    @staticmethod
    def _compare_metric(value: Any, threshold: Any, comparator: str) -> bool:
        """Support a handful of comparison operators for achievement rules."""
        try:
            if comparator == ">=":
                return value >= threshold
            if comparator == ">":
                return value > threshold
            if comparator == "==":
                return value == threshold
            if comparator == "<=":
                return value <= threshold
            if comparator == "<":
                return value < threshold
        except TypeError:
            return False
        return False

    def get_achievement_catalog(self) -> list[dict[str, Any]]:
        """Expose the configured achievement catalog."""
        return [definition.serialize() for definition in self.achievement_definitions.values()]

    def get_daily_challenges_status(self, address: str) -> dict[str, Any]:
        """Return the user's view of current daily challenges."""
        self._refresh_daily_challenges_if_needed()
        state = self.daily_challenges_state
        book = self._get_daily_completion_book(address)
        today = self._current_date_str()
        today_status = book.get(today, {})

        challenges_view: list[dict[str, Any]] = []
        for challenge in state.get("challenges", []):
            challenge_id = challenge.get("id")
            entry = dict(challenge)
            completion = today_status.get(challenge_id)
            entry["completed"] = bool(completion and completion.get("completed"))
            entry["awarded"] = bool(completion and completion.get("awarded"))
            challenges_view.append(entry)

        return {
            "rotation_date": state.get("rotation_date"),
            "challenges": challenges_view,
        }

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
        registration_xp = self.progression_rewards.get("registration", 0.0)
        if registration_xp > 0:
            self._award_xp(
                address,
                registration_xp,
                reason="registration",
                metadata={"registration_number": registration_num},
            )

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

    def check_achievements(
        self,
        address: str,
        blocks_mined: int,
        streak_days: int,
        extra_metrics: dict[str, Any] | None = None,
    ) -> Dict:
        """Evaluate and award achievements for the given miner."""
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}

        record = self.achievements.setdefault(address, {"earned": [], "total_bonus": 0, "total_xp": 0.0})
        record.setdefault("total_xp", 0.0)
        record.setdefault("earned", [])
        record.setdefault("total_bonus", 0.0)

        metrics = self._build_achievement_metrics(address, blocks_mined, streak_days, extra_metrics)
        guardian_entry = self.referral_guardian.get("referrers", {}).get(address, {})
        daily_activity = {
            "referrals_today": guardian_entry.get("daily_counts", {}).get(self._current_date_str(), 0),
        }
        earned_types = {achievement.get("type") for achievement in record["earned"]}
        newly_earned: list[dict[str, Any]] = []
        total_new_bonus = 0.0
        total_new_xp = 0.0

        for definition in self.achievement_definitions.values():
            if definition.id in earned_types:
                continue
            if not self._achievement_condition_met(definition, metrics):
                continue

            bonus_awarded = 0.0
            if definition.bonus > 0:
                success, error = self._attempt_award_bonus(
                    address,
                    "achievement",
                    definition.bonus,
                    definition.description,
                    context=f"achievement:{definition.id}",
                )
                if not success:
                    return {
                        "success": False,
                        "error": error,
                        "new_achievements": newly_earned,
                        "total_new_bonus": total_new_bonus,
                        "total_new_xp": total_new_xp,
                    }
                bonus_awarded = definition.bonus

            xp_awarded = 0.0
            xp_response = None
            if definition.xp > 0:
                xp_response = self._award_xp(
                    address,
                    definition.xp,
                    reason=f"achievement:{definition.id}",
                    context=f"achievement:{definition.id}",
                    metadata={"achievement_category": definition.category},
                )
                xp_awarded = xp_response.get("xp_awarded", definition.xp)

            achievement_entry = {
                "type": definition.id,
                "description": definition.description,
                "category": definition.category,
                "bonus": bonus_awarded,
                "xp_awarded": xp_awarded,
                "earned_at": datetime.now().isoformat(),
                "tags": list(definition.tags),
                "condition": definition.condition,
            }
            if definition.reward_badge:
                achievement_entry["badge"] = definition.reward_badge
                self._award_badge(
                    address,
                    definition.reward_badge,
                    source=f"achievement:{definition.id}",
                    metadata={"category": definition.category},
                )
            if xp_response:
                achievement_entry["level_after"] = xp_response.get("level")

            newly_earned.append(achievement_entry)
            record["earned"].append(achievement_entry)
            record["total_bonus"] = record.get("total_bonus", 0.0) + bonus_awarded
            record["total_xp"] = record.get("total_xp", 0.0) + xp_awarded
            total_new_bonus += bonus_awarded
            total_new_xp += xp_awarded
            earned_types.add(definition.id)

        if newly_earned:
            self._save_json(self.achievements_file, self.achievements)

        daily_summary = self._evaluate_daily_challenges(address, metrics, daily_activity)

        return {
            "success": True,
            "address": address,
            "blocks_mined": blocks_mined,
            "streak_days": streak_days,
            "metrics": metrics,
            "new_achievements": newly_earned,
            "total_new_bonus": total_new_bonus,
            "total_new_xp": round(total_new_xp, 2),
            "all_achievements": record["earned"],
            "available_achievements": self.get_achievement_catalog(),
            "daily_challenges": daily_summary,
            "badges": self.get_badges_summary(address),
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

    def use_referral_code(self, new_address: str, referral_code: str, metadata: dict[str, Any] | None = None) -> Dict:
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

        if self.referrals.get(new_address, {}).get("referred_by"):
            return {
                "success": False,
                "error": "Address already tied to a referral",
                "new_address": new_address,
            }

        validation_error = self._validate_referral_request(referrer_address, new_address, metadata)
        if validation_error:
            return validation_error

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
        self._record_referral_activity(referrer_address, metadata, new_address)

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
        achievements_data = self.achievements.get(address, {"earned": [], "total_bonus": 0, "total_xp": 0.0})
        referrals_data = self.referrals.get(address, {})
        badges_summary = self.get_badges_summary(address)
        daily_status = self.get_daily_challenges_status(address)

        total_bonus = 0
        claimed_bonuses = bonuses_data.get("claimed", [])
        for bonus in claimed_bonuses:
            total_bonus += bonus.get("amount", 0)

        total_bonus += achievements_data.get("total_bonus", 0)
        total_bonus += referrals_data.get("total_referral_bonus", 0)

        progression_summary = self.get_progression_summary(address)

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
            "badges": badges_summary,
            "daily_challenges": daily_status,
            "summary": {
                "total_earned_bonus": total_bonus,
                "social_bonuses_earned": sum(b.get("amount", 0) for b in claimed_bonuses),
                "achievement_bonuses_earned": achievements_data.get("total_bonus", 0),
                "achievement_xp_earned": round(achievements_data.get("total_xp", 0.0), 2),
                "referral_bonuses_earned": referrals_data.get("total_referral_bonus", 0),
                "mining_rewards": miner_data.get("total_earnings", 0),
            },
            "progression": progression_summary,
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

    def get_leaderboard(self, limit: int = 10) -> list[Dict]:
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

    def get_unified_leaderboard(self, metric: str = "composite", limit: int = 10) -> list[dict[str, Any]]:
        """Return a leaderboard that blends XP, bonuses, and referrals."""
        metric = (metric or "composite").lower()
        leaderboard: list[dict[str, Any]] = []

        for address, miner in self.miners.items():
            progression = self.progression.get(address, {})
            xp_total = float(progression.get("total_xp", 0.0))
            total_bonus = float(self.bonuses.get(address, {}).get("total_awarded", 0.0))
            referral_count = len(self.referrals.get(address, {}).get("referred_miners", []))
            max_streak = int(miner.get("max_streak", miner.get("current_streak", 0)))

            composite = (
                xp_total * 1.0
                + total_bonus * 25.0
                + referral_count * 40.0
                + max_streak * 5.0
            )
            metric_value = composite
            if metric == "xp":
                metric_value = xp_total
            elif metric == "bonus":
                metric_value = total_bonus
            elif metric == "referrals":
                metric_value = referral_count
            elif metric == "streak":
                metric_value = max_streak

            leaderboard.append(
                {
                    "address": address,
                    "metric": metric,
                    "score": round(metric_value, 2),
                    "metrics": {
                        "xp_total": round(xp_total, 2),
                        "total_bonus": round(total_bonus, 2),
                        "referrals": referral_count,
                        "max_streak": max_streak,
                    },
                }
            )

        leaderboard.sort(key=lambda entry: entry["score"], reverse=True)
        return leaderboard[: max(1, limit)]

    def get_stats(self) -> Dict:
        """Get overall system statistics

        Returns:
            Dictionary with system statistics
        """
        total_miners = len(self.miners)
        total_bonuses_awarded = self._get_total_awarded()

        active_referrals = sum(1 for data in self.referrals.values() if data.get("referral_code"))
        progression_stats = self._build_progression_stats()
        badge_count = sum(len(record.get("badges", [])) for record in self.badges.values())
        trophy_count = sum(len(record.get("trophies", [])) for record in self.badges.values())
        daily_summary = {
            "rotation_date": self.daily_challenges_state.get("rotation_date"),
            "active_challenges": len(self.daily_challenges_state.get("challenges", [])),
        }

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
            "progression": progression_stats,
            "badges": {"awarded": badge_count, "trophies": trophy_count},
            "daily_challenges": daily_summary,
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
    ) -> tuple[bool, str | None]:
        try:
            self._award_bonus(address, bonus_type, amount, description)
            self._record_progression_event(address, context, amount, bonus_type)
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
