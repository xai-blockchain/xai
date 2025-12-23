import ipaddress
import json
import logging
import os
from functools import wraps

from flask import abort, request

IP_WHITELIST_CONFIG_FILE = "ip_whitelist.json"
logger = logging.getLogger(__name__)


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
            logger.info("IP added to whitelist", extra={"event": "ip_whitelist.add", "network": str(network)})

    def remove_ip(self, ip_address_or_network):
        network = ipaddress.ip_network(ip_address_or_network, strict=False)
        if network in self.whitelisted_ips:
            self.whitelisted_ips.remove(network)
            self._save_config()
            logger.info("IP removed from whitelist", extra={"event": "ip_whitelist.remove", "network": str(network)})

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
# Example usage is intentionally omitted in production modules.
