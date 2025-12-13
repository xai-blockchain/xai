"""
Comprehensive tests for Role-Based Access Control (RBAC) security module.

Tests role management, user-role assignments, permission checking,
decorators, file persistence, and access control scenarios.
"""

import pytest
import os
import json
import tempfile
import shutil
from xai.security.rbac import RBAC


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing"""
    temp_dir = tempfile.mkdtemp()
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    yield config_dir
    os.chdir(original_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def rbac_manager(temp_config_dir):
    """Create RBAC manager instance for testing"""
    return RBAC()


@pytest.mark.security
class TestRBACInitialization:
    """Test RBAC initialization and configuration loading"""

    def test_init_with_default_roles(self, temp_config_dir):
        """Test initialization creates default roles"""
        rbac = RBAC()
        assert "admin" in rbac.roles
        assert "validator" in rbac.roles
        assert "user" in rbac.roles
        assert rbac.user_roles == {}

    def test_default_admin_permissions(self, rbac_manager):
        """Test default admin role has correct permissions"""
        admin_perms = rbac_manager.roles["admin"]
        assert "create_node" in admin_perms
        assert "register_peer" in admin_perms
        assert "manage_users" in admin_perms
        assert "manage_roles" in admin_perms

    def test_default_validator_permissions(self, rbac_manager):
        """Test default validator role has correct permissions"""
        validator_perms = rbac_manager.roles["validator"]
        assert "validate_block" in validator_perms
        assert "propose_block" in validator_perms

    def test_default_user_permissions(self, rbac_manager):
        """Test default user role has correct permissions"""
        user_perms = rbac_manager.roles["user"]
        assert "send_transaction" in user_perms
        assert "view_balance" in user_perms

    def test_config_file_created(self, temp_config_dir):
        """Test that config file is created on initialization"""
        rbac = RBAC()
        config_file = os.path.join(temp_config_dir, "rbac_config.json")
        assert os.path.exists(config_file)

    def test_config_file_has_correct_structure(self, temp_config_dir):
        """Test that config file has correct JSON structure"""
        rbac = RBAC()
        config_file = os.path.join(temp_config_dir, "rbac_config.json")
        with open(config_file, 'r') as f:
            config = json.load(f)
        assert "roles" in config
        assert "user_roles" in config

    def test_load_existing_config(self, temp_config_dir):
        """Test loading from existing config file"""
        # Create initial RBAC
        rbac1 = RBAC()
        rbac1.assign_role("user123", "admin")

        # Create new RBAC instance that should load existing config
        rbac2 = RBAC()
        assert "user123" in rbac2.user_roles
        assert "admin" in rbac2.user_roles["user123"]


@pytest.mark.security
class TestRoleManagement:
    """Test role creation and management"""

    def test_add_new_role(self, rbac_manager):
        """Test adding a new role"""
        permissions = ["deploy_contract", "call_contract"]
        rbac_manager.add_role("developer", permissions)
        assert "developer" in rbac_manager.roles
        assert rbac_manager.roles["developer"] == permissions

    def test_add_role_persists(self, temp_config_dir):
        """Test that adding a role persists to config file"""
        rbac = RBAC()
        rbac.add_role("moderator", ["ban_user", "delete_post"])

        # Load new instance
        rbac2 = RBAC()
        assert "moderator" in rbac2.roles
        assert "ban_user" in rbac2.roles["moderator"]

    def test_add_duplicate_role_raises_error(self, rbac_manager):
        """Test that adding duplicate role raises ValueError"""
        with pytest.raises(ValueError, match="Role 'admin' already exists"):
            rbac_manager.add_role("admin", ["some_permission"])

    def test_add_role_with_empty_permissions(self, rbac_manager):
        """Test adding role with empty permissions list"""
        rbac_manager.add_role("guest", [])
        assert "guest" in rbac_manager.roles
        assert rbac_manager.roles["guest"] == []

    def test_add_multiple_roles(self, rbac_manager):
        """Test adding multiple different roles"""
        rbac_manager.add_role("developer", ["deploy", "test"])
        rbac_manager.add_role("auditor", ["view_logs", "view_transactions"])
        rbac_manager.add_role("support", ["view_tickets", "respond"])

        assert len(rbac_manager.roles) >= 6  # 3 default + 3 added

    def test_add_role_with_complex_permissions(self, rbac_manager):
        """Test adding role with many permissions"""
        permissions = [f"permission_{i}" for i in range(50)]
        rbac_manager.add_role("super_admin", permissions)
        assert len(rbac_manager.roles["super_admin"]) == 50


@pytest.mark.security
class TestUserRoleAssignment:
    """Test assigning roles to users"""

    def test_assign_role_to_user(self, rbac_manager):
        """Test assigning a role to a user"""
        rbac_manager.assign_role("user_alice", "admin")
        assert "user_alice" in rbac_manager.user_roles
        assert "admin" in rbac_manager.user_roles["user_alice"]

    def test_assign_role_persists(self, temp_config_dir):
        """Test that role assignment persists"""
        rbac = RBAC()
        rbac.assign_role("user_bob", "validator")

        rbac2 = RBAC()
        assert "user_bob" in rbac2.user_roles
        assert "validator" in rbac2.user_roles["user_bob"]

    def test_assign_nonexistent_role_raises_error(self, rbac_manager):
        """Test assigning non-existent role raises ValueError"""
        with pytest.raises(ValueError, match="Role 'nonexistent' does not exist"):
            rbac_manager.assign_role("user_charlie", "nonexistent")

    def test_assign_multiple_roles_to_user(self, rbac_manager):
        """Test assigning multiple roles to same user"""
        rbac_manager.assign_role("user_dave", "admin")
        rbac_manager.assign_role("user_dave", "validator")
        rbac_manager.assign_role("user_dave", "user")

        assert len(rbac_manager.user_roles["user_dave"]) == 3
        assert "admin" in rbac_manager.user_roles["user_dave"]
        assert "validator" in rbac_manager.user_roles["user_dave"]
        assert "user" in rbac_manager.user_roles["user_dave"]

    def test_assign_same_role_twice_is_idempotent(self, rbac_manager):
        """Test assigning same role twice doesn't duplicate"""
        rbac_manager.assign_role("user_eve", "admin")
        rbac_manager.assign_role("user_eve", "admin")
        assert rbac_manager.user_roles["user_eve"].count("admin") == 1

    def test_assign_role_to_multiple_users(self, rbac_manager):
        """Test assigning same role to multiple users"""
        for i in range(10):
            rbac_manager.assign_role(f"user_{i}", "validator")

        assert len(rbac_manager.user_roles) == 10
        for i in range(10):
            assert "validator" in rbac_manager.user_roles[f"user_{i}"]


