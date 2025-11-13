"""
XAI AI Governance System

Consensus mechanism for AI-driven development:
- Quadratic voting (prevents whale dominance)
- Both miners AND node operators vote
- Voting power based on AI minutes contributed
- Time-decay prevents old contributions from controlling forever
- AI workload divided proportionally among contributors
- Timelock system delays execution after approval
- Changeable governance parameters
"""

import time
import hashlib
import math
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Import governance parameters
try:
    from aixn.core.governance_parameters import GovernanceParameters, ProposalType, TimelockProposal
except ImportError:
    # Allow running standalone
    class ProposalType(Enum):
        AI_IMPROVEMENT = "ai_improvement"
        PARAMETER_CHANGE = "parameter_change"
        EMERGENCY = "emergency"


class VoterType(Enum):
    """Types of voters in governance"""
    NODE_OPERATOR = "node_operator"  # Runs node 24/7
    MINER = "miner"                   # Mines blocks
    AI_CONTRIBUTOR = "ai_contributor" # Donated AI minutes
    HYBRID = "hybrid"                 # Multiple roles


class VotingPowerDisplay:
    """
    Shows actual voting power to prevent discouragement
    Small contributors need to see they matter
    """

    @staticmethod
    def show_contribution_impact(minutes_contributed: float) -> Dict:
        """
        Show what voting power comes from contributing X minutes
        Prevents discouragement from seeing large contributors
        """

        base_power = math.sqrt(minutes_contributed)

        return {
            'minutes_contributed': minutes_contributed,
            'voting_power': base_power,
            'actual_voting_power': base_power,
            'not_1_to_1': True,
            'explanation': f"{minutes_contributed} minutes = {base_power:.1f} votes (sqrt prevents whale control)",
            'examples': {
                '1 minute': math.sqrt(1),
                '10 minutes': math.sqrt(10),
                '100 minutes': math.sqrt(100),
                '1000 minutes': math.sqrt(1000),
                '10000 minutes': min(math.sqrt(10000), 100)  # Capped
            }
        }

    @staticmethod
    def compare_contributors(contributor_minutes: List[float]) -> List[Dict]:
        """
        Show how multiple contributors compare
        Demonstrates small contributors still matter
        """

        results = []
        total_power = sum(math.sqrt(m) for m in contributor_minutes)

        for minutes in contributor_minutes:
            power = math.sqrt(minutes)
            percentage = (power / total_power * 100) if total_power > 0 else 0

            results.append({
                'minutes': minutes,
                'voting_power': power,
                'percentage_of_total': percentage
            })

        return results


