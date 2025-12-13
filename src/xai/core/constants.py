"""
XAI Blockchain Constants

This module contains all magic numbers used throughout the codebase,
organized by category for better maintainability and understanding.

NOTE: Changes to consensus-critical constants (marked with [CONSENSUS])
will result in a hard fork. Use extreme caution and coordinate with
the network before modifying these values.
"""

from typing import Final

# =============================================================================
# TIME CONSTANTS (in seconds)
# =============================================================================

# Basic time units
SECONDS_PER_MINUTE: Final[int] = 60
SECONDS_PER_HOUR: Final[int] = 3600  # 60 * 60
SECONDS_PER_DAY: Final[int] = 86400  # 60 * 60 * 24
SECONDS_PER_WEEK: Final[int] = 604800  # 60 * 60 * 24 * 7
SECONDS_PER_30_DAYS: Final[int] = 2592000  # 60 * 60 * 24 * 30
SECONDS_PER_YEAR: Final[int] = 31536000  # 60 * 60 * 24 * 365

# Common time intervals
SECONDS_2_MINUTES: Final[int] = 120
SECONDS_5_MINUTES: Final[int] = 300
SECONDS_10_MINUTES: Final[int] = 600
SECONDS_15_MINUTES: Final[int] = 900
SECONDS_30_MINUTES: Final[int] = 1800
SECONDS_2_HOURS: Final[int] = 7200

# =============================================================================
# BLOCKCHAIN CONSENSUS CONSTANTS [CONSENSUS - DO NOT CHANGE]
# =============================================================================

# Block timing
BLOCK_TIME_TARGET_SECONDS: Final[int] = 120  # 2 minutes per block
BLOCKS_PER_HOUR: Final[int] = 30  # 60 / 2
BLOCKS_PER_DAY: Final[int] = 720  # 24 * 30
BLOCKS_PER_WEEK: Final[int] = 5040  # 7 * 720
BLOCKS_PER_YEAR: Final[int] = 262800  # 365 * 720

# Supply and rewards
MAX_SUPPLY: Final[float] = 121_000_000.0  # Maximum coin supply (Bitcoin tribute: 121M)
INITIAL_BLOCK_REWARD: Final[float] = 12.0  # Initial mining reward per block
HALVING_INTERVAL_BLOCKS: Final[int] = 262800  # Halving occurs every year (262800 blocks)

# Difficulty adjustment
DIFFICULTY_ADJUSTMENT_INTERVAL: Final[int] = 100  # Adjust difficulty every 100 blocks
DIFFICULTY_RETARGET_WINDOW: Final[int] = 2016  # Bitcoin-style difficulty window

# Mining
INITIAL_DIFFICULTY_MAINNET: Final[int] = 4
INITIAL_DIFFICULTY_TESTNET: Final[int] = 2
MAX_TEST_MINING_DIFFICULTY: Final[int] = 4  # Cap for fast mining mode
MAX_NONCE_VALUE: Final[int] = 10_000_000  # Maximum nonce value for mining

# Finality and checkpoints
CHECKPOINT_INTERVAL_BLOCKS: Final[int] = 1000  # Create checkpoint every 1000 blocks
MAX_CHECKPOINTS_STORED: Final[int] = 10  # Keep last 10 checkpoints
FINALITY_CONFIRMATION_BLOCKS: Final[int] = 6  # Blocks required for finality (Bitcoin-style)

# Block limits
MAX_BLOCK_SIZE_BYTES: Final[int] = 2_097_152  # 2 MB max block size
MAX_TRANSACTIONS_PER_BLOCK: Final[int] = 10000  # Maximum transactions per block

# =============================================================================
# FINANCIAL CONSTANTS
# =============================================================================

# Basis points (1 basis point = 0.01%)
BASIS_POINTS_DIVISOR: Final[int] = 10000  # Divide by 10000 to get percentage
BASIS_POINTS_PER_PERCENT: Final[int] = 100

