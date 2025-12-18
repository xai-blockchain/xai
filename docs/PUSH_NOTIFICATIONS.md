# XAI Push Notifications

Mobile push notification infrastructure for XAI blockchain applications.

## Overview

XAI supports push notifications for mobile applications via:
- **Firebase Cloud Messaging (FCM)** - Android and Web
- **Apple Push Notification Service (APNs)** - iOS

## Notification Types

- `transaction` - Incoming/outgoing transactions
- `confirmation` - Transaction confirmation milestones
- `price_alert` - Price threshold alerts
- `security` - Security events (new device, suspicious activity)
- `governance` - Governance proposals and votes
- `mining` - Mining rewards and status
- `contract` - Smart contract events

## API Endpoints

### Register Device
```http
POST /notifications/register
Content-Type: application/json

{
  "user_address": "XAI1234...",
  "device_token": "fcm_token_or_apns_token",
  "platform": "ios|android|web",
  "device_id": "optional_device_id",
  "notification_types": ["transaction", "security"],
  "metadata": {"os_version": "15.0", "app_version": "1.0"}
}
```

### Unregister Device
```http
DELETE /notifications/unregister
Content-Type: application/json

{"device_token": "token"}
```

### Update Settings
```http
PUT /notifications/settings/{device_token}
Content-Type: application/json

{
  "enabled": true,
  "notification_types": ["transaction", "security"]
}
```

### Get Settings
```http
GET /notifications/settings/{device_token}
```

### Test Notification
```http
POST /notifications/test
Content-Type: application/json

{"device_token": "token"}
```

## FCM Setup

### 1. Create Firebase Project
- Go to [Firebase Console](https://console.firebase.google.com/)
- Create new project or use existing
- Add Android/Web app

### 2. Get Server Key
- Project Settings → Cloud Messaging
- Copy Server Key

### 3. Configure XAI Node
```bash
export XAI_FCM_SERVER_KEY="your_server_key"
```

### 4. Mobile App Integration
```kotlin
// Android (Kotlin)
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    val token = task.result
    // Register with XAI API
}
```

## APNs Setup

### 1. Apple Developer Account
- Create App ID with Push Notifications capability
- Generate APNs Authentication Key (.p8)

### 2. Get Credentials
- Team ID: Developer account settings
- Key ID: From .p8 key
- Key file: Download .p8 file

### 3. Configure XAI Node
```bash
export XAI_APNS_KEY_ID="ABC123XYZ"
export XAI_APNS_TEAM_ID="DEF456UVW"
export XAI_APNS_KEY_PATH="/path/to/AuthKey_ABC123XYZ.p8"
```

### 4. Mobile App Integration
```swift
// iOS (Swift)
UNUserNotificationCenter.current().requestAuthorization { granted, _ in
    if granted {
        DispatchQueue.main.async {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }
}

func application(_ app: UIApplication,
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    // Register with XAI API
}
```

## Privacy Considerations

### Data Collection
- Device tokens stored encrypted
- User addresses hashed in logs
- Notification content minimized
- No personal data in payloads

### User Control
- Opt-in required for all notifications
- Per-type notification preferences
- Easy unregistration
- Device list viewable by user

### Rate Limiting
- Max 100 notifications/day per device
- Security alerts exempt from limits
- Automatic throttling on errors

## Development Mode

Without API keys, service logs warnings but doesn't crash:

```python
# Missing keys - service degrades gracefully
notification_service.send_transaction_notification(...)
# Logs warning, returns unsuccessful DeliveryResult
```

## Production Checklist

- [ ] FCM server key configured
- [ ] APNs credentials configured (.p8 key)
- [ ] SSL certificates valid
- [ ] Rate limiting configured
- [ ] Privacy policy updated
- [ ] User consent mechanism implemented
- [ ] Device cleanup cron job scheduled
- [ ] Monitoring and alerts configured
