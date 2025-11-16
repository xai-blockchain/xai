"""
XAI Blacklist Governance System

After 1 year, active nodes vote on:
- Whether blacklist updates should be mandatory
- How often updates required (if mandatory)
"""

import time
import hashlib
from typing import Dict, List, Set
from enum import Enum


class VoteOption(Enum):
    """Blacklist update policy options"""

    OPTIONAL = "optional"  # Keep optional forever
    MANDATORY_24H = "mandatory_24h"  # Mandatory every 24 hours
    MANDATORY_48H = "mandatory_48h"  # Mandatory every 48 hours
    MANDATORY_WEEKLY = "mandatory_weekly"  # Mandatory weekly


class NodeVote:
    """Individual node vote"""

    def __init__(self, node_id: str, vote: VoteOption, timestamp: float):
        self.node_id = node_id
        self.vote = vote
        self.timestamp = timestamp
        self.signature = self._generate_signature()

    def _generate_signature(self) -> str:
        """Generate vote signature"""
        data = f"{self.node_id}-{self.vote.value}-{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


class BlacklistGovernanceVote:
    """Manages governance vote on blacklist policy"""

    def __init__(self, genesis_time: float):
        self.genesis_time = genesis_time
        self.vote_start_time = genesis_time + (365 * 86400)  # 1 year
        self.vote_end_time = self.vote_start_time + (30 * 86400)  # 30-day voting period

        self.votes = {}  # node_id -> NodeVote
        self.vote_closed = False
        self.decided_result = None

    def is_voting_active(self) -> bool:
        """Check if voting period is active"""
        current_time = time.time()
        return self.vote_start_time <= current_time <= self.vote_end_time

    def can_vote_start(self) -> bool:
        """Check if voting can start"""
        return time.time() >= self.vote_start_time

    def cast_vote(self, node_id: str, vote: VoteOption, node_is_active: bool = True) -> Dict:
        """
        Cast vote (only active nodes can vote)

        Args:
            node_id: Unique node identifier
            vote: Vote option
            node_is_active: Whether node has been active (30+ days uptime)

        Returns:
            Result dict
        """

        # Check voting period
        if not self.is_voting_active():
            if not self.can_vote_start():
                return {
                    "success": False,
                    "error": "VOTING_NOT_STARTED",
                    "days_until_vote": (self.vote_start_time - time.time()) / 86400,
                }
            else:
                return {"success": False, "error": "VOTING_ENDED"}

        # Check if already voted
        if node_id in self.votes:
            return {
                "success": False,
                "error": "ALREADY_VOTED",
                "previous_vote": self.votes[node_id].vote.value,
            }

        # Check node eligibility (must be active)
        if not node_is_active:
            return {
                "success": False,
                "error": "NODE_NOT_ACTIVE",
                "message": "Only nodes with 30+ days uptime can vote",
            }

        # Record vote
        node_vote = NodeVote(node_id, vote, time.time())
        self.votes[node_id] = node_vote

        return {"success": True, "vote_recorded": vote.value, "signature": node_vote.signature}

    def get_vote_tally(self) -> Dict:
        """Get current vote counts"""

        tally = {
            VoteOption.OPTIONAL: 0,
            VoteOption.MANDATORY_24H: 0,
            VoteOption.MANDATORY_48H: 0,
            VoteOption.MANDATORY_WEEKLY: 0,
        }

        for vote in self.votes.values():
            tally[vote.vote] += 1

        return {
            "optional": tally[VoteOption.OPTIONAL],
            "mandatory_24h": tally[VoteOption.MANDATORY_24H],
            "mandatory_48h": tally[VoteOption.MANDATORY_48H],
            "mandatory_weekly": tally[VoteOption.MANDATORY_WEEKLY],
            "total_votes": len(self.votes),
        }

    def close_vote(self) -> Dict:
        """
        Close vote after voting period ends

        Returns winning option
        """

        if self.is_voting_active():
            return {"success": False, "error": "VOTING_STILL_ACTIVE"}

        if self.vote_closed:
            return {
                "success": True,
                "result": self.decided_result,
                "message": "Vote already closed",
            }

        # Count votes
        tally = self.get_vote_tally()

        # Determine winner (most votes)
        winner = None
        max_votes = 0

        for option in VoteOption:
            count = tally.get(option.value, 0)
            if count > max_votes:
                max_votes = count
                winner = option

        self.vote_closed = True
        self.decided_result = winner

        return {
            "success": True,
            "result": winner.value if winner else "optional",
            "vote_counts": tally,
            "winning_votes": max_votes,
            "total_votes": tally["total_votes"],
        }

    def get_current_policy(self) -> str:
        """Get current blacklist policy"""

        current_time = time.time()

        # Before vote starts: Optional
        if current_time < self.vote_start_time:
            return "optional"

        # During voting: Still optional
        if self.is_voting_active():
            return "optional"

        # After voting: Use result
        if self.vote_closed and self.decided_result:
            return self.decided_result.value

        # Vote ended but not closed: trigger close
        self.close_vote()
        if self.decided_result:
            return self.decided_result.value

        return "optional"

    def get_update_frequency_hours(self) -> int:
        """Get required update frequency based on policy"""

        policy = self.get_current_policy()

        if policy == "optional":
            return 0  # No requirement
        elif policy == "mandatory_24h":
            return 24
        elif policy == "mandatory_48h":
            return 48
        elif policy == "mandatory_weekly":
            return 168  # 7 days
        else:
            return 0


