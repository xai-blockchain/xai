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

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CollateralRatioBreaker,
    OracleFailureBreaker,
    PriceDeviationBreaker,
    VolumeSpikeBreaker,
)
from .concentrated_liquidity import (
    ConcentratedLiquidityFactory,
    ConcentratedLiquidityPool,
    FeeTier,
)
from .concentrated_liquidity import Position as CLPosition
from .flash_loans import FlashLoanProvider
from .lending import CollateralManager, LendingFactory, LendingPool
from .liquidity_mining import (
    FarmFactory,
    LiquidityFarm,
    RewardToken,
    UserPosition,
)
from .oracle import OracleAggregator, PriceOracle
from .staking import DelegationManager, StakingPool
from .swap_router import LimitOrder, PoolInfo, SwapPath, SwapRouter
from .vesting import (
    VestingCurve,
    VestingCurveType,
    VestingSchedule,
    VestingVault,
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
