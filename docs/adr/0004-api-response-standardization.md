# ADR-0004: API Response Standardization

**Status:** Proposed
**Date:** 2025-12-28

## Context
35 API files use inconsistent response formats:
- 283 standardized responses via `_success_response()`/`_error_response()`
- 236 raw `jsonify()` calls with ad-hoc structures

## Decision
Unified envelope for all API responses:

```json
{
  "success": true|false,
  "data": {...},
  "error": {"code": "...", "message": "...", "details": {...}},
  "pagination": {"limit": 50, "offset": 0, "total": 150},
  "metadata": {"timestamp": "...", "request_id": "..."}
}
```

Implementation:
1. Extend `api_blueprints/base.py` with `paginated_response()`, `list_response()`
2. Update 24 files with mixed patterns
3. Integrate `error_response.py` error codes

## Consequences
**Positive:**
- Consistent client experience
- Easier error handling
- Self-documenting APIs

**Negative:**
- Breaking change for some endpoints
- Need versioned rollout (/v1/ prefix)
