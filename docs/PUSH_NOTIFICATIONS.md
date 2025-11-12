# Reminder Webhooks & Push Hooks

The `scripts/wallet_reminder_daemon.py` script now supports optional HTTP
callbacks so you can relay “safe & secure wallet available” reminders to
mobile push services, Discord bots, etc.

## Environment Variables

- `XAI_NOTIFICATION_WEBHOOK` – when set, each reminder (and the daily
  summary) is sent to this HTTPS URL as JSON:

  ```json
  {
    "type": "wallet_reminder",
    "identifier": "miner_123",
    "notification": {
      "message": "🎁 UNCLAIMED WALLET AVAILABLE!",
      "details": "Daily reminder...",
      "action": "Call POST /claim-wallet..."
    }
  }
  ```

- `XAI_NOTIFICATION_LOG_JSON=1` – if no webhook is configured, setting
  this flag prints each reminder as JSON (easy to pipe into another tool).

## Scheduling Recap

```bash
# Cron (Linux)
0 5 * * * /usr/bin/python /path/to/Crypto/scripts/wallet_reminder_daemon.py

# Windows Task Scheduler → “Program/script” = python,
# Arguments = C:\Users\...\Crypto\scripts\wallet_reminder_daemon.py
```

Pairing the webhook with the mobile cache summary lets you display native
push notifications whenever a user’s wallet is ready or a reminder is due.