# Example usage
if __name__ == "__main__":
    from datetime import datetime

    print("=" * 70)
    print("XAI BLACKLIST GOVERNANCE SYSTEM")
    print("=" * 70)

    GENESIS_TIME = 1704067200.0  # Nov 6, 2024

    governance = BlacklistGovernanceVote(GENESIS_TIME)

    print(f"\nGenesis Time: {datetime.fromtimestamp(GENESIS_TIME).isoformat()}")
    print(f"Vote Start: {datetime.fromtimestamp(governance.vote_start_time).isoformat()}")
    print(f"Vote End: {datetime.fromtimestamp(governance.vote_end_time).isoformat()}")

    # Check if voting active
    print(f"\nVoting Active: {governance.is_voting_active()}")
    print(f"Current Policy: {governance.get_current_policy()}")

    # Simulate votes (would happen 1 year from now)
    print("\n" + "=" * 70)
    print("SIMULATED VOTE RESULTS (After 1 Year)")
    print("=" * 70)

    # Temporarily set to voting period for simulation
    governance.vote_start_time = time.time() - 86400
    governance.vote_end_time = time.time() + (29 * 86400)

    # Cast some votes
    governance.cast_vote("node_1", VoteOption.MANDATORY_48H, node_is_active=True)
    governance.cast_vote("node_2", VoteOption.MANDATORY_48H, node_is_active=True)
    governance.cast_vote("node_3", VoteOption.OPTIONAL, node_is_active=True)
    governance.cast_vote("node_4", VoteOption.MANDATORY_48H, node_is_active=True)
    governance.cast_vote("node_5", VoteOption.MANDATORY_WEEKLY, node_is_active=True)

    tally = governance.get_vote_tally()
    print(f"\nVote Tally:")
    print(f"  Optional: {tally['optional']}")
    print(f"  Mandatory 24h: {tally['mandatory_24h']}")
    print(f"  Mandatory 48h: {tally['mandatory_48h']}")
    print(f"  Mandatory Weekly: {tally['mandatory_weekly']}")
    print(f"  Total Votes: {tally['total_votes']}")

    # End voting and close
    governance.vote_end_time = time.time() - 1
    result = governance.close_vote()

    print(f"\nVote Result:")
    print(f"  Winner: {result['result']}")
    print(f"  Winning Votes: {result['winning_votes']}")
    print(f"\nNew Policy: {governance.get_current_policy()}")
    print(f"Update Frequency: {governance.get_update_frequency_hours()} hours")

    print("\n" + "=" * 70)
