from __future__ import annotations

"""
Enhanced Voting System with Coin-Holding Incentives

Combines two factors for voting power:
1. XAI coins held (70% weight) - Incentivizes HOLDING
2. AI minutes donated (30% weight) - Rewards contributors

Key Features:
- Must hold coins from vote through project completion
- Continuous verification (lose vote if sell coins)
- Mandatory 1-week minimum timeline
- Multiple voting checkpoints throughout project
- Anti-gaming measures

This encourages people to:
✅ Buy and HOLD XAI (price support)
✅ Donate AI credits (development funding)
✅ Stay engaged throughout project lifecycle
"""

import time
from dataclasses import dataclass
from enum import Enum


class VoteCheckpoint(Enum):
    """Multiple voting stages throughout project"""

    INITIAL_APPROVAL = "initial_approval"  # Day 0: Should we do this?
    MILESTONE_25 = "milestone_25"  # 25% through timeline
    MILESTONE_50 = "milestone_50"  # 50% through timeline
    MILESTONE_75 = "milestone_75"  # 75% through timeline
    FINAL_APPROVAL = "final_approval"  # Before deployment
    CODE_REVIEW_VOTE = "code_review_vote"  # After AI completes

class VoteStatus(Enum):
    """Status of a vote"""

    VALID = "valid"  # Voter still holds coins
    INVALIDATED_SOLD_COINS = "invalidated_sold_coins"  # Sold coins
    INVALIDATED_TRANSFERRED = "invalidated_transferred"  # Transferred coins
    WITHDRAWN = "withdrawn"  # Voter manually withdrew

@dataclass
class VoterSnapshot:
    """Snapshot of voter's holdings at vote time"""

    address: str
    vote_time: float

    # Coin holdings (verified on-chain)
    xai_balance: float  # XAI coins held
    xai_balance_block: int  # Block height of snapshot

    # AI donation contribution
    total_ai_minutes_donated: int  # Total AI minutes ever donated
    total_ai_tokens_donated: int  # Total tokens donated
    ai_usd_value: float  # USD value of donations

    # Combined voting power
    coin_voting_power: float  # From coins held (70% weight)
    donation_voting_power: float  # From donations (30% weight)
    total_voting_power: float  # Combined

    # Verification
    verified_until: float | None = None  # Last verification time
    is_valid: bool = True  # Still holds coins?
    invalidation_reason: str | None = None

@dataclass
class ProjectTimeline:
    """Mandatory timeline for proposals"""

    proposal_submitted: float  # Day 0
    voting_opens: float  # Day 0
    voting_closes: float  # Day 7+ (minimum)

    # Required checkpoints
    checkpoint_25_date: float  # 25% through
    checkpoint_50_date: float  # 50% through
    checkpoint_75_date: float  # 75% through

    # Completion
    code_review_start: float  # After AI completes
    final_vote_date: float  # Before deployment
    estimated_completion: float  # Project end

    # Minimum durations (in days)
    min_total_duration: int = 7  # 1 week minimum
    min_review_period: int = 3  # 3 days for code review
    min_final_vote: int = 2  # 2 days for final vote

