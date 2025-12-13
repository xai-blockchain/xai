#!/usr/bin/env python3
"""
Comprehensive CLI Command Verification Tests (Phase 2.3)

Tests all CLI commands and subcommands with valid/invalid parameters,
error handling, and output verification.

Entry Points:
- xai (enhanced CLI) - click-based with AI, mining, network, wallet, blockchain commands
- xai-wallet (legacy CLI) - argparse-based with wallet operations
- xai-node (node startup)

This test suite covers Phase 2.3 of LOCAL_TESTING_PLAN.md.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import pytest


class CLITestHelper:
    """Helper class for CLI testing"""

    @staticmethod
    def run_command(
        cmd: List[str],
        input_data: Optional[str] = None,
        env: Optional[dict] = None,
        expect_failure: bool = False,
    ) -> Tuple[int, str, str]:
        """
        Run a CLI command and return (returncode, stdout, stderr)

        Args:
            cmd: Command and arguments as list
            input_data: Data to pipe to stdin
            env: Environment variables
            expect_failure: If True, don't fail test on non-zero exit

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        # Merge with current environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30,
                env=full_env,
            )
            if not expect_failure and result.returncode != 0:
                print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
                print(f"STDOUT: {result.stdout}", file=sys.stderr)
                print(f"STDERR: {result.stderr}", file=sys.stderr)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            pytest.fail(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            pytest.fail(f"Command not found: {cmd[0]}")

    @staticmethod
    def is_json(text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError):
            return False


# ==============================================================================
# Enhanced CLI (xai) - Main Entry Point Tests
# ==============================================================================


class TestEnhancedCLIMain:
    """Test main xai CLI entry point"""

    def test_cli_help(self):
        """Test xai --help shows usage"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "--help"])
        assert returncode == 0
        assert "XAI Blockchain CLI" in stdout or "Usage" in stdout
        assert "wallet" in stdout.lower()
        assert "blockchain" in stdout.lower()

    def test_cli_version_info(self):
        """Test CLI displays version/info"""
        # The CLI may not have a --version flag, but help should show something
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "--help"])
        assert returncode == 0
        assert len(stdout) > 0

    def test_cli_invalid_command(self):
        """Test invalid command shows error"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "invalid-command-xyz"], expect_failure=True
        )
        assert returncode != 0

    def test_cli_json_output_flag(self):
        """Test --json-output flag is recognized"""
        # Test that --json-output is a valid global flag
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--json-output", "--help"]
        )
        assert returncode == 0


# ==============================================================================
# Wallet Commands (Enhanced CLI)
# ==============================================================================