@pytest.mark.security
class TestRoleRemoval:
    """Test removing roles from users"""

    def test_remove_role_from_user(self, rbac_manager):
        """Test removing a role from a user"""
        rbac_manager.assign_role("user_frank", "admin")
        rbac_manager.remove_role("user_frank", "admin")
        assert "user_frank" not in rbac_manager.user_roles

    def test_remove_role_persists(self, temp_config_dir):
        """Test that role removal persists"""
        rbac = RBAC()
        rbac.assign_role("user_george", "admin")
        rbac.remove_role("user_george", "admin")

        rbac2 = RBAC()
        assert "user_george" not in rbac2.user_roles

    def test_remove_one_of_multiple_roles(self, rbac_manager):
        """Test removing one role when user has multiple"""
        rbac_manager.assign_role("user_helen", "admin")
        rbac_manager.assign_role("user_helen", "validator")
        rbac_manager.remove_role("user_helen", "admin")

        assert "user_helen" in rbac_manager.user_roles
        assert "admin" not in rbac_manager.user_roles["user_helen"]
        assert "validator" in rbac_manager.user_roles["user_helen"]

    def test_remove_nonexistent_role_no_error(self, rbac_manager):
        """Test removing non-existent role doesn't raise error"""
        rbac_manager.assign_role("user_ivan", "user")
        rbac_manager.remove_role("user_ivan", "admin")  # Not assigned
        # Should not raise error

    def test_remove_role_from_nonexistent_user_no_error(self, rbac_manager):
        """Test removing role from non-existent user doesn't raise error"""
        rbac_manager.remove_role("nonexistent_user", "admin")
        # Should not raise error

    def test_remove_last_role_deletes_user_entry(self, rbac_manager):
        """Test that removing last role deletes user from user_roles"""
        rbac_manager.assign_role("user_judy", "admin")
        rbac_manager.remove_role("user_judy", "admin")
        assert "user_judy" not in rbac_manager.user_roles


