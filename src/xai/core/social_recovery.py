"""
AXN Social Recovery System
Allow users to designate trusted guardians who can vote to recover a lost wallet
"""

import json
import time
import uuid
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class SocialRecoveryManager:
    """Manage social recovery configurations and requests for AXN wallets"""

    def __init__(self, data_dir: str = None):
        """Initialize the Social Recovery Manager

        Args:
            data_dir: Directory to store recovery data (default: ./recovery_data)
        """
        if data_dir is None:
            self.data_dir = Path("./recovery_data")
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.configs_file = self.data_dir / "recovery_configs.json"
        self.requests_file = self.data_dir / "recovery_requests.json"

        # In-memory storage
        self.recovery_configs: Dict[str, dict] = {}  # owner_address -> config
        self.recovery_requests: Dict[str, dict] = {}  # request_id -> request

        # Load existing data
        self._load_data()

        # Configuration
        self.default_waiting_period = 7 * 24 * 60 * 60  # 7 days in seconds
        self.min_guardians = 2
        self.max_guardians = 5

    def _load_data(self):
        """Load recovery data from JSON files"""
        try:
            if self.configs_file.exists():
                with open(self.configs_file, "r") as f:
                    self.recovery_configs = json.load(f)
                print(f"Loaded {len(self.recovery_configs)} recovery configurations")
        except Exception as e:
            print(f"Error loading recovery configs: {e}")
            self.recovery_configs = {}

        try:
            if self.requests_file.exists():
                with open(self.requests_file, "r") as f:
                    self.recovery_requests = json.load(f)
                print(f"Loaded {len(self.recovery_requests)} recovery requests")
        except Exception as e:
            print(f"Error loading recovery requests: {e}")
            self.recovery_requests = {}

    def _save_configs(self):
        """Save recovery configurations to JSON file"""
        try:
            with open(self.configs_file, "w") as f:
                json.dump(self.recovery_configs, f, indent=2)
        except Exception as e:
            print(f"Error saving recovery configs: {e}")
            raise

    def _save_requests(self):
        """Save recovery requests to JSON file"""
        try:
            with open(self.requests_file, "w") as f:
                json.dump(self.recovery_requests, f, indent=2)
        except Exception as e:
            print(f"Error saving recovery requests: {e}")
            raise

    def setup_guardians(
        self,
        owner_address: str,
        guardian_addresses: List[str],
        threshold: int,
        signature: str = None,
    ) -> Dict:
        """Set up guardians for a wallet

        Args:
            owner_address: The wallet address to protect
            guardian_addresses: List of 2-5 guardian addresses
            threshold: Number of guardian votes required (e.g., 2 of 3)
            signature: Optional signature from owner to verify setup

        Returns:
            Dictionary with setup confirmation

        Raises:
            ValueError: If configuration is invalid
        """
        # Validation
        if not owner_address or not owner_address.startswith("XAI"):
            raise ValueError("Invalid owner address")

        if len(guardian_addresses) < self.min_guardians:
            raise ValueError(f"Minimum {self.min_guardians} guardians required")

        if len(guardian_addresses) > self.max_guardians:
            raise ValueError(f"Maximum {self.max_guardians} guardians allowed")

        # Check for duplicates
        if len(guardian_addresses) != len(set(guardian_addresses)):
            raise ValueError("Duplicate guardian addresses not allowed")

        # Validate guardian addresses
        for guardian in guardian_addresses:
            if not guardian or not guardian.startswith("XAI"):
                raise ValueError(f"Invalid guardian address: {guardian}")
            if guardian == owner_address:
                raise ValueError("Owner cannot be their own guardian")

        # Validate threshold
        if threshold < 1 or threshold > len(guardian_addresses):
            raise ValueError(f"Threshold must be between 1 and {len(guardian_addresses)}")

        # Check if owner already has a config
        if owner_address in self.recovery_configs:
            raise ValueError(
                "Recovery already configured for this address. Cancel existing config first."
            )

        # Create configuration
        config = {
            "owner_address": owner_address,
            "guardians": guardian_addresses,
            "threshold": threshold,
            "created_at": time.time(),
            "signature": signature,
        }

        # Save configuration
        self.recovery_configs[owner_address] = config
        self._save_configs()

        # Log notification (simulated)
        print(f"\n[EMAIL] NOTIFICATION: Recovery setup email sent to {owner_address}")
        print(f"   - Guardians: {len(guardian_addresses)}")
        print(f"   - Threshold: {threshold}")

        return {
            "success": True,
            "owner_address": owner_address,
            "guardians_count": len(guardian_addresses),
            "threshold": threshold,
            "created_at": config["created_at"],
            "message": "Social recovery configured successfully",
        }

    def get_recovery_config(self, owner_address: str) -> Optional[Dict]:
        """Get recovery configuration for an address

        Args:
            owner_address: The wallet address

        Returns:
            Recovery configuration or None if not found
        """
        return self.recovery_configs.get(owner_address)

    def initiate_recovery(
        self, owner_address: str, new_address: str, guardian_address: str, signature: str = None
    ) -> Dict:
        """Initiate a recovery request

        Args:
            owner_address: The wallet address to recover
            new_address: The new wallet address to transfer funds to
            guardian_address: Address of the guardian initiating recovery
            signature: Guardian's signature authorizing the recovery

        Returns:
            Dictionary with request details

        Raises:
            ValueError: If recovery cannot be initiated
        """
        # Validation
        config = self.recovery_configs.get(owner_address)
        if not config:
            raise ValueError("No recovery configuration found for this address")

        if not new_address or not new_address.startswith("XAI"):
            raise ValueError("Invalid new address")

        if new_address == owner_address:
            raise ValueError("New address cannot be the same as owner address")

        # Check if new address is a guardian (prevent collusion)
        if new_address in config["guardians"]:
            raise ValueError("Cannot recover to a guardian address (prevents collusion)")

        # Verify guardian
        if guardian_address not in config["guardians"]:
            raise ValueError("Address is not a registered guardian")

        # Check for existing pending requests
        for request_id, request in self.recovery_requests.items():
            if request["owner_address"] == owner_address and request["status"] == "pending":
                raise ValueError(f"Recovery already in progress (Request ID: {request_id})")

        # Create recovery request
        request_id = str(uuid.uuid4())
        current_time = time.time()

        request = {
            "request_id": request_id,
            "owner_address": owner_address,
            "new_address": new_address,
            "votes": [guardian_address],  # Initiator automatically votes
            "vote_signatures": {guardian_address: signature} if signature else {},
            "status": "pending",  # pending, approved, executed, cancelled
            "initiated_at": current_time,
            "initiated_by": guardian_address,
            "executable_at": current_time + self.default_waiting_period,
            "executed_at": None,
        }

        # Save request
        self.recovery_requests[request_id] = request
        self._save_requests()

        # Log notification
        print(f"\n[EMAIL] NOTIFICATION: Recovery initiated for {owner_address}")
        print(f"   - Request ID: {request_id}")
        print(f"   - New Address: {new_address}")
        print(f"   - Initiated by: {guardian_address}")
        print(f"   - Votes: 1/{config['threshold']}")
        print(
            f"   - Executable at: {datetime.fromtimestamp(request['executable_at']).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Notify all guardians
        for guardian in config["guardians"]:
            print(f"   [EMAIL] Email sent to guardian: {guardian}")

        return {
            "success": True,
            "request_id": request_id,
            "status": "pending",
            "votes": 1,
            "threshold": config["threshold"],
            "executable_at": request["executable_at"],
            "message": "Recovery request initiated successfully",
        }

    def vote_recovery(self, request_id: str, guardian_address: str, signature: str = None) -> Dict:
        """Guardian votes to approve a recovery request

        Args:
            request_id: The recovery request ID
            guardian_address: Address of the voting guardian
            signature: Guardian's signature

        Returns:
            Dictionary with voting results

        Raises:
            ValueError: If vote is invalid
        """
        # Validation
        request = self.recovery_requests.get(request_id)
        if not request:
            raise ValueError("Recovery request not found")

        if request["status"] not in ["pending", "approved"]:
            raise ValueError(f"Cannot vote on {request['status']} request")

        # Get config
        config = self.recovery_configs.get(request["owner_address"])
        if not config:
            raise ValueError("Recovery configuration not found")

        # Verify guardian
        if guardian_address not in config["guardians"]:
            raise ValueError("Address is not a registered guardian")

        # Check if already voted
        if guardian_address in request["votes"]:
            raise ValueError("Guardian has already voted")

        # Add vote
        request["votes"].append(guardian_address)
        if signature:
            request["vote_signatures"][guardian_address] = signature

        # Check if threshold reached
        votes_count = len(request["votes"])
        threshold = config["threshold"]

        if votes_count >= threshold:
            request["status"] = "approved"
            print(f"\n[OK] THRESHOLD REACHED: Recovery approved!")

        # Save
        self._save_requests()

        # Log notification
        print(f"\n[EMAIL] NOTIFICATION: Guardian vote received")
        print(f"   - Request ID: {request_id}")
        print(f"   - Guardian: {guardian_address}")
        print(f"   - Votes: {votes_count}/{threshold}")
        print(f"   - Status: {request['status']}")

        return {
            "success": True,
            "request_id": request_id,
            "votes": votes_count,
            "threshold": threshold,
            "status": request["status"],
            "message": f"Vote recorded. {votes_count}/{threshold} votes received.",
        }

    def get_recovery_status(self, owner_address: str) -> Dict:
        """Get recovery status for an address

        Args:
            owner_address: The wallet address

        Returns:
            Dictionary with recovery status
        """
        config = self.recovery_configs.get(owner_address)

        # Find pending/approved requests
        active_requests = []
        for request_id, request in self.recovery_requests.items():
            if request["owner_address"] == owner_address:
                if request["status"] in ["pending", "approved"]:
                    active_requests.append(
                        {
                            "request_id": request_id,
                            "status": request["status"],
                            "new_address": request["new_address"],
                            "votes": len(request["votes"]),
                            "threshold": config["threshold"] if config else 0,
                            "initiated_at": request["initiated_at"],
                            "executable_at": request["executable_at"],
                            "is_executable": self._is_executable(request),
                        }
                    )

        return {
            "has_recovery_config": config is not None,
            "config": config,
            "active_requests": active_requests,
            "active_requests_count": len(active_requests),
        }

    def cancel_recovery(self, request_id: str, owner_address: str, signature: str = None) -> Dict:
        """Cancel a pending recovery request

        Args:
            request_id: The recovery request ID
            owner_address: Owner's address (must match request)
            signature: Owner's signature to authorize cancellation

        Returns:
            Dictionary with cancellation confirmation

        Raises:
            ValueError: If cancellation is invalid
        """
        request = self.recovery_requests.get(request_id)
        if not request:
            raise ValueError("Recovery request not found")

        if request["owner_address"] != owner_address:
            raise ValueError("Only the owner can cancel their recovery request")

        if request["status"] not in ["pending", "approved"]:
            raise ValueError(f"Cannot cancel {request['status']} request")

        # Cancel the request
        request["status"] = "cancelled"
        request["cancelled_at"] = time.time()
        request["cancel_signature"] = signature

        self._save_requests()

        # Log notification
        print(f"\n[EMAIL] NOTIFICATION: Recovery cancelled")
        print(f"   - Request ID: {request_id}")
        print(f"   - Owner: {owner_address}")

        # Notify guardians
        config = self.recovery_configs.get(owner_address)
        if config:
            for guardian in config["guardians"]:
                print(f"   [EMAIL] Cancellation notice sent to guardian: {guardian}")

        return {
            "success": True,
            "request_id": request_id,
            "status": "cancelled",
            "message": "Recovery request cancelled successfully",
        }

    def _is_executable(self, request: dict) -> bool:
        """Check if a recovery request can be executed

        Args:
            request: The recovery request

        Returns:
            True if executable, False otherwise
        """
        if request["status"] != "approved":
            return False

        current_time = time.time()
        if current_time < request["executable_at"]:
            return False

        return True

    def execute_recovery(self, request_id: str, executor_address: str = None) -> Dict:
        """Execute an approved recovery request after waiting period

        Args:
            request_id: The recovery request ID
            executor_address: Optional address of who is executing

        Returns:
            Dictionary with execution details including transaction info

        Raises:
            ValueError: If execution is invalid
        """
        request = self.recovery_requests.get(request_id)
        if not request:
            raise ValueError("Recovery request not found")

        if request["status"] != "approved":
            raise ValueError(f"Cannot execute {request['status']} request. Must be approved.")

        # Check waiting period
        if not self._is_executable(request):
            remaining_time = request["executable_at"] - time.time()
            remaining_days = remaining_time / (24 * 60 * 60)
            raise ValueError(
                f"Waiting period not complete. "
                f"{remaining_days:.2f} days remaining until {datetime.fromtimestamp(request['executable_at']).strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Mark as executed
        request["status"] = "executed"
        request["executed_at"] = time.time()
        request["executed_by"] = executor_address

        self._save_requests()

        # Log notification
        print(f"\n[OK] RECOVERY EXECUTED")
        print(f"   - Request ID: {request_id}")
        print(f"   - Old Address: {request['owner_address']}")
        print(f"   - New Address: {request['new_address']}")
        print(
            f"   - Executed at: {datetime.fromtimestamp(request['executed_at']).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return {
            "success": True,
            "request_id": request_id,
            "status": "executed",
            "old_address": request["owner_address"],
            "new_address": request["new_address"],
            "executed_at": request["executed_at"],
            "message": "Recovery executed successfully. Funds should be transferred to new address.",
            "note": "This manager only tracks recovery status. Actual fund transfer must be implemented in blockchain.",
        }

    def remove_recovery_config(self, owner_address: str, signature: str = None) -> Dict:
        """Remove recovery configuration for an address

        Args:
            owner_address: The wallet address
            signature: Owner's signature to authorize removal

        Returns:
            Dictionary with removal confirmation

        Raises:
            ValueError: If removal is invalid
        """
        if owner_address not in self.recovery_configs:
            raise ValueError("No recovery configuration found for this address")

        # Check for pending requests
        for request in self.recovery_requests.values():
            if request["owner_address"] == owner_address and request["status"] in [
                "pending",
                "approved",
            ]:
                raise ValueError(
                    "Cannot remove config with pending recovery requests. Cancel requests first."
                )

        # Remove config
        del self.recovery_configs[owner_address]
        self._save_configs()

        print(f"\n[EMAIL] NOTIFICATION: Recovery config removed for {owner_address}")

        return {
            "success": True,
            "owner_address": owner_address,
            "message": "Recovery configuration removed successfully",
        }

    def get_guardian_duties(self, guardian_address: str) -> Dict:
        """Get all addresses this guardian is protecting

        Args:
            guardian_address: The guardian's address

        Returns:
            Dictionary with guardian duties
        """
        protecting = []
        pending_votes = []

        # Find all wallets this guardian protects
        for owner_address, config in self.recovery_configs.items():
            if guardian_address in config["guardians"]:
                protecting.append(
                    {
                        "owner_address": owner_address,
                        "threshold": config["threshold"],
                        "total_guardians": len(config["guardians"]),
                        "created_at": config["created_at"],
                    }
                )

        # Find pending recovery requests needing this guardian's vote
        for request_id, request in self.recovery_requests.items():
            if request["status"] == "pending":
                config = self.recovery_configs.get(request["owner_address"])
                if config and guardian_address in config["guardians"]:
                    if guardian_address not in request["votes"]:
                        pending_votes.append(
                            {
                                "request_id": request_id,
                                "owner_address": request["owner_address"],
                                "new_address": request["new_address"],
                                "votes": len(request["votes"]),
                                "threshold": config["threshold"],
                                "initiated_at": request["initiated_at"],
                                "executable_at": request["executable_at"],
                            }
                        )

        return {
            "guardian_address": guardian_address,
            "protecting_count": len(protecting),
            "protecting": protecting,
            "pending_votes_count": len(pending_votes),
            "pending_votes": pending_votes,
        }

    def get_all_requests(self, status: str = None) -> List[Dict]:
        """Get all recovery requests, optionally filtered by status

        Args:
            status: Filter by status (pending, approved, executed, cancelled) or None for all

        Returns:
            List of recovery requests
        """
        requests = []
        for request_id, request in self.recovery_requests.items():
            if status is None or request["status"] == status:
                config = self.recovery_configs.get(request["owner_address"])
                requests.append(
                    {
                        "request_id": request_id,
                        "owner_address": request["owner_address"],
                        "new_address": request["new_address"],
                        "status": request["status"],
                        "votes": len(request["votes"]),
                        "threshold": config["threshold"] if config else 0,
                        "initiated_at": request["initiated_at"],
                        "executable_at": request["executable_at"],
                        "is_executable": self._is_executable(request),
                    }
                )

        return requests

    def get_stats(self) -> Dict:
        """Get overall statistics about social recovery usage

        Returns:
            Dictionary with statistics
        """
        total_configs = len(self.recovery_configs)
        total_requests = len(self.recovery_requests)

        # Count by status
        pending = sum(1 for r in self.recovery_requests.values() if r["status"] == "pending")
        approved = sum(1 for r in self.recovery_requests.values() if r["status"] == "approved")
        executed = sum(1 for r in self.recovery_requests.values() if r["status"] == "executed")
        cancelled = sum(1 for r in self.recovery_requests.values() if r["status"] == "cancelled")

        # Count guardians
        all_guardians = set()
        for config in self.recovery_configs.values():
            all_guardians.update(config["guardians"])

        return {
            "total_configs": total_configs,
            "total_guardians": len(all_guardians),
            "total_requests": total_requests,
            "requests_by_status": {
                "pending": pending,
                "approved": approved,
                "executed": executed,
                "cancelled": cancelled,
            },
            "success_rate": (executed / total_requests * 100) if total_requests > 0 else 0,
        }


# Example usage and testing
if __name__ == "__main__":
    print("=" * 60)
    print("AXN SOCIAL RECOVERY SYSTEM - DEMO")
    print("=" * 60)

    # Initialize manager
    manager = SocialRecoveryManager()

    # Create test addresses
    owner = "AXN1234567890abcdef1234567890abcdef1234567890"
    guardian1 = "AXNguardian1111111111111111111111111111111111"
    guardian2 = "AXNguardian2222222222222222222222222222222222"
    guardian3 = "AXNguardian3333333333333333333333333333333333"
    new_addr = "AXNnewaddress9999999999999999999999999999999999"

    print("\n1. Setting up guardians...")
    try:
        result = manager.setup_guardians(
            owner_address=owner, guardian_addresses=[guardian1, guardian2, guardian3], threshold=2
        )
        print(f"[OK] Setup successful: {result['message']}")
    except ValueError as e:
        print(f"Error: {e}")

    print("\n2. Initiating recovery...")
    try:
        result = manager.initiate_recovery(
            owner_address=owner, new_address=new_addr, guardian_address=guardian1
        )
        request_id = result["request_id"]
        print(f"[OK] Recovery initiated: {request_id}")
    except ValueError as e:
        print(f"Error: {e}")

    print("\n3. Second guardian voting...")
    try:
        result = manager.vote_recovery(request_id=request_id, guardian_address=guardian2)
        print(f"[OK] Vote recorded: {result['message']}")
    except ValueError as e:
        print(f"Error: {e}")

    print("\n4. Checking recovery status...")
    status = manager.get_recovery_status(owner)
    print(f"Active requests: {status['active_requests_count']}")
    if status["active_requests"]:
        req = status["active_requests"][0]
        print(f"Status: {req['status']}")
        print(f"Votes: {req['votes']}/{req['threshold']}")
        print(f"Executable: {req['is_executable']}")

    print("\n5. Guardian duties check...")
    duties = manager.get_guardian_duties(guardian1)
    print(f"Protecting {duties['protecting_count']} wallets")
    print(f"Pending votes: {duties['pending_votes_count']}")

    print("\n6. System statistics...")
    stats = manager.get_stats()
    print(f"Total configs: {stats['total_configs']}")
    print(f"Total requests: {stats['total_requests']}")
    print(f"Status breakdown: {stats['requests_by_status']}")

    print("\n" + "=" * 60)
    print("Demo complete! Check recovery_data/ for saved files.")
    print("=" * 60)
