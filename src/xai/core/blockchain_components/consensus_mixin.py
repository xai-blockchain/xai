"""
Consensus Mixin for XAI Blockchain

Extracted from blockchain.py as part of god class refactoring.
Contains consensus-related methods: block rewards, difficulty adjustment,
and coinbase validation.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.chain.block_header import BlockHeader
    from xai.core.blockchain_components.block import Block

class BlockchainConsensusMixin:
    """
    Mixin providing consensus-related functionality for the Blockchain class.

    This mixin handles:
    - Block reward calculation with halving schedule
    - Difficulty adjustment algorithm
    - Coinbase transaction validation

    Required attributes on the implementing class:
    - chain: List of blocks/headers
    - difficulty: Current difficulty level
    - initial_block_reward: Starting block reward (12 XAI)
    - halving_interval: Blocks between halvings (262,800)
    - max_supply: Maximum coin supply (121M)
    - target_block_time: Target seconds per block
    - difficulty_adjustment_interval: Blocks between adjustments
    - max_difficulty_change: Maximum difficulty change factor
    - logger: Structured logger instance
    - fast_mining_enabled: Whether fast mining is enabled (test mode)
    - max_test_mining_difficulty: Cap for test mining difficulty
    """

    @property
    def block_reward(self) -> float:
        """
        Current block reward based on chain height and halving schedule.
        """
        return self.get_block_reward(len(self.chain))

    def get_block_reward(self, block_height: int) -> float:
        """Calculate block reward with halving every 1 year (262,800 blocks at 2min/block)

        Emission schedule (per WHITEPAPER):
        - Year 1 (blocks 0-262,799): 12 XAI/block → ~3.15M XAI
        - Year 2 (blocks 262,800-525,599): 6 XAI/block → ~1.58M XAI
        - Year 3 (blocks 525,600-788,399): 3 XAI/block → ~0.79M XAI
        - Year 4 (blocks 788,400-1,051,199): 1.5 XAI/block → ~0.39M XAI
        - Continues halving until reaching max supply (121M XAI total)

        CRITICAL: Enforces supply cap - rewards stop when cap is reached
        """
        # Check current supply against cap
        current_supply = self.get_circulating_supply()
        remaining_supply = self.max_supply - current_supply

        # If we've reached or exceeded the cap, no more rewards
        if remaining_supply <= 0:
            return 0.0

        # Calculate standard halving reward
        halvings = block_height // self.halving_interval
        reward = self.initial_block_reward / (2**halvings)

        # Ensure reward doesn't go below minimum (0.00000001 AXN)
        if reward < 0.00000001:
            return 0.0

        # Cap reward to remaining supply to prevent exceeding max_supply
        if reward > remaining_supply:
            reward = remaining_supply

        return reward

    def validate_coinbase_reward(self, block: "Block") -> tuple[bool, str | None]:
        """
        Validate that the coinbase transaction doesn't exceed the allowed block reward + fees.

        This is a CRITICAL security check that prevents miners from creating unlimited coins
        by validating that the coinbase reward matches the expected block reward plus
        transaction fees collected in the block.

        Security Properties:
        - Enforces halving schedule (reward halves every 262,800 blocks)
        - Validates reward doesn't exceed base reward + total fees
        - Prevents inflation attacks where miners create arbitrary amounts
        - Enforces maximum supply cap (121M XAI)

        Args:
            block: The block to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if coinbase reward is valid
            - error_message: Description of validation failure, or None if valid

        Attack Mitigation:
            Without this check, a malicious miner could set coinbase amount to any value,
            creating unlimited coins and breaking the tokenomics. This validation ensures
            the economic model is enforced at the consensus level.
        """
        # Find the coinbase transaction
        coinbase_tx = None
        for tx in block.transactions:
            if tx.sender == "COINBASE" or tx.tx_type == "coinbase":
                coinbase_tx = tx
                break

        if coinbase_tx is None:
            return False, "Block missing coinbase transaction"

        # Calculate expected base block reward for this height
        expected_reward = self.get_block_reward(block.index)

        # Calculate total transaction fees in the block (all non-coinbase transactions)
        total_fees = 0.0
        for tx in block.transactions:
            if tx.sender not in ["COINBASE", "SYSTEM", "AIRDROP"] and tx.tx_type != "coinbase":
                total_fees += tx.fee

        # Maximum allowed coinbase amount = base reward + transaction fees
        max_allowed = expected_reward + total_fees

        # Get actual coinbase reward
        actual_reward = coinbase_tx.amount

        # Validate coinbase doesn't exceed maximum allowed
        # Allow small floating point tolerance (0.00000001 XAI)
        tolerance = 0.00000001
        if actual_reward > max_allowed + tolerance:
            error_msg = (
                f"Coinbase reward {actual_reward:.8f} XAI exceeds maximum allowed {max_allowed:.8f} XAI "
                f"(base reward: {expected_reward:.8f} XAI, fees: {total_fees:.8f} XAI) at block height {block.index}"
            )
            self.logger.warn(
                "SECURITY: Invalid coinbase reward - potential inflation attack",
                extra={
                    "event": "consensus.invalid_coinbase",
                    "block_height": block.index,
                    "block_hash": block.hash,
                    "expected_reward": expected_reward,
                    "actual_reward": actual_reward,
                    "total_fees": total_fees,
                    "max_allowed": max_allowed,
                    "excess": actual_reward - max_allowed,
                }
            )
            return False, error_msg

        # Log successful validation
        self.logger.debug(
            "Coinbase reward validated successfully",
            extra={
                "event": "consensus.coinbase_validated",
                "block_height": block.index,
                "block_hash": block.hash,
                "expected_reward": expected_reward,
                "actual_reward": actual_reward,
                "total_fees": total_fees,
                "max_allowed": max_allowed,
            }
        )

        return True, None

    def calculate_next_difficulty(
        self,
        *,
        chain: Sequence["Block" | "BlockHeader"] | None = None,
        current_difficulty: int | None = None,
        emit_log: bool = True,
    ) -> int:
        """
        Calculate the next difficulty based on actual vs target block times.
        Implements Bitcoin-style difficulty adjustment algorithm.

        Adjusts difficulty every 'difficulty_adjustment_interval' blocks to maintain
        target block time. Limits adjustment to prevent extreme changes.

        Args:
            chain: Optional chain to use for calculation (defaults to self.chain)
            current_difficulty: Optional baseline difficulty (defaults to chain tip)
            emit_log: Whether to emit log messages

        Returns:
            int: New difficulty level (number of leading zeros required)
        """
        from xai.core.consensus.advanced_consensus import DynamicDifficultyAdjustment

        override_chain = chain is not None
        override_difficulty = current_difficulty is not None

        if override_chain:
            chain_view: Sequence["Block" | "BlockHeader"] = list(chain or [])
        else:
            chain_view = self.chain

        def _extract_header(entry: "Block" | "BlockHeader") -> "BlockHeader":
            return entry.header if hasattr(entry, "header") else entry

        if current_difficulty is None:
            if chain_view:
                last_header = _extract_header(chain_view[-1])
                baseline = getattr(last_header, "difficulty", None)
                current_baseline = int(baseline) if baseline is not None else int(self.difficulty or 1)
            else:
                current_baseline = int(self.difficulty or 1)
        else:
            current_baseline = int(current_difficulty)
        current_baseline = max(1, current_baseline)

        adjuster = getattr(self, "dynamic_difficulty_adjuster", None)
        if adjuster is None:
            adjuster = DynamicDifficultyAdjustment(target_block_time=self.target_block_time)
            self.dynamic_difficulty_adjuster = adjuster

        adjuster.target_block_time = self.target_block_time
        adjuster.min_difficulty = 1
        derived_cap = max(
            int(max(1, current_baseline) * max(1, self.max_difficulty_change)),
            int(current_baseline + 1),
            getattr(adjuster, "max_difficulty", 1),
        )
        adjuster.max_difficulty = max(derived_cap, adjuster.min_difficulty + 1)

        context_obj: Any | SimpleNamespace
        if override_chain or override_difficulty:
            context_obj = SimpleNamespace(chain=chain_view, difficulty=current_baseline)
        else:
            context_obj = self

        should_log = emit_log and not (override_chain or override_difficulty)

        if adjuster.should_adjust_difficulty(context_obj):
            new_difficulty = adjuster.calculate_new_difficulty(context_obj)
            if should_log and new_difficulty != current_baseline:
                self.logger.info(
                    "Dynamic difficulty adjustment applied",
                    window=adjuster.adjustment_window,
                    old_difficulty=current_baseline,
                    new_difficulty=new_difficulty,
                )
            return new_difficulty

        current_height = len(chain_view)

        # Don't adjust if we haven't reached the adjustment interval
        if current_height < self.difficulty_adjustment_interval:
            return current_baseline

        # Only adjust at the interval boundaries
        if current_height % self.difficulty_adjustment_interval != 0:
            return current_baseline

        # Get the blocks from the last adjustment period
        interval_start_block_header = _extract_header(
            chain_view[current_height - self.difficulty_adjustment_interval]
        )
        latest_block_header = _extract_header(chain_view[-1])

        # Calculate actual time taken for the last interval
        actual_time = latest_block_header.timestamp - interval_start_block_header.timestamp

        # Calculate expected time for the interval
        expected_time = self.difficulty_adjustment_interval * self.target_block_time

        # Prevent division by zero and negative times
        if actual_time <= 0:
            actual_time = 1

        # Calculate adjustment ratio
        adjustment_ratio = expected_time / actual_time

        # Limit the adjustment to prevent extreme changes (max 4x up or down)
        if adjustment_ratio > self.max_difficulty_change:
            adjustment_ratio = self.max_difficulty_change
        elif adjustment_ratio < (1.0 / self.max_difficulty_change):
            adjustment_ratio = 1.0 / self.max_difficulty_change

        # Calculate new difficulty
        # If blocks are too slow (actual_time > expected_time), ratio > 1, difficulty decreases
        # If blocks are too fast (actual_time < expected_time), ratio < 1, difficulty increases
        new_difficulty_float = current_baseline / adjustment_ratio

        # Ensure difficulty is at least 1 and is an integer
        new_difficulty = max(1, int(round(new_difficulty_float)))

        # Log the adjustment for monitoring
        if should_log:
            self.logger.info(
                f"Difficulty Adjustment at block {current_height}:",
                actual_time=actual_time,
                expected_time=expected_time,
                old_difficulty=current_baseline,
                new_difficulty=new_difficulty,
                adjustment_percent=((new_difficulty / current_baseline - 1) * 100),
            )

        return new_difficulty

    def _expected_difficulty_for_block(
        self,
        *,
        block_index: int,
        history: Sequence["Block" | "BlockHeader"],
    ) -> int | None:
        """
        Determine the deterministic difficulty for a block based on prior history.

        Args:
            block_index: Index of the block being evaluated.
            history: Sequence of blocks/headers representing the canonical chain
                     up to (but excluding) the block being validated.

        Returns:
            Expected integer difficulty or None if insufficient context.
        """
        if block_index <= 0:
            return None
        history_view = list(history)
        if not history_view or len(history_view) != block_index:
            return None

        previous_entry = history_view[-1]
        previous_header = previous_entry.header if hasattr(previous_entry, "header") else previous_entry
        previous_index = getattr(previous_header, "index", None)
        if previous_index is None or previous_index != block_index - 1:
            return None

        baseline = getattr(previous_header, "difficulty", None)
        if baseline is None:
            return None

        expected = self.calculate_next_difficulty(
            chain=history_view,
            current_difficulty=int(baseline),
            emit_log=False,
        )
        if self.fast_mining_enabled:
            return min(expected, self.max_test_mining_difficulty)
        return expected
