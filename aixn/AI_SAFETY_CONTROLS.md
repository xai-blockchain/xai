# AI Safety Controls

Instant stop capabilities for all AI operations.

## Features

**Personal AI Controls**
- Cancel any Personal AI request instantly
- User can stop AI mid-execution
- No confirmation needed

**Trading Bot Controls**
- Emergency stop for trading bot
- Stops all active trades immediately
- Prevents new trades until restarted

**Governance AI Controls**
- Pause Governance AI tasks
- Resume when ready
- Requires authorization

**Global Emergency Stop**
- Stops ALL AI operations immediately
- Use only for security threats or critical bugs
- Requires authorization to deactivate

## API Endpoints

```
POST /ai/cancel-request/<request_id>         - Cancel Personal AI request
GET  /ai/request-status/<request_id>         - Check if request cancelled
POST /ai/emergency-stop/trading-bot          - Emergency stop trading bot
POST /ai/stop-all-trading-bots               - Stop ALL trading bots
POST /ai/pause-governance-task/<task_id>     - Pause Governance AI task
POST /ai/resume-governance-task/<task_id>    - Resume Governance AI task
GET  /ai/governance-task-status/<task_id>    - Check if task paused
POST /ai/emergency-stop/global               - Global AI emergency stop
POST /ai/emergency-stop/deactivate           - Deactivate emergency stop
POST /ai/safety-level                        - Set AI safety level
GET  /ai/safety-status                       - Get current safety status
GET  /ai/active-operations                   - List active AI operations

GET  /ai/safety-callers                      - List authorized safety callers
POST /ai/safety-callers                      - Add a new safety caller identifier
DELETE /ai/safety-callers/<identifier>       - Revoke a caller from the safety list
```

## Examples

### Cancel Personal AI Request

```bash
POST /ai/cancel-request/personal_ai_XAI1a2b3c_1234567890
{
  "user_address": "XAI1a2b3c..."
}
```

### Emergency Stop Trading Bot

```bash
POST /ai/emergency-stop/trading-bot
{
  "user_address": "XAI1a2b3c..."
}
```

### Global Emergency Stop

```bash
POST /ai/emergency-stop/global
{
  "reason": "security_threat",
  "details": "Unexpected AI behavior detected",
  "activator": "system"
}
```

## Safety Levels

- **NORMAL**: Normal AI operations
- **CAUTION**: Elevated monitoring
- **RESTRICTED**: Limited AI operations
- **EMERGENCY_STOP**: All AI stopped
- **LOCKDOWN**: All AI disabled, manual only

## How It Works

1. All AI operations are registered when they start
2. User can cancel at any time via API
3. AI operations check for cancellation at multiple points
4. Request is marked as completed when done
5. Emergency stop halts all operations immediately

Philosophy: Users must have instant control over AI affecting their assets.

## Authorization

- Only hosted identities approved by the governance DAO, security committee, or AI safety team can change the global safety level.
- Calls to `/ai/safety-level` must include the caller identifier (`activator`) in the trusted list; unauthorized attempts are rejected immediately.
- The safety controller exposes `authorize_safety_caller` and `revoke_safety_caller` utilities so trusted actors can be updated without redeploying the node.
