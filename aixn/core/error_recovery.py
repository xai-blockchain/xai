"""
XAI Blockchain - Error Recovery and Resilience System

Comprehensive error handling, recovery, and resilience features:
- Graceful shutdown on errors
- Database corruption recovery
- Network partition handling
- Invalid block/transaction handling
- Circuit breaker pattern
- Automatic retry with exponential backoff
- State recovery and rollback
- Health monitoring
- Transaction queue preservation
"""

import time
import json
import os
import threading
import hashlib
import shutil
import traceback
from typing import Dict, List, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import deque
from decimal import Decimal


class RecoveryState(Enum):
    """System recovery states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    CRITICAL = "critical"
    SHUTDOWN = "shutdown"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents cascading failures by breaking the circuit when
    a service is experiencing issues.
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60,
                 success_threshold: int = 2):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute function through circuit breaker

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            (success, result, error)
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                return False, None, "Circuit breaker is OPEN"

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return True, result, None
        except Exception as e:
            self._on_failure()
            return False, None, str(e)

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class RetryStrategy:
    """
    Retry logic with exponential backoff
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        """
        Initialize retry strategy

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def execute(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute function with retry logic

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            (success, result, error)
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return True, result, None
            except Exception as e:
                last_error = str(e)

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    time.sleep(delay)

        return False, None, f"Failed after {self.max_retries + 1} attempts: {last_error}"


class BlockchainBackup:
    """
    Blockchain backup and restoration manager
    """

    def __init__(self, backup_dir: str = "data/backups"):
        """
        Initialize backup manager

        Args:
            backup_dir: Directory for backups
        """
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, blockchain, name: Optional[str] = None) -> str:
        """
        Create blockchain backup

        Args:
            blockchain: Blockchain instance
            name: Optional backup name

        Returns:
            Backup file path
        """
        if name is None:
            name = f"backup_{int(time.time())}"

        backup_path = os.path.join(self.backup_dir, f"{name}.json")

        # Create backup data
        backup_data = {
            'timestamp': time.time(),
            'chain_height': len(blockchain.chain),
            'chain': [block.to_dict() for block in blockchain.chain],
            'pending_transactions': [tx.to_dict() for tx in blockchain.pending_transactions],
            'utxo_set': blockchain.utxo_set,
            'difficulty': blockchain.difficulty,
            'metadata': {
                'latest_hash': blockchain.get_latest_block().hash,
                'total_supply': blockchain.get_total_circulating_supply() if hasattr(blockchain, 'get_total_circulating_supply') else 0
            }
        }

        # Write backup
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)

        return backup_path

    def restore_backup(self, backup_path: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Restore blockchain from backup

        Args:
            backup_path: Path to backup file

        Returns:
            (success, backup_data, error)
        """
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)

            return True, backup_data, None
        except Exception as e:
            return False, None, str(e)

    def list_backups(self) -> List[Dict]:
        """
        List available backups

        Returns:
            List of backup info
        """
        backups = []

        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.backup_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    backups.append({
                        'name': filename,
                        'path': filepath,
                        'timestamp': data.get('timestamp'),
                        'chain_height': data.get('chain_height'),
                        'size': os.path.getsize(filepath)
                    })
                except:
                    pass

        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return backups

    def cleanup_old_backups(self, keep_count: int = 10):
        """
        Remove old backups, keeping only the most recent

        Args:
            keep_count: Number of backups to keep
        """
        backups = self.list_backups()

        # Remove old backups
        for backup in backups[keep_count:]:
            try:
                os.remove(backup['path'])
            except:
                pass