# Percentage calculations
PERCENT_MULTIPLIER: Final[int] = 100  # For converting decimals to percentages
FULL_PERCENTAGE: Final[int] = 100  # Represents 100%

# Common fee percentages (in basis points for precision)
FEE_RATE_0_1_PERCENT: Final[float] = 0.001  # 0.1%
FEE_RATE_0_2_PERCENT: Final[float] = 0.002  # 0.2%
FEE_RATE_1_PERCENT: Final[float] = 0.01  # 1%

# Minimum amounts
MINIMUM_TRANSACTION_AMOUNT: Final[float] = 0.00000001  # 1 satoshi equivalent
MINIMUM_FEE_RATE: Final[float] = 0.0000001  # Minimum fee per byte

# Decimal precision
TOKEN_DECIMALS: Final[int] = 18  # Standard ERC20 decimals
WEI_PER_TOKEN: Final[int] = 10**18  # 1 token = 10^18 wei

# =============================================================================
# MEMPOOL LIMITS
# =============================================================================

MEMPOOL_MAX_SIZE_TRANSACTIONS: Final[int] = 10000  # Maximum pending transactions
MEMPOOL_MAX_SIZE_BYTES: Final[int] = 10_485_760  # 10 MB max mempool size
MEMPOOL_MAX_PER_SENDER: Final[int] = 100  # Max transactions per sender
MEMPOOL_INVALID_TX_THRESHOLD: Final[int] = 3  # Invalid tx count before ban
MEMPOOL_INVALID_BAN_SECONDS: Final[int] = 900  # 15 minutes ban
MEMPOOL_INVALID_WINDOW_SECONDS: Final[int] = 900  # 15 minutes tracking window

# =============================================================================
# P2P NETWORK CONSTANTS
# =============================================================================

# Connection limits
P2P_MAX_CONNECTIONS: Final[int] = 125  # Maximum peer connections
P2P_MAX_INBOUND_CONNECTIONS: Final[int] = 100
P2P_MAX_OUTBOUND_CONNECTIONS: Final[int] = 25
P2P_MIN_CONNECTIONS: Final[int] = 8  # Minimum desired connections

# Message limits
P2P_MAX_MESSAGE_SIZE_BYTES: Final[int] = 2_097_152  # 2 MB max message size
P2P_MAX_MESSAGES_PER_SECOND: Final[int] = 100  # Rate limit per peer

# Bandwidth limits
P2P_MAX_BANDWIDTH_IN_BYTES: Final[int] = 1_048_576  # 1 MB/s inbound
P2P_MAX_BANDWIDTH_OUT_BYTES: Final[int] = 1_048_576  # 1 MB/s outbound

# Timeouts
P2P_CONNECTION_TIMEOUT_SECONDS: Final[int] = 30  # Connection establishment timeout
P2P_IDLE_TIMEOUT_SECONDS: Final[int] = 900  # 15 minutes idle timeout
P2P_HANDSHAKE_TIMEOUT_SECONDS: Final[int] = 10  # Handshake timeout
P2P_NONCE_TTL_SECONDS: Final[int] = 300  # 5 minutes nonce validity

# Reputation system
P2P_INITIAL_REPUTATION: Final[float] = 100.0
P2P_MIN_REPUTATION: Final[float] = 0.0
P2P_MAX_REPUTATION: Final[float] = 200.0
P2P_BAN_DURATION_SECONDS: Final[int] = 86400  # 24 hours

# Diversity limits (prevent Sybil attacks)
P2P_MAX_PEERS_PER_PREFIX: Final[int] = 8
P2P_MAX_PEERS_PER_ASN: Final[int] = 16
P2P_MAX_PEERS_PER_COUNTRY: Final[int] = 48
P2P_MIN_UNIQUE_PREFIXES: Final[int] = 5
P2P_MIN_UNIQUE_ASNS: Final[int] = 5
P2P_MIN_UNIQUE_COUNTRIES: Final[int] = 5

