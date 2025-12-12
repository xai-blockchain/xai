#!/usr/bin/env python3
"""
Add return type hints to 13 public API methods.

Updates:
- src/xai/core/api_blueprints/base.py: 11 functions
- src/xai/core/api_blueprints/__init__.py: 1 function
- src/xai/core/api_security.py: 1 method
"""

import os
import sys

XAI_ROOT = '/home/hudson/blockchain-projects/xai'

def main():
    print("Adding return type hints to API methods...\n")

    # File 1: base.py (11 functions)
    print("Updating base.py...")
    base_py_path = f'{XAI_ROOT}/src/xai/core/api_blueprints/base.py'
    with open(base_py_path, 'r') as f:
        lines = f.readlines()

    # Make all replacements (0-indexed, so line N is index N-1)
    lines[23] = lines[23].replace('def get_api_context():', 'def get_api_context() -> Dict[str, Any]:')
    lines[31] = lines[31].replace('def get_node():', 'def get_node() -> Any:')
    lines[37] = lines[37].replace('def get_blockchain():', 'def get_blockchain() -> Any:')
    lines[43] = lines[43].replace('def get_peer_manager():', 'def get_peer_manager() -> Optional[Any]:')
    lines[49] = lines[49].replace('def get_api_auth():', 'def get_api_auth() -> Optional[Any]:')
    lines[55] = lines[55].replace('def get_error_registry():', 'def get_error_registry() -> Optional[Any]:')
    lines[61] = lines[61].replace('def get_spending_limits():', 'def get_spending_limits() -> Optional[Any]:')
    lines[77] = lines[77].replace('def success_response(payload: Dict[str, Any], status: int = 200):',
                                   'def success_response(payload: Dict[str, Any], status: int = 200) -> Tuple[Any, int]:')
    lines[89] = lines[89].replace('):', ') -> Tuple[Any, int]:')
    lines[97] = lines[97].replace('def handle_exception(error: Exception, context_str: str, status: int = 500):',
                                   'def handle_exception(error: Exception, context_str: str, status: int = 500) -> Tuple[Any, int]:')
    lines[127] = lines[127].replace('def require_api_auth():', 'def require_api_auth() -> Optional[Tuple[Any, int]]:')
    lines[147] = lines[147].replace('def require_admin_auth():', 'def require_admin_auth() -> Optional[Tuple[Any, int]]:')

    with open(base_py_path, 'w') as f:
        f.writelines(lines)
    print(f'  ✓ Updated {base_py_path} (11 functions)')

    # File 2: __init__.py (1 function)
    print("Updating __init__.py...")
    init_py_path = f'{XAI_ROOT}/src/xai/core/api_blueprints/__init__.py'
    with open(init_py_path, 'r') as f:
        lines = f.readlines()

    lines[88] = lines[88].replace('def inject_api_context():', 'def inject_api_context() -> None:')

    with open(init_py_path, 'w') as f:
        f.writelines(lines)
    print(f'  ✓ Updated {init_py_path} (1 function)')

    # File 3: api_security.py (1 method)
    print("Updating api_security.py...")
    api_security_path = f'{XAI_ROOT}/src/xai/core/api_security.py'
    with open(api_security_path, 'r') as f:
        lines = f.readlines()

    lines[47] = lines[47].replace('def enforce_request(self):', 'def enforce_request(self) -> None:')

    with open(api_security_path, 'w') as f:
        f.writelines(lines)
    print(f'  ✓ Updated {api_security_path} (1 method)')

    print('\n✓ All 13 return type hints added successfully!')
    print('\nModified files:')
    print(f'  - {base_py_path}')
    print(f'  - {init_py_path}')
    print(f'  - {api_security_path}')

    return 0

if __name__ == '__main__':
    sys.exit(main())
