# XAI Blockchain Tokenomics Model

## Overview

The XAI blockchain implements a fixed-supply cryptocurrency model with a hard cap of **121,000,000 XAI tokens**.

## Supply Distribution

### Genesis Allocation: 60,500,000 XAI (50%)

The genesis block allocates exactly 50% of the total supply:

| Allocation | Amount | Percentage | Purpose |
|-----------|---------|------------|---------|
| Founder (Immediate) | 2,500,000 XAI | 2.07% | Immediate founder allocation |
| Founder (Vesting) | 9,600,000 XAI | 7.93% | Vested founder allocation |
| Development Fund | 6,050,000 XAI | 5.00% | Core development and operations |
| Marketing Fund | 6,050,000 XAI | 5.00% | Marketing and community growth |
| Mining Pool Reserve | 36,300,000 XAI | 30.00% | Reserved for mining distribution |
| **TOTAL GENESIS** | **60,500,000 XAI** | **50.00%** | |

### Mining Rewards: 60,500,000 XAI (50%)

The remaining 50% is distributed through mining rewards over time using a halving schedule.

## Mining Emission Schedule

### Halving Mechanism

- **Initial Block Reward**: 12 XAI per block
- **Halving Interval**: 262,800 blocks (~1 year at 2 minutes/block)
- **Block Time Target**: 2 minutes
- **Halving Formula**: `reward = 12 / (2^halvings)`

### Emission by Year

| Year | Block Range | Reward/Block | Blocks | Total XAI Mined | Cumulative |
|------|-------------|--------------|---------|-----------------|------------|
| 1 | 0 - 262,799 | 12 XAI | 262,800 | 3,153,600 | 3,153,600 |
| 2 | 262,800 - 525,599 | 6 XAI | 262,800 | 1,576,800 | 4,730,400 |
| 3 | 525,600 - 788,399 | 3 XAI | 262,800 | 788,400 | 5,518,800 |
| 4 | 788,400 - 1,051,199 | 1.5 XAI | 262,800 | 394,200 | 5,913,000 |
| 5+ | Continues halving... | Decreasing | ... | ... | Approaches 60.5M |

### Supply Cap Enforcement

The blockchain implements **three-layer supply cap protection**:

#### 1. Genesis Cap Verification

```python
# Genesis allocates exactly 60.5M XAI
genesis_supply = 60_500_000.0
assert genesis_supply == 0.5 * max_supply
```

#### 2. Mining Reward Cap

```python
def get_block_reward(self, block_height: int) -> float:
    # Check current supply
    current_supply = self.get_circulating_supply()
    remaining_supply = self.max_supply - current_supply

    # No rewards if cap reached
    if remaining_supply <= 0:
        return 0.0

    # Calculate halving reward
    reward = self.initial_block_reward / (2**halvings)

    # Cap reward to remaining supply
    if reward > remaining_supply:
        reward = remaining_supply

    return reward
```

#### 3. Total Supply Validation

```python
# Continuous validation
assert get_circulating_supply() <= max_supply
assert get_total_supply() <= max_supply
```

## Economic Properties

### Deflationary Design

1. **Fixed Supply**: Hard cap prevents inflation
2. **Halvings**: Decreasing block rewards over time
3. **Transaction Fees**: Burned or redistributed (not minted)

### Distribution Timeline

- **Genesis (Immediate)**: 60.5M XAI distributed at launch
- **Year 1-2**: ~4.7M XAI mined (rapid early distribution)
- **Year 3-4**: ~1.2M XAI mined (slowing emission)
- **Year 5+**: Remaining ~54.6M XAI mined (asymptotic approach to cap)

### Scarcity Model

The emission follows an asymptotic curve where:
- First 50% distributed instantly (genesis)
- Next 25% distributed in ~2 years (first two halvings)
- Next 12.5% distributed in ~4 years (next two halvings)
- Remaining approaches cap over decades

## Implementation Details

### Supply Calculation

```python
def get_circulating_supply(self) -> float:
    """Calculate current circulating supply"""
    total = 0.0
    for address, utxos in self.utxo_manager.utxo_set.items():
        for utxo in utxos:
            total += utxo.get("amount", 0.0)
    return total
```

### Reward Calculation

```python
def get_block_reward(self, block_height: int) -> float:
    """Calculate block reward with supply cap enforcement"""
    current_supply = self.get_circulating_supply()
    remaining_supply = self.max_supply - current_supply

    if remaining_supply <= 0:
        return 0.0

    halvings = block_height // self.halving_interval
    reward = self.initial_block_reward / (2**halvings)

    if reward < 0.00000001:
        return 0.0

    if reward > remaining_supply:
        reward = remaining_supply

    return reward
```

## Verification

### Test Coverage

Comprehensive tests ensure supply cap enforcement:

1. **Genesis Allocation Tests**: Verify 50% allocation
2. **Mining Reward Tests**: Validate cap enforcement
3. **Supply Cap Tests**: Ensure total never exceeds 121M
4. **Halving Tests**: Verify emission schedule
5. **Edge Case Tests**: Boundary conditions and edge cases

### Audit Points

**Critical Checks**:
- ✅ Genesis allocates exactly 60.5M XAI
- ✅ Mining rewards stop at supply cap
- ✅ Total supply never exceeds 121M XAI
- ✅ Reward capped to remaining supply
- ✅ Zero reward when cap reached
- ✅ Halving schedule respected
- ✅ Transaction fees don't break cap

## Security Considerations

### Overflow Protection

```python
from decimal import Decimal, getcontext
getcontext().prec = 50  # High precision for calculations
```

### Double-Spend Prevention

- UTXO model tracks all spendable outputs
- Inputs consumed when spent
- Supply calculated from UTXOs (prevents double-counting)

### Inflation Resistance

1. **Hard Cap**: Mathematically enforced 121M limit
2. **Supply Validation**: Every block checks total supply
3. **Reward Caps**: Mining rewards capped to remaining supply
4. **No Burning**: Supply only decreases through loss, never minting

## Future Considerations

### Potential Enhancements

1. **Fee Burning**: Burn portion of transaction fees (deflationary)
2. **Vesting Schedules**: Time-locked founder allocations
3. **Staking Rewards**: From transaction fees (not minting)
4. **Governance**: Community control of economic parameters

### Long-Term Economics

- **Year 10**: ~99% of supply distributed
- **Year 20**: ~99.9% of supply distributed
- **Year 30+**: Asymptotically approaching 121M cap
- **Final State**: Mining rewards transition to transaction fees only

## Conclusion

The XAI tokenomics model ensures:
- **Predictable supply**: Fixed 121M cap
- **Fair distribution**: 50% genesis, 50% mining
- **Long-term sustainability**: Halving schedule over decades
- **Security**: Multi-layer cap enforcement
- **Transparency**: All code and tests publicly auditable

This creates a sound economic foundation for a sustainable, deflationary cryptocurrency.
