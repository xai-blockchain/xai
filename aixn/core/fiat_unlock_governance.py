"""
Simple governance-based fiat unlock manager.

Nodes can cast votes after the preset start date (March 12, 2026 UTC),
and rails unlock if enough votes agree before the scheduled auto-unlock
on November 1, 2026 UTC.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from config import Config
from anonymous_logger import log_info


class FiatUnlockGovernance:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.votes_file = os.path.join(self.data_dir, 'fiat_unlock_votes.json')
        os.makedirs(self.data_dir, exist_ok=True)
        self.votes: Dict[str, bool] = {}
        self._load_votes()

    def _load_votes(self):
        if os.path.exists(self.votes_file):
            with open(self.votes_file, 'r') as f:
                try:
                    self.votes = json.load(f)
                except json.JSONDecodeError:
                    self.votes = {}

    def _save_votes(self):
        with open(self.votes_file, 'w') as f:
            json.dump(self.votes, f, indent=2)

    def can_start_voting(self) -> bool:
        return datetime.now(timezone.utc) >= Config.FIAT_UNLOCK_GOVERNANCE_START

    def cast_vote(self, address: str, support: bool, reason: Optional[str] = None) -> Dict[str, object]:
        if not self.can_start_voting():
            raise ValueError("Voting window does not open until March 12, 2026 UTC")

        normalized = address.strip().upper()
        self.votes[normalized] = bool(support)
        self._save_votes()
        if support:
            log_info(f"Fiat unlock vote supporting from {normalized}; reason: {reason or 'none'}")
        else:
            log_info(f"Fiat unlock vote opposing from {normalized}; reason: {reason or 'none'}")
        return self.get_status()

    def support_count(self) -> int:
        return sum(1 for vote in self.votes.values() if vote)

    def total_votes(self) -> int:
        return len(self.votes)

    def support_ratio(self) -> float:
        total = self.total_votes()
        if total == 0:
            return 0.0
        return self.support_count() / total

    def is_unlocked(self) -> bool:
        now = datetime.now(timezone.utc)
        if now >= Config.FIAT_REENABLE_DATE:
            return True
        if not self.can_start_voting():
            return False
        if (
            self.total_votes() >= Config.FIAT_UNLOCK_REQUIRED_VOTES
            and self.support_ratio() >= Config.FIAT_UNLOCK_SUPPORT_PERCENT
        ):
            return True
        return False

    def get_status(self) -> Dict[str, object]:
        return {
            "votes_cast": self.total_votes(),
            "votes_for": self.support_count(),
            "support_ratio": round(self.support_ratio(), 4),
            "required_votes": Config.FIAT_UNLOCK_REQUIRED_VOTES,
            "support_threshold": Config.FIAT_UNLOCK_SUPPORT_PERCENT,
            "governance_start": Config.FIAT_UNLOCK_GOVERNANCE_START.isoformat(),
            "auto_unlock": Config.FIAT_REENABLE_DATE.isoformat(),
            "unlocked": self.is_unlocked(),
        }
