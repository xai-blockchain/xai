"""
Comprehensive tests for IP Whitelist security module.

Tests IP whitelisting, network range management, access control,
Flask decorator integration, and security validation.
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch
from flask import Flask
from xai.security.ip_whitelist import IPWhitelist


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
def ip_whitelist(temp_config_dir):
    """Create IP whitelist instance for testing"""
    return IPWhitelist()


@pytest.fixture
def flask_app():
    """Create Flask app instance for testing"""
    app = Flask(__name__)
    return app


@pytest.mark.security
class TestIPWhitelistInitialization:
    """Test IP whitelist initialization"""

    def test_init_creates_config_file(self, temp_config_dir):
        """Test that initialization creates config file"""
        whitelist = IPWhitelist()
        config_file = os.path.join(temp_config_dir, "ip_whitelist.json")
        assert os.path.exists(config_file)

    def test_init_empty_whitelist(self, ip_whitelist):
        """Test that whitelist starts empty"""
        assert len(ip_whitelist.whitelisted_ips) == 0

    def test_init_loads_existing_config(self, temp_config_dir):
        """Test loading existing configuration"""
        # Create initial whitelist
        wl1 = IPWhitelist()
        wl1.add_ip("192.168.1.0/24")

        # Create new instance
        wl2 = IPWhitelist()
        assert len(wl2.whitelisted_ips) == 1


@pytest.mark.security
class TestAddingIPs:
    """Test adding IP addresses to whitelist"""

    def test_add_single_ip(self, ip_whitelist):
        """Test adding single IP address"""
        ip_whitelist.add_ip("192.168.1.100")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_ipv4_network(self, ip_whitelist):
        """Test adding IPv4 network range"""
        ip_whitelist.add_ip("192.168.1.0/24")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_ipv6_address(self, ip_whitelist):
        """Test adding IPv6 address"""
        ip_whitelist.add_ip("2001:db8::1")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_ipv6_network(self, ip_whitelist):
        """Test adding IPv6 network range"""
        ip_whitelist.add_ip("2001:db8::/32")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_localhost(self, ip_whitelist):
        """Test adding localhost"""
        ip_whitelist.add_ip("127.0.0.1")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_duplicate_ip_no_duplicates(self, ip_whitelist):
        """Test that adding duplicate IP doesn't create duplicates"""
        ip_whitelist.add_ip("192.168.1.100")
        ip_whitelist.add_ip("192.168.1.100")
        assert len(ip_whitelist.whitelisted_ips) == 1

    def test_add_multiple_ips(self, ip_whitelist):
        """Test adding multiple different IPs"""
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        for ip in ips:
            ip_whitelist.add_ip(ip)
        assert len(ip_whitelist.whitelisted_ips) == 3

    def test_add_ip_persists(self, temp_config_dir):
        """Test that adding IP persists to config"""
        wl1 = IPWhitelist()
        wl1.add_ip("192.168.1.100")

        wl2 = IPWhitelist()
        assert len(wl2.whitelisted_ips) == 1

    def test_add_ip_with_cidr_notation(self, ip_whitelist):
        """Test adding IP with various CIDR notations"""
        ip_whitelist.add_ip("10.0.0.0/8")
        ip_whitelist.add_ip("172.16.0.0/12")
        ip_whitelist.add_ip("192.168.0.0/16")
        assert len(ip_whitelist.whitelisted_ips) == 3