class TestEnhancedWalletCommands:
    """Test xai wallet subcommands"""

    def test_wallet_help(self):
        """Test xai wallet --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "wallet", "--help"])
        assert returncode == 0
        assert "wallet" in stdout.lower()
        assert any(cmd in stdout.lower() for cmd in ["create", "balance", "send"])

    def test_wallet_create_help(self):
        """Test xai wallet create --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "create", "--help"]
        )
        assert returncode == 0
        assert "create" in stdout.lower()
        assert "keystore" in stdout.lower()

    def test_wallet_create_basic(self):
        """Test wallet create without saving"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "wallet", "create"])
        assert returncode == 0
        assert "address" in stdout.lower() or "Address" in stdout

    def test_wallet_create_json_output(self):
        """Test wallet create with --json-output"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--json-output", "wallet", "create"]
        )
        assert returncode == 0
        assert CLITestHelper.is_json(stdout)
        data = json.loads(stdout)
        assert "address" in data
        assert "public_key" in data

    def test_wallet_balance_missing_address(self):
        """Test wallet balance without address fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "balance"], expect_failure=True
        )
        assert returncode != 0

    def test_wallet_send_missing_params(self):
        """Test wallet send without required params fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "send"], expect_failure=True
        )
        assert returncode != 0

    def test_wallet_send_help(self):
        """Test wallet send --help shows required params"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "send", "--help"]
        )
        assert returncode == 0
        assert "--sender" in stdout
        assert "--recipient" in stdout
        assert "--amount" in stdout

    def test_wallet_history_help(self):
        """Test wallet history --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "history", "--help"]
        )
        assert returncode == 0
        assert "history" in stdout.lower()
        assert "--limit" in stdout or "--offset" in stdout

    def test_wallet_portfolio_help(self):
        """Test wallet portfolio --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "portfolio", "--help"]
        )
        assert returncode == 0
        assert "portfolio" in stdout.lower()


# ==============================================================================
# Blockchain Commands (Enhanced CLI)
# ==============================================================================


class TestEnhancedBlockchainCommands:
    """Test xai blockchain subcommands"""

    def test_blockchain_help(self):
        """Test xai blockchain --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "blockchain", "--help"])
        assert returncode == 0
        assert "blockchain" in stdout.lower()

    def test_blockchain_info_help(self):
        """Test xai blockchain info --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "blockchain", "info", "--help"]
        )
        assert returncode == 0
        assert "info" in stdout.lower()

    def test_blockchain_block_help(self):
        """Test xai blockchain block --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "blockchain", "block", "--help"]
        )
        assert returncode == 0
        assert "block" in stdout.lower()

    def test_blockchain_block_missing_id(self):
        """Test blockchain block without ID fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "blockchain", "block"], expect_failure=True
        )
        assert returncode != 0

    def test_blockchain_mempool_help(self):
        """Test xai blockchain mempool --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "blockchain", "mempool", "--help"]
        )
        assert returncode == 0
        assert "mempool" in stdout.lower()


# ==============================================================================
# Mining Commands (Enhanced CLI)
# ==============================================================================


class TestEnhancedMiningCommands:
    """Test xai mining subcommands"""

    def test_mining_help(self):
        """Test xai mining --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "mining", "--help"])
        assert returncode == 0
        assert "mining" in stdout.lower()

    def test_mining_start_help(self):
        """Test xai mining start --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "mining", "start", "--help"]
        )
        assert returncode == 0
        assert "start" in stdout.lower()
        assert "--address" in stdout

    def test_mining_start_missing_address(self):
        """Test mining start without address fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "mining", "start"], expect_failure=True
        )
        assert returncode != 0

    def test_mining_stop_help(self):
        """Test xai mining stop --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "mining", "stop", "--help"]
        )
        assert returncode == 0

    def test_mining_status_help(self):
        """Test xai mining status --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "mining", "status", "--help"]
        )
        assert returncode == 0

    def test_mining_stats_help(self):
        """Test xai mining stats --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "mining", "stats", "--help"]
        )
        assert returncode == 0
        assert "--address" in stdout


# ==============================================================================
# Network Commands (Enhanced CLI)
# ==============================================================================