class VotingPower:
    """
    Calculate voting power using quadratic voting
    Prevents whale dominance while rewarding contribution
    """

    def __init__(self):
        # Time decay: contributions lose 10% voting power per month
        self.monthly_decay_rate = 0.10

        # Caps to prevent dominance
        self.max_ai_minutes_votes = 100  # sqrt(10,000 minutes)
        self.max_mining_votes = 50       # sqrt(2,500 blocks)
        self.max_node_votes = 75         # sqrt(5,625 days)

    def calculate_ai_minutes_voting_power(self, minutes_contributed: float,
                                         contribution_timestamp: float) -> float:
        """
        Quadratic voting: sqrt of minutes contributed
        Time decay: Older contributions matter less

        Args:
            minutes_contributed: AI API minutes donated
            contribution_timestamp: When contributed

        Returns:
            Voting power (0-100)
        """

        # Quadratic scaling (sqrt prevents whale control)
        base_power = math.sqrt(minutes_contributed)

        # Apply time decay
        months_old = (time.time() - contribution_timestamp) / (30 * 86400)
        decay_factor = (1 - self.monthly_decay_rate) ** months_old

        voting_power = base_power * decay_factor

        # Cap at maximum
        return min(voting_power, self.max_ai_minutes_votes)

    def calculate_mining_voting_power(self, blocks_mined: int,
                                     last_block_timestamp: float) -> float:
        """
        Miners get votes based on blocks mined
        Recent mining activity matters more
        """

        base_power = math.sqrt(blocks_mined)

        # Decay if not mining recently
        days_since_last_block = (time.time() - last_block_timestamp) / 86400
        if days_since_last_block > 30:
            decay_factor = 0.5  # 50% power if inactive
        else:
            decay_factor = 1.0

        voting_power = base_power * decay_factor

        return min(voting_power, self.max_mining_votes)

    def calculate_node_voting_power(self, uptime_days: int,
                                   is_currently_active: bool) -> float:
        """
        Node operators get votes for running infrastructure
        """

        if not is_currently_active:
            return 0  # Must be active to vote

        base_power = math.sqrt(uptime_days)

        return min(base_power, self.max_node_votes)

    def calculate_total_voting_power(self, voter_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate total voting power across all contributions

        Returns:
            (total_power, breakdown)
        """

        breakdown = {
            'ai_minutes': 0,
            'mining': 0,
            'node_operation': 0,
            'bonus': 0
        }

        # AI minutes contribution
        if voter_data.get('ai_minutes_contributed', 0) > 0:
            breakdown['ai_minutes'] = self.calculate_ai_minutes_voting_power(
                voter_data['ai_minutes_contributed'],
                voter_data.get('ai_contribution_timestamp', time.time())
            )

        # Mining contribution
        if voter_data.get('blocks_mined', 0) > 0:
            breakdown['mining'] = self.calculate_mining_voting_power(
                voter_data['blocks_mined'],
                voter_data.get('last_block_timestamp', time.time())
            )

        # Node operation
        if voter_data.get('node_uptime_days', 0) > 0:
            breakdown['node_operation'] = self.calculate_node_voting_power(
                voter_data['node_uptime_days'],
                voter_data.get('node_active', False)
            )

        # Hybrid bonus: If contributing in multiple ways, +10% total
        active_contributions = sum(1 for v in breakdown.values() if v > 0)
        if active_contributions >= 2:
            base_total = sum(breakdown.values())
            breakdown['bonus'] = base_total * 0.10

        total = sum(breakdown.values())

        return total, breakdown


class AIWorkloadDistribution:
    """
    Distribute AI workload proportionally among contributors
    """

    def __init__(self):
        self.contributor_pool = {}  # address -> contribution data

    def add_contributor(self, address: str, ai_model: str,
                       minutes_contributed: float, timestamp: float):
        """Record AI minutes contribution"""

        if address not in self.contributor_pool:
            self.contributor_pool[address] = {
                'total_minutes': 0,
                'contributions': [],
                'tasks_completed': 0,
                'quality_score': 1.0
            }

        self.contributor_pool[address]['total_minutes'] += minutes_contributed
        self.contributor_pool[address]['contributions'].append({
            'ai_model': ai_model,
            'minutes': minutes_contributed,
            'timestamp': timestamp
        })

    def calculate_workload_shares(self, total_task_minutes: float) -> Dict:
        """
        Divide AI workload among contributors proportionally

        Example:
        Alice donated 100 minutes (50%)
        Bob donated 60 minutes (30%)
        Carol donated 40 minutes (20%)

        Task requires 20 minutes total:
        Alice does 10 minutes (50%)
        Bob does 6 minutes (30%)
        Carol does 4 minutes (20%)
        """

        total_pool = sum(c['total_minutes'] for c in self.contributor_pool.values())

        if total_pool == 0:
            return {}

        workload = {}

        for address, data in self.contributor_pool.items():
            share_percentage = data['total_minutes'] / total_pool
            assigned_minutes = total_task_minutes * share_percentage

            workload[address] = {
                'minutes_assigned': assigned_minutes,
                'share_percentage': share_percentage * 100,
                'total_contributed': data['total_minutes'],
                'quality_score': data['quality_score']
            }

        return workload

    def execute_distributed_task(self, task_description: str,
                                 total_estimated_minutes: float) -> Dict:
        """
        Execute AI task using distributed workload

        Each contributor's AI works on the task proportionally
        Results merged together
        """

        workload = self.calculate_workload_shares(total_estimated_minutes)

        execution_plan = {
            'task': task_description,
            'total_minutes': total_estimated_minutes,
            'contributor_assignments': []
        }

        for address, assignment in workload.items():
            execution_plan['contributor_assignments'].append({
                'contributor': address,
                'minutes_allocated': assignment['minutes_assigned'],
                'percentage': assignment['share_percentage'],
                'ai_model': self._get_best_model_for_contributor(address),
                'status': 'pending'
            })

        return execution_plan

    def _get_best_model_for_contributor(self, address: str) -> str:
        """Get most recent AI model contributor used"""

        contribs = self.contributor_pool[address]['contributions']
        if contribs:
            return contribs[-1]['ai_model']
        return 'claude-sonnet-4'


class ConsensusRules:
    """
    Dynamic consensus system that adapts to community size
    Prevents whale control through power caps and approval voter count
    """

    def __init__(self):
        # Single approval threshold
        self.approval_percent = 66  # Supermajority

        # Anti-whale protections
        self.max_individual_power_percent = 20  # No single voter > 20% of total
        self.min_approval_voters = 10  # At least 10 different "yes" votes required

        # Dynamic minimum voters
        self.initial_min_voters = 250
        self.reduction_rate = 0.20  # Lower by 20% each failed vote
        self.absolute_minimum = 50  # Never go below 50 voters
        self.revote_delay_days = 7  # Wait 7 days before revote

    def _apply_power_caps(self, votes: Dict) -> Dict:
        """
        Cap individual voting power to prevent whale control
        Returns adjusted votes
        """

        total_power = sum(v['voting_power'] for v in votes.values())
        max_allowed_power = total_power * (self.max_individual_power_percent / 100)

        adjusted_votes = {}
        for address, vote_data in votes.items():
            adjusted_power = min(vote_data['voting_power'], max_allowed_power)
            adjusted_votes[address] = {
                'vote': vote_data['vote'],
                'voting_power': adjusted_power,
                'original_power': vote_data['voting_power'],
                'capped': adjusted_power < vote_data['voting_power']
            }

        return adjusted_votes

    def check_consensus_reached(self, proposal: Dict, votes: Dict,
                                current_min_voters: int = None) -> Tuple[bool, str, Dict]:
        """
        Check if proposal reached consensus

        Returns:
            (consensus_reached, reason, next_action)
        """

        if current_min_voters is None:
            current_min_voters = self.initial_min_voters

        # Apply power caps to prevent whale control
        adjusted_votes = self._apply_power_caps(votes)

        # Count votes with adjusted power
        total_voting_power = sum(v['voting_power'] for v in adjusted_votes.values())
        approval_power = sum(v['voting_power'] for v in adjusted_votes.values() if v['vote'] == 'yes')
        approval_voter_count = sum(1 for v in adjusted_votes.values() if v['vote'] == 'yes')
        voter_count = len(adjusted_votes)

        # Check minimum voters
        if voter_count < current_min_voters:
            # Calculate next threshold
            next_min_voters = max(
                int(current_min_voters * (1 - self.reduction_rate)),
                self.absolute_minimum
            )

            return False, f"Need {current_min_voters} voters, have {voter_count}", {
                'action': 'revote',
                'wait_days': self.revote_delay_days,
                'next_min_voters': next_min_voters,
                'reason': 'insufficient_turnout'
            }

        # Check minimum approval voters (prevents single whale from deciding)
        if approval_voter_count < self.min_approval_voters:
            return False, f"Need {self.min_approval_voters} different 'yes' votes, have {approval_voter_count}", {
                'action': 'rejected',
                'reason': 'insufficient_approval_diversity'
            }

        # Check approval percentage
        approval_percent = (approval_power / total_voting_power * 100) if total_voting_power > 0 else 0

        if approval_percent < self.approval_percent:
            return False, f"Need {self.approval_percent}% approval, have {approval_percent:.1f}%", {
                'action': 'rejected',
                'reason': 'insufficient_approval'
            }

        return True, f"Consensus reached: {approval_percent:.1f}% approval from {voter_count} voters", {
            'action': 'approved',
            'approval_percent': approval_percent,
            'voter_count': voter_count,
            'approval_voter_count': approval_voter_count
        }


class AIGovernanceProposal:
    """Proposal with adaptive voting and timelock"""

    def __init__(self, title: str, category: str, description: str,
                 detailed_prompt: str, estimated_minutes: float,
                 proposal_type: ProposalType = ProposalType.AI_IMPROVEMENT,
                 parameter_change: Optional[Dict] = None,
                 submitter_address: str = None,
                 submitter_voting_power: float = 0):
        self.proposal_id = hashlib.sha256(f"{title}{time.time()}".encode()).hexdigest()[:16]
        self.title = title
        self.category = category
        self.description = description
        self.detailed_prompt = detailed_prompt
        self.estimated_minutes = estimated_minutes
        self.proposal_type = proposal_type
        self.parameter_change = parameter_change  # For PARAMETER_CHANGE type
        self.submitter_address = submitter_address
        self.submitter_voting_power = submitter_voting_power

        self.votes = {}  # address -> vote data
        self.status = 'proposed'
        self.created_at = time.time()

        # Community estimation process
        self.time_estimates = {}  # address -> estimated_minutes
        self.consensus_time_estimate = estimated_minutes

        # Adaptive voting tracking
        self.vote_attempts = []  # List of vote attempts
        self.current_min_voters = 250  # Start at initial threshold
        self.next_vote_time = None

        # Timelock tracking
        self.approval_time = None
        self.timelock_expiry = None
        self.timelock_days = None

        self.execution_result = None
        self.code_review_status = None

    def cast_vote(self, voter_address: str, vote: str, voting_power: float):
        """Record vote with voting power"""

        self.votes[voter_address] = {
            'vote': vote,  # 'yes', 'no', 'abstain'
            'voting_power': voting_power,
            'timestamp': time.time()
        }

    def submit_time_estimate(self, voter_address: str, estimated_minutes: float,
                            voter_power: float) -> Dict:
        """
        Community members estimate AI work time
        Weighted by voting power to prevent spam
        """

        if estimated_minutes <= 0:
            return {
                'success': False,
                'error': 'Invalid estimate'
            }

        self.time_estimates[voter_address] = {
            'minutes': estimated_minutes,
            'voting_power': voter_power,
            'timestamp': time.time()
        }

        # Recalculate weighted average
        total_weight = sum(e['voting_power'] for e in self.time_estimates.values())
        weighted_sum = sum(e['minutes'] * e['voting_power'] for e in self.time_estimates.values())

        self.consensus_time_estimate = weighted_sum / total_weight if total_weight > 0 else self.estimated_minutes

        return {
            'success': True,
            'your_estimate': estimated_minutes,
            'community_average': self.consensus_time_estimate,
            'estimate_count': len(self.time_estimates)
        }

    def close_vote_attempt(self, consensus_rules: 'ConsensusRules') -> Dict:
        """
        Close current vote attempt and determine next action
        """

        reached, reason, next_action = consensus_rules.check_consensus_reached(
            {'title': self.title, 'category': self.category},
            self.votes,
            self.current_min_voters
        )

        # Record this attempt
        self.vote_attempts.append({
            'timestamp': time.time(),
            'voter_count': len(self.votes),
            'min_required': self.current_min_voters,
            'result': 'passed' if reached else 'failed',
            'reason': reason
        })

        if next_action['action'] == 'revote':
            # Schedule revote with lower threshold
            self.current_min_voters = next_action['next_min_voters']
            self.next_vote_time = time.time() + (next_action['wait_days'] * 86400)
            self.votes = {}  # Clear votes for fresh start
            self.status = 'revote_scheduled'

            return {
                'result': 'revote_scheduled',
                'next_min_voters': self.current_min_voters,
                'next_vote_time': self.next_vote_time,
                'wait_days': next_action['wait_days'],
                'attempt_number': len(self.vote_attempts)
            }

        elif next_action['action'] == 'approved':
            self.status = 'approved_timelock'
            self.approval_time = time.time()
            return {
                'result': 'approved_timelock',
                'approval_percent': next_action['approval_percent'],
                'voter_count': next_action['voter_count'],
                'approval_voter_count': next_action.get('approval_voter_count', 0),
                'attempt_number': len(self.vote_attempts),
                'message': 'Approved - timelock activated'
            }

        else:  # rejected
            self.status = 'rejected'
            return {
                'result': 'rejected',
                'reason': next_action['reason'],
                'attempt_number': len(self.vote_attempts)
            }

    def activate_timelock(self, governance_params: 'GovernanceParameters') -> Dict:
        """
        Activate timelock after approval
        Standard mechanism: delay between approval and execution
        """

        if self.status != 'approved_timelock':
            return {
                'success': False,
                'error': 'Proposal not in approved state'
            }

        self.timelock_days = governance_params.get_timelock_duration(self.proposal_type)
        self.timelock_expiry = self.approval_time + (self.timelock_days * 86400)
        self.status = 'timelock_active'

        return {
            'success': True,
            'timelock_days': self.timelock_days,
            'timelock_expiry': self.timelock_expiry,
            'can_execute_at': self.timelock_expiry
        }

    def can_execute(self) -> Tuple[bool, str]:
        """Check if proposal can be executed"""

        if self.status != 'timelock_active':
            return False, f"Status is {self.status}, not timelock_active"

        if time.time() < self.timelock_expiry:
            days_remaining = (self.timelock_expiry - time.time()) / 86400
            return False, f"Timelock active for {days_remaining:.1f} more days"

        return True, "Ready for execution"

    def get_vote_summary(self) -> Dict:
        """Get current vote tallies"""

        yes_power = sum(v['voting_power'] for v in self.votes.values() if v['vote'] == 'yes')
        no_power = sum(v['voting_power'] for v in self.votes.values() if v['vote'] == 'no')
        abstain_power = sum(v['voting_power'] for v in self.votes.values() if v['vote'] == 'abstain')
        total_power = yes_power + no_power + abstain_power

        return {
            'yes_power': yes_power,
            'no_power': no_power,
            'abstain_power': abstain_power,
            'total_power': total_power,
            'yes_percent': (yes_power / total_power * 100) if total_power > 0 else 0,
            'voter_count': len(self.votes),
            'min_voters_needed': self.current_min_voters,
            'vote_attempt': len(self.vote_attempts) + 1
        }



class AIGovernance:
    """Simplified AI governance facade used by the pytest suite."""

    def __init__(self):
        self.proposals: Dict[str, Dict] = {}
        self.parameters: Dict[str, float] = {
            'quorum': 0.5,
            'timelock_days': 1.0
        }
        self.voter_type_weights = {
            VoterType.NODE_OPERATOR: 1.25,
            VoterType.MINER: 1.0,
            VoterType.AI_CONTRIBUTOR: 1.1,
            VoterType.HYBRID: 1.3
        }

    def _generate_proposal_id(self, title: str, proposer: str) -> str:
        seed = f"{title}-{proposer}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def create_proposal(self, proposer_address: str, title: str,
                        description: str, proposal_type: str = "ai_improvement") -> str:
        """Create a proposal record."""
        proposal_id = self._generate_proposal_id(title, proposer_address)
        timelock_seconds = self.parameters.get('timelock_days', 1.0) * 86400
        proposal = {
            'proposal_id': proposal_id,
            'title': title,
            'description': description,
            'proposer': proposer_address,
            'proposal_type': proposal_type,
            'status': 'active',
            'votes': {},
            'timelock': time.time() + timelock_seconds,
            'execution_time': None,
            'last_tally': None
        }
        self.proposals[proposal_id] = proposal
        return proposal_id

    def cast_vote(self, proposal_id: str, voter_address: str,
                  vote: str, voting_power: float) -> bool:
        """Record votes and guard against double voting."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False

        if voter_address in proposal['votes']:
            return False

        proposal['votes'][voter_address] = {
            'vote': vote,
            'voting_power': voting_power,
            'timestamp': time.time()
        }
        return True

    def calculate_quadratic_power(self, amount: float) -> float:
        return math.sqrt(max(amount, 0.0))

    def calculate_voting_power(self, amount: float, days_ago: int = 0) -> float:
        base = self.calculate_quadratic_power(amount)
        decay = max(0.1, 1 - (days_ago / 365) * 0.1)
        return base * decay

    def get_voter_type_weight(self, voter_type: VoterType) -> float:
        return self.voter_type_weights.get(voter_type, 1.0)

    def tally_votes(self, proposal_id: str) -> Dict:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {'passed': False}

        yes_power = sum(
            v['voting_power'] for v in proposal['votes'].values() if v['vote'] == 'yes'
        )
        no_power = sum(
            v['voting_power'] for v in proposal['votes'].values() if v['vote'] == 'no'
        )
        passed = yes_power > no_power and yes_power > 0

        result = {
            'passed': passed,
            'yes_power': yes_power,
            'no_power': no_power,
            'votes': len(proposal['votes'])
        }

        proposal['status'] = 'passed' if passed else 'failed'
        proposal['last_tally'] = result
        return result

    def execute_proposal(self, proposal_id: str) -> Optional[Dict]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        result = self.tally_votes(proposal_id)
        if not result['passed']:
            return {'status': 'failed', 'executed': False}

        if time.time() < proposal['timelock']:
            return {'status': 'timelock_pending', 'ready_at': proposal['timelock']}

        proposal['execution_time'] = time.time()
        proposal['status'] = 'executed'
        return {'status': 'executed', 'executed': True}

    def get_parameters(self) -> Dict[str, float]:
        return dict(self.parameters)

    def update_parameter(self, key: str, value: float) -> bool:
        self.parameters[key] = value
        return True


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("XAI AI GOVERNANCE SYSTEM")
    print("=" * 70)

    # Show voting power transparency
    print("\nVOTING POWER TRANSPARENCY")
    print("-" * 70)
    print("Small contributors: Don't be discouraged!")
    print("100 minutes donated does NOT = 100 votes")
    print()

    display = VotingPowerDisplay()

    # Show examples
    for minutes in [1, 10, 100, 1000, 10000]:
        impact = display.show_contribution_impact(minutes)
        print(f"{minutes:5} minutes = {impact['actual_voting_power']:6.2f} votes")

    # Compare small vs large contributors
    print("\nCOMPARISON: Small vs Whale Contributors (Before Caps)")
    print("-" * 70)

    comparison = display.compare_contributors([10, 50, 100, 5000])
    for c in comparison:
        print(f"  {c['minutes']:5} minutes = {c['voting_power']:6.2f} votes ({c['percentage_of_total']:5.2f}% uncapped)")

    print("\nBefore caps: Person with 5000 minutes has 77.75% power")
    print("After 20% cap: Maximum 20% of total voting power per person")
    print("Also requires: Minimum 10 different 'yes' voters to pass")
    print("Result: No single person can control votes!")

    # Test voting power calculation
    print("\n" + "=" * 70)
    print("VOTING POWER CALCULATION")
    print("-" * 70)

    vp = VotingPower()

    # Example voters
    alice_data = {
        'ai_minutes_contributed': 500,
        'ai_contribution_timestamp': time.time() - (15 * 86400),  # 15 days ago
        'blocks_mined': 100,
        'last_block_timestamp': time.time() - (5 * 86400),
        'node_uptime_days': 60,
        'node_active': True
    }

    alice_power, alice_breakdown = vp.calculate_total_voting_power(alice_data)

    print("\nAlice (Hybrid Contributor):")
    print(f"  AI Minutes: {alice_breakdown['ai_minutes']:.2f} votes")
    print(f"  Mining: {alice_breakdown['mining']:.2f} votes")
    print(f"  Node Operation: {alice_breakdown['node_operation']:.2f} votes")
    print(f"  Hybrid Bonus: {alice_breakdown['bonus']:.2f} votes")
    print(f"  TOTAL VOTING POWER: {alice_power:.2f}")

    # Whale attempt
    whale_data = {
        'ai_minutes_contributed': 10000,  # Massive contribution
        'ai_contribution_timestamp': time.time(),
        'blocks_mined': 0,
        'node_uptime_days': 0,
        'node_active': False
    }

    whale_power, whale_breakdown = vp.calculate_total_voting_power(whale_data)

    print("\nWhale (10,000 AI minutes, nothing else):")
    print(f"  AI Minutes: {whale_breakdown['ai_minutes']:.2f} votes (capped at 100)")
    print(f"  TOTAL VOTING POWER: {whale_power:.2f}")
    print(f"  Note: Quadratic voting prevents dominance!")

    # Test workload distribution
    print("\n" + "=" * 70)
    print("WORKLOAD DISTRIBUTION")
    print("-" * 70)

    workload = AIWorkloadDistribution()
    workload.add_contributor("alice", "claude-sonnet-4", 500, time.time())
    workload.add_contributor("bob", "gpt-4-turbo", 300, time.time())
    workload.add_contributor("carol", "gemini-pro", 200, time.time())

    task_plan = workload.execute_distributed_task(
        "Add privacy features to wallet",
        total_estimated_minutes=50
    )

    print(f"\nTask: {task_plan['task']}")
    print(f"Total Minutes: {task_plan['total_minutes']}")
    print("\nContributor Assignments:")
    for assignment in task_plan['contributor_assignments']:
        print(f"  {assignment['contributor']}: {assignment['minutes_allocated']:.1f} min ({assignment['percentage']:.1f}%)")

    # Test community time estimation
    print("\n" + "=" * 70)
    print("COMMUNITY TIME ESTIMATION")
    print("-" * 70)

    proposal_obj = AIGovernanceProposal(
        title="Add zero-knowledge proof support",
        category="new_features",
        description="Implement zkSNARKs for enhanced privacy",
        detailed_prompt="Add zkSNARK support using libsnark library",
        estimated_minutes=200,
        estimator_address="proposer_1"
    )

    print(f"\nProposal: {proposal_obj.title}")
    print(f"Initial Estimate: {proposal_obj.estimated_minutes} minutes (by proposer)")
    print("\nCommunity members submit their estimates:")

    # Community members estimate time (weighted by voting power)
    est1 = proposal_obj.submit_time_estimate("alice", 180, alice_power)
    print(f"  Alice ({alice_power:.1f} votes): 180 min -> Community avg: {est1['community_average']:.1f}")

    est2 = proposal_obj.submit_time_estimate("bob", 250, 45.3)
    print(f"  Bob (45.3 votes): 250 min -> Community avg: {est2['community_average']:.1f}")

    est3 = proposal_obj.submit_time_estimate("carol", 220, 23.1)
    print(f"  Carol (23.1 votes): 220 min -> Community avg: {est3['community_average']:.1f}")

    print(f"\nConsensus Estimate: {proposal_obj.consensus_time_estimate:.1f} minutes (weighted by voting power)")
    print("Prevents single person from manipulating time estimates")

    # Test adaptive voting system
    print("\n" + "=" * 70)
    print("ADAPTIVE VOTING SYSTEM")
    print("-" * 70)

    consensus = ConsensusRules()

    vote_proposal = AIGovernanceProposal(
        title="Add new atomic swap pair",
        category="new_features",
        description="Add XAI/SOL trading pair",
        detailed_prompt="Implement Solana atomic swap support",
        estimated_minutes=150
    )

    print(f"\nProposal: {vote_proposal.title}")
    print(f"Required Approval: {consensus.approval_percent}%")
    print(f"Initial Min Voters: {vote_proposal.current_min_voters}")

    # Vote Attempt 1: Only 100 voters (not enough)
    print("\n--- Vote Attempt 1 ---")
    for i in range(100):
        vote_proposal.cast_vote(f"voter_{i}", "yes" if i < 70 else "no", 5.0)

    summary1 = vote_proposal.get_vote_summary()
    print(f"Voters: {summary1['voter_count']} / {summary1['min_voters_needed']} needed")
    print(f"Approval: {summary1['yes_percent']:.1f}%")

    result1 = vote_proposal.close_vote_attempt(consensus)
    print(f"Result: {result1['result']}")
    if result1['result'] == 'revote_scheduled':
        print(f"Next threshold: {result1['next_min_voters']} voters")
        print(f"Wait: {result1['wait_days']} days")

    # Vote Attempt 2: 150 voters (still not enough for new threshold of 200)
    print("\n--- Vote Attempt 2 (After 7 days) ---")
    for i in range(150):
        vote_proposal.cast_vote(f"voter_{i}", "yes" if i < 100 else "no", 5.0)

    summary2 = vote_proposal.get_vote_summary()
    print(f"Voters: {summary2['voter_count']} / {summary2['min_voters_needed']} needed")
    print(f"Approval: {summary2['yes_percent']:.1f}%")

    result2 = vote_proposal.close_vote_attempt(consensus)
    print(f"Result: {result2['result']}")
    if result2['result'] == 'revote_scheduled':
        print(f"Next threshold: {result2['next_min_voters']} voters")
        print(f"Wait: {result2['wait_days']} days")

    # Vote Attempt 3: 165 voters (enough for threshold of 160)
    print("\n--- Vote Attempt 3 (After another 7 days) ---")
    for i in range(165):
        vote_proposal.cast_vote(f"voter_{i}", "yes" if i < 110 else "no", 5.0)

    summary3 = vote_proposal.get_vote_summary()
    print(f"Voters: {summary3['voter_count']} / {summary3['min_voters_needed']} needed")
    print(f"Approval: {summary3['yes_percent']:.1f}%")

    result3 = vote_proposal.close_vote_attempt(consensus)
    print(f"Result: {result3['result']}")
    if result3['result'] == 'approved':
        print(f"PASSED with {result3['approval_percent']:.1f}% approval")
        print(f"Took {result3['attempt_number']} attempts")

    print("\n" + "=" * 70)
    print("WHALE CONTROL PREVENTION")
    print("-" * 70)

    # Test whale trying to control vote
    whale_proposal = AIGovernanceProposal(
        title="Test whale control",
        category="test",
        description="Can whale control vote?",
        detailed_prompt="Test",
        estimated_minutes=100
    )

    # Whale has 77.75% of total power (like in comparison example)
    # 9 small voters + 1 whale
    for i in range(9):
        whale_proposal.cast_vote(f"small_voter_{i}", "no", 2.5)  # Total: 22.5 power

    whale_proposal.cast_vote("whale", "yes", 70.71)  # 77.75% of 91 total power

    print("\nScenario: Whale has 70.71 votes, 9 others have 2.5 each (22.5 total)")
    print(f"Whale's share: 77.75% of voting power")
    print(f"Approval threshold: {consensus.approval_percent}%")
    print(f"Max individual power: {consensus.max_individual_power_percent}%")
    print(f"Min approval voters: {consensus.min_approval_voters}")

    # Set minimum to 10 so we can test
    whale_proposal.current_min_voters = 10

    result_whale = whale_proposal.close_vote_attempt(consensus)
    print(f"\nResult: {result_whale['result']}")
    if result_whale['result'] == 'rejected':
        print(f"Reason: {result_whale['reason']}")
        print("WHALE CANNOT CONTROL VOTE ALONE!")
    else:
        print("ERROR: Whale controlled the vote!")

    # Now test with proper distribution
    print("\n--- Proper Distribution Test ---")
    proper_proposal = AIGovernanceProposal(
        title="Test proper voting",
        category="test",
        description="Distributed voting power",
        detailed_prompt="Test",
        estimated_minutes=100
    )
    proper_proposal.current_min_voters = 15

    # 15 voters with distributed power
    for i in range(10):
        proper_proposal.cast_vote(f"voter_{i}", "yes", 8.0)  # 80 power

    for i in range(5):
        proper_proposal.cast_vote(f"voter_no_{i}", "no", 5.0)  # 25 power

    # Total: 105 power, 76.2% approval, 10 yes voters
    result_proper = proper_proposal.close_vote_attempt(consensus)
    print(f"15 voters, distributed power (10 yes, 5 no)")
    print(f"Result: {result_proper['result']}")
    if result_proper['result'] == 'approved':
        print(f"PASSED with {result_proper['approval_percent']:.1f}% from {result_proper['approval_voter_count']} yes voters")

    print("\n" + "=" * 70)
    print("ADAPTIVE THRESHOLD SUMMARY")
    print("-" * 70)
    print(f"Approval required: {consensus.approval_percent}%")
    print(f"Max individual power: {consensus.max_individual_power_percent}%")
    print(f"Min approval voters: {consensus.min_approval_voters}")
    print(f"Initial minimum: {consensus.initial_min_voters} voters")
    print(f"Reduction per failed vote: {consensus.reduction_rate * 100}%")
    print(f"Absolute minimum: {consensus.absolute_minimum} voters")
    print(f"Revote delay: {consensus.revote_delay_days} days")

    print("\n" + "=" * 70)