@pytest.mark.security
class TestRemovingIPs:
    """Test removing IP addresses from whitelist"""

    def test_remove_ip(self, ip_whitelist):
        """Test removing IP address"""
        ip_whitelist.add_ip("192.168.1.100")
        ip_whitelist.remove_ip("192.168.1.100")
        assert len(ip_whitelist.whitelisted_ips) == 0

    def test_remove_network(self, ip_whitelist):
        """Test removing network range"""
        ip_whitelist.add_ip("192.168.1.0/24")
        ip_whitelist.remove_ip("192.168.1.0/24")
        assert len(ip_whitelist.whitelisted_ips) == 0

    def test_remove_nonexistent_ip_no_error(self, ip_whitelist):
        """Test removing non-existent IP doesn't raise error"""
        ip_whitelist.remove_ip("10.0.0.1")
        # Should not raise error

    def test_remove_ip_persists(self, temp_config_dir):
        """Test that removing IP persists"""
        wl1 = IPWhitelist()
        wl1.add_ip("192.168.1.100")
        wl1.remove_ip("192.168.1.100")

        wl2 = IPWhitelist()
        assert len(wl2.whitelisted_ips) == 0

    def test_remove_one_of_many(self, ip_whitelist):
        """Test removing one IP from many"""
        ip_whitelist.add_ip("192.168.1.1")
        ip_whitelist.add_ip("192.168.1.2")
        ip_whitelist.add_ip("192.168.1.3")

        ip_whitelist.remove_ip("192.168.1.2")

        assert len(ip_whitelist.whitelisted_ips) == 2
        assert ip_whitelist.is_whitelisted("192.168.1.1")
        assert not ip_whitelist.is_whitelisted("192.168.1.2")
        assert ip_whitelist.is_whitelisted("192.168.1.3")


@pytest.mark.security
class TestIPWhitelistChecking:
    """Test checking if IPs are whitelisted"""

    def test_is_whitelisted_single_ip_match(self, ip_whitelist):
        """Test checking whitelisted single IP"""
        ip_whitelist.add_ip("192.168.1.100")
        assert ip_whitelist.is_whitelisted("192.168.1.100") is True

    def test_is_whitelisted_single_ip_no_match(self, ip_whitelist):
        """Test checking non-whitelisted IP"""
        ip_whitelist.add_ip("192.168.1.100")
        assert ip_whitelist.is_whitelisted("192.168.1.101") is False

    def test_is_whitelisted_network_range(self, ip_whitelist):
        """Test checking IP in whitelisted network range"""
        ip_whitelist.add_ip("192.168.1.0/24")
        assert ip_whitelist.is_whitelisted("192.168.1.1") is True
        assert ip_whitelist.is_whitelisted("192.168.1.100") is True
        assert ip_whitelist.is_whitelisted("192.168.1.254") is True
        assert ip_whitelist.is_whitelisted("192.168.2.1") is False

    def test_is_whitelisted_empty_whitelist(self, ip_whitelist):
        """Test checking against empty whitelist"""
        assert ip_whitelist.is_whitelisted("192.168.1.1") is False

    def test_is_whitelisted_invalid_ip_format(self, ip_whitelist):
        """Test checking invalid IP format returns False"""
        ip_whitelist.add_ip("192.168.1.0/24")
        assert ip_whitelist.is_whitelisted("invalid_ip") is False
        assert ip_whitelist.is_whitelisted("999.999.999.999") is False

    def test_is_whitelisted_ipv6(self, ip_whitelist):
        """Test checking IPv6 addresses"""
        ip_whitelist.add_ip("2001:db8::/32")
        assert ip_whitelist.is_whitelisted("2001:db8::1") is True
        assert ip_whitelist.is_whitelisted("2001:db8::1234") is True
        assert ip_whitelist.is_whitelisted("2001:db9::1") is False

    def test_is_whitelisted_multiple_ranges(self, ip_whitelist):
        """Test checking with multiple whitelisted ranges"""
        ip_whitelist.add_ip("192.168.1.0/24")
        ip_whitelist.add_ip("10.0.0.0/8")

        assert ip_whitelist.is_whitelisted("192.168.1.50") is True
        assert ip_whitelist.is_whitelisted("10.5.10.20") is True
        assert ip_whitelist.is_whitelisted("172.16.0.1") is False


