"""
XAI Blockchain - Error Recovery Usage Examples

Examples and test scenarios for error recovery system.
"""

from xai.core.error_recovery import (
    ErrorRecoveryManager,
    create_recovery_manager,
    CircuitBreaker,
    RetryStrategy,
    CorruptionDetector,
)
from xai.core.error_recovery_integration import (
    integrate_recovery_with_blockchain,
    add_recovery_to_node,
    RecoveryEnabledBlockchain,
    RecoveryScheduler,
)


# Example 1: Basic Integration
def example_basic_integration():
    """
    Basic error recovery integration
    """
    from xai.core.blockchain import Blockchain

    blockchain = Blockchain()
    recovery_manager = create_recovery_manager(blockchain)

    print("Recovery manager created")
    print(f"State: {recovery_manager.state.value}")

    # Create initial backup
    backup_path = recovery_manager.create_checkpoint("initial")
    print(f"Initial backup: {backup_path}")

    # Get status
    status = recovery_manager.get_recovery_status()
    print(f"Health score: {status['health']['score']}")


# Example 2: Using Circuit Breakers
def example_circuit_breaker():
    """
    Circuit breaker example
    """
    # Create circuit breaker
    breaker = CircuitBreaker(failure_threshold=3, timeout=60, success_threshold=2)

    # Define a flaky operation
    call_count = [0]

    def flaky_operation():
        call_count[0] += 1
        if call_count[0] < 5:
            raise Exception("Operation failed")
        return "Success"

    # Execute through circuit breaker
    for i in range(10):
        success, result, error = breaker.call(flaky_operation)

        print(f"Attempt {i + 1}: success={success}, state={breaker.state.value}")

        if success:
            print(f"  Result: {result}")
        elif error:
            print(f"  Error: {error}")


# Example 3: Retry with Exponential Backoff
def example_retry_strategy():
    """
    Retry strategy example
    """
    retry = RetryStrategy(max_retries=5, base_delay=1.0, max_delay=30.0, exponential_base=2.0)

    # Simulate flaky network call
    call_count = [0]

    def flaky_network_call():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Network timeout")
        return {"data": "success"}

    # Execute with retry
    success, result, error = retry.execute(flaky_network_call)

    if success:
        print(f"Succeeded after {call_count[0]} attempts: {result}")
    else:
        print(f"Failed: {error}")


# Example 4: Corruption Detection and Recovery
def example_corruption_recovery():
    """
    Corruption detection and recovery example
    """
    from xai.core.blockchain import Blockchain

    # Create blockchain with some blocks
    blockchain = Blockchain()

    # Add recovery
    recovery_manager = create_recovery_manager(blockchain)

    # Create backup
    recovery_manager.create_checkpoint("before_corruption")

    # Simulate corruption (for testing only!)
    # blockchain.chain[0].hash = "corrupted_hash"

    # Detect corruption
    is_corrupted, issues = recovery_manager.corruption_detector.detect_corruption(blockchain)

    print(f"Corrupted: {is_corrupted}")
    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")

    # Recover if corrupted
    if is_corrupted:
        success, error = recovery_manager.handle_corruption()
        if success:
            print("Recovery successful!")
        else:
            print(f"Recovery failed: {error}")


# Example 5: Graceful Shutdown
def example_graceful_shutdown():
    """
    Graceful shutdown example
    """
    from xai.core.blockchain import Blockchain

    # Create blockchain
    blockchain = Blockchain()
    recovery_manager = create_recovery_manager(blockchain)

    # Perform graceful shutdown
    recovery_manager.graceful_shutdown("testing")

    print("Shutdown complete")


# Example 6: Health Monitoring
def example_health_monitoring():
    """
    Health monitoring example
    """
    from xai.core.blockchain import Blockchain
    import time

    # Create blockchain
    blockchain = Blockchain()
    recovery_manager = create_recovery_manager(blockchain)

    # Monitor health over time
    for i in range(5):
        # Update metrics
        recovery_manager.health_monitor.update_metrics(blockchain)

        # Get health status
        health = recovery_manager.health_monitor.get_health_status()

        print(f"\nIteration {i + 1}:")
        print(f"  Status: {health['status']}")
        print(f"  Score: {health['score']:.1f}")
        print(f"  Blocks: {health['metrics']['blocks_mined']}")
        print(f"  Mempool: {health['metrics']['mempool_size']}")

        time.sleep(1)


# Example 7: Full Node Integration
def example_node_integration():
    """
    Full node integration example
    """
    # Note: This requires a running node instance

    # from node import BlockchainNode
    #
    # # Create node
    # node = BlockchainNode()
    #
    # # Add error recovery
    # recovery_manager = add_recovery_to_node(node)
    #
    # # Now the node has:
    # # - Automatic backups
    # # - Corruption detection
    # # - Circuit breakers
    # # - Health monitoring
    # # - Recovery API endpoints
    #
    # # Access recovery features
    # status = node.recovery_manager.get_recovery_status()
    # health = node.recovery_manager.get_health_status()
    #
    # # Run node
    # node.run()

    print("See code comments for full node integration example")


