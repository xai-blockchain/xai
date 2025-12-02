# Gas Sponsorship Rate Limiting

## Overview

The XAI blockchain's gas sponsorship system implements comprehensive multi-tier rate limiting to prevent burst attacks and abuse. This document describes the rate limiting architecture, configuration, and best practices.

## Problem Statement

Without proper rate limiting, gas sponsorship is vulnerable to burst attacks:

- **Daily Limit Drain**: An attacker could drain the entire daily limit (e.g., 1000 transactions) in seconds
- **High-Value Bursts**: Sponsor many high-gas transactions instantly to maximize damage
- **DoS Attacks**: Consume all sponsor capacity, blocking legitimate users
- **Cost Amplification**: Exploit any gas pricing inefficiencies at scale

## Solution: Multi-Tier Rate Limiting

The system implements a sliding window rate limiter with multiple time windows and gas amount tracking.

### Rate Limit Tiers

| Tier | Window | Purpose |
|------|--------|---------|
| **Per-Second** | 1 second | Prevents instant burst attacks |
| **Per-Minute** | 60 seconds | Limits sustained high-frequency abuse |
| **Per-Hour** | 3600 seconds | Controls medium-term usage patterns |
| **Per-Day** | 86400 seconds | Overall daily budget management |

### Gas Amount Limiting

In addition to transaction counts, the system tracks **total gas amounts** across all time windows:

- `max_gas_per_second`: Maximum total gas per second (all transactions combined)
- `max_gas_per_minute`: Maximum total gas per minute
- `max_gas_per_hour`: Maximum total gas per hour
- `max_gas_per_day`: Maximum total gas per day
- `max_gas_per_transaction`: Maximum gas for a single transaction

This prevents an attacker from sponsoring fewer but higher-value transactions to drain the budget quickly.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│ GasSponsor                                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Global Rate Limiter                                 │     │
│ │ - Applies to all users combined                     │     │
│ │ - Protects sponsor's total capacity                 │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐     │
│ │ Per-User Rate Limiters                              │     │
│ │ - User1: SlidingWindowRateLimiter                   │     │
│ │ - User2: SlidingWindowRateLimiter                   │     │
│ │ - User3: SlidingWindowRateLimiter                   │     │
│ │ - Isolates users from each other                    │     │
│ │ - Prevents one user from blocking others            │     │
│ └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Sliding Window Implementation

The `SlidingWindowRateLimiter` uses a time-ordered deque to track requests:

```python
requests: Deque[Tuple[timestamp, gas_amount]]
```

For each request, it:

1. **Cleanup**: Removes entries older than 24 hours
2. **Count Checks**: Counts requests in each time window (1s, 60s, 3600s, 86400s)
3. **Gas Checks**: Sums gas amounts in each time window
4. **Enforcement**: Rejects if any limit exceeded
5. **Recording**: Appends new request if approved

This provides accurate, real-time limiting without complex window management.

## Configuration

### Default Configuration

```python
RateLimitConfig(
    # Transaction count limits
    per_second=10,
    per_minute=100,
    per_hour=500,
    per_day=1000,

    # Gas amount limits
    max_gas_per_second=1.0,
    max_gas_per_minute=10.0,
    max_gas_per_hour=50.0,
    max_gas_per_day=100.0,

    # Per-transaction limits
    max_gas_per_transaction=0.1,
    max_cost_per_transaction=1.0
)
```

### Custom Configuration

```python
from xai.core.account_abstraction import RateLimitConfig, GasSponsor

# Create custom config
config = RateLimitConfig(
    per_second=5,           # More restrictive
    per_minute=50,
    per_hour=200,
    per_day=500,
    max_gas_per_second=0.5,
    max_gas_per_minute=5.0,
    max_gas_per_hour=25.0,
    max_gas_per_day=50.0,
    max_gas_per_transaction=0.05
)

# Create sponsor with custom config
sponsor = GasSponsor(
    sponsor_address="XAI...",
    budget=100.0,
    rate_limit_config=config
)
```

### Updating Configuration

```python
# Update configuration at runtime
new_config = RateLimitConfig(per_second=20, per_minute=200)
sponsor.update_rate_limit_config(new_config)
```

## Usage

### Registering a Sponsor with Rate Limiting

```python
from xai.core.account_abstraction import (
    SponsoredTransactionProcessor,
    RateLimitConfig
)

processor = SponsoredTransactionProcessor()

# Configure strict rate limits
config = RateLimitConfig(
    per_second=5,
    per_minute=50,
    per_hour=200,
    per_day=500,
    max_gas_per_second=0.5,
    max_gas_per_transaction=0.05
)

# Register sponsor
sponsor = processor.register_sponsor(
    sponsor_address="XAI1234...",
    sponsor_public_key="04abc...",
    budget=100.0,
    rate_limit_config=config
)
```

### Handling Rate Limit Errors

```python
from xai.core.account_abstraction import SponsorshipResult

# Validate transaction
validation = processor.validate_sponsored_transaction(tx)

if validation.result == SponsorshipResult.RATE_LIMIT_EXCEEDED:
    # Get retry-after time
    retry_after = validation.retry_after

    print(f"Rate limit exceeded. Retry after {retry_after:.1f} seconds")

    # Return appropriate HTTP header
    response.headers['Retry-After'] = str(int(retry_after))
    return 429  # Too Many Requests
```

### Monitoring Rate Limit Usage

```python
# Get global usage statistics
stats = sponsor.get_stats()
print(f"Global usage: {stats['global_usage']}")

# Get per-user usage
user_usage = sponsor.get_user_usage("XAIuser123")
print(f"User rate limit usage: {user_usage['rate_limit_usage']}")

# Check retry-after for a user
retry_after = sponsor.get_retry_after("XAIuser123")
if retry_after > 0:
    print(f"User must wait {retry_after:.1f} seconds")
```

