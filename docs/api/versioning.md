# API Versioning

The REST API exposes explicit version prefixes so clients can opt into
compatible behavior and discover upcoming sunsets.

| Version | Prefix       | Status  | Sunset |
|---------|--------------|---------|--------|
| v1      | `/api/v1`    | current | _none_ |
| legacy  | `/v1`        | supported (backward compat) | TBD |
| legacy  | _(no prefix)_ | supported (backward compat) | TBD |

## Requesting a Version

### Recommended: Use /api/v1/ Prefix

- Call `https://node.example.com/api/v1/<endpoint>` to target v1 explicitly.
- Example: `GET https://node.example.com/api/v1/blocks`
- This is the recommended format for all new integrations.

### Backward Compatibility

The API maintains backward compatibility for existing clients:

- **Legacy `/v1/` prefix**: Requests to `/v1/<endpoint>` are supported (e.g., `/v1/blocks`)
- **No prefix**: Requests without version prefix (e.g., `/blocks`) are automatically routed to v1

Both legacy formats work transparently thanks to the API versioning middleware, which:
1. Detects the version prefix (or lack thereof)
2. Strips it from the request path
3. Routes to the appropriate version handler
4. Adds version information to response headers

### Migration Path

Clients using legacy URL formats (`/blocks`, `/v1/blocks`) should migrate to `/api/v1/blocks`:

**Before:**
```
GET http://localhost:12001/blocks
GET http://localhost:12001/v1/blocks
```

**After:**
```
GET http://localhost:12001/api/v1/blocks
```

The XAI SDK automatically handles this - simply use the latest SDK version.

## Response Headers

Every response includes:

- `X-API-Version`: the version that processed the request (e.g., "v1")
- `Deprecation`: only present for deprecated URL patterns
- `Sunset`: RFC 8594 timestamp for deprecated versions (when applicable)
- `Link`: documentation URL describing the migration plan

These headers allow SDKs and monitoring agents to detect when the calling
pattern is deprecated.

## Error Responses

Requests with an unsupported version prefix (e.g., `/api/v99/blocks`) return:

```json
{
  "success": false,
  "error": "Unsupported API version",
  "code": "unsupported_api_version",
  "requested_version": "v99",
  "supported_versions": ["v1"]
}
```

Status code: `404 NOT FOUND`
