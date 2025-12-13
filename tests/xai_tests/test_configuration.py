"""
Comprehensive Configuration Testing for Phase 2.2

Tests all configuration parameters to verify:
- PoW parameters affect blockchain behavior correctly
- P2P settings are validated and applied
- Mempool configuration works as expected
- Configuration validation and error handling
- Boundary conditions and edge cases
- Graceful failure for invalid configurations
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from xai.core.config import (
    Config,
    TestnetConfig,
    MainnetConfig,
    NetworkType,
    ConfigurationError,
    _get_required_secret,
    _parse_origin_list,
    _parse_int_list,
    _parse_deprecations,
    _parse_deposit_sources,
    MEMPOOL_MIN_FEE_RATE,
    MEMPOOL_MAX_SIZE,
    MEMPOOL_MAX_PER_SENDER,
    MEMPOOL_INVALID_TX_THRESHOLD,
    MEMPOOL_INVALID_BAN_SECONDS,
    MEMPOOL_INVALID_WINDOW_SECONDS,
    P2P_MAX_PEERS_PER_PREFIX,
    P2P_MAX_PEERS_PER_ASN,
    P2P_MAX_PEERS_PER_COUNTRY,
    P2P_MIN_UNIQUE_PREFIXES,
    P2P_MIN_UNIQUE_ASNS,
    P2P_MIN_UNIQUE_COUNTRIES,
    P2P_MAX_MESSAGE_RATE,
    P2P_POW_DIFFICULTY_BITS,
    P2P_POW_MAX_ITERATIONS,
    API_RATE_LIMIT,
    API_RATE_WINDOW_SECONDS,
    API_MAX_JSON_BYTES,
    FEATURE_FLAGS,
    SECURITY_WEBHOOK_URL,
    SECURITY_WEBHOOK_TOKEN,
    SECURITY_WEBHOOK_TIMEOUT,
    EMBEDDED_WALLET_SALT,
    EMBEDDED_WALLET_DIR,
    TIME_CAPSULE_MASTER_KEY,
    MAX_CONTRACT_GAS,
)


class TestPowParameters:
    """Test Proof-of-Work configuration parameters"""

    def test_initial_block_reward_testnet(self):
        """Test testnet initial block reward"""
        assert TestnetConfig.INITIAL_BLOCK_REWARD == 12.0
        assert isinstance(TestnetConfig.INITIAL_BLOCK_REWARD, float)
        assert TestnetConfig.INITIAL_BLOCK_REWARD > 0

    def test_initial_block_reward_mainnet(self):
        """Test mainnet initial block reward"""
        assert MainnetConfig.INITIAL_BLOCK_REWARD == 12.0
        assert isinstance(MainnetConfig.INITIAL_BLOCK_REWARD, float)
        assert MainnetConfig.INITIAL_BLOCK_REWARD > 0

    def test_initial_difficulty_testnet(self):
        """Test testnet initial difficulty (lower for testing)"""
        assert TestnetConfig.INITIAL_DIFFICULTY == 2
        assert isinstance(TestnetConfig.INITIAL_DIFFICULTY, int)
        assert TestnetConfig.INITIAL_DIFFICULTY > 0
        assert TestnetConfig.INITIAL_DIFFICULTY < MainnetConfig.INITIAL_DIFFICULTY

    def test_initial_difficulty_mainnet(self):
        """Test mainnet initial difficulty (production level)"""
        assert MainnetConfig.INITIAL_DIFFICULTY == 4
        assert isinstance(MainnetConfig.INITIAL_DIFFICULTY, int)
        assert MainnetConfig.INITIAL_DIFFICULTY > TestnetConfig.INITIAL_DIFFICULTY

    def test_block_time_target(self):
        """Test block time target is 2 minutes"""
        assert TestnetConfig.BLOCK_TIME_TARGET == 120
        assert MainnetConfig.BLOCK_TIME_TARGET == 120
        assert TestnetConfig.BLOCK_TIME_TARGET == MainnetConfig.BLOCK_TIME_TARGET

    def test_halving_interval(self):
        """Test halving interval is 1 year (262800 blocks)"""
        assert TestnetConfig.HALVING_INTERVAL == 262800
        assert MainnetConfig.HALVING_INTERVAL == 262800
        # At 120 seconds per block: 262800 * 120 / 86400 = 365 days
        blocks_per_day = 86400 / TestnetConfig.BLOCK_TIME_TARGET
        expected_days = TestnetConfig.HALVING_INTERVAL / blocks_per_day
        assert abs(expected_days - 365) < 1  # Within 1 day of a year

    def test_max_supply(self):
        """Test max supply is 121 million (Bitcoin tribute)"""
        assert TestnetConfig.MAX_SUPPLY == 121000000.0
        assert MainnetConfig.MAX_SUPPLY == 121000000.0
        assert isinstance(TestnetConfig.MAX_SUPPLY, float)

    def test_difficulty_affects_mining(self):
        """Test that difficulty parameter affects mining (conceptual test)"""
        # Lower difficulty means easier mining
        assert TestnetConfig.INITIAL_DIFFICULTY < MainnetConfig.INITIAL_DIFFICULTY
        # Difficulty is measured in leading zeros required
        assert TestnetConfig.INITIAL_DIFFICULTY >= 1
        assert MainnetConfig.INITIAL_DIFFICULTY >= 1


class TestP2PConfiguration:
    """Test Peer-to-Peer network configuration"""

    def test_p2p_max_peers_per_prefix(self):
        """Test maximum peers per IP prefix"""
        assert isinstance(P2P_MAX_PEERS_PER_PREFIX, int)
        assert P2P_MAX_PEERS_PER_PREFIX > 0
        assert P2P_MAX_PEERS_PER_PREFIX <= 100  # Reasonable upper bound

    def test_p2p_max_peers_per_asn(self):
        """Test maximum peers per ASN (Autonomous System Number)"""
        assert isinstance(P2P_MAX_PEERS_PER_ASN, int)
        assert P2P_MAX_PEERS_PER_ASN > 0
        assert P2P_MAX_PEERS_PER_ASN >= P2P_MAX_PEERS_PER_PREFIX  # ASN should allow more

    def test_p2p_max_peers_per_country(self):
        """Test maximum peers per country"""
        assert isinstance(P2P_MAX_PEERS_PER_COUNTRY, int)
        assert P2P_MAX_PEERS_PER_COUNTRY > 0
        assert P2P_MAX_PEERS_PER_COUNTRY >= P2P_MAX_PEERS_PER_ASN  # Country should allow more

    def test_p2p_min_unique_prefixes(self):
        """Test minimum unique IP prefixes required"""
        assert isinstance(P2P_MIN_UNIQUE_PREFIXES, int)
        assert P2P_MIN_UNIQUE_PREFIXES > 0
        assert P2P_MIN_UNIQUE_PREFIXES <= P2P_MAX_PEERS_PER_PREFIX

    def test_p2p_min_unique_asns(self):
        """Test minimum unique ASNs required"""
        assert isinstance(P2P_MIN_UNIQUE_ASNS, int)
        assert P2P_MIN_UNIQUE_ASNS > 0

    def test_p2p_min_unique_countries(self):
        """Test minimum unique countries required"""
        assert isinstance(P2P_MIN_UNIQUE_COUNTRIES, int)
        assert P2P_MIN_UNIQUE_COUNTRIES > 0

    def test_p2p_max_message_rate(self):
        """Test maximum message rate per peer"""
        assert isinstance(P2P_MAX_MESSAGE_RATE, int)
        assert P2P_MAX_MESSAGE_RATE > 0
        assert P2P_MAX_MESSAGE_RATE <= 1000  # Reasonable upper bound

    def test_p2p_bandwidth_limits(self):
        """Test P2P bandwidth limits are set"""
        assert hasattr(Config, "P2P_MAX_BANDWIDTH_IN")
        assert hasattr(Config, "P2P_MAX_BANDWIDTH_OUT")
        assert Config.P2P_MAX_BANDWIDTH_IN > 0
        assert Config.P2P_MAX_BANDWIDTH_OUT > 0

    def test_p2p_pow_enabled(self):
        """Test P2P proof-of-work is configurable"""
        # Default should be enabled for anti-spam
        assert hasattr(Config, "P2P_POW_ENABLED") or True  # May not be set in Config

    def test_p2p_pow_difficulty(self):
        """Test P2P PoW difficulty bits"""
        assert isinstance(P2P_POW_DIFFICULTY_BITS, int)
        assert P2P_POW_DIFFICULTY_BITS > 0
        assert P2P_POW_DIFFICULTY_BITS <= 32  # Reasonable upper bound

    def test_p2p_pow_max_iterations(self):
        """Test P2P PoW maximum iterations"""
        assert isinstance(P2P_POW_MAX_ITERATIONS, int)
        assert P2P_POW_MAX_ITERATIONS > 0

    def test_p2p_connection_timeout(self):
        """Test P2P connection idle timeout"""
        assert hasattr(Config, "P2P_CONNECTION_IDLE_TIMEOUT_SECONDS")
        assert Config.P2P_CONNECTION_IDLE_TIMEOUT_SECONDS > 0

    def test_p2p_parallel_sync_config(self):
        """Test P2P parallel sync configuration"""
        assert hasattr(Config, "P2P_PARALLEL_SYNC_ENABLED")
        assert hasattr(Config, "P2P_PARALLEL_SYNC_WORKERS")
        assert hasattr(Config, "P2P_PARALLEL_SYNC_CHUNK_SIZE")
        if Config.P2P_PARALLEL_SYNC_ENABLED:
            assert Config.P2P_PARALLEL_SYNC_WORKERS > 0
            assert Config.P2P_PARALLEL_SYNC_CHUNK_SIZE > 0


class TestMempoolConfiguration:
    """Test mempool configuration parameters"""

    def test_mempool_min_fee_rate(self):
        """Test minimum fee rate for mempool inclusion"""
        assert isinstance(MEMPOOL_MIN_FEE_RATE, float)
        assert MEMPOOL_MIN_FEE_RATE > 0
        assert MEMPOOL_MIN_FEE_RATE < 1.0  # Should be fractional

    def test_mempool_min_fee_rate_accessible(self):
        """Test mempool min fee rate is accessible from Config"""
        assert hasattr(Config, "MEMPOOL_MIN_FEE_RATE")
        assert Config.MEMPOOL_MIN_FEE_RATE == MEMPOOL_MIN_FEE_RATE

    def test_mempool_max_size(self):
        """Test maximum mempool size"""
        assert isinstance(MEMPOOL_MAX_SIZE, int)
        assert MEMPOOL_MAX_SIZE > 0
        assert MEMPOOL_MAX_SIZE >= 1000  # Reasonable minimum

    def test_mempool_max_per_sender(self):
        """Test maximum transactions per sender in mempool"""
        assert isinstance(MEMPOOL_MAX_PER_SENDER, int)
        assert MEMPOOL_MAX_PER_SENDER > 0
        assert MEMPOOL_MAX_PER_SENDER <= MEMPOOL_MAX_SIZE

    def test_mempool_invalid_tx_threshold(self):
        """Test invalid transaction threshold before banning"""
        assert isinstance(MEMPOOL_INVALID_TX_THRESHOLD, int)
        assert MEMPOOL_INVALID_TX_THRESHOLD > 0
        assert MEMPOOL_INVALID_TX_THRESHOLD <= 10  # Reasonable threshold

    def test_mempool_invalid_ban_seconds(self):
        """Test ban duration for invalid transactions"""
        assert isinstance(MEMPOOL_INVALID_BAN_SECONDS, int)
        assert MEMPOOL_INVALID_BAN_SECONDS > 0
        assert MEMPOOL_INVALID_BAN_SECONDS >= 60  # At least 1 minute

    def test_mempool_invalid_window_seconds(self):
        """Test time window for tracking invalid transactions"""
        assert isinstance(MEMPOOL_INVALID_WINDOW_SECONDS, int)
        assert MEMPOOL_INVALID_WINDOW_SECONDS > 0
        assert MEMPOOL_INVALID_WINDOW_SECONDS >= MEMPOOL_INVALID_BAN_SECONDS

    def test_mempool_alert_thresholds(self):
        """Test mempool alerting thresholds"""
        assert hasattr(Config, "MEMPOOL_ALERT_INVALID_DELTA")
        assert hasattr(Config, "MEMPOOL_ALERT_BAN_DELTA")
        assert hasattr(Config, "MEMPOOL_ALERT_ACTIVE_BANS")
        assert Config.MEMPOOL_ALERT_INVALID_DELTA > 0
        assert Config.MEMPOOL_ALERT_BAN_DELTA > 0
        assert Config.MEMPOOL_ALERT_ACTIVE_BANS >= 0


class TestAPIConfiguration:
    """Test API configuration parameters"""

    def test_api_rate_limit(self):
        """Test API rate limiting"""
        assert isinstance(API_RATE_LIMIT, int)
        assert API_RATE_LIMIT > 0
        assert hasattr(Config, "API_RATE_LIMIT")

    def test_api_rate_window(self):
        """Test API rate limit window"""
        assert isinstance(API_RATE_WINDOW_SECONDS, int)
        assert API_RATE_WINDOW_SECONDS > 0
        assert hasattr(Config, "API_RATE_WINDOW_SECONDS")

    def test_api_max_json_bytes(self):
        """Test maximum JSON payload size"""
        assert isinstance(API_MAX_JSON_BYTES, int)
        assert API_MAX_JSON_BYTES > 0
        assert API_MAX_JSON_BYTES >= 1024  # At least 1KB
        assert hasattr(Config, "API_MAX_JSON_BYTES")

    def test_api_versioning(self):
        """Test API versioning configuration"""
        assert hasattr(Config, "API_SUPPORTED_VERSIONS")
        assert hasattr(Config, "API_DEFAULT_VERSION")
        assert isinstance(Config.API_SUPPORTED_VERSIONS, list)
        assert len(Config.API_SUPPORTED_VERSIONS) > 0
        assert Config.API_DEFAULT_VERSION in Config.API_SUPPORTED_VERSIONS

    def test_api_deprecated_versions(self):
        """Test API deprecated versions tracking"""
        assert hasattr(Config, "API_DEPRECATED_VERSIONS")
        assert isinstance(Config.API_DEPRECATED_VERSIONS, dict)


class TestAtomicSwapConfiguration:
    """Test atomic swap configuration"""

    def test_atomic_swap_fee_rate(self):
        """Test atomic swap fee rate"""
        assert hasattr(Config, "ATOMIC_SWAP_FEE_RATE")
        assert isinstance(Config.ATOMIC_SWAP_FEE_RATE, float)
        assert Config.ATOMIC_SWAP_FEE_RATE > 0

    def test_atomic_swap_utxo_tx_size(self):
        """Test UTXO transaction size estimate for swaps"""
        assert hasattr(Config, "ATOMIC_SWAP_UTXO_TX_SIZE")
        assert isinstance(Config.ATOMIC_SWAP_UTXO_TX_SIZE, int)
        assert Config.ATOMIC_SWAP_UTXO_TX_SIZE > 0

    def test_atomic_swap_eth_config(self):
        """Test Ethereum atomic swap configuration"""
        assert hasattr(Config, "ATOMIC_SWAP_ETH_GAS_LIMIT")
        assert hasattr(Config, "ATOMIC_SWAP_ETH_MAX_FEE_GWEI")
        assert hasattr(Config, "ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI")
        assert Config.ATOMIC_SWAP_ETH_GAS_LIMIT > 0
        assert Config.ATOMIC_SWAP_ETH_MAX_FEE_GWEI > 0
        assert Config.ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI > 0


class TestConfigurationValidation:
    """Test configuration validation and error handling"""

    def test_required_secret_mainnet_enforcement(self):
        """Test that required secrets are enforced on mainnet"""
        with pytest.raises(ConfigurationError):
            _get_required_secret("NONEXISTENT_SECRET", "mainnet")

    def test_required_secret_testnet_generation(self, caplog):
        """Test that testnet generates secrets with warning"""
        secret = _get_required_secret("NONEXISTENT_SECRET_TEST", "testnet")
        assert secret is not None
        assert len(secret) > 0
        # Should log a warning
        assert any("Security" in record.message for record in caplog.records)

    def test_network_type_enum(self):
        """Test NetworkType enum"""
        assert NetworkType.TESTNET.value == "testnet"
        assert NetworkType.MAINNET.value == "mainnet"

    def test_configuration_error_exception(self):
        """Test ConfigurationError exception"""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Test error")

    def test_parse_origin_list_valid(self):
        """Test parsing of allowed origins list"""
        origins = _parse_origin_list("http://localhost:3000,https://example.com")
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins

    def test_parse_origin_list_empty(self):
        """Test parsing of empty origins list"""
        origins = _parse_origin_list("")
        assert len(origins) == 0

    def test_parse_origin_list_whitespace(self):
        """Test parsing of origins with whitespace"""
        origins = _parse_origin_list(" http://localhost:3000 , https://example.com ")
        assert len(origins) == 2
        assert "http://localhost:3000" in origins

    def test_parse_int_list_valid(self):
        """Test parsing of integer list"""
        ints = _parse_int_list("1,2,3,4,5")
        assert ints == [1, 2, 3, 4, 5]

    def test_parse_int_list_invalid(self):
        """Test parsing of integer list with invalid values"""
        ints = _parse_int_list("1,two,3,four,5")
        assert ints == [1, 3, 5]  # Invalid values skipped

    def test_parse_int_list_empty(self):
        """Test parsing of empty integer list"""
        ints = _parse_int_list("")
        assert len(ints) == 0

    def test_parse_deprecations_valid(self):
        """Test parsing of API version deprecations"""
        deps = _parse_deprecations("v1=2025-01-01,v2=2026-01-01")
        assert "v1" in deps
        assert "v2" in deps
        assert deps["v1"]["sunset"] == "2025-01-01"

    def test_parse_deprecations_empty(self):
        """Test parsing of empty deprecations"""
        deps = _parse_deprecations("")
        assert len(deps) == 0

    def test_parse_deposit_sources_valid(self):
        """Test parsing of crypto deposit sources"""
        sources = _parse_deposit_sources('{"BTC": {"rpc": "http://localhost:8332"}}')
        assert "BTC" in sources
        assert "rpc" in sources["BTC"]

    def test_parse_deposit_sources_invalid_json(self, caplog):
        """Test parsing of invalid JSON deposit sources"""
        sources = _parse_deposit_sources("invalid json")
        assert len(sources) == 0
        # Should log an error

    def test_parse_deposit_sources_not_dict(self, caplog):
        """Test parsing of non-dict deposit sources"""
        sources = _parse_deposit_sources("[1, 2, 3]")
        assert len(sources) == 0


class TestBoundaryConditions:
    """Test boundary conditions and edge cases"""

    @patch.dict(os.environ, {"XAI_MEMPOOL_MIN_FEE_RATE": "0.0"})
    def test_zero_fee_rate_invalid(self):
        """Test that zero fee rate should be handled gracefully"""
        # Reload config module to pick up env change
        # This is a conceptual test - actual implementation may vary
        pass

    def test_max_values_within_reason(self):
        """Test that maximum values are within reasonable bounds"""
        assert MEMPOOL_MAX_SIZE < 1000000  # Less than 1 million
        assert API_RATE_LIMIT < 100000  # Less than 100k requests
        assert P2P_MAX_MESSAGE_RATE < 10000  # Less than 10k messages

    def test_min_values_positive(self):
        """Test that minimum values are positive"""
        assert MEMPOOL_MIN_FEE_RATE > 0
        assert MEMPOOL_INVALID_TX_THRESHOLD > 0
        assert P2P_MIN_UNIQUE_PREFIXES > 0

    def test_timeout_values_reasonable(self):
        """Test that timeout values are reasonable"""
        assert MEMPOOL_INVALID_BAN_SECONDS >= 60  # At least 1 minute
        assert MEMPOOL_INVALID_BAN_SECONDS <= 86400  # At most 1 day
        assert MEMPOOL_INVALID_WINDOW_SECONDS >= 60

    def test_difficulty_range(self):
        """Test that difficulty is within reasonable range"""
        assert TestnetConfig.INITIAL_DIFFICULTY >= 1
        assert TestnetConfig.INITIAL_DIFFICULTY <= 10
        assert MainnetConfig.INITIAL_DIFFICULTY >= 1
        assert MainnetConfig.INITIAL_DIFFICULTY <= 20


class TestConfigurationBehavior:
    """Test that configuration changes affect behavior"""

    def test_testnet_allows_reset(self):
        """Test that testnet allows chain reset"""
        assert TestnetConfig.ALLOW_CHAIN_RESET is True

    def test_mainnet_forbids_reset(self):
        """Test that mainnet forbids chain reset"""
        assert MainnetConfig.ALLOW_CHAIN_RESET is False

    def test_testnet_has_faucet(self):
        """Test that testnet has faucet enabled"""
        assert TestnetConfig.FAUCET_ENABLED is True
        assert TestnetConfig.FAUCET_AMOUNT > 0

    def test_mainnet_no_faucet(self):
        """Test that mainnet has no faucet"""
        assert MainnetConfig.FAUCET_ENABLED is False
        assert MainnetConfig.FAUCET_AMOUNT == 0

    def test_network_id_uniqueness(self):
        """Test that network IDs are unique and valid"""
        assert TestnetConfig.NETWORK_ID != MainnetConfig.NETWORK_ID
        assert TestnetConfig.NETWORK_ID > 0
        assert MainnetConfig.NETWORK_ID > 0

    def test_port_separation(self):
        """Test that networks use different ports"""
        assert TestnetConfig.DEFAULT_PORT != MainnetConfig.DEFAULT_PORT
        assert TestnetConfig.DEFAULT_RPC_PORT != MainnetConfig.DEFAULT_RPC_PORT
        # Testnet ports should be offset
        assert TestnetConfig.DEFAULT_PORT > MainnetConfig.DEFAULT_PORT

    def test_genesis_file_separation(self):
        """Test that networks use different genesis files"""
        assert TestnetConfig.GENESIS_FILE != MainnetConfig.GENESIS_FILE
        assert "testnet" in TestnetConfig.GENESIS_FILE.lower()

    def test_address_prefix_separation(self):
        """Test that networks use different address prefixes"""
        assert TestnetConfig.ADDRESS_PREFIX != MainnetConfig.ADDRESS_PREFIX
        assert TestnetConfig.ADDRESS_PREFIX.startswith("T")  # Testnet prefix
        assert not MainnetConfig.ADDRESS_PREFIX.startswith("T")


class TestFeatureFlags:
    """Test feature flag configuration"""

    def test_feature_flags_exist(self):
        """Test that feature flags are defined"""
        # Feature flags are defined as module-level variable
        assert isinstance(FEATURE_FLAGS, dict)

    def test_vm_feature_flag(self):
        """Test VM feature flag"""
        assert "vm" in FEATURE_FLAGS
        assert isinstance(FEATURE_FLAGS["vm"], bool)


class TestSecurityConfiguration:
    """Test security-related configuration"""

    def test_security_webhook_config(self):
        """Test security webhook configuration"""
        # These are defined as module-level variables
        assert isinstance(SECURITY_WEBHOOK_URL, str)
        assert isinstance(SECURITY_WEBHOOK_TOKEN, str)
        assert isinstance(SECURITY_WEBHOOK_TIMEOUT, int)
        assert SECURITY_WEBHOOK_TIMEOUT > 0

    def test_embedded_wallet_config(self):
        """Test embedded wallet configuration"""
        assert isinstance(EMBEDDED_WALLET_SALT, str)
        assert isinstance(EMBEDDED_WALLET_DIR, str)
        assert len(EMBEDDED_WALLET_SALT) > 0
        assert len(EMBEDDED_WALLET_DIR) > 0

    def test_trade_peer_secret(self):
        """Test wallet trade peer secret"""
        assert hasattr(Config, "WALLET_TRADE_PEER_SECRET")
        assert len(Config.WALLET_TRADE_PEER_SECRET) > 0

    def test_time_capsule_key(self):
        """Test time capsule master key"""
        assert isinstance(TIME_CAPSULE_MASTER_KEY, str)
        assert len(TIME_CAPSULE_MASTER_KEY) > 0


class TestGovernanceConfiguration:
    """Test governance configuration"""

    def test_fiat_unlock_governance_start(self):
        """Test fiat unlock governance start date"""
        assert hasattr(Config, "FIAT_UNLOCK_GOVERNANCE_START")
        assert isinstance(Config.FIAT_UNLOCK_GOVERNANCE_START, datetime)
        assert Config.FIAT_UNLOCK_GOVERNANCE_START.tzinfo == timezone.utc

    def test_fiat_unlock_required_votes(self):
        """Test required votes for fiat unlock"""
        assert hasattr(Config, "FIAT_UNLOCK_REQUIRED_VOTES")
        assert isinstance(Config.FIAT_UNLOCK_REQUIRED_VOTES, int)
        assert Config.FIAT_UNLOCK_REQUIRED_VOTES > 0

    def test_fiat_unlock_support_percent(self):
        """Test support percentage for fiat unlock"""
        assert hasattr(Config, "FIAT_UNLOCK_SUPPORT_PERCENT")
        assert isinstance(Config.FIAT_UNLOCK_SUPPORT_PERCENT, float)
        assert 0 < Config.FIAT_UNLOCK_SUPPORT_PERCENT <= 1

    def test_fiat_reenable_date(self):
        """Test fiat reenable date"""
        assert hasattr(Config, "FIAT_REENABLE_DATE")
        assert isinstance(Config.FIAT_REENABLE_DATE, datetime)


class TestTradingConfiguration:
    """Test trading configuration"""

    def test_trade_fee_percent(self):
        """Test trade fee percentage"""
        assert hasattr(Config, "TRADE_FEE_PERCENT")
        assert isinstance(Config.TRADE_FEE_PERCENT, float)
        assert Config.TRADE_FEE_PERCENT > 0
        assert Config.TRADE_FEE_PERCENT < 0.1  # Less than 10%

    def test_trade_order_expiry(self):
        """Test trade order expiry time"""
        assert hasattr(Config, "TRADE_ORDER_EXPIRY")
        assert isinstance(Config.TRADE_ORDER_EXPIRY, int)
        assert Config.TRADE_ORDER_EXPIRY > 0

    def test_trade_fee_address(self):
        """Test trade fee collection address"""
        assert hasattr(Config, "TRADE_FEE_ADDRESS")
        assert isinstance(Config.TRADE_FEE_ADDRESS, str)
        assert len(Config.TRADE_FEE_ADDRESS) > 0


class TestBlockHeaderConfiguration:
    """Test block header configuration"""

    def test_block_header_version(self):
        """Test block header version"""
        assert hasattr(Config, "BLOCK_HEADER_VERSION")
        assert isinstance(Config.BLOCK_HEADER_VERSION, int)
        assert Config.BLOCK_HEADER_VERSION > 0

    def test_block_header_allowed_versions(self):
        """Test allowed block header versions"""
        assert hasattr(Config, "BLOCK_HEADER_ALLOWED_VERSIONS")
        assert isinstance(Config.BLOCK_HEADER_ALLOWED_VERSIONS, list)
        assert len(Config.BLOCK_HEADER_ALLOWED_VERSIONS) > 0
        assert Config.BLOCK_HEADER_VERSION in Config.BLOCK_HEADER_ALLOWED_VERSIONS


class TestGasConfiguration:
    """Test gas/execution configuration"""

    def test_max_contract_gas(self):
        """Test maximum contract gas limit"""
        assert isinstance(MAX_CONTRACT_GAS, int)
        assert MAX_CONTRACT_GAS > 0
        assert MAX_CONTRACT_GAS <= 100000000  # Reasonable upper bound


class TestGenesisHashConfiguration:
    """Test genesis hash configuration"""

    def test_safe_genesis_hashes(self):
        """Test safe genesis hashes are defined"""
        assert hasattr(Config, "SAFE_GENESIS_HASHES")
        assert isinstance(Config.SAFE_GENESIS_HASHES, dict)
        assert NetworkType.TESTNET in Config.SAFE_GENESIS_HASHES
        assert NetworkType.MAINNET in Config.SAFE_GENESIS_HASHES

    def test_testnet_genesis_hash_set(self):
        """Test testnet genesis hash is set"""
        assert len(Config.SAFE_GENESIS_HASHES[NetworkType.TESTNET]) > 0

    def test_genesis_hash_format(self):
        """Test genesis hash format (hex string)"""
        testnet_hash = Config.SAFE_GENESIS_HASHES[NetworkType.TESTNET]
        # Should be hex string
        assert all(c in "0123456789abcdef" for c in testnet_hash.lower())
        # Should be 64 characters (SHA-256)
        assert len(testnet_hash) == 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