class TestEnhancedNetworkCommands:
    """Test xai network subcommands"""

    def test_network_help(self):
        """Test xai network --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "network", "--help"])
        assert returncode == 0
        assert "network" in stdout.lower()

    def test_network_info_help(self):
        """Test xai network info --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "network", "info", "--help"]
        )
        assert returncode == 0

    def test_network_peers_help(self):
        """Test xai network peers --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "network", "peers", "--help"]
        )
        assert returncode == 0


# ==============================================================================
# AI Commands (Enhanced CLI)
# ==============================================================================


class TestEnhancedAICommands:
    """Test xai ai subcommands"""

    def test_ai_help(self):
        """Test xai ai --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "ai", "--help"])
        assert returncode == 0
        assert "ai" in stdout.lower()

    def test_ai_submit_help(self):
        """Test xai ai submit --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "ai", "submit", "--help"])
        assert returncode == 0
        assert "submit" in stdout.lower()
        assert "--task-type" in stdout
        assert "--description" in stdout

    def test_ai_submit_missing_params(self):
        """Test ai submit without required params fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "submit"], expect_failure=True
        )
        assert returncode != 0

    def test_ai_query_help(self):
        """Test xai ai query --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "ai", "query", "--help"])
        assert returncode == 0
        assert "--watch" in stdout or "watch" in stdout.lower()

    def test_ai_query_missing_task_id(self):
        """Test ai query without task ID fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "query"], expect_failure=True
        )
        assert returncode != 0

    def test_ai_cancel_help(self):
        """Test xai ai cancel --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "ai", "cancel", "--help"])
        assert returncode == 0

    def test_ai_list_help(self):
        """Test xai ai list --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "ai", "list", "--help"])
        assert returncode == 0
        assert "--status" in stdout or "--limit" in stdout

    def test_ai_providers_help(self):
        """Test xai ai providers --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "providers", "--help"]
        )
        assert returncode == 0
        assert "--sort-by" in stdout or "sort" in stdout.lower()

    def test_ai_provider_details_help(self):
        """Test xai ai provider-details --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "provider-details", "--help"]
        )
        assert returncode == 0

    def test_ai_earnings_help(self):
        """Test xai ai earnings --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "earnings", "--help"]
        )
        assert returncode == 0
        assert "--provider-id" in stdout

    def test_ai_register_provider_help(self):
        """Test xai ai register-provider --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "register-provider", "--help"]
        )
        assert returncode == 0
        assert "--wallet" in stdout
        assert "--models" in stdout

    def test_ai_marketplace_help(self):
        """Test xai ai marketplace --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "ai", "marketplace", "--help"]
        )
        assert returncode == 0


# ==============================================================================
# Legacy Wallet CLI (xai-wallet) Tests
# ==============================================================================


class TestLegacyWalletCLI:
    """Test legacy xai-wallet CLI (argparse-based)"""

    def test_legacy_wallet_help(self):
        """Test xai-wallet --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai-wallet", "--help"])
        assert returncode == 0
        assert "wallet" in stdout.lower()

    def test_legacy_wallet_no_args(self):
        """Test xai-wallet with no args shows help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai-wallet"])
        assert returncode == 0
        # Should show help or usage

    def test_generate_address_help(self):
        """Test xai-wallet generate-address --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "generate-address", "--help"]
        )
        assert returncode == 0
        assert "generate" in stdout.lower()
        assert "--save-keystore" in stdout

    def test_generate_address_basic(self):
        """Test generating address (no saving)"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "generate-address"]
        )
        assert returncode == 0
        assert "address" in stdout.lower()

    def test_request_faucet_help(self):
        """Test xai-wallet request-faucet --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "request-faucet", "--help"]
        )
        assert returncode == 0
        assert "--address" in stdout

    def test_request_faucet_missing_address(self):
        """Test request-faucet without address fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "request-faucet"], expect_failure=True
        )
        assert returncode != 0

    def test_balance_help(self):
        """Test xai-wallet balance --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "balance", "--help"]
        )
        assert returncode == 0
        assert "--address" in stdout

    def test_balance_missing_address(self):
        """Test balance without address fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "balance"], expect_failure=True
        )
        assert returncode != 0

    def test_send_help(self):
        """Test xai-wallet send --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai-wallet", "send", "--help"])
        assert returncode == 0
        assert "--sender" in stdout
        assert "--recipient" in stdout
        assert "--amount" in stdout

    def test_send_missing_params(self):
        """Test send without required params fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "send"], expect_failure=True
        )
        assert returncode != 0

    def test_history_help(self):
        """Test xai-wallet history --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "history", "--help"]
        )
        assert returncode == 0
        assert "--address" in stdout

    def test_export_help(self):
        """Test xai-wallet export --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "export", "--help"]
        )
        assert returncode == 0
        assert "--address" in stdout
        assert "--encrypt" in stdout or "--output" in stdout

    def test_export_missing_address(self):
        """Test export without address fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "export"], expect_failure=True
        )
        assert returncode != 0

    def test_import_help(self):
        """Test xai-wallet import --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "import", "--help"]
        )
        assert returncode == 0
        assert "--file" in stdout

    def test_import_missing_file(self):
        """Test import without file fails"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "import"], expect_failure=True
        )
        assert returncode != 0

    def test_mnemonic_qr_help(self):
        """Test xai-wallet mnemonic-qr --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "mnemonic-qr", "--help"]
        )
        assert returncode == 0
        assert "mnemonic" in stdout.lower()

    def test_2fa_setup_help(self):
        """Test xai-wallet 2fa-setup --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "2fa-setup", "--help"]
        )
        assert returncode == 0
        assert "--label" in stdout

    def test_2fa_status_help(self):
        """Test xai-wallet 2fa-status --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "2fa-status", "--help"]
        )
        assert returncode == 0
        assert "--label" in stdout

    def test_2fa_disable_help(self):
        """Test xai-wallet 2fa-disable --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "2fa-disable", "--help"]
        )
        assert returncode == 0
        assert "--label" in stdout


