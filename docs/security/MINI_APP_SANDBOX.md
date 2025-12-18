# Mini-App Sandbox Security

Secure execution environment for third-party mini-applications in XAI wallet.

## Overview

XAI provides a secure sandbox for running untrusted mini-app code with multiple layers of isolation and permission control.

## Architecture

```
┌─────────────────────────────────────────┐
│         Mini-App (Untrusted Code)       │
├─────────────────────────────────────────┤
│     Execution Layer (Python/WASM)      │
│  ┌────────────────┬──────────────────┐  │
│  │RestrictedPython│ WASM Runtime    │  │
│  │  + Subprocess  │ (wasmer/wasmtime)│  │
│  └────────────────┴──────────────────┘  │
├─────────────────────────────────────────┤
│       Permission Manager (Capability)    │
│  - User approval required               │
│  - Time-limited grants                  │
│  - Audit logging                        │
├─────────────────────────────────────────┤
│        Sandbox API (Controlled)         │
│  - Wallet operations                    │
│  - Blockchain queries                   │
│  - Storage (quota-limited)              │
├─────────────────────────────────────────┤
│       Resource Limits (Enforced)        │
│  - CPU time, Memory, Network, Files     │
└─────────────────────────────────────────┘
```

## Security Layers

### 1. Code Execution Isolation

**Python Code (RestrictedPython)**
- Safe subset of Python with restricted builtins
- No access to dangerous modules (os, sys, subprocess)
- Limited imports to whitelisted modules only
- Custom print/input redirection
- Optional subprocess isolation for stronger boundaries

**WebAssembly (WASM)**
- True sandboxing via WASM runtime
- No host system access by default
- Capability-based imports (WASI)
- Memory-safe execution
- Deterministic behavior

### 2. Permission System

**Capability-Based Security**
- Permissions must be explicitly requested
- User approval required for sensitive operations
- Permissions can be time-limited
- Revocable at any time

**Permission Levels**
```python
class PermissionLevel(Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
```

**Available Permissions**
- `READ_BALANCE` - View wallet balance
- `READ_TRANSACTIONS` - View transaction history
- `READ_BLOCKCHAIN` - Query blockchain state
- `SIGN_TRANSACTIONS` - Sign transactions (requires user approval)
- `SEND_TRANSACTIONS` - Broadcast transactions (requires user approval)
- `NETWORK_HTTP/HTTPS` - Make network requests
- `STORAGE_READ/WRITE` - Local storage access
- `CAMERA`, `MICROPHONE`, `GEOLOCATION` - Device features
- `KEYRING_ACCESS` - Access keyring (dangerous)
- `PRIVATE_KEY_EXPORT` - Export private keys (dangerous)

### 3. Resource Limits

All mini-apps are constrained by strict resource limits:

```python
ResourceLimits(
    max_memory_mb=128,           # 128MB RAM
    max_cpu_seconds=5,           # 5 seconds CPU time
    max_wall_time_seconds=10,    # 10 seconds total time
    max_file_descriptors=64,     # 64 open files
    max_output_bytes=100*1024,   # 100KB output
    max_storage_bytes=1*1024*1024 # 1MB storage
)
```

**WASM Limits**
```python
WasmLimits(
    max_memory_pages=256,        # 16MB memory
    max_table_elements=1000,     # 1000 table entries
    max_execution_fuel=1000000,  # Metered instructions
    max_wall_time_seconds=10     # 10 seconds timeout
)
```

### 4. Network Isolation

- No network access by default
- `NETWORK_*` permission required
- Domain whitelist enforced
- Request size limits
- Timeout enforcement
- No raw sockets

### 5. Filesystem Isolation

- No filesystem access by default
- `FILESYSTEM_READ/WRITE` required
- Path restrictions (no `/etc`, `/proc`, etc.)
- Read-only by default
- Quota limits on writes

### 6. Audit Logging

All sandbox operations are logged:

```python
@dataclass
class AuditLogEntry:
    timestamp: float
    app_id: str
    permission: Permission
    action: str
    success: bool
    details: Dict[str, Any]
    user_address: Optional[str]
```

**Logged Events**
- Permission requests
- Permission approvals/denials
- API calls
- Resource limit violations
- Security violations
- Suspicious activity patterns

## Usage

### Installing a Mini-App

```python
from xai.mobile.mini_app_sandbox import MiniApp, MiniAppRegistry

# Create app metadata
app = MiniApp(
    app_id="calculator_v1",
    name="Calculator",
    version="1.0.0",
    developer="trusted_dev",
    description="Simple calculator app",
    icon_url="https://example.com/icon.png",
    entry_point="main",
    permissions=["storage"]  # Request storage permission
)

# Register app
registry = MiniAppRegistry(storage_path="./mini_apps")
success = registry.register_app(app)
```

### Executing Mini-App Code

```python
from xai.mobile.mini_app_sandbox import AppSandbox
from pathlib import Path

# Create sandbox
sandbox = AppSandbox(
    app=app,
    wallet_interface=wallet,
    storage_path=Path("./sandbox_data")
)

# Execute Python code
code = """
def main(x, y):
    return x + y
"""

result = sandbox.execute(
    code=code,
    language="python",
    entry_point="main",
    context={"x": 5, "y": 3}
)

print(f"Result: {result.return_value}")  # 8
```