class EnhancedVotingSystem:
    """
    Voting system that incentivizes coin holding + donations
    """

    def __init__(self, blockchain):
        self.blockchain = blockchain

        # Vote storage
        self.proposals: dict[str, Dict] = {}
        self.voter_snapshots: dict[str, dict[str, VoterSnapshot]] = (
            {}
        )  # proposal_id -> {address -> snapshot}

        # Weight configuration
        self.coin_weight = 0.70  # 70% from coins held
        self.donation_weight = 0.30  # 30% from donations

        # Verification frequency
        self.verification_interval = 3600  # Verify every hour

        # Minimum requirements
        self.min_coins_to_vote = 1.0  # Must hold at least 1 XAI
        self.min_timeline_days = 7  # 1 week minimum

    def calculate_voting_power(
        self, address: str, ai_donation_history: Dict
    ) -> tuple[float, float, float]:
        """
        Calculate combined voting power from coins + donations

        Returns: (coin_power, donation_power, total_power)
        """

        # Get current XAI balance
        xai_balance = self.blockchain.get_balance(address)

        # Coin voting power (70% weight)
        coin_power = xai_balance * self.coin_weight

        # Donation voting power (30% weight)
        # Based on total AI minutes/tokens ever donated
        total_minutes = ai_donation_history.get("total_minutes_donated", 0)
        total_tokens = ai_donation_history.get("total_tokens_donated", 0)
        usd_value = ai_donation_history.get("total_usd_value", 0)

        # Calculate donation power
        # 1 minute = 1 voting power OR 10,000 tokens = 1 voting power OR $0.01 = 1 voting power
        # Use whichever is highest
        donation_power_from_minutes = total_minutes
        donation_power_from_tokens = total_tokens / 10000
        donation_power_from_usd = usd_value * 100

        donation_power_raw = max(
            donation_power_from_minutes, donation_power_from_tokens, donation_power_from_usd
        )

        donation_power = donation_power_raw * self.donation_weight

        # Total voting power
        total_power = coin_power + donation_power

        return (coin_power, donation_power, total_power)

    def submit_vote(
        self,
        proposal_id: str,
        voter_address: str,
        vote: str,  # 'for', 'against', 'abstain'
        ai_donation_history: Dict,
    ) -> Dict:
        """
        Submit vote with combined coin + donation power
        """

        # Check minimum coin requirement
        current_balance = self.blockchain.get_balance(voter_address)

        if current_balance < self.min_coins_to_vote:
            return {
                "success": False,
                "error": "INSUFFICIENT_COINS",
                "message": f"Must hold at least {self.min_coins_to_vote} XAI to vote",
                "current_balance": current_balance,
            }

        # Calculate voting power
        coin_power, donation_power, total_power = self.calculate_voting_power(
            voter_address, ai_donation_history
        )

        # Create voter snapshot
        snapshot = VoterSnapshot(
            address=voter_address,
            vote_time=time.time(),
            xai_balance=current_balance,
            xai_balance_block=self.blockchain.get_height(),
            total_ai_minutes_donated=ai_donation_history.get("total_minutes_donated", 0),
            total_ai_tokens_donated=ai_donation_history.get("total_tokens_donated", 0),
            ai_usd_value=ai_donation_history.get("total_usd_value", 0),
            coin_voting_power=coin_power,
            donation_voting_power=donation_power,
            total_voting_power=total_power,
            verified_until=time.time(),
            is_valid=True,
        )

        # Store snapshot
        if proposal_id not in self.voter_snapshots:
            self.voter_snapshots[proposal_id] = {}

        self.voter_snapshots[proposal_id][voter_address] = snapshot

        # Record vote
        if proposal_id not in self.proposals:
            self.proposals[proposal_id] = {
                "votes_for": 0,
                "votes_against": 0,
                "votes_abstain": 0,
                "voters": {},
                "created_at": time.time(),
            }

        # Remove old vote if re-voting
        if voter_address in self.proposals[proposal_id]["voters"]:
            old_vote = self.proposals[proposal_id]["voters"][voter_address]
            old_power = old_vote["voting_power"]

            if old_vote["vote"] == "for":
                self.proposals[proposal_id]["votes_for"] -= old_power
            elif old_vote["vote"] == "against":
                self.proposals[proposal_id]["votes_against"] -= old_power
            elif old_vote["vote"] == "abstain":
                self.proposals[proposal_id]["votes_abstain"] -= old_power

        # Add new vote
        self.proposals[proposal_id]["voters"][voter_address] = {
            "vote": vote,
            "voting_power": total_power,
            "coin_power": coin_power,
            "donation_power": donation_power,
            "timestamp": time.time(),
        }

        # Update totals
        if vote == "for":
            self.proposals[proposal_id]["votes_for"] += total_power
        elif vote == "against":
            self.proposals[proposal_id]["votes_against"] += total_power
        elif vote == "abstain":
            self.proposals[proposal_id]["votes_abstain"] += total_power

        return {
            "success": True,
            "voting_power": {
                "from_coins": coin_power,
                "from_donations": donation_power,
                "total": total_power,
            },
            "breakdown": {
                "xai_balance": current_balance,
                "ai_minutes_donated": ai_donation_history.get("total_minutes_donated", 0),
                "ai_tokens_donated": ai_donation_history.get("total_tokens_donated", 0),
                "ai_usd_value": ai_donation_history.get("total_usd_value", 0),
            },
            "vote_recorded": vote,
            "snapshot_created": True,
            "message": f"Vote recorded with {total_power:.2f} voting power "
            f"({coin_power:.2f} from coins + {donation_power:.2f} from donations)",
        }

    def verify_voter_still_holds_coins(self, proposal_id: str, voter_address: str) -> Dict:
        """
        Verify voter still holds coins from when they voted

        If they sold coins, their vote is INVALIDATED
        """

        if proposal_id not in self.voter_snapshots:
            return {"success": False, "error": "PROPOSAL_NOT_FOUND"}

        if voter_address not in self.voter_snapshots[proposal_id]:
            return {"success": False, "error": "NO_VOTE_FOUND"}

        snapshot = self.voter_snapshots[proposal_id][voter_address]

        # Get current balance
        current_balance = self.blockchain.get_balance(voter_address)

        # Check if they still hold at least as many coins as when they voted
        if current_balance < snapshot.xai_balance:
            # They sold coins! INVALIDATE VOTE
            old_power = snapshot.total_voting_power

            snapshot.is_valid = False
            snapshot.invalidation_reason = (
                f"Sold coins: had {snapshot.xai_balance}, now {current_balance}"
            )

            # Remove vote power
            voter_data = self.proposals[proposal_id]["voters"][voter_address]
            vote_type = voter_data["vote"]

            if vote_type == "for":
                self.proposals[proposal_id]["votes_for"] -= old_power
            elif vote_type == "against":
                self.proposals[proposal_id]["votes_against"] -= old_power
            elif vote_type == "abstain":
                self.proposals[proposal_id]["votes_abstain"] -= old_power

            # Mark voter as invalidated
            voter_data["invalidated"] = True
            voter_data["invalidation_reason"] = snapshot.invalidation_reason
            voter_data["voting_power"] = 0

            return {
                "success": True,
                "valid": False,
                "invalidated": True,
                "reason": snapshot.invalidation_reason,
                "vote_power_removed": old_power,
                "message": f"Vote INVALIDATED - voter sold {snapshot.xai_balance - current_balance} XAI coins",
            }

        # Still holds enough coins
        snapshot.verified_until = time.time()

        return {
            "success": True,
            "valid": True,
            "invalidated": False,
            "current_balance": current_balance,
            "original_balance": snapshot.xai_balance,
            "vote_power": snapshot.total_voting_power,
            "message": "Vote still valid - voter holds coins",
        }

    def verify_all_votes_for_proposal(self, proposal_id: str) -> Dict:
        """
        Verify ALL voters for a proposal still hold their coins

        Run this periodically throughout project lifecycle
        """

        if proposal_id not in self.voter_snapshots:
            return {"success": False, "error": "PROPOSAL_NOT_FOUND"}

        results = {
            "verified": 0,
            "invalidated": 0,
            "total_voters": len(self.voter_snapshots[proposal_id]),
            "invalid_voters": [],
            "total_power_removed": 0,
        }

        for voter_address in list(self.voter_snapshots[proposal_id].keys()):
            verification = self.verify_voter_still_holds_coins(proposal_id, voter_address)

            if verification.get("invalidated"):
                results["invalidated"] += 1
                results["invalid_voters"].append(
                    {
                        "address": voter_address,
                        "reason": verification["reason"],
                        "power_removed": verification["vote_power_removed"],
                    }
                )
                results["total_power_removed"] += verification["vote_power_removed"]
            else:
                results["verified"] += 1

        # Recalculate proposal totals after invalidations
        self._recalculate_proposal_totals(proposal_id)

        return {
            "success": True,
            "proposal_id": proposal_id,
            "results": results,
            "message": f'Verified {results["verified"]} votes, invalidated {results["invalidated"]}',
        }

    def _recalculate_proposal_totals(self, proposal_id: str):
        """Recalculate vote totals after invalidations"""

        proposal = self.proposals[proposal_id]

        # Reset totals
        votes_for = 0
        votes_against = 0
        votes_abstain = 0

        # Sum up all valid votes
        for voter_address, voter_data in proposal["voters"].items():
            if voter_data.get("invalidated", False):
                continue  # Skip invalidated votes

            power = voter_data["voting_power"]
            vote = voter_data["vote"]

            if vote == "for":
                votes_for += power
            elif vote == "against":
                votes_against += power
            elif vote == "abstain":
                votes_abstain += power

        # Update proposal
        proposal["votes_for"] = votes_for
        proposal["votes_against"] = votes_against
        proposal["votes_abstain"] = votes_abstain

    def create_mandatory_timeline(
        self, proposal_id: str, estimated_duration_days: int
    ) -> ProjectTimeline:
        """
        Create mandatory timeline with checkpoints

        Minimum 1 week, with checkpoints at 25%, 50%, 75%
        """

        # Enforce minimum
        duration_days = max(estimated_duration_days, self.min_timeline_days)

        now = time.time()
        day_seconds = 86400

        # Calculate dates
        voting_closes = now + (7 * day_seconds)  # 7 days for initial vote

        # Checkpoints during execution
        execution_start = voting_closes
        execution_duration = duration_days * day_seconds

        checkpoint_25 = execution_start + (execution_duration * 0.25)
        checkpoint_50 = execution_start + (execution_duration * 0.50)
        checkpoint_75 = execution_start + (execution_duration * 0.75)

        # Code review and final vote
        code_review_start = execution_start + execution_duration
        final_vote_date = code_review_start + (3 * day_seconds)  # 3 days for review
        estimated_completion = final_vote_date + (2 * day_seconds)  # 2 days for final vote

        timeline = ProjectTimeline(
            proposal_submitted=now,
            voting_opens=now,
            voting_closes=voting_closes,
            checkpoint_25_date=checkpoint_25,
            checkpoint_50_date=checkpoint_50,
            checkpoint_75_date=checkpoint_75,
            code_review_start=code_review_start,
            final_vote_date=final_vote_date,
            estimated_completion=estimated_completion,
            min_total_duration=duration_days,
        )

        return timeline

    def checkpoint_vote(self, proposal_id: str, checkpoint: VoteCheckpoint) -> Dict:
        """
        Run verification + re-vote at checkpoint

        Voters who sold coins lose their vote power
        Remaining voters can change their vote
        """

        # First, verify all current votes
        verification = self.verify_all_votes_for_proposal(proposal_id)

        # Calculate current approval
        proposal = self.proposals[proposal_id]
        total_votes = proposal["votes_for"] + proposal["votes_against"] + proposal["votes_abstain"]

        if total_votes > 0:
            approval_rate = proposal["votes_for"] / (
                proposal["votes_for"] + proposal["votes_against"]
            )
        else:
            approval_rate = 0

        # Check if still has support
        passing = approval_rate >= 0.66  # 66% approval needed

        return {
            "success": True,
            "checkpoint": checkpoint.value,
            "verification": verification,
            "current_votes": {
                "for": proposal["votes_for"],
                "against": proposal["votes_against"],
                "abstain": proposal["votes_abstain"],
                "total": total_votes,
            },
            "approval_rate": approval_rate * 100,
            "passing": passing,
            "message": f'Checkpoint {checkpoint.value}: {"PASSING" if passing else "FAILING"} '
            f"({approval_rate*100:.1f}% approval)",
        }

    def get_voter_power_breakdown(self, address: str, ai_donation_history: Dict) -> Dict:
        """
        Show user how their voting power is calculated
        Helps them understand the benefit of holding + donating
        """

        xai_balance = self.blockchain.get_balance(address)
        coin_power, donation_power, total_power = self.calculate_voting_power(
            address, ai_donation_history
        )

        return {
            "address": address,
            "xai_balance": xai_balance,
            "coin_voting_power": {
                "raw": xai_balance,
                "weight": self.coin_weight,
                "power": coin_power,
                "percentage": (coin_power / total_power * 100) if total_power > 0 else 0,
            },
            "donation_voting_power": {
                "minutes_donated": ai_donation_history.get("total_minutes_donated", 0),
                "tokens_donated": ai_donation_history.get("total_tokens_donated", 0),
                "usd_value": ai_donation_history.get("total_usd_value", 0),
                "weight": self.donation_weight,
                "power": donation_power,
                "percentage": (donation_power / total_power * 100) if total_power > 0 else 0,
            },
            "total_voting_power": total_power,
            "incentives": {
                "buy_1000_more_xai": f"+{1000 * self.coin_weight:.1f} voting power",
                "donate_100k_tokens": f"+{(100000/10000) * self.donation_weight:.1f} voting power",
                "donate_60_minutes": f"+{60 * self.donation_weight:.1f} voting power",
            },
        }

# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("ENHANCED VOTING SYSTEM - DEMONSTRATION")
    print("=" * 80)

    # Mock blockchain
    class MockBlockchain:
        def __init__(self):
            self.balances = {
                "XAI_Alice": 10000,  # Big holder
                "XAI_Bob": 500,  # Small holder but donated
                "XAI_Charlie": 5000,  # Medium holder
            }

        def get_balance(self, address):
            return self.balances.get(address, 0)

        def get_height(self):
            return 150000

    blockchain = MockBlockchain()
    voting = EnhancedVotingSystem(blockchain)

    print("\n" + "=" * 80)
    print("SCENARIO 1: Three voters with different profiles")
    print("=" * 80)

    voters = [
        {
            "address": "XAI_Alice",
            "profile": "Big holder, no donations",
            "ai_history": {
                "total_minutes_donated": 0,
                "total_tokens_donated": 0,
                "total_usd_value": 0,
            },
        },
        {
            "address": "XAI_Bob",
            "profile": "Small holder, BIG donor",
            "ai_history": {
                "total_minutes_donated": 5000,
                "total_tokens_donated": 50000000,
                "total_usd_value": 375,
            },
        },
        {
            "address": "XAI_Charlie",
            "profile": "Medium holder, medium donor",
            "ai_history": {
                "total_minutes_donated": 500,
                "total_tokens_donated": 5000000,
                "total_usd_value": 37.5,
            },
        },
    ]

    for voter in voters:
        print(f"\n{voter['profile']}")
        print("-" * 80)

        breakdown = voting.get_voter_power_breakdown(voter["address"], voter["ai_history"])

        print(f"XAI Balance: {breakdown['xai_balance']:,}")
        print(f"\nVoting Power Breakdown:")
        print(
            f"  From coins (70%):     {breakdown['coin_voting_power']['power']:,.1f} "
            f"({breakdown['coin_voting_power']['percentage']:.1f}%)"
        )
        print(
            f"  From donations (30%): {breakdown['donation_voting_power']['power']:,.1f} "
            f"({breakdown['donation_voting_power']['percentage']:.1f}%)"
        )
        print(f"  TOTAL:                {breakdown['total_voting_power']:,.1f}")

    print("\n\n" + "=" * 80)
    print("SCENARIO 2: Voting on proposal")
    print("=" * 80)

    proposal_id = "prop_001"

    for voter in voters:
        result = voting.submit_vote(
            proposal_id=proposal_id,
            voter_address=voter["address"],
            vote="for",
            ai_donation_history=voter["ai_history"],
        )

        print(f"\n✅ {voter['address']} voted")
        print(f"   Power: {result['voting_power']['total']:.1f}")
        print(
            f"   ({result['voting_power']['from_coins']:.1f} coins + "
            f"{result['voting_power']['from_donations']:.1f} donations)"
        )

    print("\n\n" + "=" * 80)
    print("SCENARIO 3: Alice sells coins - vote gets invalidated!")
    print("=" * 80)

    # Alice sells half her coins
    print("\n⚠️ Alice sells 5000 XAI (from 10000 → 5000)")
    blockchain.balances["XAI_Alice"] = 5000

    # Verify votes
    verification = voting.verify_all_votes_for_proposal(proposal_id)

    print(f"\n📊 Verification Results:")
    print(f"   Valid votes: {verification['results']['verified']}")
    print(f"   Invalidated: {verification['results']['invalidated']}")

    if verification["results"]["invalid_voters"]:
        for invalid in verification["results"]["invalid_voters"]:
            print(f"\n   ❌ {invalid['address']}")
            print(f"      Reason: {invalid['reason']}")
            print(f"      Power removed: {invalid['power_removed']:.1f}")

    print("\n\n" + "=" * 80)
    print("KEY BENEFITS")
    print("=" * 80)
    print(
        """
✅ Incentivizes HOLDING coins (70% of power)
   - Don't sell or lose your vote!
   - Want more power? Buy more XAI!

✅ Rewards AI donations (30% of power)
   - Donate API credits = gain voting power
   - Even small holders can have influence

✅ Continuous verification
   - Can't vote then sell immediately
   - Must hold through project completion

✅ Multiple checkpoints
   - 25%, 50%, 75% verification points
   - Project can be canceled if support drops

✅ Mandatory timeline
   - Minimum 1 week
   - Can't rush through governance
   - Proper deliberation time

Result: Strong price support + development funding!
    """
    )
