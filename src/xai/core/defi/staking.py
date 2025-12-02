"""
Staking Protocol Implementation.

Provides comprehensive staking functionality with:
- Token staking with rewards
- Delegation to validators
- Slashing mechanism
- Unbonding periods
- Reward distribution

Security features:
- Slashing conditions
- Lock periods
- Withdrawal delays
- Validator jailing
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum

from ..vm.exceptions import VMExecutionError
from .access_control import AccessControl, SignedRequest, RoleBasedAccessControl, Role

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


class ValidatorStatus(Enum):
    """Validator status."""
    ACTIVE = "active"
    UNBONDING = "unbonding"
    JAILED = "jailed"
    INACTIVE = "inactive"


@dataclass
class Validator:
    """Validator information."""

    address: str
    name: str
    commission: int  # Commission rate (basis points)

    # Staking
    self_stake: int = 0
    delegated_stake: int = 0

    # Status
    status: ValidatorStatus = ValidatorStatus.INACTIVE
    jailed_until: float = 0.0

    # Performance
    blocks_proposed: int = 0
    blocks_missed: int = 0
    slashing_events: int = 0

    # Rewards
    accumulated_rewards: int = 0

    @property
    def total_stake(self) -> int:
        """Total stake (self + delegated)."""
        return self.self_stake + self.delegated_stake

    @property
    def is_active(self) -> bool:
        """Check if validator is active."""
        return self.status == ValidatorStatus.ACTIVE


@dataclass
class Delegation:
    """Delegation from a staker to a validator."""

    delegator: str
    validator: str
    amount: int
    shares: int  # Delegation shares
    start_time: float = field(default_factory=time.time)

    # Unbonding
    unbonding_amount: int = 0
    unbonding_completion: float = 0.0

    # Rewards tracking
    accumulated_rewards: int = 0  # Unclaimed delegator rewards


@dataclass
class StakingPool:
    """
    Complete staking pool implementation.

    Features:
    - Stake tokens to earn rewards
    - Delegate to validators
    - Slashing for misbehavior
    - Unbonding period
    - Compound rewards

    Security features:
    - Slashing mechanism
    - Validator jailing
    - Unbonding delays
    - Minimum stake requirements
    """

    name: str = "XAI Staking"
    address: str = ""
    owner: str = ""

    # Token configuration
    staking_token: str = "XAI"

    # Validators
    validators: Dict[str, Validator] = field(default_factory=dict)
    max_validators: int = 100
    min_self_stake: int = 10000 * 10**18  # Minimum self-stake to be validator

    # Delegations: delegator -> validator -> Delegation
    delegations: Dict[str, Dict[str, Delegation]] = field(default_factory=dict)

    # Unbonding period (seconds)
    unbonding_period: int = 21 * 24 * 3600  # 21 days

    # Slashing parameters (basis points)
    slash_fraction_downtime: int = 100  # 1%
    slash_fraction_double_sign: int = 500  # 5%

    # Rewards
    reward_rate: int = 500  # 5% APY (basis points)
    total_rewards_distributed: int = 0

    # Pool state
    total_staked: int = 0
    total_shares: int = 0

    # Minimum stake
    min_delegation: int = 100 * 10**18  # 100 tokens minimum

    # Constants
    BASIS_POINTS: int = 10000
    PRECISION: int = 10**18

    # Access control with signature verification
    access_control: AccessControl = field(default_factory=AccessControl)
    rbac: Optional[RoleBasedAccessControl] = None

    def __post_init__(self) -> None:
        """Initialize pool."""
        if not self.address:
            import hashlib
            addr_hash = hashlib.sha3_256(f"{self.name}{time.time()}".encode()).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

        # Initialize RBAC with owner as admin
        if self.owner and not self.rbac:
            self.rbac = RoleBasedAccessControl(
                access_control=self.access_control,
                admin_address=self.owner,
            )

    # ==================== Validator Management ====================

    def register_validator(
        self,
        caller: str,
        name: str,
        commission: int,
        self_stake: int,
    ) -> bool:
        """
        Register as a validator.

        Args:
            caller: Validator address
            name: Validator name
            commission: Commission rate (basis points)
            self_stake: Initial self-stake amount

        Returns:
            True if successful
        """
        caller_norm = self._normalize(caller)

        if caller_norm in self.validators:
            raise VMExecutionError("Already registered as validator")

        if len(self.validators) >= self.max_validators:
            raise VMExecutionError("Max validators reached")

        if commission > self.BASIS_POINTS:
            raise VMExecutionError("Commission cannot exceed 100%")

        if self_stake < self.min_self_stake:
            raise VMExecutionError(
                f"Self-stake below minimum: {self_stake} < {self.min_self_stake}"
            )

        # Create validator
        validator = Validator(
            address=caller_norm,
            name=name,
            commission=commission,
            self_stake=self_stake,
            status=ValidatorStatus.ACTIVE,
        )

        self.validators[caller_norm] = validator
        self.total_staked += self_stake

        logger.info(
            "Validator registered",
            extra={
                "event": "staking.validator_registered",
                "validator": caller_norm[:10],
                "validator_name": name,
                "self_stake": self_stake,
            }
        )

        return True

    def update_commission(self, caller: str, new_commission: int) -> bool:
        """Update validator commission rate."""
        caller_norm = self._normalize(caller)
        self._require_validator(caller_norm)

        if new_commission > self.BASIS_POINTS:
            raise VMExecutionError("Commission cannot exceed 100%")

        # Could add rate limiting on commission changes
        self.validators[caller_norm].commission = new_commission
        return True

    # ==================== Delegation ====================

    def delegate(
        self,
        caller: str,
        validator: str,
        amount: int,
    ) -> bool:
        """
        Delegate stake to a validator.

        Args:
            caller: Delegator address
            validator: Validator address
            amount: Amount to delegate

        Returns:
            True if successful
        """
        caller_norm = self._normalize(caller)
        validator_norm = self._normalize(validator)

        self._require_validator(validator_norm)

        if amount < self.min_delegation:
            raise VMExecutionError(
                f"Delegation below minimum: {amount} < {self.min_delegation}"
            )

        val = self.validators[validator_norm]

        if not val.is_active:
            raise VMExecutionError(f"Validator {validator} is not active")

        # Calculate shares
        if val.delegated_stake == 0:
            shares = amount
        else:
            # Get existing delegations total shares for this validator
            existing_shares = self._get_validator_total_shares(validator_norm)
            shares = (amount * existing_shares) // val.delegated_stake if existing_shares > 0 else amount

        # Create or update delegation
        if caller_norm not in self.delegations:
            self.delegations[caller_norm] = {}

        if validator_norm in self.delegations[caller_norm]:
            # Add to existing delegation
            delegation = self.delegations[caller_norm][validator_norm]
            delegation.amount += amount
            delegation.shares += shares
        else:
            # New delegation
            self.delegations[caller_norm][validator_norm] = Delegation(
                delegator=caller_norm,
                validator=validator_norm,
                amount=amount,
                shares=shares,
            )

        # Update validator
        val.delegated_stake += amount
        self.total_staked += amount
        self.total_shares += shares

        logger.info(
            "Stake delegated",
            extra={
                "event": "staking.delegated",
                "delegator": caller_norm[:10],
                "validator": validator_norm[:10],
                "amount": amount,
            }
        )

        return True

    def undelegate(
        self,
        caller: str,
        validator: str,
        amount: int,
    ) -> bool:
        """
        Undelegate stake from a validator.

        Starts unbonding period.

        Args:
            caller: Delegator address
            validator: Validator address
            amount: Amount to undelegate

        Returns:
            True if successful
        """
        caller_norm = self._normalize(caller)
        validator_norm = self._normalize(validator)

        delegation = self._get_delegation(caller_norm, validator_norm)
        if not delegation:
            raise VMExecutionError("No delegation found")

        if amount > delegation.amount:
            raise VMExecutionError(
                f"Undelegate amount exceeds delegation: {amount} > {delegation.amount}"
            )

        val = self.validators[validator_norm]

        # Calculate shares to remove
        shares_to_remove = (amount * delegation.shares) // delegation.amount

        # Update delegation
        delegation.amount -= amount
        delegation.shares -= shares_to_remove

        # Start unbonding
        delegation.unbonding_amount += amount
        delegation.unbonding_completion = time.time() + self.unbonding_period

        # Update validator
        val.delegated_stake -= amount
        self.total_staked -= amount
        self.total_shares -= shares_to_remove

        logger.info(
            "Stake undelegated",
            extra={
                "event": "staking.undelegated",
                "delegator": caller_norm[:10],
                "validator": validator_norm[:10],
                "amount": amount,
                "completion_time": delegation.unbonding_completion,
            }
        )

        return True

    def withdraw_unbonded(self, caller: str, validator: str) -> int:
        """
        Withdraw unbonded stake after unbonding period.

        Args:
            caller: Delegator address
            validator: Validator address

        Returns:
            Amount withdrawn
        """
        caller_norm = self._normalize(caller)
        validator_norm = self._normalize(validator)

        delegation = self._get_delegation(caller_norm, validator_norm)
        if not delegation:
            raise VMExecutionError("No delegation found")

        if delegation.unbonding_amount == 0:
            raise VMExecutionError("No unbonding stake")

        if time.time() < delegation.unbonding_completion:
            remaining = delegation.unbonding_completion - time.time()
            raise VMExecutionError(
                f"Unbonding not complete: {remaining:.0f}s remaining"
            )

        amount = delegation.unbonding_amount
        delegation.unbonding_amount = 0
        delegation.unbonding_completion = 0

        logger.info(
            "Unbonded stake withdrawn",
            extra={
                "event": "staking.withdrawn",
                "delegator": caller_norm[:10],
                "amount": amount,
            }
        )

        return amount

    def redelegate(
        self,
        caller: str,
        src_validator: str,
        dst_validator: str,
        amount: int,
    ) -> bool:
        """
        Redelegate stake to a different validator.

        No unbonding period for redelegation.

        Args:
            caller: Delegator address
            src_validator: Source validator
            dst_validator: Destination validator
            amount: Amount to redelegate

        Returns:
            True if successful
        """
        caller_norm = self._normalize(caller)
        src_norm = self._normalize(src_validator)
        dst_norm = self._normalize(dst_validator)

        self._require_validator(dst_norm)

        delegation = self._get_delegation(caller_norm, src_norm)
        if not delegation:
            raise VMExecutionError("No delegation to source validator")

        if amount > delegation.amount:
            raise VMExecutionError("Amount exceeds delegation")

        dst_val = self.validators[dst_norm]
        if not dst_val.is_active:
            raise VMExecutionError("Destination validator not active")

        # Remove from source
        shares_removed = (amount * delegation.shares) // delegation.amount
        delegation.amount -= amount
        delegation.shares -= shares_removed
        self.validators[src_norm].delegated_stake -= amount

        # Add to destination
        if caller_norm not in self.delegations:
            self.delegations[caller_norm] = {}

        if dst_norm in self.delegations[caller_norm]:
            dst_delegation = self.delegations[caller_norm][dst_norm]
            dst_delegation.amount += amount
            dst_delegation.shares += shares_removed
        else:
            self.delegations[caller_norm][dst_norm] = Delegation(
                delegator=caller_norm,
                validator=dst_norm,
                amount=amount,
                shares=shares_removed,
            )

        dst_val.delegated_stake += amount

        logger.info(
            "Stake redelegated",
            extra={
                "event": "staking.redelegated",
                "delegator": caller_norm[:10],
                "from": src_norm[:10],
                "to": dst_norm[:10],
                "amount": amount,
            }
        )

        return True

    # ==================== Rewards ====================

    def distribute_rewards(self, caller: str, amount: int) -> bool:
        """
        Distribute rewards to all stakers.

        Distributes rewards proportionally to validators based on total stake,
        then distributes to delegators after validator commission.

        Args:
            caller: Must be owner or reward distributor
            amount: Total rewards to distribute

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if self.total_staked == 0:
            return True

        total_delegator_rewards = 0
        total_commission = 0

        # Distribute proportionally to validators
        for val_addr, validator in self.validators.items():
            if validator.total_stake == 0:
                continue

            # Validator's share of rewards
            val_share = (amount * validator.total_stake) // self.total_staked

            # Validator takes commission
            commission = (val_share * validator.commission) // self.BASIS_POINTS
            validator.accumulated_rewards += commission
            total_commission += commission

            # Remaining goes to delegators (proportionally)
            delegator_rewards = val_share - commission

            # Distribute to delegators for this validator
            if delegator_rewards > 0 and validator.delegated_stake > 0:
                distributed = self._distribute_delegator_rewards(
                    val_addr,
                    validator,
                    delegator_rewards
                )
                total_delegator_rewards += distributed

        self.total_rewards_distributed += amount

        logger.info(
            "Rewards distributed",
            extra={
                "event": "staking.rewards_distributed",
                "total_amount": amount,
                "total_commission": total_commission,
                "total_delegator_rewards": total_delegator_rewards,
                "num_validators": len(self.validators),
            }
        )

        return True

    def _distribute_delegator_rewards(
        self,
        validator_addr: str,
        validator: Validator,
        total_rewards: int
    ) -> int:
        """
        Distribute rewards to delegators of a specific validator.

        Args:
            validator_addr: Validator address
            validator: Validator object
            total_rewards: Total rewards to distribute to delegators

        Returns:
            Total amount actually distributed
        """
        if validator.delegated_stake == 0:
            return 0

        distributed = 0
        dust = 0

        # Iterate through all delegations to this validator
        for delegator_addr, del_map in self.delegations.items():
            if validator_addr not in del_map:
                continue

            delegation = del_map[validator_addr]

            # Calculate proportional share
            delegator_share = (total_rewards * delegation.amount) // validator.delegated_stake

            # Credit the delegator
            delegation.accumulated_rewards += delegator_share
            distributed += delegator_share

        # Handle dust (remaining rewards due to integer division)
        dust = total_rewards - distributed

        if dust > 0:
            # Add dust to validator's rewards to prevent loss
            validator.accumulated_rewards += dust
            logger.debug(
                "Reward distribution dust added to validator",
                extra={
                    "validator": validator_addr[:10],
                    "dust_amount": dust,
                }
            )

        logger.info(
            "Delegator rewards distributed",
            extra={
                "event": "staking.delegator_rewards_distributed",
                "validator": validator_addr[:10],
                "total_rewards": total_rewards,
                "distributed": distributed,
                "dust": dust,
                "num_delegators": sum(
                    1 for dm in self.delegations.values() if validator_addr in dm
                ),
            }
        )

        return distributed

    def claim_rewards(self, caller: str, validator: str) -> int:
        """
        Claim accumulated rewards.

        Delegators can claim their accumulated rewards that were distributed
        via distribute_rewards(). This zeroes their accumulated_rewards balance.

        Args:
            caller: Delegator address
            validator: Validator address

        Returns:
            Rewards claimed (amount withdrawn)
        """
        caller_norm = self._normalize(caller)
        validator_norm = self._normalize(validator)

        delegation = self._get_delegation(caller_norm, validator_norm)
        if not delegation:
            raise VMExecutionError("No delegation found")

        # Get accumulated rewards from reward distribution
        reward_amount = delegation.accumulated_rewards

        if reward_amount == 0:
            logger.debug(
                "No rewards to claim",
                extra={
                    "delegator": caller_norm[:10],
                    "validator": validator_norm[:10],
                }
            )
            return 0

        # Reset accumulated rewards
        delegation.accumulated_rewards = 0

        logger.info(
            "Rewards claimed",
            extra={
                "event": "staking.rewards_claimed",
                "delegator": caller_norm[:10],
                "validator": validator_norm[:10],
                "amount": reward_amount,
            }
        )

        return reward_amount

    def claim_validator_rewards(self, caller: str) -> int:
        """
        Claim accumulated validator rewards (commission + self-stake rewards).

        Args:
            caller: Validator address

        Returns:
            Rewards claimed
        """
        caller_norm = self._normalize(caller)
        self._require_validator(caller_norm)

        validator = self.validators[caller_norm]
        reward_amount = validator.accumulated_rewards

        if reward_amount == 0:
            logger.debug(
                "No validator rewards to claim",
                extra={"validator": caller_norm[:10]}
            )
            return 0

        # Reset accumulated rewards
        validator.accumulated_rewards = 0

        logger.info(
            "Validator rewards claimed",
            extra={
                "event": "staking.validator_rewards_claimed",
                "validator": caller_norm[:10],
                "amount": reward_amount,
            }
        )

        return reward_amount

    def compound_rewards(self, caller: str, validator: str) -> bool:
        """
        Compound rewards by auto-delegating.

        Args:
            caller: Delegator address
            validator: Validator address

        Returns:
            True if successful
        """
        rewards = self.claim_rewards(caller, validator)
        if rewards >= self.min_delegation:
            self.delegate(caller, validator, rewards)
        return True

    # ==================== Slashing ====================

    def slash_validator(
        self,
        caller: str,
        validator: str,
        reason: str,
        fraction: int,
    ) -> int:
        """
        Slash a validator for misbehavior.

        Args:
            caller: Must be owner/slashing authority
            validator: Validator to slash
            reason: Reason for slashing (downtime, double_sign)
            fraction: Slash fraction (basis points)

        Returns:
            Amount slashed
        """
        self._require_owner(caller)
        validator_norm = self._normalize(validator)
        self._require_validator(validator_norm)

        val = self.validators[validator_norm]

        # Calculate slash amount
        slash_amount = (val.total_stake * fraction) // self.BASIS_POINTS

        # Apply to self-stake first
        if val.self_stake >= slash_amount:
            val.self_stake -= slash_amount
        else:
            # Slash delegators proportionally
            remaining = slash_amount - val.self_stake
            val.self_stake = 0

            if val.delegated_stake > 0:
                for delegator, del_map in self.delegations.items():
                    if validator_norm in del_map:
                        delegation = del_map[validator_norm]
                        del_slash = (
                            remaining * delegation.amount
                        ) // val.delegated_stake
                        delegation.amount -= del_slash

                val.delegated_stake -= remaining

        self.total_staked -= slash_amount
        val.slashing_events += 1

        logger.warning(
            "Validator slashed",
            extra={
                "event": "staking.slashed",
                "validator": validator_norm[:10],
                "reason": reason,
                "amount": slash_amount,
            }
        )

        return slash_amount

    def jail_validator(self, caller: str, validator: str, duration: int) -> bool:
        """
        Jail a validator (temporary suspension).

        Args:
            caller: Must be owner
            validator: Validator to jail
            duration: Jail duration in seconds

        Returns:
            True if successful
        """
        self._require_owner(caller)
        validator_norm = self._normalize(validator)
        self._require_validator(validator_norm)

        val = self.validators[validator_norm]
        val.status = ValidatorStatus.JAILED
        val.jailed_until = time.time() + duration

        logger.warning(
            "Validator jailed",
            extra={
                "event": "staking.jailed",
                "validator": validator_norm[:10],
                "until": val.jailed_until,
            }
        )

        return True

    def unjail_validator(self, caller: str) -> bool:
        """
        Unjail validator (self-unjail after jail period).

        Args:
            caller: Validator address

        Returns:
            True if successful
        """
        caller_norm = self._normalize(caller)
        self._require_validator(caller_norm)

        val = self.validators[caller_norm]

        if val.status != ValidatorStatus.JAILED:
            raise VMExecutionError("Validator not jailed")

        if time.time() < val.jailed_until:
            remaining = val.jailed_until - time.time()
            raise VMExecutionError(f"Jail period not over: {remaining:.0f}s remaining")

        val.status = ValidatorStatus.ACTIVE
        val.jailed_until = 0

        return True

    # ==================== Secure Functions (Signature-Verified) ====================

    def slash_validator_secure(
        self,
        request: SignedRequest,
        validator: str,
        reason: str,
        fraction: int,
    ) -> int:
        """
        Slash a validator for misbehavior with signature verification.

        SECURE: Requires cryptographic proof of slasher role.

        Args:
            request: Signed request from authorized slasher
            validator: Validator to slash
            reason: Reason for slashing
            fraction: Slash fraction (basis points)

        Returns:
            Amount slashed

        Raises:
            VMExecutionError: If signature verification fails or not authorized
        """
        # Verify caller has slasher role or is owner
        if not (self.rbac and self.rbac.has_role(Role.SLASHER.value, request.address)):
            # Fall back to owner check
            self.access_control.verify_caller_simple(request, self.owner)
        else:
            # Verify slasher signature
            self.rbac.verify_role_simple(request, Role.SLASHER.value)

        validator_norm = self._normalize(validator)
        self._require_validator(validator_norm)

        val = self.validators[validator_norm]

        # Calculate slash amount
        slash_amount = (val.total_stake * fraction) // self.BASIS_POINTS

        # Apply to self-stake first
        if val.self_stake >= slash_amount:
            val.self_stake -= slash_amount
        else:
            # Slash delegators proportionally
            remaining = slash_amount - val.self_stake
            val.self_stake = 0

            if val.delegated_stake > 0:
                for delegator, del_map in self.delegations.items():
                    if validator_norm in del_map:
                        delegation = del_map[validator_norm]
                        del_slash = (
                            remaining * delegation.amount
                        ) // val.delegated_stake
                        delegation.amount -= del_slash

                val.delegated_stake -= remaining

        self.total_staked -= slash_amount
        val.slashing_events += 1

        logger.warning(
            "Validator slashed (secure)",
            extra={
                "event": "staking.slashed_secure",
                "validator": validator_norm[:10],
                "reason": reason,
                "amount": slash_amount,
                "slasher": request.address[:10],
            }
        )

        return slash_amount

    def jail_validator_secure(
        self,
        request: SignedRequest,
        validator: str,
        duration: int,
    ) -> bool:
        """
        Jail a validator with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner
            validator: Validator to jail
            duration: Jail duration in seconds

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)

        validator_norm = self._normalize(validator)
        self._require_validator(validator_norm)

        val = self.validators[validator_norm]
        val.status = ValidatorStatus.JAILED
        val.jailed_until = time.time() + duration

        logger.warning(
            "Validator jailed (secure)",
            extra={
                "event": "staking.jailed_secure",
                "validator": validator_norm[:10],
                "until": val.jailed_until,
                "admin": request.address[:10],
            }
        )

        return True

    def update_commission_secure(
        self,
        request: SignedRequest,
        new_commission: int,
    ) -> bool:
        """
        Update validator commission rate with signature verification.

        SECURE: Requires cryptographic proof that caller is the validator.

        Args:
            request: Signed request from validator
            new_commission: New commission rate (basis points)

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails or not validator
        """
        caller_norm = self._normalize(request.address)
        self._require_validator(caller_norm)

        # Verify signature proves ownership of validator address
        self.access_control.verify_caller_simple(request, request.address)

        if new_commission > self.BASIS_POINTS:
            raise VMExecutionError("Commission cannot exceed 100%")

        self.validators[caller_norm].commission = new_commission

        logger.info(
            "Commission updated (secure)",
            extra={
                "event": "staking.commission_updated_secure",
                "validator": caller_norm[:10],
                "new_commission_bps": new_commission,
            }
        )

        return True

    def distribute_rewards_secure(
        self,
        request: SignedRequest,
        amount: int,
    ) -> bool:
        """
        Distribute rewards to all stakers with signature verification.

        SECURE: Requires cryptographic proof of owner's private key.

        Args:
            request: Signed request from owner/reward distributor
            amount: Total rewards to distribute

        Returns:
            True if successful

        Raises:
            VMExecutionError: If signature verification fails
        """
        self.access_control.verify_caller_simple(request, self.owner)

        if self.total_staked == 0:
            return True

        total_delegator_rewards = 0
        total_commission = 0

        # Distribute proportionally to validators
        for val_addr, validator in self.validators.items():
            if validator.total_stake == 0:
                continue

            # Validator's share of rewards
            val_share = (amount * validator.total_stake) // self.total_staked

            # Validator takes commission
            commission = (val_share * validator.commission) // self.BASIS_POINTS
            validator.accumulated_rewards += commission
            total_commission += commission

            # Remaining goes to delegators
            delegator_rewards = val_share - commission

            # Distribute to delegators for this validator
            if delegator_rewards > 0 and validator.delegated_stake > 0:
                distributed = self._distribute_delegator_rewards(
                    val_addr,
                    validator,
                    delegator_rewards
                )
                total_delegator_rewards += distributed

        self.total_rewards_distributed += amount

        logger.info(
            "Rewards distributed (secure)",
            extra={
                "event": "staking.rewards_distributed_secure",
                "total_amount": amount,
                "total_commission": total_commission,
                "total_delegator_rewards": total_delegator_rewards,
                "distributor": request.address[:10],
            }
        )

        return True

    # ==================== View Functions ====================

    def get_validator_info(self, validator: str) -> Dict:
        """Get validator information."""
        validator_norm = self._normalize(validator)
        self._require_validator(validator_norm)

        val = self.validators[validator_norm]
        return {
            "address": val.address,
            "name": val.name,
            "commission": val.commission,
            "self_stake": val.self_stake,
            "delegated_stake": val.delegated_stake,
            "total_stake": val.total_stake,
            "status": val.status.value,
            "blocks_proposed": val.blocks_proposed,
            "blocks_missed": val.blocks_missed,
            "slashing_events": val.slashing_events,
        }

    def get_delegation_info(self, delegator: str, validator: str) -> Dict:
        """Get delegation information including accumulated rewards."""
        delegation = self._get_delegation(
            self._normalize(delegator),
            self._normalize(validator)
        )

        if not delegation:
            return {
                "amount": 0,
                "shares": 0,
                "accumulated_rewards": 0,
            }

        return {
            "amount": delegation.amount,
            "shares": delegation.shares,
            "unbonding_amount": delegation.unbonding_amount,
            "unbonding_completion": delegation.unbonding_completion,
            "start_time": delegation.start_time,
            "accumulated_rewards": delegation.accumulated_rewards,
        }

    def get_all_validators(self) -> List[Dict]:
        """Get list of all validators."""
        return [
            self.get_validator_info(addr)
            for addr in self.validators.keys()
        ]

    def get_staking_stats(self) -> Dict:
        """Get overall staking statistics."""
        active_validators = sum(
            1 for v in self.validators.values()
            if v.status == ValidatorStatus.ACTIVE
        )

        return {
            "total_staked": self.total_staked,
            "total_validators": len(self.validators),
            "active_validators": active_validators,
            "total_rewards_distributed": self.total_rewards_distributed,
            "reward_rate": self.reward_rate,
            "unbonding_period": self.unbonding_period,
        }

    def get_delegator_rewards(self, delegator: str) -> Dict:
        """
        Get all pending rewards for a delegator across all validators.

        Args:
            delegator: Delegator address

        Returns:
            Dict with total rewards and per-validator breakdown
        """
        delegator_norm = self._normalize(delegator)

        if delegator_norm not in self.delegations:
            return {
                "total_rewards": 0,
                "rewards_by_validator": {},
            }

        total = 0
        by_validator = {}

        for val_addr, delegation in self.delegations[delegator_norm].items():
            rewards = delegation.accumulated_rewards
            total += rewards
            by_validator[val_addr] = rewards

        return {
            "total_rewards": total,
            "rewards_by_validator": by_validator,
        }

    def claim_all_rewards(self, caller: str) -> int:
        """
        Claim all accumulated rewards across all validators.

        Args:
            caller: Delegator address

        Returns:
            Total rewards claimed
        """
        caller_norm = self._normalize(caller)

        if caller_norm not in self.delegations:
            return 0

        total_claimed = 0

        for val_addr in list(self.delegations[caller_norm].keys()):
            claimed = self.claim_rewards(caller_norm, val_addr)
            total_claimed += claimed

        logger.info(
            "All rewards claimed",
            extra={
                "event": "staking.all_rewards_claimed",
                "delegator": caller_norm[:10],
                "total_amount": total_claimed,
            }
        )

        return total_claimed

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        return address.lower()

    def _require_owner(self, caller: str) -> None:
        if self._normalize(caller) != self._normalize(self.owner):
            raise VMExecutionError("Caller is not owner")

    def _require_validator(self, validator: str) -> None:
        if validator not in self.validators:
            raise VMExecutionError(f"Validator {validator} not found")

    def _get_delegation(
        self, delegator: str, validator: str
    ) -> Optional[Delegation]:
        if delegator not in self.delegations:
            return None
        return self.delegations[delegator].get(validator)

    def _get_validator_total_shares(self, validator: str) -> int:
        total = 0
        for del_map in self.delegations.values():
            if validator in del_map:
                total += del_map[validator].shares
        return total

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize staking pool state."""
        return {
            "name": self.name,
            "address": self.address,
            "owner": self.owner,
            "staking_token": self.staking_token,
            "validators": {
                k: {
                    "address": v.address,
                    "name": v.name,
                    "commission": v.commission,
                    "self_stake": v.self_stake,
                    "delegated_stake": v.delegated_stake,
                    "status": v.status.value,
                    "jailed_until": v.jailed_until,
                    "accumulated_rewards": v.accumulated_rewards,
                }
                for k, v in self.validators.items()
            },
            "delegations": {
                delegator: {
                    val_addr: {
                        "amount": d.amount,
                        "shares": d.shares,
                        "accumulated_rewards": d.accumulated_rewards,
                        "unbonding_amount": d.unbonding_amount,
                        "unbonding_completion": d.unbonding_completion,
                    }
                    for val_addr, d in del_map.items()
                }
                for delegator, del_map in self.delegations.items()
            },
            "total_staked": self.total_staked,
            "unbonding_period": self.unbonding_period,
            "reward_rate": self.reward_rate,
            "total_rewards_distributed": self.total_rewards_distributed,
        }


