# Troubleshooting Guide

## Common Errors

- **ModuleNotFoundError: No module named 'xai'**  
  Activate the virtualenv and reinstall editable:  
  ```bash
  source .venv/bin/activate
  pip install -e .
  ```

- **Invalid address prefix**  
  Use wallet-generated addresses (must start with `XAI`/`TXAI`). Avoid hardcoded placeholders.

- **Request too large (413)**  
  Reduce JSON body size or increase `API_MAX_JSON_BYTES` for local dev. Large lists should be paginated.

- **Rate limit exceeded (429)**  
  Back off; tune `RATE_LIMIT_REQUESTS/RATE_LIMIT_WINDOW` for local testing.

- **CSRF token missing/invalid (403)**  
  Fetch `/csrf-token` and include it in `X-CSRF-Token` for POST/PUT/DELETE.

- **Stale transaction timestamp**  
  Ensure client clock is in sync and payload timestamp is recent; `/send` rejects stale/future timestamps.

- **Hardware wallet not detected**  
  Ensure drivers/libs are installed; set `XAI_ALLOW_MOCK_HARDWARE_WALLET=true` only in test environments.

## Network/Node Issues

- **Peers not connecting**: Verify `p2p_port` is open, firewall allows traffic, and version/capability handshake is correct.
- **Explorer/backend fails to fetch mempool**: Ensure node is running and reachable at the configured RPC URL; check logs for connection refusals.

## Logs & Diagnostics

- Enable DEBUG logging for local runs via config/env.
- Check structured logs for `event` keys; they include error context for rate limits, CSRF, signing, etc.

## Getting Help

- Review `docs/api/api_error_codes.md` and `docs/api/rate_limits.md` for HTTP issues.
- Consult `docs/user-guides/faq.md` for quick answers.
- For suspected security issues, follow the private contact in `SECURITY.md`.***
