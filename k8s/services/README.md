# XAI Kubernetes Service Separation

Specialized node types for independent scaling and resource optimization.

## Node Types

| Node Type | Replicas | Storage | Scaling | Purpose |
|-----------|----------|---------|---------|---------|
| API | 3-10 | None | HPA | RPC/WebSocket endpoints |
| Archive | 2 | 500Gi | Manual | Historical data queries |
| Validator | 3 | 200Gi | Fixed (BFT) | Consensus participation |

## Deployment

```bash
# Apply all services
kubectl apply -k k8s/services/

# Or individually
kubectl apply -f k8s/services/api/
kubectl apply -f k8s/services/archive/
kubectl apply -f k8s/services/validator/
```

## Service Endpoints

- **API**: `xai-api:8546` (RPC), `xai-api:8547` (WS)
- **Archive**: `xai-archive:8546`, `xai-archive-headless:8546`
- **Validator**: `xai-validator:8546`, `xai-validator-headless:8545`

## Resource Estimates

| Component | CPU (total) | Memory (total) | Storage |
|-----------|-------------|----------------|---------|
| API (3x) | 1.5-3 cores | 3-6 GB | 0 |
| Archive (2x) | 2-4 cores | 8-16 GB | 1 TB |
| Validator (3x) | 6-12 cores | 12-24 GB | 600 GB |
| **Total** | ~10-19 cores | ~23-46 GB | ~1.6 TB |
