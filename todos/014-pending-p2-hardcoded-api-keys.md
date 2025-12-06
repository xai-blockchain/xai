# Hardcoded API Keys in Example Code

---
status: pending
priority: p2
issue_id: 014
tags: [security, credentials, configuration, code-review]
dependencies: []
---

## Problem Statement

Test/example API keys are hardcoded in source files. While these appear to be placeholders, they demonstrate insecure patterns and could lead to accidental credential commits.

## Findings

### Locations

| File | Line | Pattern |
|------|------|---------|
| `src/xai/core/ai_trading_bot.py` | 954 | `user_api_key="YOUR_ANTHROPIC_API_KEY_HERE"` |
| `src/xai/core/secure_api_key_manager.py` | 607 | `api_key="sk-ant-api03-test-key-123456789..."` |
| `src/xai/core/ai_pool_with_strict_limits.py` | 1070 | `api_key="sk-ant-api03-test-key-123456789"` |

### Impact

- Demonstrates insecure pattern to developers
- Test keys may accidentally be used in production
- If real keys are committed, attackers can extract them from git history

## Proposed Solutions

### Option A: Environment Variables (Recommended)
**Effort:** Small | **Risk:** Low

```python
# Before
api_key = "sk-ant-api03-test-key-123456789"

# After
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable required")
```

### Option B: Configuration File
**Effort:** Small | **Risk:** Low

```python
# config/secrets.example.yaml (committed)
anthropic_api_key: "YOUR_KEY_HERE"

# config/secrets.yaml (gitignored)
anthropic_api_key: "sk-actual-key..."
```

## Acceptance Criteria

- [ ] No hardcoded API keys in source code
- [ ] All secrets loaded from environment or config
- [ ] Example configs use clear placeholders
- [ ] Pre-commit hook detects API key patterns

## Resources

- [12-Factor App Config](https://12factor.net/config)
