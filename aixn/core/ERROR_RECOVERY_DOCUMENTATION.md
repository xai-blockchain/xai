# XAI Blockchain - Error Recovery and Resilience System

Comprehensive error handling, recovery, and resilience features for the XAI blockchain.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Components](#components)
5. [Integration Guide](#integration-guide)
6. [API Endpoints](#api-endpoints)
7. [Usage Examples](#usage-examples)
8. [Configuration](#configuration)
9. [Best Practices](#best-practices)

## Overview

The Error Recovery System provides enterprise-grade resilience for the XAI blockchain, protecting against:

- **Database corruption** - Automatic detection and rollback
- **Network partitions** - Graceful degradation and recovery
- **Invalid data** - Transaction and block validation
- **System failures** - Circuit breakers and automatic retry
- **Resource exhaustion** - Health monitoring and alerts
- **Data loss** - Automatic backups and restoration

## Features

### 1. Circuit Breaker Pattern

Prevents cascading failures by breaking the circuit when a service is experiencing issues.

```python
from error_recovery import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,    # Open after 5 failures
    timeout=60,             # Wait 60s before retry
    success_threshold=2     # Close after 2 successes
)

success, result, error = breaker.call(risky_operation, *args)
```

**States:**
- **CLOSED** - Normal operation
- **OPEN** - Failing, rejecting requests
- **HALF_OPEN** - Testing recovery

### 2. Automatic Retry with Exponential Backoff

Retry failed operations with increasing delays.

```python
from error_recovery import RetryStrategy

retry = RetryStrategy(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0
)

success, result, error = retry.execute(flaky_operation)
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: 1s delay
- Attempt 3: 2s delay
- Attempt 4: 4s delay

### 3. Blockchain Backup and Restoration

Automatic and manual blockchain backups.

```python
from error_recovery import BlockchainBackup

backup_manager = BlockchainBackup()

# Create backup
backup_path = backup_manager.create_backup(blockchain, "checkpoint_1")

# List backups
backups = backup_manager.list_backups()

# Restore backup
success, data, error = backup_manager.restore_backup(backup_path)
```

**Backup Contents:**
- Complete blockchain
- UTXO set
- Pending transactions
- Difficulty and metadata

### 4. Corruption Detection

Comprehensive blockchain integrity checks.

```python
from error_recovery import CorruptionDetector

detector = CorruptionDetector()

is_corrupted, issues = detector.detect_corruption(blockchain)

if is_corrupted:
    for issue in issues:
        print(f"Issue: {issue}")
```

**Checks Performed:**
- Hash integrity
- Chain continuity
- UTXO consistency
- Supply validation
- Transaction validity

### 5. Health Monitoring

Real-time blockchain health tracking.

```python
from error_recovery import HealthMonitor

monitor = HealthMonitor()

monitor.update_metrics(blockchain, node)
health = monitor.get_health_status()

print(f"Status: {health['status']}")
print(f"Score: {health['score']}")
```

**Health Metrics:**
- Last block time
- Blocks mined
- Transaction throughput
- Network peers
- Mempool size
- Error rate

**Health Scores:**
- 80-100: Healthy
- 60-79: Degraded
- 40-59: Warning
- 0-39: Critical

### 6. Error Recovery Manager

Main coordinator for all recovery operations.

```python
from error_recovery import create_recovery_manager

recovery_manager = create_recovery_manager(blockchain, node)

# Get status
status = recovery_manager.get_recovery_status()

# Handle corruption
success, error = recovery_manager.handle_corruption()

# Graceful shutdown
recovery_manager.graceful_shutdown("maintenance")
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Error Recovery Manager                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Circuit   │  │    Retry     │  │   Health   │ │
│  │  Breakers   │  │   Strategy   │  │  Monitor   │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Backup    │  │  Corruption  │  │   Error    │ │
│  │   Manager   │  │   Detector   │  │   Logger   │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │        Blockchain              │
        │                                │
        │  - Chain                       │
        │  - UTXO Set                    │
        │  - Pending Transactions        │
        │  - Validation                  │
        └────────────────────────────────┘
```

## Components

### ErrorRecoveryManager

Main class coordinating all recovery operations.

**Methods:**
- `wrap_operation(operation, func, *args, **kwargs)` - Wrap critical operations
- `handle_corruption(force_rollback=False)` - Handle blockchain corruption
- `handle_network_partition()` - Handle network issues
- `handle_invalid_block(block)` - Handle invalid blocks
- `handle_invalid_transaction(transaction)` - Handle invalid transactions
- `graceful_shutdown(reason)` - Perform graceful shutdown
- `create_checkpoint(name)` - Create backup checkpoint
- `get_recovery_status()` - Get recovery system status

### CircuitBreaker

Implements circuit breaker pattern for fault tolerance.

**Methods:**
- `call(func, *args, **kwargs)` - Execute function through circuit breaker
- `reset()` - Manually reset circuit breaker

**States:**
- `CLOSED` - Normal operation
- `OPEN` - Rejecting requests
- `HALF_OPEN` - Testing recovery

### RetryStrategy

Implements retry logic with exponential backoff.

**Methods:**
- `execute(func, *args, **kwargs)` - Execute with retry logic

### BlockchainBackup

Manages blockchain backups and restoration.

**Methods:**
- `create_backup(blockchain, name)` - Create backup
- `restore_backup(backup_path)` - Restore from backup
- `list_backups()` - List available backups
- `cleanup_old_backups(keep_count)` - Remove old backups

### CorruptionDetector

Detects blockchain corruption.

**Methods:**
- `detect_corruption(blockchain)` - Run all corruption checks

**Checks:**
- Hash integrity
- Chain continuity
- UTXO consistency
- Supply validation
- Transaction validity

### HealthMonitor

Monitors blockchain health metrics.

**Methods:**
- `update_metrics(blockchain, node)` - Update health metrics
- `get_health_status()` - Get current health status

## Integration Guide

### Basic Integration

```python
from error_recovery_integration import integrate_recovery_with_blockchain
from blockchain import Blockchain

# Create blockchain
blockchain = Blockchain()

# Add error recovery
recovery_manager = integrate_recovery_with_blockchain(blockchain)

# Use blockchain normally
# Recovery is automatic
```

### Node Integration

```python
from error_recovery_integration import add_recovery_to_node
from node import BlockchainNode

# Create node
node = BlockchainNode()

# Add error recovery
recovery_manager = add_recovery_to_node(node)

# Run node
# Recovery is automatic, API endpoints added
node.run()
```

### Wrapper Pattern

```python
from error_recovery_integration import RecoveryEnabledBlockchain
from blockchain import Blockchain

# Create base blockchain
base_blockchain = Blockchain()

# Wrap with recovery
blockchain = RecoveryEnabledBlockchain(base_blockchain)

# Use blockchain with automatic recovery
blockchain.mine_block(miner_address)
blockchain.add_transaction(tx)
blockchain.validate_chain()
```

### Manual Integration

```python
from error_recovery import ErrorRecoveryManager

# Create recovery manager
recovery_manager = ErrorRecoveryManager(blockchain, node)

# Wrap critical operations
success, result, error = recovery_manager.wrap_operation(
    'mining',
    blockchain.mine_pending_transactions,
    miner_address
)

if not success:
    print(f"Mining failed: {error}")
```

## API Endpoints

### GET /recovery/status

Get error recovery system status.

**Response:**
```json
{
  "success": true,
  "recovery_status": {
    "state": "healthy",
    "recovery_in_progress": false,
    "health": {
      "status": "healthy",
      "score": 95.0
    },
    "circuit_breakers": {
      "mining": "closed",
      "validation": "closed"
    },
    "backups_available": 10
  }
}
```

### GET /recovery/health

Get blockchain health metrics.

**Response:**
```json
{
  "success": true,
  "health": {
    "status": "healthy",
    "score": 95.0,
    "metrics": {
      "last_block_time": 1234567890,
      "blocks_mined": 1000,
      "mempool_size": 50,
      "network_peers": 5
    }
  }
}
```

### GET /recovery/circuit-breakers

Get circuit breaker states.

**Response:**
```json
{
  "success": true,
  "circuit_breakers": {
    "mining": {
      "state": "closed",
      "failure_count": 0,
      "success_count": 0
    },
    "validation": {
      "state": "closed",
      "failure_count": 0,
      "success_count": 0
    }
  }
}
```

### POST /recovery/circuit-breakers/{name}/reset

Reset specific circuit breaker.

**Response:**
```json
{
  "success": true,
  "message": "Circuit breaker mining reset"
}
```

### GET /recovery/backups

List available backups.

**Response:**
```json
{
  "success": true,
  "count": 10,
  "backups": [
    {
      "name": "backup_1234567890.json",
      "path": "data/backups/backup_1234567890.json",
      "timestamp": 1234567890,
      "chain_height": 1000,
      "size": 1024000
    }
  ]
}
```

### POST /recovery/backup/create

Create manual backup.

**Request:**
```json
{
  "name": "manual_backup"
}
```

**Response:**
```json
{
  "success": true,
  "backup_path": "data/backups/manual_backup.json",
  "message": "Backup created successfully"
}
```

### POST /recovery/backup/restore

Restore from backup.

**Request:**
```json
{
  "backup_name": "backup_1234567890.json"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Restored from backup: backup_1234567890.json",
  "chain_height": 1000
}
```

### POST /recovery/corruption/check

Check for blockchain corruption.

**Response:**
```json
{
  "success": true,
  "is_corrupted": false,
  "issue_count": 0,
  "issues": []
}
```

### POST /recovery/corruption/fix

Attempt to fix blockchain corruption.

**Request:**
```json
{
  "force_rollback": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Corruption fixed successfully"
}
```

### GET /recovery/errors

Get recent errors.

**Query Parameters:**
- `limit` (default: 50) - Number of errors to return

**Response:**
```json
{
  "success": true,
  "count": 5,
  "errors": [
    {
      "timestamp": 1234567890,
      "operation": "mining",
      "error": "Block validation failed",
      "severity": "medium"
    }
  ]
}
```

### GET /recovery/actions

Get recent recovery actions.

**Query Parameters:**
- `limit` (default: 50) - Number of actions to return

**Response:**
```json
{
  "success": true,
  "count": 3,
  "actions": [
    {
      "timestamp": 1234567890,
      "type": "corruption_recovery",
      "status": "success",
      "details": "Restored from backup: backup_1234567890.json"
    }
  ]
}
```

### POST /recovery/shutdown

Perform graceful shutdown.

**Request:**
```json
{
  "reason": "maintenance"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Graceful shutdown initiated"
}
```

### POST /recovery/network/reconnect

Handle network partition.

**Response:**
```json
{
  "success": true,
  "message": "Network partition handled"
}
```

## Usage Examples

### Example 1: Wrap Mining Operation

```python
recovery_manager = create_recovery_manager(blockchain, node)

# Wrap mining with error handling
success, block, error = recovery_manager.wrap_operation(
    'mining',
    blockchain.mine_pending_transactions,
    miner_address
)

if success:
    print(f"Block mined: {block.hash}")
else:
    print(f"Mining failed: {error}")
```

### Example 2: Handle Corruption

```python
# Check for corruption
is_corrupted, issues = recovery_manager.corruption_detector.detect_corruption(blockchain)

if is_corrupted:
    print(f"Corruption detected: {len(issues)} issues")

    # Attempt recovery
    success, error = recovery_manager.handle_corruption()

    if success:
        print("Corruption fixed!")
    else:
        print(f"Recovery failed: {error}")
```

### Example 3: Create Checkpoint

```python
# Create backup before major operation
checkpoint = recovery_manager.create_checkpoint("before_upgrade")

# Perform risky operation
try:
    perform_upgrade()
except Exception as e:
    # Restore from checkpoint if failed
    recovery_manager.backup_manager.restore_backup(checkpoint)
```

### Example 4: Monitor Health

```python
# Update health metrics
recovery_manager.health_monitor.update_metrics(blockchain, node)

# Get health status
health = recovery_manager.health_monitor.get_health_status()

if health['score'] < 60:
    print("WARNING: Blockchain health degraded!")
    print(f"Score: {health['score']}")
    print(f"Status: {health['status']}")
```

### Example 5: Circuit Breaker

```python
# Get circuit breaker
mining_breaker = recovery_manager.circuit_breakers['mining']

# Check state
if mining_breaker.state == CircuitState.OPEN:
    print("Mining circuit is OPEN - waiting for recovery")
else:
    # Safe to mine
    success, block, error = mining_breaker.call(
        blockchain.mine_pending_transactions,
        miner_address
    )
```

## Configuration

### Recovery Manager Configuration

```python
config = {
    'backup_interval': 3600,      # Hourly backups
    'corruption_check_interval': 21600,  # 6-hour checks
    'max_backups': 24,            # Keep 24 backups
    'health_check_interval': 60,  # Monitor every minute
}

recovery_manager = ErrorRecoveryManager(blockchain, node, config)
```

### Circuit Breaker Configuration

```python
circuit_breakers = {
    'mining': CircuitBreaker(
        failure_threshold=5,
        timeout=60,
        success_threshold=2
    ),
    'validation': CircuitBreaker(
        failure_threshold=3,
        timeout=30,
        success_threshold=2
    ),
    'network': CircuitBreaker(
        failure_threshold=10,
        timeout=120,
        success_threshold=3
    )
}
```

### Retry Strategy Configuration

```python
retry_strategy = RetryStrategy(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0
)
```

## Best Practices

### 1. Regular Backups

Create backups regularly and before risky operations:

```python
# Hourly backups
recovery_manager.create_checkpoint(f"hourly_{int(time.time())}")

# Before upgrade
recovery_manager.create_checkpoint("before_upgrade")
```

### 2. Monitor Health

Check health metrics regularly:

```python
health = recovery_manager.health_monitor.get_health_status()

if health['score'] < 60:
    # Take action
    send_alert("Blockchain health degraded")
```

### 3. Handle Errors Gracefully

Use circuit breakers for critical operations:

```python
success, result, error = recovery_manager.wrap_operation(
    'mining',
    blockchain.mine_pending_transactions,
    miner_address
)

if not success:
    log_error(error)
    send_notification(error)
```

### 4. Test Recovery Procedures

Regularly test recovery:

```python
# Test backup/restore
backup = recovery_manager.create_checkpoint("test")
recovery_manager.backup_manager.restore_backup(backup)

# Test corruption detection
is_corrupted, issues = recovery_manager.corruption_detector.detect_corruption(blockchain)
```

### 5. Graceful Shutdown

Always use graceful shutdown:

```python
try:
    node.run()
finally:
    recovery_manager.graceful_shutdown("normal_shutdown")
```

### 6. Preserve Transactions

Ensure pending transactions are preserved:

```python
# Before shutdown
recovery_manager._preserve_pending_transactions()

# After restart
recovery_manager._restore_pending_transactions()
```

### 7. Cleanup Old Backups

Prevent disk space issues:

```python
# Keep only recent backups
recovery_manager.backup_manager.cleanup_old_backups(keep_count=24)
```

### 8. Log Everything

Track all recovery actions:

```python
recovery_manager._log_error(operation, error, severity)
recovery_manager._log_recovery(type, status, details)
```

## Recovery Scenarios

### Scenario 1: Database Corruption

**Detection:**
```python
is_corrupted, issues = detector.detect_corruption(blockchain)
```

**Recovery:**
1. Preserve pending transactions
2. Find last good backup
3. Restore from backup
4. Restore pending transactions
5. Resume normal operation

### Scenario 2: Network Partition

**Detection:**
- No peers connected
- Unable to sync

**Recovery:**
1. Attempt peer reconnection with retry
2. Enter degraded mode if offline
3. Continue local operations
4. Re-sync when connection restored

### Scenario 3: Invalid Block

**Detection:**
- Block validation fails

**Recovery:**
1. Reject invalid block
2. Check for chain corruption
3. Request valid block from peers
4. Continue with valid chain

### Scenario 4: System Failure

**Protection:**
- Circuit breakers prevent cascading failures
- Automatic retry with backoff
- Graceful degradation
- Transaction preservation

### Scenario 5: Resource Exhaustion

**Monitoring:**
- Mempool size limits
- Health score tracking
- Automatic alerts

**Response:**
1. Clear old pending transactions
2. Reject new transactions temporarily
3. Scale resources if needed

## Troubleshooting

### Issue: Circuit Breaker Stuck OPEN

**Solution:**
```python
# Reset circuit breaker
recovery_manager.circuit_breakers['mining'].reset()
```

### Issue: No Backups Available

**Solution:**
```python
# Create emergency backup
recovery_manager.create_checkpoint("emergency")
```

### Issue: Corruption Detection False Positive

**Solution:**
```python
# Force validation
blockchain.validate_chain()

# If valid, no recovery needed
```

### Issue: High Error Rate

**Solution:**
```python
# Check error log
errors = list(recovery_manager.error_log)[-50:]

# Identify pattern
# Fix root cause
# Reset counters
```

## Performance Considerations

- **Backups**: ~1-5 seconds for 1000 blocks
- **Corruption Check**: ~2-10 seconds for full chain
- **Health Monitoring**: ~100ms per update
- **Circuit Breaker**: <1ms overhead per call
- **Retry Strategy**: Varies by retry count and delay

## Conclusion

The Error Recovery System provides comprehensive protection for the XAI blockchain, ensuring:

- **Reliability** - Automatic recovery from failures
- **Data Integrity** - Corruption detection and rollback
- **Availability** - Graceful degradation and recovery
- **Observability** - Health monitoring and error tracking
- **Resilience** - Circuit breakers and retry logic

For more examples, see `error_recovery_examples.py`.
