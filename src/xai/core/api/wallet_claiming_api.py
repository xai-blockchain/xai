from __future__ import annotations

"""
XAI Blockchain - Wallet Claiming API

Multiple ways to claim early adopter wallets:
1. Explicit claiming via /claim-wallet endpoint
2. Automatic check after mining
3. Persistent notifications until claimed

Includes Time Capsule Protocol integration
"""

import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from flask import jsonify, request

logger = logging.getLogger(__name__)

class FraudDetector:
    """Comprehensive fraud detection for wallet claims"""

    def __init__(self, rate_limit_window: int = 3600, max_claims_per_ip: int = 5,
                 max_claims_per_identity: int = 1, suspicious_pattern_threshold: int = 3):
        """
        Initialize fraud detector.

        Args:
            rate_limit_window: Time window for rate limiting (seconds)
            max_claims_per_ip: Maximum claims allowed per IP in window
            max_claims_per_identity: Maximum claims per verified identity
            suspicious_pattern_threshold: Number of failed attempts before flagging
        """
        self.rate_limit_window = rate_limit_window
        self.max_claims_per_ip = max_claims_per_ip
        self.max_claims_per_identity = max_claims_per_identity
        self.suspicious_pattern_threshold = suspicious_pattern_threshold

        # Rate limiting per IP
        self.ip_attempts: dict[str, deque] = defaultdict(lambda: deque())

        # Track claims per identity proof
        self.identity_claims: dict[str, set[str]] = defaultdict(set)

        # Failed attempts tracking for pattern detection
        self.failed_attempts: dict[str, int] = defaultdict(int)
        self.blacklisted_ips: set[str] = set()
        self.suspicious_patterns: dict[str, list] = defaultdict(list)

        # Signature validation tracking
        self.verified_signatures: dict[str, dict[str, Any]] = {}

        self._lock = threading.RLock()

        logger.info(
            f"FraudDetector initialized. Rate limit: {max_claims_per_ip}/{rate_limit_window}s, "
            f"Max per identity: {max_claims_per_identity}"
        )

    def check_rate_limit(self, ip_address: str) -> dict[str, Any]:
        """
        Check if IP is within rate limits.

        Returns:
            dict with 'allowed' (bool) and details
        """
        with self._lock:
            current_time = time.time()

            # Check if blacklisted
            if ip_address in self.blacklisted_ips:
                logger.warning(f"Blacklisted IP attempted claim: {ip_address}")
                return {
                    "allowed": False,
                    "reason": "ip_blacklisted",
                    "message": "This IP has been blacklisted due to suspicious activity"
                }

            # Clean old attempts
            attempts = self.ip_attempts[ip_address]
            while attempts and current_time - attempts[0] > self.rate_limit_window:
                attempts.popleft()

            # Check rate limit
            if len(attempts) >= self.max_claims_per_ip:
                logger.warning(
                    f"Rate limit exceeded for IP {ip_address}: "
                    f"{len(attempts)} attempts in {self.rate_limit_window}s"
                )
                return {
                    "allowed": False,
                    "reason": "rate_limit_exceeded",
                    "message": f"Too many claim attempts. Try again in {int(self.rate_limit_window/60)} minutes",
                    "attempts": len(attempts),
                    "limit": self.max_claims_per_ip
                }

            # Add this attempt
            attempts.append(current_time)

            return {
                "allowed": True,
                "attempts": len(attempts),
                "limit": self.max_claims_per_ip
            }

    def verify_proof_of_ownership(self, identifier: str, signature: str | None = None,
                                  public_key: str | None = None) -> dict[str, Any]:
        """
        Verify proof of ownership for wallet claim.

        Args:
            identifier: Claim identifier
            signature: Cryptographic signature
            public_key: Public key for verification

        Returns:
            dict with 'verified' (bool) and details
        """
        with self._lock:
            if not signature or not public_key:
                logger.debug(f"No signature/public_key provided for {identifier}")
                return {
                    "verified": False,
                    "reason": "missing_credentials",
                    "message": "Signature and public key required for verification"
                }

            # Production cryptographic signature verification
            # Use ECDSA signature verification with the provided public key
            try:
                from xai.core.security.crypto_utils import verify_signature_hex

                # Verify the signature using ECDSA
                # CRITICAL: verify_signature_hex(public_hex, message, signature_hex) - correct parameter order
                is_valid = verify_signature_hex(public_key, identifier.encode(), signature)

                if not is_valid:
                    logger.warning(f"Invalid signature for {identifier}")
                    return {
                        "verified": False,
                        "reason": "invalid_signature",
                        "message": "Signature verification failed"
                    }
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.error(f"Signature verification error for {identifier}: {e}")
                return {
                    "verified": False,
                    "reason": "verification_error",
                    "message": f"Could not verify signature: {e}"
                }

            # Store verified signature
            self.verified_signatures[identifier] = {
                "public_key": public_key,
                "signature": signature,
                "verified_at": time.time()
            }

            logger.info(f"Signature verified for {identifier}")
            return {
                "verified": True,
                "public_key": public_key,
                "verified_at": time.time()
            }

    def check_identity_uniqueness(self, identity_proof: str, identifier: str) -> dict[str, Any]:
        """
        Check if identity has already claimed (prevent multiple accounts).

        Args:
            identity_proof: Identity verification proof (hashed)
            identifier: Current claim identifier

        Returns:
            dict with 'unique' (bool) and details
        """
        with self._lock:
            # Hash the identity proof
            identity_hash = hashlib.sha256(identity_proof.encode()).hexdigest()

            existing_claims = self.identity_claims[identity_hash]

            if len(existing_claims) >= self.max_claims_per_identity:
                logger.warning(
                    f"Identity {identity_hash[:8]}... already has {len(existing_claims)} claims: "
                    f"{existing_claims}"
                )
                return {
                    "unique": False,
                    "reason": "identity_already_claimed",
                    "message": "This identity has already claimed a wallet",
                    "existing_claims": len(existing_claims)
                }

            # Add to claims
            existing_claims.add(identifier)

            return {
                "unique": True,
                "identity_hash": identity_hash[:16],
                "total_claims": len(existing_claims)
            }

    def detect_suspicious_patterns(self, ip_address: str, identifier: str,
                                   claim_data: dict[str, Any]) -> dict[str, Any]:
        """
        Detect suspicious patterns for abuse prevention.

        Args:
            ip_address: Requester IP
            identifier: Claim identifier
            claim_data: Additional claim data for pattern analysis

        Returns:
            dict with 'suspicious' (bool) and detected patterns
        """
        with self._lock:
            patterns_detected = []

            # Pattern 1: Rapid sequential identifiers (bot-like behavior)
            if identifier.isdigit() or (identifier.startswith("0x") and len(identifier) == 66):
                recent_similar = sum(
                    1 for p in self.suspicious_patterns[ip_address][-10:]
                    if p.get("pattern") == "sequential_ids"
                )
                if recent_similar >= 3:
                    patterns_detected.append({
                        "pattern": "sequential_identifiers",
                        "description": "Multiple sequential IDs from same IP",
                        "severity": "high"
                    })

            # Pattern 2: Same IP claiming multiple identifiers quickly
            recent_claims = [
                p for p in self.suspicious_patterns[ip_address]
                if time.time() - p.get("timestamp", 0) < 300  # Last 5 minutes
            ]
            if len(recent_claims) >= 3:
                patterns_detected.append({
                    "pattern": "rapid_multiple_claims",
                    "description": "Multiple claims from same IP in short time",
                    "severity": "medium",
                    "count": len(recent_claims)
                })

            # Pattern 3: Failed signature validations
            if self.failed_attempts[identifier] >= self.suspicious_pattern_threshold:
                patterns_detected.append({
                    "pattern": "repeated_failures",
                    "description": "Multiple failed validation attempts",
                    "severity": "high",
                    "attempts": self.failed_attempts[identifier]
                })

            # Record this pattern check
            self.suspicious_patterns[ip_address].append({
                "identifier": identifier,
                "timestamp": time.time(),
                "patterns": patterns_detected
            })

            # Auto-blacklist if high severity patterns
            high_severity_count = sum(1 for p in patterns_detected if p.get("severity") == "high")
            if high_severity_count >= 2:
                self.blacklisted_ips.add(ip_address)
                logger.error(f"IP {ip_address} auto-blacklisted due to suspicious patterns")

            return {
                "suspicious": len(patterns_detected) > 0,
                "patterns": patterns_detected,
                "risk_level": "high" if high_severity_count > 0 else "medium" if patterns_detected else "low"
            }

    def record_failed_attempt(self, identifier: str, reason: str):
        """Record a failed claim attempt."""
        with self._lock:
            self.failed_attempts[identifier] += 1
            logger.debug(f"Failed attempt for {identifier}: {reason} (total: {self.failed_attempts[identifier]})")

    def reset_identifier(self, identifier: str):
        """Reset fraud tracking for an identifier (after successful claim)."""
        with self._lock:
            self.failed_attempts.pop(identifier, None)

