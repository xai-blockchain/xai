# Push Notification Framework for XAI Mobile Apps

Complete push notification infrastructure supporting FCM (Android/Web) and APNs (iOS).

## Overview

The push notification framework provides:
- Device registration and management
- Firebase Cloud Messaging (FCM) for Android/Web
- Apple Push Notification Service (APNs) for iOS
- Rate limiting per device
- Batch notification support
- Multiple notification types with priorities
- Comprehensive error handling and retry logic

## Architecture

```
xai.mobile.push_notifications (wrapper)
    └── xai.notifications (core implementation)
        ├── push_service.py       - Delivery service
        ├── device_registry.py    - Device management
        └── notification_types.py - Payload schemas
```

## Environment Configuration

Set these environment variables for production:

```bash
# Firebase Cloud Messaging (Android/Web)
export XAI_FCM_SERVER_KEY="your_fcm_server_key_here"

# Apple Push Notification Service (iOS)
export XAI_APNS_KEY_ID="your_apns_key_id"
export XAI_APNS_TEAM_ID="your_apple_team_id"
export XAI_APNS_KEY_PATH="/path/to/apns_key.p8"
```

## API Endpoints

All endpoints are available at `/notifications/*`:

### 1. Register Device

**POST** `/notifications/register`

Register a device for push notifications.

```json
{
  "user_address": "XAI1234567890abcdef...",
  "device_token": "fcm_token_or_apns_token",
  "platform": "ios",
  "device_id": "optional_unique_device_id",
  "notification_types": ["transaction", "confirmation", "security"],
  "metadata": {"os_version": "16.0", "app_version": "1.0.0"}
}
```

Response (201):
```json
{
  "status": "registered",
  "device": {
    "device_token": "fcm_abc123...",
    "platform": "ios",
    "user_address": "XAI1234567890abcdef...",
    "enabled": true,
    "notification_types": ["transaction", "confirmation", "security"]
  }
}
```

### 2. Unregister Device

**DELETE** `/notifications/unregister`

Remove device registration.

```json
{
  "device_token": "fcm_token_or_apns_token"
}
```

### 3. Get Notification Settings

**GET** `/notifications/settings/<device_token>`

Retrieve current notification settings for a device.

### 4. Update Notification Settings

**PUT** `/notifications/settings/<device_token>`

Update notification preferences.

```json
{
  "enabled": true,
  "notification_types": ["transaction", "security"]
}
```

### 5. Send Test Notification

**POST** `/notifications/test`

Send a test notification to verify device registration.

```json
{
  "device_token": "fcm_token_or_apns_token"
}
```

### 6. Get User Devices

**GET** `/notifications/devices/<address>`

List all devices registered to a blockchain address.

### 7. Get System Statistics

**GET** `/notifications/stats`

Get notification system statistics.

## Usage Examples

### Python Backend Integration

```python
from xai.mobile import PushNotificationService, DeviceRegistry
from xai.mobile.notification_types import create_transaction_notification
import asyncio

# Initialize services
device_registry = DeviceRegistry(db_path="/path/to/devices.db")
push_service = PushNotificationService(device_registry)

# Send transaction notification
async def notify_transaction(address: str, tx_hash: str, amount: str):
    results = await push_service.send_transaction_notification(
        address=address,
        tx_hash=tx_hash,
        amount=f"{amount} XAI",
        from_address="XAI1111...",
        to_address=address,
        is_incoming=True
    )

    for result in results:
        if result.success:
            print(f"Notification sent to {result.device_token[:10]}...")
        else:
            print(f"Failed: {result.error}")

# Run async function
asyncio.run(notify_transaction(
    "XAI1234567890abcdef...",
    "0xabc123",
    "10.5"
))
```

### Mobile App Integration (Android - Kotlin)

```kotlin
// Register device with FCM token
val client = OkHttpClient()
val json = JSONObject().apply {
    put("user_address", userAddress)
    put("device_token", FirebaseMessaging.getInstance().token.await())
    put("platform", "android")
    put("notification_types", JSONArray(listOf("transaction", "security")))
}

val request = Request.Builder()
    .url("https://your-node.com/notifications/register")
    .post(json.toString().toRequestBody("application/json".toMediaType()))
    .build()

val response = client.newCall(request).execute()
```

### Mobile App Integration (iOS - Swift)

```swift
// Register device with APNs token
func registerForPushNotifications(userAddress: String, deviceToken: Data) {
    let tokenString = deviceToken.map { String(format: "%02x", $0) }.joined()

    let parameters: [String: Any] = [
        "user_address": userAddress,
        "device_token": tokenString,
        "platform": "ios",
        "notification_types": ["transaction", "confirmation", "security"]
    ]

    var request = URLRequest(url: URL(string: "https://your-node.com/notifications/register")!)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONSerialization.data(withJSONObject: parameters)

    URLSession.shared.dataTask(with: request) { data, response, error in
        // Handle response
    }.resume()
}
```

## Notification Types

The system supports these notification types:

- **transaction** - Incoming/outgoing transactions (HIGH priority for incoming)
- **confirmation** - Transaction confirmation updates (NORMAL priority)
- **price_alert** - Price threshold crossed (NORMAL priority)
- **security** - Security alerts (CRITICAL priority)
- **governance** - Governance proposals and votes (NORMAL priority)
- **mining** - Mining rewards and status (NORMAL priority)
- **contract** - Smart contract events (NORMAL priority)
- **social_recovery** - Social recovery requests (HIGH priority)

## Priority Levels

- **LOW** - Batched, no alert sound
- **NORMAL** - Standard notification with alert
- **HIGH** - Important, guaranteed delivery
- **CRITICAL** - Security-critical, bypasses quiet hours

## Rate Limiting

The notification system includes built-in rate limiting:
- Per device limits prevent spam
- Invalid tokens are automatically unregistered
- Retry logic for transient failures
- Exponential backoff for rate limit errors

## Device Management

### Automatic Cleanup

Devices inactive for 90+ days are automatically removed:

```python
removed = device_registry.cleanup_inactive_devices(days=90)
print(f"Cleaned up {removed} inactive devices")
```

### Platform Support

- **iOS** - APNs via HTTP/2 (production & sandbox)
- **Android** - FCM via HTTPS
- **Web** - FCM web push

## Security Features

- Device tokens stored in SQLite with proper indexing
- No plaintext storage of sensitive data
- Address validation on all endpoints
- Rate limiting prevents abuse
- Automatic invalid token cleanup

## Error Handling

The service handles these error conditions:

- **Invalid tokens** - Auto-unregister
- **Rate limits** - Retry with backoff
- **Network errors** - Retry up to 3 times
- **Missing credentials** - Graceful degradation (dev mode)

## Testing

Run comprehensive test suite:

```bash
pytest tests/xai_tests/unit/test_push_notifications.py -v
```

All 27 tests cover:
- Notification payload creation
- Device registration/management
- FCM/APNs delivery (mocked)
- API endpoints
- Error scenarios

## Production Deployment

1. Set environment variables for FCM and APNs credentials
2. Configure device database path
3. Enable notification routes in node API
4. Set up monitoring for delivery metrics
5. Configure cleanup cron job (optional)

## Monitoring

Track notification metrics:

```python
stats = device_registry.get_stats()
print(f"Total devices: {stats['total']}")
print(f"Enabled: {stats['enabled']}")
print(f"By platform: {stats['by_platform']}")
```

## License

Part of the XAI blockchain project. See main repository for license details.
