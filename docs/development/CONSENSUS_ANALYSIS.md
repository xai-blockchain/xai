# XAI Testnet Consensus Failure Analysis

## Executive Summary

This document analyzes the consensus failures in the XAI multi-validator testnet based on industry research and codebase investigation. The 2-node network is stable, but 3+ node networks experience consensus drift where validators fall behind due to signature verification failures.

## Research Findings

### Common BFT Consensus Failure Modes

Based on academic research and production blockchain analysis:

1. **Invalid Peer Connections** ([Tendermint #9995](https://github.com/tendermint/tendermint/issues/9995))
   - Malformed messages from peers can destroy consensus
   - Invalid signature formats cause cascade failures
   - **XAI Impact**: Signature verification failures match this pattern

2. **Message Serialization Bugs** ([Tyr Research Paper](http://www.wingtecher.com/themes/WingTecherResearch/assets/papers/SP23-Tyr.pdf))
   - Non-deterministic JSON serialization causes signature mismatches
   - Tool Tyr found 20 vulnerabilities across major blockchains
   - **XAI Impact**: JSON trimming workaround suggests serialization issues

3. **Network Partitions** ([BFT Performance Analysis](https://arxiv.org/html/2411.07622))
   - Nodes can't agree on state when partitioned
   - View change protocols fail under sustained network stress
   - **XAI Impact**: Node2 falling behind at heights 8-9 indicates partial partition

4. **Time Synchronization** ([Cosmos Validator FAQ](https://docs.cosmos.network/hub/v25/validators/validator-faq))
   - Clock skew causes timestamp validation failures
   - Stale message rejection (300s window in XAI) sensitive to time drift
   - **XAI Impact**: Containerized environments may have clock drift

5. **Insufficient Quorum** ([Tendermint #2634](https://github.com/tendermint/tendermint/issues/2634))
   - BFT requires 2f+1 validators to tolerate f failures
   - 2 validators cannot tolerate ANY failures (need 3 minimum)
   - **XAI Impact**: 2-node testnet is fragile; 4 validators needed for proper testing

## Current XAI Implementation Analysis

### Signature Generation (src/xai/network/peer_manager.py:1472-1523)

```python
def create_signed_message(self, payload: Dict[str, Any]) -> bytes:
    message = {
        "payload": payload,
        "timestamp": int(time.time()),
        "nonce": os.urandom(16).hex(),
        "sender_id": identity_fingerprint,
    }
    # Canonical serialization
    serialized_message = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str).encode('utf-8')
    message_hash = hashlib.sha256(serialized_message).digest()
    signature = self.signing_key.ecdsa_sign(message_hash)
    # Return signed envelope
    return json.dumps({"message": message, "signature": pubkey_hex + '.' + sig_hex}, sort_keys=True).encode('utf-8')
```

### Signature Verification (src/xai/network/peer_manager.py:1552-1702)

```python
def verify_signed_message(self, signed_message_bytes: bytes) -> Optional[Dict[str, Any]]:
    # Parse and extract message
    signed_message = json.loads(signed_message_bytes.decode('utf-8'))
    message = signed_message["message"]

    # Verify timestamp freshness (300s window)
    if time.time() - message["timestamp"] > 300:
        return None  # Stale message

    # Re-serialize message for verification
    serialized_message = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str).encode('utf-8')
    message_hash = hashlib.sha256(serialized_message).digest()

    # Verify signature
    if not pubkey.ecdsa_verify(message_hash, signature):
        return None  # Invalid signature
```

### Identified Issues

1. **Serialization Consistency**: ✅ GOOD
   - Both signing and verification use identical serialization: `sort_keys=True, separators=(",", ":")`
   - Using `default=str` for non-JSON-serializable objects

2. **Timestamp Validation**: ⚠️ POTENTIAL ISSUE
   - 300-second freshness window is reasonable
   - BUT: Docker containers may have clock drift
   - Signature failures could be due to time skew, not actual invalid signatures

3. **JSON Trimming Workaround**: 🔴 SYMPTOM OF DEEPER ISSUE
   - Lines 1566-1598 implement fallback to handle malformed JSON
   - Finding `{"message"` in byte stream and trimming garbage
   - This suggests WebSocket layer is corrupting messages or appending junk data

4. **Missing Block Sync Trigger**: ⚠️ NEEDS INVESTIGATION
   - When a node falls behind, signature failures prevent it from catching up
   - Need to verify `/sync` endpoint works reliably

5. **Key Persistence**: ✅ GOOD
   - Each validator has unique signing key stored in persistent volume
   - Keys loaded from `data/keys/signing_key.pem` on restart

## Root Cause Hypothesis

Based on the evidence:

**Primary Cause: WebSocket Message Framing Issues**
- Messages from some peers include trailing data or corruption
- JSON trimming workaround masks this for single-node failures
- With 3+ nodes, multiple corrupted messages overwhelm the system
- Signature verification fails → node falls behind → can't sync

**Contributing Factors:**
1. **Time Drift**: Container clocks may not be synchronized
2. **Network Ordering**: No guaranteed message delivery order in P2P mesh
3. **Sync Failure**: When a node falls behind, sync mechanism may fail to recover

## Action Plan

### Phase 1: Baseline & Diagnostics (2-Node Network)

1. ✅ **Verify 2-node network works** (Per HANDOFF.md, this is confirmed)
   ```bash
   docker compose -f docker/testnet/docker-compose.two-node.yml up -d --build
   # Verify heights match via /health endpoint
   ```

2. **Add Enhanced Logging**
   - Log full message bytes when signature verification fails
   - Log sender identity, timestamp, and time delta
   - Capture first 1KB of payload for malformed messages

3. **Verify Time Synchronization**
   ```bash
   docker exec xai-testnet-bootstrap date +%s
   docker exec xai-testnet-node1 date +%s
   # Should be within 1-2 seconds
   ```

### Phase 2: Root Cause Fix

Based on diagnostics, implement ONE of these fixes:

**Option A: WebSocket Frame Corruption**
- Add explicit message framing (length prefix + payload)
- Validate message length before JSON parsing
- Reject messages with trailing data

**Option B: Time Synchronization**
- Add NTP container to docker-compose
- Sync all containers to common time source
- Increase timestamp freshness window to 600s

**Option C: Signature Bypass for Known Peers**
- Add trusted peer whitelist by public key
- Skip signature verification for whitelisted peers
- Still log verification results for monitoring

### Phase 3: Incremental Scaling

1. **3-Node Network**
   - Apply fix from Phase 2
   - Bring up docker-compose.three-node.yml
   - Verify all 3 nodes reach consensus
   - Monitor for 100+ blocks

2. **4-Node Network**
   - Apply same fix to docker-compose.yml (4-node)
   - Verify full network reaches consensus
   - Test network partition scenarios
   - Re-enable P2P PoW if desired

## Diagnostic Commands

### Check Current State
```bash
# Health check all nodes
curl -s http://localhost:12001/health | jq .
curl -s http://localhost:12011/health | jq .

# View recent logs
docker compose -f docker/testnet/docker-compose.two-node.yml logs --tail=100 | grep -i signature

# Check time sync
docker exec xai-testnet-bootstrap date +"%Y-%m-%d %H:%M:%S"
docker exec xai-testnet-node1 date +"%Y-%m-%d %H:%M:%S"
```

### Force Sync
```bash
# Get CSRF token
TOKEN=$(curl -s http://localhost:12011/csrf-token | jq -r .csrf_token)

# Trigger sync (requires API key)
curl -X POST http://localhost:12011/sync \
  -H "X-CSRF-Token: $TOKEN" \
  -H "X-API-Key: ${API_KEY}" \
  -b "csrf_token=${TOKEN}"
```

## Next Steps

1. Run Phase 1 diagnostics on 2-node network
2. Capture signature failure logs to identify pattern
3. Implement targeted fix based on evidence
4. Test 3-node, then 4-node networks
5. Document final solution in HANDOFF.md

## References

- [Tendermint Invalid Peer Issue](https://github.com/tendermint/tendermint/issues/9995)
- [Tyr: Finding Consensus Failure Bugs](http://www.wingtecher.com/themes/WingTecherResearch/assets/papers/SP23-Tyr.pdf)
- [BFT Consensus Performance Analysis](https://arxiv.org/html/2411.07622)
- [Cosmos Validator FAQ](https://docs.cosmos.network/hub/v25/validators/validator-faq)
- [Tendermint Running in Production](https://docs.tendermint.com/v0.34/tendermint-core/running-in-production.html)
