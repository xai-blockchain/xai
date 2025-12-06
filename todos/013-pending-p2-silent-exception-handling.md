# Silent Exception Swallowing - 37 Files with except: pass

---
status: pending
priority: p2
issue_id: 013
tags: [code-quality, error-handling, debugging, code-review]
dependencies: []
---

## Problem Statement

37 files contain `except: pass` or `except Exception: pass` patterns that silently swallow errors. This makes debugging and troubleshooting extremely difficult and hides production issues.

## Findings

### Affected Files

- `src/xai/openai.py`
- `src/xai/exchange.py`
- `src/xai/core/blockchain.py`
- `src/xai/core/node.py`
- `src/xai/core/wallet.py`
- `src/xai/core/ai_governance.py`
- `src/xai/core/vm/evm/abi.py` (multiple fallback attempts)
- And 30 more files...

### Example Pattern

```python
# src/xai/core/vm/evm/abi.py - Lines 28-50
try:
    import sha3
    k = sha3.keccak_256()
    k.update(data)
    return k.digest()
except Exception:
    pass  # Silent failure, tries next provider
```

### Impact

- Production issues invisible until catastrophic failure
- Debug and troubleshooting extremely difficult
- Error patterns cannot be monitored
- Silent data corruption possible

## Proposed Solutions

### Option A: Add Logging to All Exception Handlers (Recommended)
**Effort:** Medium | **Risk:** Low

```python
# Before
try:
    process_data()
except Exception:
    pass

# After
try:
    process_data()
except Exception as e:
    logger.warning("Data processing failed, using fallback", error=str(e), exc_info=True)
```

### Option B: Specific Exception Types
**Effort:** Medium | **Risk:** Low

```python
# Before
try:
    import sha3
except Exception:
    pass

# After
try:
    import sha3
except ImportError:
    logger.debug("sha3 not available, using fallback")
except Exception as e:
    logger.error("Unexpected error loading sha3", exc_info=True)
    raise
```

## Acceptance Criteria

- [ ] No bare `except: pass` in codebase
- [ ] All exceptions logged with context
- [ ] Specific exception types where possible
- [ ] Critical exceptions re-raised after logging

## Resources

- [Python Exception Handling Best Practices](https://docs.python.org/3/tutorial/errors.html)
