# Mini App Manifest

Mini Apps/Frames extend the personal AI + analytics surface by exposing We-based polls, votes, games, and AML companions that can be embedded into any dashboard via `iframe` or React/SPA helpers. The manifest endpoint tells you what is available, how to embed it, and whether the on-chain AML metadata suggests high/low risk behavior.

## Manifest Endpoint

- Endpoint: `GET /mini-apps/manifest`
- Optional query: `?address=XAI1...` (validates the address and attaches its `risk_score`, `risk_level`, and `flag_reasons`)
- Response fields:
  - `mini_apps`: array of `id`, `name`, `description`, `app_type`, `embed_url`, `risk_focus`, `recommended_flow`, and `aml_cues`.
  - `aml_context`: risk snapshot (`risk_score`, `risk_level`, `flag_reasons`, `last_seen`) derived from the same on-chain data everywhere else (e.g., `/regulator/flagged`).

GUIs can call the endpoint once per session (or per user selection) and immediately render the provided `embed_url` inside a friendly wrapper.

## Embedding Best Practices

1. Use the returned `embed_url` inside an `iframe` or React `<Suspense>` component. Example:

   ```html
   <iframe
     src="https://miniapps.xai.network/polls/community-pulse?mode=clean"
     width="100%"
     height="420"
     frameborder="0"
     loading="lazy">
   </iframe>
   ```

2. Honor the `recommended_flow` value:
   - `"open"`: render the app as-is (low-risk).
   - `"balanced"` / `"observe"`: overlay risk guidance or request MFA before continuing.
   - `"cautious"` / `"limited"`: show the app behind a compliance wrapper (e.g., show a warning bar, require confirmation, or disable non-essential features).

3. Use `aml_cues` for quick visual hints (badges, icons) that match how the mini-app wants to be presented (e.g., `["high-risk-guard"]`).

4. If you pass an `address`, the returned `aml_context` lets you display a risk badge (`risk_level`, `risk_score`) near the widget so users understand whether the flow was tailored for low- or high-risk operations.

## Example Manifest Call

```bash
curl "http://localhost:18545/mini-apps/manifest?address=XAI1seededMiner..." \
  -H "Accept: application/json"
```

```json
{
  "success": true,
  "address": "XAI1seededMiner...",
  "aml_context": {
    "risk_score": 12,
    "risk_level": "low",
    "flag_reasons": [],
    "last_seen": 1734567890
  },
  "mini_apps": [
    {
      "id": "community-pulse",
      "name": "Community Pulse Poll",
      "embed_url": "https://miniapps.xai.network/polls/community-pulse?mode=low",
      "recommended_flow": "open",
      "aml_cues": ["low-risk-fill", "safe-mode"],
      "...": "..."
    }
  ]
}
```

## Why AML Metadata?

The same `risk_score` / `risk_level` fields that power `/regulator/flagged` are attached to each transaction and now surface again in the manifest so the UI can:

1. Personalize the call to show friendly polls when the address is clean.
2. Offer more guarded flows (e.g., `Mini App Guard`, `Treasure Hunt`) when ledger data says the address has interacted with suspicious transfers.
3. Propagate `flag_reasons` to the UI so analysts can quickly tie a mini-app session to compliance data without leaking private keys.

By combining mini-apps with AML metadata, dashboards keep the experience playful while signalling to users when a flow is risk-aware.