# Example 8: Recovery-Enabled Blockchain Wrapper
def example_recovery_wrapper():
    """
    Using RecoveryEnabledBlockchain wrapper
    """
    from xai.core.blockchain import Blockchain, Transaction
    from xai.core.wallet import Wallet

    # Create base blockchain
    base_blockchain = Blockchain()

    # Wrap with recovery
    blockchain = RecoveryEnabledBlockchain(base_blockchain)

    # Use blockchain normally - recovery is automatic
    wallet = Wallet()

    # Add transaction with automatic validation and recovery
    tx = Transaction("COINBASE", wallet.address, 100.0)
    tx.txid = tx.calculate_hash()

    success = blockchain.add_transaction(tx)
    print(f"Transaction added: {success}")

    # Validate chain with automatic corruption detection
    is_valid = blockchain.validate_chain()
    print(f"Chain valid: {is_valid}")

    # Get recovery status
    recovery_status = blockchain.get_recovery_status()
    print(f"Recovery state: {recovery_status['state']}")

    # Get health status
    health = blockchain.get_health_status()
    print(f"Health score: {health['score']:.1f}")


# Example 9: API Endpoint Usage
def example_api_usage():
    """
    Using recovery API endpoints
    """
    import requests

    base_url = "http://localhost:12001"

    # Get recovery status
    response = requests.get(f"{base_url}/recovery/status", timeout=30)
    print(f"Recovery Status: {response.json()}")

    # Get health metrics
    response = requests.get(f"{base_url}/recovery/health", timeout=30)
    print(f"Health: {response.json()}")

    # Get circuit breaker states
    response = requests.get(f"{base_url}/recovery/circuit-breakers", timeout=30)
    print(f"Circuit Breakers: {response.json()}")

    # Create manual backup
    response = requests.post(f"{base_url}/recovery/backup/create", json={"name": "manual_backup"}, timeout=30)
    print(f"Backup Created: {response.json()}")

    # List backups
    response = requests.get(f"{base_url}/recovery/backups", timeout=30)
    print(f"Available Backups: {response.json()}")

    # Check for corruption
    response = requests.post(f"{base_url}/recovery/corruption/check", timeout=30)
    print(f"Corruption Check: {response.json()}")

    # Get error log
    response = requests.get(f"{base_url}/recovery/errors?limit=10", timeout=30)
    print(f"Recent Errors: {response.json()}")


# Example 10: Testing Recovery Scenarios
def test_recovery_scenarios():
    """
    Test various recovery scenarios
    """
    from xai.core.blockchain import Blockchain

    print("\n=== Testing Error Recovery Scenarios ===\n")

    # Scenario 1: Normal operation
    print("Scenario 1: Normal Operation")
    blockchain = Blockchain()
    recovery_manager = create_recovery_manager(blockchain)
    print(f"  State: {recovery_manager.state.value}")
    print(f"  Health: {recovery_manager.health_monitor.get_health_status()['score']:.1f}")

    # Scenario 2: Transaction validation failure
    print("\nScenario 2: Invalid Transaction")
    from xai.core.blockchain import Transaction

    invalid_tx = Transaction("INVALID", "RECIPIENT", -100.0)  # Negative amount
    success = recovery_manager.handle_invalid_transaction(invalid_tx)
    print(f"  Handled: {success}")

    # Scenario 3: Backup and restore
    print("\nScenario 3: Backup and Restore")
    backup_path = recovery_manager.create_checkpoint("test")
    print(f"  Backup created: {backup_path}")

    backups = recovery_manager.backup_manager.list_backups()
    print(f"  Available backups: {len(backups)}")

    # Scenario 4: Circuit breaker protection
    print("\nScenario 4: Circuit Breaker")
    breaker = recovery_manager.circuit_breakers["mining"]
    print(f"  Initial state: {breaker.state.value}")

    # Simulate failures
    for i in range(6):
        breaker._on_failure()

    print(f"  After failures: {breaker.state.value}")

    # Reset
    breaker.reset()
    print(f"  After reset: {breaker.state.value}")

    # Scenario 5: Health monitoring
    print("\nScenario 5: Health Monitoring")
    recovery_manager.health_monitor.update_metrics(blockchain)
    health = recovery_manager.health_monitor.get_health_status()
    print(f"  Status: {health['status']}")
    print(f"  Score: {health['score']:.1f}")

    # Scenario 6: Error logging
    print("\nScenario 6: Error Logging")
    from error_recovery import ErrorSeverity

    recovery_manager._log_error("test", "Test error", ErrorSeverity.MEDIUM)
    recent_errors = list(recovery_manager.error_log)[-5:]
    print(f"  Recent errors: {len(recent_errors)}")

    print("\n=== All Tests Complete ===\n")


# Main execution
if __name__ == "__main__":
    print("XAI Blockchain - Error Recovery Examples\n")

    # Run examples
    print("\n--- Example 1: Basic Integration ---")
    example_basic_integration()

    print("\n--- Example 2: Circuit Breaker ---")
    example_circuit_breaker()

    print("\n--- Example 3: Retry Strategy ---")
    example_retry_strategy()

    print("\n--- Example 4: Corruption Recovery ---")
    example_corruption_recovery()

    print("\n--- Example 5: Graceful Shutdown ---")
    example_graceful_shutdown()

    print("\n--- Example 6: Health Monitoring ---")
    example_health_monitoring()

    print("\n--- Example 7: Node Integration ---")
    example_node_integration()

    print("\n--- Example 8: Recovery Wrapper ---")
    example_recovery_wrapper()

    # Run tests
    test_recovery_scenarios()

    print("\nAll examples complete!")
