# XAI Interoperability (Aura + PAW)

This document is the single source of truth for cross-chain compatibility references in the XAI repo. XAI maintains a distinct identity and codebase, while enabling explicit cross-chain interoperability with **Aura** and **PAW** where required.

## Principles

- XAI code and infrastructure remain XAI-centric.
- Cross-chain integration references should be functional and scoped (e.g., genesis settings, wallet/bridge compatibility, relayer configs).
- Avoid unrelated documentation or tooling that mentions other chains.

## Allowed References

The following categories may explicitly reference Aura or PAW when necessary:

- Genesis or network configuration enabling cross-chain transactions
- Wallet compatibility and address format support
- Shared multi-chain wallet location: `/home/hudson/blockchain-projects/shared/wallet/multi-chain-wallet`
- Bridge or relayer configuration
- Chain registry or connection metadata

## Not Allowed

- Multi-chain monitoring configs
- Shared infra tooling for multiple chains
- Docs or examples that mention other chains outside of this file

If a new interop surface is added, document it here and keep the implementation scoped to XAI functionality.