class CorruptionDetector:
    """
    Detect and handle blockchain data corruption
    """

    def __init__(self):
        """Initialize corruption detector"""
        self.corruption_checks = {
            'hash_integrity': self._check_hash_integrity,
            'chain_continuity': self._check_chain_continuity,
            'utxo_consistency': self._check_utxo_consistency,
            'supply_validation': self._check_supply_validation,
            'transaction_validity': self._check_transaction_validity
        }

    def detect_corruption(self, blockchain) -> Tuple[bool, List[str]]:
        """
        Run all corruption checks

        Args:
            blockchain: Blockchain instance

        Returns:
            (is_corrupted, list of issues)
        """
        issues = []

        for check_name, check_func in self.corruption_checks.items():
            try:
                is_valid, errors = check_func(blockchain)
                if not is_valid:
                    issues.extend([f"[{check_name}] {err}" for err in errors])
            except Exception as e:
                issues.append(f"[{check_name}] Check failed: {str(e)}")

        return len(issues) > 0, issues

    def _check_hash_integrity(self, blockchain) -> Tuple[bool, List[str]]:
        """Check block hash integrity"""
        errors = []

        for i, block in enumerate(blockchain.chain):
            # Verify hash matches content
            calculated_hash = block.calculate_hash()
            if block.hash != calculated_hash:
                errors.append(f"Block {i} hash mismatch: {block.hash[:16]}... != {calculated_hash[:16]}...")

        return len(errors) == 0, errors

    def _check_chain_continuity(self, blockchain) -> Tuple[bool, List[str]]:
        """Check chain continuity"""
        errors = []

        for i in range(1, len(blockchain.chain)):
            current = blockchain.chain[i]
            previous = blockchain.chain[i - 1]

            if current.previous_hash != previous.hash:
                errors.append(f"Block {i} broken chain: previous_hash mismatch")

            if current.index != previous.index + 1:
                errors.append(f"Block {i} index discontinuity")

        return len(errors) == 0, errors

    def _check_utxo_consistency(self, blockchain) -> Tuple[bool, List[str]]:
        """Check UTXO set consistency"""
        errors = []

        # Rebuild UTXO set from chain and compare
        try:
            rebuilt_utxo = {}

            for block in blockchain.chain:
                for tx in block.transactions:
                    # Add outputs
                    if tx.recipient not in rebuilt_utxo:
                        rebuilt_utxo[tx.recipient] = []

                    rebuilt_utxo[tx.recipient].append({
                        'txid': tx.txid,
                        'amount': tx.amount,
                        'spent': False
                    })

                    # Mark inputs as spent (simplified)
                    if tx.sender != "COINBASE" and tx.sender in rebuilt_utxo:
                        spent_amount = tx.amount + tx.fee
                        remaining = spent_amount

                        for utxo in rebuilt_utxo[tx.sender]:
                            if not utxo['spent'] and remaining > 0:
                                if utxo['amount'] <= remaining:
                                    utxo['spent'] = True
                                    remaining -= utxo['amount']
                                else:
                                    utxo['amount'] -= remaining
                                    remaining = 0

            # Compare balances
            for address in rebuilt_utxo:
                rebuilt_balance = sum(u['amount'] for u in rebuilt_utxo[address] if not u['spent'])
                current_balance = blockchain.get_balance(address)

                if abs(rebuilt_balance - current_balance) > 0.00000001:
                    errors.append(f"UTXO mismatch for {address[:10]}...: rebuilt={rebuilt_balance}, current={current_balance}")

        except Exception as e:
            errors.append(f"UTXO check failed: {str(e)}")

        return len(errors) == 0, errors

    def _check_supply_validation(self, blockchain) -> Tuple[bool, List[str]]:
        """Check total supply doesn't exceed cap"""
        errors = []

        try:
            total_supply = Decimal(0)
            for address, utxos in blockchain.utxo_set.items():
                for utxo in utxos:
                    if not utxo['spent']:
                        total_supply += Decimal(str(utxo['amount']))

            max_supply = getattr(blockchain, 'max_supply', 121000000)

            if float(total_supply) > max_supply:
                errors.append(f"Supply cap exceeded: {float(total_supply)} > {max_supply}")

        except Exception as e:
            errors.append(f"Supply validation failed: {str(e)}")

        return len(errors) == 0, errors

    def _check_transaction_validity(self, blockchain) -> Tuple[bool, List[str]]:
        """Check transaction validity"""
        errors = []

        for i, block in enumerate(blockchain.chain):
            for j, tx in enumerate(block.transactions):
                # Check basic transaction properties
                if tx.amount < 0:
                    errors.append(f"Block {i}, tx {j}: Negative amount")

                if tx.fee < 0:
                    errors.append(f"Block {i}, tx {j}: Negative fee")

                # Verify signature (skip coinbase)
                if tx.sender != "COINBASE":
                    if not tx.verify_signature():
                        errors.append(f"Block {i}, tx {j}: Invalid signature")

        return len(errors) == 0, errors


