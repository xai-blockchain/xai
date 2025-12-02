# Fast Mining Control

Fast mining is a **test-only** convenience to cap proof-of-work difficulty during local runs.

- **Env flags**: `XAI_FAST_MINING=1` enables the cap; `XAI_MAX_TEST_MINING_DIFFICULTY` sets the ceiling (default `4`).
- **Mainnet blocked**: initialization raises if `XAI_FAST_MINING=1` while `XAI_NETWORK=mainnet`, and a critical security event (`config.fast_mining_rejected`) is emitted.
- **Telemetry**: when enabled on non-mainnet, a warning security event (`config.fast_mining_enabled`) includes the network and cap; surfaces in SIEM webhook sinks.
- **Operational guidance**:
  - Do **not** set `XAI_FAST_MINING` in production or staging overlays.
  - Watch for the above security events; treat any production occurrence as a release blocker.
  - Keep caps low in tests to prevent runaway PoW effort; raise only for targeted perf exercises.
- **Resetting to normal**: unset `XAI_FAST_MINING` (or set to `0`) and restart the node. Difficulty will follow standard adjustment rules.