@pytest.mark.security
class TestPermissionChecking:
    """Test permission checking functionality"""

    def test_get_user_permissions_single_role(self, rbac_manager):
        """Test getting permissions for user with single role"""
        rbac_manager.assign_role("user_kate", "admin")
        perms = rbac_manager.get_user_permissions("user_kate")
        assert "create_node" in perms
        assert "manage_users" in perms

    def test_get_user_permissions_multiple_roles(self, rbac_manager):
        """Test getting permissions for user with multiple roles"""
        rbac_manager.assign_role("user_leo", "admin")
        rbac_manager.assign_role("user_leo", "validator")
        perms = rbac_manager.get_user_permissions("user_leo")

        # Should have permissions from both roles
        assert "create_node" in perms  # from admin
        assert "validate_block" in perms  # from validator

    def test_get_user_permissions_no_roles(self, rbac_manager):
        """Test getting permissions for user with no roles"""
        perms = rbac_manager.get_user_permissions("user_mike")
        assert perms == []

    def test_get_user_permissions_removes_duplicates(self, rbac_manager):
        """Test that duplicate permissions are removed"""
        rbac_manager.add_role("role1", ["perm1", "perm2"])
        rbac_manager.add_role("role2", ["perm2", "perm3"])
        rbac_manager.assign_role("user_nancy", "role1")
        rbac_manager.assign_role("user_nancy", "role2")

        perms = rbac_manager.get_user_permissions("user_nancy")
        assert perms.count("perm2") == 1
        assert len(perms) == 3

    def test_has_permission_true(self, rbac_manager):
        """Test has_permission returns True for valid permission"""
        rbac_manager.assign_role("user_oscar", "admin")
        assert rbac_manager.has_permission("user_oscar", "create_node") is True

    def test_has_permission_false(self, rbac_manager):
        """Test has_permission returns False for invalid permission"""
        rbac_manager.assign_role("user_paul", "user")
        assert rbac_manager.has_permission("user_paul", "create_node") is False

    def test_has_permission_no_roles(self, rbac_manager):
        """Test has_permission returns False for user with no roles"""
        assert rbac_manager.has_permission("user_quinn", "any_permission") is False


@pytest.mark.security
class TestPermissionDecorator:
    """Test permission_required decorator"""

    def test_decorator_allows_authorized_user(self, rbac_manager):
        """Test decorator allows user with required permission"""
        rbac_manager.assign_role("user_rachel", "admin")

        @rbac_manager.permission_required("create_node")
        def create_node(user_id):
            return f"Node created by {user_id}"

        result = create_node("user_rachel")
        assert result == "Node created by user_rachel"

    def test_decorator_blocks_unauthorized_user(self, rbac_manager):
        """Test decorator blocks user without required permission"""
        rbac_manager.assign_role("user_sam", "user")

        @rbac_manager.permission_required("create_node")
        def create_node(user_id):
            return f"Node created by {user_id}"

        with pytest.raises(PermissionError, match="does not have permission 'create_node'"):
            create_node("user_sam")

    def test_decorator_blocks_user_with_no_roles(self, rbac_manager):
        """Test decorator blocks user with no roles"""
        @rbac_manager.permission_required("send_transaction")
        def send_tx(user_id, amount):
            return f"{user_id} sent {amount}"

        with pytest.raises(PermissionError):
            send_tx("user_tina", 100)

    def test_decorator_with_multiple_parameters(self, rbac_manager):
        """Test decorator works with functions with multiple parameters"""
        rbac_manager.assign_role("user_uma", "validator")

        @rbac_manager.permission_required("validate_block")
        def validate_block(user_id, block_hash, block_height):
            return f"{user_id} validated block {block_hash} at height {block_height}"

        result = validate_block("user_uma", "abc123", 100)
        assert "validated block abc123" in result

    def test_decorator_with_kwargs(self, rbac_manager):
        """Test decorator works with keyword arguments"""
        rbac_manager.assign_role("user_victor", "admin")

        @rbac_manager.permission_required("manage_users")
        def manage_user(user_id, action=None, target_user=None):
            return f"{user_id} performed {action} on {target_user}"

        result = manage_user("user_victor", action="ban", target_user="user_xyz")
        assert "performed ban on user_xyz" in result

    def test_decorator_preserves_function_metadata(self, rbac_manager):
        """Test that decorator preserves function metadata"""
        @rbac_manager.permission_required("create_node")
        def create_node(user_id):
            """Create a new node"""
            return "created"

        assert create_node.__name__ == "create_node"
        assert create_node.__doc__ == "Create a new node"


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_user_id_with_special_characters(self, rbac_manager):
        """Test user IDs with special characters"""
        user_id = "user@domain.com"
        rbac_manager.assign_role(user_id, "admin")
        assert rbac_manager.has_permission(user_id, "create_node")

    def test_user_id_with_spaces(self, rbac_manager):
        """Test user IDs with spaces"""
        user_id = "User With Spaces"
        rbac_manager.assign_role(user_id, "validator")
        perms = rbac_manager.get_user_permissions(user_id)
        assert len(perms) > 0

    def test_very_long_user_id(self, rbac_manager):
        """Test very long user ID"""
        user_id = "a" * 1000
        rbac_manager.assign_role(user_id, "user")
        assert rbac_manager.has_permission(user_id, "send_transaction")

    def test_permission_name_case_sensitive(self, rbac_manager):
        """Test that permission names are case-sensitive"""
        rbac_manager.assign_role("user_wendy", "admin")
        assert rbac_manager.has_permission("user_wendy", "create_node") is True
        assert rbac_manager.has_permission("user_wendy", "CREATE_NODE") is False

    def test_role_name_case_sensitive(self, rbac_manager):
        """Test that role names are case-sensitive"""
        rbac_manager.add_role("Admin", ["perm1"])
        assert "Admin" in rbac_manager.roles
        assert "admin" in rbac_manager.roles
        assert rbac_manager.roles["Admin"] != rbac_manager.roles["admin"]

    def test_empty_string_user_id(self, rbac_manager):
        """Test empty string as user ID"""
        rbac_manager.assign_role("", "admin")
        assert "" in rbac_manager.user_roles

    def test_role_with_unicode_permissions(self, rbac_manager):
        """Test role with unicode permission names"""
        rbac_manager.add_role("international", ["创建节点", "验证区块"])
        rbac_manager.assign_role("user_xavier", "international")
        assert rbac_manager.has_permission("user_xavier", "创建节点")