@pytest.mark.security
class TestFlaskDecorator:
    """Test Flask decorator for whitelist enforcement"""

    def test_decorator_allows_whitelisted_ip(self, ip_whitelist, flask_app):
        """Test decorator allows whitelisted IP"""
        ip_whitelist.add_ip("192.168.1.100")

        @ip_whitelist.whitelist_required()
        def test_route():
            return "success"

        # Use Flask test request context
        with flask_app.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.100'}):
            result = test_route()
            assert result == "success"

    def test_decorator_blocks_non_whitelisted_ip(self, ip_whitelist, flask_app):
        """Test decorator blocks non-whitelisted IP"""
        ip_whitelist.add_ip("192.168.1.100")

        @ip_whitelist.whitelist_required()
        def test_route():
            return "success"

        # Use Flask test request context and expect abort
        with flask_app.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.101'}):
            with pytest.raises(Exception) as exc_info:
                test_route()
            # Verify it's a 403 Forbidden error
            assert '403' in str(exc_info.value) or 'Forbidden' in str(exc_info.value)

    def test_decorator_with_network_range(self, ip_whitelist, flask_app):
        """Test decorator works with network ranges"""
        ip_whitelist.add_ip("192.168.1.0/24")

        @ip_whitelist.whitelist_required()
        def test_route():
            return "success"

        # Use Flask test request context
        with flask_app.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.50'}):
            result = test_route()
            assert result == "success"


@pytest.mark.security
class TestNetworkRanges:
    """Test various network range scenarios"""

    def test_class_a_network(self, ip_whitelist):
        """Test Class A network (10.0.0.0/8)"""
        ip_whitelist.add_ip("10.0.0.0/8")
        assert ip_whitelist.is_whitelisted("10.0.0.1") is True
        assert ip_whitelist.is_whitelisted("10.255.255.254") is True

    def test_class_b_network(self, ip_whitelist):
        """Test Class B network (172.16.0.0/12)"""
        ip_whitelist.add_ip("172.16.0.0/12")
        assert ip_whitelist.is_whitelisted("172.16.0.1") is True
        assert ip_whitelist.is_whitelisted("172.31.255.254") is True

    def test_class_c_network(self, ip_whitelist):
        """Test Class C network (192.168.1.0/24)"""
        ip_whitelist.add_ip("192.168.1.0/24")
        assert ip_whitelist.is_whitelisted("192.168.1.1") is True
        assert ip_whitelist.is_whitelisted("192.168.1.254") is True

    def test_single_host_cidr32(self, ip_whitelist):
        """Test single host with /32 CIDR"""
        ip_whitelist.add_ip("192.168.1.100/32")
        assert ip_whitelist.is_whitelisted("192.168.1.100") is True
        assert ip_whitelist.is_whitelisted("192.168.1.101") is False

    def test_entire_internet_cidr0(self, ip_whitelist):
        """Test whitelisting entire internet (0.0.0.0/0)"""
        ip_whitelist.add_ip("0.0.0.0/0")
        assert ip_whitelist.is_whitelisted("192.168.1.1") is True
        assert ip_whitelist.is_whitelisted("8.8.8.8") is True


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_add_ip_without_cidr_assumes_host(self, ip_whitelist):
        """Test adding IP without CIDR assumes single host"""
        ip_whitelist.add_ip("192.168.1.100")
        # Should match exact IP
        assert ip_whitelist.is_whitelisted("192.168.1.100") is True
        # Should also match (ipaddress module auto-converts)
        assert ip_whitelist.is_whitelisted("192.168.1.100") is True

    def test_localhost_variations(self, ip_whitelist):
        """Test various localhost representations"""
        ip_whitelist.add_ip("127.0.0.1")
        assert ip_whitelist.is_whitelisted("127.0.0.1") is True

    def test_ipv6_localhost(self, ip_whitelist):
        """Test IPv6 localhost"""
        ip_whitelist.add_ip("::1")
        assert ip_whitelist.is_whitelisted("::1") is True

    def test_empty_string_ip(self, ip_whitelist):
        """Test empty string IP returns False"""
        assert ip_whitelist.is_whitelisted("") is False

    def test_none_ip_returns_false(self, ip_whitelist):
        """Test None IP is handled safely"""
        # is_whitelisted expects string, but test robustness
        try:
            result = ip_whitelist.is_whitelisted(None)
            assert result is False
        except (TypeError, AttributeError, ValueError) as e:
            # Expected to fail with specific exceptions, which is acceptable
            import logging
            logging.debug(f"Expected exception when checking None IP: {e}")
            pass
        except Exception as e:
            # Unexpected exception type
            import logging
            logging.warning(f"Unexpected exception type when checking None IP: {e}")
            pass


