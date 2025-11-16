import ipaddress
from functools import wraps
from flask import request, abort
import json
import os

IP_WHITELIST_CONFIG_FILE = "ip_whitelist.json"


class IPWhitelist:
    def __init__(self, config_file=IP_WHITELIST_CONFIG_FILE):
        self.config_file = os.path.join("config", config_file)
        self.whitelisted_ips = []
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.whitelisted_ips = [
                    ipaddress.ip_network(ip, strict=False)
                    for ip in config.get("whitelisted_ips", [])
                ]
        else:
            # Default to an empty whitelist if config file doesn't exist
            self.whitelisted_ips = []
            self._save_config()

    def _save_config(self):
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump({"whitelisted_ips": [str(ip) for ip in self.whitelisted_ips]}, f, indent=4)

    def add_ip(self, ip_address_or_network):
        network = ipaddress.ip_network(ip_address_or_network, strict=False)
        if network not in self.whitelisted_ips:
            self.whitelisted_ips.append(network)
            self._save_config()

    def remove_ip(self, ip_address_or_network):
        network = ipaddress.ip_network(ip_address_or_network, strict=False)
        if network in self.whitelisted_ips:
            self.whitelisted_ips.remove(network)
            self._save_config()

    def is_whitelisted(self, ip_address):
        try:
            ip = ipaddress.ip_address(ip_address)
            for whitelisted_net in self.whitelisted_ips:
                if ip in whitelisted_net:
                    return True
            return False
        except ValueError:
            return False  # Invalid IP address format

    def whitelist_required(self):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                client_ip = request.remote_addr
                if not self.is_whitelisted(client_ip):
                    abort(403, description="Forbidden: IP address not whitelisted.")
                return f(*args, **kwargs)

            return decorated_function

        return decorator


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Create a dummy config directory for testing
    os.makedirs("config", exist_ok=True)

    whitelist_manager = IPWhitelist()
    print(f"Initial Whitelist: {[str(ip) for ip in whitelist_manager.whitelisted_ips]}")

    # Add some IPs
    whitelist_manager.add_ip("127.0.0.1")
    whitelist_manager.add_ip("192.168.1.0/24")
    print(f"Whitelist after adding: {[str(ip) for ip in whitelist_manager.whitelisted_ips]}")

    # Test IP addresses
    print(f"Is '127.0.0.1' whitelisted? {whitelist_manager.is_whitelisted('127.0.0.1')}")
    print(f"Is '192.168.1.50' whitelisted? {whitelist_manager.is_whitelisted('192.168.1.50')}")
    print(f"Is '10.0.0.1' whitelisted? {whitelist_manager.is_whitelisted('10.0.0.1')}")

    # Remove an IP
    whitelist_manager.remove_ip("127.0.0.1")
    print(f"Whitelist after removing: {[str(ip) for ip in whitelist_manager.whitelisted_ips]}")
    print(f"Is '127.0.0.1' whitelisted? {whitelist_manager.is_whitelisted('127.0.0.1')}")

    # Clean up dummy config file
    os.remove(os.path.join("config", IP_WHITELIST_CONFIG_FILE))
    os.rmdir("config")
