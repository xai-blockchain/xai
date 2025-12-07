# Flash Loan Reentrancy Vulnerability

---
status: complete
priority: p1
issue_id: 023
tags: [security, defi, reentrancy, flash-loans, code-review]
dependencies: []
completed: 2025-12-07
---

## Problem Statement

The flash loan implementation has reentrancy protection via `_execution_lock`, but the lock is released in the `finally` block AFTER balance verification. An attacker could potentially exploit the window between balance update and lock release.

## Findings

### Location
**File:** `src/xai/core/defi/flash_loans.py` (Lines 134-165, 166-320)

### Evidence

```python
with self._execution_lock:
    if borrower in self._active_loans:
        raise VMExecutionError("Flash loan already in progress")
    self._active_loans[borrower] = loan  # Set here

try:
    # ... transfer funds, execute callback ...
    # Balance verification happens here (lines 210-265)
except Exception:
    # ... revert ...
finally:
    with self._execution_lock:  # Lock reacquired - reentrancy window!
        if borrower in self._active_loans:
            del self._active_loans[borrower]
```

### Attack Scenario

1. Attacker initiates flash loan for 1000 XAI
2. In callback, attacker triggers another contract action
3. During the window between balance check and lock re-acquisition
4. Second call can observe inconsistent state
5. Potential for fund extraction beyond loan amount

### Impact

- **Fund Theft**: Extract more funds than borrowed
- **Protocol Insolvency**: Drain liquidity pools
- **State Corruption**: Leave protocol in inconsistent state

## Proposed Solutions

### Option A: Single Lock Context (Recommended)
**Effort:** Medium | **Risk:** Low

```python
def execute_flash_loan(self, borrower: str, amounts: List[int], callback: Callable) -> bool:
    with self._execution_lock:  # Hold lock for ENTIRE operation
        if borrower in self._active_loans:
            raise VMExecutionError("Flash loan already in progress")

        self._active_loans[borrower] = loan

        try:
            # Transfer funds
            self._transfer_to_borrower(borrower, amounts)

            # Execute callback (still under lock)
            callback_result = callback(loan)

            # Verify repayment (still under lock)
            if not self._verify_repayment(loan):
                raise VMExecutionError("Flash loan not repaid")

            return True
        except Exception:
            self._revert_loan(loan)
            raise
        finally:
            del self._active_loans[borrower]
            # Lock released here at the end
```

### Option B: Explicit Reentrancy Guard
**Effort:** Small | **Risk:** Low

```python
class FlashLoanManager:
    def __init__(self):
        self._reentrancy_guard: Dict[str, bool] = {}

    def _require_no_reentry(self, borrower: str) -> None:
        if self._reentrancy_guard.get(borrower, False):
            raise VMExecutionError("Reentrancy detected")
        self._reentrancy_guard[borrower] = True

    def _clear_reentry_guard(self, borrower: str) -> None:
        self._reentrancy_guard[borrower] = False

    def execute_flash_loan(self, borrower: str, ...) -> bool:
        self._require_no_reentry(borrower)
        try:
            # ... flash loan logic ...
        finally:
            self._clear_reentry_guard(borrower)
```

### Option C: Checks-Effects-Interactions Pattern
**Effort:** Medium | **Risk:** Low

Restructure to follow CEI pattern - all state changes before any external calls.

## Recommended Action

Implement Option A with Option B as defense-in-depth. This is a classic DeFi attack vector.

## Technical Details

**Affected Components:**
- Flash loan manager
- All DeFi protocols using flash loans
- Liquidity pools

**Database Changes:** None

## Acceptance Criteria

- [x] Single lock context for entire flash loan lifecycle
- [x] Explicit reentrancy guard as defense-in-depth
- [x] Unit tests for reentrancy attempts
- [ ] Integration tests simulating multi-call attacks (future work)
- [ ] Fuzz testing for flash loan edge cases (future work)

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by security-sentinel agent | Critical reentrancy vulnerability |
| 2025-12-07 | Implemented fix with defense-in-depth | COMPLETE: Single lock context + explicit guard + CEI pattern |

## Implementation Details

### Changes Made

1. **Added Explicit Reentrancy Guard** (`_reentrancy_guard: Dict[str, bool]`)
   - Checked BEFORE acquiring lock (fail-fast)
   - Cleared AFTER lock is released (defense-in-depth)
   - Separate from lock mechanism for layered security

2. **Single Lock Context for Entire Operation**
   - Lock acquired once at the beginning
   - Held through all: checks, transfers, callback, verification
   - Released only after cleanup is complete
   - No reentrancy window exists

3. **Checks-Effects-Interactions Pattern**
   - CHECKS: Input validation, liquidity verification
   - EFFECTS: State updates (loan tracking, balance changes)
   - INTERACTIONS: External callback execution
   - VERIFICATION: Post-interaction balance checks

4. **Helper Methods**
   - `_require_no_reentry(borrower)`: Set and check guard
   - `_clear_reentry_guard(borrower)`: Clear guard in finally block

### Security Properties

- **No Reentrancy Window**: Lock held from start to finish
- **Defense-in-Depth**: Guard + lock + active loan tracking
- **Fail-Fast**: Guard checked before expensive lock acquisition
- **Proper Cleanup**: Always executed via finally blocks
- **CEI Compliance**: State changes before external calls

### Test Results

- Syntax check: PASSED
- Module import: PASSED
- Reentrancy test: PASSED (correctly blocked reentrant calls)
- Flash loan protection tests: 3/3 PASSED

## Resources

- [Reentrancy Attacks](https://consensys.github.io/smart-contract-best-practices/attacks/reentrancy/)
- [Flash Loan Security](https://www.paradigm.xyz/2020/04/understanding-the-dao-attack/)
