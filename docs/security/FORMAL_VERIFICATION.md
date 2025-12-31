# Formal Verification Requirements

**Version:** 1.0.0
**Last Updated:** 2025-12-30

## Overview

This document outlines the formal verification strategy for critical XAI blockchain components.

## Verification Targets

### Priority 1: Must Verify Before Mainnet

| Component | Property | Method |
|-----------|----------|--------|
| Consensus | No double-spend | Model checking |
| Signatures | ECDSA correctness | Proof assistant |
| State Machine | Transition validity | TLA+ |
| UTXO Set | Balance invariants | Property testing |

### Priority 2: Should Verify

| Component | Property | Method |
|-----------|----------|--------|
| Fork Choice | Heaviest chain selection | Model checking |
| Fee Market | EIP-1559 invariants | SMT solving |
| DeFi | AMM invariants | Formal proofs |

## Verification Methods

### 1. Model Checking (TLA+)

**Applicable To:**
- Consensus protocol
- State transitions
- P2P message ordering

**Tool:** TLA+ Toolbox

**Example Specification:**
```tla
--------------------------- MODULE Consensus ---------------------------
EXTENDS Integers, Sequences

VARIABLES chain, pending_blocks

TypeInvariant ==
    /\ chain \in Seq(Block)
    /\ pending_blocks \in SUBSET Block

SafetyInvariant ==
    \A i, j \in 1..Len(chain):
        i /= j => chain[i].hash /= chain[j].hash

NoDoubleSpend ==
    \A tx1, tx2 \in AllTransactions:
        tx1.input = tx2.input => tx1 = tx2
========================================================================
```

### 2. Property-Based Testing (Hypothesis)

**Applicable To:**
- Transaction validation
- Serialization/deserialization
- Cryptographic operations

**Current Coverage:**
- 3,596 property-based test cases
- Tests in `tests/xai_tests/property/`

**Example:**
```python
@given(st.binary(min_size=1, max_size=1000))
def test_signature_roundtrip(message: bytes):
    wallet = Wallet()
    signature = wallet.sign_message(message)
    assert wallet.verify_signature(message, signature, wallet.public_key)
```

### 3. SMT Solving (Z3)

**Applicable To:**
- Arithmetic overflow checking
- Constraint satisfaction
- Path feasibility

**Tool:** Z3 Prover

### 4. Proof Assistants (Coq/Lean)

**Applicable To:**
- Cryptographic primitives
- Core algorithms

**Priority Proofs:**
1. ECDSA signature verification
2. Merkle tree construction
3. Difficulty adjustment

## Invariants to Verify

### Consensus Invariants

```
INV-C1: No two valid blocks at same height have same hash
INV-C2: Chain always has monotonically increasing heights
INV-C3: Every block references a valid previous block
INV-C4: Genesis block is immutable
```

### Transaction Invariants

```
INV-T1: sum(inputs) >= sum(outputs) + fee
INV-T2: All inputs reference existing UTXOs
INV-T3: No UTXO spent twice in same block
INV-T4: Signatures validate against public keys
INV-T5: Nonces are sequential per address
```

### State Invariants

```
INV-S1: Total supply <= MAX_SUPPLY
INV-S2: sum(all_balances) == total_supply
INV-S3: No negative balances
INV-S4: UTXO set consistent with chain
```

### DeFi Invariants

```
INV-D1: AMM: x * y = k (constant product)
INV-D2: Flash loans repaid in same tx
INV-D3: Collateral ratio >= minimum
INV-D4: No tokens created from nothing
```

## Verification Status

### Verified Properties

| Property | Method | Status | Evidence |
|----------|--------|--------|----------|
| Signature malleability fix | Testing | ✅ | `test_crypto_utils.py` |
| Double-spend detection | Testing | ✅ | `test_utxo_double_spend.py` |
| Overflow protection | Testing | ✅ | `test_safe_math.py` |
| Canonical signatures | Testing | ✅ | `test_ecdsa_edge_cases.py` |

### Pending Verification

| Property | Method | Status | Assignee |
|----------|--------|--------|----------|
| Consensus liveness | TLA+ | 🔄 Planned | TBD |
| Fork choice rule | Model check | 🔄 Planned | TBD |
| EVM opcode semantics | Coq | 🔄 Planned | TBD |

## Tooling Setup

### TLA+ Installation

```bash
# Install TLA+ Toolbox
wget https://github.com/tlaplus/tlaplus/releases/latest
# Or use VS Code extension: vscode-tlaplus
```

### Z3 Installation

```bash
pip install z3-solver
```

### Hypothesis (Already Installed)

```bash
pip install hypothesis
# Already in requirements.txt
```

## Verification Workflow

### 1. Specification Phase

1. Identify critical property
2. Write formal specification
3. Review with team
4. Document assumptions

### 2. Verification Phase

1. Run verification tool
2. Analyze counterexamples
3. Refine model or fix code
4. Iterate until verified

### 3. Maintenance Phase

1. Update specs with code changes
2. Re-verify on major updates
3. Track verification coverage

## CI/CD Integration

### Automated Verification

```yaml
# .github/workflows/verify.yml
name: Formal Verification
on: [push, pull_request]

jobs:
  property-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Hypothesis tests
        run: pytest tests/xai_tests/property/ -v

  invariant-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run invariant tests
        run: pytest tests/xai_tests/invariants/ -v
```

## References

### Academic Papers

1. "The Science of the Blockchain" - Tschorsch & Scheuermann
2. "Formal Verification of Smart Contracts" - Hirai
3. "Modeling Bitcoin in TLA+" - Pirlea & Rosu

### Tools Documentation

- TLA+: https://lamport.azurewebsites.net/tla/tla.html
- Z3: https://github.com/Z3Prover/z3
- Hypothesis: https://hypothesis.readthedocs.io
- Coq: https://coq.inria.fr

---

*Formal verification is an ongoing process that improves with each release.*
