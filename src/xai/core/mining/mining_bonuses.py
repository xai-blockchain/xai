from __future__ import annotations

"""
Mining Bonus and Reward Tracking System for AXN Blockchain
Manages early adopter bonuses, achievements, referrals, and social bonuses.
Configuration is loaded from JSON for easier maintenance.
"""

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from xai.core.security.blockchain_security import BlockchainSecurityConfig
from xai.core.config import Config

logger = logging.getLogger(__name__)

# Path to static config file
_CONFIG_PATH = Path(__file__).parents[2] / "config" / "achievements.json"


class BonusSupplyExceededError(RuntimeError):
    """Raised when awarding a bonus would exceed the configured supply cap."""

    def __init__(self, requested: float, remaining: float, cap: float):
        super().__init__(
            f"Cannot award {requested} tokens. Remaining bonus pool {remaining}, cap {cap}"
        )
        self.requested = requested
        self.remaining = remaining
        self.cap = cap


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AchievementDefinition":
        return cls(
            id=data["id"],
            description=data.get("description", data["id"]),
            category=data.get("category", "general"),
            condition=data.get("condition", {}),
            bonus=float(data.get("bonus", 0.0)),
            xp=float(data.get("xp", 0.0)),
            tags=tuple(data.get("tags", [])),
            reward_badge=data.get("reward_badge"),
        )


def _load_static_config() -> dict[str, Any]:
    """Load the static achievements.json config file."""
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load achievements config: %s", e)
    return {}


