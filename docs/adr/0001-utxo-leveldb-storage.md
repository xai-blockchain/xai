# ADR-0001: UTXO LevelDB Storage

**Status:** Accepted (Implemented 2025-12-28)
**Date:** 2025-12-28

## Context
Current UTXO storage uses JSON file (`utxo_set.json`). At scale (>500k UTXOs), this becomes a bottleneck:
- Full file reparse on startup: O(n) for all UTXOs
- Full file rewrite on each block: O(n) serialization
- Memory: entire set loaded (185MB at 1M UTXOs)

## Decision
Migrate to LevelDB via adapter pattern:
1. Create abstract `UTXOStore` interface
2. Implement `MemoryUTXOStore` (current dict-based)
3. Add `LevelDBUTXOStore` with plyvel

Key schema: `utxo:{txid}:{vout}` -> UTXO JSON, `addr:{address}:{txid}:{vout}` for range scans.

## Consequences
**Positive:**
- 6-10x faster address queries via range scans
- 94% memory reduction at 100k+ UTXOs
- Incremental writes (append-only)

**Negative:**
- Binary format not human-readable
- Requires leveldb-dev on Ubuntu

**Migration:** Auto-convert existing JSON on first LevelDB init.
