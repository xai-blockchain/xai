-- AIXN Blockchain - Database Initialization Script
-- PostgreSQL initialization for Docker deployment

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS blockchain;
CREATE SCHEMA IF NOT EXISTS wallet;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO blockchain, public;

-- ============================================================================
-- Blockchain Tables
-- ============================================================================

-- Blocks table
CREATE TABLE IF NOT EXISTS blockchain.blocks (
    block_hash VARCHAR(64) PRIMARY KEY,
    block_height BIGINT NOT NULL UNIQUE,
    previous_hash VARCHAR(64),
    timestamp BIGINT NOT NULL,
    nonce BIGINT NOT NULL,
    difficulty INTEGER NOT NULL,
    merkle_root VARCHAR(64) NOT NULL,
    transaction_count INTEGER DEFAULT 0,
    size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_previous_block FOREIGN KEY (previous_hash)
        REFERENCES blockchain.blocks(block_hash) ON DELETE SET NULL
);

CREATE INDEX idx_blocks_height ON blockchain.blocks(block_height DESC);
CREATE INDEX idx_blocks_timestamp ON blockchain.blocks(timestamp DESC);
CREATE INDEX idx_blocks_previous ON blockchain.blocks(previous_hash);

-- Transactions table
CREATE TABLE IF NOT EXISTS blockchain.transactions (
    tx_hash VARCHAR(64) PRIMARY KEY,
    block_hash VARCHAR(64),
    sender VARCHAR(50),
    recipient VARCHAR(50) NOT NULL,
    amount NUMERIC(20, 8) NOT NULL,
    fee NUMERIC(20, 8) DEFAULT 0,
    nonce BIGINT NOT NULL,
    signature TEXT,
    timestamp BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_block FOREIGN KEY (block_hash)
        REFERENCES blockchain.blocks(block_hash) ON DELETE CASCADE
);

CREATE INDEX idx_transactions_block ON blockchain.transactions(block_hash);
CREATE INDEX idx_transactions_sender ON blockchain.transactions(sender);
CREATE INDEX idx_transactions_recipient ON blockchain.transactions(recipient);
CREATE INDEX idx_transactions_timestamp ON blockchain.transactions(timestamp DESC);
CREATE INDEX idx_transactions_status ON blockchain.transactions(status);

-- UTXO table
CREATE TABLE IF NOT EXISTS blockchain.utxos (
    tx_hash VARCHAR(64) NOT NULL,
    output_index INTEGER NOT NULL,
    address VARCHAR(50) NOT NULL,
    amount NUMERIC(20, 8) NOT NULL,
    spent BOOLEAN DEFAULT FALSE,
    spent_in_tx VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tx_hash, output_index)
);

CREATE INDEX idx_utxos_address ON blockchain.utxos(address) WHERE NOT spent;
CREATE INDEX idx_utxos_spent ON blockchain.utxos(spent);

-- ============================================================================
-- Wallet Tables
-- ============================================================================

