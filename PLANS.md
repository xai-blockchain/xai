# Execution Plans

This document defines how agents should plan and execute complex work across all blockchain projects (PAW, Aura, XAI).

---

## Purpose

ExecPlans are **living design documents** that guide implementation of significant features or changes. They ensure:

1. **Complete implementation** - No stubs, no placeholders, no "later"
2. **Verifiable outcomes** - Observable, testable results
3. **Professional quality** - Code that impresses blockchain auditors
4. **Continuous progress** - Agents work autonomously through the plan

---

## When to Create an ExecPlan

Create an ExecPlan in this file when:

- Implementing a new module or major feature
- Performing significant refactoring
- Fixing complex bugs spanning multiple files
- Conducting security hardening across components
- Migrating between SDK versions or frameworks

**For routine tasks in `ROADMAP_PRODUCTION.md`, execute directly without an ExecPlan.**

---

## ExecPlan Structure

Each plan follows this format:

```markdown
## [Plan Name]

**Status:** 🟡 In Progress | 🟢 Complete | 🔴 Blocked
**Project:** PAW | Aura | XAI
**Created:** YYYY-MM-DD
**Last Updated:** YYYY-MM-DD HH:MM

### Big Picture

[2-3 sentences: What does this achieve? What will users/validators/developers gain?
How will we know it's working?]

### Observable Outcomes

When complete, these behaviors will be verifiable:

1. [Specific command and expected output]
2. [Specific test and expected result]
3. [Specific user action and observable effect]

### Current State

[Brief description of what exists now. Assume reader has no prior knowledge.
Reference specific files with full paths.]

### Plan of Work

[Narrative description of the implementation sequence. What gets built first,
what depends on what, how pieces connect.]

### Milestones

#### Milestone 1: [Name]

**Goal:** [What this milestone achieves]

**Files Modified:**
- `/path/to/file1.go` - [what changes]
- `/path/to/file2.go` - [what changes]

**Implementation:**
[Detailed steps with code patterns, NOT pseudocode or stubs]

**Validation:**
    [exact command]
    [expected output]

**Acceptance:** [How to verify this milestone is complete]

---

#### Milestone 2: [Name]
[Same structure...]

---

### Progress

- [ ] `[YYYY-MM-DD HH:MM]` Step description
- [x] `[YYYY-MM-DD HH:MM]` Completed step ✓

### Discoveries

[Unexpected findings during implementation. Include evidence.]

### Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| YYYY-MM-DD | Chose X over Y | Because Z provides better security/performance |

### Retrospective

[Filled in upon completion: What worked, what was harder than expected,
lessons for future work]
```

---

## Non-Negotiable Requirements

### 1. Self-Contained

The plan must contain ALL information needed to implement. An agent reading only this plan should be able to execute completely.

**Include:**
- Full file paths (repository-relative)
- Complete code patterns (not pseudocode)
- Exact commands with expected outputs
- All relevant context

**Never:**
- Reference external documents without embedding key content
- Assume prior knowledge of the codebase
- Use vague language like "update as needed"

### 2. Observable Outcomes

Every plan must define **verifiable behaviors**, not just code changes.

**Good:**
```
After starting the node with `./pawd start`, querying
`pawcli query dex pools` returns a JSON list of active pools
with their liquidity amounts and fee tiers.
```

**Bad:**
```
DEX pool functionality is implemented.
```

### 3. Complete Implementation

Plans guide agents to **production-ready code**. Every milestone must result in:

- Fully functional code (no stubs)
- Complete error handling
- Security hardening applied
- Tests written and passing
- Documentation updated

**Never include milestones like:**
- "Stub out the interface"
- "Add placeholder implementation"
- "Basic version, enhance later"

### 4. Living Document

Update this plan as work progresses:

- Check off completed steps with timestamps
- Add discoveries as they occur
- Log decisions with rationale
- Update milestones if scope changes

### 5. Professional Standards

All code produced must meet blockchain industry standards:

- Would pass Trail of Bits audit
- Follows OpenZeppelin patterns (where applicable)
- Implements Cosmos SDK best practices
- Handles all edge cases and attack vectors

---

## Quality Gates

Before marking any milestone complete:

```
□ Code compiles without errors
□ All existing tests pass
□ New tests cover new code (>90% coverage)
□ No security vulnerabilities introduced
□ Error handling is complete
□ Documentation is updated
□ Changes committed and pushed
□ ROADMAP_PRODUCTION.md updated
```

---

## Forbidden Patterns

Plans must NOT include:

| Pattern | Why Forbidden | Alternative |
|---------|---------------|-------------|
| "Implement basic version first" | Leads to incomplete code | Design complete solution, implement fully |
| "Stub for now, fill in later" | "Later" never comes | Implement completely or don't start |
| "Skip edge cases initially" | Security vulnerabilities | Handle all cases from the start |
| "Comment out problematic code" | Hides bugs | Fix the underlying issue |
| "Simplify to make progress" | Delivers incomplete product | Implement full complexity |
| "Test manually for now" | Tests get forgotten | Write automated tests immediately |
| Milestones without validation | Can't verify completion | Every milestone needs verification steps |

---

## Example: Good vs Bad Plans

### BAD Plan (Do NOT write plans like this)

```markdown
## Implement DEX Module

### Goal
Add DEX functionality

### Steps
1. Create types
2. Add keeper
3. Write handlers
4. Add tests
5. Update docs

### Notes
Will implement basic swap first, add advanced features later.
```

**Problems:**
- Vague steps with no detail
- No observable outcomes
- "Basic first, advanced later" = incomplete
- No validation criteria
- No file paths or code patterns

### GOOD Plan

```markdown
## Implement DEX Constant-Product AMM

**Status:** 🟡 In Progress
**Project:** PAW
**Created:** 2024-11-29
**Last Updated:** 2024-11-29 14:30

### Big Picture

Implement a Uniswap V2-style constant-product AMM allowing users to create
liquidity pools, add/remove liquidity, and swap tokens with configurable fees.
Validators and users will interact via CLI; DeFi applications will integrate
via gRPC/REST.

### Observable Outcomes

1. `pawcli tx dex create-pool uatom upaw 1000000 1000000 --fee-tier 30 --from validator`
   creates a pool and returns pool ID in transaction result

2. `pawcli query dex pool 1` returns:
       pool_id: 1
       token_a: {denom: "uatom", amount: "1000000"}
       token_b: {denom: "upaw", amount: "1000000"}
       total_shares: "1000000"
       fee_bps: 30

3. `go test ./x/dex/... -v` shows all tests passing with >90% coverage

4. Security test `TestSwap_ReentrancyProtection` explicitly verifies
   reentrancy attack is prevented

### Current State

The `/x/dex/` directory exists with partial implementation:
- `/x/dex/types/` - Message types defined but missing validation
- `/x/dex/keeper/` - Keeper struct exists, methods incomplete
- `/x/dex/module.go` - Registered in app but handlers return errors

No pools can be created. Swap calculations exist but lack slippage protection.

### Plan of Work

First, complete the type definitions with full validation. Then implement
the keeper methods following checks-effects-interactions pattern for security.
Add the AMM math library with comprehensive tests. Wire up message handlers
and gRPC queries. Finally, add integration tests and update documentation.

### Milestones

#### Milestone 1: Complete Type Definitions

**Goal:** All message types fully defined with validation

**Files Modified:**
- `/x/dex/types/pool.go` - Pool struct with invariant checks
- `/x/dex/types/msgs.go` - MsgCreatePool, MsgSwap, MsgAddLiquidity, MsgRemoveLiquidity
- `/x/dex/types/errors.go` - All error types
- `/x/dex/types/keys.go` - Store key prefixes

**Implementation:**

Pool structure with invariants:
    type Pool struct {
        Id            uint64
        TokenA        sdk.Coin
        TokenB        sdk.Coin
        TotalShares   sdk.Int
        FeeBps        uint32  // Basis points (30 = 0.30%)
        CreatedAt     int64
        CreatedBy     sdk.AccAddress
    }

    func (p Pool) Validate() error {
        if p.TokenA.Amount.IsNegative() || p.TokenB.Amount.IsNegative() {
            return ErrInvalidPoolState
        }
        if p.FeeBps > 10000 {
            return ErrInvalidFee
        }
        // Verify constant product invariant
        // ... complete validation
    }

Message validation:
    func (msg MsgSwap) ValidateBasic() error {
        if _, err := sdk.AccAddressFromBech32(msg.Sender); err != nil {
            return errorsmod.Wrap(sdkerrors.ErrInvalidAddress, "invalid sender")
        }
        if !msg.TokenIn.IsValid() || msg.TokenIn.IsZero() {
            return errorsmod.Wrap(sdkerrors.ErrInvalidCoins, "invalid token in")
        }
        if msg.MinAmountOut.IsNegative() {
            return ErrInvalidSlippage
        }
        return nil
    }

**Validation:**
    go build ./x/dex/...
    # Should compile without errors

    go test ./x/dex/types/... -v
    # Should show all type validation tests passing

**Acceptance:** All types compile, ValidateBasic() covers all edge cases,
100% test coverage on validation functions.

---

#### Milestone 2: AMM Math Library

**Goal:** Implement constant-product AMM calculations with precision handling

**Files Created:**
- `/x/dex/keeper/amm.go` - Core AMM math functions

**Implementation:**

Constant product swap calculation:
    // CalculateSwapOutput computes output amount for constant product AMM
    // Formula: y_out = (y * x_in * (10000 - feeBps)) / (x * 10000 + x_in * (10000 - feeBps))
    // Uses integer math with proper rounding to prevent precision loss attacks
    func CalculateSwapOutput(
        reserveIn, reserveOut, amountIn sdk.Int,
        feeBps uint32,
    ) (amountOut sdk.Int, priceImpact sdk.Dec, err error) {
        if reserveIn.IsZero() || reserveOut.IsZero() {
            return sdk.ZeroInt(), sdk.ZeroDec(), ErrEmptyPool
        }
        if amountIn.IsZero() {
            return sdk.ZeroInt(), sdk.ZeroDec(), ErrZeroAmount
        }

        // Calculate fee-adjusted input
        feeMultiplier := sdk.NewInt(10000 - int64(feeBps))
        amountInWithFee := amountIn.Mul(feeMultiplier)

        // Constant product formula
        numerator := reserveOut.Mul(amountInWithFee)
        denominator := reserveIn.Mul(sdk.NewInt(10000)).Add(amountInWithFee)

        amountOut = numerator.Quo(denominator)

        // Calculate price impact
        spotPrice := sdk.NewDecFromInt(reserveOut).Quo(sdk.NewDecFromInt(reserveIn))
        executionPrice := sdk.NewDecFromInt(amountOut).Quo(sdk.NewDecFromInt(amountIn))
        priceImpact = spotPrice.Sub(executionPrice).Quo(spotPrice).Abs()

        return amountOut, priceImpact, nil
    }

Liquidity calculations with share minting:
    // CalculateLiquidityShares computes LP tokens for adding liquidity
    // First depositor: shares = sqrt(amountA * amountB) - MINIMUM_LIQUIDITY
    // Subsequent: shares = min(amountA/reserveA, amountB/reserveB) * totalShares
    func CalculateLiquidityShares(...) { ... }

**Validation:**
    go test ./x/dex/keeper/amm_test.go -v

    # Must include tests for:
    # - Normal swap calculation
    # - Zero/negative inputs (should error)
    # - Large numbers (no overflow)
    # - Fee calculation accuracy
    # - Price impact calculation
    # - Minimum liquidity constant

**Acceptance:** AMM math is correct for all test cases, handles edge cases,
no precision loss, fuzz tests pass.

---

[Additional milestones continue with same detail level...]

### Progress

- [x] `[2024-11-29 10:00]` Created plan structure ✓
- [x] `[2024-11-29 11:30]` Completed Pool type with validation ✓
- [ ] `[2024-11-29 14:00]` Implementing message types
- [ ] AMM math library
- [ ] Keeper methods
- [ ] Message handlers
- [ ] Integration tests

### Discoveries

**[2024-11-29]** Existing swap calculation in `/x/dex/keeper/swap.go:45`
has precision vulnerability - uses floating point division.
Must replace with integer math.

### Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-11-29 | Use basis points for fees | Integer math, no floating point errors, standard in DeFi |
| 2024-11-29 | Minimum liquidity lock | Prevents first depositor manipulation, Uniswap V2 pattern |

### Retrospective

[To be completed upon plan completion]
```

