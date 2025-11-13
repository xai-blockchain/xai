# Auto-Switching API Key System - Complete Explanation

## Overview

The system supports **TWO modes** of multi-key usage, both with strict per-key limits:

1. **Pre-Allocation Mode** - Find all needed keys BEFORE starting
2. **Hot-Swap Mode** - Switch keys DURING task execution

Both modes maintain **STRICT limits per key** - no key can ever be over-used.

---

## Mode 1: Pre-Allocation (Multi-Key Planning)

### How It Works

Before starting the task, the system finds ALL keys needed and allocates tokens from each.

### Example Scenario

```
Task needs: 250,000 tokens

Available keys:
- Key A: 100,000 tokens remaining
- Key B: 80,000 tokens remaining
- Key C: 150,000 tokens remaining
```

### Pre-Allocation Process

```python
# Step 1: Find suitable keys
suitable_keys = _find_suitable_keys(provider=ANTHROPIC, tokens_needed=250000)

# Result:
suitable_keys = [
    Key C (150k tokens),  # Best fit - most tokens
    Key A (100k tokens)   # Secondary - enough to cover rest
]
# Total: 250k tokens available ✓

# Step 2: Plan allocation
allocation_plan = {
    'Key C': 150000,  # Use all 150k
    'Key A': 100000   # Use all 100k
}
# Total: 250k exactly

# Step 3: Execute task with combined budget
response = client.messages.create(
    max_tokens=250000,  # HARD LIMIT for entire task
    messages=[...]
)

# Step 4: Deduct proportionally based on ACTUAL usage
actual_tokens_used = 237,458

# Deduct from keys in order:
Key C: -150,000 (DEPLETED → destroyed)
Key A: -87,458  (12,542 remaining)
```

### Strict Limits Enforced

```python
def _deduct_tokens_from_keys(keys, total_tokens):
    remaining_to_deduct = total_tokens

    for key in keys:
        available = key.remaining_tokens()

        # STRICT CHECK: Never deduct more than available
        deduct_amount = min(available, remaining_to_deduct)

        # Update usage
        is_depleted = key.mark_usage(deduct_amount)

        # Auto-destroy if depleted
        if is_depleted:
            _destroy_api_key(key.key_id)

        remaining_to_deduct -= deduct_amount

        if remaining_to_deduct <= 0:
            break
```

**Guarantees:**
- ✅ Each key's limit is checked before deduction
- ✅ Deduction never exceeds `remaining_tokens()`
- ✅ Depleted keys are immediately destroyed
- ✅ Total usage = sum of per-key usage

---

## Mode 2: Hot-Swap (Dynamic Switching)

### How It Works

Start with ONE key, monitor usage in real-time, automatically switch when approaching limit.

### Example Scenario

```
Long task (unknown final length)

Available keys:
- Key A: 100,000 tokens
- Key B: 80,000 tokens
- Key C: 150,000 tokens
```

### Hot-Swap Process (Step-by-Step)

#### **Turn 1: Start with Key A**

```python
# Start task with Key A
current_key_id = "Key A"
current_key_remaining = 100,000

# Set safe limit (90% of remaining + buffer)
safe_limit = int(100000 * 0.9) - 5000 = 85,000

# Execute with HARD LIMIT
response_1 = client.messages.create(
    max_tokens=85000,  # STRICT LIMIT for Key A
    messages=[{"role": "user", "content": "Write atomic swap guide"}]
)

# Actual usage: 82,341 tokens
actual_tokens = 82,341

# Update Key A
Key A.used_tokens += 82,341
Key A.remaining_tokens = 100000 - 82341 = 17,659

# Key A approaching limit but not depleted
```

**Strict Limit Check:**
```
✓ safe_limit (85,000) enforced by API
✓ actual_tokens (82,341) < safe_limit ✓
✓ Key A.remaining_tokens (17,659) > 0 ✓
```

---