class HealthMonitor:
    """
    Monitor blockchain health and performance
    """

    def __init__(self):
        """Initialize health monitor"""
        self.metrics = {
            'last_block_time': time.time(),
            'blocks_mined': 0,
            'transactions_processed': 0,
            'errors_encountered': 0,
            'network_peers': 0,
            'mempool_size': 0,
            'sync_status': 'synced'
        }

        self.health_history = deque(maxlen=100)

    def update_metrics(self, blockchain, node=None):
        """
        Update health metrics

        Args:
            blockchain: Blockchain instance
            node: Optional node instance
        """
        self.metrics['last_block_time'] = blockchain.get_latest_block().timestamp
        self.metrics['blocks_mined'] = len(blockchain.chain)
        self.metrics['mempool_size'] = len(blockchain.pending_transactions)

        if node:
            self.metrics['network_peers'] = len(node.peers) if hasattr(node, 'peers') else 0

        # Calculate health score
        health_score = self._calculate_health_score(blockchain)

        self.health_history.append({
            'timestamp': time.time(),
            'score': health_score,
            'metrics': dict(self.metrics)
        })

    def _calculate_health_score(self, blockchain) -> float:
        """
        Calculate overall health score (0-100)

        Args:
            blockchain: Blockchain instance

        Returns:
            Health score
        """
        score = 100.0

        # Penalize if last block is old
        time_since_last_block = time.time() - self.metrics['last_block_time']
        if time_since_last_block > 600:  # 10 minutes
            score -= min(30, time_since_last_block / 60)

        # Penalize if mempool is very full
        if self.metrics['mempool_size'] > 10000:
            score -= min(20, (self.metrics['mempool_size'] - 10000) / 500)

        # Penalize if no peers
        if self.metrics['network_peers'] == 0:
            score -= 25

        # Penalize for errors
        if self.metrics['errors_encountered'] > 10:
            score -= min(25, self.metrics['errors_encountered'])

        return max(0, score)

    def get_health_status(self) -> Dict:
        """
        Get current health status

        Returns:
            Health status info
        """
        if not self.health_history:
            return {
                'status': 'unknown',
                'score': 0,
                'metrics': self.metrics
            }

        current = self.health_history[-1]
        score = current['score']

        if score >= 80:
            status = 'healthy'
        elif score >= 60:
            status = 'degraded'
        elif score >= 40:
            status = 'warning'
        else:
            status = 'critical'

        return {
            'status': status,
            'score': score,
            'metrics': current['metrics'],
            'timestamp': current['timestamp']
        }