---

## Active Plans

<!-- Add active execution plans below this line -->
<!-- Each plan should follow the structure defined above -->
<!-- Delete plans when complete, or move to an archive section -->

---

## Completed Plans Archive

<!-- Move completed plans here with completion date -->

---

## Notes for Agents

1. **Read this file** at the start of complex work
2. **Create a plan** if the work warrants it
3. **Update progress** as you work
4. **Complete milestones fully** before moving on
5. **Never leave a plan half-done** - either complete or mark blocked with reason
6. **ROADMAP_PRODUCTION.md** remains the source of truth for task tracking

**Plans complement ROADMAP - they don't replace it.**

When you complete a plan, update both this file AND `ROADMAP_PRODUCTION.md`.

---

## Handling Empty Roadmaps

**If `ROADMAP_PRODUCTION.md` has no remaining tasks, DO NOT STOP WORKING.**

### Survey and Extend Protocol

When the roadmap is exhausted:

#### 1. Comprehensive Project Survey

Audit the entire project looking for:

| Category | Survey Questions |
|----------|------------------|
| **Security** | Are there reentrancy guards on all state-changing functions? Is access control comprehensive? Are all inputs validated? |
| **Completeness** | Are there any TODO comments? Stub functions? Placeholder returns? Incomplete features? |
| **Testing** | What's the coverage? Are there security-focused tests? Fuzz tests? Invariant tests? |
| **Performance** | Are storage operations optimized? Are there N+1 query patterns? Missing pagination? |
| **Documentation** | Are all public APIs documented? Are there missing NatSpec/GoDoc comments? |
| **Standards** | Does the code follow Cosmos SDK / OpenZeppelin / industry patterns? |