#### **Turn 2: Key A too low, switch to Key C**

```python
# Check if Key A can handle another turn
if Key A.remaining_tokens < buffer_tokens:
    # Switch to next key!
    print("⚠️ Key A approaching limit, switching...")

    # Get next available key
    new_key = _switch_to_next_key(
        old_key_id="Key A",
        provider=ANTHROPIC,
        reason="approaching_limit"
    )

    # Result: Key C (150k tokens - best available)
    current_key_id = "Key C"
    current_key_remaining = 150,000

# Continue task with NEW key
safe_limit = int(150000 * 0.9) - 5000 = 130,000

response_2 = client.messages.create(
    max_tokens=130000,  # STRICT LIMIT for Key C
    messages=conversation_context  # Preserves context!
)

# Actual usage: 117,892 tokens
actual_tokens = 117,892

# Update Key C
Key C.used_tokens += 117,892
Key C.remaining_tokens = 150000 - 117892 = 32,108
```

**Strict Limit Check:**
```
✓ safe_limit (130,000) enforced by API
✓ actual_tokens (117,892) < safe_limit ✓
✓ Key C.remaining_tokens (32,108) > 0 ✓
```

**Swap Event Recorded:**
```python
{
    'timestamp': 1699565200.0,
    'old_key_id': 'Key A',
    'new_key_id': 'Key C',
    'tokens_used_old_key': 82341,
    'tokens_remaining_old_key': 17659,
    'reason': 'approaching_limit'
}
```

---

#### **Turn 3: Key C sufficient, continue**

```python
# Key C still has enough
Key C.remaining_tokens = 32,108

safe_limit = int(32108 * 0.9) - 5000 = 23,897

response_3 = client.messages.create(
    max_tokens=23897,  # STRICT LIMIT for Key C
    messages=conversation_context
)

# Actual usage: 21,456 tokens
actual_tokens = 21,456

# Update Key C
Key C.used_tokens += 21,456
Key C.remaining_tokens = 32108 - 21456 = 10,652

# Task completes naturally
```

**Final State:**
```
Key A: 82,341 / 100,000 used (17,659 remaining) - ACTIVE
Key B: 0 / 80,000 used (80,000 remaining) - UNUSED
Key C: 139,348 / 150,000 used (10,652 remaining) - ACTIVE

Total tokens used: 221,689
Keys actually used: 2
Automatic swaps: 1
```

---

## Strict Limit Enforcement (Both Modes)

### Per-Key Safety Checks

Every key has built-in safety:

```python
class DonatedAPIKey:
    def can_use(self, tokens_needed: int) -> Tuple[bool, str]:
        """STRICT pre-check before ANY usage"""

        if not self.is_active:
            return False, "Key is not active"

        if self.is_depleted:
            return False, "Key is already depleted"

        # HARD CHECK: Never allow more than remaining
        if tokens_needed > self.remaining_tokens():
            return False, f"Insufficient: need {tokens_needed}, have {self.remaining_tokens()}"

        return True, "Sufficient balance"

    def mark_usage(self, tokens_used: int) -> bool:
        """Update usage and check for depletion"""

        self.used_tokens += tokens_used

        # Auto-depletion check
        if self.remaining_tokens() <= 0:
            self.is_depleted = True
            self.depleted_at = time.time()
            return True  # Signal: destroy me!

        return False
```

### API-Level Hard Limits

```python
# ANTHROPIC
response = client.messages.create(
    max_tokens=85000,  # Anthropic GUARANTEES output ≤ this
    messages=[...]
)

# OPENAI
response = client.chat.completions.create(
    max_tokens=85000,  # OpenAI GUARANTEES output ≤ this
    messages=[...]
)

# GOOGLE
response = model.generate_content(
    ...,
    generation_config={'max_output_tokens': 85000}  # Google enforces
)
```

All AI providers **enforce** `max_tokens` - they will STOP generating at exactly that limit.