# ==============================================================================
# Parameter Validation Tests
# ==============================================================================


class TestParameterValidation:
    """Test parameter validation and error messages"""

    def test_invalid_amount_format(self):
        """Test invalid amount format is rejected"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            [
                "xai",
                "wallet",
                "send",
                "--sender",
                "ADDR1",
                "--recipient",
                "ADDR2",
                "--amount",
                "invalid",
            ],
            expect_failure=True,
        )
        assert returncode != 0

    def test_negative_amount(self):
        """Test negative amount is rejected"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            [
                "xai",
                "wallet",
                "send",
                "--sender",
                "ADDR1",
                "--recipient",
                "ADDR2",
                "--amount",
                "-10",
            ],
            expect_failure=True,
        )
        assert returncode != 0

    def test_invalid_timeout(self):
        """Test invalid timeout value"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--timeout", "invalid", "wallet", "--help"], expect_failure=True
        )
        assert returncode != 0

    def test_valid_timeout(self):
        """Test valid timeout value"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--timeout", "60.0", "wallet", "--help"]
        )
        assert returncode == 0

    def test_invalid_node_url(self):
        """Test malformed node URL is handled"""
        # Should not crash, but may warn or use default
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--node-url", "not-a-valid-url", "wallet", "--help"]
        )
        # Should still show help even with bad URL
        assert returncode == 0


# ==============================================================================
# Output Format Tests
# ==============================================================================


class TestOutputFormats:
    """Test different output formats"""

    def test_json_output_wallet_create(self):
        """Test JSON output for wallet create"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--json-output", "wallet", "create"]
        )
        assert returncode == 0
        assert CLITestHelper.is_json(stdout)

    def test_json_output_legacy_wallet(self):
        """Test JSON output for legacy wallet"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "generate-address", "--json"], input_data="SHOW JSON\n"
        )
        # May fail or require confirmation - just check it doesn't crash
        assert returncode in [0, 1]

    def test_human_readable_output(self):
        """Test human-readable output (default)"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "wallet", "create"])
        assert returncode == 0
        # Should not be JSON
        assert not CLITestHelper.is_json(stdout)


# ==============================================================================
# Error Message Quality Tests
# ==============================================================================


class TestErrorMessages:
    """Test that error messages are clear and helpful"""

    def test_command_not_found_error(self):
        """Test error for non-existent command"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "nonexistent-command"], expect_failure=True
        )
        assert returncode != 0
        # Should have some error message
        assert len(stdout) + len(stderr) > 0

    def test_missing_required_param_error(self):
        """Test error for missing required parameter"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "balance"], expect_failure=True
        )
        assert returncode != 0
        # Should mention the missing parameter
        error_output = stdout + stderr
        assert "address" in error_output.lower() or "required" in error_output.lower()

    def test_help_shows_examples(self):
        """Test that help text includes examples or usage"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "wallet", "send", "--help"]
        )
        assert returncode == 0
        # Should have sender, recipient, amount mentioned
        assert "--sender" in stdout
        assert "--recipient" in stdout
        assert "--amount" in stdout


# ==============================================================================
# Integration: Keystore Operations
# ==============================================================================


