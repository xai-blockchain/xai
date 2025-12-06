# EVM Interpreter: No Jump Destination Cache

---
status: pending
priority: p2
issue_id: 015
tags: [performance, evm, smart-contracts, code-review]
dependencies: [009]
---

## Problem Statement

Jump destinations are recomputed on **every contract execution** by scanning the entire bytecode. For popular contracts, this wastes millions of CPU cycles per block.

## Findings

### Location
**File:** `src/xai/core/vm/evm/interpreter.py` (Lines 266-287)

### Evidence

```python
def _compute_jump_destinations(self, code: bytes) -> set:
    jump_dests = set()
    i = 0
    while i < len(code):  # Full scan
        op = code[i]
        if op == Opcode.JUMPDEST:
            jump_dests.add(i)
        if is_push(op):
            i += get_push_size(op)
        i += 1
    return jump_dests  # Not cached!
```

### Performance Impact

- Large contract (24KB): ~24,000 iterations per call
- Popular contract (100 calls/block): 2.4M iterations per block
- Pure computational waste - results never cached

## Proposed Solutions

### Option A: Hash-Based Cache (Recommended)
**Effort:** Small | **Risk:** Low

```python
class EVMInterpreter:
    def __init__(self):
        self._jump_dest_cache: Dict[str, set] = {}

    def _compute_jump_destinations(self, code: bytes) -> set:
        code_hash = hashlib.sha256(code).hexdigest()
        if code_hash in self._jump_dest_cache:
            return self._jump_dest_cache[code_hash]

        jump_dests = set()
        i = 0
        while i < len(code):
            op = code[i]
            if op == Opcode.JUMPDEST:
                jump_dests.add(i)
            if is_push(op):
                i += get_push_size(op)
            i += 1

        self._jump_dest_cache[code_hash] = jump_dests
        return jump_dests
```

## Acceptance Criteria

- [ ] Jump destinations cached by code hash
- [ ] Cache lookup instead of recomputation
- [ ] LRU eviction for memory management
- [ ] Benchmark: 100 executions of same contract <10ms total

## Resources

- Related: Issue 009 (Bytecode caching)