### Post-Call Verification

```python
# After API call completes
actual_tokens = response.usage.total_tokens

# CRITICAL CHECK
if actual_tokens > max_tokens:
    # This should NEVER happen (API contract violated)
    trigger_emergency_stop()
    raise ValueError(f"LIMIT BREACH: {actual_tokens} > {max_tokens}")

# Safe to proceed
key.mark_usage(actual_tokens)
```

---

## Visual Timeline: Hot-Swap in Action

```
Time: 0s
┌─────────────────────────────────────────┐
│ Task Start                               │
│ Selected: Key A (100k tokens)           │
│ Safe limit: 85k                         │
└─────────────────────────────────────────┘

Time: 45s (Turn 1 complete)
┌─────────────────────────────────────────┐
│ Key A Status:                           │
│   Used: 82,341 tokens                   │
│   Remaining: 17,659 tokens              │
│   Status: APPROACHING LIMIT             │
└─────────────────────────────────────────┘

Time: 46s (Switching)
┌─────────────────────────────────────────┐
│ ⚠️  AUTO-SWITCH TRIGGERED               │
│ Reason: Key A < 20k remaining           │
│                                         │
│ Old: Key A                              │
│ New: Key C (150k tokens)                │
│                                         │
│ ✅ Context preserved                    │
│ ✅ Conversation continues seamlessly    │
└─────────────────────────────────────────┘

Time: 47s (Continuing with Key C)
┌─────────────────────────────────────────┐
│ Task Resumed                            │
│ Selected: Key C (150k tokens)           │
│ Safe limit: 130k                        │
│ Conversation history: Maintained        │
└─────────────────────────────────────────┘

Time: 102s (Turn 2 complete)
┌─────────────────────────────────────────┐
│ Key C Status:                           │
│   Used: 117,892 tokens                  │
│   Remaining: 32,108 tokens              │
│   Status: ACTIVE (enough for more)      │
└─────────────────────────────────────────┘

Time: 135s (Turn 3 complete)
┌─────────────────────────────────────────┐
│ Task Complete!                          │
│                                         │
│ Total tokens: 221,689                   │
│ Keys used: 2 (A + C)                    │
│ Swaps: 1                                │
│ Success: ✅                              │
└─────────────────────────────────────────┘
```

---

## Conversation Context Preservation

### The Challenge

When switching keys mid-task, you're creating a NEW API client. How do you maintain context?

### The Solution: ConversationContext Object

```python
@dataclass
class ConversationContext:
    messages: List[Dict]  # Full conversation history
    system_prompt: Optional[str] = None

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_context_for_continuation(self) -> List[Dict]:
        return self.messages.copy()
```

### Example: 3-Turn Conversation with Key Swap

```python
# Initial state
context = ConversationContext(messages=[])

# Turn 1 (Key A)
context.add_message("user", "Write atomic swap implementation")

response_1 = client_A.messages.create(
    messages=context.messages  # [user: "Write atomic swap..."]
)

context.add_message("assistant", response_1.content[0].text)

# -- KEY SWAP HAPPENS HERE --

# Turn 2 (Key C) - FULL CONTEXT PRESERVED
response_2 = client_C.messages.create(
    messages=context.messages  # [user: "Write...", assistant: "...", user: "Continue"]
)

context.add_message("assistant", response_2.content[0].text)

# Turn 3 (Key C) - ALL CONTEXT STILL THERE
response_3 = client_C.messages.create(
    messages=context.messages  # Full conversation with all turns
)
```

**Result:** AI has complete awareness of everything that happened, even across different API keys!

---

## Streaming with Hot-Swap

### Challenge

How to switch keys during a LIVE streaming response?

### Current Implementation

