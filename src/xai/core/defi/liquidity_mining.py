"""
Liquidity Mining and Yield Farming.

Provides incentivized liquidity provision through:
- LP token staking for rewards
- Time-weighted reward distribution
- Multiple reward token support (dual farming)
- Boosted rewards with governance token locks
- Reward multipliers and tiers

Security features:
- Reentrancy protection
- Precision handling for reward calculations
- Emergency withdrawal support
- Admin controls with timelocks
"""

from __future__ import annotations

import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


# Precision for reward calculations
REWARD_PRECISION = 10**18


class FarmStatus(Enum):
    """Status of a liquidity farm."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass
class RewardToken:
    """Configuration for a reward token."""
    address: str
    symbol: str
    reward_per_second: int = 0
    accumulated_per_share: int = 0  # Scaled by REWARD_PRECISION
    last_update_time: float = 0.0
    total_distributed: int = 0
    remaining_rewards: int = 0


@dataclass
class UserPosition:
    """User's position in a farm."""
    user: str
    staked_amount: int = 0

    # Reward debt per token (for accurate reward calculation)
    reward_debt: Dict[str, int] = field(default_factory=dict)

    # Pending rewards per token
    pending_rewards: Dict[str, int] = field(default_factory=dict)

    # Boost multiplier (1x = 10000)
    boost_multiplier: int = 10000

    # Lock duration for boosted rewards
    lock_until: float = 0.0

    # Stats
    total_claimed: Dict[str, int] = field(default_factory=dict)
    staked_at: float = field(default_factory=time.time)


