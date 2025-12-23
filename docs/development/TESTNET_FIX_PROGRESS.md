# XAI Testnet Consensus Fix - Progress Report

**Date:** 2025-12-14
**Status:** Partial fixes implemented, additional work needed

## Summary

Successfully identified and fixed TWO critical bugs causing consensus failures:
1. **Message concatenation in WebSocket frames**
2. **Async event loop management errors**

However, nodes still diverge after ~30-60 seconds due to connection instability.

## Research-Based Root Cause Analysis

### Academic & Industry Findings

Based on research from:
- [Tendermint consensus issues](https://github.com/tendermint/tendermint/issues/9995)
- [Tyr: Finding Consensus Failure Bugs](http://www.wingtecher.com/themes/WingTecherResearch/assets/papers/SP23-Tyr.pdf)
- [BFT Consensus Performance Analysis](https://arxiv.org/html/2411.07622)
- [Cosmos Validator FAQ](https://docs.cosmos.network/hub/v25/validators/validator-faq)

**Key Failure Modes Identified:**
1. Invalid peer connections from malformed messages
2. Message serialization bugs (non-deterministic JSON)
3. Network partitions preventing state agreement
4. Time synchronization issues (clock skew)
5. Insufficient validator count (need 4 for proper BFT)

### XAI-Specific Findings

**Bug #1: Message Concatenation**

**Symptom:** Log showed corrupted JSON like:
```
...f6b5b"}{"message": {"no7543794df58d094b571879dd72fc94d
```

**Root Cause:** Multiple JSON messages sent via `websocket.send()` were arriving concatenated in a single WebSocket frame, causing JSON parsing to fail.

**Fix Applied:**
- Added newline delimiters (`\n`) to all outgoing messages
- Modified `_handle_message()` to split on newlines and process each message separately
- Files modified:
  - `src/xai/core/node_p2p.py`: Lines 1234, 825-842
  - `src/xai/network/peer_manager.py`: Lines 793, 823

**Bug #2: Async Event Loop Errors**

**Symptom:** Logs showed:
```
RuntimeError: no running event loop
IndexError: deque index out of range
Fatal error on SSL protocol
```

**Root Cause:** `_dispatch_async()` was calling `asyncio.run(coro)` which creates a NEW event loop, causing conflicts when called from async contexts or threads.

**Fix Applied:**
- Store reference to main event loop in `P2PNetworkManager.start()`
- Use `asyncio.run_coroutine_threadsafe()` for thread-safe task scheduling
- Fall back to `create_task()` when loop exists but isn't running
- Files modified:
  - `src/xai/core/node_p2p.py`: Lines 156, 306, 1313-1328

## Test Results

### 2-Node Testnet (docker-compose.two-node.yml)

**Initial Connection:** ✅ SUCCESS
- Both nodes reach consensus at height ~10
- Matching block hashes
- No signature verification failures
- Time synchronization confirmed (clocks within 0-1 second)

**Sustained Consensus:** ❌ FAILURE
- After 30-60 seconds, connection drops
- Node1 P2P server appears to stop accepting connections
- Bootstrap logs show: "Connection refused" to Node1:8765
- Node1 gets stuck at a height while Bootstrap continues

**Error Pattern:**
```
Bootstrap logs:
- Network error creating pooled connection: [Errno 111] Connect call failed
- Peer discovery failed during startup: PeerNetworkError
- Failed to connect to peer wss://xai-testnet-node1:8765
- Error broadcasting to peer peer_1: ConnectionClosedError
```

## Remaining Issues

### Issue #1: P2P Server Stability

**Observation:** Node1's P2P server stops accepting connections after initial success.

**Hypothesis:**
1. P2P server crashes silently (no error logs)
2. Event loop stops running
3. Some exception is being swallowed

**Next Steps:**
1. Add comprehensive exception handling around P2P server lifecycle
2. Add heartbeat/keepalive to P2P connections
3. Implement automatic reconnection logic
4. Add P2P server health check endpoint

### Issue #2: Connection Pool Management

**Observation:** Bootstrap tries to connect to Node1 but gets "connection refused"

**Hypothesis:**
1. Connection pool might not be releasing connections properly
2. TLS/SSL handshake might be timing out
3. Node1 might be hitting max connection limit

**Next Steps:**
1. Review connection pool implementation in `peer_manager.py`
2. Add connection pool metrics
3. Implement connection draining on errors
4. Test with longer handshake timeouts

### Issue #3: Missing Reconnection Logic

**Current Behavior:** When a peer disconnects, no automatic reconnection

**Required:**
1. Exponential backoff reconnection
2. Peer health tracking
3. Connection quality metrics
4. Automatic peer rotation

## Recommended Next Actions

### Immediate (Before scaling to 3-4 nodes):

1. **Add P2P Server Monitoring**
   ```python
   # In P2PNetworkManager.start()
   async def _monitor_server_health(self):
       while self.server.is_serving():
           await asyncio.sleep(5)
           logger.debug("P2P server health: OK")
       logger.critical("P2P server stopped unexpectedly!")
   ```

2. **Add WebSocket Keep-Alive**
   ```python
   # In docker-compose.yml
   XAI_P2P_KEEPALIVE_SECONDS: "30"
   ```

3. **Add Automatic Reconnection**
   ```python
   # On connection loss, retry with exponential backoff
   async def _reconnect_to_peer(self, peer_uri):
       for attempt in range(5):
           try:
               await asyncio.sleep(2 ** attempt)
               await self._connect_to_peer(peer_uri)
               break
           except Exception as e:
               logger.warning(f"Reconnect attempt {attempt+1} failed: {e}")
   ```

4. **Add Connection Health Checks**
   - Ping/pong every 30 seconds
   - Detect stale connections
   - Force reconnect on timeout

### Medium-term:

1. Test 3-node network once 2-node is stable
2. Test 4-node network
3. Re-enable P2P PoW
4. Add network chaos testing (latency, packet loss)
5. Implement checkpoint sync for faster recovery

### Long-term:

1. Implement libp2p for better P2P networking
2. Add gossipsub for efficient message propagation
3. Implement connection quality scoring
4. Add peer reputation system

## Code Changes Made

### File: src/xai/core/node_p2p.py

**Lines 156:** Added `_loop` instance variable
```python
self._loop: Optional[asyncio.AbstractEventLoop] = None
```

**Lines 306:** Store event loop reference
```python
self._loop = asyncio.get_running_loop()
```

**Lines 825-842:** Split concatenated messages
```python
async def _handle_message(self, websocket, message):
    message_str = message if isinstance(message, str) else message.decode("utf-8", errors="replace")
    individual_messages = [msg.strip() for msg in message_str.split("\n") if msg.strip()]
    for msg in individual_messages:
        await self._process_single_message(websocket, peer_id, msg.encode("utf-8"))
```

**Lines 1234:** Add newline delimiter
```python
await websocket.send(signed_message.decode("utf-8") + "\n")
```

**Lines 1313-1328:** Fix async dispatch
```python
def _dispatch_async(self, coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = self._loop or asyncio.get_event_loop()

    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, loop)
    else:
        loop.create_task(coro)
```

### File: src/xai/network/peer_manager.py

**Lines 793, 823:** Add newline delimiters to handshake and request messages
```python
await websocket.send(signed_handshake.decode("utf-8") + "\n")
await websocket.send(signed_request.decode("utf-8") + "\n")
```

## Testing Protocol

### 2-Node Test
```bash
cd ~/blockchain-projects/xai
docker compose -f docker/testnet/docker-compose.two-node.yml down -v
docker compose -f docker/testnet/docker-compose.two-node.yml up -d --build

# Wait 60 seconds
sleep 60

# Check consensus
curl -s http://localhost:12001/health | jq '{height: .blockchain.height, hash: .blockchain.latest_block_hash}'
curl -s http://localhost:12011/health | jq '{height: .blockchain.height, hash: .blockchain.latest_block_hash}'

# Monitor for 5 minutes
for i in {1..10}; do
    sleep 30
    echo "=== Check $i ==="
    curl -s http://localhost:12001/health | jq '.blockchain | {height, hash: .latest_block_hash}'
    curl -s http://localhost:12011/health | jq '.blockchain | {height, hash: .latest_block_hash}'
done
```

### Expected Success Criteria
- ✅ Both nodes reach identical heights
- ✅ Both nodes have matching block hashes
- ✅ No signature verification failures in logs
- ✅ Consensus maintained for 100+ blocks
- ✅ Connections remain stable for 10+ minutes
- ✅ No "connection refused" errors

## References

- See `CONSENSUS_ANALYSIS.md` for detailed research findings
- See `HANDOFF.md` for historical context
- See docker-compose files in `docker/testnet/`

## Next Session

When continuing this work:
1. Review this document
2. Implement P2P server monitoring
3. Add connection health checks
4. Test with enhanced logging
5. Once 2-node is stable for 10+ minutes, proceed to 3-node