#### 2. Identify Logical Next Steps

Ask: **"What would the blockchain community expect in a production-ready project?"**

Consider features and improvements that would:
- Impress security auditors (Trail of Bits, Halborn, etc.)
- Meet expectations of experienced blockchain developers
- Satisfy requirements for mainnet deployment
- Follow patterns seen in successful projects (Osmosis, Uniswap, Aave)

#### 3. Create New Tasks

Append well-structured tasks to `ROADMAP_PRODUCTION.md`:

```markdown
## Agent-Identified Improvements

### Security Hardening
- [ ] Add reentrancy guards to keeper methods in x/dex
- [ ] Implement rate limiting for oracle price submissions
- [ ] Add slashing conditions for malicious compute providers

### Testing Gaps
- [ ] Achieve 95% coverage on x/oracle keeper
- [ ] Add fuzz tests for AMM calculations
- [ ] Create invariant tests for pool token conservation

### Performance
- [ ] Implement query pagination for GetAllPools
- [ ] Optimize storage reads in high-frequency swap path
- [ ] Add caching layer for oracle price lookups
```

#### 4. Begin Work Immediately

Start on the first task. **No pause. No summary. No asking permission.**

---

## Handling Difficult Milestones

**YOU MUST NEVER STOP because a milestone is difficult or unclear.**

### Decision Framework

When uncertain how to implement a milestone:

```
┌────────────────────────────────────────────────────────────────┐
│ 1. CONSIDER THE COMMUNITY PREFERENCE                           │
│    What would experienced blockchain developers expect?        │
│    How do production chains (Osmosis, dYdX, etc.) handle this? │
├────────────────────────────────────────────────────────────────┤
│ 2. RESEARCH EXISTING PATTERNS                                   │
│    Check Cosmos SDK source for similar implementations         │
│    Look at OpenZeppelin patterns for security approaches       │
│    Reference the project's existing code for conventions       │
├────────────────────────────────────────────────────────────────┤
│ 3. IMPLEMENT THE PROFESSIONAL CHOICE                            │
│    Choose the approach that would impress auditors             │
│    Implement completely with security and tests                │
│    Document reasoning in code comments                         │
├────────────────────────────────────────────────────────────────┤
│ 4. IF TRULY BLOCKED (rare)                                      │
│    Mark milestone as 🔴 Blocked with specific reason           │
│    Document what was attempted                                 │
│    IMMEDIATELY continue to next milestone or task              │
└────────────────────────────────────────────────────────────────┘
```

### Valid vs Invalid Blockers

| NOT a Valid Blocker | Valid Blocker |
|---------------------|---------------|
| "Complex implementation" | External API key required from user |
| "Not sure of best approach" | Third-party service is down |
| "Would take significant effort" | Hardware access needed |
| "Need to learn this first" | Explicit user decision required (rare) |
| "Tests are failing" | |

**Default to implementing. The bar for "blocked" is extremely high.**

### Blocked Milestone Format

```markdown
#### Milestone N: [Name]

**Status:** 🔴 Blocked

**Blocker:** [Specific, concrete issue - NOT "complex" or "unclear"]

**Attempted:**
- Approach 1: [Description and why it didn't work]
- Approach 2: [Description and why it didn't work]

**Needs:** [Specific external input/resource required]

**Date:** YYYY-MM-DD

---
[IMMEDIATELY proceed to next milestone]
```

---

## Continuous Operation Reminder

**The agent workflow is:**

1. Check `ROADMAP_PRODUCTION.md` for tasks
2. If tasks exist → Execute them completely
3. If no tasks → Survey project, add tasks, execute them
4. Check `PLANS.md` for active ExecPlans
5. If plans exist → Continue executing milestones
6. If plan complete → Update both files, start next task
7. **NEVER STOP** unless user explicitly says "stop"

**There are no time constraints. Quality and completeness are paramount.**
