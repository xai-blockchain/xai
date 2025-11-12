# Micro-AI Assistant Network

The personal AI assistant now exposes a **network of micro-assistants** with distinct personalities, skill sets, and growth metrics. Each request can be routed through a different micro-assistant based on user preference (`X-AI-Assistant` header) or left to the default “Guiding Mentor”.

## Key capabilities

| Name | Personality | Skills | Profile info |
| --- | --- | --- | --- |
| Guiding Mentor | Calm, explanatory, patient | onboarding, contracts | Ideal for newcomers who want step-by-step instructions. |
| Trading Sage | Rapid, opportunistic, data-driven | swaps, liquidity, markets | Stays focused on fees, slippage, and arbitrage opportunities. |
| Safety Overseer | Skeptical, risk-aware | security, compliance, time capsules | Highlights guardrails and recovery safeguards. |

## Aggregate learning

- Every assistant tracks usage count, tokens consumed, satisfaction, and last active timestamp.
- The network records trending skills from aggregated usage (e.g., “swaps”, “gas optimizations”) so new apps can surface the most relevant assistants for their context.
- The `personal-ai/assistants` endpoint (see `docs/COMPREHENSIVE_API_DOCUMENTATION.md`) returns both per-assistant profiles and aggregate metrics like total requests, tokens, and trending skills.

## Integration ideas

1. Surface the assistant roster in the wallet dashboard along with metrics, letting users choose “Trading Sage” or “Safety Overseer” before issuing a contract.
2. Track satisfaction scores (per profile) to let apps nudge users toward under-used assistants, encouraging viral discovery as each assistant “grows” with usage.
3. Log `assistant_profile` + `assistant_aggregate` data in the response so explorers or UIs can display what assistant provided the advice and how the network is learning over time.