@pytest.mark.security
class TestConcurrentAccess:
    """Test scenarios with multiple RBAC instances"""

    def test_multiple_instances_share_config(self, temp_config_dir):
        """Test that multiple instances share the same config file"""
        rbac1 = RBAC()
        rbac1.assign_role("user_yara", "admin")

        rbac2 = RBAC()
        assert "user_yara" in rbac2.user_roles

    def test_changes_in_one_instance_persist_for_new_instances(self, temp_config_dir):
        """Test that changes persist across instance recreation"""
        rbac1 = RBAC()
        rbac1.add_role("custom_role", ["custom_perm"])
        rbac1.assign_role("user_zara", "custom_role")

        rbac2 = RBAC()
        assert "custom_role" in rbac2.roles
        assert rbac2.has_permission("user_zara", "custom_perm")


@pytest.mark.security
class TestComplexScenarios:
    """Test complex real-world scenarios"""

    def test_hierarchical_role_system(self, rbac_manager):
        """Test implementing hierarchical roles"""
        # Create role hierarchy
        rbac_manager.add_role("super_admin", ["*"])
        rbac_manager.add_role("operator", ["start_node", "stop_node", "view_logs"])
        rbac_manager.add_role("viewer", ["view_logs", "view_status"])

        # Assign roles
        rbac_manager.assign_role("alice", "super_admin")
        rbac_manager.assign_role("bob", "operator")
        rbac_manager.assign_role("charlie", "viewer")

        # Verify permissions
        assert rbac_manager.has_permission("alice", "*")
        assert rbac_manager.has_permission("bob", "start_node")
        assert rbac_manager.has_permission("charlie", "view_logs")
        assert not rbac_manager.has_permission("charlie", "start_node")

    def test_dynamic_role_modification(self, rbac_manager):
        """Test modifying roles dynamically"""
        # Create initial role
        rbac_manager.add_role("dynamic_role", ["perm1", "perm2"])
        rbac_manager.assign_role("user_dynamic", "dynamic_role")

        # User has initial permissions
        assert rbac_manager.has_permission("user_dynamic", "perm1")

        # Modify role by creating new one
        rbac_manager.add_role("dynamic_role_v2", ["perm1", "perm2", "perm3"])
        rbac_manager.remove_role("user_dynamic", "dynamic_role")
        rbac_manager.assign_role("user_dynamic", "dynamic_role_v2")

        # User now has updated permissions
        assert rbac_manager.has_permission("user_dynamic", "perm3")

    def test_multi_tenant_isolation(self, rbac_manager):
        """Test multi-tenant access control"""
        # Create tenant-specific roles
        rbac_manager.add_role("tenant_a_admin", ["access_tenant_a"])
        rbac_manager.add_role("tenant_b_admin", ["access_tenant_b"])

        rbac_manager.assign_role("admin_a", "tenant_a_admin")
        rbac_manager.assign_role("admin_b", "tenant_b_admin")

        # Verify isolation
        assert rbac_manager.has_permission("admin_a", "access_tenant_a")
        assert not rbac_manager.has_permission("admin_a", "access_tenant_b")
        assert rbac_manager.has_permission("admin_b", "access_tenant_b")
        assert not rbac_manager.has_permission("admin_b", "access_tenant_a")
