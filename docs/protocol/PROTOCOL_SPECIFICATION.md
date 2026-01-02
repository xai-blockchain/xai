# XAI Protocol Specification (Draft)

Version: 0.1
Status: Draft
Last updated: 2026-01-01

## Overview

XAI is a proof-of-work blockchain with a UTXO transaction model, a JSON-based REST API, and a Python reference implementation.

## Networks

Parameters are defined in `src/xai/core/config.py`.

| Network | ID | Address Prefix | Block Time Target | Initial Reward | Halving Interval | Max Supply |
| --- | --- | --- | --- | --- | --- | --- |
| Testnet | `0xABCD` | `TXAI` | 120 seconds | 12.0 XAI | 262,800 blocks | 121,000,000 XAI |
| Mainnet | `0x5841` | `XAI` | 120 seconds | 12.0 XAI | 262,800 blocks | 121,000,000 XAI |

## Consensus

- Proof-of-work with SHA-256 over the canonical JSON block header.
- `difficulty` is the number of leading zeroes required in the block hash.

### Block Header Fields

- `index`
- `previous_hash`
- `merkle_root`
- `timestamp`
- `difficulty`
- `nonce`
- `version` (optional, included in hash when set)

## Transactions

Transactions are UTXO-based and signed with secp256k1 ECDSA. Canonical JSON serialization is used for hashing.

Common fields include:

- `sender`
- `recipient`
- `amount`
- `fee`
- `nonce`
- `timestamp`
- `public_key`
- `signature`
- `inputs` and `outputs`
- `metadata` (optional)

## Addresses

Addresses use a network prefix (`XAI` or `TXAI`) followed by a hexadecimal body. Standard addresses use 40 hex characters, with optional checksum handling.

## Notes

This document reflects the current implementation and may change as the code evolves.
