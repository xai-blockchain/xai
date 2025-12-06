# Replace 2,271 Print Statements with Structured Logging

---
status: pending
priority: p1
issue_id: 011
tags: [code-quality, logging, observability, code-review]
dependencies: []
---

## Problem Statement

The codebase contains **2,271 print statements** across 100+ files. Print statements cannot be filtered, rotated, or sent to monitoring systems, making production debugging impossible.

## Findings

### Files with Heavy Print Usage

| File | Print Count | Severity |
|------|-------------|----------|
| `src/xai/wallet/cli.py` | 156 | HIGH |
| `src/xai/core/ai_governance.py` | 98 | HIGH |
| `src/xai/test_ai_safety_controls.py` | 79 | MEDIUM |
| `src/xai/core/multi_ai_collaboration.py` | 78 | HIGH |
| `src/xai/core/ai_node_operator_questioning.py` | 71 | HIGH |
| `src/xai/core/blockchain_loader.py` | 71 | HIGH |
| `src/xai/cli/ai_commands.py` | 60 | HIGH |
| `src/xai/cli/enhanced_cli.py` | 59 | HIGH |
| `src/xai/create_founder_wallets.py` | 47 | MEDIUM |
| `src/xai/network/peer_manager.py` | 41 | HIGH |

### Impact

- **No log levels** - cannot filter debug vs error messages
- **No timestamps** - cannot correlate events
- **No structured data** - cannot query logs
- **No rotation** - logs fill disk
- **No remote shipping** - cannot use ELK/Datadog/etc
- **Thread unsafe** - print can interleave in multi-threaded code

## Proposed Solutions

### Option A: Use Existing Structured Logger (Recommended)
**Effort:** Medium | **Risk:** Low

The project already has `structured_logger.py` - use it consistently:

```python
# Before
print(f"Block {block.index} added successfully")
print(f"Error processing transaction: {e}")

# After
from xai.core.structured_logger import get_structured_logger

logger = get_structured_logger(__name__)

logger.info("Block added", block_index=block.index)
logger.error("Transaction processing failed", error=str(e), exc_info=True)
```

### Option B: Automated Conversion Script
**Effort:** Small | **Risk:** Medium

Create script to auto-convert simple print statements:

```python
#!/usr/bin/env python3
import re
import sys

def convert_print_to_log(content: str) -> str:
    # Add logger import if not present
    if "get_structured_logger" not in content:
        import_line = "from xai.core.structured_logger import get_structured_logger\n"
        import_line += "logger = get_structured_logger(__name__)\n\n"
        # Add after other imports

    # Convert print to logger.info
    content = re.sub(
        r'print\(f"([^"]+)"\)',
        r'logger.info("\1")',
        content
    )

    # Convert print with error patterns to logger.error
    content = re.sub(
        r'print\(f"(Error|Failed|Exception)[^"]+"\)',
        r'logger.error("\1")',
        content
    )

    return content
```

### Option C: CLI Exception - Keep Print for User Output
**Effort:** Small | **Risk:** Low

For CLI tools (`wallet/cli.py`, `cli/main.py`), print is acceptable for user-facing output. But internal logic must use logging:

```python
# CLI output - OK to use print
def main():
    print("XAI Wallet CLI v1.0")
    print("=" * 40)

# Internal logic - MUST use logging
def process_transaction(tx):
    logger.debug("Processing transaction", tx_id=tx.id)
    # ...
    logger.info("Transaction processed", tx_id=tx.id, status="success")
```

## Recommended Action

1. **Week 1:** Convert core modules (blockchain.py, node.py, transaction.py)
2. **Week 2:** Convert network modules (peer_manager.py, node_p2p.py)
3. **Week 3:** Convert AI modules (ai_governance.py, ai_safety_controls.py)
4. **Week 4:** Convert remaining files, audit for completeness

## Technical Details

**Affected Components:**
- All Python modules with print statements
- Test files (can keep print for test output)

**Database Changes:** None

## Acceptance Criteria

- [ ] Zero print() in production code paths
- [ ] All logs use structured logger
- [ ] Log levels appropriate (debug, info, warning, error)
- [ ] CLI tools exempt for user-facing output
- [ ] Test logs can use print or logger

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by pattern-recognition agent | 2,271 print statements found |

## Resources

- `src/xai/core/structured_logger.py` - existing logger implementation
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- ROADMAP_PRODUCTION.md: "Convert remaining ~1,650 print() statements"
