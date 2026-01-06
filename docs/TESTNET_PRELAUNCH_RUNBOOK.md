# XAI Testnet Prelaunch Runbook (Parallel-Safe, Extensive)

This runbook is designed to catch rookie errors before a public testnet launch. It is split into local (pre-testnet) tests and testnet validation. Parallel-safe steps can be run by separate agents in parallel across XAI components.

## Goals

- Catch coding errors before public exposure
- Validate protocol behavior, APIs, and infrastructure
- Stress critical services without cross-agent interference

## Requirements

- bash, curl, jq
- Optional: `k6` for load tests

## Public Testnet Security Baseline (Required)

Before opening the public testnet, ensure these controls are in place:

### Edge/WAF (Cloudflare or equivalent)
- Enable bot protection and WAF rules for RPC/API/Explorer/Faucet.
- Add rate limit rules for write-heavy endpoints:
  - `/send`, `/faucet/claim`, `/transaction/receive`, `/block/receive`
- Block obvious abuse patterns (high 4xx/429 spikes, known bad ASNs, malformed payloads).
- Enforce HTTPS only and redirect HTTP → HTTPS.

### Host Firewalling
- Allow only required public ports (RPC/REST/WS/Explorer/Faucet).
- Keep metrics/admin endpoints private (block 12000-12004, admin-only APIs).
- Restrict SSH to known IPs; disable password login.

### Node/API Hardening
- Set proxy-aware IP handling and (optionally) allow/deny lists:
  - `XAI_TRUST_PROXY_HEADERS=1`
  - `XAI_TRUSTED_PROXY_NETWORKS=<edge CIDRs>`
  - `XAI_API_IP_ALLOWLIST=<optional CIDRs>`
  - `XAI_API_IP_DENYLIST=<optional CIDRs>`
- Enable the public testnet hardening profile:
  - `XAI_PUBLIC_TESTNET_HARDENED=1`
  - `XAI_WRITE_AUTH_REQUIRED=1`
  - `XAI_WRITE_AUTH_EXEMPT_PATHS=<optional prefixes>`
- Ensure API keys are rotated and scoped (admin/operator/auditor).

### Monitoring & Response
- Alerts for auth failures, rate-limit spikes, mempool pressure, peer churn.
- Log retention + centralized security webhook sink.
- Incident response runbook reviewed and reachable.

## Setup

1) Copy the env template and edit values:

```bash
cp scripts/testnet/runbook/env.example scripts/testnet/runbook/.env
```

2) Edit `scripts/testnet/runbook/.env`:

- Set `RUN_ID` to a unique value per agent (e.g., `xai-agent1-YYYYMMDDHHMMSS`).
- Provide `ADDRESS` for faucet/balance checks.
- If JSON-RPC is enabled, set `JSONRPC_URL`.

3) Load the env file:

```bash
set -a
. scripts/testnet/runbook/.env
set +a
```

## Phase 0: Local Pre-Testnet Gates (must pass before public testnet)

### 0.1 Python unit tests

```bash
python -m venv venv
source venv/bin/activate
pip install .
pytest
```

### 0.2 Targeted unit suites (optional)

```bash
pytest tests/xai_tests/unit -q
```

## Phase 1: Parallel-Safe Testnet Suite

These steps are safe to run in parallel with other XAI components. They are read-only or minimal-impact.

### 1.1 Smoke checks

```bash
bash scripts/testnet/runbook/smoke.sh
```

### 1.2 Height progression

```bash
bash scripts/testnet/runbook/height_watch.sh
```

### 1.3 Error contract checks (invalid input should fail safely)

```bash
bash scripts/testnet/runbook/error_contract.sh
```

### 1.4 Read-only load (safe defaults)

```bash
k6 run scripts/testnet/runbook/k6_api_read.js
```

Optional tuning (still safe):

```bash
VUS=10 DURATION=3m k6 run scripts/testnet/runbook/k6_api_read.js
```

Baseline+peak wrapper (recommended):

```bash
bash scripts/testnet/runbook/run_k6_baseline_peak.sh
```

Summary output:

- `./out/<RUN_ID>/k6/summary.md`

Optional thresholds (override defaults):

```bash
P95_MS=500 P99_MS=2000 ERROR_RATE=0.001 k6 run scripts/testnet/runbook/k6_api_read.js
```

Calibration mode (prints suggested thresholds from observed p95/p99):

```bash
CALIBRATE=1 k6 run scripts/testnet/runbook/k6_api_read.js
```

Peak profile (higher load + relaxed thresholds):

```bash
PROFILE=peak k6 run scripts/testnet/runbook/k6_api_read.js
```

### 1.5 Faucet + balance (optional)

```bash
bash scripts/testnet/runbook/faucet_and_balance.sh
```

### 1.6 JSON-RPC smoke (optional)

Only run if JSON-RPC is enabled on your endpoint:

```bash
bash scripts/testnet/runbook/jsonrpc_smoke.sh
```

## Phase 2: Coordinated-Only Testnet Suite (schedule these)

These tests can affect other agents and must be scheduled to avoid interference.

- High-throughput transaction spam / mempool stress
- Primary node stop/start and failover validation
- SERVICES server stop/start
- Rate-limit and DDoS behavior validation under load

## Pass/Fail Criteria

- REST endpoints respond successfully
- Chain height does not decrease across checks
- Invalid input returns client errors, not 200/500
- Optional faucet/balance check returns a valid response
- k6 read-only load stays within agreed p95 latency and error rate thresholds
- Optional JSON-RPC smoke returns valid results

## Output Artifacts

- Outputs are written to `${OUT_DIR}/${RUN_ID}`
- Attach results to the overall prelaunch report