### Permission Management

```python
from xai.sandbox.permissions import PermissionManager, Permission, PermissionLevel

# Create permission manager
pm = PermissionManager(storage_path=Path("./permissions"))

# App requests permission
pm.request_permission(
    app_id="calculator_v1",
    permission=Permission.READ_BALANCE,
    level=PermissionLevel.READ,
    duration_seconds=3600  # 1 hour
)

# User approves (would be done via UI)
pm.approve_permission(
    app_id="calculator_v1",
    permission=Permission.READ_BALANCE,
    user_address="xai1user123..."
)

# Check permission
has_perm = pm.has_permission(
    app_id="calculator_v1",
    permission=Permission.READ_BALANCE
)  # True
```

### WASM Execution

```python
# Load compiled WASM module
wasm_bytes = Path("app.wasm").read_bytes()

# Execute WASM
result = sandbox.execute(
    code=wasm_bytes,
    language="wasm",
    entry_point="_start",
    context={}
)
```

## Security Best Practices

### For App Developers

1. **Request Minimal Permissions**: Only request permissions you actually need
2. **Handle Denials Gracefully**: User may deny permissions
3. **Respect Limits**: Work within resource constraints
4. **Validate Inputs**: Don't trust context data
5. **Use WASM for Performance**: Compiled code runs faster

### For Wallet Developers

1. **Display Clear Prompts**: Show what app is requesting
2. **Educate Users**: Explain dangerous permissions
3. **Monitor Audit Logs**: Watch for suspicious patterns
4. **Update Regularly**: Keep sandbox dependencies current
5. **Test Thoroughly**: Verify isolation boundaries

### For Users

1. **Review Permissions**: Understand what app can do
2. **Trust Verified Apps**: Verified developers are safer
3. **Revoke Unused Apps**: Remove apps you don't use
4. **Check Audit Logs**: Review app activity
5. **Report Suspicious Behavior**: Flag malicious apps

## Threat Model

### Protected Against

- **Code Injection**: RestrictedPython prevents dangerous code
- **Filesystem Access**: No access without explicit permission
- **Network Exfiltration**: Network access controlled and logged
- **Resource Exhaustion**: CPU, memory, time limits enforced
- **Privilege Escalation**: Capability-based permissions
- **Private Key Theft**: KEYRING_ACCESS requires approval
- **Reentrancy**: Transaction creation requires user approval

### Not Protected Against

- **Social Engineering**: App can trick user into approving
- **Side Channels**: Timing attacks may leak info
- **UI Spoofing**: Malicious app UI can mislead
- **User Error**: User may approve dangerous permissions
- **Logic Bugs**: App bugs are app's responsibility

## Dependencies

**Required**
- Python 3.8+
- Standard library (no external deps for basic operation)

**Optional (Enhanced Security)**
- `RestrictedPython` - Safer Python execution
- `wasmer` or `wasmtime` - WASM execution
- `python-seccomp` - Syscall filtering (Linux)

**Installation**
```bash
# Basic (permission system only)
pip install -e .

# Enhanced security
pip install RestrictedPython wasmer

# Linux syscall filtering
pip install python-seccomp
```

## Testing

Run security tests:

```bash
# All sandbox tests
pytest tests/xai_tests/unit/test_sandbox_security.py -v

# Specific test classes
pytest tests/xai_tests/unit/test_sandbox_security.py::TestPermissionSystem -v
pytest tests/xai_tests/unit/test_sandbox_security.py::TestSecureExecutor -v
pytest tests/xai_tests/unit/test_sandbox_security.py::TestSecurityBoundaries -v
```

## Audit Checklist

Before deploying mini-app support:

- [ ] All tests pass
- [ ] RestrictedPython installed and working
- [ ] Resource limits tested and enforced
- [ ] Permission system requires user approval for dangerous ops
- [ ] Audit logging enabled and persisted
- [ ] Network isolation verified
- [ ] Filesystem isolation verified
- [ ] WASM runtime available (optional)
- [ ] Documentation complete
- [ ] User education materials ready

## Known Limitations

1. **RestrictedPython Not Perfect**: Determined attacker may find bypass
2. **Subprocess Overhead**: Subprocess isolation has performance cost
3. **WASM Dependencies**: Requires external runtime
4. **Platform-Specific**: Some features (seccomp) are Linux-only
5. **User Approval Required**: Can't prevent user from approving malicious app

## Future Enhancements

- [ ] Hardware-backed key isolation (TEE/SGX)
- [ ] Formal verification of sandbox boundaries
- [ ] Machine learning for anomaly detection
- [ ] Automated app security scoring
- [ ] Community-driven app verification
- [ ] Gas metering for fair resource accounting
- [ ] Sandboxed GPU access for AI apps

## References

- [RestrictedPython Documentation](https://restrictedpython.readthedocs.io/)
- [WebAssembly Security](https://webassembly.org/docs/security/)
- [Linux Seccomp](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [Capability-Based Security](https://en.wikipedia.org/wiki/Capability-based_security)

## Contact

For security issues, contact: security@xai.network

**Do not open public issues for security vulnerabilities.**
