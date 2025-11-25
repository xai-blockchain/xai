# XAI Browser Wallet & Miner Extension

This Chrome/Edge/Firefox-compatible extension exposes the mining and wallet-to-wallet trading APIs in a single popup.  
It is intentionally focused on API access (no KYC) and serves as a light WalletConnect-style pane for browser wallets.

## Features

- Configure the API host and wallet address.
- Start/stop the node miner so you can earn rewards directly from the popup.
- Browse current trade orders and matches.
- Submit new orders (sell or buy) that are routed through `POST /wallet-trades/orders`.
- Automatically refresh matches and broadcast events on settlement.

## Installation

1. Build the extension by leaving the `browser_wallet_extension/` folder as-is.
2. In your Chromium-based or Firefox browser open the extensions page (e.g., `chrome://extensions`).
3. Enable developer mode (if required) and choose “Load unpacked”/“Load Temporary Add-on”.
4. Point it at `xai/browser_wallet_extension`.

## API Notes

- Mining controls call `/mining/start`, `/mining/stop`, and `/mining/status`.
-- Replace the default API host (`http://localhost:8545`) using the API Host field in the popup if your node runs elsewhere.
-- The wallet registers a WalletConnect-style session (`/wallet-trades/register`) and signs each order payload with the session secret before posting; if you operate multiple nodes, configure `XAI_WALLET_TRADE_PEER_SECRET/XAI_WALLET_TRADE_PEERS` so they gossip orders via `/wallet-trades/gossip`.
-- For enhanced security the extension now performs a WalletConnect-style ECDH handshake via `/wallet-trades/wc/handshake` and `/wallet-trades/wc/confirm`, deriving per-session secrets used for signing/encrypted trade payloads.
