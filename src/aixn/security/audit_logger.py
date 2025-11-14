import logging
import json
from datetime import datetime, timezone
import os

AUDIT_LOG_FILE = os.path.join("logs", "audit.log")

class AuditLogger:
    def __init__(self, log_file=AUDIT_LOG_FILE):
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        self.logger = logging.getLogger("audit_logger")
        self.logger.setLevel(logging.INFO)
        
        # Prevent adding multiple handlers if already configured
        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(message)s') # We'll format the message as JSON
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_action(self, user_id: str, action: str, details: dict = None, outcome: str = "SUCCESS"):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "details": details if details is not None else {}
        }
        self.logger.info(json.dumps(log_entry))

# Example Usage (for testing purposes)
if __name__ == "__main__":
    audit = AuditLogger()

    # Log a successful login
    audit.log_action(user_id="admin_user_pubkey_hex", action="login", details={"ip_address": "192.168.1.100"}, outcome="SUCCESS")

    # Log a failed administrative action
    audit.log_action(user_id="unauthorized_user", action="write_node_config", details={"config_param": "miner_address"}, outcome="FAILURE", message="Insufficient permissions")

    # Log a successful node configuration change
    audit.log_action(user_id="admin_user_pubkey_hex", action="write_node_config", details={"config_param": "rpc_port", "new_value": 18546}, outcome="SUCCESS")

    print(f"Audit logs written to {AUDIT_LOG_FILE}")
    # You can inspect the log file to see the JSON entries
```