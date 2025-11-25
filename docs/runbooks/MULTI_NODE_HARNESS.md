# Multi-node Integration Harness

This harness exercises an automated, multi-node deployment of the XAI node binary and verifies that consensus/transaction propagation holds once the network is formed.  It is intended for CI/QA pipelines that need an end-to-end check before promoting complex changes.

## What the harness does

1. Spins up `N` nodes (default 3), each with isolated disk-backed state directories and dedicated ports.
2. Ensures every node exposes the health API before forming a peer mesh via `/peers/add`.
3. Requests a faucet credit so there is a pending transaction, waits for the auto-miner to produce a block, and confirms every node sees the same height/hash.
4. Tears down the nodes cleanly and leaves the temporary data directory for post-mortem inspection, if needed.

## Running the harness

Execute it from the repo root using the bundled virtualenv:

```
./venv/bin/python scripts/tools/multi_node_harness.py --nodes 3 --base-port 8550
```

Optional arguments:

- `--nodes`: Number of nodes to start (3 by default).  
- `--base-port`: Port for the first node; each additional node increments sequentially.

The harness prints the temporary data directory so you can inspect `blocks/`, `contracts_state.json`, or any logs after the run.

## CI integration ideas

- Run the harness in a matrix job that toggles `XAI_NETWORK=testnet` vs. a deterministic fixture to guard consensus changes.
- Collect the temporary directory path from the output and upload it as an artifact for debugging when failures occur.
- Pair the script with `./venv/bin/python -m pytest tests/xai_tests/integration/test_multi_node_consensus.py` for a broader coverage phase.

## Security & Reliability

- The harness only speaks to nodes on `127.0.0.1` and disables API auth via `XAI_API_AUTH_REQUIRED=0`, so run it in isolated CI workers.  
- Each node mines only when there are pending transactions, which prevents runaway block production.  
- Any failure stops all subprocesses via `SIGINT` and kills lingering processes after a timeout.