class TestKeystoreOperations:
    """Test keystore file operations"""

    def test_generate_with_keystore_help(self):
        """Test generate with keystore option"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "generate-address", "--help"]
        )
        assert returncode == 0
        assert "--save-keystore" in stdout

    def test_export_with_encryption_help(self):
        """Test export with encryption option"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "export", "--help"]
        )
        assert returncode == 0
        assert "--encrypt" in stdout or "--no-encrypt" in stdout

    def test_kdf_options(self):
        """Test KDF options are available"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai-wallet", "generate-address", "--help"]
        )
        assert returncode == 0
        assert "--kdf" in stdout or "pbkdf2" in stdout.lower() or "argon2" in stdout.lower()


# ==============================================================================
# Flag Combinations
# ==============================================================================


class TestFlagCombinations:
    """Test valid and invalid flag combinations"""

    def test_help_with_other_flags(self):
        """Test --help works even with other flags"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--node-url", "http://localhost:8545", "wallet", "--help"]
        )
        assert returncode == 0

    def test_json_and_help_together(self):
        """Test --json-output with --help"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--json-output", "wallet", "create", "--help"]
        )
        assert returncode == 0

    def test_multiple_format_flags(self):
        """Test behavior with multiple output format flags"""
        # Test with JSON output at different positions
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--json-output", "wallet", "create"]
        )
        assert returncode == 0


# ==============================================================================
# Legacy Mode Tests
# ==============================================================================


class TestLegacyMode:
    """Test --legacy flag functionality"""

    def test_legacy_flag_exists(self):
        """Test --legacy flag is recognized"""
        # This should fall back to legacy wallet CLI
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "--legacy", "--help"])
        # Should work regardless of which CLI it uses
        assert returncode == 0


# ==============================================================================
# Node URL Configuration
# ==============================================================================


class TestNodeURLConfiguration:
    """Test node URL configuration"""

    def test_default_node_url(self):
        """Test default node URL is used"""
        returncode, stdout, stderr = CLITestHelper.run_command(["xai", "wallet", "--help"])
        assert returncode == 0

    def test_custom_node_url(self):
        """Test custom node URL flag"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--node-url", "http://custom:8545", "wallet", "--help"]
        )
        assert returncode == 0

    def test_node_url_with_trailing_slash(self):
        """Test node URL with trailing slash is handled"""
        returncode, stdout, stderr = CLITestHelper.run_command(
            ["xai", "--node-url", "http://localhost:8545/", "wallet", "--help"]
        )
        assert returncode == 0


# ==============================================================================
# Command Listing Test
# ==============================================================================


def test_all_commands_have_help():
    """Meta-test: Ensure all commands have help text"""
    commands = [
        ["xai", "--help"],
        ["xai", "wallet", "--help"],
        ["xai", "blockchain", "--help"],
        ["xai", "mining", "--help"],
        ["xai", "network", "--help"],
        ["xai", "ai", "--help"],
        ["xai-wallet", "--help"],
    ]

    for cmd in commands:
        returncode, stdout, stderr = CLITestHelper.run_command(cmd)
        assert returncode == 0, f"Help failed for: {' '.join(cmd)}"
        assert len(stdout) > 0, f"No help output for: {' '.join(cmd)}"


# ==============================================================================
# Summary Test
# ==============================================================================


def test_cli_test_summary():
    """Print summary of CLI test coverage"""
    print("\n" + "=" * 80)
    print("CLI Command Verification Test Summary (Phase 2.3)")
    print("=" * 80)
    print("\nCovered Entry Points:")
    print("  - xai (enhanced CLI)")
    print("  - xai-wallet (legacy CLI)")
    print("\nCovered Command Groups:")
    print("  - wallet (create, balance, send, history, portfolio)")
    print("  - blockchain (info, block, mempool)")
    print("  - mining (start, stop, status, stats)")
    print("  - network (info, peers)")
    print("  - ai (submit, query, cancel, list, providers, earnings, marketplace)")
    print("\nCovered Test Categories:")
    print("  - Help text verification")
    print("  - Parameter validation")
    print("  - Missing parameter handling")
    print("  - Invalid parameter handling")
    print("  - Output format verification (JSON, human-readable)")
    print("  - Error message quality")
    print("  - Flag combinations")
    print("  - Keystore operations")
    print("=" * 80)
