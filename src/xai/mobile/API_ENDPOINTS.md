# Push Notification API Endpoints

Complete REST API documentation for XAI push notification system.

## Base URL

All endpoints are accessible at: `http://your-node-address:port/notifications/`

## Endpoints

### 1. Register Device

Register a mobile device for push notifications.

**Endpoint:** `POST /notifications/register`

**Request Body:**
```json
{
  "user_address": "XAI1234567890abcdef1234567890abcdef123456",
  "device_token": "fcm_token_or_apns_token_here",
  "platform": "android",
  "device_id": "optional_unique_device_identifier",
  "notification_types": ["transaction", "confirmation", "security"],
  "metadata": {
    "os_version": "13.0",
    "app_version": "1.2.0",
    "device_model": "Pixel 6"
  }
}
```

**Required Fields:**
- `user_address` (string) - XAI blockchain address
- `device_token` (string) - FCM token (Android/Web) or APNs token (iOS)
- `platform` (string) - Must be: "android", "ios", or "web"

**Optional Fields:**
- `device_id` (string) - Unique device identifier
- `notification_types` (array) - Default: ["transaction", "confirmation", "security", "governance"]
- `metadata` (object) - Additional device information

**Response (201 Created):**
```json
{
  "status": "registered",
  "device": {
    "device_token": "fcm_abc123...",
    "platform": "android",
    "user_address": "XAI1234567890abcdef1234567890abcdef123456",
    "device_id": "device_001",
    "enabled": true,
    "notification_types": ["transaction", "confirmation", "security"],
    "last_active": "2025-12-18T10:30:00.000000"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Missing or invalid fields
- `500 Internal Server Error` - Registration failed

---

### 2. Unregister Device

Remove device registration from push notification system.

**Endpoint:** `DELETE /notifications/unregister`

**Request Body:**
```json
{
  "device_token": "fcm_token_or_apns_token_here"
}
```

**Response (200 OK):**
```json
{
  "status": "unregistered",
  "device_token": "fcm_abc123..."
}
```

**Error Responses:**
- `404 Not Found` - Device not found
- `400 Bad Request` - Missing device_token
- `500 Internal Server Error` - Unregistration failed

---

### 3. Get Notification Settings

Retrieve notification settings for a specific device.

**Endpoint:** `GET /notifications/settings/<device_token>`

**Path Parameters:**
- `device_token` (string) - Push notification token

**Response (200 OK):**
```json
{
  "device_token": "fcm_abc123...",
  "platform": "android",
  "user_address": "XAI1234567890abcdef1234567890abcdef123456",
  "enabled": true,
  "notification_types": ["transaction", "security"],
  "last_active": "2025-12-18T10:30:00.000000"
}
```

**Error Responses:**
- `404 Not Found` - Device not found

---

### 4. Update Notification Settings

Update notification preferences for a device.

**Endpoint:** `PUT /notifications/settings/<device_token>`

**Path Parameters:**
- `device_token` (string) - Push notification token

**Request Body:**
```json
{
  "enabled": true,
  "notification_types": ["transaction", "security"]
}
```

**Optional Fields:**
- `enabled` (boolean) - Enable/disable all notifications
- `notification_types` (array) - Types of notifications to receive

**Response (200 OK):**
```json
{
  "status": "updated",
  "settings": {
    "enabled": true,
    "notification_types": ["transaction", "security"]
  }
}
```

**Error Responses:**
- `404 Not Found` - Device not found
- `400 Bad Request` - Invalid request body
- `500 Internal Server Error` - Update failed

---

### 5. Send Test Notification

Send a test notification to verify device registration works.

**Endpoint:** `POST /notifications/test`

**Request Body:**
```json
{
  "device_token": "fcm_token_or_apns_token_here"
}
```

**Response (200 OK):**
```json
{
  "status": "sent",
  "device_token": "fcm_abc123..."
}
```

**Error Responses:**
- `404 Not Found` - Device not registered
- `503 Service Unavailable` - Notification service unavailable
- `500 Internal Server Error` - Delivery failed

---

### 6. Get User Devices

Get all devices registered to a blockchain address.

**Endpoint:** `GET /notifications/devices/<address>`

**Path Parameters:**
- `address` (string) - XAI blockchain address

**Response (200 OK):**
```json
{
  "address": "XAI1234567890abcdef1234567890abcdef123456",
  "device_count": 2,
  "devices": [
    {
      "device_token": "fcm_abc123...",
      "platform": "android",
      "enabled": true,
      "notification_types": ["transaction", "security"],
      "last_active": "2025-12-18T10:30:00.000000"
    },
    {
      "device_token": "apns_xyz78...",
      "platform": "ios",
      "enabled": true,
      "notification_types": ["transaction", "confirmation"],
      "last_active": "2025-12-18T09:15:00.000000"
    }
  ]
}
```

**Note:** Device tokens are truncated for privacy (first 10 chars + "...")

**Error Responses:**
- `400 Bad Request` - Invalid address format

---

### 7. Get System Statistics

Get push notification system statistics.

**Endpoint:** `GET /notifications/stats`

**Response (200 OK):**
```json
{
  "stats": {
    "total": 150,
    "enabled": 142,
    "disabled": 8,
    "by_platform": {
      "android": {
        "enabled": 85,
        "disabled": 5
      },
      "ios": {
        "enabled": 55,
        "disabled": 3
      },
      "web": {
        "enabled": 2,
        "disabled": 0
      }
    }
  }
}
```

---

## Notification Types

Valid notification types for `notification_types` array:

- `transaction` - Incoming/outgoing transactions
- `confirmation` - Transaction confirmation updates
- `price_alert` - Price threshold alerts
- `security` - Security-related alerts
- `governance` - Governance proposals and votes
- `mining` - Mining rewards and status
- `contract` - Smart contract events
- `social_recovery` - Social recovery requests

## Rate Limiting

All endpoints are subject to rate limiting:
- Default: 200 requests per hour per client
- Per-device limits apply to prevent spam
- Rate limit headers included in responses

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Error message here",
  "code": "error_code",
  "status": 400
}
```

## Authentication

Currently, notification endpoints use the same authentication as other XAI node APIs.
For production deployments, consider:
- API key authentication
- Address ownership verification
- Rate limiting per address

## Testing Endpoints

Use curl to test endpoints:

```bash
# Register device
curl -X POST http://localhost:8080/notifications/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "XAI1234567890abcdef1234567890abcdef123456",
    "device_token": "test_token_123",
    "platform": "android"
  }'

# Get devices for address
curl http://localhost:8080/notifications/devices/XAI1234567890abcdef1234567890abcdef123456

# Update settings
curl -X PUT http://localhost:8080/notifications/settings/test_token_123 \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "notification_types": ["transaction", "security"]
  }'

# Send test notification
curl -X POST http://localhost:8080/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"device_token": "test_token_123"}'

# Unregister
curl -X DELETE http://localhost:8080/notifications/unregister \
  -H "Content-Type: application/json" \
  -d '{"device_token": "test_token_123"}'
```

## SDK Integration

See `PUSH_NOTIFICATIONS.md` for complete SDK integration examples in:
- Python (backend)
- Kotlin (Android)
- Swift (iOS)
- JavaScript (Web)
