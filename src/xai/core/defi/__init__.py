"""
XAI DeFi Protocols.

This module provides production-grade DeFi implementations including:
- Lending: Collateralized borrowing with liquidation (Aave/Compound style)
- Flash Loans: Uncollateralized single-transaction loans
- Staking: Token staking with delegation and slashing
- Oracle: Price feed aggregation
- Swap Router: Multi-hop swap aggregation with limit orders
- Vesting: Advanced token vesting with multiple curve types
- Liquidity Mining: Yield farming with boosted rewards
- Circuit Breakers: Emergency safety mechanisms
- Concentrated Liquidity: Uniswap V3-style capital-efficient AMM
"""

from .lending import LendingPool, LendingFactory, CollateralManager
from .flash_loans import FlashLoanProvider
from .staking import StakingPool, DelegationManager
from .oracle import PriceOracle, OracleAggregator
from .swap_router import SwapRouter, LimitOrder, SwapPath, PoolInfo
from .vesting import (
    VestingVault,
    VestingSchedule,
    VestingCurve,
    VestingCurveType,
)
from .liquidity_mining import (
    LiquidityFarm,
    FarmFactory,
    UserPosition,
    RewardToken,
)
from .circuit_breaker import (
    CircuitBreakerRegistry,
    CircuitBreaker,
    PriceDeviationBreaker,
    CollateralRatioBreaker,
    VolumeSpikeBreaker,
    OracleFailureBreaker,
)
from .concentrated_liquidity import (
    ConcentratedLiquidityPool,
    ConcentratedLiquidityFactory,
    Position as CLPosition,
    FeeTier,
)

__all__ = [
    # Lending
    "LendingPool",
    "LendingFactory",
    "CollateralManager",
    # Flash Loans
    "FlashLoanProvider",
    # Staking
    "StakingPool",
    "DelegationManager",
    # Oracle
    "PriceOracle",
    "OracleAggregator",
    # Swap Router
    "SwapRouter",
    "LimitOrder",
    "SwapPath",
    "PoolInfo",
    # Vesting
    "VestingVault",
    "VestingSchedule",
    "VestingCurve",
    "VestingCurveType",
    # Liquidity Mining
    "LiquidityFarm",
    "FarmFactory",
    "UserPosition",
    "RewardToken",
    # Circuit Breakers
    "CircuitBreakerRegistry",
    "CircuitBreaker",
    "PriceDeviationBreaker",
    "CollateralRatioBreaker",
    "VolumeSpikeBreaker",
    "OracleFailureBreaker",
    # Concentrated Liquidity
    "ConcentratedLiquidityPool",
    "ConcentratedLiquidityFactory",
    "CLPosition",
    "FeeTier",
]
