# Thread Safety Concerns in Shared State

---
status: pending
priority: p2
issue_id: 033
tags: [concurrency, thread-safety, race-condition, architecture, code-review]
dependencies: []
---

## Problem Statement

Multiple components access shared state (blockchain, mempool, peer list) without proper synchronization. This can cause race conditions, data corruption, and inconsistent views across concurrent operations.

## Findings

### Locations
**Files:**
- `src/xai/core/blockchain.py` - Chain state modifications
- `src/xai/network/peer_manager.py` - Peer list management
- `src/xai/core/mempool.py` - Transaction pool operations

### Evidence

```python
# Unsynchronized access to chain state
class Blockchain:
    def add_block(self, block):
        # No lock acquired
        self.chain.append(block)  # Thread A
        self.update_utxo_set(block)  # Thread B could read stale

    def get_latest_block(self):
        # Can return inconsistent state if add_block is running
        return self.chain[-1]

# Peer list modification without locks
class PeerManager:
    def add_peer(self, peer):
        self.peers.append(peer)  # No synchronization

    def broadcast(self, message):
        for peer in self.peers:  # List can change during iteration
            peer.send(message)
```

### Impact

- **Data Corruption**: Inconsistent chain state
- **Lost Updates**: Transactions or blocks dropped
- **Iteration Errors**: "list changed size during iteration"
- **Race Conditions**: Double-spend possible in edge cases

## Proposed Solutions

### Option A: Threading Locks (Recommended)
**Effort:** Medium | **Risk:** Low

```python
import threading
from contextlib import contextmanager
from typing import TypeVar, Generic

T = TypeVar('T')

class ThreadSafeState(Generic[T]):
    """Thread-safe wrapper for shared state."""

    def __init__(self, initial_value: T):
        self._value = initial_value
        self._lock = threading.RLock()

    @contextmanager
    def locked(self):
        """Context manager for exclusive access."""
        with self._lock:
            yield self._value

    def get(self) -> T:
        """Get a snapshot (copy for mutable types)."""
        with self._lock:
            if isinstance(self._value, list):
                return self._value.copy()
            return self._value


class Blockchain:
    def __init__(self):
        self._chain_lock = threading.RLock()
        self._chain: List[Block] = []

    def add_block(self, block: Block) -> bool:
        """Thread-safe block addition."""
        with self._chain_lock:
            if not self._validate_block(block):
                return False
            self._chain.append(block)
            self._update_utxo_set(block)
            return True

    def get_latest_block(self) -> Optional[Block]:
        """Thread-safe chain access."""
        with self._chain_lock:
            return self._chain[-1] if self._chain else None

    @contextmanager
    def chain_snapshot(self):
        """Get consistent chain view for reads."""
        with self._chain_lock:
            yield list(self._chain)
```

### Option B: Asyncio with Single Writer
**Effort:** Medium | **Risk:** Medium

```python
import asyncio
from asyncio import Queue

class ChainWriter:
    """Single-threaded chain writer with async queue."""

    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.write_queue: Queue[Block] = Queue()
        self._running = False

    async def start(self):
        """Process writes sequentially."""
        self._running = True
        while self._running:
            block = await self.write_queue.get()
            try:
                await self._process_block(block)
            finally:
                self.write_queue.task_done()

    async def submit_block(self, block: Block) -> asyncio.Future:
        """Submit block for processing."""
        future = asyncio.Future()
        await self.write_queue.put((block, future))
        return await future
```

### Option C: Copy-on-Write Pattern
**Effort:** Small | **Risk:** Low

```python
import copy
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ImmutableChainState:
    """Immutable chain state - modifications create new instances."""
    blocks: tuple
    utxo_set: frozenset

    def with_new_block(self, block: Block) -> "ImmutableChainState":
        """Return new state with block added."""
        new_blocks = self.blocks + (block,)
        new_utxos = self._compute_new_utxos(block)
        return ImmutableChainState(new_blocks, new_utxos)
```

## Recommended Action

Implement Option A for immediate safety, consider Option C for critical state.

## Technical Details

**Components Requiring Synchronization:**
1. `Blockchain.chain` - All read/write operations
2. `Blockchain.utxo_set` - Must be atomic with chain updates
3. `PeerManager.peers` - List modifications and iterations
4. `Mempool.transactions` - Add/remove/query operations
5. `StateManager.balances` - Balance updates

**Testing Strategy:**
```python
def test_concurrent_block_addition():
    """Test thread safety of block addition."""
    blockchain = Blockchain()
    errors = []

    def add_blocks(start: int):
        for i in range(100):
            try:
                blockchain.add_block(create_block(start + i))
            except Exception as e:
                errors.append(e)

    threads = [
        threading.Thread(target=add_blocks, args=(i * 100,))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(blockchain.chain) == 1000
```

## Acceptance Criteria

- [ ] RLock protection for chain state
- [ ] Peer list synchronized for iteration
- [ ] Mempool operations thread-safe
- [ ] No "list changed during iteration" errors
- [ ] Concurrent stress tests pass
- [ ] Deadlock detection in tests

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-07 | Issue identified by architecture-strategist agent | Concurrency risk |

## Resources

- [Python Threading](https://docs.python.org/3/library/threading.html)
- [Thread Safety Patterns](https://realpython.com/intro-to-python-threading/)