class WalletClaimingTracker:
    """Tracks unclaimed wallets and sends persistent notifications"""

    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.dirname(__file__))

        self.data_dir = data_dir
        self.pending_claims_file = os.path.join(data_dir, "pending_wallet_claims.json")
        self.pending_claims = {}

        # Initialize fraud detector
        self.fraud_detector = FraudDetector()

        self._load_pending_claims()

    def _load_pending_claims(self):
        """Load pending wallet claims"""
        if os.path.exists(self.pending_claims_file):
            with open(self.pending_claims_file, "r") as f:
                self.pending_claims = json.load(f)
        else:
            self.pending_claims = {}

    def _save_pending_claims(self):
        """Save pending claims"""
        with open(self.pending_claims_file, "w") as f:
            json.dump(self.pending_claims, f, indent=2)

    def register_eligible_claimer(self, identifier: str, context: str = "unknown"):
        """
        Register someone as eligible to claim wallet

        Args:
            identifier: Node ID, miner address, or unique identifier
            context: How they became eligible (node_start, first_mine, etc.)
        """
        if identifier not in self.pending_claims:
            self.pending_claims[identifier] = {
                "identifier": identifier,
                "registered_utc": datetime.utcnow().timestamp(),
                "context": context,
                "notification_count": 0,
                "last_notification_utc": None,
                "claimed": False,
                "dismissed": False,
                "last_dismissed_utc": None,
            }
            self._save_pending_claims()

    def mark_claimed(self, identifier: str):
        """Mark wallet as claimed"""
        if identifier in self.pending_claims:
            self.pending_claims[identifier]["claimed"] = True
            self.pending_claims[identifier]["claimed_utc"] = datetime.utcnow().timestamp()
            self._save_pending_claims()

    def get_unclaimed_notification(self, identifier: str) -> dict:
        """Get notification for unclaimed wallet"""
        if identifier not in self.pending_claims:
            return None

        claim = self.pending_claims[identifier]
        if claim["claimed"]:
            return None

        now = datetime.utcnow().timestamp()
        freq = 30 * 86400 if claim.get("dismissed") else 86400
        last = claim.get("last_notification_utc")
        if last and (now - last) < freq:
            return None

        claim["notification_count"] += 1
        claim["last_notification_utc"] = now
        self._save_pending_claims()

        reminder = (
            "Daily reminder: your pre-loaded wallet is safe & secure and waiting to be claimed."
            if not claim.get("dismissed")
            else "Monthly reminder: your wallet is still ready whenever you return."
        )

        return {
            "message": "🎁 UNCLAIMED WALLET AVAILABLE!",
            "details": reminder,
            "action": "Call POST /claim-wallet to claim your wallet or POST /claim-wallet/notification/dismiss to postpone",
            "notification_number": claim["notification_count"],
        }

    def dismiss_notification(self, identifier: str) -> bool:
        if identifier not in self.pending_claims:
            return False
        claim = self.pending_claims[identifier]
        claim["dismissed"] = True
        claim["last_dismissed_utc"] = datetime.utcnow().timestamp()
        self._save_pending_claims()
        return True

    def pending_claims_summary(self) -> list:
        """Return a snapshot of all pending wallet claims for dashboards."""
        now = datetime.utcnow().timestamp()
        summary = []
        for claim in self.pending_claims.values():
            if claim.get("claimed"):
                continue
            freq = 30 * 86400 if claim.get("dismissed") else 86400
            last_notified = claim.get("last_notification_utc") or claim.get("registered_utc") or now
            next_due = last_notified + freq
            summary.append(
                {
                    "identifier": claim["identifier"],
                    "context": claim.get("context"),
                    "notification_count": claim.get("notification_count", 0),
                    "dismissed": claim.get("dismissed", False),
                    "last_notification_utc": claim.get("last_notification_utc"),
                    "next_notification_due": next_due,
                    "next_notification_due_iso": datetime.utcfromtimestamp(next_due).isoformat()
                    + "Z",
                }
            )
        return summary

