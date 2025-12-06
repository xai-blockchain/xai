# Node API: No Response Caching for Immutable Data

---
status: pending
priority: p2
issue_id: 017
tags: [performance, api, caching, code-review]
dependencies: []
---

## Problem Statement

Every API request executes full query, even for immutable blockchain data. The `/chain` endpoint serializes the entire chain on every request, wasting CPU and bandwidth.

## Findings

### Location
**File:** `src/xai/core/node.py` (Lines 463-473)

### Evidence

```python
@self.app.before_request
def before_request():
    request.start_time = time.time()

@self.app.after_request
def after_request(response):
    latency = time.time() - request.start_time
    # No caching logic
```

### Impact

- `/chain` endpoint: Serializes entire chain on every request
- Popular blocks: Re-serialized 1000s of times
- High CPU + bandwidth usage
- Poor user experience with slow API responses

## Proposed Solutions

### Option A: ETag-Based Caching (Recommended)
**Effort:** Medium | **Risk:** Low

```python
from flask import make_response
import hashlib

@app.route('/block/<int:index>')
def get_block(index):
    block = blockchain.get_block(index)
    if not block:
        return jsonify({"error": "Block not found"}), 404

    # Generate ETag from block hash
    etag = f'"{block.hash}"'

    # Check If-None-Match header
    if request.headers.get('If-None-Match') == etag:
        return '', 304  # Not Modified

    response = make_response(jsonify(block.to_dict()))
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = 'public, max-age=31536000'  # Immutable
    return response
```

### Option B: Redis Cache Layer
**Effort:** Large | **Risk:** Medium

```python
import redis
from functools import wraps

cache = redis.Redis()

def cached(ttl=3600):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__name__}:{args}:{kwargs}"
            result = cache.get(key)
            if result:
                return json.loads(result)
            result = f(*args, **kwargs)
            cache.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

## Acceptance Criteria

- [ ] Immutable data (blocks) cached with long TTL
- [ ] ETag support for conditional requests
- [ ] Cache-Control headers set appropriately
- [ ] Benchmark: 90% reduction in repeated requests

## Resources

- [HTTP Caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
- [Flask-Caching](https://flask-caching.readthedocs.io/)