# =============================================================================
# EVM / SMART CONTRACT CONSTANTS
# =============================================================================

# Gas limits
GAS_LIMIT_DEFAULT: Final[int] = 21000  # Standard transaction gas
GAS_LIMIT_CONTRACT_CREATION: Final[int] = 53000  # Contract deployment base gas
GAS_LIMIT_CONTRACT_CALL: Final[int] = 21000  # Contract call base gas
MAX_CONTRACT_GAS: Final[int] = 20_000_000  # Maximum gas per contract execution

# EVM opcode gas costs (common values)
GAS_COST_ZERO: Final[int] = 0
GAS_COST_BASE: Final[int] = 2
GAS_COST_VERY_LOW: Final[int] = 3
GAS_COST_LOW: Final[int] = 5
GAS_COST_MID: Final[int] = 8
GAS_COST_HIGH: Final[int] = 10

# Storage costs
GAS_COST_SSTORE_SET: Final[int] = 20000  # Set storage from zero
GAS_COST_SSTORE_RESET: Final[int] = 5000  # Reset storage to zero
GAS_COST_SLOAD: Final[int] = 200  # Load from storage

# Memory costs
GAS_COST_MEMORY_WORD: Final[int] = 3  # Per word of memory
MEMORY_WORD_SIZE_BYTES: Final[int] = 32  # EVM word size

# Call costs
GAS_COST_CALL: Final[int] = 700  # Base cost for CALL opcode
GAS_COST_CREATE: Final[int] = 32000  # Create contract

# Stack/Memory limits
EVM_STACK_MAX_DEPTH: Final[int] = 1024  # Maximum stack depth
EVM_MAX_CODE_SIZE: Final[int] = 24576  # 24 KB max contract size

# =============================================================================
# API RATE LIMITING
# =============================================================================

API_RATE_LIMIT_PER_MINUTE: Final[int] = 120  # Requests per minute
API_RATE_WINDOW_SECONDS: Final[int] = 60  # Rate limit window
API_MAX_REQUEST_SIZE_BYTES: Final[int] = 1_048_576  # 1 MB max request
API_REQUEST_TIMEOUT_SECONDS: Final[int] = 30  # Request timeout

# =============================================================================
# GOVERNANCE CONSTANTS
# =============================================================================

# Voting requirements
GOVERNANCE_MIN_VOTERS: Final[int] = 500  # Minimum voters for proposal
GOVERNANCE_MIN_REVIEWERS: Final[int] = 250  # Minimum code reviewers
GOVERNANCE_APPROVAL_THRESHOLD: Final[float] = 0.66  # 66% approval required
GOVERNANCE_QUORUM_PERCENTAGE: Final[int] = 50  # 50% quorum required

# Voting periods
GOVERNANCE_VOTING_PERIOD_BLOCKS: Final[int] = 10080  # 1 week voting period
GOVERNANCE_REVIEW_PERIOD_BLOCKS: Final[int] = 5040  # 3.5 days review period
GOVERNANCE_EXECUTION_DELAY_BLOCKS: Final[int] = 1440  # 1 day execution delay

# =============================================================================
# GAMIFICATION / EASTER EGGS
# =============================================================================

# Lucky blocks
LUCKY_BLOCK_PROBABILITY: Final[int] = 100  # 1 in 100 chance (1%)
LUCKY_BLOCK_NORMAL_REWARD: Final[float] = 60.0  # Normal lucky reward
LUCKY_BLOCK_BONUS_REWARD: Final[float] = 120.0  # Bonus lucky reward

# Treasure hunt
TREASURE_WALLET_COUNT: Final[int] = 100  # Number of treasure wallets
TREASURE_WALLET_BALANCE: Final[float] = 1000.0  # XAI per treasure wallet
TREASURE_TOTAL_VALUE: Final[float] = 100_000.0  # Total treasure pool

