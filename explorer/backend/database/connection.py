from __future__ import annotations

"""
Database connection management for XAI Explorer
"""
import asyncpg
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)

class Database:
    """Async PostgreSQL database connection manager"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        """Establish database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=10,
                max_size=50,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def is_connected(self) -> bool:
        """Check if database is connected"""
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def fetch_one(self, query: str, *args) -> dict[str, Any] | None:
        """Fetch single row"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def fetch_all(self, query: str, *args) -> list[dict[str, Any]]:
        """Fetch multiple rows"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute(self, query: str, *args) -> str:
        """Execute query without result"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args: Sequence[Sequence[Any]]) -> None:
        """Execute many statements efficiently."""
        if not args:
            return
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args)

    async def run_migrations(self) -> None:
        """Create core tables for explorer (idempotent)."""
        migrations = [
            """
            CREATE TABLE IF NOT EXISTS blocks (
                height BIGINT PRIMARY KEY,
                hash TEXT UNIQUE NOT NULL,
                timestamp TIMESTAMPTZ,
                miner TEXT,
                difficulty NUMERIC(36,18),
                tx_count INTEGER DEFAULT 0,
                raw JSONB NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);",
            """
            CREATE TABLE IF NOT EXISTS transactions (
                txid TEXT PRIMARY KEY,
                block_height BIGINT REFERENCES blocks(height) ON DELETE SET NULL,
                sender TEXT,
                recipient TEXT,
                amount NUMERIC(36,18),
                fee NUMERIC(36,18),
                status TEXT,
                raw JSONB NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_transactions_block_height ON transactions(block_height);",
            """
            CREATE TABLE IF NOT EXISTS ai_tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT,
                task_type TEXT,
                priority TEXT,
                requester_address TEXT,
                provider_address TEXT,
                cost_estimate NUMERIC(36,18),
                actual_cost NUMERIC(36,18),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                raw JSONB NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS ai_providers (
                provider_address TEXT PRIMARY KEY,
                provider_name TEXT,
                reputation_score NUMERIC(10,4),
                total_tasks_completed INTEGER DEFAULT 0,
                total_tasks_failed INTEGER DEFAULT 0,
                total_earnings NUMERIC(36,18),
                last_seen TIMESTAMPTZ,
                raw JSONB NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS mempool_transactions (
                txid TEXT PRIMARY KEY,
                sender TEXT,
                recipient TEXT,
                amount NUMERIC(36,18),
                fee NUMERIC(36,18),
                fee_rate NUMERIC(36,18),
                size_bytes INTEGER,
                nonce BIGINT,
                tx_type TEXT,
                rbf_enabled BOOLEAN,
                first_seen TIMESTAMPTZ DEFAULT timezone('utc', now()),
                last_updated TIMESTAMPTZ DEFAULT timezone('utc', now()),
                raw JSONB NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_mempool_transactions_last_updated ON mempool_transactions(last_updated DESC);",
            """
            CREATE TABLE IF NOT EXISTS mempool_stats (
                captured_at TIMESTAMPTZ PRIMARY KEY,
                tx_count INTEGER,
                size_bytes BIGINT,
                total_fees NUMERIC(36,18),
                total_value NUMERIC(36,18),
                pressure JSONB,
                fees JSONB,
                raw JSONB NOT NULL
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_mempool_stats_captured ON mempool_stats(captured_at DESC);",
        ]
        for statement in migrations:
            await self.execute(statement)
        logger.info("Explorer migrations executed successfully")

    async def upsert_block(self, block: dict[str, Any]) -> None:
        """Persist or update a block record."""
        if not block:
            return
        txs = block.get("transactions") or []
        query = """
        INSERT INTO blocks (height, hash, timestamp, miner, difficulty, tx_count, raw)
        VALUES ($1, $2, to_timestamp($3), $4, $5, $6, $7::jsonb)
        ON CONFLICT (height) DO UPDATE SET
            hash = EXCLUDED.hash,
            timestamp = EXCLUDED.timestamp,
            miner = EXCLUDED.miner,
            difficulty = EXCLUDED.difficulty,
            tx_count = EXCLUDED.tx_count,
            raw = EXCLUDED.raw;
        """
        await self.execute(
            query,
            block.get("index") or block.get("height"),
            block.get("hash"),
            block.get("timestamp") or block.get("time") or 0,
            block.get("miner"),
            block.get("difficulty"),
            len(txs),
            json.dumps(block),
        )
        if txs:
            await self.upsert_transactions(txs, block.get("index") or block.get("height"))

    async def upsert_transactions(self, transactions: list[dict[str, Any]], block_height: Any = None) -> None:
        """Persist transactions in bulk."""
        if not transactions:
            return
        args = []
        for tx in transactions:
            args.append(
                [
                    tx.get("txid"),
                    block_height,
                    tx.get("sender") or tx.get("from"),
                    tx.get("recipient") or tx.get("to"),
                    tx.get("amount") or tx.get("value"),
                    tx.get("fee") or tx.get("gas_fee"),
                    tx.get("status", "confirmed"),
                    json.dumps(tx),
                ]
            )
        query = """
        INSERT INTO transactions (txid, block_height, sender, recipient, amount, fee, status, raw)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
        ON CONFLICT (txid) DO UPDATE SET
            block_height = EXCLUDED.block_height,
            sender = EXCLUDED.sender,
            recipient = EXCLUDED.recipient,
            amount = EXCLUDED.amount,
            fee = EXCLUDED.fee,
            status = EXCLUDED.status,
            raw = EXCLUDED.raw;
        """
        await self.execute_many(query, args)

    async def upsert_ai_task(self, task: dict[str, Any]) -> None:
        """Persist AI task metadata for explorer analytics."""
        if not task:
            return
        query = """
        INSERT INTO ai_tasks (
            task_id, status, task_type, priority, requester_address, provider_address,
            cost_estimate, actual_cost, started_at, completed_at, raw
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8, to_timestamp($9), to_timestamp($10), $11::jsonb)
        ON CONFLICT (task_id) DO UPDATE SET
            status = EXCLUDED.status,
            task_type = EXCLUDED.task_type,
            priority = EXCLUDED.priority,
            requester_address = EXCLUDED.requester_address,
            provider_address = EXCLUDED.provider_address,
            cost_estimate = EXCLUDED.cost_estimate,
            actual_cost = EXCLUDED.actual_cost,
            started_at = EXCLUDED.started_at,
            completed_at = EXCLUDED.completed_at,
            raw = EXCLUDED.raw;
        """
        await self.execute(
            query,
            task.get("task_id") or task.get("id"),
            task.get("status"),
            task.get("task_type"),
            task.get("priority"),
            task.get("requester_address"),
            task.get("provider_address"),
            task.get("cost_estimate"),
            task.get("actual_cost"),
            task.get("started_at") or 0,
            task.get("completed_at") or 0,
            json.dumps(task),
        )

    async def upsert_mempool_transactions(self, transactions: list[dict[str, Any]]) -> None:
        """Persist pending mempool transactions with rolling updates."""
        if not transactions:
            await self.execute(
                "DELETE FROM mempool_transactions WHERE last_updated < timezone('utc', now()) - interval '2 hours';"
            )
            return

        rows = []
        for tx in transactions:
            rows.append(
                [
                    tx.get("txid"),
                    tx.get("sender"),
                    tx.get("recipient"),
                    tx.get("amount"),
                    tx.get("fee"),
                    tx.get("fee_rate"),
                    tx.get("size_bytes"),
                    tx.get("nonce"),
                    tx.get("type"),
                    bool(tx.get("rbf_enabled")),
                    json.dumps(tx),
                ]
            )
        query = """
        INSERT INTO mempool_transactions (
            txid, sender, recipient, amount, fee, fee_rate, size_bytes, nonce, tx_type, rbf_enabled, raw
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
        ON CONFLICT (txid) DO UPDATE SET
            sender = EXCLUDED.sender,
            recipient = EXCLUDED.recipient,
            amount = EXCLUDED.amount,
            fee = EXCLUDED.fee,
            fee_rate = EXCLUDED.fee_rate,
            size_bytes = EXCLUDED.size_bytes,
            nonce = EXCLUDED.nonce,
            tx_type = EXCLUDED.tx_type,
            rbf_enabled = EXCLUDED.rbf_enabled,
            raw = EXCLUDED.raw,
            last_updated = timezone('utc', now());
        """
        await self.execute_many(query, rows)
        await self.execute(
            "DELETE FROM mempool_transactions WHERE last_updated < timezone('utc', now()) - interval '2 hours';"
        )

    async def record_mempool_snapshot(self, stats: dict[str, Any], overview: dict[str, Any] | None = None) -> None:
        """Record mempool congestion snapshot for analytics."""
        if not stats and not overview:
            return
        overview = overview or {}
        pressure = stats.get("pressure", {}) if stats else {}
        tx_count = int(
            pressure.get("pending_transactions")
            or overview.get("pending_count")
            or overview.get("pool_size")
            or 0
        )
        size_bytes = int(pressure.get("size_bytes") or overview.get("size_bytes") or 0)
        total_fees = float(overview.get("total_fees") or 0.0)
        total_value = float(overview.get("total_amount") or 0.0)

        query = """
        INSERT INTO mempool_stats (
            captured_at, tx_count, size_bytes, total_fees, total_value, pressure, fees, raw
        ) VALUES (
            timezone('utc', now()), $1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb
        );
        """
        await self.execute(
            query,
            tx_count,
            size_bytes,
            total_fees,
            total_value,
            json.dumps(pressure or {}),
            json.dumps(stats.get("fees") if stats else {}),
            json.dumps(stats or overview),
        )
        await self.execute(
            "DELETE FROM mempool_stats WHERE captured_at < timezone('utc', now()) - interval '24 hours';"
        )

    async def get_recent_mempool_transactions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return most recently updated mempool transactions."""
        query = """
        SELECT txid, sender, recipient, amount, fee, fee_rate, size_bytes, nonce, tx_type,
               rbf_enabled, first_seen, last_updated, raw
        FROM mempool_transactions
        ORDER BY last_updated DESC
        LIMIT $1;
        """
        return await self.fetch_all(query, limit)

    async def get_latest_mempool_stats(self) -> dict[str, Any] | None:
        """Return the latest mempool snapshot."""
        query = """
        SELECT captured_at, tx_count, size_bytes, total_fees, total_value, pressure, fees, raw
        FROM mempool_stats
        ORDER BY captured_at DESC
        LIMIT 1;
        """
        return await self.fetch_one(query)
