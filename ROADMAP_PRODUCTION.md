# XAI Blockchain - Documentation Audit Roadmap

Last updated: 2026-01-02

## Status

- Documentation audit complete; validation tasks remain.
- Updated Discord invite links in docs and setup wizard.

## Roadmap

### Validation

- [ ] Run full test suite with a longer timeout (low-priority scheduling to avoid overload)
- [x] Ensure faker/hypothesis are tracked in test/dev requirements
- [x] Confirm Python is available in PATH or via a venv for testing
- [x] Install faker and run fuzzing tests (low-priority scheduling to avoid overload)

### Test Batches (Completed/Recorded)

- [x] tests/alerting (12 passed)
- [x] tests/api (0 collected)
- [x] tests/chaos/test_node_failures.py (16 passed)
- [x] tests/chaos/test_p2p_security_metrics.py (1 passed)
- [x] tests/chaos/test_partition_reconnect_utxo_digest.py (1 passed)
- [x] tests/chaos/test_reorg_snapshot_bounded_orphans.py (1 passed)
- [x] tests/chaos/test_security_modules_chaos.py (3 passed)
- [x] tests/e2e (50 passed)
- [x] tests/tools (6 passed; 2 return-not-none warnings)
- [x] tests/xai_tests/fuzz tests/xai_tests/fuzzing (30 passed)
- [x] tests/test_agent_accessibility.py (35 passed)
- [x] tests/test_cli_entry_points.py (11 passed)
- [x] tests/test_crypto_utils.py (37 passed)
- [x] tests/test_utxo_manager.py (62 passed)
- [x] tests/xai_tests/unit batch 01 (test_abi_utils.py, test_access_control.py, test_additional_ai_providers_coverage.py)
- [x] tests/xai_tests/unit batch 02 (test_address_checksum.py, test_address_format_validator.py, test_address_index.py)
- [x] tests/xai_tests/unit test_advanced_consensus_coverage.py (61 passed; HYPOTHESIS_MAX_EXAMPLES=10, ~5m)
- [x] tests/xai_tests/unit test_advanced_rate_limiter_coverage.py (62 passed)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py completed via batches A-F
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch A (TestBlockStatusEnum, TestBlockPropagationMonitorEdgeCases, TestOrphanBlockPoolEdgeCases)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch B (TestTransactionOrderingEdgeCases, TestFinalityTrackerEdgeCases, TestFinalityMechanismEdgeCases)
- [ ] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C timed out at 4m (DynamicDifficultyAdjustment, DifficultyAdjustment, AdvancedConsensusManager)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C1 (TestDynamicDifficultyAdjustmentEdgeCases)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C2 (TestDifficultyAdjustmentEdgeCases)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C3.1 (test_process_new_block_with_peer_tracking)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C3.2 (test_process_orphans_recursive_chain)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch C3.3 (order_pending_transactions_empty, adjust_difficulty_no_change, mark_finalized_blocks_short_chain, consensus_stats_integration)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch D (TestTransactionOrderingRulesEdgeCases)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch E (TestOrphanBlockManagerCompatibility)
- [x] tests/xai_tests/unit test_advanced_consensus_enhanced.py batch F (TestComplexIntegrationScenarios)
- [x] tests/xai_tests/unit batch 03 (test_ai_governance_coverage.py, test_ai_governance_griefing.py, test_ai_pool_with_strict_limits_coverage.py)
- [x] tests/xai_tests/unit batch 04 (test_ai_safety_controls_api_coverage.py, test_ai_safety_controls_coverage.py, test_ai_safety_controls.py) (170 passed)
- [x] tests/xai_tests/unit test_ai_trading_bot_coverage.py (71 passed; 1 warning)
- [x] tests/xai_tests/unit test_algo_fee_optimizer.py (2 passed)
- [x] tests/xai_tests/unit test_aml_compliance_simple.py (12 passed)
- [x] tests/xai_tests/unit test_aml_compliance.py (35 passed)
- [x] tests/xai_tests/unit test_aml_compliance_coverage.py (71 passed)
- [x] tests/xai_tests/unit test_anonymous_logger.py (1 passed)
- [x] tests/xai_tests/unit test_anti_whale_manager.py (4 passed)
- [x] tests/xai_tests/unit test_api_ai_coverage.py (60 passed)
- [x] tests/xai_tests/unit test_api_auth.py (3 passed)
- [x] tests/xai_tests/unit test_api_auth_scopes.py (3 passed)
- [x] tests/xai_tests/unit test_api_auth_keystore.py (5 passed)
- [x] tests/xai_tests/unit test_api_caching.py (16 passed; 3 warnings)
- [x] tests/xai_tests/unit test_api_explorer.py (9 passed)
- [x] tests/xai_tests/unit test_api_governance.py (20 passed)
- [x] tests/xai_tests/unit test_api_mining.py (21 passed)
- [x] tests/xai_tests/unit test_api_rate_limiting.py (21 passed)
- [x] tests/xai_tests/unit test_api_security.py (3 passed)
- [x] tests/xai_tests/unit test_api_versioning.py (3 passed; 3 warnings)
- [x] tests/xai_tests/unit test_api_wallet_coverage.py (70 passed)
- [x] tests/xai_tests/unit test_api_wallet_private_key_security.py (17 passed)
- [x] tests/xai_tests/unit test_api_wallet.py (38 passed)
- [x] tests/xai_tests/unit test_api_websocket.py (3 passed)
- [x] tests/xai_tests/unit test_ast_validator.py (55 passed)
- [x] tests/xai_tests/unit test_atomic_swap_amount_parsing.py (1 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_cli_tools.py (2 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_cross_chain_verifier.py (10 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_fee_calc.py (4 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_htlc_generation.py (6 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_manager_recovery.py (3 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_recovery_service.py (3 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_recovery_service_transition.py (1 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_redeem_script.py (1 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_spv.py (4 passed; 1 warning)
- [x] tests/xai_tests/unit test_atomic_swap_timeouts.py (12 passed)
- [x] tests/xai_tests/unit test_auto_switching_ai_executor_coverage.py (49 passed)
- [x] tests/xai_tests/unit test_biometric_auth.py (46 passed)
- [x] tests/xai_tests/unit test_blacklist_updater.py (4 passed)
- [x] tests/xai_tests/unit test_blockchain_admin.py (3 passed)
- [x] tests/xai_tests/unit test_blockchain_balance_provider.py (2 passed)
- [x] tests/xai_tests/unit test_blockchain_checkpoint_sync.py (2 passed)
- [x] tests/xai_tests/unit test_blockchain_coverage_boost.py (38 passed)
- [x] tests/xai_tests/unit test_blockchain_determinism.py (1 passed)
- [x] tests/xai_tests/unit test_blockchain_enhanced.py (50 passed)
- [x] tests/xai_tests/unit test_blockchain_finality.py (4 passed)
- [x] tests/xai_tests/unit test_blockchain_fork_atomicity.py (5 passed)
- [x] tests/xai_tests/unit test_blockchain_fork_handling.py (14 passed)
- [x] tests/xai_tests/unit test_blockchain_governance_enforcement.py (1 passed)
- [x] tests/xai_tests/unit test_blockchain_governance_mixin.py (16 passed)
- [x] tests/xai_tests/unit test_blockchain_invariants_comprehensive.py (24 passed)
- [x] tests/xai_tests/unit test_blockchain_orphan_mixin.py (24 passed)
- [x] tests/xai_tests/unit test_blockchain_persistence.py (26 passed)
- [x] tests/xai_tests/unit test_blockchain.py (61 passed)
- [x] tests/xai_tests/unit test_blockchain_reorg.py (18 passed)
- [x] tests/xai_tests/unit test_blockchain_storage_compression.py (11 passed)
- [x] tests/xai_tests/unit test_blockchain_storage_index.py (13 passed)
- [x] tests/xai_tests/unit test_blockchain_storage_metrics.py (1 passed)
- [x] tests/xai_tests/unit test_blockchain_trade_orders.py (3 passed)
- [x] tests/xai_tests/unit test_blockchain_trading_mixin.py (25 passed)
- [x] tests/xai_tests/unit test_blockchain_wal.py (48 passed)
- [x] tests/xai_tests/unit test_blockchain_work_and_size.py (2 passed)
- [x] tests/xai_tests/unit test_block_explorer_coverage.py (74 passed)
- [x] tests/xai_tests/unit test_block_header.py (2 passed)
- [x] tests/xai_tests/unit test_block_index.py (17 passed)
- [x] tests/xai_tests/unit test_block_merkle_proof.py (15 passed)
- [x] tests/xai_tests/unit test_block_processor.py (41 passed)
- [x] tests/xai_tests/unit test_block.py (3 passed)
- [x] tests/xai_tests/unit test_burning_api_endpoints.py (3 passed)
- [x] tests/xai_tests/unit test_centralized_validation.py (44 passed)
- [x] tests/xai_tests/unit test_chain_reorg_mempool.py (5 passed)
- [x] tests/xai_tests/unit test_checkpoint_corruption.py (8 passed)
- [x] tests/xai_tests/unit test_checkpoint_payload.py (2 passed)
- [x] tests/xai_tests/unit test_checkpoint_peer_diversity.py (1 passed)
- [x] tests/xai_tests/unit test_checkpoint_peer_fallback.py (1 passed)
- [x] tests/xai_tests/unit test_checkpoint_peer_request.py (1 passed; 1 warning)
- [x] tests/xai_tests/unit test_checkpoint_protection.py (10 passed)
- [x] tests/xai_tests/unit test_checkpoint_signature_validation.py (1 passed)
- [x] tests/xai_tests/unit test_checkpoints.py (14 passed)
- [x] tests/xai_tests/unit test_checkpoint_sync_file_load.py (5 passed)
- [x] tests/xai_tests/unit test_checkpoint_sync_manager.py (5 passed)
- [x] tests/xai_tests/unit test_checkpoint_sync_payload.py (2 passed)
- [x] tests/xai_tests/unit test_checkpoint_work_validation.py (1 passed)
- [x] tests/xai_tests/unit test_checkpoint_sync.py (2 passed)
- [x] tests/xai_tests/unit test_chunked_sync.py (22 passed)
- [x] tests/xai_tests/unit test_circuit_breaker.py (2 passed)
- [x] tests/xai_tests/unit test_cli_completion.py (1 passed)
- [x] tests/xai_tests/unit test_cli_errors.py (14 passed)
- [x] tests/xai_tests/unit test_cli_tooling.py (2 passed)
- [x] tests/xai_tests/unit test_coinbase_validation.py (7 passed)
- [x] tests/xai_tests/unit test_community_standards_compliance.py (32 passed)
- [x] tests/xai_tests/unit test_compact_block.py (22 passed)
- [x] tests/xai_tests/unit test_concentrated_liquidity_precision.py (37 passed)
- [x] tests/xai_tests/unit test_config_env.py (2 passed)
- [x] tests/xai_tests/unit test_config_manager_coverage.py (121 passed)
- [x] tests/xai_tests/unit test_consensus_mixin.py (3 passed)
- [x] tests/xai_tests/unit test_consensus.py (28 passed)
- [x] tests/xai_tests/unit test_contract_gas.py (13 passed)
- [x] tests/xai_tests/unit test_contract_governance.py (2 passed)
- [x] tests/xai_tests/unit test_contract_metadata_api.py (3 passed; 6 warnings)
- [x] tests/xai_tests/unit test_contract_metrics.py (1 passed)
- [x] tests/xai_tests/unit test_cors_policy_manager.py (1 passed; 3 warnings)
- [x] tests/xai_tests/unit test_cosmos_light_client.py (22 passed)
- [x] tests/xai_tests/unit test_cross_chain_and_fraud.py (6 passed)
- [x] tests/xai_tests/unit test_crypto_deposit_manager.py (4 passed)
- [x] tests/xai_tests/unit test_crypto_deposit_monitor.py (5 passed)
- [x] tests/xai_tests/unit test_cryptographic_randomness.py (6 passed)
- [x] tests/xai_tests/unit test_crypto_utils_signature_ranges.py (6 passed)
- [x] tests/xai_tests/unit test_crypto_vectors.py (3 passed)
- [x] tests/xai_tests/unit test_csprng.py (2 passed)
- [x] tests/xai_tests/unit test_daily_withdrawal_limits.py (48 passed)
- [x] tests/xai_tests/unit test_ddos_memory_limits.py (18 passed)
- [x] tests/xai_tests/unit test_ddos_protector.py (4 passed)
- [x] tests/xai_tests/unit test_ddos_stress.py (11 passed)
- [x] tests/xai_tests/unit test_defi_safety.py (3 passed)
- [x] tests/xai_tests/unit test_defi_staking.py (12 passed)
- [x] tests/xai_tests/unit test_double_sign_detector.py (4 passed)
- [x] tests/xai_tests/unit test_downtime_and_fork_protection.py (3 passed)
- [x] tests/xai_tests/unit test_ecdsa_edge_cases.py (25 passed)
- [x] tests/xai_tests/unit test_eclipse_protector.py (3 passed)
- [x] tests/xai_tests/unit test_emergency_pause.py (3 passed)
- [x] tests/xai_tests/unit test_encrypted_api_key_store.py (28 passed)
- [x] tests/xai_tests/unit test_enhanced_cli_genesis.py (3 passed)
- [x] tests/xai_tests/unit test_error_detection_comprehensive.py (73 passed)
- [x] tests/xai_tests/unit test_error_detection.py (26 passed)
- [x] tests/xai_tests/unit test_error_handlers_comprehensive.py (73 passed)
- [x] tests/xai_tests/unit test_error_handlers_simple.py (16 passed)
- [x] tests/xai_tests/unit test_error_recovery_comprehensive.py (45 passed)
- [x] tests/xai_tests/unit test_error_recovery_simple.py (15 passed)
- [x] tests/xai_tests/unit test_evm_builtin_tokens.py (7 passed)
- [x] tests/xai_tests/unit test_evm_bytecode_cache.py (17 passed)
- [x] tests/xai_tests/unit test_evm_call_execution.py (16 passed)
- [x] tests/xai_tests/unit test_evm_call_memory.py (2 passed)
- [x] tests/xai_tests/unit test_evm_create_opcodes.py (20 passed)
- [x] tests/xai_tests/unit test_evm_delegatecall.py (2 passed)
- [x] tests/xai_tests/unit test_evm_interpreter.py (58 passed)
- [x] tests/xai_tests/unit test_evm_jump_dest_cache.py (16 passed)
- [x] tests/xai_tests/unit test_evm_light_client.py (22 passed)
- [x] tests/xai_tests/unit test_evm_point_evaluation_precompile.py (6 passed)
- [x] tests/xai_tests/unit test_evm_precompiles_basic.py (15 passed)
- [x] tests/xai_tests/unit test_evm_primitives.py (7 passed)
- [x] tests/xai_tests/unit test_exchange_coverage.py (75 passed)
- [x] tests/xai_tests/unit test_exchange_simple.py (17 passed)
- [x] tests/xai_tests/unit test_exchange_slippage.py (1 passed)
- [x] tests/xai_tests/unit test_exchange_validation.py (11 passed)
- [x] tests/xai_tests/unit test_explorer_backend_coverage.py (93 passed)
- [x] tests/xai_tests/unit test_explorer_search.py (10 passed)
- [x] tests/xai_tests/unit test_extreme_difficulty.py (28 passed)
- [x] tests/xai_tests/unit test_fee_adjuster.py (38 passed)
- [x] tests/xai_tests/unit test_fee_ordering.py (13 passed)
- [x] tests/xai_tests/unit test_finality_metrics.py (3 passed)
- [x] tests/xai_tests/unit test_find_uncovered_lines.py (5 passed)
- [x] tests/xai_tests/unit test_flash_loan_protection.py (5 passed)
- [x] tests/xai_tests/unit test_flash_loans_attacks.py (4 passed)
- [x] tests/xai_tests/unit test_flash_loans.py (5 passed)
- [x] tests/xai_tests/unit test_flask_secret_manager.py (19 passed)
- [x] tests/xai_tests/unit test_fork_detector.py (2 passed)
- [x] tests/xai_tests/unit test_fork_manager.py (3 passed)
- [x] tests/xai_tests/unit test_fraud_detection.py (69 passed)
- [x] tests/xai_tests/unit test_fraud_proofs.py (4 passed)
- [x] tests/xai_tests/unit test_gamification.py (46 passed)
- [x] tests/xai_tests/unit test_gas_estimator_accuracy.py (16 passed)
- [x] tests/xai_tests/unit test_generate_premine_coverage.py (62 passed)
- [x] tests/xai_tests/unit test_generate_premine_simple.py (9 passed)
- [x] tests/xai_tests/unit test_geoip_resolver.py (45 passed)
- [x] tests/xai_tests/unit test_gossip_validator.py (4 passed)
- [x] tests/xai_tests/unit test_governance_execution.py (5 passed)
- [x] tests/xai_tests/unit test_governance_lifecycle.py (13 passed)
- [x] tests/xai_tests/unit test_governance.py (85 passed)
- [x] tests/xai_tests/unit test_governance_transactions.py (17 passed)
- [x] tests/xai_tests/unit test_hardware_wallet_integration.py (4 passed)
- [x] tests/xai_tests/unit test_hardware_wallet_provider.py (5 passed)
- [x] tests/xai_tests/unit test_hardware_wallet_signatures.py (1 passed)
- [x] tests/xai_tests/unit test_hd_wallet_accounts.py (3 passed)
- [x] tests/xai_tests/unit test_hd_wallet_passphrase_edges.py (4 passed)
- [x] tests/xai_tests/unit test_hsm.py (3 passed)
- [x] tests/xai_tests/unit test_impermanent_loss.py (3 passed)
- [x] tests/xai_tests/unit test_insurance_fund.py (3 passed)
- [x] tests/xai_tests/unit test_invariants.py (23 passed)
- [x] tests/xai_tests/unit test_jwt_auth_manager_cleanup.py (17 passed)
- [x] tests/xai_tests/unit test_jwt_auth_manager_expiration.py (10 passed)
- [x] tests/xai_tests/unit test_jwt_auth_manager.py (3 passed)
- [x] tests/xai_tests/unit test_jwt_blacklist_cleanup.py (18 passed)
- [x] tests/xai_tests/unit test_jwt_expiration.py (14 passed)
- [x] tests/xai_tests/unit test_lending_dust_loss.py (15 passed)
- [x] tests/xai_tests/unit test_light_client.py (1 passed)
- [x] tests/xai_tests/unit test_liquidity_locker.py (2 passed)
- [x] tests/xai_tests/unit test_malformed_blocks.py (21 passed)
- [x] tests/xai_tests/unit test_margin_engine.py (4 passed)
- [x] tests/xai_tests/unit test_mempool_concurrent_double_spend.py (7 passed; 1 skipped)
- [x] tests/xai_tests/unit test_mempool_eviction.py (19 passed)
- [x] tests/xai_tests/unit test_mempool_eviction_stress.py (9 passed)
- [x] tests/xai_tests/unit test_mempool_lazy_deletion.py (15 passed)
- [x] tests/xai_tests/unit test_mempool_mixin.py (23 passed)
- [x] tests/xai_tests/unit test_merchant_payment_processor.py (24 passed)
- [x] tests/xai_tests/unit test_merkle_proof_comprehensive.py (17 passed)
- [x] tests/xai_tests/unit test_merkle_proof_verification.py (13 passed)
- [x] tests/xai_tests/unit test_metrics.py (2 passed)
- [x] tests/xai_tests/unit test_mev_and_pool_managers.py (4 passed)
- [x] tests/xai_tests/unit test_mev_front_running_protection.py (6 passed)
- [x] tests/xai_tests/unit test_mining_algorithm.py (37 passed)
- [x] tests/xai_tests/unit test_mining_bonuses.py (38 passed)
- [x] tests/xai_tests/unit test_mining_economic_metrics.py (1 passed)
- [x] tests/xai_tests/unit test_mining_guardrails.py (3 passed)
- [x] tests/xai_tests/unit test_mining_mixin.py (2 passed)
- [x] tests/xai_tests/unit test_mnemonic_qr_backup.py (5 passed)
- [x] tests/xai_tests/unit test_mobile_sync_manager.py (25 passed)
- [x] tests/xai_tests/unit test_mobile_telemetry.py (38 passed)
- [x] tests/xai_tests/unit test_mobile_wallet_bridge.py (2 passed)
- [x] tests/xai_tests/unit test_module_attachment_guard.py (8 passed)
- [x] tests/xai_tests/unit test_mpc_dkg.py (3 passed)
- [x] tests/xai_tests/unit test_multi_sig_treasury.py (56 passed)
- [x] tests/xai_tests/unit test_multisig_wallet_nonce.py (4 passed)
- [x] tests/xai_tests/unit test_node_api_additional_coverage.py (79 passed)
- [x] tests/xai_tests/unit test_node_api.py (133 passed)

## Testnet Infrastructure Tasks

### Completed

- [x] Node running and producing blocks
- [x] RPC API endpoint (testnet-rpc.xaiblockchain.com)
- [x] Faucet API endpoint (testnet-faucet.xaiblockchain.com)
- [x] Explorer API endpoint (testnet-explorer.xaiblockchain.com)
- [x] Prometheus metrics collection
- [x] Grafana monitoring dashboards with anonymous access
- [x] SSL certificates for all endpoints
- [x] Automated daily snapshots
- [x] fail2ban security
- [x] nginx rate limiting
- [x] Log rotation

### High Priority - User Facing

- [x] Deploy block explorer web UI (https://testnet-explorer.xaiblockchain.com)
- [x] Deploy faucet web UI (https://testnet-faucet.xaiblockchain.com)
- [x] Deploy documentation site (https://docs.xaiblockchain.com)
- [x] Create public status page (https://status.xaiblockchain.com)
- [x] Publish genesis.json (https://artifacts.xaiblockchain.com/genesis.json)
- [x] Publish seed node list (https://artifacts.xaiblockchain.com/seeds.json)
- [x] Add WebSocket subscriptions (wss://ws.xaiblockchain.com)

### Medium Priority - Developer Experience

- [x] Deploy OpenAPI/Swagger UI (https://api.xaiblockchain.com)
- [ ] Publish SDKs to package registries - npm for TypeScript, pub.dev for Flutter, etc
- [x] Create chain registry entry (https://artifacts.xaiblockchain.com/chain.json)
- [x] Add GraphQL endpoint (https://api.xaiblockchain.com/graphql)
- [x] Network stats page (https://stats.xaiblockchain.com)

### Lower Priority - Advanced Features

- [x] Run multiple validator nodes - Node 2 running on port 8555 with address TXAI759460929623A1A488388CED4054734BCF1F835D
- [x] Deploy archive node - primary node stores full historical state
- [x] Set up indexer service - SQLite indexer at https://api.xaiblockchain.com/indexer
- [ ] Geographic distribution - requires additional servers in other regions
- [x] Load balanced RPC - nginx upstream configured with failover to Node 2

### Testnet Hardening & Professionalization

- [x] Firewall P2P port (8333) to VPN only (10.10.0.0/24)
- [x] Publish peers.json with VPN addresses (https://artifacts.xaiblockchain.com/peers.json)
- [x] Publish snapshot artifacts with checksums (https://artifacts.xaiblockchain.com/snapshots/latest.json)
- [x] Configure Grafana alerts (node down, chain stalled, mempool, disk, CPU)
- [x] Host hardening (SSH key-only, MaxAuthTries=3, PermitRootLogin=no)
- [x] fail2ban active with 173+ banned IPs
- [x] Unattended upgrades enabled
- [x] Set up encrypted offsite backups (~/.validator-backups/keys/xai-backup.sh, daily cron at 3 AM)
- [x] Document incident response runbook (docs/INCIDENT_RESPONSE_RUNBOOK.md)

#### Hardening Implementation Notes (2026-01-03)

**Firewall Configuration:**
- P2P port 8333 restricted to VPN (10.10.0.0/24) only
- RPC (8545), WebSocket (8765), Explorer (8080) remain public for API access
- Secondary node peers over VPN (10.10.0.3 ↔ 10.10.0.4)

**Published Artifacts:**
- `https://artifacts.xaiblockchain.com/peers.json`
- `https://artifacts.xaiblockchain.com/snapshots/latest.json`

**Security Hardening:**
- SSH: Key-only, no root, MaxAuthTries=3
- fail2ban: Active with 170+ banned IPs
- Unattended upgrades enabled

**Encrypted Backups:**
- Script: `~/.validator-backups/keys/xai-backup.sh`
- GPG AES256 encrypted
- Daily cron at 3 AM

## Details

## Goal
Prepare the repository documentation for a public testnet by removing non-standard materials, tightening language, and ensuring the remaining docs match the code and current workflows.

## Audit Tasks
- [x] Inventory documentation and classify keep/remove; record decisions and task list
- [x] Remove non-customary documentation (internal reports, archives, marketing, duplicates)
- [x] Update top-level docs for accuracy and concision (README, CHANGELOG, CODE_OF_CONDUCT, SECURITY, CONTRIBUTING)
- [x] Review remaining docs for accuracy (quickstart, testnet, API, protocol) and update or remove
- [x] Final sweep for prohibited language, broken links, and inconsistent instructions