# Block ranges for clues
TREASURE_MIN_BLOCK: Final[int] = 100
TREASURE_MAX_BLOCK: Final[int] = 10000

# Airdrop amounts
AIRDROP_90_DAY_AMOUNT: Final[float] = 50_000.0
AIRDROP_90_DAY_RECIPIENTS: Final[int] = 100
AIRDROP_180_DAY_AMOUNT: Final[float] = 100_000.0
AIRDROP_180_DAY_RECIPIENTS: Final[int] = 500
AIRDROP_365_DAY_AMOUNT: Final[float] = 200_000.0
AIRDROP_365_DAY_RECIPIENTS: Final[int] = 1000

# =============================================================================
# SECURITY LIMITS
# =============================================================================

# Transaction validation
MAX_TRANSACTION_SIZE_BYTES: Final[int] = 102400  # 100 KB max transaction
MAX_SIGNATURE_SIZE_BYTES: Final[int] = 128  # Maximum signature size
MAX_INPUT_SCRIPT_SIZE: Final[int] = 1650  # Maximum input script size
MAX_OUTPUT_SCRIPT_SIZE: Final[int] = 10000  # Maximum output script size

# DOS protection
MAX_SCRIPT_ELEMENT_SIZE: Final[int] = 520  # Maximum script element
MAX_OPS_PER_SCRIPT: Final[int] = 201  # Maximum operations in script
MAX_PUBKEYS_PER_MULTISIG: Final[int] = 20  # Maximum keys in multisig
MAX_BLOCK_SIGOPS: Final[int] = 20000  # Maximum signature operations per block

# Replay protection
TRANSACTION_EXPIRY_BLOCKS: Final[int] = 720  # Transaction expires after 1 day
NONCE_WINDOW_SIZE: Final[int] = 1000  # Nonce tracking window

# =============================================================================
# WALLET / EXCHANGE LIMITS
# =============================================================================

# Withdrawal limits
MIN_WITHDRAWAL_USD: Final[float] = 10.0
MIN_WITHDRAWAL_XAI: Final[float] = 100.0
MIN_WITHDRAWAL_BTC: Final[float] = 0.001
MIN_WITHDRAWAL_ETH: Final[float] = 0.01
MIN_WITHDRAWAL_USDT: Final[float] = 10.0

# Transaction history
MAX_TRANSACTION_HISTORY_SIZE: Final[int] = 10000  # Keep last 10k transactions

# Faucet (testnet only)
FAUCET_AMOUNT_TESTNET: Final[float] = 100.0
FAUCET_COOLDOWN_SECONDS: Final[int] = 86400  # 1 day between faucet claims

# =============================================================================
# TRADE ORDER CONSTANTS
# =============================================================================

TRADE_ORDER_EXPIRY_SECONDS: Final[int] = 3600  # 1 hour order expiry
TRADE_FEE_PERCENT_MAINNET: Final[float] = 0.001  # 0.1% trading fee
TRADE_FEE_PERCENT_TESTNET: Final[float] = 0.002  # 0.2% trading fee

# =============================================================================
# ATOMIC SWAP CONSTANTS
# =============================================================================

ATOMIC_SWAP_UTXO_TX_SIZE_BYTES: Final[int] = 300  # Estimated UTXO tx size
ATOMIC_SWAP_ETH_GAS_LIMIT: Final[int] = 200_000  # Gas limit for ETH swaps
ATOMIC_SWAP_ETH_MAX_FEE_GWEI: Final[float] = 60.0  # Max gas price
ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI: Final[float] = 2.0  # Priority fee

# =============================================================================
# CACHE / STORAGE LIMITS
# =============================================================================

# Cache sizes
CACHE_MAX_ENTRIES: Final[int] = 1000  # Default cache size
CACHE_BLOCK_HEADERS: Final[int] = 2000  # Block header cache
CACHE_TRANSACTIONS: Final[int] = 10000  # Transaction cache
CACHE_UTXO_SET: Final[int] = 100000  # UTXO cache

