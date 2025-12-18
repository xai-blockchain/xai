#!/usr/bin/env python3
"""
Demo of XAI Mini-App Sandbox Security

Shows how to safely execute untrusted code with permissions.
"""

from pathlib import Path
from unittest.mock import Mock

from xai.sandbox.permissions import (
    Permission,
    PermissionLevel,
    PermissionManager,
    AuditLog,
)
from xai.sandbox.secure_executor import (
    SecureExecutor,
    ExecutionContext,
    ResourceLimits,
    SandboxAPI,
)


def demo_basic_execution():
    """Demo 1: Basic safe code execution"""
    print("\n=== Demo 1: Basic Safe Execution ===\n")

    executor = SecureExecutor()

    code = """
def main(x, y):
    result = x + y
    return result
"""

    context = ExecutionContext(
        app_id="calculator",
        code=code,
        entry_point="main",
        arguments={"x": 10, "y": 32}
    )

    result = executor.execute(context)

    if result.success:
        print(f"✓ Execution successful")
        print(f"  Return value: {result.return_value}")
        print(f"  Execution time: {result.execution_time:.3f}s")
    else:
        print(f"✗ Execution failed: {result.error}")


def demo_permission_system():
    """Demo 2: Permission management"""
    print("\n=== Demo 2: Permission Management ===\n")

    # Create permission manager
    pm = PermissionManager()

    # App requests permission
    app_id = "wallet_viewer"
    print(f"App '{app_id}' requests READ_BALANCE permission...")

    granted = pm.request_permission(
        app_id=app_id,
        permission=Permission.READ_BALANCE,
        level=PermissionLevel.READ,
        auto_approve=False  # Requires user approval
    )

    print(f"  Auto-granted: {granted}")

    # Check permission (should be denied)
    has_perm = pm.has_permission(app_id, Permission.READ_BALANCE)
    print(f"  Has permission before approval: {has_perm}")

    # User approves
    print("\nUser approves permission...")
    pm.approve_permission(
        app_id=app_id,
        permission=Permission.READ_BALANCE,
        user_address="xai1user123..."
    )

    # Check again
    has_perm = pm.has_permission(app_id, Permission.READ_BALANCE)
    print(f"  Has permission after approval: {has_perm}")

    # Try to use without permission (different permission)
    print("\nApp tries to use SIGN_TRANSACTIONS without permission...")
    try:
        pm.check_permission(
            app_id=app_id,
            permission=Permission.SIGN_TRANSACTIONS,
            action="sign_transaction"
        )
        print("  ✗ Should have been denied!")
    except Exception as e:
        print(f"  ✓ Correctly denied: {e.__class__.__name__}")


def demo_security_blocks():
    """Demo 3: Security boundaries"""
    print("\n=== Demo 3: Security Boundaries ===\n")

    executor = SecureExecutor()

    # Test 1: Dangerous import blocked
    print("Test 1: Block dangerous import (os module)")
    dangerous_code = """
import os
os.system('echo pwned')
"""

    context = ExecutionContext(
        app_id="malicious_app",
        code=dangerous_code
    )

    result = executor.execute(context)

    if not result.success:
        print(f"  ✓ Blocked: {result.error[:50]}...")
    else:
        print(f"  ✗ Should have been blocked!")

    # Test 2: File access blocked
    print("\nTest 2: Block file access")
    file_code = """
data = open('/etc/passwd', 'r').read()
"""

    context = ExecutionContext(
        app_id="file_reader",
        code=file_code
    )

    result = executor.execute(context)

    if not result.success:
        print(f"  ✓ Blocked: {result.error[:50]}...")
    else:
        print(f"  ✗ Should have been blocked!")

    # Test 3: Resource limits
    print("\nTest 3: Enforce resource limits")
    infinite_loop = """
while True:
    pass
"""

    executor_limited = SecureExecutor(
        limits=ResourceLimits(max_wall_time_seconds=1)
    )

    context = ExecutionContext(
        app_id="cpu_hog",
        code=infinite_loop
    )

    result = executor_limited.execute(context)

    if not result.success or result.resource_exceeded:
        print(f"  ✓ Resource limit enforced")
    else:
        print(f"  ✗ Should have hit resource limit!")


def demo_api_integration():
    """Demo 4: Sandbox API with permissions"""
    print("\n=== Demo 4: Sandbox API Integration ===\n")

    # Setup
    pm = PermissionManager()
    wallet = Mock()
    wallet.get_balance.return_value = 100.5

    # Grant permission
    app_id = "balance_checker"
    pm.request_permission(app_id, Permission.READ_BALANCE)
    pm.approve_permission(app_id, Permission.READ_BALANCE, "user123")

    # Create API
    api = SandboxAPI(
        app_id=app_id,
        permission_manager=pm,
        wallet_interface=wallet
    )

    # Use API
    print(f"App '{app_id}' calls get_balance()...")
    try:
        balance = api.get_balance()
        print(f"  ✓ Success: balance = {balance}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Try without permission
    print("\nApp tries to create transaction without permission...")
    try:
        tx = api.create_transaction("recipient", 10.0)
        print(f"  ✗ Should have been denied!")
    except Exception as e:
        print(f"  ✓ Correctly denied: {e.__class__.__name__}")


def demo_audit_log():
    """Demo 5: Audit logging"""
    print("\n=== Demo 5: Audit Logging ===\n")

    audit_log = AuditLog()
    pm = PermissionManager(audit_log=audit_log)

    app_id = "suspicious_app"

    # Generate some activity
    print(f"App '{app_id}' makes multiple permission requests...")

    for i in range(5):
        try:
            pm.check_permission(
                app_id=app_id,
                permission=Permission.SIGN_TRANSACTIONS,
                action=f"attempt_{i}"
            )
        except Exception:
            pass

    # Check audit log
    entries = audit_log.get_entries(app_id=app_id)
    print(f"\n  Total log entries: {len(entries)}")

    # Check suspicious activity
    suspicious = audit_log.get_suspicious_activity(app_id, threshold=3)
    print(f"  Suspicious entries: {len(suspicious)}")

    if suspicious:
        print(f"  ⚠ Warning: Detected suspicious activity from {app_id}")


def main():
    """Run all demos"""
    print("=" * 60)
    print("XAI Mini-App Sandbox Security Demo")
    print("=" * 60)

    demo_basic_execution()
    demo_permission_system()
    demo_security_blocks()
    demo_api_integration()
    demo_audit_log()

    print("\n" + "=" * 60)
    print("All demos complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
