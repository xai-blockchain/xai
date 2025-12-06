# API Versioning

The REST API exposes explicit version prefixes so clients can opt into
compatible behavior and discover upcoming sunsets.

| Version | Prefix | Status      | Sunset                  |
|---------|--------|-------------|-------------------------|
| v2      | `/v2`  | current     | _none_                  |
| v1      | `/v1`  | deprecated  | 1 Jan 2025 00:00:00 GMT |
| legacy  | _(none)_ | deprecated | 1 Jan 2025 00:00:00 GMT |

## Requesting a Version

- Call `https://node.example.com/v2/<endpoint>` to target v2 explicitly.
- Legacy clients that omit the prefix are automatically routed to the
  default version (currently v2) but receive `Deprecation: version="legacy"`
  headers so they can upgrade before the sunset date.
- Requests with an unknown prefix return `404` along with a payload listing
  the supported versions.

## Response Headers

Every response includes:

- `X-API-Version`: the version that processed the request.
- `Deprecation`: only present for deprecated versions (`version="v1"` etc).
- `Sunset`: RFC 8594 timestamp for deprecated versions.
- `Link`: documentation URL describing the migration plan.

These headers allow SDKs and monitoring agents to detect when the calling
version is about to expire.