# TTL values
CACHE_TTL_SHORT_SECONDS: Final[int] = 300  # 5 minutes
CACHE_TTL_MEDIUM_SECONDS: Final[int] = 3600  # 1 hour
CACHE_TTL_LONG_SECONDS: Final[int] = 86400  # 24 hours

# =============================================================================
# METRICS / MONITORING
# =============================================================================

METRICS_SERVER_DEFAULT_PORT: Final[int] = 8000  # Prometheus metrics port
METRICS_BUCKET_SMALL: Final[int] = 1000
METRICS_BUCKET_MEDIUM: Final[int] = 10000
METRICS_BUCKET_LARGE: Final[int] = 100000

# =============================================================================
# SYNC / REORG LIMITS
# =============================================================================

SYNC_CHUNK_SIZE_BLOCKS: Final[int] = 128  # Blocks to sync in one chunk
SYNC_PARALLEL_WORKERS: Final[int] = 4  # Parallel sync workers
SYNC_PAGE_LIMIT: Final[int] = 200  # Max blocks per page
SYNC_RETRY_ATTEMPTS: Final[int] = 2  # Retry failed syncs

MAX_REORG_DEPTH_BLOCKS: Final[int] = 100  # Maximum reorg depth allowed

# =============================================================================
# ERROR RECOVERY
# =============================================================================

ERROR_RETRY_MAX_ATTEMPTS: Final[int] = 3  # Maximum retry attempts
ERROR_RETRY_BACKOFF_SECONDS: Final[int] = 5  # Initial backoff delay
ERROR_CIRCUIT_BREAKER_THRESHOLD: Final[int] = 5  # Failures before circuit opens

# =============================================================================
# WEBHOOK / EXTERNAL API
# =============================================================================

WEBHOOK_TIMEOUT_SECONDS: Final[int] = 5  # Webhook request timeout
WEBHOOK_QUEUE_MAX_SIZE: Final[int] = 1000  # Max queued webhook events

# =============================================================================
# TESTING / DEBUG CONSTANTS
# =============================================================================

# These are only used in test environments
TEST_GENESIS_TIMESTAMP: Final[int] = 1704067200  # Fixed timestamp for testing
TEST_BLOCKS_FOR_STATS: Final[int] = 10000  # Number of blocks for statistics

# =============================================================================
# CRYPTOGRAPHIC CONSTANTS
# =============================================================================

# Key sizes
PRIVATE_KEY_SIZE_BYTES: Final[int] = 32  # 256-bit private key
PUBLIC_KEY_SIZE_BYTES: Final[int] = 64  # Uncompressed public key (no prefix)
PUBLIC_KEY_COMPRESSED_SIZE_BYTES: Final[int] = 33  # Compressed public key
HASH_SIZE_BYTES: Final[int] = 32  # SHA-256 hash size

# PBKDF2 parameters
PBKDF2_ITERATIONS: Final[int] = 100000  # Key derivation iterations
PBKDF2_SALT_SIZE_BYTES: Final[int] = 32  # Salt size

# AES encryption
AES_KEY_SIZE_BYTES: Final[int] = 32  # AES-256
AES_BLOCK_SIZE_BYTES: Final[int] = 16  # AES block size
AES_IV_SIZE_BYTES: Final[int] = 16  # Initialization vector size

# =============================================================================
# PROOF OF WORK / MINING
# =============================================================================

POW_DIFFICULTY_BITS: Final[int] = 18  # P2P PoW difficulty
POW_MAX_ITERATIONS: Final[int] = 250_000  # Max PoW attempts
POW_REUSE_WINDOW_SECONDS: Final[int] = 600  # PoW solution reuse window

# =============================================================================
# DATA SIZES (in bytes)
# =============================================================================

SIZE_1_KB: Final[int] = 1024
SIZE_10_KB: Final[int] = 10240
SIZE_100_KB: Final[int] = 102400
SIZE_1_MB: Final[int] = 1_048_576
SIZE_2_MB: Final[int] = 2_097_152
SIZE_10_MB: Final[int] = 10_485_760
SIZE_100_MB: Final[int] = 104_857_600