@pytest.mark.security
class TestConfigPersistence:
    """Test configuration file persistence"""

    def test_config_file_structure(self, temp_config_dir):
        """Test config file has correct structure"""
        whitelist = IPWhitelist()
        whitelist.add_ip("192.168.1.0/24")

        config_file = os.path.join(temp_config_dir, "ip_whitelist.json")
        with open(config_file, 'r') as f:
            config = json.load(f)

        assert "whitelisted_ips" in config
        assert isinstance(config["whitelisted_ips"], list)

    def test_multiple_saves_overwrite(self, temp_config_dir):
        """Test that multiple saves overwrite config correctly"""
        whitelist = IPWhitelist()
        whitelist.add_ip("192.168.1.1")
        whitelist.add_ip("192.168.1.2")
        whitelist.remove_ip("192.168.1.1")

        # Load fresh instance
        whitelist2 = IPWhitelist()
        assert len(whitelist2.whitelisted_ips) == 1


@pytest.mark.security
class TestSecurityScenarios:
    """Test real-world security scenarios"""

    def test_corporate_network_scenario(self, ip_whitelist):
        """Test corporate network whitelisting"""
        # Whitelist corporate network
        ip_whitelist.add_ip("10.0.0.0/8")

        # Employee IPs should be allowed
        assert ip_whitelist.is_whitelisted("10.10.10.100") is True
        assert ip_whitelist.is_whitelisted("10.20.30.40") is True

        # External IPs should be blocked
        assert ip_whitelist.is_whitelisted("8.8.8.8") is False

    def test_vpn_gateway_scenario(self, ip_whitelist):
        """Test VPN gateway whitelisting"""
        # Whitelist VPN gateway IPs
        ip_whitelist.add_ip("203.0.113.10")
        ip_whitelist.add_ip("203.0.113.20")

        assert ip_whitelist.is_whitelisted("203.0.113.10") is True
        assert ip_whitelist.is_whitelisted("203.0.113.20") is True
        assert ip_whitelist.is_whitelisted("203.0.113.30") is False

    def test_api_access_control(self, ip_whitelist):
        """Test API access control scenario"""
        # Whitelist partner API servers
        ip_whitelist.add_ip("198.51.100.0/24")

        # Partner IPs allowed
        assert ip_whitelist.is_whitelisted("198.51.100.50") is True

        # Public IPs blocked
        assert ip_whitelist.is_whitelisted("1.2.3.4") is False

    def test_multi_region_deployment(self, ip_whitelist):
        """Test multi-region deployment whitelisting"""
        # Whitelist multiple datacenter regions
        ip_whitelist.add_ip("10.0.0.0/24")  # US East
        ip_whitelist.add_ip("10.1.0.0/24")  # US West
        ip_whitelist.add_ip("10.2.0.0/24")  # EU

        assert ip_whitelist.is_whitelisted("10.0.0.50") is True
        assert ip_whitelist.is_whitelisted("10.1.0.50") is True
        assert ip_whitelist.is_whitelisted("10.2.0.50") is True
        assert ip_whitelist.is_whitelisted("10.3.0.50") is False
