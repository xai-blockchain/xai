"""
XAI Blockchain - Error Recovery Integration

Integration examples and helper functions for incorporating
error recovery into the blockchain node.
"""

from aixn.core.error_recovery import (
    ErrorRecoveryManager,
    create_recovery_manager,
    wrap_blockchain_operation,
)
from flask import jsonify, request
import functools
import time


def integrate_recovery_with_blockchain(blockchain, node=None):
    """
    Integrate error recovery with blockchain

    Args:
        blockchain: Blockchain instance
        node: Optional node instance

    Returns:
        ErrorRecoveryManager instance
    """
    # Create recovery manager
    recovery_manager = create_recovery_manager(blockchain, node)

    # Create initial backup
    print("Creating initial blockchain backup...")
    recovery_manager.create_checkpoint("initial")

    # Wrap critical blockchain methods
    _wrap_blockchain_methods(blockchain, recovery_manager)

    print("Error recovery system initialized")
    return recovery_manager


def _wrap_blockchain_methods(blockchain, recovery_manager):
    """
    Wrap critical blockchain methods with error handling

    Args:
        blockchain: Blockchain instance
        recovery_manager: ErrorRecoveryManager instance
    """
    # Wrap mine_pending_transactions
    original_mine = blockchain.mine_pending_transactions

    @functools.wraps(original_mine)
    def wrapped_mine(*args, **kwargs):
        return wrap_blockchain_operation(recovery_manager, "mining", original_mine, *args, **kwargs)

    blockchain.mine_pending_transactions = wrapped_mine

    # Wrap add_transaction
    original_add_tx = blockchain.add_transaction

    @functools.wraps(original_add_tx)
    def wrapped_add_tx(transaction):
        try:
            # Validate transaction first
            success, result, error = recovery_manager.wrap_operation(
                "validation", lambda: blockchain.validate_transaction(transaction)
            )

            if not success or not result:
                # Handle invalid transaction
                recovery_manager.handle_invalid_transaction(transaction)
                return False

            # Add transaction
            return original_add_tx(transaction)

        except Exception as e:
            recovery_manager.handle_invalid_transaction(transaction)
            return False

    blockchain.add_transaction = wrapped_add_tx

    # Wrap validate_chain
    original_validate = blockchain.validate_chain

    @functools.wraps(original_validate)
    def wrapped_validate():
        success, result, error = recovery_manager.wrap_operation("validation", original_validate)

        if not success or not result:
            # Chain validation failed - check for corruption
            recovery_manager.handle_corruption()
            return False

        return result

    blockchain.validate_chain = wrapped_validate


