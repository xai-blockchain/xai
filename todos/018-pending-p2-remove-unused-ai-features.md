# YAGNI: Remove Unused AI Features (~2,000 Lines)

---
status: pending
priority: p2
issue_id: 018
tags: [simplification, yagni, code-quality, code-review]
dependencies: []
---

## Problem Statement

Two large AI feature modules are barely used in the codebase, adding ~2,000 lines of unnecessary complexity:

1. `multi_ai_collaboration.py` (1,058 lines) - Only 1 import in entire codebase
2. `ai_node_operator_questioning.py` (995 lines) - Only imported by one wrapper file

## Findings

### multi_ai_collaboration.py (1,058 lines)

**Purpose:** Elaborate system for 2-3 AIs working together with peer review, voting, merging

**Usage:** Found only **1 import** in `ai_executor_with_questioning.py`

**Contains:**
- 6 Enums: CollaborationStrategy, AIRole, etc.
- 5 Dataclasses: AIContribution, AIPeerReview, CollaborativeTask, etc.
- Complex peer review, voting, merging systems

### ai_node_operator_questioning.py (995 lines)

**Purpose:** Allows node operators to question AI decisions before execution

**Usage:** Only imported by `ai_executor_with_questioning.py`

**Contains:**
- Complex voting system
- Timeout/override mechanisms
- Elaborate state machines

### Impact

- 2,053 lines of code to maintain
- Complex dependencies to manage
- Testing overhead
- Cognitive load for developers

## Proposed Solutions

### Option A: Delete Entirely (Recommended)
**Effort:** Small | **Risk:** Low

```bash
# Remove unused files
rm src/xai/core/multi_ai_collaboration.py
rm src/xai/core/ai_node_operator_questioning.py

# Update any imports in ai_executor_with_questioning.py
# Either remove the file or simplify to basic functionality
```

### Option B: Archive for Future
**Effort:** Small | **Risk:** Low

```bash
# Move to archive directory
mkdir -p src/xai/archive/
mv src/xai/core/multi_ai_collaboration.py src/xai/archive/
mv src/xai/core/ai_node_operator_questioning.py src/xai/archive/
```

## Acceptance Criteria

- [ ] Unused files removed or archived
- [ ] No import errors after removal
- [ ] All tests pass
- [ ] ~2,000 lines removed from production code

## Resources

- [YAGNI Principle](https://en.wikipedia.org/wiki/You_aren%27t_gonna_need_it)
- Code simplicity review findings