class ErrorRecoveryManager:
    """
    Main error recovery and resilience manager

    Coordinates all recovery mechanisms and provides high-level
    error handling for the blockchain.
    """

    def __init__(self, blockchain, node=None, config: Optional[Dict] = None):
        """
        Initialize error recovery manager

        Args:
            blockchain: Blockchain instance
            node: Optional node instance
            config: Optional configuration
        """
        self.blockchain = blockchain
        self.node = node
        self.config = config or {}

        # Recovery state
        self.state = RecoveryState.HEALTHY
        self.recovery_in_progress = False

        # Initialize components
        self.circuit_breakers = {
            'mining': CircuitBreaker(failure_threshold=5, timeout=60),
            'validation': CircuitBreaker(failure_threshold=3, timeout=30),
            'network': CircuitBreaker(failure_threshold=10, timeout=120),
            'storage': CircuitBreaker(failure_threshold=2, timeout=30)
        }

        self.retry_strategy = RetryStrategy(max_retries=3, base_delay=1.0)
        self.backup_manager = BlockchainBackup()
        self.corruption_detector = CorruptionDetector()
        self.health_monitor = HealthMonitor()

        # Error tracking
        self.error_log = deque(maxlen=1000)
        self.recovery_log = deque(maxlen=100)

        # Transaction queue preservation
        self.preserved_transactions = []

        # Setup logging
        self.logger = logging.getLogger('error_recovery')
        self.logger.setLevel(logging.INFO)

        # Start health monitoring thread
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.monitor_thread.start()

    def wrap_operation(self, operation: str, func: Callable,
                      *args, **kwargs) -> Tuple[bool, Any, Optional[str]]:
        """
        Wrap critical operation with error handling

        Args:
            operation: Operation name (mining, validation, network, storage)
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            (success, result, error)
        """
        circuit_breaker = self.circuit_breakers.get(operation)

        if circuit_breaker:
            # Use circuit breaker
            success, result, error = circuit_breaker.call(func, *args, **kwargs)

            if not success:
                self._log_error(operation, error, ErrorSeverity.MEDIUM)

            return success, result, error
        else:
            # Direct execution with try-catch
            try:
                result = func(*args, **kwargs)
                return True, result, None
            except Exception as e:
                error = str(e)
                self._log_error(operation, error, ErrorSeverity.MEDIUM)
                return False, None, error

    def handle_corruption(self, force_rollback: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Handle blockchain corruption

        Args:
            force_rollback: Force rollback without checks

        Returns:
            (success, error)
        """
        self.logger.warning("Checking for blockchain corruption...")

        # Detect corruption
        is_corrupted, issues = self.corruption_detector.detect_corruption(self.blockchain)

        if not is_corrupted and not force_rollback:
            self.logger.info("No corruption detected")
            return True, None

        if is_corrupted:
            self.logger.error(f"Corruption detected: {len(issues)} issues")
            for issue in issues:
                self.logger.error(f"  - {issue}")

        # Attempt recovery
        self.state = RecoveryState.RECOVERING
        self.recovery_in_progress = True

        try:
            # 1. Preserve pending transactions
            self._preserve_pending_transactions()

            # 2. Find last good backup
            backups = self.backup_manager.list_backups()

            if not backups:
                return False, "No backups available for recovery"

            # 3. Try restoring backups (newest first)
            for backup in backups:
                self.logger.info(f"Attempting restore from {backup['name']}...")

                success, backup_data, error = self.backup_manager.restore_backup(backup['path'])

                if not success:
                    continue

                # Validate backup before applying
                if self._validate_backup(backup_data):
                    self._apply_backup(backup_data)
                    self.logger.info(f"Successfully restored from {backup['name']}")

                    # Restore pending transactions
                    self._restore_pending_transactions()

                    self.state = RecoveryState.HEALTHY
                    self.recovery_in_progress = False

                    self._log_recovery("corruption_recovery", "success",
                                      f"Restored from backup: {backup['name']}")

                    return True, None

            return False, "All backup restoration attempts failed"

        except Exception as e:
            self.state = RecoveryState.CRITICAL
            self.recovery_in_progress = False
            self._log_recovery("corruption_recovery", "failed", str(e))
            return False, str(e)

    def handle_network_partition(self) -> Tuple[bool, Optional[str]]:
        """
        Handle network partition recovery

        Returns:
            (success, error)
        """
        self.logger.warning("Handling network partition...")

        try:
            # 1. Attempt to reconnect to peers
            if self.node:
                self.logger.info("Attempting peer reconnection...")

                # Try to sync with network
                success = self.retry_strategy.execute(
                    lambda: self.node.sync_with_network() if hasattr(self.node, 'sync_with_network') else True
                )[0]

                if success:
                    self.logger.info("Network partition resolved")
                    self._log_recovery("network_partition", "success", "Reconnected to network")
                    return True, None

            # 2. Enter degraded mode
            self.state = RecoveryState.DEGRADED
            self.logger.warning("Operating in degraded mode (offline)")

            return True, "Operating in degraded mode"

        except Exception as e:
            self._log_recovery("network_partition", "failed", str(e))
            return False, str(e)

    def handle_invalid_block(self, block) -> Tuple[bool, Optional[str]]:
        """
        Handle invalid block

        Args:
            block: Invalid block

        Returns:
            (success, error)
        """
        self.logger.warning(f"Handling invalid block {block.index}...")

        try:
            # 1. Reject the block
            self.logger.info(f"Rejecting invalid block {block.index}")

            # 2. Check if we need to rollback
            if block.index < len(self.blockchain.chain):
                # This block is already in our chain - potential corruption
                self.logger.error("Invalid block found in chain - checking for corruption")
                return self.handle_corruption()

            # 3. Request valid block from network
            if self.node:
                self.logger.info("Requesting valid block from network...")
                # Implementation would request block from peers

            self._log_recovery("invalid_block", "success", f"Rejected block {block.index}")
            return True, None

        except Exception as e:
            self._log_recovery("invalid_block", "failed", str(e))
            return False, str(e)

    def handle_invalid_transaction(self, transaction) -> Tuple[bool, Optional[str]]:
        """
        Handle invalid transaction

        Args:
            transaction: Invalid transaction

        Returns:
            (success, error)
        """
        try:
            # Remove from pending transactions
            if transaction in self.blockchain.pending_transactions:
                self.blockchain.pending_transactions.remove(transaction)
                self.logger.info(f"Removed invalid transaction {transaction.txid[:16]}...")

            return True, None

        except Exception as e:
            return False, str(e)

    def graceful_shutdown(self, reason: str = "manual"):
        """
        Perform graceful shutdown

        Args:
            reason: Shutdown reason
        """
        self.logger.info(f"Initiating graceful shutdown: {reason}")
        self.state = RecoveryState.SHUTDOWN

        try:
            # 1. Stop mining
            if self.node and hasattr(self.node, 'stop_mining'):
                self.logger.info("Stopping mining...")
                self.node.stop_mining()

            # 2. Preserve pending transactions
            self._preserve_pending_transactions()

            # 3. Create final backup
            self.logger.info("Creating final backup...")
            backup_path = self.backup_manager.create_backup(
                self.blockchain,
                name=f"shutdown_{int(time.time())}"
            )
            self.logger.info(f"Backup created: {backup_path}")

            # 4. Cleanup old backups
            self.backup_manager.cleanup_old_backups(keep_count=10)

            # 5. Stop health monitoring
            self.monitoring_active = False

            self.logger.info("Graceful shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def create_checkpoint(self, name: Optional[str] = None) -> str:
        """
        Create blockchain checkpoint/backup

        Args:
            name: Optional checkpoint name

        Returns:
            Checkpoint path
        """
        return self.backup_manager.create_backup(self.blockchain, name)

    def get_recovery_status(self) -> Dict:
        """
        Get recovery system status

        Returns:
            Status information
        """
        health_status = self.health_monitor.get_health_status()

        return {
            'state': self.state.value,
            'recovery_in_progress': self.recovery_in_progress,
            'health': health_status,
            'circuit_breakers': {
                name: breaker.state.value
                for name, breaker in self.circuit_breakers.items()
            },
            'recent_errors': list(self.error_log)[-10:],
            'recent_recoveries': list(self.recovery_log)[-10:],
            'backups_available': len(self.backup_manager.list_backups()),
            'preserved_transactions': len(self.preserved_transactions)
        }

    def _preserve_pending_transactions(self):
        """Preserve pending transactions to disk"""
        try:
            self.preserved_transactions = [
                tx.to_dict() for tx in self.blockchain.pending_transactions
            ]

            os.makedirs('data/recovery', exist_ok=True)
            with open('data/recovery/pending_transactions.json', 'w') as f:
                json.dump(self.preserved_transactions, f, indent=2)

            self.logger.info(f"Preserved {len(self.preserved_transactions)} pending transactions")

        except Exception as e:
            self.logger.error(f"Failed to preserve transactions: {e}")

    def _restore_pending_transactions(self):
        """Restore preserved pending transactions"""
        try:
            if os.path.exists('data/recovery/pending_transactions.json'):
                with open('data/recovery/pending_transactions.json', 'r') as f:
                    preserved = json.load(f)

                # Recreate transaction objects
                from blockchain import Transaction
                for tx_data in preserved:
                    tx = Transaction(
                        tx_data['sender'],
                        tx_data['recipient'],
                        tx_data['amount'],
                        tx_data['fee']
                    )
                    tx.txid = tx_data['txid']
                    tx.signature = tx_data['signature']
                    tx.public_key = tx_data.get('public_key')
                    tx.timestamp = tx_data['timestamp']

                    # Re-validate and add
                    if self.blockchain.validate_transaction(tx):
                        self.blockchain.pending_transactions.append(tx)

                self.logger.info(f"Restored {len(preserved)} pending transactions")

        except Exception as e:
            self.logger.error(f"Failed to restore transactions: {e}")

    def _validate_backup(self, backup_data: Dict) -> bool:
        """
        Validate backup data before applying

        Args:
            backup_data: Backup data

        Returns:
            Is valid
        """
        try:
            # Check required fields
            if 'chain' not in backup_data or 'utxo_set' not in backup_data:
                return False

            # Check chain is not empty
            if len(backup_data['chain']) == 0:
                return False

            return True

        except:
            return False

    def _apply_backup(self, backup_data: Dict):
        """
        Apply backup to blockchain

        Args:
            backup_data: Backup data
        """
        from blockchain import Block, Transaction

        # Rebuild chain
        new_chain = []
        for block_data in backup_data['chain']:
            # Recreate transactions
            transactions = []
            for tx_data in block_data['transactions']:
                tx = Transaction(
                    tx_data['sender'],
                    tx_data['recipient'],
                    tx_data['amount'],
                    tx_data['fee']
                )
                tx.txid = tx_data['txid']
                tx.signature = tx_data.get('signature')
                tx.public_key = tx_data.get('public_key')
                tx.timestamp = tx_data['timestamp']
                tx.tx_type = tx_data.get('tx_type', 'normal')
                tx.nonce = tx_data.get('nonce')
                transactions.append(tx)

            # Recreate block
            block = Block(
                block_data['index'],
                transactions,
                block_data['previous_hash'],
                block_data['difficulty']
            )
            block.timestamp = block_data['timestamp']
            block.nonce = block_data['nonce']
            block.merkle_root = block_data['merkle_root']
            block.hash = block_data['hash']

            new_chain.append(block)

        # Apply new chain
        self.blockchain.chain = new_chain

        # Restore UTXO set
        self.blockchain.utxo_set = backup_data['utxo_set']

        # Clear pending transactions (will be restored separately)
        self.blockchain.pending_transactions = []

    def _monitor_health(self):
        """Background health monitoring"""
        while self.monitoring_active:
            try:
                self.health_monitor.update_metrics(self.blockchain, self.node)

                # Check for critical issues
                health = self.health_monitor.get_health_status()

                if health['score'] < 40 and self.state == RecoveryState.HEALTHY:
                    self.logger.warning(f"Health degraded: score={health['score']}")
                    self.state = RecoveryState.DEGRADED

                # Auto-backup on schedule
                if int(time.time()) % 3600 == 0:  # Every hour
                    self.backup_manager.create_backup(
                        self.blockchain,
                        name=f"auto_{int(time.time())}"
                    )
                    self.backup_manager.cleanup_old_backups(keep_count=24)

            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")

            time.sleep(60)  # Check every minute

    def _log_error(self, operation: str, error: str, severity: ErrorSeverity):
        """
        Log error

        Args:
            operation: Operation name
            error: Error message
            severity: Error severity
        """
        error_entry = {
            'timestamp': time.time(),
            'operation': operation,
            'error': error,
            'severity': severity.value
        }

        self.error_log.append(error_entry)
        self.health_monitor.metrics['errors_encountered'] += 1

        if severity == ErrorSeverity.CRITICAL:
            self.logger.error(f"[CRITICAL] {operation}: {error}")
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"[HIGH] {operation}: {error}")
        else:
            self.logger.warning(f"[{severity.value.upper()}] {operation}: {error}")

    def _log_recovery(self, recovery_type: str, status: str, details: str):
        """
        Log recovery action

        Args:
            recovery_type: Type of recovery
            status: Recovery status
            details: Recovery details
        """
        recovery_entry = {
            'timestamp': time.time(),
            'type': recovery_type,
            'status': status,
            'details': details
        }

        self.recovery_log.append(recovery_entry)
        self.logger.info(f"Recovery [{recovery_type}]: {status} - {details}")


# Convenience functions for integration

def create_recovery_manager(blockchain, node=None, config=None) -> ErrorRecoveryManager:
    """
    Create and initialize error recovery manager

    Args:
        blockchain: Blockchain instance
        node: Optional node instance
        config: Optional configuration

    Returns:
        ErrorRecoveryManager instance
    """
    return ErrorRecoveryManager(blockchain, node, config)


def wrap_blockchain_operation(recovery_manager: ErrorRecoveryManager,
                              operation: str, func: Callable,
                              *args, **kwargs):
    """
    Convenience wrapper for blockchain operations

    Args:
        recovery_manager: ErrorRecoveryManager instance
        operation: Operation name
        func: Function to execute
        *args, **kwargs: Function arguments

    Returns:
        Function result
    """
    success, result, error = recovery_manager.wrap_operation(operation, func, *args, **kwargs)

    if not success:
        raise Exception(f"{operation} failed: {error}")

    return result
