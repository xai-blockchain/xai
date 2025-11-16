"""
Test suite for XAI Configuration (Testnet/Mainnet)

Tests:
- Testnet configuration
- Mainnet configuration
- Network switching
- Configuration values
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import Config, TestnetConfig, MainnetConfig, NetworkType


class TestConfiguration:
    """Test configuration system"""

    def test_config_exists(self):
        """Test that Config is properly loaded"""
        assert Config is not None, "Config should be loaded"

    def test_network_type(self):
        """Test that network type is set"""
        assert hasattr(Config, "NETWORK_TYPE"), "Should have NETWORK_TYPE"
        assert Config.NETWORK_TYPE in [
            NetworkType.TESTNET,
            NetworkType.MAINNET,
        ], "Network type should be TESTNET or MAINNET"


class TestTestnetConfig:
    """Test testnet-specific configuration"""

    def test_testnet_network_type(self):
        """Test testnet network type"""
        assert TestnetConfig.NETWORK_TYPE == NetworkType.TESTNET

    def test_testnet_difficulty(self):
        """Test testnet has lower difficulty"""
        assert TestnetConfig.INITIAL_DIFFICULTY == 2, "Testnet difficulty should be 2"
        assert (
            TestnetConfig.INITIAL_DIFFICULTY < MainnetConfig.INITIAL_DIFFICULTY
        ), "Testnet difficulty should be less than mainnet"

    def test_testnet_ports(self):
        """Test testnet uses different ports"""
        assert TestnetConfig.DEFAULT_PORT == 18545, "Testnet port should be 18545"
        assert TestnetConfig.DEFAULT_RPC_PORT == 18546, "Testnet RPC port should be 18546"

    def test_testnet_address_prefix(self):
        """Test testnet address prefix"""
        assert TestnetConfig.ADDRESS_PREFIX == "TXAI", "Testnet prefix should be TXAI"

    def test_testnet_faucet_enabled(self):
        """Test testnet has faucet enabled"""
        assert TestnetConfig.FAUCET_ENABLED == True, "Testnet should have faucet"
        assert TestnetConfig.FAUCET_AMOUNT == 100.0, "Testnet faucet should give 100 XAI"

    def test_testnet_reset_allowed(self):
        """Test testnet allows chain reset"""
        assert TestnetConfig.ALLOW_CHAIN_RESET == True, "Testnet should allow reset"

    def test_testnet_genesis_file(self):
        """Test testnet uses separate genesis file"""
        assert TestnetConfig.GENESIS_FILE == "genesis_testnet.json"

    def test_testnet_blockchain_file(self):
        """Test testnet uses separate blockchain file"""
        assert TestnetConfig.BLOCKCHAIN_FILE == "blockchain_testnet.json"


class TestMainnetConfig:
    """Test mainnet-specific configuration"""

    def test_mainnet_network_type(self):
        """Test mainnet network type"""
        assert MainnetConfig.NETWORK_TYPE == NetworkType.MAINNET

    def test_mainnet_difficulty(self):
        """Test mainnet has production difficulty"""
        assert MainnetConfig.INITIAL_DIFFICULTY == 4, "Mainnet difficulty should be 4"

    def test_mainnet_ports(self):
        """Test mainnet uses standard ports"""
        assert MainnetConfig.DEFAULT_PORT == 8545, "Mainnet port should be 8545"
        assert MainnetConfig.DEFAULT_RPC_PORT == 8546, "Mainnet RPC port should be 8546"

    def test_mainnet_address_prefix(self):
        """Test mainnet address prefix"""
        assert MainnetConfig.ADDRESS_PREFIX == "AIXN", "Mainnet prefix should be AIXN"

    def test_mainnet_faucet_disabled(self):
        """Test mainnet has faucet disabled"""
        assert MainnetConfig.FAUCET_ENABLED == False, "Mainnet should not have faucet"
        assert MainnetConfig.FAUCET_AMOUNT == 0.0, "Mainnet faucet amount should be 0"

    def test_mainnet_reset_not_allowed(self):
        """Test mainnet does not allow chain reset"""
        assert MainnetConfig.ALLOW_CHAIN_RESET == False, "Mainnet should not allow reset"

    def test_mainnet_genesis_file(self):
        """Test mainnet uses production genesis file"""
        assert MainnetConfig.GENESIS_FILE == "genesis_new.json"

    def test_mainnet_blockchain_file(self):
        """Test mainnet uses production blockchain file"""
        assert MainnetConfig.BLOCKCHAIN_FILE == "blockchain.json"


class TestSharedConfig:
    """Test configuration values shared between testnet and mainnet"""

    def test_max_supply(self):
        """Test max supply is same for both networks"""
        assert TestnetConfig.MAX_SUPPLY == 121000000.0, "Testnet max supply should be 121M"
        assert MainnetConfig.MAX_SUPPLY == 121000000.0, "Mainnet max supply should be 121M"
        assert (
            TestnetConfig.MAX_SUPPLY == MainnetConfig.MAX_SUPPLY
        ), "Both networks should have same max supply"

    def test_block_reward(self):
        """Test initial block reward is same"""
        assert TestnetConfig.INITIAL_BLOCK_REWARD == 12.0
        assert MainnetConfig.INITIAL_BLOCK_REWARD == 12.0
        assert TestnetConfig.INITIAL_BLOCK_REWARD == MainnetConfig.INITIAL_BLOCK_REWARD

    def test_halving_interval(self):
        """Test halving interval is same"""
        assert TestnetConfig.HALVING_INTERVAL == 262800
        assert MainnetConfig.HALVING_INTERVAL == 262800
        assert TestnetConfig.HALVING_INTERVAL == MainnetConfig.HALVING_INTERVAL

    def test_block_time_target(self):
        """Test block time target"""
        assert TestnetConfig.BLOCK_TIME_TARGET == 120, "Block time should be 2 minutes"
        assert MainnetConfig.BLOCK_TIME_TARGET == 120, "Block time should be 2 minutes"


class TestNetworkIsolation:
    """Test that testnet and mainnet are properly isolated"""

    def test_different_network_ids(self):
        """Test networks have different IDs"""
        assert (
            TestnetConfig.NETWORK_ID != MainnetConfig.NETWORK_ID
        ), "Networks should have different IDs"

    def test_different_ports(self):
        """Test networks use different ports"""
        assert (
            TestnetConfig.DEFAULT_PORT != MainnetConfig.DEFAULT_PORT
        ), "Networks should use different ports"

    def test_different_address_prefixes(self):
        """Test networks use different address prefixes"""
        assert (
            TestnetConfig.ADDRESS_PREFIX != MainnetConfig.ADDRESS_PREFIX
        ), "Networks should use different address prefixes"

    def test_different_genesis_files(self):
        """Test networks use different genesis files"""
        assert (
            TestnetConfig.GENESIS_FILE != MainnetConfig.GENESIS_FILE
        ), "Networks should use different genesis files"

    def test_different_blockchain_files(self):
        """Test networks use different blockchain files"""
        assert (
            TestnetConfig.BLOCKCHAIN_FILE != MainnetConfig.BLOCKCHAIN_FILE
        ), "Networks should use different blockchain files"

    def test_different_data_directories(self):
        """Test networks use different data directories"""
        assert (
            TestnetConfig.DATA_DIR != MainnetConfig.DATA_DIR
        ), "Networks should use different data directories"


class TestSecurityConstraints:
    """Test security-related configuration constraints"""

    def test_mainnet_security(self):
        """Test mainnet has strict security"""
        assert MainnetConfig.FAUCET_ENABLED == False, "Mainnet should not have faucet"
        assert MainnetConfig.ALLOW_CHAIN_RESET == False, "Mainnet should not allow reset"

    def test_testnet_flexibility(self):
        """Test testnet has development flexibility"""
        assert TestnetConfig.FAUCET_ENABLED == True, "Testnet should have faucet for testing"
        assert TestnetConfig.ALLOW_CHAIN_RESET == True, "Testnet should allow reset for testing"

    def test_production_difficulty(self):
        """Test mainnet has higher difficulty for security"""
        assert (
            MainnetConfig.INITIAL_DIFFICULTY > TestnetConfig.INITIAL_DIFFICULTY
        ), "Mainnet should have higher difficulty than testnet"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