# =============================================================================
# VALIDATOR / SLASHING CONSTANTS
# =============================================================================

VALIDATOR_MIN_STAKE: Final[float] = 1000.0  # Minimum stake to be validator
VALIDATOR_ROTATION_PERIOD_BLOCKS: Final[int] = 720  # Rotate validators daily
SLASHING_PENALTY_DOUBLE_SIGN: Final[float] = 0.05  # 5% slash for double signing
SLASHING_PENALTY_DOWNTIME: Final[float] = 0.01  # 1% slash for downtime

# =============================================================================
# NETWORK IDs
# =============================================================================

NETWORK_ID_MAINNET: Final[int] = 0x5841  # 'XA' in hex
NETWORK_ID_TESTNET: Final[int] = 0xABCD  # Testnet identifier

# =============================================================================
# GENESIS TIMESTAMP
# =============================================================================

GENESIS_TIMESTAMP: Final[float] = 1704067200.0  # 2024-01-01 00:00:00 UTC

# =============================================================================
# EXPORT ALL CONSTANTS
# =============================================================================

__all__ = [
    # Time constants
    'SECONDS_PER_MINUTE', 'SECONDS_PER_HOUR', 'SECONDS_PER_DAY', 'SECONDS_PER_WEEK',
    'SECONDS_PER_30_DAYS', 'SECONDS_PER_YEAR', 'SECONDS_2_MINUTES', 'SECONDS_5_MINUTES',
    'SECONDS_10_MINUTES', 'SECONDS_15_MINUTES', 'SECONDS_30_MINUTES', 'SECONDS_2_HOURS',

    # Blockchain consensus
    'BLOCK_TIME_TARGET_SECONDS', 'BLOCKS_PER_HOUR', 'BLOCKS_PER_DAY', 'BLOCKS_PER_WEEK',
    'BLOCKS_PER_YEAR', 'MAX_SUPPLY', 'INITIAL_BLOCK_REWARD', 'HALVING_INTERVAL_BLOCKS',
    'DIFFICULTY_ADJUSTMENT_INTERVAL', 'DIFFICULTY_RETARGET_WINDOW', 'INITIAL_DIFFICULTY_MAINNET',
    'INITIAL_DIFFICULTY_TESTNET', 'MAX_TEST_MINING_DIFFICULTY', 'MAX_NONCE_VALUE',
    'CHECKPOINT_INTERVAL_BLOCKS', 'MAX_CHECKPOINTS_STORED', 'FINALITY_CONFIRMATION_BLOCKS',
    'MAX_BLOCK_SIZE_BYTES', 'MAX_TRANSACTIONS_PER_BLOCK',

    # Financial
    'BASIS_POINTS_DIVISOR', 'BASIS_POINTS_PER_PERCENT', 'PERCENT_MULTIPLIER',
    'FULL_PERCENTAGE', 'FEE_RATE_0_1_PERCENT', 'FEE_RATE_0_2_PERCENT',
    'FEE_RATE_1_PERCENT', 'MINIMUM_TRANSACTION_AMOUNT', 'MINIMUM_FEE_RATE',
    'TOKEN_DECIMALS', 'WEI_PER_TOKEN',

    # Mempool
    'MEMPOOL_MAX_SIZE_TRANSACTIONS', 'MEMPOOL_MAX_SIZE_BYTES', 'MEMPOOL_MAX_PER_SENDER',
    'MEMPOOL_INVALID_TX_THRESHOLD', 'MEMPOOL_INVALID_BAN_SECONDS', 'MEMPOOL_INVALID_WINDOW_SECONDS',

    # P2P Network
    'P2P_MAX_CONNECTIONS', 'P2P_MAX_INBOUND_CONNECTIONS', 'P2P_MAX_OUTBOUND_CONNECTIONS',
    'P2P_MIN_CONNECTIONS', 'P2P_MAX_MESSAGE_SIZE_BYTES', 'P2P_MAX_MESSAGES_PER_SECOND',
    'P2P_MAX_BANDWIDTH_IN_BYTES', 'P2P_MAX_BANDWIDTH_OUT_BYTES', 'P2P_CONNECTION_TIMEOUT_SECONDS',
    'P2P_IDLE_TIMEOUT_SECONDS', 'P2P_HANDSHAKE_TIMEOUT_SECONDS', 'P2P_NONCE_TTL_SECONDS',
    'P2P_INITIAL_REPUTATION', 'P2P_MIN_REPUTATION', 'P2P_MAX_REPUTATION',
    'P2P_BAN_DURATION_SECONDS', 'P2P_MAX_PEERS_PER_PREFIX', 'P2P_MAX_PEERS_PER_ASN',
    'P2P_MAX_PEERS_PER_COUNTRY', 'P2P_MIN_UNIQUE_PREFIXES', 'P2P_MIN_UNIQUE_ASNS',
    'P2P_MIN_UNIQUE_COUNTRIES',

    # EVM/Smart contracts
    'GAS_LIMIT_DEFAULT', 'GAS_LIMIT_CONTRACT_CREATION', 'GAS_LIMIT_CONTRACT_CALL',
    'MAX_CONTRACT_GAS', 'GAS_COST_ZERO', 'GAS_COST_BASE', 'GAS_COST_VERY_LOW',
    'GAS_COST_LOW', 'GAS_COST_MID', 'GAS_COST_HIGH', 'GAS_COST_SSTORE_SET',
    'GAS_COST_SSTORE_RESET', 'GAS_COST_SLOAD', 'GAS_COST_MEMORY_WORD',
    'MEMORY_WORD_SIZE_BYTES', 'GAS_COST_CALL', 'GAS_COST_CREATE',
    'EVM_STACK_MAX_DEPTH', 'EVM_MAX_CODE_SIZE',

    # API rate limiting
    'API_RATE_LIMIT_PER_MINUTE', 'API_RATE_WINDOW_SECONDS', 'API_MAX_REQUEST_SIZE_BYTES',
    'API_REQUEST_TIMEOUT_SECONDS',

    # Governance
    'GOVERNANCE_MIN_VOTERS', 'GOVERNANCE_MIN_REVIEWERS', 'GOVERNANCE_APPROVAL_THRESHOLD',
    'GOVERNANCE_QUORUM_PERCENTAGE', 'GOVERNANCE_VOTING_PERIOD_BLOCKS',
    'GOVERNANCE_REVIEW_PERIOD_BLOCKS', 'GOVERNANCE_EXECUTION_DELAY_BLOCKS',

    # Gamification
    'LUCKY_BLOCK_PROBABILITY', 'LUCKY_BLOCK_NORMAL_REWARD', 'LUCKY_BLOCK_BONUS_REWARD',
    'TREASURE_WALLET_COUNT', 'TREASURE_WALLET_BALANCE', 'TREASURE_TOTAL_VALUE',
    'TREASURE_MIN_BLOCK', 'TREASURE_MAX_BLOCK', 'AIRDROP_90_DAY_AMOUNT',
    'AIRDROP_90_DAY_RECIPIENTS', 'AIRDROP_180_DAY_AMOUNT', 'AIRDROP_180_DAY_RECIPIENTS',
    'AIRDROP_365_DAY_AMOUNT', 'AIRDROP_365_DAY_RECIPIENTS',

    # Security limits
    'MAX_TRANSACTION_SIZE_BYTES', 'MAX_SIGNATURE_SIZE_BYTES', 'MAX_INPUT_SCRIPT_SIZE',
    'MAX_OUTPUT_SCRIPT_SIZE', 'MAX_SCRIPT_ELEMENT_SIZE', 'MAX_OPS_PER_SCRIPT',
    'MAX_PUBKEYS_PER_MULTISIG', 'MAX_BLOCK_SIGOPS', 'TRANSACTION_EXPIRY_BLOCKS',
    'NONCE_WINDOW_SIZE',

    # Wallet/Exchange
    'MIN_WITHDRAWAL_USD', 'MIN_WITHDRAWAL_XAI', 'MIN_WITHDRAWAL_BTC',
    'MIN_WITHDRAWAL_ETH', 'MIN_WITHDRAWAL_USDT', 'MAX_TRANSACTION_HISTORY_SIZE',
    'FAUCET_AMOUNT_TESTNET', 'FAUCET_COOLDOWN_SECONDS',

    # Trade orders
    'TRADE_ORDER_EXPIRY_SECONDS', 'TRADE_FEE_PERCENT_MAINNET', 'TRADE_FEE_PERCENT_TESTNET',

    # Atomic swaps
    'ATOMIC_SWAP_UTXO_TX_SIZE_BYTES', 'ATOMIC_SWAP_ETH_GAS_LIMIT',
    'ATOMIC_SWAP_ETH_MAX_FEE_GWEI', 'ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI',

    # Cache/Storage
    'CACHE_MAX_ENTRIES', 'CACHE_BLOCK_HEADERS', 'CACHE_TRANSACTIONS',
    'CACHE_UTXO_SET', 'CACHE_TTL_SHORT_SECONDS', 'CACHE_TTL_MEDIUM_SECONDS',
    'CACHE_TTL_LONG_SECONDS',

    # Metrics
    'METRICS_SERVER_DEFAULT_PORT', 'METRICS_BUCKET_SMALL', 'METRICS_BUCKET_MEDIUM',
    'METRICS_BUCKET_LARGE',

    # Sync/Reorg
    'SYNC_CHUNK_SIZE_BLOCKS', 'SYNC_PARALLEL_WORKERS', 'SYNC_PAGE_LIMIT',
    'SYNC_RETRY_ATTEMPTS', 'MAX_REORG_DEPTH_BLOCKS',

    # Error recovery
    'ERROR_RETRY_MAX_ATTEMPTS', 'ERROR_RETRY_BACKOFF_SECONDS',
    'ERROR_CIRCUIT_BREAKER_THRESHOLD',

    # Webhooks
    'WEBHOOK_TIMEOUT_SECONDS', 'WEBHOOK_QUEUE_MAX_SIZE',

    # Testing
    'TEST_GENESIS_TIMESTAMP', 'TEST_BLOCKS_FOR_STATS',

    # Cryptography
    'PRIVATE_KEY_SIZE_BYTES', 'PUBLIC_KEY_SIZE_BYTES', 'PUBLIC_KEY_COMPRESSED_SIZE_BYTES',
    'HASH_SIZE_BYTES', 'PBKDF2_ITERATIONS', 'PBKDF2_SALT_SIZE_BYTES',
    'AES_KEY_SIZE_BYTES', 'AES_BLOCK_SIZE_BYTES', 'AES_IV_SIZE_BYTES',

    # PoW/Mining
    'POW_DIFFICULTY_BITS', 'POW_MAX_ITERATIONS', 'POW_REUSE_WINDOW_SECONDS',

    # Data sizes
    'SIZE_1_KB', 'SIZE_10_KB', 'SIZE_100_KB', 'SIZE_1_MB', 'SIZE_2_MB',
    'SIZE_10_MB', 'SIZE_100_MB',

    # Validators/Slashing
    'VALIDATOR_MIN_STAKE', 'VALIDATOR_ROTATION_PERIOD_BLOCKS',
    'SLASHING_PENALTY_DOUBLE_SIGN', 'SLASHING_PENALTY_DOWNTIME',

    # Network IDs
    'NETWORK_ID_MAINNET', 'NETWORK_ID_TESTNET',

    # Genesis
    'GENESIS_TIMESTAMP',
]
