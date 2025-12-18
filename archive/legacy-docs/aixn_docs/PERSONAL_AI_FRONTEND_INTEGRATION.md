# Personal AI Browser Wallet Integration

## Purpose
Users of the XAI browser wallet or extension can now call the new `/personal-ai/*` endpoints.
This document explains how to send the required headers, build the payload, and handle the responses
that the `PersonalAIAssistant` produces.

## Required Headers
All personal AI endpoints authenticate via headers so that the wallet never ships private keys to the server:

| Header | Description |
| --- | --- |
| `X-User-Address` | The XAI address of the requesting wallet (e.g., `XAI1abc...`). |
| `X-User-API-Key` | The user’s own AI provider key (must be encrypted in transit). |
| `X-AI-Provider` | Provider label (`anthropic`, `openai`, `groq`, etc.). |
| `X-AI-Model` | Model name (e.g., `claude-opus-4`, `gpt-4-turbo`). |

## Example Fetch
```javascript
const personalAiBase = 'http://localhost:12001/personal-ai';

async function requestAtomicSwap({userAddress, apiKey, provider, model, swapDetails}) {
  const response = await fetch(`${personalAiBase}/atomic-swap`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Address': userAddress,
      'X-User-API-Key': apiKey,
      'X-AI-Provider': provider,
      'X-AI-Model': model
    },
    body: JSON.stringify({swap_details: swapDetails})
  });

  const data = await response.json();
  if (!data.success) {
    throw new Error(data.message || 'Personal AI request failed');
  }

  return data;
}
```

The same headers work for `/smart-contract/create`, `/smart-contract/deploy`, `/transaction/optimize`, `/analyze`, and `/wallet/analyze`.  Just change the route path and payload.

## Suggested Flow
1. Collect the AI API key from the user wallet UI and provide the `X-User-API-Key` header.
2. Build `swap_details`, `contract_description`, or `transaction` payloads as needed.
3. Call one of the endpoints and display the returned instructions, warnings, `ai_cost`, and generated code/transaction.
4. Let the user review, sign, and broadcast the final transaction themselves.

## Rate Limits
Personal AI endpoints share the assistant’s internal rate limits (`100/hour`, `500/day`, `5,000/month`).  The response will include `retry_after` when a limit is hit.

## Verification Tips
- After a successful request, inspect the `ai_analysis` object to show atomic swap instructions.
- Check `swap_transaction` or `contract_code` in the payload before presenting it to the user.
- For integration testing, wire the wallet to the `http://localhost:12001/personal-ai` base URL or your deployed node, and replay requests using the snippet above.

## Key Lifecycle & Deletion Assurance

The wallet/miner UI now exposes **three key-management modes**:

1. **Temporary** (default): the key exists only in the input field and is deleted immediately after the session, with a “key deleted” notice.
2. **Session cache**: the key is encrypted in browser storage while the extension is open; click “Clear Key” to wipe it and see a confirmation message.
3. **External key manager**: the wallet never stores the key—users provide it manually for each request, ideal for hardware-secured flows.

Choose the mode that matches your security comfort, then enter the key, provider, and model for the request. After each call, the UI confirms the key lifecycle (deleted or cached as appropriate).

The wallet/miner UI accepts your AI API key just for the duration of each request. To keep the key on-device only while it is needed:

1. Prompt the user for the key right before the Personal AI call and keep it in-memory only (e.g., in an input field or temporary variable).
2. Send the key in the `X-User-API-Key` header when invoking `/personal-ai/*`. Do not store it on disk, logs, or backend data structures.
3. Once the AI response returns (success or error), immediately clear the input/variable and show a confirmation such as “AI session complete—your AI API key has been deleted from this wallet.” The browser wallet popup already follows this pattern (`popup.js` clears the field and updates `#aiKeyDeleted`).
4. If the user wants to reuse the assistant later, ask them to re-enter their key; no cached value should survive between sessions.

This workflow guarantees the assistant never retains the user’s API key, purely operates on user-supplied credentials, and transparently notifies the user when the key is deleted.
