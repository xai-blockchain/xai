# Blockchain Testing Quick Reference

## Run All Tests
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-blockchain-test-suite.sh
```

## Individual Tests

### 1. Validator Key Rotation
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-validator-rotation.sh
```

### 2. Slashing Detection
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-slashing-detection.sh
```

### 3. MEV Protection
```bash
sudo kubectl apply -f k8s/mev-network-policy.yaml
sudo kubectl describe networkpolicy mev-protection -n xai
```

### 4. Finality Testing
```bash
/home/hudson/blockchain-projects/xai/scripts/k8s-finality-check.sh
```

## Files Created

**Manifests:**
- `k8s/validator-keys-rotated.yaml` - Rotated validator keys secret
- `k8s/mev-network-policy.yaml` - MEV protection network policy

**Scripts:**
- `scripts/k8s-validator-rotation.sh` - Automated key rotation
- `scripts/k8s-slashing-detection.sh` - Slashing behavior detection
- `scripts/k8s-finality-check.sh` - Finality verification
- `scripts/k8s-blockchain-test-suite.sh` - Comprehensive test runner

**Docs:**
- `docs/K8S_BLOCKCHAIN_TESTING.md` - Complete testing guide