def setup_recovery_api_endpoints(app, recovery_manager):
    """
    Setup Flask API endpoints for error recovery

    Args:
        app: Flask app
        recovery_manager: ErrorRecoveryManager instance
    """

    @app.route("/recovery/status", methods=["GET"])
    def get_recovery_status():
        """Get error recovery system status"""
        status = recovery_manager.get_recovery_status()
        return jsonify({"success": True, "recovery_status": status})

    @app.route("/recovery/health", methods=["GET"])
    def get_health():
        """Get blockchain health metrics"""
        health = recovery_manager.health_monitor.get_health_status()
        return jsonify({"success": True, "health": health})

    @app.route("/recovery/circuit-breakers", methods=["GET"])
    def get_circuit_breakers():
        """Get circuit breaker states"""
        breakers = {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
            }
            for name, breaker in recovery_manager.circuit_breakers.items()
        }

        return jsonify({"success": True, "circuit_breakers": breakers})

    @app.route("/recovery/circuit-breakers/<name>/reset", methods=["POST"])
    def reset_circuit_breaker(name):
        """Reset specific circuit breaker"""
        if name not in recovery_manager.circuit_breakers:
            return jsonify({"success": False, "error": f"Circuit breaker not found: {name}"}), 404

        recovery_manager.circuit_breakers[name].reset()

        return jsonify({"success": True, "message": f"Circuit breaker {name} reset"})

    @app.route("/recovery/backups", methods=["GET"])
    def list_backups():
        """List available backups"""
        backups = recovery_manager.backup_manager.list_backups()
        return jsonify({"success": True, "count": len(backups), "backups": backups})

    @app.route("/recovery/backup/create", methods=["POST"])
    def create_backup():
        """Create manual backup"""
        data = request.get_json() or {}
        name = data.get("name")

        backup_path = recovery_manager.create_checkpoint(name)

        return jsonify(
            {"success": True, "backup_path": backup_path, "message": "Backup created successfully"}
        )

    @app.route("/recovery/backup/restore", methods=["POST"])
    def restore_backup():
        """Restore from backup"""
        data = request.get_json()

        if not data or "backup_name" not in data:
            return jsonify({"success": False, "error": "Missing backup_name"}), 400

        # Find backup
        backups = recovery_manager.backup_manager.list_backups()
        backup = next((b for b in backups if b["name"] == data["backup_name"]), None)

        if not backup:
            return jsonify({"success": False, "error": "Backup not found"}), 404

        # Restore backup
        success, backup_data, error = recovery_manager.backup_manager.restore_backup(backup["path"])

        if not success:
            return jsonify({"success": False, "error": f"Restore failed: {error}"}), 500

        # Validate and apply
        if recovery_manager._validate_backup(backup_data):
            recovery_manager._apply_backup(backup_data)

            return jsonify(
                {
                    "success": True,
                    "message": f'Restored from backup: {data["backup_name"]}',
                    "chain_height": len(recovery_manager.blockchain.chain),
                }
            )
        else:
            return jsonify({"success": False, "error": "Backup validation failed"}), 500

    @app.route("/recovery/corruption/check", methods=["POST"])
    def check_corruption():
        """Check for blockchain corruption"""
        is_corrupted, issues = recovery_manager.corruption_detector.detect_corruption(
            recovery_manager.blockchain
        )

        return jsonify(
            {
                "success": True,
                "is_corrupted": is_corrupted,
                "issue_count": len(issues),
                "issues": issues,
            }
        )

    @app.route("/recovery/corruption/fix", methods=["POST"])
    def fix_corruption():
        """Attempt to fix blockchain corruption"""
        data = request.get_json() or {}
        force_rollback = data.get("force_rollback", False)

        success, error = recovery_manager.handle_corruption(force_rollback)

        if success:
            return jsonify({"success": True, "message": "Corruption fixed successfully"})
        else:
            return jsonify({"success": False, "error": error}), 500

    @app.route("/recovery/errors", methods=["GET"])
    def get_error_log():
        """Get recent errors"""
        limit = request.args.get("limit", default=50, type=int)

        errors = list(recovery_manager.error_log)[-limit:]

        return jsonify({"success": True, "count": len(errors), "errors": errors})

    @app.route("/recovery/actions", methods=["GET"])
    def get_recovery_log():
        """Get recent recovery actions"""
        limit = request.args.get("limit", default=50, type=int)

        actions = list(recovery_manager.recovery_log)[-limit:]

        return jsonify({"success": True, "count": len(actions), "actions": actions})

    @app.route("/recovery/shutdown", methods=["POST"])
    def graceful_shutdown():
        """Perform graceful shutdown"""
        data = request.get_json() or {}
        reason = data.get("reason", "manual")

        # Initiate shutdown in background thread
        import threading

        shutdown_thread = threading.Thread(
            target=recovery_manager.graceful_shutdown, args=(reason,), daemon=True
        )
        shutdown_thread.start()

        return jsonify({"success": True, "message": "Graceful shutdown initiated"})

    @app.route("/recovery/network/reconnect", methods=["POST"])
    def handle_network_partition():
        """Handle network partition"""
        success, error = recovery_manager.handle_network_partition()

        if success:
            return jsonify({"success": True, "message": "Network partition handled"})
        else:
            return jsonify({"success": False, "error": error}), 500

    print("Recovery API endpoints registered")


