# Route to Blueprint Migration Status

## Overview

The XAI blockchain API routes are being reorganized from the old function registration pattern (`api_routes/`) into Flask Blueprints (`api_blueprints/`) for better modularity and maintainability.

## Migration Status

### ✅ Completed Blueprints

1. **payment_bp** (`api_blueprints/payment_bp.py`)
   - Source: `api_routes/payment.py` (936 lines)
   - Routes: 6 endpoints
     - GET `/payment/qr/<address>` - Generate address QR code
     - POST `/payment/qr` - Generate payment request QR
     - POST `/payment/request` - Create tracked payment request
     - GET `/payment/request/<request_id>` - Check payment status
     - POST `/payment/parse` - Parse payment URI
     - POST `/payment/verify` - Verify payment
   - Status: **Fully migrated, added to `__init__.py`**

2. **core_bp** (`api_blueprints/core_bp.py`)
   - Health, stats, metrics endpoints
   - Status: **Already exists**

3. **blockchain_bp** (`api_blueprints/blockchain_bp.py`)
   - Block and blockchain query endpoints
   - Status: **Already exists**

4. **wallet_bp** (`api_blueprints/wallet_bp.py`)
   - Balance, nonce, history, faucet endpoints
   - Status: **Already exists**

5. **mining_bp** (`api_blueprints/mining_bp.py`)
   - Mining endpoints
   - Status: **Already exists**

6. **exchange_bp** (`api_blueprints/exchange_bp.py`)
   - Exchange/trading endpoints
   - Status: **Partially migrated** (some routes in `api_routes/exchange.py`)

7. **admin_bp** (`api_blueprints/admin_bp.py`)
   - Admin endpoints (API keys, withdrawals, spend limits)
   - Status: **Partially migrated** (some routes in `api_routes/admin.py`)

### 🚧 Pending Migration

The following route files still need to be migrated to blueprints:

1. **transactions** (`api_routes/transactions.py` - 385 lines)
   - Needs: `transactions_bp.py`

2. **contracts** (`api_routes/contracts.py` - 693 lines)
   - Needs: `contracts_bp.py`

3. **notifications** (`api_routes/notifications.py` - 474 lines)
   - Needs: `notifications_bp.py`

4. **sync** (`api_routes/sync.py` - 491 lines)
   - Needs: `sync_bp.py`

5. **light_client** (`api_routes/light_client.py` - 451 lines)
   - Needs: `light_client_bp.py`

6. **recovery** (`api_routes/recovery.py` - 483 lines)
   - Needs: `recovery_bp.py`

7. **gamification** (`api_routes/gamification.py` - 359 lines)
   - Needs: `gamification_bp.py`

8. **crypto_deposits** (`api_routes/crypto_deposits.py` - 294 lines)
   - Needs: `crypto_deposits_bp.py`

9. **mining_bonus** (`api_routes/mining_bonus.py` - 411 lines)
   - Needs: `mining_bonus_bp.py`

10. **algo** (`api_routes/algo.py` - 203 lines)
    - Needs: `algo_bp.py`

11. **peer** (`api_routes/peer.py` - 110 lines)
    - Needs: `peer_bp.py`

12. **faucet** (`api_routes/faucet.py` - 121 lines)
    - Can be merged into `wallet_bp` or standalone

13. **core** (`api_routes/core.py` - 311 lines)
    - Partially merged into `core_bp`, needs completion

14. **blockchain** (`api_routes/blockchain.py` - 290 lines)
    - Partially merged into `blockchain_bp`, needs completion

15. **exchange** (`api_routes/exchange.py` - 863 lines)
    - Partially merged into `exchange_bp`, needs completion

16. **admin** (`api_routes/admin.py` - 845 lines)
    - Partially merged into `admin_bp`, needs many additional routes:
      - Emergency pause/unpause
      - Circuit breaker control
      - Mining control
      - Peer management
      - Config reload
      - Profiling control

## Architecture

### Old Pattern (api_routes/)
```python
def register_*_routes(routes: NodeAPIRoutes):
    app = routes.app
    @app.route("/path", methods=["GET"])
    def handler():
        ...
```

### New Pattern (api_blueprints/)
```python
bp = Blueprint("name", __name__, url_prefix="/prefix")

@bp.route("/path", methods=["GET"])
def handler():
    # Use helper functions from base.py
    node = get_node()
    blockchain = get_blockchain()
    ...
```

### Helper Utilities (`api_blueprints/base.py`)
- `get_node()` - Access to blockchain node
- `get_blockchain()` - Access to blockchain
- `get_api_context()` - Full context dict
- `get_peer_manager()` - Peer manager access
- `get_api_auth()` - API auth manager
- `error_response()` - Standard error responses
- `success_response()` - Standard success responses
- `require_api_auth()` - API key authentication
- `require_admin_auth()` - Admin authentication
- `get_pagination_params()` - Pagination helpers

## Benefits of Blueprint Pattern

1. **Modularity** - Each domain in its own file
2. **Testability** - Blueprints can be tested in isolation
3. **Reusability** - Shared utilities in `base.py`
4. **URL Prefixing** - Automatic URL prefix handling
5. **Maintainability** - Smaller, focused files
6. **Scalability** - Easy to add new blueprints

## Migration Checklist

For each route file:

1. [ ] Create new blueprint file in `api_blueprints/`
2. [ ] Convert routes from `@app.route` to `@bp.route`
3. [ ] Replace direct node/blockchain access with helper functions
4. [ ] Add blueprint to `api_blueprints/__init__.py`
5. [ ] Register blueprint in `register_blueprints()`
6. [ ] Test backward compatibility
7. [ ] Update documentation
8. [ ] Remove old route registration from `node_api.py`

## Backward Compatibility

- Both old routes and new blueprints work during migration
- Old `api_routes/` files remain until fully migrated
- URL paths remain identical (no breaking changes)
- Tests continue to pass with either pattern

## Next Steps

1. Complete migration of remaining 16 route files
2. Update `node_api.py` to use blueprints exclusively
3. Remove old `api_routes/` directory
4. Update all tests to use blueprint imports
5. Add comprehensive blueprint tests
6. Document API versioning strategy

## Notes

- The `payment_bp` blueprint is the reference implementation
- Follow the same pattern for consistency
- All blueprints should use helpers from `base.py`
- Keep URL paths identical for backward compatibility
- Add appropriate url_prefix to each blueprint
