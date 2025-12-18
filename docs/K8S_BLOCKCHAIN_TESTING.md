# Kubernetes Blockchain Testing - XAI

## 1. Validator Key Rotation

**Automated hot-swap** (zero-downtime):
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-validator-rotation.sh
```

**Manual rotation**:
```bash
sudo kubectl apply -f k8s/validator-keys-rotated.yaml -n xai
sudo kubectl patch statefulset xai-validator -n xai -p '{"spec":{"template":{"spec":{"volumes":[{"name":"keys","secret":{"secretName":"validator-keys-rotated"}}]}}}}'
```

**Rollback**: Patch back to `validator-keys` secret and restart.

## 2. Slashing Simulation

**Slashable behaviors**: Double-signing (byzantine), downtime (>500 missed blocks)

**Detection script**:
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-slashing-detection.sh
```

**Simulate downtime** (testnet only):
```bash
sudo kubectl scale statefulset xai-validator -n xai --replicas=0  # All down
sudo kubectl scale statefulset xai-validator -n xai --replicas=2  # Restore after 10min
```

**Manual inspection**: `sudo kubectl logs -n xai -l app=xai-validator | grep -i "double.*sign\|slash"`

## 3. MEV Protection

**Apply network policy**:
```bash
sudo kubectl apply -f k8s/mev-network-policy.yaml
```

**Enforced**: RPC restricted to `role=trusted-rpc-client` only, P2P validator-mesh only, egress to validators+DNS only

**Verify**: `sudo kubectl describe networkpolicy mev-protection -n xai`

## 4. Finality Testing

**Check finality**:
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-finality-check.sh
```

**Manual queries**:
```bash
sudo kubectl exec -n xai xai-validator-0 -- curl localhost:26657/status  # Block height
sudo kubectl logs -n xai xai-validator-0 | grep "commit\|prevote"       # Consensus
```

**Prometheus metrics**: `tendermint_consensus_height`, `tendermint_consensus_validators`, `tendermint_consensus_missing_validators`

**Health**: Good (1-3s blocks), Warning (>5s blocks), Critical (>30s no blocks)

---

**Run all tests**: `/home/hudson/blockchain-projects/xai/scripts/k8s-blockchain-test-suite.sh`