-- Wallets table
CREATE TABLE IF NOT EXISTS wallet.wallets (
    address VARCHAR(50) PRIMARY KEY,
    public_key TEXT NOT NULL,
    balance NUMERIC(20, 8) DEFAULT 0,
    nonce BIGINT DEFAULT 0,
    wallet_type VARCHAR(20) DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wallets_balance ON wallet.wallets(balance DESC);
CREATE INDEX idx_wallets_type ON wallet.wallets(wallet_type);

-- Wallet transactions view
CREATE OR REPLACE VIEW wallet.wallet_transactions AS
SELECT
    address,
    tx_hash,
    CASE
        WHEN sender = address THEN 'sent'
        WHEN recipient = address THEN 'received'
    END AS transaction_type,
    CASE
        WHEN sender = address THEN -amount
        WHEN recipient = address THEN amount
    END AS net_amount,
    timestamp,
    status
FROM (
    SELECT sender AS address, tx_hash, sender, recipient, amount, timestamp, status
    FROM blockchain.transactions
    UNION ALL
    SELECT recipient AS address, tx_hash, sender, recipient, amount, timestamp, status
    FROM blockchain.transactions
) AS combined;

-- ============================================================================
-- Analytics Tables
-- ============================================================================

-- Daily statistics
CREATE TABLE IF NOT EXISTS analytics.daily_stats (
    stat_date DATE PRIMARY KEY,
    total_blocks INTEGER DEFAULT 0,
    total_transactions INTEGER DEFAULT 0,
    total_volume NUMERIC(20, 8) DEFAULT 0,
    avg_block_time NUMERIC(10, 2) DEFAULT 0,
    avg_transaction_fee NUMERIC(20, 8) DEFAULT 0,
    active_addresses INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_daily_stats_date ON analytics.daily_stats(stat_date DESC);

-- Network statistics
CREATE TABLE IF NOT EXISTS analytics.network_stats (
    timestamp BIGINT PRIMARY KEY,
    hash_rate NUMERIC(20, 2),
    difficulty INTEGER,
    peer_count INTEGER,
    mempool_size INTEGER,
    blockchain_size BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_network_stats_timestamp ON analytics.network_stats(timestamp DESC);

-- ============================================================================
-- Functions and Triggers
-- ============================================================================

-- Update wallet balance function
CREATE OR REPLACE FUNCTION wallet.update_wallet_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- Update sender balance
    IF NEW.sender IS NOT NULL THEN
        UPDATE wallet.wallets
        SET balance = balance - NEW.amount - NEW.fee,
            last_activity = NOW()
        WHERE address = NEW.sender;
    END IF;

    -- Update recipient balance
    UPDATE wallet.wallets
    SET balance = balance + NEW.amount,
        last_activity = NOW()
    WHERE address = NEW.recipient;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for balance updates (commented out - handle in application)
-- CREATE TRIGGER trg_update_balance
-- AFTER INSERT ON blockchain.transactions
-- FOR EACH ROW WHEN (NEW.status = 'confirmed')
-- EXECUTE FUNCTION wallet.update_wallet_balance();

-- Update daily stats function
CREATE OR REPLACE FUNCTION analytics.update_daily_stats()
RETURNS void AS $$
BEGIN
    INSERT INTO analytics.daily_stats (
        stat_date,
        total_blocks,
        total_transactions,
        total_volume,
        avg_block_time,
        active_addresses
    )
    SELECT
        CURRENT_DATE,
        COUNT(DISTINCT b.block_hash),
        COUNT(DISTINCT t.tx_hash),
        COALESCE(SUM(t.amount), 0),
        AVG(b.timestamp - LAG(b.timestamp) OVER (ORDER BY b.block_height)),
        COUNT(DISTINCT t.sender) + COUNT(DISTINCT t.recipient)
    FROM blockchain.blocks b
    LEFT JOIN blockchain.transactions t ON b.block_hash = t.block_hash
    WHERE DATE(b.created_at) = CURRENT_DATE
    ON CONFLICT (stat_date)
    DO UPDATE SET
        total_blocks = EXCLUDED.total_blocks,
        total_transactions = EXCLUDED.total_transactions,
        total_volume = EXCLUDED.total_volume,
        avg_block_time = EXCLUDED.avg_block_time,
        active_addresses = EXCLUDED.active_addresses;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Initial Data
-- ============================================================================

-- Insert genesis block placeholder (will be replaced by application)
INSERT INTO blockchain.blocks (
    block_hash,
    block_height,
    previous_hash,
    timestamp,
    nonce,
    difficulty,
    merkle_root,
    transaction_count,
    size
) VALUES (
    '0000000000000000000000000000000000000000000000000000000000000000',
    0,
    '0000000000000000000000000000000000000000000000000000000000000000',
    EXTRACT(EPOCH FROM NOW())::BIGINT,
    0,
    1,
    '0000000000000000000000000000000000000000000000000000000000000000',
    0,
    0
) ON CONFLICT (block_hash) DO NOTHING;

-- ============================================================================
-- Grants and Permissions
-- ============================================================================

-- Grant permissions to aixn user (will be created by Docker)
GRANT USAGE ON SCHEMA blockchain TO PUBLIC;
GRANT USAGE ON SCHEMA wallet TO PUBLIC;
GRANT USAGE ON SCHEMA analytics TO PUBLIC;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA blockchain TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA wallet TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO PUBLIC;

-- ============================================================================
-- Maintenance
-- ============================================================================

-- Vacuum and analyze
VACUUM ANALYZE blockchain.blocks;
VACUUM ANALYZE blockchain.transactions;
VACUUM ANALYZE wallet.wallets;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'AIXN Blockchain database initialized successfully';
END $$;