class MiningBonusManager:
    """Manages all mining bonuses, rewards, and referral system."""

    def __init__(
        self,
        data_dir: str = "mining_data",
        max_bonus_supply: float | None = None,
        time_provider: Callable[[], datetime] | None = None,
    ):
        self._time_provider = time_provider or datetime.utcnow
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        # File paths for persistent state
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

        # Load static config
        static_config = _load_static_config()

        # Configure supply cap
        absolute_cap = float(getattr(Config, "MAX_SUPPLY", BlockchainSecurityConfig.MAX_SUPPLY))
        resolved_cap = float(max_bonus_supply) if max_bonus_supply is not None else absolute_cap
        if resolved_cap <= 0:
            raise ValueError("max_bonus_supply must be positive.")
        self.max_bonus_supply = min(resolved_cap, absolute_cap)

        # Alert threshold
        threshold_env = os.getenv("XAI_MINING_BONUS_ALERT_THRESHOLD", "0.9")
        try:
            threshold_value = float(threshold_env)
        except ValueError:
            threshold_value = 0.9
        self.bonus_alert_threshold = min(max(threshold_value, 0.0), 1.0)
        self._bonus_alert_emitted = False

        # Load runtime overrides (from data_dir)
        overrides = self._load_bonus_configuration()

        # Initialize bonus configurations from static config + overrides
        self.early_adopter_tiers = self._configure_early_adopter_tiers(
            overrides.get("early_adopter_tiers") or static_config.get("early_adopter_tiers")
        )
        self.achievement_bonuses = self._configure_bonus_map(
            overrides.get("achievement_bonuses"),
            static_config.get("achievement_bonuses", {}),
            "achievement",
        )
        self.referral_bonuses = self._configure_bonus_map(
            overrides.get("referral_bonuses"),
            static_config.get("referral_bonuses", {}),
            "referral",
        )
        self.social_bonuses = self._configure_bonus_map(
            overrides.get("social_bonuses"),
            static_config.get("social_bonuses", {}),
            "social",
        )
        self.progression_rewards = self._configure_progression_rewards(
            overrides.get("progression_rewards") or static_config.get("progression_rewards")
        )

        # XP multipliers from config
        self._xp_context_multipliers = static_config.get("xp_context_multipliers", {
            "early_adopter": 1.15, "achievement": 3.5, "referral": 2.5,
            "referral_milestone": 3.75, "social": 1.5, "default": 1.0
        })

        # Progression engine settings
        self.progression_config = dict(static_config.get("progression_engine", {
            "base_xp_per_level": 150.0, "level_growth_rate": 1.18,
            "max_xp_per_level": 4000.0, "xp_per_token": 1.0,
            "min_event_xp": 8.0, "history_limit": 50
        }))
        self._configure_progression_settings(overrides.get("progression_config"))

        # Referral limits
        ref_limits = static_config.get("referral_limits", {})
        self._referral_daily_limit = ref_limits.get("daily_limit", 25)
        self._referral_window_seconds = ref_limits.get("recent_window_seconds", 120)
        self._referral_burst_limit = ref_limits.get("burst_limit", 3)

        # Daily challenge catalog from config
        self._daily_challenge_catalog = static_config.get("daily_challenges", [])

        # Trophy definitions from config
        self._trophy_definitions = static_config.get("trophies", [])

        # Validate budget
        self._reserved_bonus_budget = self._calculate_reserved_bonus_budget()
        if self._reserved_bonus_budget > self.max_bonus_supply:
            raise ValueError(
                f"Configured mining bonuses ({self._reserved_bonus_budget}) exceed bonus cap {self.max_bonus_supply}"
            )

        # Load persistent state
        self.miners = self._load_json(self.miners_file)
        self.bonuses = self._load_json(self.bonuses_file)
        self.referrals = self._load_json(self.referrals_file)
        self.achievements = self._load_json(self.achievements_file)
        self.progression = self._load_json(self.progression_file)
        self.achievement_definitions = self._load_achievement_definitions(static_config)
        self.badges = self._load_json(self.badges_file) or {}
        self.daily_challenges_state = self._load_json(self.daily_challenges_file) or {}
        self.referral_guardian = self._load_json(self.referral_guardian_file) or {}
        self.referral_guardian.setdefault("identities", {})
        self.referral_guardian.setdefault("referrers", {})
        self._refresh_daily_challenges_if_needed()

    # ----- Configuration Loading -----

    def _load_bonus_configuration(self) -> dict[str, Any]:
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Ignoring invalid bonus config at %s: %s", self.config_file, e)
            return {}

    def _configure_early_adopter_tiers(self, overrides: dict[str, Any] | None) -> dict[int, float]:
        defaults = {"100": 100, "1000": 50, "10000": 10}
        source = overrides if overrides else defaults
        parsed: dict[int, float] = {}
        for key, val in source.items():
            tier_cap = int(key)
            if tier_cap <= 0:
                raise ValueError(f"Invalid tier '{tier_cap}': must be positive")
            parsed[tier_cap] = self._validate_positive_amount(val, f"tier_{tier_cap}")
        return dict(sorted(parsed.items()))

    def _configure_bonus_map(
        self, overrides: dict[str, Any] | None, defaults: dict[str, float], category: str
    ) -> dict[str, float]:
        values = dict(defaults)
        if overrides:
            for key, val in overrides.items():
                values[str(key)] = self._validate_positive_amount(val, f"{category}:{key}")
        return values

    def _configure_progression_rewards(self, overrides: dict[str, Any] | None) -> dict[str, float]:
        defaults = {"registration": 150.0}
        rewards = dict(overrides) if overrides else dict(defaults)
        for key, val in rewards.items():
            v = float(val)
            if v < 0:
                raise ValueError(f"Progression reward {key} must be non-negative")
            rewards[key] = v
        return rewards

    def _configure_progression_settings(self, overrides: dict[str, Any] | None) -> None:
        if not overrides:
            return
        float_keys = {"base_xp_per_level", "level_growth_rate", "max_xp_per_level", "xp_per_token", "min_event_xp"}
        for key, val in overrides.items():
            if key in float_keys:
                v = float(val)
                if v <= 0:
                    raise ValueError(f"Progression config {key} must be positive")
                self.progression_config[key] = v
            elif key == "history_limit":
                self.progression_config[key] = max(10, int(val))

    def _load_achievement_definitions(self, static_config: dict[str, Any]) -> dict[str, AchievementDefinition]:
        # Try runtime config first
        if os.path.exists(self.achievement_rules_file):
            data = self._load_json(self.achievement_rules_file)
            if isinstance(data, dict) and data.get("definitions"):
                return self._parse_achievement_list(data["definitions"])

        # Fall back to static config
        achievements_list = static_config.get("achievements", [])
        if achievements_list:
            return self._parse_achievement_list(achievements_list)

        # Return empty if nothing available
        return {}

    def _parse_achievement_list(self, entries: list[dict[str, Any]]) -> dict[str, AchievementDefinition]:
        definitions = {}
        for entry in entries:
            try:
                # Apply bonus override if available
                if entry["id"] in self.achievement_bonuses:
                    entry = dict(entry)
                    entry["bonus"] = self.achievement_bonuses[entry["id"]]
                defn = AchievementDefinition.from_dict(entry)
                definitions[defn.id] = defn
            except (KeyError, TypeError, ValueError):
                continue
        return definitions

    def _validate_positive_amount(self, raw_value: Any, context: str) -> float:
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid bonus value for {context}: {raw_value}") from e
        if value <= 0:
            raise ValueError(f"Bonus value for {context} must be positive (got {value})")
        if value > self.max_bonus_supply:
            raise ValueError(f"Bonus value for {context} ({value}) exceeds cap {self.max_bonus_supply}")
        return value

    # ----- JSON I/O -----

    def _load_json(self, filepath: str) -> dict:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_json(self, filepath: str, data: dict) -> None:
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error("IOError in _save_json", extra={"error": str(e), "function": "_save_json"})

    # ----- Time Utilities -----

    def _now(self) -> datetime:
        return self._time_provider()

    def _current_date_str(self) -> str:
        return self._now().strftime("%Y-%m-%d")

    # ----- Persistence Helpers -----

    def _save_progression(self) -> None:
        self._save_json(self.progression_file, self.progression)

    def _save_badges(self) -> None:
        self._save_json(self.badges_file, self.badges)

    def _save_daily_challenges(self) -> None:
        self._save_json(self.daily_challenges_file, self.daily_challenges_state)

    def _save_referral_guardian(self) -> None:
        self._save_json(self.referral_guardian_file, self.referral_guardian)

    # ----- Badge/Trophy System -----

    def _get_badge_record(self, address: str) -> dict[str, Any]:
        record = self.badges.get(address)
        if record is None:
            record = {"badges": [], "trophies": [], "daily_challenge_counts": {}}
            self.badges[address] = record
        record.setdefault("badges", [])
        record.setdefault("trophies", [])
        record.setdefault("daily_challenge_counts", {})
        return record

    def _award_badge(self, address: str, badge_name: str, source: str, metadata: dict[str, Any] | None = None) -> None:
        record = self._get_badge_record(address)
        if any(b.get("name") == badge_name for b in record["badges"]):
            return
        entry = {"name": badge_name, "awarded_at": self._now().isoformat(), "source": source}
        if metadata:
            entry["metadata"] = metadata
        record["badges"].append(entry)
        self._save_badges()
        self._evaluate_trophies(address)

    def _evaluate_trophies(self, address: str) -> None:
        record = self._get_badge_record(address)
        owned_badges = {b["name"] for b in record.get("badges", [])}
        owned_trophies = {t["id"] for t in record.get("trophies", [])}

        for defn in self._trophy_definitions:
            trophy_id = defn["id"]
            if trophy_id in owned_trophies:
                continue
            required = set(defn.get("required_badges", []))
            if required and not required.issubset(owned_badges):
                continue
            daily_req = defn.get("daily_requirement")
            if daily_req:
                cid = daily_req.get("id")
                cnt_req = daily_req.get("count", 0)
                counts = record["daily_challenge_counts"].get(cid, {})
                if counts.get("total", 0) < cnt_req:
                    continue

            bonus_awarded = 0.0
            if defn.get("bonus", 0.0) > 0:
                ok, _ = self._attempt_award_bonus(
                    address, "trophy", float(defn["bonus"]),
                    f"Trophy unlocked: {trophy_id}", context=f"trophy:{trophy_id}"
                )
                if ok:
                    bonus_awarded = float(defn["bonus"])

            xp_awarded = 0.0
            if defn.get("xp", 0.0) > 0:
                res = self._award_xp(address, float(defn["xp"]), reason=f"trophy:{trophy_id}", context=f"trophy:{trophy_id}")
                xp_awarded = res.get("xp_awarded", defn["xp"])

            record.setdefault("trophies", []).append({
                "id": trophy_id, "awarded_at": self._now().isoformat(),
                "description": defn["description"], "bonus": bonus_awarded, "xp": xp_awarded
            })
            self._save_badges()

    def get_badges_summary(self, address: str) -> dict[str, Any]:
        record = self._get_badge_record(address)
        return {
            "badges": list(record.get("badges", [])),
            "trophies": list(record.get("trophies", [])),
            "daily_challenge_counts": dict(record.get("daily_challenge_counts", {})),
        }

    # ----- Daily Challenges -----

    def _refresh_daily_challenges_if_needed(self) -> None:
        today = self._current_date_str()
        state = self.daily_challenges_state
        if state.get("rotation_date") == today and state.get("challenges"):
            state.setdefault("completions", {})
            return
        challenges = self._generate_daily_challenges(today)
        self.daily_challenges_state = {"rotation_date": today, "challenges": challenges, "completions": {}}
        self._save_daily_challenges()

    def _generate_daily_challenges(self, date_key: str) -> list[dict[str, Any]]:
        if not self._daily_challenge_catalog:
            return []
        selected, used = [], set()
        target = min(3, len(self._daily_challenge_catalog))
        for salt in range(target * 3):
            digest = hashlib.sha256(f"{date_key}:{salt}".encode()).digest()
            idx = int.from_bytes(digest[:4], byteorder="big") % len(self._daily_challenge_catalog)
            if idx in used:
                continue
            used.add(idx)
            selected.append(dict(self._daily_challenge_catalog[idx]))
            if len(selected) == target:
                break
        return selected

    def _get_daily_completion_book(self, address: str) -> dict[str, Any]:
        self.daily_challenges_state.setdefault("completions", {})
        book = self.daily_challenges_state["completions"].setdefault(address, {})
        return book

    def _is_challenge_completed(self, challenge: dict, metrics: dict, daily_activity: dict) -> bool:
        cond = challenge.get("condition", {})
        ctype, thresh = cond.get("type"), cond.get("threshold", 0)
        comp = cond.get("comparison", ">=")
        val = daily_activity.get("referrals_today", 0) if ctype == "referral_count_daily" else metrics.get(ctype, 0)
        return self._compare_metric(val, thresh, comp)

    def _record_daily_challenge_completion(self, address: str, cid: str, book: dict) -> bool:
        today = self._current_date_str()
        entry = book.setdefault(today, {}).setdefault(cid, {"completed": False, "awarded": False})
        if entry["completed"]:
            return False
        entry["completed"] = True
        return True

    def _update_daily_challenge_counter(self, address: str, cid: str) -> None:
        record = self._get_badge_record(address)
        entry = record.setdefault("daily_challenge_counts", {}).setdefault(cid, {"total": 0, "dates": []})
        entry["total"] += 1
        today = self._current_date_str()
        if today not in entry["dates"]:
            entry["dates"].append(today)
            entry["dates"] = entry["dates"][-30:]
        self._save_badges()

    def _evaluate_daily_challenges(self, address: str, metrics: dict, daily_activity: dict | None = None) -> dict:
        self._refresh_daily_challenges_if_needed()
        state = self.daily_challenges_state
        book = self._get_daily_completion_book(address)
        daily_activity = daily_activity or {}
        completions = []

        for ch in state.get("challenges", []):
            cid = ch.get("id")
            if not cid:
                continue
            if book.get(self._current_date_str(), {}).get(cid, {}).get("completed"):
                continue
            if not self._is_challenge_completed(ch, metrics, daily_activity):
                continue
            if not self._record_daily_challenge_completion(address, cid, book):
                continue

            awarded_tokens, awarded_xp = 0.0, 0.0
            if ch.get("bonus", 0.0) > 0:
                ok, _ = self._attempt_award_bonus(
                    address, "daily_challenge", float(ch["bonus"]),
                    f"Daily challenge completed: {cid}", context=f"daily_challenge:{cid}"
                )
                if ok:
                    awarded_tokens = float(ch["bonus"])
            if ch.get("xp", 0.0) > 0:
                res = self._award_xp(address, float(ch["xp"]), reason=f"daily_challenge:{cid}", context=f"daily_challenge:{cid}")
                awarded_xp = res.get("xp_awarded", ch["xp"])

            completions.append({"challenge_id": cid, "awarded_tokens": awarded_tokens, "awarded_xp": awarded_xp, "completed_at": self._now().isoformat()})
            self._update_daily_challenge_counter(address, cid)

        if completions:
            self._save_daily_challenges()
            self._evaluate_trophies(address)

        return {"rotation_date": state.get("rotation_date"), "completed_today": completions, "active_challenges": state.get("challenges", [])}

    def get_daily_challenges_status(self, address: str) -> dict[str, Any]:
        self._refresh_daily_challenges_if_needed()
        state = self.daily_challenges_state
        book = self._get_daily_completion_book(address)
        today = self._current_date_str()
        today_status = book.get(today, {})
        result = []
        for ch in state.get("challenges", []):
            entry = dict(ch)
            cinfo = today_status.get(ch.get("id"))
            entry["completed"] = bool(cinfo and cinfo.get("completed"))
            entry["awarded"] = bool(cinfo and cinfo.get("awarded"))
            result.append(entry)
        return {"rotation_date": state.get("rotation_date"), "challenges": result}

    # ----- Progression System -----

    def _get_progression_record(self, address: str) -> dict[str, Any]:
        record = self.progression.get(address)
        if record is None:
            record = {"address": address, "total_xp": 0.0, "lifetime_xp": 0.0, "history": [], "last_reason": None, "last_updated": None}
            self.progression[address] = record
        return record

    def _calculate_level_state(self, total_xp: float) -> dict[str, float]:
        base = self.progression_config.get("base_xp_per_level", 150.0)
        growth = self.progression_config.get("level_growth_rate", 1.18)
        max_thresh = self.progression_config.get("max_xp_per_level", 4000.0)
        remaining = max(0.0, float(total_xp))
        level, xp_threshold = 1, base
        while remaining >= xp_threshold:
            remaining -= xp_threshold
            level += 1
            xp_threshold = min(max_thresh, xp_threshold * growth)
        progress = round((remaining / xp_threshold) * 100, 2) if xp_threshold > 0 else 0.0
        return {"level": level, "xp_into_level": remaining, "xp_to_next_level": xp_threshold, "progress_percent": progress}

    def _xp_from_context(self, context: str, amount: float) -> float:
        prefix = context.split(":", 1)[0] if context else "default"
        mult = self._xp_context_multipliers.get(prefix, self._xp_context_multipliers.get("default", 1.0))
        xp = float(amount) * mult * self.progression_config.get("xp_per_token", 1.0)
        return round(max(self.progression_config.get("min_event_xp", 8.0), xp), 2)

    def _award_xp(self, address: str, xp_amount: float, reason: str, context: str | None = None, metadata: dict | None = None) -> dict:
        xp = max(0.0, float(xp_amount))
        if xp == 0:
            return {"xp_awarded": 0.0, "level_up": False}
        record = self._get_progression_record(address)
        before = self._calculate_level_state(record.get("total_xp", 0.0))
        record["total_xp"] = record.get("total_xp", 0.0) + xp
        record["lifetime_xp"] = record.get("lifetime_xp", 0.0) + xp
        after = self._calculate_level_state(record["total_xp"])
        event = {"timestamp": datetime.now().isoformat(), "xp": xp, "reason": reason, "context": context or reason, "level_after": after["level"]}
        if metadata:
            event["metadata"] = metadata
        history = record.setdefault("history", [])
        history.append(event)
        limit = int(self.progression_config.get("history_limit", 50))
        if len(history) > limit:
            del history[:len(history) - limit]
        record["last_reason"], record["last_updated"] = reason, event["timestamp"]
        self._save_progression()
        return {"xp_awarded": xp, "level_up": after["level"] > before["level"], "level": after["level"], "progress_percent": after["progress_percent"]}

    def _record_progression_event(self, address: str, context: str, amount: float, bonus_type: str) -> None:
        xp = self._xp_from_context(context, amount)
        self._award_xp(address, xp, reason=context.split(":", 1)[0] if context else "bonus", context=context, metadata={"bonus_amount": amount, "bonus_type": bonus_type})

    def get_progression_summary(self, address: str) -> dict[str, Any]:
        record = self._get_progression_record(address)
        state = self._calculate_level_state(record.get("total_xp", 0.0))
        return {
            "address": address, "level": state["level"],
            "total_xp": round(record.get("total_xp", 0.0), 2),
            "lifetime_xp": round(record.get("lifetime_xp", 0.0), 2),
            "xp_into_level": round(state["xp_into_level"], 2),
            "xp_to_next_level": round(state["xp_to_next_level"], 2),
            "progress_percent": state["progress_percent"],
            "last_updated": record.get("last_updated"),
            "last_reason": record.get("last_reason"),
            "recent_events": list(reversed(record.get("history", [])[-5:])),
        }

    # ----- Achievement System -----

    def _build_achievement_metrics(self, address: str, blocks_mined: int, streak_days: int, overrides: dict | None = None) -> dict:
        record = self.progression.get(address) or {}
        ref_data = self.referrals.get(address, {})
        social_claims = self.bonuses.get(address, {}).get("claimed", [])
        guardian = self.referral_guardian.get("referrers", {}).get(address, {})
        today = self._current_date_str()
        metrics = {
            "blocks_mined": max(0, int(blocks_mined)),
            "streak_days": max(0, int(streak_days)),
            "referral_count": len(ref_data.get("referred_miners", [])),
            "referral_count_daily": int(guardian.get("daily_counts", {}).get(today, 0)),
            "xp_total": float(record.get("total_xp", 0.0)),
            "social_actions": len(social_claims),
        }
        if overrides:
            metrics.update(overrides)
        return metrics

    def _achievement_condition_met(self, defn: AchievementDefinition, metrics: dict) -> bool:
        cond = defn.condition or {}
        ctype, thresh, comp = cond.get("type"), cond.get("threshold", 0), cond.get("comparison", ">=")
        value = metrics.get(ctype, 0)
        return self._compare_metric(value, thresh, comp)

    @staticmethod
    def _compare_metric(value: Any, threshold: Any, comparator: str) -> bool:
        try:
            if comparator == ">=": return value >= threshold
            if comparator == ">": return value > threshold
            if comparator == "==": return value == threshold
            if comparator == "<=": return value <= threshold
            if comparator == "<": return value < threshold
        except TypeError:
            return False
        return False

    def get_achievement_catalog(self) -> list[dict[str, Any]]:
        return [d.serialize() for d in self.achievement_definitions.values()]

    def check_achievements(self, address: str, blocks_mined: int, streak_days: int, extra_metrics: dict | None = None) -> dict:
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}
        record = self.achievements.setdefault(address, {"earned": [], "total_bonus": 0, "total_xp": 0.0})
        record.setdefault("total_xp", 0.0)
        metrics = self._build_achievement_metrics(address, blocks_mined, streak_days, extra_metrics)
        daily_activity = {"referrals_today": self.referral_guardian.get("referrers", {}).get(address, {}).get("daily_counts", {}).get(self._current_date_str(), 0)}
        earned_types = {a.get("type") for a in record["earned"]}
        newly_earned, total_new_bonus, total_new_xp = [], 0.0, 0.0

        for defn in self.achievement_definitions.values():
            if defn.id in earned_types:
                continue
            if not self._achievement_condition_met(defn, metrics):
                continue

            bonus_awarded = 0.0
            if defn.bonus > 0:
                ok, err = self._attempt_award_bonus(address, "achievement", defn.bonus, defn.description, context=f"achievement:{defn.id}")
                if not ok:
                    return {"success": False, "error": err, "new_achievements": newly_earned, "total_new_bonus": total_new_bonus, "total_new_xp": total_new_xp}
                bonus_awarded = defn.bonus

            xp_awarded, xp_res = 0.0, None
            if defn.xp > 0:
                xp_res = self._award_xp(address, defn.xp, reason=f"achievement:{defn.id}", context=f"achievement:{defn.id}", metadata={"achievement_category": defn.category})
                xp_awarded = xp_res.get("xp_awarded", defn.xp)

            entry = {"type": defn.id, "description": defn.description, "category": defn.category, "bonus": bonus_awarded, "xp_awarded": xp_awarded, "earned_at": datetime.now().isoformat(), "tags": list(defn.tags), "condition": defn.condition}
            if defn.reward_badge:
                entry["badge"] = defn.reward_badge
                self._award_badge(address, defn.reward_badge, source=f"achievement:{defn.id}", metadata={"category": defn.category})
            if xp_res:
                entry["level_after"] = xp_res.get("level")

            newly_earned.append(entry)
            record["earned"].append(entry)
            record["total_bonus"] = record.get("total_bonus", 0.0) + bonus_awarded
            record["total_xp"] = record.get("total_xp", 0.0) + xp_awarded
            total_new_bonus += bonus_awarded
            total_new_xp += xp_awarded
            earned_types.add(defn.id)

        if newly_earned:
            self._save_json(self.achievements_file, self.achievements)

        daily_summary = self._evaluate_daily_challenges(address, metrics, daily_activity)
        return {"success": True, "address": address, "blocks_mined": blocks_mined, "streak_days": streak_days, "metrics": metrics, "new_achievements": newly_earned, "total_new_bonus": total_new_bonus, "total_new_xp": round(total_new_xp, 2), "all_achievements": record["earned"], "available_achievements": self.get_achievement_catalog(), "daily_challenges": daily_summary, "badges": self.get_badges_summary(address)}

    # ----- Referral System -----

    def _extract_identity_hash(self, metadata: dict | None) -> str | None:
        if not metadata:
            return None
        ih = metadata.get("identity_hash")
        if not ih or not isinstance(ih, str) or len(ih.strip()) < 32:
            return None
        return ih.strip()

    def _validate_referral_request(self, referrer: str, new_addr: str, metadata: dict | None) -> dict | None:
        if referrer == new_addr:
            return {"success": False, "error": "Self-referrals are not permitted", "referrer_address": referrer}
        guardian = self.referral_guardian.setdefault("referrers", {})
        entry = guardian.setdefault(referrer, {"recent": [], "daily_counts": {}, "flagged": False})
        today = self._current_date_str()
        if entry.get("daily_counts", {}).get(today, 0) >= self._referral_daily_limit:
            return {"success": False, "error": "Daily referral limit reached", "limit": self._referral_daily_limit}
        now_ts = self._now().timestamp()
        recent = [ts for ts in entry["recent"] if now_ts - ts <= self._referral_window_seconds]
        if len(recent) >= self._referral_burst_limit:
            entry["flagged"] = True
            self._save_referral_guardian()
            return {"success": False, "error": "Referral burst detected. Try again later.", "cooldown_seconds": self._referral_window_seconds}
        entry["recent"] = recent
        ih = self._extract_identity_hash(metadata)
        if ih:
            identities = self.referral_guardian.setdefault("identities", {})
            existing = identities.get(ih)
            if existing and existing != new_addr:
                return {"success": False, "error": "Identity already registered with another address", "address": existing}
        return None

    def _record_referral_activity(self, referrer: str, metadata: dict | None, new_addr: str) -> None:
        guardian = self.referral_guardian.setdefault("referrers", {})
        entry = guardian.setdefault(referrer, {"recent": [], "daily_counts": {}, "flagged": False})
        today = self._current_date_str()
        entry["recent"].append(self._now().timestamp())
        entry["daily_counts"][today] = entry["daily_counts"].get(today, 0) + 1
        ih = self._extract_identity_hash(metadata)
        if ih:
            self.referral_guardian.setdefault("identities", {})[ih] = new_addr
        self._save_referral_guardian()

    def create_referral_code(self, address: str) -> dict:
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}
        if address not in self.referrals:
            self.referrals[address] = {"referral_code": str(uuid.uuid4())[:8].upper(), "referred_miners": [], "total_referral_bonus": 0, "created_at": datetime.now().isoformat()}
        elif "referral_code" in self.referrals[address]:
            return {"success": True, "address": address, "referral_code": self.referrals[address]["referral_code"], "message": "Referral code already exists"}
        self._save_json(self.referrals_file, self.referrals)
        return {"success": True, "address": address, "referral_code": self.referrals[address]["referral_code"], "message": "Referral code created successfully", "bonus_per_referral": self.referral_bonuses.get("refer_friend", 10), "bonus_when_friend_mines_10": self.referral_bonuses.get("friend_10_blocks", 25)}

    def use_referral_code(self, new_address: str, referral_code: str, metadata: dict | None = None) -> dict:
        referrer = None
        for addr, data in self.referrals.items():
            if data.get("referral_code") == referral_code:
                referrer = addr
                break
        if not referrer:
            return {"success": False, "error": "Invalid referral code", "new_address": new_address}
        if self.referrals.get(new_address, {}).get("referred_by"):
            return {"success": False, "error": "Address already tied to a referral", "new_address": new_address}
        val_error = self._validate_referral_request(referrer, new_address, metadata)
        if val_error:
            return val_error
        if new_address not in self.miners:
            self.register_miner(new_address)
        bonus = self.referral_bonuses.get("refer_friend", 10)
        ok, err = self._attempt_award_bonus(referrer, "referral", bonus, f"Referred new miner: {new_address}", context="referral:new_miner")
        if not ok:
            return {"success": False, "error": err, "message": "Referral bonus pool exhausted", "referrer_address": referrer}
        self.referrals[referrer]["referred_miners"].append({"address": new_address, "referred_at": datetime.now().isoformat(), "blocks_mined": 0, "milestone_bonus_claimed": False})
        self.referrals[referrer]["total_referral_bonus"] += bonus
        self.referrals.setdefault(new_address, {})["referred_by"] = referrer
        self._save_json(self.referrals_file, self.referrals)
        self._record_referral_activity(referrer, metadata, new_address)
        return {"success": True, "new_address": new_address, "referrer_address": referrer, "referrer_bonus": bonus, "message": "Successfully registered with referral code"}

    def check_referral_milestone(self, referrer_address: str, referred_address: str, blocks_mined: int) -> dict:
        if referrer_address not in self.referrals:
            return {"success": False, "error": "Referrer not found"}
        ref_list = self.referrals[referrer_address].get("referred_miners", [])
        rec = next((r for r in ref_list if r["address"] == referred_address), None)
        if not rec:
            return {"success": False, "error": "Referred miner not found in records"}
        if blocks_mined >= 10 and not rec.get("milestone_bonus_claimed"):
            bonus = self.referral_bonuses.get("friend_10_blocks", 25)
            ok, err = self._attempt_award_bonus(referrer_address, "referral_milestone", bonus, f"Friend {referred_address} mined 10 blocks", context="referral:milestone")
            if not ok:
                return {"success": False, "error": err, "referrer_address": referrer_address, "referred_address": referred_address}
            rec["milestone_bonus_claimed"], rec["blocks_mined"] = True, blocks_mined
            self.referrals[referrer_address]["total_referral_bonus"] += bonus
            self._save_json(self.referrals_file, self.referrals)
            return {"success": True, "referrer_bonus": bonus, "message": "Milestone bonus awarded for friend reaching 10 blocks", "total_bonus": self.referrals[referrer_address]["total_referral_bonus"]}
        return {"success": False, "message": "Milestone not yet reached or already claimed"}

    # ----- Miner Registration & Stats -----

    def register_miner(self, address: str) -> dict:
        if address in self.miners:
            return {"success": False, "message": "Miner already registered", "address": address}
        miner_count = len(self.miners)
        self.miners[address] = {"registered_at": datetime.now().isoformat(), "registration_number": miner_count + 1, "blocks_mined": 0, "total_earnings": 0, "last_block_timestamp": None, "streak_start": None, "current_streak": 0, "max_streak": 0}
        self._save_json(self.miners_file, self.miners)
        reg_num = miner_count + 1
        early_bonus, bonus_tier = 0, None
        for tier, bonus in sorted(self.early_adopter_tiers.items()):
            if reg_num <= tier:
                early_bonus, bonus_tier = bonus, tier
                break
        result = {"success": True, "message": "Miner registered successfully", "address": address, "registration_number": reg_num, "early_adopter_bonus": early_bonus}
        reg_xp = self.progression_rewards.get("registration", 0.0)
        if reg_xp > 0:
            self._award_xp(address, reg_xp, reason="registration", metadata={"registration_number": reg_num})
        if early_bonus > 0:
            result["bonus_tier"] = f"First {bonus_tier} miners"
            ok, err = self._attempt_award_bonus(address, "early_adopter", early_bonus, f"Early adopter bonus - tier {bonus_tier}", context="early_adopter")
            if not ok:
                result["early_adopter_bonus"], result["bonus_error"] = 0, err
        return result

    def update_miner_stats(self, address: str, blocks_mined: int, streak_days: int, mining_reward: float) -> None:
        if address in self.miners:
            m = self.miners[address]
            m["blocks_mined"], m["current_streak"], m["total_earnings"] = blocks_mined, streak_days, mining_reward
            m["last_block_timestamp"] = datetime.now().isoformat()
            if streak_days > m.get("max_streak", 0):
                m["max_streak"] = streak_days
            self._save_json(self.miners_file, self.miners)

    # ----- Bonus Claiming -----

    def claim_bonus(self, address: str, bonus_type: str) -> dict:
        if address not in self.miners:
            return {"success": False, "error": "Miner not registered"}
        if address not in self.bonuses:
            self.bonuses[address] = {"total_awarded": 0, "bonuses": [], "claimed": []}
        self.bonuses[address].setdefault("claimed", [])
        claimed = [b["type"] for b in self.bonuses[address]["claimed"]]
        if bonus_type in claimed:
            return {"success": False, "error": f"Bonus {bonus_type} already claimed", "address": address}
        if bonus_type == "tweet_verification":
            amt, desc = self.social_bonuses.get("tweet_verification", 5), "Tweet verification bonus"
        elif bonus_type == "discord_join":
            amt, desc = self.social_bonuses.get("discord_join", 2), "Discord join bonus"
        else:
            return {"success": False, "error": f"Unknown bonus type: {bonus_type}", "address": address}
        ok, err = self._attempt_award_bonus(address, bonus_type, amt, desc, context=f"social:{bonus_type}")
        if not ok:
            return {"success": False, "error": err, "address": address, "bonus_type": bonus_type}
        self.bonuses[address]["claimed"].append({"type": bonus_type, "amount": amt, "claimed_at": datetime.now().isoformat(), "description": desc})
        self._save_json(self.bonuses_file, self.bonuses)
        return {"success": True, "address": address, "bonus_type": bonus_type, "amount": amt, "message": f"{desc} claimed successfully", "claimed_at": datetime.now().isoformat()}

    # ----- Internal Bonus Award -----

    def _award_bonus(self, address: str, bonus_type: str, amount: float, description: str) -> None:
        if amount <= 0:
            raise ValueError("Bonus amount must be positive.")
        remaining = self._get_bonus_supply_remaining()
        if amount > remaining + 1e-9:
            raise BonusSupplyExceededError(amount, remaining, self.max_bonus_supply)
        if address not in self.bonuses:
            self.bonuses[address] = {"total_awarded": 0, "bonuses": [], "claimed": []}
        self.bonuses[address]["bonuses"].append({"type": bonus_type, "amount": amount, "description": description, "awarded_at": datetime.now().isoformat()})
        self.bonuses[address]["total_awarded"] = self.bonuses[address].get("total_awarded", 0) + amount
        total = self._get_total_awarded()
        usage = total / self.max_bonus_supply if self.max_bonus_supply else 1.0
        if not self._bonus_alert_emitted and self.bonus_alert_threshold > 0 and usage >= self.bonus_alert_threshold:
            logger.warning("Mining bonus pool usage at %.2f%% of cap", usage * 100, extra={"event": "mining_bonus.cap_threshold", "total_awarded": total, "cap": self.max_bonus_supply})
            self._bonus_alert_emitted = True

    def _attempt_award_bonus(self, address: str, bonus_type: str, amount: float, description: str, context: str) -> tuple[bool, str | None]:
        try:
            self._award_bonus(address, bonus_type, amount, description)
            self._record_progression_event(address, context, amount, bonus_type)
            return True, None
        except BonusSupplyExceededError as e:
            logger.warning("Bonus award skipped: %s", str(e), extra={"event": "mining_bonus.cap_exceeded", "context": context, "address": address, "bonus_type": bonus_type})
            return False, str(e)

    def _get_total_awarded(self) -> float:
        return sum(float(d.get("total_awarded", 0)) for d in self.bonuses.values() if isinstance(d.get("total_awarded"), (int, float)))

    def _get_bonus_supply_remaining(self) -> float:
        return max(0.0, self.max_bonus_supply - self._get_total_awarded())

    def _calculate_reserved_bonus_budget(self) -> float:
        total = 0.0
        prev = 0
        for tier_cap in sorted(self.early_adopter_tiers):
            total += (tier_cap - prev) * float(self.early_adopter_tiers[tier_cap])
            prev = tier_cap
        total += sum(float(v) for v in self.achievement_bonuses.values())
        total += sum(float(v) for v in self.referral_bonuses.values())
        total += sum(float(v) for v in self.social_bonuses.values())
        return total

    def get_total_awarded_amount(self) -> float:
        return self._get_total_awarded()

    def get_bonus_supply_remaining(self) -> float:
        return self._get_bonus_supply_remaining()

    # ----- User Bonuses Summary -----

    def get_user_bonuses(self, address: str) -> dict:
        if address not in self.miners:
            return {"error": "Miner not registered"}
        m = self.miners[address]
        bonuses_data = self.bonuses.get(address, {"claimed": []})
        ach_data = self.achievements.get(address, {"earned": [], "total_bonus": 0, "total_xp": 0.0})
        ref_data = self.referrals.get(address, {})
        claimed = bonuses_data.get("claimed", [])
        total_bonus = sum(b.get("amount", 0) for b in claimed) + ach_data.get("total_bonus", 0) + ref_data.get("total_referral_bonus", 0)
        return {
            "success": True, "address": address,
            "miner_stats": {"registered_at": m["registered_at"], "registration_number": m["registration_number"], "blocks_mined": m["blocks_mined"], "current_streak": m["current_streak"], "max_streak": m["max_streak"]},
            "social_bonuses": claimed,
            "achievements": ach_data["earned"],
            "referral_info": {"referral_code": ref_data.get("referral_code"), "referred_by": ref_data.get("referred_by"), "referred_miners": ref_data.get("referred_miners", []), "total_referral_bonus": ref_data.get("total_referral_bonus", 0)},
            "badges": self.get_badges_summary(address),
            "daily_challenges": self.get_daily_challenges_status(address),
            "summary": {"total_earned_bonus": total_bonus, "social_bonuses_earned": sum(b.get("amount", 0) for b in claimed), "achievement_bonuses_earned": ach_data.get("total_bonus", 0), "achievement_xp_earned": round(ach_data.get("total_xp", 0.0), 2), "referral_bonuses_earned": ref_data.get("total_referral_bonus", 0), "mining_rewards": m.get("total_earnings", 0)},
            "progression": self.get_progression_summary(address),
        }

    # ----- Leaderboards -----

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        data = [{"address": addr, "total_bonus": d.get("total_awarded", 0), "bonus_count": len(d.get("bonuses", []))} for addr, d in self.bonuses.items()]
        data.sort(key=lambda x: x["total_bonus"], reverse=True)
        return data[:limit]

    def get_unified_leaderboard(self, metric: str = "composite", limit: int = 10) -> list[dict]:
        metric = (metric or "composite").lower()
        lb = []
        for addr, miner in self.miners.items():
            prog = self.progression.get(addr, {})
            xp_total = float(prog.get("total_xp", 0.0))
            total_bonus = float(self.bonuses.get(addr, {}).get("total_awarded", 0.0))
            ref_count = len(self.referrals.get(addr, {}).get("referred_miners", []))
            max_streak = int(miner.get("max_streak", miner.get("current_streak", 0)))
            composite = xp_total + total_bonus * 25 + ref_count * 40 + max_streak * 5
            val = {"xp": xp_total, "bonus": total_bonus, "referrals": ref_count, "streak": max_streak}.get(metric, composite)
            lb.append({"address": addr, "metric": metric, "score": round(val, 2), "metrics": {"xp_total": round(xp_total, 2), "total_bonus": round(total_bonus, 2), "referrals": ref_count, "max_streak": max_streak}})
        lb.sort(key=lambda x: x["score"], reverse=True)
        return lb[:max(1, limit)]

    # ----- Stats -----

    def _build_progression_stats(self) -> dict:
        if not self.progression:
            return {"tracked_players": 0, "average_level": 1.0, "top_level": 1, "total_tracked_xp": 0.0}
        levels = [self._calculate_level_state(float(r.get("total_xp", 0.0)))["level"] for r in self.progression.values()]
        totals = [float(r.get("total_xp", 0.0)) for r in self.progression.values()]
        return {"tracked_players": len(levels), "average_level": round(sum(levels) / len(levels), 2), "top_level": max(levels), "total_tracked_xp": round(sum(totals), 2)}

    def get_stats(self) -> dict:
        return {
            "total_registered_miners": len(self.miners),
            "total_bonuses_awarded": self._get_total_awarded(),
            "active_referral_codes": sum(1 for d in self.referrals.values() if d.get("referral_code")),
            "early_adopter_tiers": self.early_adopter_tiers,
            "achievement_bonuses": self.achievement_bonuses,
            "referral_bonuses": self.referral_bonuses,
            "social_bonuses": self.social_bonuses,
            "bonus_cap": self.max_bonus_supply,
            "bonus_remaining": self._get_bonus_supply_remaining(),
            "progression": self._build_progression_stats(),
            "badges": {"awarded": sum(len(r.get("badges", [])) for r in self.badges.values()), "trophies": sum(len(r.get("trophies", [])) for r in self.badges.values())},
            "daily_challenges": {"rotation_date": self.daily_challenges_state.get("rotation_date"), "active_challenges": len(self.daily_challenges_state.get("challenges", []))},
        }


if __name__ == "__main__":
    manager = MiningBonusManager()
    print("Registering miners...")
    print(manager.register_miner("AXN123abc"))
    print(manager.register_miner("AXN456def"))
    print("\nCreating referral code...")
    ref_result = manager.create_referral_code("AXN123abc")
    print(ref_result)
    print("\nUsing referral code...")
    print(manager.use_referral_code("AXN789ghi", ref_result["referral_code"]))
    print("\nChecking achievements...")
    print(manager.check_achievements("AXN123abc", 100, 7))
    print("\nClaiming social bonus...")
    print(manager.claim_bonus("AXN456def", "tweet_verification"))
    print("\nUser bonuses summary...")
    print(json.dumps(manager.get_user_bonuses("AXN123abc"), indent=2))
    print("\nLeaderboard...")
    print(json.dumps(manager.get_leaderboard(), indent=2))
    print("\nSystem stats...")
    print(json.dumps(manager.get_stats(), indent=2))
