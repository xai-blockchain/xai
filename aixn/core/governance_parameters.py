"""
XAI Governance Parameters

On-chain parameters that can be changed via community vote
Standard mechanism used in crypto governance systems
"""

import time
from typing import Dict, Tuple
from enum import Enum


class ProposalType(Enum):
    """Types of governance proposals"""
    AI_IMPROVEMENT = "ai_improvement"  # AI work on blockchain code
    PARAMETER_CHANGE = "parameter_change"  # Change governance rules
    EMERGENCY = "emergency"  # Security fixes (shorter timelock)


class GovernanceParameters:
    """
    On-chain parameters that can be changed via governance vote
    Similar to Compound, Uniswap, MakerDAO governance
    """

    def __init__(self, mining_start_time: float):
        self.mining_start_time = mining_start_time

        # AI improvement restrictions
        self.ai_restriction_period_days = 90  # 3 months after mining starts
        self.ai_improvement_frequency_days = 30  # Once per month after restriction
        self.last_ai_improvement_time = None

        # Proposal submission requirements (prevents spam)
        self.min_voting_power_to_propose = 10  # Need 10 voting power to submit
        self.proposal_deposit_xai = 100  # Refunded if proposal passes

        # Timelock delays (days between approval and execution)
        # Standard in DeFi governance (Compound, Uniswap use 2-7 days)
        self.timelock_ai_improvement = 7  # 7 days
        self.timelock_parameter_change = 14  # 14 days (longer for rule changes)
        self.timelock_emergency = 1  # 1 day for security fixes

        # Voting parameters - Initial approval to START work
        self.voting_period_days = 14
        self.approval_percent = 66
        self.max_individual_power_percent = 20
        self.min_approval_voters = 10
        self.initial_min_voters = 250
        self.reduction_rate = 0.20
        self.absolute_minimum = 50
        self.revote_delay_days = 7

        # Implementation approval (after code review)
        # Must get 50% of original approvers to approve implementation
        self.implementation_approval_percent = 50  # 50% of original voters
        self.min_code_reviewers = 250  # Minimum reviewers for code review stage

    def can_submit_ai_improvement(self) -> Tuple[bool, str]:
        """Check if AI improvements are currently allowed"""

        current_time = time.time()
        restriction_end = self.mining_start_time + (self.ai_restriction_period_days * 86400)

        # Within restriction period (first 3 months)
        if current_time < restriction_end:
            days_remaining = (restriction_end - current_time) / 86400
            return False, f"AI improvements restricted for {days_remaining:.1f} more days"

        # Check frequency limit (once per month by default)
        if self.last_ai_improvement_time:
            next_allowed = self.last_ai_improvement_time + (self.ai_improvement_frequency_days * 86400)
            if current_time < next_allowed:
                days_until = (next_allowed - current_time) / 86400
                return False, f"Next AI improvement allowed in {days_until:.1f} days"

        return True, "AI improvements allowed"

    def record_ai_improvement(self):
        """Record when AI improvement was executed"""
        self.last_ai_improvement_time = time.time()

    def get_timelock_duration(self, proposal_type: ProposalType) -> int:
        """Get timelock duration in days for proposal type"""

        if proposal_type == ProposalType.AI_IMPROVEMENT:
            return self.timelock_ai_improvement
        elif proposal_type == ProposalType.PARAMETER_CHANGE:
            return self.timelock_parameter_change
        elif proposal_type == ProposalType.EMERGENCY:
            return self.timelock_emergency
        else:
            return self.timelock_ai_improvement

    def update_parameter(self, param_name: str, new_value: float) -> Dict:
        """
        Update governance parameter (called after vote passes and timelock expires)
        Similar to Compound's governance parameter changes
        """

        # Define allowed parameters with min/max ranges
        allowed_params = {
            'ai_improvement_frequency_days': (1, 365),  # 1 day to 1 year
            'timelock_ai_improvement': (1, 30),
            'timelock_parameter_change': (7, 90),
            'timelock_emergency': (1, 7),
            'approval_percent': (51, 90),
            'max_individual_power_percent': (5, 50),
            'min_approval_voters': (5, 100),
            'min_voting_power_to_propose': (1, 100),
            'proposal_deposit_xai': (0, 10000),
            'voting_period_days': (7, 30),
            'initial_min_voters': (50, 1000),
            'reduction_rate': (0.05, 0.50),
            'absolute_minimum': (10, 200)
        }

        if param_name not in allowed_params:
            return {
                'success': False,
                'error': 'PARAMETER_NOT_CHANGEABLE',
                'allowed_params': list(allowed_params.keys())
            }

        min_val, max_val = allowed_params[param_name]
        if not (min_val <= new_value <= max_val):
            return {
                'success': False,
                'error': 'VALUE_OUT_OF_RANGE',
                'min': min_val,
                'max': max_val
            }

        old_value = getattr(self, param_name)
        setattr(self, param_name, new_value)

        return {
            'success': True,
            'parameter': param_name,
            'old_value': old_value,
            'new_value': new_value
        }

    def get_all_parameters(self) -> Dict:
        """Get all current parameter values"""

        return {
            # AI restrictions
            'ai_restriction_period_days': self.ai_restriction_period_days,
            'ai_improvement_frequency_days': self.ai_improvement_frequency_days,

            # Proposal requirements
            'min_voting_power_to_propose': self.min_voting_power_to_propose,
            'proposal_deposit_xai': self.proposal_deposit_xai,

            # Timelocks
            'timelock_ai_improvement': self.timelock_ai_improvement,
            'timelock_parameter_change': self.timelock_parameter_change,
            'timelock_emergency': self.timelock_emergency,

            # Voting
            'voting_period_days': self.voting_period_days,
            'approval_percent': self.approval_percent,
            'max_individual_power_percent': self.max_individual_power_percent,
            'min_approval_voters': self.min_approval_voters,
            'initial_min_voters': self.initial_min_voters,
            'reduction_rate': self.reduction_rate,
            'absolute_minimum': self.absolute_minimum,
            'revote_delay_days': self.revote_delay_days
        }