## Security Considerations

### Attack Scenarios Prevented

1. **Instant Burst Attack**
   - **Attack**: Send 1000 requests in 1 second
   - **Prevention**: Per-second limit (e.g., 10 requests/sec) blocks after 10 requests
   - **Result**: Attacker gets maximum 10 transactions instead of 1000

2. **High-Value Burst Attack**
   - **Attack**: Send 100 high-gas transactions instantly
   - **Prevention**: Gas amount limits (e.g., 1.0 gas/sec) block when limit reached
   - **Result**: Attacker limited by total gas value, not just count

3. **Sustained High-Frequency Attack**
   - **Attack**: Send 10 requests/sec for 10 minutes = 6000 requests
   - **Prevention**: Per-minute limit (e.g., 100 requests/min) blocks after 100
   - **Result**: Attacker limited to 100 requests per minute

4. **DoS via Capacity Exhaustion**
   - **Attack**: One user consumes all sponsor capacity
   - **Prevention**: Per-user rate limiters isolate users
   - **Result**: Other users can still get sponsored transactions

### Best Practices

1. **Set Conservative Limits**
   - Start with restrictive limits and increase based on usage patterns
   - Monitor metrics to detect legitimate users hitting limits

2. **Use Gas Amount Limits**
   - Always configure gas amount limits, not just transaction counts
   - Prevents high-value transaction exploitation

3. **Monitor and Alert**
   - Set up alerts for rate limit violations
   - Track patterns to detect abuse attempts

4. **Adjust Dynamically**
   - Update configuration based on observed attack patterns
   - Use different configs for different risk levels

5. **Log Rejections**
   - Log all rate limit rejections with details
   - Analyze logs to identify attackers and patterns

## Integration with Transaction Processing

The rate limiting is integrated into the transaction sponsorship flow:

```
1. User requests sponsored transaction
   ↓
2. Check blacklist/whitelist
   ↓
3. Check budget
   ↓
4. Check per-transaction limits
   ↓
5. Check GLOBAL rate limits (all users) ← NEW
   ↓
6. Check PER-USER rate limits (this user) ← NEW
   ↓
7. Approve sponsorship
   ↓
8. Deduct from budget
   ↓
9. Record in rate limiters ← NEW
```

## Monitoring and Observability

### Metrics to Track

- **Rate Limit Hit Rate**: % of requests rejected due to rate limiting
- **Window Distribution**: Which time window is most commonly exceeded
- **Per-User Patterns**: Users frequently hitting limits (potential abuse)
- **Gas Usage Patterns**: Correlation between transaction count and gas usage

### Logging

Rate limit events are logged with structured metadata:

```python
# Approval
logger.info("Transaction sponsored", extra={
    "event": "gas_sponsor.sponsored",
    "user": "XAI...",
    "gas_amount": 0.01,
    "remaining_budget": 99.99
})

# Rejection
logger.warning("Sponsorship rejected: global rate limit exceeded", extra={
    "event": "gas_sponsor.rejected",
    "reason": "global_rate_limit",
    "user": "XAI...",
    "retry_after_seconds": 0.5,
    "gas_requested": 0.01
})
```

## Performance Considerations

### Memory Usage

Each rate limiter stores timestamps in a deque:

- **Global limiter**: One deque per sponsor
- **Per-user limiters**: One deque per user (per sponsor)
- **Memory per entry**: ~24 bytes (timestamp + gas amount)
- **Maximum entries**: Limited by daily transaction limit

Example: 1000 transactions/day × 24 bytes = 24 KB per limiter

With 100 active users: 100 × 24 KB = 2.4 MB

### Computational Complexity

- **Cleanup**: O(k) where k = expired entries
- **Count checks**: O(n) where n = total entries in deque
- **Sum checks**: O(n)
- **Overall per request**: O(n) where n ≤ daily limit

For typical daily limits (1000), this is negligible.

### Optimizations

The implementation includes several optimizations:

1. **Lazy cleanup**: Only removes old entries when needed
2. **Early termination**: Checks fail-fast on first exceeded limit
3. **Shared config**: Config objects shared across limiters

## Testing

Comprehensive test coverage includes:

- Per-second, minute, hour, day limit enforcement
- Gas amount limiting across all windows
- Per-user isolation
- Global vs per-user interaction
- Burst attack prevention scenarios
- Retry-after calculations
- Backwards compatibility with legacy code

See `tests/xai_tests/unit/test_rate_limiting.py` for full test suite.

## Migration Guide

### From Legacy Rate Limiting

**Before** (only daily limit):

```python
sponsor = GasSponsor(
    "XAI1234",
    budget=100.0,
    rate_limit=50  # Only daily limit
)
```

**After** (multi-tier limits):

```python
config = RateLimitConfig(
    per_second=5,
    per_minute=50,
    per_hour=200,
    per_day=500  # Same as old rate_limit
)

sponsor = GasSponsor(
    "XAI1234",
    budget=100.0,
    rate_limit_config=config
)
```

**Backwards Compatible** (automatic migration):

```python
# Old code still works - creates default config
sponsor = GasSponsor(
    "XAI1234",
    budget=100.0,
    rate_limit=50
)
# Now has multi-tier limits with per_day=50
```

## References

- [SWC-128: DoS with Block Gas Limit](https://swcregistry.io/docs/SWC-128)
- [Rate Limiting Best Practices (OWASP)](https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks)
- [Sliding Window Rate Limiting](https://en.wikipedia.org/wiki/Rate_limiting)
- XAI Gas Sponsorship Architecture (Task 178)