def setup_wallet_claiming_api(app, node):
    """
    Setup wallet claiming API endpoints

    Args:
        app: Flask app instance
        node: XAI Node instance
    """

    # Initialize tracker
    tracker = WalletClaimingTracker(node.data_dir if hasattr(node, "data_dir") else None)

    @app.route("/claim-wallet", methods=["POST"])
    def claim_wallet():
        """
        Explicit wallet claiming endpoint

        Body:
        {
          "identifier": "node_id or miner_address",
          "uptime_minutes": 30  # Optional: how long node has been running
        }

        Response:
        {
          "success": true,
          "tier": "premium|standard|micro",
          "wallet": {...},
          "time_capsule_offer": {...}  # If eligible
        }
        """
        data = request.get_json()

        if not data or "identifier" not in data:
            return jsonify({"error": "Missing identifier"}), 400

        identifier = data["identifier"]
        uptime_minutes = data.get("uptime_minutes", 0)
        tracker.register_eligible_claimer(identifier, context="claim_wallet")

        # Check if already claimed
        wallet_files = ["xai_og_wallet.json", "xai_early_adopter_wallet.json"]
        for wallet_file in wallet_files:
            full_path = os.path.join(os.path.dirname(__file__), "..", wallet_file)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    existing_wallet = json.load(f)
                    if existing_wallet.get("node_id") == identifier:
                        return jsonify(
                            {
                                "success": False,
                                "error": "Wallet already claimed",
                                "wallet_file": wallet_file,
                                "address": existing_wallet["address"],
                            }
                        )

        # Try to claim premium wallet first (immediate)
        try:
            result = node.wallet_claim_system.claim_premium_wallet(
                node_id=identifier, proof_of_mining=None  # No proof needed
            )

            if result["success"]:
                # Save wallet
                node._save_bonus_wallet(result["wallet"], tier=result["tier"])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                return jsonify(
                    {
                        "success": True,
                        "tier": "premium",
                        "wallet": {
                            "address": result["wallet"]["address"],
                            "file": "xai_og_wallet.json",
                        },
                        "message": "CONGRATULATIONS! Premium wallet claimed!",
                        "remaining_premium": result.get("remaining_premium", 0),
                    }
                )

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Log premium wallet claim failure but continue to bonus/standard tiers
            logger.warning(
                "Premium wallet claim failed for identifier=%s, falling back to bonus tier: %s",
                identifier[:16] + "..." if len(identifier) > 16 else identifier,
                str(e),
                extra={"event": "wallet_claim.premium_failed", "identifier_prefix": identifier[:8]}
            )

        try:
            bonus_result = node.wallet_claim_system.claim_bonus_wallet(miner_id=identifier)

            if bonus_result["success"] and bonus_result.get("tier") != "empty":
                node._save_bonus_wallet(bonus_result["wallet"], tier=bonus_result["tier"])
                tracker.mark_claimed(identifier)
                response = {
                    "success": True,
                    "tier": bonus_result["tier"],
                    "wallet": bonus_result["wallet"],
                    "message": bonus_result.get("message", "Bonus wallet claimed!"),
                }
                if "remaining_bonus" in bonus_result:
                    response["remaining_bonus"] = bonus_result["remaining_bonus"]
                return jsonify(response)

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Log bonus wallet claim failure but continue to standard tier
            logger.warning(
                "Bonus wallet claim failed for identifier=%s, falling back to standard tier: %s",
                identifier[:16] + "..." if len(identifier) > 16 else identifier,
                str(e),
                extra={"event": "wallet_claim.bonus_failed", "identifier_prefix": identifier[:8]}
            )

        # Check uptime requirement for standard/micro (30 minutes)
        if uptime_minutes < 30:
            tracker.register_eligible_claimer(identifier, "pending_uptime")
            return (
                jsonify(
                    {
                        "success": True,
                        "tier": "pending",
                        "required_uptime_minutes": 30,
                        "current_uptime_minutes": uptime_minutes,
                        "message": f"Run your node for {30 - uptime_minutes} more minutes to unlock your wallet",
                    }
                ),
                200,
            )

        # Try standard wallet
        try:
            result = node.wallet_claim_system.claim_standard_wallet(identifier)

            if result["success"]:
                # Save wallet
                node._save_bonus_wallet(result["wallet"], tier=result["tier"])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                response = {
                    "success": True,
                    "tier": "standard",
                    "wallet": {
                        "address": result["wallet"]["address"],
                        "balance": result["wallet"]["balance"],
                        "file": "xai_early_adopter_wallet.json",
                    },
                    "message": "WELCOME TO XAI COIN! Standard wallet claimed!",
                    "remaining_standard": result.get("remaining_standard", 0),
                }

                # Add time capsule offer if eligible
                if "time_capsule_offer" in result:
                    response["time_capsule_offer"] = result["time_capsule_offer"]
                    response[
                        "message"
                    ] += "\n\n🎁 SPECIAL OFFER AVAILABLE! Check time_capsule_offer field."

                return jsonify(response)

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Log standard wallet claim failure but continue to micro tier
            logger.warning(
                "Standard wallet claim failed for identifier=%s, falling back to micro tier: %s",
                identifier[:16] + "..." if len(identifier) > 16 else identifier,
                str(e),
                extra={"event": "wallet_claim.standard_failed", "identifier_prefix": identifier[:8]}
            )

        # Try micro wallet
        try:
            result = node.wallet_claim_system.claim_micro_wallet(identifier)

            if result["success"]:
                # Save wallet
                node._save_bonus_wallet(result["wallet"], tier=result["tier"])

                # Mark as claimed
                tracker.mark_claimed(identifier)

                return jsonify(
                    {
                        "success": True,
                        "tier": "micro",
                        "wallet": {
                            "address": result["wallet"]["address"],
                            "balance": result["wallet"]["balance"],
                            "file": "xai_early_adopter_wallet.json",
                        },
                        "message": "WELCOME TO XAI COIN! Micro wallet claimed!",
                        "remaining_micro": result.get("remaining_micro", 0),
                    }
                )

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            # Log micro wallet claim failure - all tiers exhausted
            logger.error(
                "Micro wallet claim failed for identifier=%s, all tiers exhausted: %s",
                identifier[:16] + "..." if len(identifier) > 16 else identifier,
                str(e),
                extra={"event": "wallet_claim.micro_failed", "identifier_prefix": identifier[:8]}
            )

        return (
            jsonify(
                {
                    "success": True,
                    "tier": "empty",
                    "message": "All allocated early adopter wallets have been issued; an empty wallet is reserved for you.",
                }
            ),
            200,
        )

    @app.route("/check-unclaimed-wallet/<identifier>", methods=["GET"])
    def check_unclaimed_wallet(identifier):
        """
        Check if user has unclaimed wallet

        Response:
        {
          "unclaimed": true/false,
          "notification": {...}
        }
        """
        notification = tracker.get_unclaimed_notification(identifier)

        if notification:
            return jsonify({"unclaimed": True, "notification": notification})
        else:
            return jsonify(
                {"unclaimed": False, "message": "No unclaimed wallet or already claimed"}
            )

    @app.route("/claim-wallet/notification/dismiss", methods=["POST"])
    def dismiss_wallet_notification():
        data = request.get_json() or {}
        identifier = data.get("identifier")
        if not identifier:
            return jsonify({"success": False, "error": "Missing identifier"}), 400
        tracker.dismiss_notification(identifier)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Notifications dismissed; monthly reminders will resume.",
                }
            ),
            200,
        )

    @app.route("/wallet-claims/summary", methods=["GET"])
    def wallet_claims_summary():
        summary = tracker.pending_claims_summary()
        return jsonify({"success": True, "pending_count": len(summary), "pending": summary})

    @app.route("/accept-time-capsule", methods=["POST"])
    def accept_time_capsule():
        """
        Accept time capsule protocol offer

        Body:
        {
          "wallet_address": "XAI...",
          "accept": true/false
        }

        Response:
        {
          "success": true,
          "message": "Time Capsule Protocol Initiated",
          "locked_wallet": {...},
          "replacement_wallet": {...}
        }
        """
        data = request.get_json()

        if not data or "wallet_address" not in data:
            return jsonify({"error": "Missing wallet_address"}), 400

        wallet_address = data["wallet_address"]
        accept = data.get("accept", False)

        # Load wallet data
        wallet_file = os.path.join(os.path.dirname(__file__), "..", "xai_early_adopter_wallet.json")
        if not os.path.exists(wallet_file):
            return jsonify({"error": "Wallet file not found"}), 404

        with open(wallet_file, "r") as f:
            wallet_data = json.load(f)

        if wallet_data["address"] != wallet_address:
            return jsonify({"error": "Wallet address mismatch"}), 400

        # Check eligibility
        if not wallet_data.get("time_capsule_eligible", False):
            return jsonify({"error": "Wallet not eligible for time capsule protocol"}), 400

        if not accept:
            return jsonify(
                {
                    "success": True,
                    "message": "Time capsule protocol declined",
                    "wallet_unchanged": True,
                }
            )

        # Initiate time capsule
        from xai.core.governance.time_capsule_protocol import TimeCapsuleProtocol

        time_capsule = TimeCapsuleProtocol(
            blockchain=node.blockchain if hasattr(node, "blockchain") else None
        )

        result = time_capsule.initiate_time_capsule(wallet_data, user_accepted=True)

        if not result["success"]:
            return jsonify(result), 400

        # Replace wallet file with replacement wallet
        with open(wallet_file, "w") as f:
            json.dump(result["replacement_wallet"], f, indent=2)

        print(result["protocol_message"])

        return jsonify(
            {
                "success": True,
                "message": "Time Capsule Protocol Engaged",
                "locked_wallet": result["locked_wallet"],
                "replacement_wallet": {
                    "address": result["replacement_wallet"]["address"],
                    "balance": 0,
                    "file": "xai_early_adopter_wallet.json (updated)",
                },
                "unlock_message": f"You may claim your wallet with {result['locked_wallet']['amount']} XAI on {result['locked_wallet']['unlock_date_utc']}",
            }
        )

    return tracker
