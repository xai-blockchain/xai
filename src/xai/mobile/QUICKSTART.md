# Push Notifications Quick Start Guide

Get push notifications working in 5 minutes.

## 1. Environment Setup

Set your API keys:

```bash
export XAI_FCM_SERVER_KEY="your_firebase_server_key"
export XAI_APNS_KEY_ID="your_apns_key_id"
export XAI_APNS_TEAM_ID="your_team_id"
export XAI_APNS_KEY_PATH="/path/to/apns_key.p8"
```

## 2. Import and Initialize

```python
from xai.mobile import PushNotificationService, DeviceRegistry

# Initialize
registry = DeviceRegistry(db_path="devices.db")
service = PushNotificationService(registry)
```

## 3. Register a Device

```python
device = registry.register_device(
    user_address="XAI1234567890abcdef...",
    device_token="fcm_or_apns_token_here",
    platform="android",  # or "ios", "web"
)
```

## 4. Send Notification

```python
import asyncio

async def send():
    results = await service.send_transaction_notification(
        address="XAI1234567890abcdef...",
        tx_hash="0xabc123",
        amount="10.5 XAI",
        from_address="XAI9876...",
        to_address="XAI1234...",
        is_incoming=True
    )

    for result in results:
        print(f"Success: {result.success}")

asyncio.run(send())
```

## 5. REST API

Register device via HTTP:

```bash
curl -X POST http://localhost:8080/notifications/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "XAI1234567890abcdef...",
    "device_token": "your_device_token",
    "platform": "android"
  }'
```

## 6. Test Notification

```bash
curl -X POST http://localhost:8080/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"device_token": "your_device_token"}'
```

## That's It!

For more details:
- Full guide: `PUSH_NOTIFICATIONS.md`
- API reference: `API_ENDPOINTS.md`
- Examples: `notification_example.py`
- Tests: `tests/xai_tests/unit/test_push_notifications.py`

## Notification Types

- `transaction` - Incoming/outgoing payments
- `confirmation` - Transaction confirmations
- `security` - Security alerts
- `price_alert` - Price notifications
- `governance` - Governance updates

## Mobile Integration

### Android (Kotlin)
```kotlin
val token = FirebaseMessaging.getInstance().token.await()
// POST to /notifications/register with token
```

### iOS (Swift)
```swift
func application(_ application: UIApplication,
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let tokenString = deviceToken.map { String(format: "%02x", $0) }.joined()
    // POST to /notifications/register with tokenString
}
```

## Troubleshooting

**No notifications received?**
1. Check FCM/APNs keys are set
2. Verify device is registered: `GET /notifications/devices/<address>`
3. Check device is enabled: `GET /notifications/settings/<token>`
4. Send test notification: `POST /notifications/test`

**Invalid token errors?**
- Device automatically unregistered
- Re-register with new token

**Rate limited?**
- Wait before retrying
- Check rate limit in response

## Production Checklist

- [ ] Set FCM server key
- [ ] Configure APNs credentials
- [ ] Set database path
- [ ] Enable HTTPS
- [ ] Configure rate limits
- [ ] Set up monitoring
- [ ] Test on all platforms
- [ ] Document recovery procedures