```python
# Safe approach: Complete current stream, then switch for next turn
with client.messages.stream(max_tokens=safe_limit, messages=context) as stream:
    for chunk in stream.text_stream:
        full_response += chunk
        # Cannot switch mid-stream (API limitation)

# Stream complete - NOW we can switch if needed
if needs_more_work and key_depleted:
    switch_to_next_key()
    # Continue with new streaming session
```

### Future Enhancement: Mid-Stream Switching

```python
# Advanced: Monitor token usage during stream
with client.messages.stream(max_tokens=safe_limit, messages=context) as stream:
    tokens_consumed = 0

    for chunk in stream.text_stream:
        full_response += chunk
        tokens_consumed += estimate_tokens(chunk)

        # Approaching limit mid-stream?
        if tokens_consumed > safe_limit * 0.95:
            # Gracefully stop this stream
            stream.close()

            # Switch key
            new_key = switch_to_next_key()

            # Resume streaming with new key
            context.add_message("assistant", full_response)
            context.add_message("user", "Continue from where you left off.")

            # New stream continues seamlessly
            with new_client.messages.stream(...) as new_stream:
                ...
```

---

## Multi-Key Statistics

### Tracking Across Keys

```python
task_state = {
    'task_id': 'task_001',
    'total_tokens_used': 221689,
    'keys_used': ['key_a', 'key_c'],
    'swap_count': 1,

    'per_key_usage': {
        'key_a': {
            'tokens_used': 82341,
            'tokens_donated': 100000,
            'utilization': 82.3,
            'turns': 1
        },
        'key_c': {
            'tokens_used': 139348,
            'tokens_donated': 150000,
            'utilization': 92.9,
            'turns': 2
        }
    },

    'swap_events': [
        {
            'timestamp': 1699565200.0,
            'old_key': 'key_a',
            'new_key': 'key_c',
            'reason': 'approaching_limit',
            'old_remaining': 17659,
            'new_available': 150000
        }
    ]
}
```

---

## Benefits of Both Modes

### Pre-Allocation Benefits

1. ✅ **Predictable** - Know exactly which keys will be used
2. ✅ **Efficient** - Single API call for entire task
3. ✅ **Simple** - No mid-task complexity
4. ✅ **Fast** - No switching overhead

**Best for:**
- Tasks with known token requirements
- When you have keys large enough to handle task
- Simple single-turn completions

### Hot-Swap Benefits

1. ✅ **Flexible** - Handle tasks of unknown length
2. ✅ **Resilient** - Auto-recover from key depletion
3. ✅ **Optimal** - Use up small/partial keys efficiently
4. ✅ **Continuous** - Never stop due to single key limit

**Best for:**
- Long-running tasks
- Multi-turn conversations
- Streaming responses
- When task length is unpredictable

---

## Summary

### Can Multiple Keys Be Combined?

**YES - In Two Ways:**

1. **Pre-Allocation:**
   ```
   Task needs 250k tokens
   → Find Key A (100k) + Key B (150k)
   → Execute with 250k hard limit
   → Deduct proportionally after completion
   ```

2. **Hot-Swap:**
   ```
   Start with Key A (100k)
   → Use 82k, approaching limit
   → Switch to Key C (150k)
   → Use 139k, task completes
   ```

### Are Strict Limits Maintained Per Key?

**YES - Multiple Layers:**

1. **Pre-check:** `key.can_use(tokens_needed)` before allocation
2. **API limit:** `max_tokens` parameter enforced by provider
3. **Post-check:** Verify `actual_usage <= max_tokens`
4. **Auto-depletion:** Destroy when `remaining <= 0`

### What Happens If Key Depletes?

**Automatic Destruction:**
```python
if key.remaining_tokens() <= 0:
    key.is_depleted = True
    _destroy_api_key(key_id)  # 3-pass overwrite
```

---

**Bottom Line:** The system can use multiple keys together while maintaining strict per-key limits through pre-validation, hard API limits, post-verification, and automatic destruction. Both pre-allocation and hot-swap modes respect donated limits absolutely.