# Decorator for automatic error handling
def with_recovery(recovery_manager, operation="validation"):
    """
    Decorator for automatic error handling

    Args:
        recovery_manager: ErrorRecoveryManager instance
        operation: Operation name for circuit breaker

    Returns:
        Decorator function
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            success, result, error = recovery_manager.wrap_operation(
                operation, func, *args, **kwargs
            )

            if not success:
                raise Exception(f"{operation} failed: {error}")

            return result

        return wrapper

    return decorator


# Example usage in blockchain operations
class RecoveryEnabledBlockchain:
    """
    Example of blockchain with integrated error recovery
    """

    def __init__(self, blockchain, node=None):
        """
        Initialize recovery-enabled blockchain

        Args:
            blockchain: Base blockchain instance
            node: Optional node instance
        """
        self.blockchain = blockchain
        self.node = node
        self.recovery_manager = integrate_recovery_with_blockchain(blockchain, node)

    @property
    def chain(self):
        return self.blockchain.chain

    @property
    def pending_transactions(self):
        return self.blockchain.pending_transactions

    def mine_block(self, miner_address: str):
        """
        Mine block with error recovery

        Args:
            miner_address: Miner's address

        Returns:
            Mined block
        """

        @with_recovery(self.recovery_manager, "mining")
        def _mine():
            return self.blockchain.mine_pending_transactions(miner_address)

        block = _mine()

        # Create backup after successful mining
        if len(self.blockchain.chain) % 100 == 0:  # Every 100 blocks
            self.recovery_manager.create_checkpoint(f"block_{len(self.blockchain.chain)}")

        return block

    def add_transaction(self, transaction):
        """
        Add transaction with validation and recovery

        Args:
            transaction: Transaction to add

        Returns:
            Success status
        """
        try:
            # Validate with circuit breaker
            @with_recovery(self.recovery_manager, "validation")
            def _validate():
                return self.blockchain.validate_transaction(transaction)

            is_valid = _validate()

            if not is_valid:
                self.recovery_manager.handle_invalid_transaction(transaction)
                return False

            # Add transaction
            return self.blockchain.add_transaction(transaction)

        except Exception as e:
            self.recovery_manager.handle_invalid_transaction(transaction)
            return False

    def validate_chain(self):
        """
        Validate blockchain with corruption detection

        Returns:
            Validation result
        """
        # First check for corruption
        is_corrupted, issues = self.recovery_manager.corruption_detector.detect_corruption(
            self.blockchain
        )

        if is_corrupted:
            print(f"Corruption detected: {len(issues)} issues")
            # Attempt automatic recovery
            success, error = self.recovery_manager.handle_corruption()
            if not success:
                raise Exception(f"Chain validation failed: {error}")

        # Then validate chain
        @with_recovery(self.recovery_manager, "validation")
        def _validate():
            return self.blockchain.validate_chain()

        return _validate()

    def get_recovery_status(self):
        """Get recovery system status"""
        return self.recovery_manager.get_recovery_status()

    def get_health_status(self):
        """Get blockchain health"""
        return self.recovery_manager.health_monitor.get_health_status()


# Scheduled recovery tasks
class RecoveryScheduler:
    """
    Schedule periodic recovery tasks
    """

    def __init__(self, recovery_manager):
        """
        Initialize scheduler

        Args:
            recovery_manager: ErrorRecoveryManager instance
        """
        self.recovery_manager = recovery_manager
        self.running = True
        self.scheduler_thread = None

    def start(self):
        """Start scheduled tasks"""
        import threading

        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        print("Recovery scheduler started")

    def stop(self):
        """Stop scheduled tasks"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

    def _run_scheduler(self):
        """Run scheduled tasks"""
        last_backup = time.time()
        last_corruption_check = time.time()
        last_cleanup = time.time()

        while self.running:
            try:
                current_time = time.time()

                # Hourly backup
                if current_time - last_backup >= 3600:  # 1 hour
                    print("Creating scheduled backup...")
                    self.recovery_manager.create_checkpoint(f"scheduled_{int(current_time)}")
                    last_backup = current_time

                # Corruption check every 6 hours
                if current_time - last_corruption_check >= 21600:  # 6 hours
                    print("Running scheduled corruption check...")
                    is_corrupted, issues = (
                        self.recovery_manager.corruption_detector.detect_corruption(
                            self.recovery_manager.blockchain
                        )
                    )

                    if is_corrupted:
                        print(f"Corruption detected during scheduled check: {len(issues)} issues")
                        self.recovery_manager.handle_corruption()

                    last_corruption_check = current_time

                # Cleanup old backups daily
                if current_time - last_cleanup >= 86400:  # 24 hours
                    print("Cleaning up old backups...")
                    self.recovery_manager.backup_manager.cleanup_old_backups(keep_count=24)
                    last_cleanup = current_time

            except Exception as e:
                print(f"Scheduler error: {e}")

            time.sleep(60)  # Check every minute


# Helper function for node integration
def add_recovery_to_node(node):
    """
    Add error recovery to blockchain node

    Args:
        node: BlockchainNode instance

    Returns:
        ErrorRecoveryManager instance
    """
    # Create recovery manager
    recovery_manager = integrate_recovery_with_blockchain(node.blockchain, node)

    # Add recovery API endpoints
    setup_recovery_api_endpoints(node.app, recovery_manager)

    # Start recovery scheduler
    scheduler = RecoveryScheduler(recovery_manager)
    scheduler.start()

    # Store references
    node.recovery_manager = recovery_manager
    node.recovery_scheduler = scheduler

    # Add shutdown hook
    original_run = node.run

    @functools.wraps(original_run)
    def wrapped_run(*args, **kwargs):
        try:
            return original_run(*args, **kwargs)
        finally:
            recovery_manager.graceful_shutdown("node_shutdown")
            scheduler.stop()

    node.run = wrapped_run

    print("Error recovery fully integrated with node")
    return recovery_manager
