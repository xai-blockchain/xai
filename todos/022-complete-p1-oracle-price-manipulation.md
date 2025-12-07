# Oracle Price Manipulation via Timing Attack

---
status: complete
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

- [x] Deviation check occurs before ANY logging or state observation
- [x] Rate limiting on price update attempts
- [x] Unit tests for oracle manipulation scenarios
- [x] Integration tests simulating flash loan attacks
- [x] No observable state changes for rejected updates

## Resolution Summary

The vulnerability has been completely fixed with production-quality implementation:

### Implementation Details

**File:** `src/xai/core/defi/oracle.py`

**Key Changes:**

1. **Atomic Validation (Lines 353-443):**
   - All validation checks execute BEFORE any state changes or logging
   - Deviation check against TWAP (lines 399-410) occurs in validation phase
   - State updates only begin at line 444 after all validations pass
   - Logging occurs at line 474, after successful state update

2. **Rate Limiting (Lines 378-385):**
   - Per-source rate limiting with configurable `min_update_interval`
   - Default 60-second minimum between updates from same source
   - Prevents rapid spam attacks and manipulation attempts

3. **TWAP Protection (Lines 399-410):**
   - Deviation checked against Time-Weighted Average Price, not just last price
   - Prevents flash loan manipulation where single block price spike would pass
   - Properly weighted by time duration (implementation lines 1061-1116)

4. **Multi-Source Validation (Lines 412-442):**
   - Requires consensus from multiple sources when configured
   - Median aggregation resists outlier manipulation
   - Pending updates stored and aggregated atomically

5. **Comprehensive Security Checks:**
   - Price staleness validation (lines 365-370)
   - Future timestamp rejection (lines 373-376)
   - Price bounds enforcement (lines 388-393)
   - Positive price validation (lines 396-397)
   - Circuit breaker support (line 359)

### Test Coverage

**File:** `tests/xai_tests/security/test_oracle_manipulation.py`

All 15 security tests pass, including:
- `test_atomic_validation_prevents_timing_attack` - Validates no state changes on rejection
- `test_twap_prevents_flash_loan_manipulation` - Tests TWAP protection
- `test_rate_limiting_prevents_spam_attacks` - Validates rate limiting
- `test_staleness_check_prevents_replay_attacks` - Prevents old price replay
- `test_future_timestamp_rejection` - Prevents future timestamps
- `test_multi_source_aggregation` - Tests consensus requirement
- `test_median_aggregation_resists_outliers` - Tests manipulation resistance
- Additional edge case and error condition tests

### Security Properties Verified

✅ **No Observable State Before Validation:** All checks complete before any logging or state modification
✅ **Rate Limiting:** Prevents rapid manipulation attempts
✅ **TWAP-Based Validation:** Prevents flash loan attacks
✅ **Multi-Source Consensus:** Requires agreement from multiple providers when configured
✅ **Comprehensive Input Validation:** Staleness, bounds, timestamps all checked
✅ **Atomic Operations:** Check-then-act pattern ensures no partial state changes

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by security-sentinel agent | Critical DeFi vulnerability |
| 2025-12-07 | Implemented atomic validation pattern | All validation before state changes |
| 2025-12-07 | Added rate limiting per source | 60s minimum interval default |
| 2025-12-07 | Added TWAP-based deviation checking | Prevents flash loan manipulation |
| 2025-12-07 | Comprehensive test suite added | 15 security tests, all passing |
| 2025-12-07 | Issue verified complete | All acceptance criteria met |

## Resources

- [Oracle Manipulation Attacks](https://consensys.github.io/smart-contract-best-practices/development-recommendations/solidity-specific/oracle-manipulation/)
- Related: Flash loan attack patterns