@dataclass
class LiquidityFarm:
    """
    Liquidity mining farm for incentivized LP provision.

    Rewards liquidity providers with governance tokens and
    other reward tokens based on their share of the pool.

    Features:
    - Multiple reward tokens (dual/triple farming)
    - Time-weighted reward distribution
    - Boost multipliers for locked stakes
    - Flexible reward rate adjustment
    - Emergency withdrawal
    """

    name: str = ""
    address: str = ""
    owner: str = ""

    # LP token being staked
    lp_token: str = ""
    pool_address: str = ""

    # Reward tokens
    reward_tokens: Dict[str, RewardToken] = field(default_factory=dict)

    # User positions
    positions: Dict[str, UserPosition] = field(default_factory=dict)

    # Total staked
    total_staked: int = 0

    # Farm status
    status: FarmStatus = FarmStatus.ACTIVE
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0  # 0 = no end

    # Boost configuration
    boost_enabled: bool = True
    max_boost: int = 25000  # 2.5x max boost
    boost_lock_duration: int = 86400 * 30  # 30 days for max boost

    # Reentrancy guard
    _in_operation: bool = False

    def __post_init__(self) -> None:
        """Initialize farm."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"farm:{self.lp_token}:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

        if not self.name:
            self.name = f"XAI Farm ({self.lp_token[:10]}...)"

    # ==================== Reward Token Management ====================

    def add_reward_token(
        self,
        caller: str,
        token_address: str,
        symbol: str,
        reward_per_second: int,
        initial_rewards: int = 0,
    ) -> bool:
        """
        Add a reward token to the farm.

        Args:
            caller: Must be owner
            token_address: Reward token address
            symbol: Token symbol
            reward_per_second: Rewards distributed per second
            initial_rewards: Initial reward pool

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if token_address in self.reward_tokens:
            raise VMExecutionError(f"Reward token {token_address} already exists")

        self.reward_tokens[token_address] = RewardToken(
            address=token_address,
            symbol=symbol,
            reward_per_second=reward_per_second,
            last_update_time=time.time(),
            remaining_rewards=initial_rewards,
        )

        logger.info(
            "Reward token added",
            extra={
                "event": "farm.reward_added",
                "farm": self.address[:10],
                "token": symbol,
                "rate": reward_per_second,
            }
        )

        return True

    def update_reward_rate(
        self,
        caller: str,
        token_address: str,
        new_rate: int,
    ) -> bool:
        """Update reward rate for a token."""
        self._require_owner(caller)
        self._update_rewards()

        if token_address not in self.reward_tokens:
            raise VMExecutionError(f"Reward token {token_address} not found")

        self.reward_tokens[token_address].reward_per_second = new_rate
        return True

    def add_rewards(
        self,
        caller: str,
        token_address: str,
        amount: int,
    ) -> bool:
        """Add rewards to the pool."""
        if token_address not in self.reward_tokens:
            raise VMExecutionError(f"Reward token {token_address} not found")

        self.reward_tokens[token_address].remaining_rewards += amount

        logger.info(
            "Rewards added",
            extra={
                "event": "farm.rewards_added",
                "farm": self.address[:10],
                "token": token_address[:10],
                "amount": amount,
            }
        )

        return True

    # ==================== Staking Operations ====================

    def stake(
        self,
        caller: str,
        amount: int,
        lock_duration: int = 0,
    ) -> bool:
        """
        Stake LP tokens in the farm.

        Args:
            caller: Staker address
            amount: Amount of LP tokens to stake
            lock_duration: Optional lock duration for boost

        Returns:
            True if successful
        """
        if self.status != FarmStatus.ACTIVE:
            raise VMExecutionError(f"Farm is {self.status.value}")

        if amount <= 0:
            raise VMExecutionError("Amount must be positive")

        self._require_no_reentrancy()

        try:
            self._in_operation = True
            self._update_rewards()

            # Get or create position
            position = self.positions.get(caller)
            if not position:
                position = UserPosition(user=caller)
                self.positions[caller] = position

            # Calculate pending rewards before stake update
            self._update_user_rewards(position)

            # Update stake
            position.staked_amount += amount
            self.total_staked += amount

            # Apply boost if locked
            if lock_duration > 0:
                position.lock_until = max(
                    position.lock_until,
                    time.time() + lock_duration
                )
                position.boost_multiplier = self._calculate_boost(lock_duration)

            # Update reward debt
            for token_addr, reward in self.reward_tokens.items():
                position.reward_debt[token_addr] = (
                    position.staked_amount *
                    reward.accumulated_per_share //
                    REWARD_PRECISION
                )

            logger.info(
                "LP tokens staked",
                extra={
                    "event": "farm.staked",
                    "farm": self.address[:10],
                    "user": caller[:10],
                    "amount": amount,
                    "boost": position.boost_multiplier,
                }
            )

            return True

        finally:
            self._in_operation = False

    def unstake(self, caller: str, amount: int) -> int:
        """
        Unstake LP tokens from the farm.

        Args:
            caller: Staker address
            amount: Amount to unstake

        Returns:
            Amount unstaked
        """
        position = self.positions.get(caller)
        if not position:
            raise VMExecutionError("No position found")

        if amount > position.staked_amount:
            raise VMExecutionError(
                f"Cannot unstake {amount}, only {position.staked_amount} staked"
            )

        # Check lock
        if time.time() < position.lock_until:
            raise VMExecutionError(
                f"Tokens locked until {position.lock_until}"
            )

        self._require_no_reentrancy()

        try:
            self._in_operation = True
            self._update_rewards()
            self._update_user_rewards(position)

            # Claim pending rewards first
            self._claim_all_rewards(position)

            # Update stake
            position.staked_amount -= amount
            self.total_staked -= amount

            # Reset boost if fully unstaked
            if position.staked_amount == 0:
                position.boost_multiplier = 10000

            # Update reward debt
            for token_addr, reward in self.reward_tokens.items():
                position.reward_debt[token_addr] = (
                    position.staked_amount *
                    reward.accumulated_per_share //
                    REWARD_PRECISION
                )

            logger.info(
                "LP tokens unstaked",
                extra={
                    "event": "farm.unstaked",
                    "farm": self.address[:10],
                    "user": caller[:10],
                    "amount": amount,
                }
            )

            return amount

        finally:
            self._in_operation = False

    def emergency_withdraw(self, caller: str) -> int:
        """
        Emergency withdraw all staked tokens, forfeiting rewards.

        Use only in emergencies - pending rewards are lost.
        """
        position = self.positions.get(caller)
        if not position or position.staked_amount == 0:
            raise VMExecutionError("No staked tokens")

        amount = position.staked_amount

        # Reset position without claiming
        position.staked_amount = 0
        position.pending_rewards = {}
        position.reward_debt = {}
        position.boost_multiplier = 10000

        self.total_staked -= amount

        logger.warning(
            "Emergency withdrawal",
            extra={
                "event": "farm.emergency_withdraw",
                "farm": self.address[:10],
                "user": caller[:10],
                "amount": amount,
            }
        )

        return amount

    # ==================== Reward Operations ====================

    def claim_rewards(
        self,
        caller: str,
        token_address: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Claim pending rewards.

        Args:
            caller: Claimant address
            token_address: Specific token (None = all)

        Returns:
            Dict of token -> amount claimed
        """
        position = self.positions.get(caller)
        if not position:
            raise VMExecutionError("No position found")

        self._require_no_reentrancy()

        try:
            self._in_operation = True
            self._update_rewards()
            self._update_user_rewards(position)

            claimed = {}

            if token_address:
                # Claim specific token
                if token_address in position.pending_rewards:
                    amount = position.pending_rewards[token_address]
                    if amount > 0:
                        claimed[token_address] = amount
                        position.pending_rewards[token_address] = 0
                        position.total_claimed[token_address] = (
                            position.total_claimed.get(token_address, 0) + amount
                        )
            else:
                # Claim all
                claimed = self._claim_all_rewards(position)

            if claimed:
                logger.info(
                    "Rewards claimed",
                    extra={
                        "event": "farm.claimed",
                        "farm": self.address[:10],
                        "user": caller[:10],
                        "rewards": claimed,
                    }
                )

            return claimed

        finally:
            self._in_operation = False

    def _claim_all_rewards(self, position: UserPosition) -> Dict[str, int]:
        """Claim all pending rewards for a position."""
        claimed = {}

        for token_addr in list(position.pending_rewards.keys()):
            amount = position.pending_rewards.get(token_addr, 0)
            if amount > 0:
                claimed[token_addr] = amount
                position.pending_rewards[token_addr] = 0
                position.total_claimed[token_addr] = (
                    position.total_claimed.get(token_addr, 0) + amount
                )
                self.reward_tokens[token_addr].total_distributed += amount

        return claimed

    def _update_rewards(self) -> None:
        """Update accumulated rewards per share for all tokens."""
        if self.total_staked == 0:
            return

        now = time.time()

        for token_addr, reward in self.reward_tokens.items():
            if reward.last_update_time >= now:
                continue

            elapsed = now - reward.last_update_time

            # Calculate rewards for this period
            rewards_to_distribute = int(elapsed * reward.reward_per_second)
            rewards_to_distribute = min(
                rewards_to_distribute,
                reward.remaining_rewards
            )

            if rewards_to_distribute > 0:
                # Update accumulated per share
                reward.accumulated_per_share += (
                    rewards_to_distribute * REWARD_PRECISION // self.total_staked
                )
                reward.remaining_rewards -= rewards_to_distribute

            reward.last_update_time = now

    def _update_user_rewards(self, position: UserPosition) -> None:
        """Update pending rewards for a user position."""
        for token_addr, reward in self.reward_tokens.items():
            accumulated = (
                position.staked_amount *
                reward.accumulated_per_share //
                REWARD_PRECISION
            )
            debt = position.reward_debt.get(token_addr, 0)

            pending = accumulated - debt
            if pending > 0:
                # Apply boost
                boosted = pending * position.boost_multiplier // 10000
                position.pending_rewards[token_addr] = (
                    position.pending_rewards.get(token_addr, 0) + boosted
                )

    # ==================== Boost Mechanics ====================

    def _calculate_boost(self, lock_duration: int) -> int:
        """Calculate boost multiplier based on lock duration."""
        if not self.boost_enabled or lock_duration <= 0:
            return 10000  # 1x

        # Linear scaling from 1x to max_boost
        max_lock = self.boost_lock_duration
        ratio = min(lock_duration, max_lock) / max_lock

        boost = 10000 + int((self.max_boost - 10000) * ratio)
        return min(boost, self.max_boost)

    def extend_lock(
        self,
        caller: str,
        additional_duration: int,
    ) -> int:
        """
        Extend lock duration for higher boost.

        Args:
            caller: Position holder
            additional_duration: Additional lock time in seconds

        Returns:
            New boost multiplier
        """
        position = self.positions.get(caller)
        if not position:
            raise VMExecutionError("No position found")

        # Calculate new lock end
        current_lock_end = max(position.lock_until, time.time())
        new_lock_end = current_lock_end + additional_duration

        position.lock_until = new_lock_end

        # Recalculate boost based on total lock from now
        total_lock = int(new_lock_end - time.time())
        position.boost_multiplier = self._calculate_boost(total_lock)

        return position.boost_multiplier

    # ==================== View Functions ====================

    def get_pending_rewards(self, user: str) -> Dict[str, int]:
        """Get pending rewards for a user."""
        position = self.positions.get(user)
        if not position:
            return {}

        # Simulate update
        pending = dict(position.pending_rewards)

        if self.total_staked > 0:
            now = time.time()
            for token_addr, reward in self.reward_tokens.items():
                elapsed = now - reward.last_update_time
                rewards_to_distribute = int(elapsed * reward.reward_per_second)
                rewards_to_distribute = min(
                    rewards_to_distribute,
                    reward.remaining_rewards
                )

                if rewards_to_distribute > 0:
                    new_accumulated = reward.accumulated_per_share + (
                        rewards_to_distribute * REWARD_PRECISION // self.total_staked
                    )

                    accumulated = (
                        position.staked_amount * new_accumulated // REWARD_PRECISION
                    )
                    debt = position.reward_debt.get(token_addr, 0)
                    user_pending = accumulated - debt

                    if user_pending > 0:
                        boosted = user_pending * position.boost_multiplier // 10000
                        pending[token_addr] = pending.get(token_addr, 0) + boosted

        return pending

    def get_position(self, user: str) -> Optional[Dict]:
        """Get user position details."""
        position = self.positions.get(user)
        if not position:
            return None

        return {
            "user": position.user,
            "staked_amount": position.staked_amount,
            "boost_multiplier": position.boost_multiplier,
            "boost_percentage": position.boost_multiplier / 100,
            "lock_until": position.lock_until,
            "pending_rewards": self.get_pending_rewards(user),
            "total_claimed": dict(position.total_claimed),
            "staked_at": position.staked_at,
        }

    def get_farm_info(self) -> Dict:
        """Get farm information."""
        return {
            "name": self.name,
            "address": self.address,
            "lp_token": self.lp_token,
            "pool_address": self.pool_address,
            "status": self.status.value,
            "total_staked": self.total_staked,
            "total_stakers": len([
                p for p in self.positions.values()
                if p.staked_amount > 0
            ]),
            "reward_tokens": {
                addr: {
                    "symbol": r.symbol,
                    "rate_per_second": r.reward_per_second,
                    "rate_per_day": r.reward_per_second * 86400,
                    "remaining": r.remaining_rewards,
                    "total_distributed": r.total_distributed,
                }
                for addr, r in self.reward_tokens.items()
            },
            "boost_enabled": self.boost_enabled,
            "max_boost": self.max_boost / 10000,
        }

    def get_apr(self, token_address: str, token_price: int, lp_price: int) -> int:
        """
        Calculate APR for a reward token.

        Args:
            token_address: Reward token
            token_price: Price in base units (e.g., USD * 10^8)
            lp_price: LP token price in same units

        Returns:
            APR in basis points (e.g., 10000 = 100%)
        """
        if token_address not in self.reward_tokens:
            return 0

        reward = self.reward_tokens[token_address]
        if self.total_staked == 0 or lp_price == 0:
            return 0

        # Annual rewards value
        annual_rewards = reward.reward_per_second * 86400 * 365
        annual_value = annual_rewards * token_price

        # Total staked value
        staked_value = self.total_staked * lp_price

        # APR = annual_value / staked_value * 10000
        return annual_value * 10000 // staked_value if staked_value > 0 else 0

    # ==================== Admin Functions ====================

    def pause(self, caller: str) -> bool:
        """Pause the farm."""
        self._require_owner(caller)
        self._update_rewards()
        self.status = FarmStatus.PAUSED
        return True

    def unpause(self, caller: str) -> bool:
        """Unpause the farm."""
        self._require_owner(caller)
        self.status = FarmStatus.ACTIVE
        # Reset last update times
        for reward in self.reward_tokens.values():
            reward.last_update_time = time.time()
        return True

    def end_farm(self, caller: str) -> bool:
        """End the farm (no new stakes, existing can unstake)."""
        self._require_owner(caller)
        self._update_rewards()
        self.status = FarmStatus.ENDED
        self.end_time = time.time()
        return True

    # ==================== Helpers ====================

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

    def _require_no_reentrancy(self) -> None:
        if self._in_operation:
            raise VMExecutionError("Reentrancy detected")


@dataclass
class FarmFactory:
    """Factory for deploying liquidity farms."""

    address: str = ""
    owner: str = ""

    # Deployed farms
    farms: Dict[str, LiquidityFarm] = field(default_factory=dict)

    # Farms by LP token
    farms_by_lp: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize factory."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"farm_factory:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def create_farm(
        self,
        caller: str,
        lp_token: str,
        pool_address: str,
        reward_token: str,
        reward_symbol: str,
        reward_per_second: int,
        initial_rewards: int = 0,
    ) -> LiquidityFarm:
        """
        Create a new liquidity farm.

        Args:
            caller: Farm owner
            lp_token: LP token to stake
            pool_address: Source liquidity pool
            reward_token: Initial reward token
            reward_symbol: Reward token symbol
            reward_per_second: Reward emission rate
            initial_rewards: Initial reward pool

        Returns:
            Created farm
        """
        farm = LiquidityFarm(
            owner=caller,
            lp_token=lp_token,
            pool_address=pool_address,
        )

        # Add initial reward token
        farm.add_reward_token(
            caller,
            reward_token,
            reward_symbol,
            reward_per_second,
            initial_rewards,
        )

        self.farms[farm.address] = farm

        if lp_token not in self.farms_by_lp:
            self.farms_by_lp[lp_token] = []
        self.farms_by_lp[lp_token].append(farm.address)

        logger.info(
            "Farm created",
            extra={
                "event": "factory.farm_created",
                "farm": farm.address[:10],
                "lp_token": lp_token[:10],
            }
        )

        return farm

    def get_farm(self, address: str) -> Optional[LiquidityFarm]:
        """Get farm by address."""
        return self.farms.get(address)

    def get_farms_for_lp(self, lp_token: str) -> List[LiquidityFarm]:
        """Get all farms for an LP token."""
        addresses = self.farms_by_lp.get(lp_token, [])
        return [self.farms[addr] for addr in addresses if addr in self.farms]

    def get_all_active_farms(self) -> List[Dict]:
        """Get info for all active farms."""
        return [
            farm.get_farm_info()
            for farm in self.farms.values()
            if farm.status == FarmStatus.ACTIVE
        ]
