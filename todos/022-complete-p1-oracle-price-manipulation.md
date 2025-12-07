# Oracle Price Manipulation via Timing Attack

---
status: pending
priority: p1
issue_id: 022
tags: [security, defi, oracle, code-review]
dependencies: []
---

## Problem Statement

The oracle deviation check in `/src/xai/core/defi/oracle.py` raises `VMExecutionError` to reject price updates that exceed the threshold, but the error is raised AFTER logging. An attacker could exploit timing to submit manipulated prices that pass initial validation but fail after state changes.

## Findings

### Location
**File:** `src/xai/core/defi/oracle.py` (Lines 341-359, 736-755)

### Evidence

```python
# Lines 341-359
deviation = abs(price - feed.latest_price) * 10000 // feed.latest_price
if deviation > feed.deviation_threshold:
    logger.error(...)  # State observable before rejection
    raise VMExecutionError(...)  # Too late - timing attack window
```

### Attack Vector

1. Attacker monitors oracle update transactions in mempool
2. Submits transaction that passes initial validation
3. Exploits window between logging and error raise
4. Can manipulate DeFi protocol decisions based on observable state

### Impact

- **Oracle Manipulation**: Price feeds can be briefly manipulated
- **DeFi Exploits**: Flash loan attacks using manipulated prices
- **Liquidation Gaming**: Trigger false liquidations with temporary price spikes

## Proposed Solutions

### Option A: Atomic Check-Then-Act Pattern (Recommended)
**Effort:** Small | **Risk:** Low

```python
def update_price(self, caller: str, pair: str, price: int, timestamp: Optional[float] = None) -> bool:
    # VALIDATE FIRST - NO STATE CHANGES
    feed = self._get_feed(pair)
    if not feed:
        raise VMExecutionError("Price feed not found")

    # Check deviation BEFORE any logging or state observation
    deviation = abs(price - feed.latest_price) * 10000 // feed.latest_price
    if deviation > feed.deviation_threshold:
        raise VMExecutionError(
            f"Price deviation {deviation} exceeds threshold {feed.deviation_threshold}"
        )

    # Only log and update state AFTER validation passes
    logger.info(f"Price update accepted for {pair}: {price}")
    feed.update(price, timestamp)
    return True
```

### Option B: Rate Limiting Per Address
**Effort:** Medium | **Risk:** Low

Add rate limiting to prevent rapid price update attempts:

```python
def update_price(self, caller: str, pair: str, price: int, ...) -> bool:
    # Rate limit: max 1 update per block per address
    if not self._check_rate_limit(caller, pair):
        raise VMExecutionError("Rate limit exceeded for price updates")

    # ... validation logic ...
```

## Recommended Action

Implement Option A immediately. This is a DeFi security critical bug.

## Technical Details

**Affected Components:**
- Oracle price feed system
- All DeFi protocols consuming price data
- Liquidation mechanisms
- Lending/borrowing calculations

**Database Changes:** None

## Acceptance Criteria

- [ ] Deviation check occurs before ANY logging or state observation
- [ ] Rate limiting on price update attempts
- [ ] Unit tests for oracle manipulation scenarios
- [ ] Integration tests simulating flash loan attacks
- [ ] No observable state changes for rejected updates

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by security-sentinel agent | Critical DeFi vulnerability |

## Resources

- [Oracle Manipulation Attacks](https://consensys.github.io/smart-contract-best-practices/development-recommendations/solidity-specific/oracle-manipulation/)
- Related: Flash loan attack patterns