@dataclass
class DelegationManager:
    """Helper for managing delegations across validators."""

    pool: StakingPool

    def get_best_validator(self) -> Optional[str]:
        """Get validator with best metrics (lowest commission, highest stake)."""
        best = None
        best_score = -1

        for addr, val in self.pool.validators.items():
            if not val.is_active:
                continue

            # Simple scoring: stake - commission penalty
            score = val.total_stake - (val.commission * 100)

            if score > best_score:
                best_score = score
                best = addr

        return best

    def get_total_delegated(self, delegator: str) -> int:
        """Get total amount delegated by an address."""
        delegator_norm = delegator.lower()
        if delegator_norm not in self.pool.delegations:
            return 0

        return sum(
            d.amount for d in self.pool.delegations[delegator_norm].values()
        )

    def get_estimated_rewards(self, delegator: str) -> int:
        """Estimate pending rewards for a delegator."""
        delegator_norm = delegator.lower()
        if delegator_norm not in self.pool.delegations:
            return 0

        total_rewards = 0
        for val_addr, delegation in self.pool.delegations[delegator_norm].items():
            val = self.pool.validators.get(val_addr)
            if not val:
                continue

            time_staked = time.time() - delegation.start_time
            reward = (
                delegation.amount * self.pool.reward_rate * int(time_staked)
                // (365 * 24 * 3600 * self.pool.BASIS_POINTS)
            )
            reward = reward * (self.pool.BASIS_POINTS - val.commission) // self.pool.BASIS_POINTS
            total_rewards += reward

        return total_rewards
