import json
import os
from functools import wraps

RBAC_CONFIG_FILE = "rbac_config.json"


class RBAC:
    def __init__(self, config_file=RBAC_CONFIG_FILE):
        self.config_file = os.path.join(
            "config", config_file
        )  # Store config in the 'config' directory
        self.roles = {}
        self.user_roles = {}
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.roles = config.get("roles", {})
                self.user_roles = config.get("user_roles", {})
        else:
            # Initialize with some default roles if config file doesn't exist
            self.roles = {
                "admin": ["create_node", "register_peer", "manage_users", "manage_roles"],
                "validator": ["validate_block", "propose_block"],
                "user": ["send_transaction", "view_balance"],
            }
            self.user_roles = {}  # No users assigned by default
            self._save_config()

    def _save_config(self):
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump({"roles": self.roles, "user_roles": self.user_roles}, f, indent=4)

    def add_role(self, role_name, permissions):
        if role_name in self.roles:
            raise ValueError(f"Role '{role_name}' already exists.")
        self.roles[role_name] = permissions
        self._save_config()

    def assign_role(self, user_id, role_name):
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' does not exist.")
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        if role_name not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_name)
            self._save_config()

    def remove_role(self, user_id, role_name):
        if user_id in self.user_roles and role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)
            if not self.user_roles[user_id]:
                del self.user_roles[user_id]
            self._save_config()

    def get_user_permissions(self, user_id):
        permissions = set()
        for role_name in self.user_roles.get(user_id, []):
            permissions.update(self.roles.get(role_name, []))
        return list(permissions)

    def has_permission(self, user_id, permission):
        return permission in self.get_user_permissions(user_id)

    def permission_required(self, permission):
        def decorator(func):
            @wraps(func)
            def wrapper(user_id, *args, **kwargs):
                if not self.has_permission(user_id, permission):
                    raise PermissionError(
                        f"User '{user_id}' does not have permission '{permission}'."
                    )
                return func(user_id, *args, **kwargs)

            return wrapper

        return decorator


# Example Usage (for testing purposes)
if __name__ == "__main__":
    rbac_manager = RBAC()

    # Assign a user to a role
    print("Assigning 'admin_user' to 'admin' role...")
    rbac_manager.assign_role("admin_user_pubkey_hex", "admin")
    print(
        f"Permissions for admin_user: {rbac_manager.get_user_permissions('admin_user_pubkey_hex')}"
    )

    # Check permissions
    print(
        f"Admin user has 'create_node' permission: {rbac_manager.has_permission('admin_user_pubkey_hex', 'create_node')}"
    )
    print(
        f"Admin user has 'send_transaction' permission: {rbac_manager.has_permission('admin_user_pubkey_hex', 'send_transaction')}"
    )

    # Try to use a permission-protected function
    @rbac_manager.permission_required("create_node")
    def create_node_action(user, node_id):
        print(f"User {user} is creating node {node_id}")

    @rbac_manager.permission_required("send_transaction")
    def send_transaction_action(user, amount):
        print(f"User {user} is sending {amount} coins")

    try:
        create_node_action("admin_user_pubkey_hex", "node_alpha")
    except PermissionError as e:
        print(e)

    try:
        send_transaction_action("admin_user_pubkey_hex", 100)
    except PermissionError as e:
        print(e)

    # Assign a 'user' role and test
    print("\nAssigning 'regular_user' to 'user' role...")
    rbac_manager.assign_role("regular_user_pubkey_hex", "user")
    print(
        f"Permissions for regular_user: {rbac_manager.get_user_permissions('regular_user_pubkey_hex')}"
    )

    try:
        create_node_action("regular_user_pubkey_hex", "node_beta")
    except PermissionError as e:
        print(e)

    try:
        send_transaction_action("regular_user_pubkey_hex", 50)
    except PermissionError as e:
        print(e)

    # Remove a role
    print("\nRemoving 'admin' role from 'admin_user'...")
    rbac_manager.remove_role("admin_user_pubkey_hex", "admin")
    print(
        f"Permissions for admin_user after removal: {rbac_manager.get_user_permissions('admin_user_pubkey_hex')}"
    )