class TimelockProposal:
    """
    Proposal in timelock queue waiting for execution
    Standard pattern in DeFi governance
    """

    def __init__(self, proposal_id: str, proposal_type: ProposalType,
                 approval_time: float, timelock_days: int, execution_data: Dict):
        self.proposal_id = proposal_id
        self.proposal_type = proposal_type
        self.approval_time = approval_time
        self.timelock_days = timelock_days
        self.execution_time = approval_time + (timelock_days * 86400)
        self.execution_data = execution_data
        self.executed = False
        self.cancelled = False

    def can_execute(self) -> bool:
        """Check if timelock has expired and proposal can execute"""
        return time.time() >= self.execution_time and not self.executed and not self.cancelled

    def days_until_execution(self) -> float:
        """Days remaining until execution allowed"""
        remaining_seconds = self.execution_time - time.time()
        return max(0, remaining_seconds / 86400)


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI GOVERNANCE PARAMETERS")
    print("=" * 70)

    # Simulate mining start (3 months ago for testing)
    mining_start = time.time() - (60 * 86400)  # 60 days ago

    params = GovernanceParameters(mining_start)

    print("\nCurrent Parameters:")
    print("-" * 70)
    all_params = params.get_all_parameters()
    for name, value in all_params.items():
        print(f"  {name}: {value}")

    # Test AI improvement restrictions
    print("\n" + "=" * 70)
    print("AI IMPROVEMENT RESTRICTIONS")
    print("-" * 70)

    can_submit, reason = params.can_submit_ai_improvement()
    print(f"\nCan submit AI improvement: {can_submit}")
    print(f"Reason: {reason}")

    # Test parameter change
    print("\n" + "=" * 70)
    print("PARAMETER CHANGE EXAMPLE")
    print("-" * 70)

    print("\nChanging ai_improvement_frequency_days from 30 to 14")
    result = params.update_parameter('ai_improvement_frequency_days', 14)
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Old value: {result['old_value']} days")
        print(f"New value: {result['new_value']} days")

    # Test timelock
    print("\n" + "=" * 70)
    print("TIMELOCK SYSTEM")
    print("-" * 70)

    timelock_proposal = TimelockProposal(
        proposal_id="prop_001",
        proposal_type=ProposalType.AI_IMPROVEMENT,
        approval_time=time.time(),
        timelock_days=params.timelock_ai_improvement,
        execution_data={'task': 'Add privacy features'}
    )

    print(f"\nProposal: {timelock_proposal.proposal_id}")
    print(f"Type: {timelock_proposal.proposal_type.value}")
    print(f"Timelock: {timelock_proposal.timelock_days} days")
    print(f"Can execute now: {timelock_proposal.can_execute()}")
    print(f"Days until execution: {timelock_proposal.days_until_execution():.1f}")

    print("\n" + "=" * 70)
