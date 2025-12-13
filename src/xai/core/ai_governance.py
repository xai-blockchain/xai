"""
XAI AI Governance System

Consensus mechanism for AI-driven development:
- Quadratic voting (prevents whale dominance)
- Both miners AND node operators vote
- Voting power based on AI minutes contributed
- Time-decay prevents old contributions from controlling forever
- AI workload divided proportionally among contributors
- Timelock system delays execution after approval
- Changeable governance parameters
"""

from __future__ import annotations
import time
import hashlib
import math
import inspect
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)

# Import governance parameters
try:
    from xai.core.governance_parameters import GovernanceParameters, ProposalType, TimelockProposal
    _GP_SIG = inspect.signature(GovernanceParameters.__init__)
    if "mining_start_time" in _GP_SIG.parameters and _GP_SIG.parameters[
        "mining_start_time"
    ].default is inspect._empty:
        _ORIGINAL_GP_INIT = GovernanceParameters.__init__

        def _patched_gp_init(self, *args, **kwargs):
            if "mining_start_time" not in kwargs and not args:
                kwargs["mining_start_time"] = time.time()
            _ORIGINAL_GP_INIT(self, *args, **kwargs)

        GovernanceParameters.__init__ = _patched_gp_init
except ImportError:
    # Allow running standalone
    class ProposalType(Enum):
        AI_IMPROVEMENT = "ai_improvement"
        PARAMETER_CHANGE = "parameter_change"
        EMERGENCY = "emergency"


class VoterType(Enum):
    """Types of voters in governance"""

    NODE_OPERATOR = "node_operator"  # Runs node 24/7
    MINER = "miner"  # Mines blocks
    AI_CONTRIBUTOR = "ai_contributor"  # Donated AI minutes
    HYBRID = "hybrid"  # Multiple roles


class VotingPowerDisplay:
    """
    Shows actual voting power to prevent discouragement
    Small contributors need to see they matter
    """

    @staticmethod
    def show_contribution_impact(minutes_contributed: float) -> Dict:
        """
        Show what voting power comes from contributing X minutes
        Prevents discouragement from seeing large contributors
        """

        base_power = math.sqrt(minutes_contributed)

        return {
            "minutes_contributed": minutes_contributed,
            "voting_power": base_power,
            "actual_voting_power": base_power,
            "not_1_to_1": True,
            "explanation": f"{minutes_contributed} minutes = {base_power:.1f} votes (sqrt prevents whale control)",
            "examples": {
                "1 minute": math.sqrt(1),
                "10 minutes": math.sqrt(10),
                "100 minutes": math.sqrt(100),
                "1000 minutes": math.sqrt(1000),
                "10000 minutes": min(math.sqrt(10000), 100),  # Capped
            },
        }

    @staticmethod
    def compare_contributors(contributor_minutes: List[float]) -> List[Dict]:
        """
        Show how multiple contributors compare
        Demonstrates small contributors still matter
        """

        results = []
        total_power = sum(math.sqrt(m) for m in contributor_minutes)

        for minutes in contributor_minutes:
            power = math.sqrt(minutes)
            percentage = (power / total_power * 100) if total_power > 0 else 0

            results.append(
                {"minutes": minutes, "voting_power": power, "percentage_of_total": percentage}
            )

        return results


class VotingPower:
    """
    Calculate voting power using quadratic voting
    Prevents whale dominance while rewarding contribution
    """

    def __init__(self) -> None:
        # Time decay: contributions lose 10% voting power per month
        self.monthly_decay_rate = 0.10

        # Caps to prevent dominance
        self.max_ai_minutes_votes = 100  # sqrt(10,000 minutes)
        self.max_mining_votes = 50  # sqrt(2,500 blocks)
        self.max_node_votes = 75  # sqrt(5,625 days)

    def calculate_ai_minutes_voting_power(
        self, minutes_contributed: float, contribution_timestamp: float
    ) -> float:
        """
        Quadratic voting: sqrt of minutes contributed
        Time decay: Older contributions matter less

        Args:
            minutes_contributed: AI API minutes donated
            contribution_timestamp: When contributed

        Returns:
            Voting power (0-100)
        """

        # Quadratic scaling (sqrt prevents whale control)
        base_power = math.sqrt(minutes_contributed)

        # Apply time decay
        months_old = (time.time() - contribution_timestamp) / (30 * 86400)
        if months_old < 1e-9:
            months_old = 0.0
        decay_factor = (1 - self.monthly_decay_rate) ** months_old

        voting_power = base_power * decay_factor

        # Cap at maximum
        return min(voting_power, self.max_ai_minutes_votes)

    def calculate_mining_voting_power(
        self, blocks_mined: int, last_block_timestamp: float
    ) -> float:
        """
        Miners get votes based on blocks mined
        Recent mining activity matters more
        """

        base_power = math.sqrt(blocks_mined)

        # Decay if not mining recently
        days_since_last_block = (time.time() - last_block_timestamp) / 86400
        if days_since_last_block > 30:
            decay_factor = 0.5  # 50% power if inactive
        else:
            decay_factor = 1.0

        voting_power = base_power * decay_factor

        return min(voting_power, self.max_mining_votes)

    def calculate_node_voting_power(self, uptime_days: int, is_currently_active: bool) -> float:
        """
        Node operators get votes for running infrastructure
        """

        if not is_currently_active:
            return 0  # Must be active to vote

        base_power = math.sqrt(uptime_days)

        return min(base_power, self.max_node_votes)

    def calculate_total_voting_power(self, voter_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate total voting power across all contributions

        Returns:
            (total_power, breakdown)
        """

        breakdown = {"ai_minutes": 0, "mining": 0, "node_operation": 0, "bonus": 0}

        # AI minutes contribution
        if voter_data.get("ai_minutes_contributed", 0) > 0:
            breakdown["ai_minutes"] = self.calculate_ai_minutes_voting_power(
                voter_data["ai_minutes_contributed"],
                voter_data.get("ai_contribution_timestamp", time.time()),
            )

        # Mining contribution
        if voter_data.get("blocks_mined", 0) > 0:
            breakdown["mining"] = self.calculate_mining_voting_power(
                voter_data["blocks_mined"], voter_data.get("last_block_timestamp", time.time())
            )

        # Node operation
        if voter_data.get("node_uptime_days", 0) > 0:
            breakdown["node_operation"] = self.calculate_node_voting_power(
                voter_data["node_uptime_days"], voter_data.get("node_active", False)
            )

        # Hybrid bonus: If contributing in multiple ways, +10% total
        active_contributions = sum(1 for v in breakdown.values() if v > 0)
        if active_contributions >= 2:
            base_total = sum(breakdown.values())
            breakdown["bonus"] = base_total * 0.10

        total = sum(breakdown.values())

        return total, breakdown


class GovernanceFraudDetector:
    """Detect coordinated/sybil voting patterns and emit structured alerts."""

    CLUSTER_WINDOW_SECONDS = 600
    CLUSTER_MIN_UNIQUE = 3
    CLUSTER_MIN_POWER = 15.0
    NEW_ACCOUNT_WINDOW_SECONDS = 900
    NEW_ACCOUNT_MAX_AGE_DAYS = 3
    NEW_ACCOUNT_MIN_VOTERS = 4
    NEW_ACCOUNT_MIN_POWER = 20.0
    PRUNE_WINDOW_SECONDS = 3600
    BURST_WINDOW_SECONDS = 90
    BURST_MIN_UNIQUE = 5
    BURST_MIN_TOTAL = 6
    POWER_SKEW_SHARE = 0.65
    POWER_SKEW_MIN_VOTERS = 3

    def __init__(self) -> None:
        self.vote_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.alerts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._cluster_alerted: Set[Tuple[str, str, str]] = set()
        self._new_account_alerted: Set[str] = set()
        self._burst_alerted: Set[str] = set()
        self._power_alerted: Set[Tuple[str, str, str]] = set()

    def record_vote(
        self,
        proposal_id: str,
        voter_address: str,
        voting_power: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Store vote telemetry and evaluate heuristics."""
        metadata = metadata or {}
        entry = {
            "address": voter_address,
            "voting_power": float(voting_power),
            "timestamp": time.time(),
            "metadata": metadata,
            "cluster_keys": self._extract_cluster_keys(metadata),
        }
        self.vote_records[proposal_id].append(entry)
        self._prune_records(proposal_id)

        alerts: List[Dict[str, Any]] = []
        alerts.extend(self._detect_identity_clusters(proposal_id, entry))
        alerts.extend(self._detect_new_account_swarms(proposal_id))
        alerts.extend(self._detect_burst_activity(proposal_id))
        alerts.extend(self._detect_power_skew(proposal_id, entry))

        if alerts:
            if any(alert.get("type") == "new_account_suspicion" for alert in alerts):
                self.alerts[proposal_id] = [
                    existing
                    for existing in self.alerts[proposal_id]
                    if existing.get("type") != "new_account_suspicion"
                ]
            self.alerts[proposal_id].extend(alerts)
        return alerts

    def get_alerts(self, proposal_id: str) -> List[Dict[str, Any]]:
        """Return previously generated alerts for a proposal."""
        alerts = list(self.alerts.get(proposal_id, []))
        new_account_alerts = [
            alert for alert in alerts if alert.get("type") == "new_account_suspicion"
        ]
        other_alerts = [
            alert for alert in alerts if alert.get("type") != "new_account_suspicion"
        ]
        new_account_alerts.sort(
            key=lambda alert: len(alert.get("unique_voters", [])), reverse=True
        )
        return new_account_alerts + other_alerts

    def _prune_records(self, proposal_id: str) -> None:
        cutoff = time.time() - self.PRUNE_WINDOW_SECONDS
        self.vote_records[proposal_id] = [
            record for record in self.vote_records[proposal_id] if record["timestamp"] >= cutoff
        ]

    def _calculate_total_power(self, proposal_id: str) -> float:
        return sum(record["voting_power"] for record in self.vote_records[proposal_id])

    def _extract_cluster_keys(self, metadata: Dict[str, Any]) -> List[Tuple[str, str]]:
        keys: List[Tuple[str, str]] = []
        ip_address = metadata.get("ip_address")
        if isinstance(ip_address, str) and ip_address.count(".") >= 1:
            subnet = ".".join(ip_address.split(".")[:3])
            if subnet:
                keys.append(("ip_subnet", subnet))
        device = metadata.get("device_fingerprint")
        if device:
            keys.append(("device_fingerprint", str(device)))
        wallet_cluster = metadata.get("wallet_cluster") or metadata.get("linked_wallet")
        if wallet_cluster:
            keys.append(("wallet_cluster", str(wallet_cluster)))
        geo = metadata.get("geo_hash")
        if geo:
            keys.append(("geo_hash", str(geo)))
        return keys

    def _detect_identity_clusters(
        self, proposal_id: str, latest_entry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not latest_entry["cluster_keys"]:
            return []
        now = latest_entry["timestamp"]
        recent_records = [
            record
            for record in self.vote_records[proposal_id]
            if now - record["timestamp"] <= self.CLUSTER_WINDOW_SECONDS
        ]
        alerts: List[Dict[str, Any]] = []
        for dimension, value in latest_entry["cluster_keys"]:
            matching = [
                record
                for record in recent_records
                if (dimension, value) in record["cluster_keys"]
            ]
            unique_addresses = {record["address"] for record in matching}
            total_power = sum(record["voting_power"] for record in matching)
            cache_key = (proposal_id, dimension, value)
            if (
                cache_key not in self._cluster_alerted
                and len(unique_addresses) >= self.CLUSTER_MIN_UNIQUE
                and total_power >= self.CLUSTER_MIN_POWER
            ):
                alerts.append(
                    {
                        "type": "identity_cluster",
                        "severity": "high"
                        if len(unique_addresses) > self.CLUSTER_MIN_UNIQUE
                        else "medium",
                        "cluster": {"dimension": dimension, "value": value},
                        "unique_voters": sorted(unique_addresses),
                        "total_voting_power": round(total_power, 3),
                        "window_seconds": self.CLUSTER_WINDOW_SECONDS,
                        "timestamp": now,
                        "message": (
                            f"Detected {len(unique_addresses)} voters sharing {dimension}={value} "
                            f"within {self.CLUSTER_WINDOW_SECONDS // 60} minutes."
                        ),
                    }
                )
                self._cluster_alerted.add(cache_key)
        return alerts

    def _detect_new_account_swarms(self, proposal_id: str) -> List[Dict[str, Any]]:
        now = time.time()
        recent = [
            record
            for record in self.vote_records[proposal_id]
            if now - record["timestamp"] <= self.NEW_ACCOUNT_WINDOW_SECONDS
        ]
        swarm = [
            record
            for record in recent
            if float(record["metadata"].get("account_age_days", 9999)) <= self.NEW_ACCOUNT_MAX_AGE_DAYS
        ]
        if not swarm:
            return []
        unique_addresses = {record["address"] for record in swarm}
        total_power = sum(record["voting_power"] for record in swarm)
        cache_key = f"{proposal_id}:{len(unique_addresses)}:{int(total_power)}"
        if (
            cache_key in self._new_account_alerted
            or len(unique_addresses) < self.NEW_ACCOUNT_MIN_VOTERS
            or total_power < self.NEW_ACCOUNT_MIN_POWER
        ):
            return []
        alert = {
            "type": "new_account_suspicion",
            "severity": "high"
            if len(unique_addresses) >= self.NEW_ACCOUNT_MIN_VOTERS + 2
            else "medium",
            "unique_voters": sorted(unique_addresses),
            "total_voting_power": round(total_power, 3),
            "window_seconds": self.NEW_ACCOUNT_WINDOW_SECONDS,
            "timestamp": now,
            "message": (
                f"{len(unique_addresses)} newly created accounts "
                f"voted within {self.NEW_ACCOUNT_WINDOW_SECONDS // 60} minutes."
            ),
        }
        self._new_account_alerted.add(cache_key)
        return [alert]

    def _detect_burst_activity(self, proposal_id: str) -> List[Dict[str, Any]]:
        now = time.time()
        recent = [
            record
            for record in self.vote_records[proposal_id]
            if now - record["timestamp"] <= self.BURST_WINDOW_SECONDS
        ]
        if len(recent) < self.BURST_MIN_TOTAL:
            return []
        unique_voters = {record["address"] for record in recent}
        cache_key = f"{proposal_id}:{int(now)}:{len(unique_voters)}"
        if len(unique_voters) < self.BURST_MIN_UNIQUE or cache_key in self._burst_alerted:
            return []
        total_power = sum(record["voting_power"] for record in recent)
        alert = {
            "type": "burst_activity",
            "severity": "high" if len(unique_voters) >= self.BURST_MIN_UNIQUE + 3 else "medium",
            "unique_voters": len(unique_voters),
            "votes_in_window": len(recent),
            "window_seconds": self.BURST_WINDOW_SECONDS,
            "total_voting_power": round(total_power, 3),
            "timestamp": now,
            "message": (
                f"{len(recent)} votes (unique {len(unique_voters)}) observed "
                f"within {self.BURST_WINDOW_SECONDS} seconds."
            ),
        }
        self._burst_alerted.add(cache_key)
        return [alert]

    def _detect_power_skew(
        self, proposal_id: str, latest_entry: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        total_power = self._calculate_total_power(proposal_id)
        if total_power <= 0 or not latest_entry["cluster_keys"]:
            return []
        now = latest_entry["timestamp"]
        alerts: List[Dict[str, Any]] = []
        for dimension, value in latest_entry["cluster_keys"]:
            matching = [
                record
                for record in self.vote_records[proposal_id]
                if (dimension, value) in record["cluster_keys"]
            ]
            unique_addresses = {record["address"] for record in matching}
            if len(unique_addresses) < self.POWER_SKEW_MIN_VOTERS:
                continue
            cluster_power = sum(record["voting_power"] for record in matching)
            share = cluster_power / total_power
            cache_key = (proposal_id, dimension, value)
            if share >= self.POWER_SKEW_SHARE and cache_key not in self._power_alerted:
                alerts.append(
                    {
                        "type": "power_anomaly",
                        "severity": "high" if share >= 0.8 else "medium",
                        "cluster": {"dimension": dimension, "value": value},
                        "unique_voters": sorted(unique_addresses),
                        "cluster_power": round(cluster_power, 3),
                        "share_of_total": round(share * 100, 2),
                        "timestamp": now,
                        "message": (
                            f"{dimension}={value} controls {share*100:.2f}% of voting power "
                            f"({len(unique_addresses)} voters)."
                        ),
                    }
                )
                self._power_alerted.add(cache_key)
        return alerts

    def evaluate_sybil_risk(self, proposal_id: str) -> Dict[str, Any]:
        alerts = self.get_alerts(proposal_id)
        severity_weights = {"low": 1, "medium": 3, "high": 6}
        raw_score = sum(severity_weights.get(alert.get("severity", "").lower(), 2) for alert in alerts)
        normalized = min(1.0, raw_score / 18.0)
        return {
            "proposal_id": proposal_id,
            "risk_score": round(normalized, 3),
            "alert_count": len(alerts),
            "alerts": alerts,
        }


class AIWorkloadDistribution:
    """
    Distribute AI workload proportionally among contributors
    """

    QUALITY_FLOOR = 0.25
    QUALITY_CEILING = 1.75

    def __init__(self) -> None:
        self.contributor_pool = {}  # address -> contribution data

    def _ensure_contributor_entry(self, address: str) -> Dict[str, Any]:
        """Return contributor record, creating a baseline entry if needed."""
        if address not in self.contributor_pool:
            self.contributor_pool[address] = {
                "total_minutes": 0,
                "contributions": [],
                "tasks_completed": 0,
                "quality_score": 1.0,
                "last_feedback": None,
            }
        return self.contributor_pool[address]

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def add_contributor(
        self, address: str, ai_model: str, minutes_contributed: float, timestamp: float
    ) -> None:
        """Record AI minutes contribution"""

        entry = self._ensure_contributor_entry(address)
        entry["total_minutes"] += minutes_contributed
        entry["contributions"].append(
            {"ai_model": ai_model, "minutes": minutes_contributed, "timestamp": timestamp}
        )

    def record_task_feedback(
        self,
        address: str,
        planned_minutes: float,
        actual_minutes: Optional[float],
        satisfaction_score: float,
        incidents: int = 0,
        breach_detected: bool = False,
    ) -> float:
        """
        Update contributor quality using post-task telemetry.

        Args:
            address: contributor identifier
            planned_minutes: expected effort
            actual_minutes: observed execution time (defaults to plan if None/0)
            satisfaction_score: 0-1 feedback score from reviewers
            incidents: count of issues discovered during review
            breach_detected: whether a policy/security breach happened

        Returns:
            Updated quality score clamped to [QUALITY_FLOOR, QUALITY_CEILING]
        """
        entry = self._ensure_contributor_entry(address)
        entry["tasks_completed"] += 1

        planned = max(float(planned_minutes or 0.0), 1.0)
        actual = max(float(actual_minutes or planned), 0.5)
        satisfaction = self._clamp(float(satisfaction_score), 0.0, 1.25)
        efficiency = self._clamp(planned / actual, 0.4, 1.5)

        incident_penalty = min(incidents * 0.08, 0.4)
        if breach_detected:
            incident_penalty += 0.25
        stability_bonus = 0.05 if incidents == 0 else 0.0

        target_quality = self._clamp(
            (efficiency * 0.45) + (satisfaction * 0.55) + stability_bonus - incident_penalty,
            0.15,
            1.5,
        )

        smoothing = min(0.35, 0.7 / max(entry["tasks_completed"], 1))
        blended = (entry["quality_score"] * (1 - smoothing)) + (target_quality * smoothing)
        entry["quality_score"] = round(
            self._clamp(blended, self.QUALITY_FLOOR, self.QUALITY_CEILING),
            3,
        )
        entry["last_feedback"] = {
            "planned_minutes": planned_minutes,
            "actual_minutes": actual_minutes,
            "satisfaction_score": satisfaction,
            "incidents": incidents,
            "breach_detected": breach_detected,
            "timestamp": time.time(),
        }
        return entry["quality_score"]

    def calculate_workload_shares(self, total_task_minutes: float) -> Dict:
        """
        Divide AI workload among contributors proportionally

        Example:
        Alice donated 100 minutes (50%)
        Bob donated 60 minutes (30%)
        Carol donated 40 minutes (20%)

        Task requires 20 minutes total:
        Alice does 10 minutes (50%)
        Bob does 6 minutes (30%)
        Carol does 4 minutes (20%)
        """

        total_pool = sum(
            c["total_minutes"]
            * self._clamp(c["quality_score"], self.QUALITY_FLOOR, self.QUALITY_CEILING)
            for c in self.contributor_pool.values()
        )

        if total_pool == 0:
            return {}

        workload = {}

        for address, data in self.contributor_pool.items():
            quality_weight = self._clamp(
                data["quality_score"], self.QUALITY_FLOOR, self.QUALITY_CEILING
            )
            effective_minutes = data["total_minutes"] * quality_weight
            share_percentage = effective_minutes / total_pool
            assigned_minutes = total_task_minutes * share_percentage

            workload[address] = {
                "minutes_assigned": assigned_minutes,
                "share_percentage": share_percentage * 100,
                "total_contributed": data["total_minutes"],
                "quality_score": data["quality_score"],
                "quality_weight": quality_weight,
                "effective_minutes": effective_minutes,
            }

        return workload

    def execute_distributed_task(
        self, task_description: str, total_estimated_minutes: float
    ) -> Dict:
        """
        Execute AI task using distributed workload

        Each contributor's AI works on the task proportionally
        Results merged together
        """

        workload = self.calculate_workload_shares(total_estimated_minutes)

        execution_plan = {
            "task": task_description,
            "total_minutes": total_estimated_minutes,
            "contributor_assignments": [],
        }

        for address, assignment in workload.items():
            execution_plan["contributor_assignments"].append(
                {
                    "contributor": address,
                    "minutes_allocated": assignment["minutes_assigned"],
                    "percentage": assignment["share_percentage"],
                    "ai_model": self._get_best_model_for_contributor(address),
                    "status": "pending",
                }
            )

        return execution_plan

    def apply_execution_feedback(self, feedback_entries: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Batch update contributor quality metrics from execution feedback.

        Args:
            feedback_entries: List of dict entries containing:
                - address
                - planned_minutes
                - actual_minutes
                - satisfaction_score
                - incidents (optional)
                - breach_detected (optional)

        Returns:
            Mapping of address -> updated quality score
        """
        updates: Dict[str, float] = {}
        for entry in feedback_entries:
            address = entry.get("address")
            if not address:
                continue
            updated = self.record_task_feedback(
                address=address,
                planned_minutes=float(entry.get("planned_minutes", 0.0)),
                actual_minutes=entry.get("actual_minutes"),
                satisfaction_score=float(entry.get("satisfaction_score", 0.0)),
                incidents=int(entry.get("incidents", 0)),
                breach_detected=bool(entry.get("breach_detected", False)),
            )
            updates[address] = updated
        return updates

    def _get_best_model_for_contributor(self, address: str) -> str:
        """Get most recent AI model contributor used"""

        contribs = self.contributor_pool[address]["contributions"]
        if contribs:
            return contribs[-1]["ai_model"]
        return "claude-sonnet-4"


class ConsensusRules:
    """
    Dynamic consensus system that adapts to community size
    Prevents whale control through power caps and approval voter count
    """

    def __init__(self) -> None:
        # Single approval threshold
        self.approval_percent = 66  # Supermajority

        # Anti-whale protections
        self.max_individual_power_percent = 20  # No single voter > 20% of total
        self.min_approval_voters = 10  # At least 10 different "yes" votes required

        # Dynamic minimum voters
        self.initial_min_voters = 250
        self.reduction_rate = 0.20  # Lower by 20% each failed vote
        self.absolute_minimum = 50  # Never go below 50 voters
        self.revote_delay_days = 7  # Wait 7 days before revote

    def _apply_power_caps(self, votes: Dict) -> Dict:
        """
        Cap individual voting power to prevent whale control
        Returns adjusted votes
        """

        total_power = sum(v["voting_power"] for v in votes.values())
        voter_count = max(1, len(votes))
        max_vote_power = max((v["voting_power"] for v in votes.values()), default=0.0)
        average_power = total_power / voter_count if voter_count else 0.0
        min_voters_for_cap = max(
            1, math.ceil(100 / max(self.max_individual_power_percent, 1))
        )
        skip_caps_for_low_turnout = (
            voter_count < min_voters_for_cap
            and max_vote_power <= average_power * 1.05
        )
        if skip_caps_for_low_turnout:
            max_allowed_power = float("inf")
        else:
            max_allowed_power = total_power * (self.max_individual_power_percent / 100)

        adjusted_votes = {}
        for address, vote_data in votes.items():
            adjusted_power = min(vote_data["voting_power"], max_allowed_power)
            adjusted_votes[address] = {
                "vote": vote_data["vote"],
                "voting_power": adjusted_power,
                "original_power": vote_data["voting_power"],
                "capped": adjusted_power < vote_data["voting_power"],
            }

        return adjusted_votes

    def check_consensus_reached(
        self, proposal: Dict, votes: Dict, current_min_voters: int = None
    ) -> Tuple[bool, str, Dict]:
        """
        Check if proposal reached consensus

        Returns:
            (consensus_reached, reason, next_action)
        """

        if current_min_voters is None:
            current_min_voters = self.initial_min_voters

        # Apply power caps to prevent whale control
        adjusted_votes = self._apply_power_caps(votes)

        # Count votes with adjusted power
        total_voting_power = sum(v["voting_power"] for v in adjusted_votes.values())
        approval_power = sum(
            v["voting_power"] for v in adjusted_votes.values() if v["vote"] == "yes"
        )
        approval_voter_count = sum(1 for v in adjusted_votes.values() if v["vote"] == "yes")
        voter_count = len(adjusted_votes)

        # Check minimum voters
        if voter_count < current_min_voters:
            # Calculate next threshold
            next_min_voters = max(
                int(current_min_voters * (1 - self.reduction_rate)), self.absolute_minimum
            )

            return (
                False,
                f"Need {current_min_voters} voters, have {voter_count}",
                {
                    "action": "revote",
                    "wait_days": self.revote_delay_days,
                    "next_min_voters": next_min_voters,
                    "reason": "insufficient_turnout",
                },
            )

        # Check minimum approval voters (prevents single whale from deciding)
        if approval_voter_count < self.min_approval_voters:
            return (
                False,
                f"Need {self.min_approval_voters} different 'yes' votes, have {approval_voter_count}",
                {"action": "rejected", "reason": "insufficient_approval_diversity"},
            )

        # Check approval percentage
        approval_percent = (
            (approval_power / total_voting_power * 100) if total_voting_power > 0 else 0
        )

        if approval_percent < self.approval_percent:
            return (
                False,
                f"Need {self.approval_percent}% approval, have {approval_percent:.1f}%",
                {"action": "rejected", "reason": "insufficient_approval"},
            )

        return (
            True,
            f"Consensus reached: {approval_percent:.1f}% approval from {voter_count} voters",
            {
                "action": "approved",
                "approval_percent": approval_percent,
                "voter_count": voter_count,
                "approval_voter_count": approval_voter_count,
            },
        )


class AIGovernanceProposal:
    """Proposal with adaptive voting and timelock"""

    def __init__(
        self,
        title: str,
        category: str,
        description: str,
        detailed_prompt: str,
        estimated_minutes: float,
        proposal_type: ProposalType = ProposalType.AI_IMPROVEMENT,
        parameter_change: Optional[Dict] = None,
        submitter_address: Optional[str] = None,
        submitter_voting_power: float = 0,
    ) -> None:
        self.proposal_id = hashlib.sha256(f"{title}{time.time()}".encode()).hexdigest()[:16]
        self.title = title
        self.category = category
        self.description = description
        self.detailed_prompt = detailed_prompt
        self.estimated_minutes = estimated_minutes
        self.proposal_type = proposal_type
        self.parameter_change = parameter_change  # For PARAMETER_CHANGE type
        self.submitter_address = submitter_address
        self.submitter_voting_power = submitter_voting_power

        self.votes = {}  # address -> vote data
        self.status = "proposed"
        self.created_at = time.time()

        # Community estimation process
        self.time_estimates = {}  # address -> estimated_minutes
        self.consensus_time_estimate = estimated_minutes

        # Adaptive voting tracking
        self.vote_attempts = []  # List of vote attempts
        self.current_min_voters = 250  # Start at initial threshold
        self.next_vote_time = None

        # Timelock tracking
        self.approval_time = None
        self.timelock_expiry = None
        self.timelock_days = None

        self.execution_result = None
        self.code_review_status = None

    def cast_vote(self, voter_address: str, vote: str, voting_power: float) -> None:
        """Record vote with voting power"""

        self.votes[voter_address] = {
            "vote": vote,  # 'yes', 'no', 'abstain'
            "voting_power": voting_power,
            "timestamp": time.time(),
        }

    def submit_time_estimate(
        self, voter_address: str, estimated_minutes: float, voter_power: float
    ) -> Dict:
        """
        Community members estimate AI work time
        Weighted by voting power to prevent spam
        """

        if estimated_minutes <= 0:
            return {"success": False, "error": "Invalid estimate"}

        self.time_estimates[voter_address] = {
            "minutes": estimated_minutes,
            "voting_power": voter_power,
            "timestamp": time.time(),
        }

        # Recalculate weighted average
        total_weight = sum(e["voting_power"] for e in self.time_estimates.values())
        weighted_sum = sum(e["minutes"] * e["voting_power"] for e in self.time_estimates.values())

        self.consensus_time_estimate = (
            weighted_sum / total_weight if total_weight > 0 else self.estimated_minutes
        )

        return {
            "success": True,
            "your_estimate": estimated_minutes,
            "community_average": self.consensus_time_estimate,
            "estimate_count": len(self.time_estimates),
        }

    def close_vote_attempt(self, consensus_rules: "ConsensusRules") -> Dict:
        """
        Close current vote attempt and determine next action
        """

        reached, reason, next_action = consensus_rules.check_consensus_reached(
            {"title": self.title, "category": self.category}, self.votes, self.current_min_voters
        )

        # Record this attempt
        self.vote_attempts.append(
            {
                "timestamp": time.time(),
                "voter_count": len(self.votes),
                "min_required": self.current_min_voters,
                "result": "passed" if reached else "failed",
                "reason": reason,
            }
        )

        if next_action["action"] == "revote":
            # Schedule revote with lower threshold
            self.current_min_voters = next_action["next_min_voters"]
            self.next_vote_time = time.time() + (next_action["wait_days"] * 86400)
            self.votes = {}  # Clear votes for fresh start
            self.status = "revote_scheduled"

            return {
                "result": "revote_scheduled",
                "next_min_voters": self.current_min_voters,
                "next_vote_time": self.next_vote_time,
                "wait_days": next_action["wait_days"],
                "attempt_number": len(self.vote_attempts),
            }

        elif next_action["action"] == "approved":
            self.status = "approved_timelock"
            self.approval_time = time.time()
            return {
                "result": "approved_timelock",
                "approval_percent": next_action["approval_percent"],
                "voter_count": next_action["voter_count"],
                "approval_voter_count": next_action.get("approval_voter_count", 0),
                "attempt_number": len(self.vote_attempts),
                "message": "Approved - timelock activated",
            }

        else:  # rejected
            self.status = "rejected"
            return {
                "result": "rejected",
                "reason": next_action["reason"],
                "attempt_number": len(self.vote_attempts),
            }

    def activate_timelock(self, governance_params: "GovernanceParameters") -> Dict:
        """
        Activate timelock after approval
        Standard mechanism: delay between approval and execution
        """

        if self.status != "approved_timelock":
            return {"success": False, "error": "Proposal not in approved state"}

        self.timelock_days = governance_params.get_timelock_duration(self.proposal_type)
        self.timelock_expiry = self.approval_time + (self.timelock_days * 86400)
        self.status = "timelock_active"

        return {
            "success": True,
            "timelock_days": self.timelock_days,
            "timelock_expiry": self.timelock_expiry,
            "can_execute_at": self.timelock_expiry,
        }

    def can_execute(self) -> Tuple[bool, str]:
        """Check if proposal can be executed"""

        if self.status != "timelock_active":
            return False, f"Status is {self.status}, not timelock_active"

        if time.time() < self.timelock_expiry:
            days_remaining = (self.timelock_expiry - time.time()) / 86400
            return False, f"Timelock active for {days_remaining:.1f} more days"

        return True, "Ready for execution"

    def get_vote_summary(self) -> Dict:
        """Get current vote tallies"""

        yes_power = sum(v["voting_power"] for v in self.votes.values() if v["vote"] == "yes")
        no_power = sum(v["voting_power"] for v in self.votes.values() if v["vote"] == "no")
        abstain_power = sum(
            v["voting_power"] for v in self.votes.values() if v["vote"] == "abstain"
        )
        total_power = yes_power + no_power + abstain_power

        return {
            "yes_power": yes_power,
            "no_power": no_power,
            "abstain_power": abstain_power,
            "total_power": total_power,
            "yes_percent": (yes_power / total_power * 100) if total_power > 0 else 0,
            "voter_count": len(self.votes),
            "min_voters_needed": self.current_min_voters,
            "vote_attempt": len(self.vote_attempts) + 1,
        }


class ProposalImpactAnalyzer:
    """
    AI-powered proposal impact analysis system.
    Provides detailed analysis reports for governance proposals.
    """

    def __init__(self, ai_executor=None):
        """
        Initialize impact analyzer with optional AI executor

        Args:
            ai_executor: Optional AI executor for ML-powered analysis
        """
        self.ai_executor = ai_executor
        self.analysis_cache: Dict[str, Dict] = {}

    @staticmethod
    def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
        """Clamp floating point values into a closed range."""
        return max(min_value, min(max_value, value))

    @staticmethod
    def _normalize_iterable(value: Any) -> List[str]:
        """Convert iterable or scalar into a list of lowercase strings."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value.lower()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).lower() for item in value if isinstance(item, (str, int, float))]
        return []

    def _extract_tags(self, proposal: Dict) -> Set[str]:
        """Collect normalized tags/keywords describing the proposal impact surface."""
        tags: Set[str] = set()
        for key in ("tags", "components", "modules", "impact_scope"):
            tags.update(self._normalize_iterable(proposal.get(key)))

        description = str(proposal.get("description", "")).lower()
        keyword_hints = [
            "wallet",
            "consensus",
            "p2p",
            "governance",
            "api",
            "trading",
            "privacy",
            "ai",
            "mining",
            "staking",
        ]
        for keyword in keyword_hints:
            if keyword in description:
                tags.add(keyword)
        return tags

    @staticmethod
    def _score_keywords(text: str, keyword_weights: Dict[str, float]) -> float:
        """Score text based on presence of weighted keywords."""
        lowered = text.lower()
        return sum(weight for keyword, weight in keyword_weights.items() if keyword in lowered)

    def analyze_proposal_impact(
        self, proposal: Dict, historical_data: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive impact analysis for a proposal

        Args:
            proposal: Proposal data
            historical_data: Optional historical data for trend analysis

        Returns:
            Detailed impact analysis report
        """
        analysis_id = hashlib.sha256(
            f"{proposal.get('proposal_id', '')}_{time.time()}".encode()
        ).hexdigest()[:16]

        # Component analyses
        technical_analysis = self._analyze_technical_changes(proposal)
        financial_impact = self._analyze_financial_impact(proposal, historical_data)
        security_assessment = self._assess_security_implications(proposal)
        community_impact = self._predict_community_impact(proposal, historical_data)
        risk_assessment = self._assess_risks(
            proposal,
            technical_analysis,
            security_assessment,
            financial_impact,
            community_impact,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            proposal,
            risk_assessment,
            community_impact,
            technical_analysis,
            security_assessment,
            financial_impact,
        )

        # Calculate overall score (0-100)
        overall_score = self._calculate_overall_score(
            risk_assessment,
            community_impact,
            technical_analysis,
            security_assessment,
            financial_impact,
        )

        analysis = {
            "analysis_id": analysis_id,
            "proposal_id": proposal.get("proposal_id", "unknown"),
            "timestamp": time.time(),
            "overall_score": overall_score,
            "recommendation": self._determine_recommendation(overall_score),
            "risk_assessment": risk_assessment,
            "community_impact": community_impact,
            "technical_analysis": technical_analysis,
            "financial_impact": financial_impact,
            "security_assessment": security_assessment,
            "recommendations": recommendations,
            "confidence_level": self._calculate_confidence(overall_score),
        }

        # Cache analysis
        self.analysis_cache[analysis_id] = analysis

        return analysis

    def _assess_risks(
        self,
        proposal: Dict,
        technical_analysis: Dict,
        security_assessment: Dict,
        financial_impact: Dict,
        community_impact: Dict,
    ) -> Dict:
        """Assess proposal risks using holistic signal aggregation."""
        description = str(proposal.get("description", "")).lower()
        tags = self._extract_tags(proposal)
        modules = proposal.get("modules") or proposal.get("components") or []
        files_to_modify = proposal.get("files_to_modify", [])
        change_surface = (
            len(modules) if isinstance(modules, (list, tuple, set)) else 0
        ) + (len(files_to_modify) if isinstance(files_to_modify, (list, tuple, set)) else 0)
        estimated_minutes = max(float(proposal.get("estimated_minutes", 0)), 1.0)

        risk_factors: List[str] = []
        mitigation_strategies: List[str] = []

        def _add_unique(target: List[str], item: str) -> None:
            if item not in target:
                target.append(item)

        technical_risk = 0.2 + 0.05 * math.log1p(estimated_minutes)
        technical_risk += 0.02 * min(change_surface, 15)
        technical_risk += 0.25 * technical_analysis.get("complexity_score", 0.0)
        if technical_analysis.get("breaking_changes"):
            technical_risk += 0.18
            _add_unique(risk_factors, "Breaking changes require coordinated rollouts")
            _add_unique(mitigation_strategies, "Publish migration tooling and run staggered rollout")
        if "consensus" in tags or "p2p" in tags:
            technical_risk += 0.12
            _add_unique(risk_factors, "Consensus/p2p mechanics being modified")
            _add_unique(mitigation_strategies, "Run deterministic network simulations prior to mainnet")
        if proposal.get("requires_data_migration") or "database" in description:
            technical_risk += 0.1
            _add_unique(risk_factors, "State migrations could corrupt chain data")
            _add_unique(mitigation_strategies, "Capture pre/post migration snapshots with validation")
        if proposal.get("introduces_new_crypto"):
            technical_risk += 0.08
            _add_unique(risk_factors, "Novel cryptography path requires peer review")
            _add_unique(mitigation_strategies, "Validate crypto primitives with test vectors")
        technical_risk = self._clamp(technical_risk)

        security_risk = 1.0 - security_assessment.get("security_score", 1.0)
        if proposal.get("requires_external_audit"):
            security_risk = min(0.95, security_risk + 0.15)
            _add_unique(risk_factors, "Proposal already marked as requiring external audit")
        if proposal.get("introduces_new_ai_policy"):
            security_risk = min(0.95, security_risk + 0.08)
            _add_unique(risk_factors, "AI policy change could bypass safety guardrails")
            _add_unique(mitigation_strategies, "Run independent AI policy review and staged rollout")

        budget_cap = float(proposal.get("budget_cap_usd") or 400000.0)
        implementation_cost = float(financial_impact.get("implementation_cost_usd", 0.0))
        cost_ratio = financial_impact.get("cost_benefit_ratio", 0.0)
        financial_risk = self._clamp(
            0.15
            + 0.4 * (implementation_cost / max(budget_cap, 1.0))
            + (0.2 if cost_ratio < 1.0 else 0.0)
        )
        if implementation_cost > budget_cap:
            _add_unique(risk_factors, "Implementation cost exceeds configured budget")
            _add_unique(mitigation_strategies, "Secure staged funding approvals before build")
        if cost_ratio < 1.0:
            _add_unique(risk_factors, "ROI below breakeven threshold")
            _add_unique(mitigation_strategies, "Trim scope or identify incremental revenue offsets")

        adoption_risk = 0.15
        if proposal.get("breaking_changes") or "breaking" in description:
            adoption_risk += 0.2
            _add_unique(risk_factors, "User-facing breaking changes risk churn")
        if proposal.get("requires_user_action") or proposal.get("forces_migration"):
            adoption_risk += 0.15
            _add_unique(risk_factors, "Requires mandatory client/user action")
            _add_unique(mitigation_strategies, "Provide beta channel and scripted upgrade helpers")
        community_sentiment = community_impact.get("adoption_likelihood", 0.5)
        adoption_risk += max(0.0, 0.6 - community_sentiment) * 0.5
        adoption_risk = self._clamp(adoption_risk)

        overall_risk = (
            technical_risk * 0.35
            + security_risk * 0.3
            + financial_risk * 0.2
            + adoption_risk * 0.15
        )

        return {
            "technical_risk": round(technical_risk, 3),
            "security_risk": round(security_risk, 3),
            "financial_risk": round(financial_risk, 3),
            "adoption_risk": round(adoption_risk, 3),
            "overall_risk_score": round(self._clamp(overall_risk), 3),
            "risk_factors": risk_factors or ["No critical risks flagged"],
            "mitigation_strategies": mitigation_strategies
            or ["Maintain heightened monitoring during rollout"],
        }

    def _predict_community_impact(
        self, proposal: Dict, historical_data: Optional[Dict] = None
    ) -> Dict:
        """Predict how proposal will impact the community with contextual signals."""
        historical = historical_data or {}
        feedback = proposal.get("community_feedback", {})
        description = str(proposal.get("description", ""))
        tags = self._extract_tags(proposal)

        base_sentiment = feedback.get("sentiment_score")
        if base_sentiment is None:
            positive_weight = {
                "improve": 0.04,
                "privacy": 0.05,
                "reduce fees": 0.06,
                "performance": 0.04,
                "throughput": 0.03,
            }
            negative_weight = {
                "deprecate": 0.05,
                "breaking": 0.05,
                "fee increase": 0.06,
                "downtime": 0.04,
            }
            base = 0.55
            base += self._score_keywords(description, positive_weight)
            base -= self._score_keywords(description, negative_weight)
            base_sentiment = self._clamp(base)

        supporters = float(feedback.get("support_votes", proposal.get("supporters", 0)))
        opposers = float(feedback.get("opposition_votes", proposal.get("opponents", 0)))
        total_votes = supporters + opposers
        support_ratio = supporters / total_votes if total_votes > 0 else base_sentiment

        feature_requests = float(feedback.get("feature_requests", 0))
        avg_requests = float(historical.get("avg_feature_requests", 25) or 25)
        request_pressure = self._clamp(feature_requests / (avg_requests * 2.0))

        adoption_likelihood = self._clamp(
            0.35
            + 0.35 * base_sentiment
            + 0.2 * support_ratio
            + 0.1 * request_pressure
        )

        scope_mapping = {
            "global": 0.85,
            "wallet": 0.75,
            "api": 0.65,
            "node": 0.55,
            "developer": 0.45,
            "consensus": 0.50,
            "trading": 0.48,
            "mining": 0.52,
        }
        scope_key = str(proposal.get("impact_scope", "")).lower()
        scope_values = [scope_mapping[key] for key in scope_mapping if key in tags]
        scope_weight = scope_mapping.get(scope_key) or (max(scope_values) if scope_values else 0.45)
        affected_user_percentage = self._clamp(scope_weight + 0.1 * request_pressure)

        benefit_inputs = proposal.get("expected_benefits", [])
        if isinstance(benefit_inputs, str):
            positive_impacts = [benefit_inputs]
        elif isinstance(benefit_inputs, (list, tuple, set)):
            positive_impacts = [str(item) for item in benefit_inputs if item]
        else:
            positive_impacts = []

        if not positive_impacts:
            if "wallet" in tags:
                positive_impacts.append("Improves wallet usability and safety")
            if "consensus" in tags:
                positive_impacts.append("Stronger finality and fork resistance")
            if "api" in tags or "trading" in tags:
                positive_impacts.append("Unlocks new integration and trading flows")
            if not positive_impacts:
                positive_impacts.append("General ecosystem improvement")

        negative_inputs = proposal.get("known_risks", [])
        if isinstance(negative_inputs, str):
            negative_impacts = [negative_inputs]
        elif isinstance(negative_inputs, (list, tuple, set)):
            negative_impacts = [str(item) for item in negative_inputs if item]
        else:
            negative_impacts = []

        if proposal.get("breaking_changes") or "breaking" in description:
            negative_impacts.append("Requires coordinated client upgrades")
        if request_pressure < 0.2 and adoption_likelihood < 0.5:
            negative_impacts.append("Potentially limited immediate demand")
        if not negative_impacts:
            negative_impacts.append("Learning curve for upgraded workflows")

        benefits_score = 0.55 + 0.2 * self._score_keywords(
            description,
            {"performance": 0.2, "privacy": 0.2, "fee": 0.15, "stability": 0.15},
        )
        user_benefit_score = self._clamp(benefits_score)

        stakeholder_templates = {
            "miners": {"keywords": {"mining", "miner", "consensus", "pow"}},
            "node_operators": {"keywords": {"node", "p2p", "consensus", "governance"}},
            "users": {"keywords": {"wallet", "fee", "privacy", "ux"}},
            "developers": {"keywords": {"api", "sdk", "contract", "developer"}},
        }

        stakeholder_groups: Dict[str, Dict[str, Any]] = {}
        for group, profile in stakeholder_templates.items():
            impact_base = 0.2
            if profile["keywords"] & tags:
                impact_base = 0.6
            elif any(keyword in description for keyword in profile["keywords"]):
                impact_base = 0.45
            impact_value = self._clamp(impact_base + 0.1 * request_pressure)
            sentiment_label = (
                "positive"
                if adoption_likelihood >= 0.6
                else "mixed"
                if adoption_likelihood >= 0.45
                else "negative"
            )
            if "fee increase" in description and group == "users":
                sentiment_label = "negative"
            stakeholder_groups[group] = {
                "impact": round(impact_value, 2),
                "sentiment": sentiment_label,
            }

        return {
            "adoption_likelihood": round(adoption_likelihood, 3),
            "user_benefit_score": round(user_benefit_score, 3),
            "affected_user_percentage": round(affected_user_percentage, 3),
            "positive_impacts": positive_impacts,
            "negative_impacts": negative_impacts,
            "stakeholder_groups": stakeholder_groups,
        }

    def _analyze_technical_changes(self, proposal: Dict) -> Dict:
        """Analyze technical aspects of the proposal."""
        tags = self._extract_tags(proposal)
        description = str(proposal.get("description", "")).lower()
        estimated_minutes = max(float(proposal.get("estimated_minutes", 0)), 1.0)
        files_to_modify = proposal.get("files_to_modify", [])
        components = proposal.get("modules") or proposal.get("components") or []
        files_count = len(files_to_modify) if isinstance(files_to_modify, (list, tuple, set)) else 0
        component_count = len(components) if isinstance(components, (list, tuple, set)) else 0

        requires_migration = bool(
            proposal.get("requires_data_migration")
            or "database" in tags
            or "state" in description
        )
        touches_consensus = "consensus" in tags
        new_crypto = bool(
            proposal.get("introduces_new_crypto")
            or any(keyword in description for keyword in ["zk", "kzg", "bls", "signature"])
        )
        concurrency_sensitive = bool(proposal.get("touches_concurrency") or "p2p" in tags)

        complexity = 0.2 + 0.05 * math.log1p(estimated_minutes)
        complexity += 0.02 * min(files_count, 25)
        complexity += 0.03 * min(component_count, 15)
        if requires_migration:
            complexity += 0.12
        if touches_consensus or concurrency_sensitive:
            complexity += 0.1
        if new_crypto:
            complexity += 0.1
        complexity = self._clamp(complexity, max_value=0.98)

        raw_dependencies = proposal.get("dependencies", [])
        dependencies: Set[str] = set()
        if isinstance(raw_dependencies, str):
            dependencies.add(raw_dependencies)
        elif isinstance(raw_dependencies, (list, tuple, set)):
            dependencies.update(str(dep) for dep in raw_dependencies if dep)
        if touches_consensus:
            dependencies.add("consensus_manager")
        if "wallet" in tags:
            dependencies.add("wallet_manager")
        if "api" in tags:
            dependencies.add("node_api")
        if new_crypto:
            dependencies.add("crypto_primitives")

        breaking_changes = bool(
            proposal.get("breaking_changes")
            or "breaking change" in description
            or "hardfork" in description
        )
        backward_compatible = not breaking_changes and not requires_migration

        testing_requirements: List[str] = []
        if touches_consensus:
            testing_requirements.append("deterministic consensus regression")
        if "wallet" in tags:
            testing_requirements.append("wallet integration and hardware wallet tests")
        if "api" in tags or "trading" in tags:
            testing_requirements.append("public API contract and load tests")
        if new_crypto:
            testing_requirements.append("cryptographic vector verification")
        if not testing_requirements:
            testing_requirements.append("comprehensive unit and integration tests")

        documentation_updates = ["Release notes", "Runbook updates"]
        if "api" in tags:
            documentation_updates.append("API reference")
        if "wallet" in tags:
            documentation_updates.append("User wallet guide")
        if breaking_changes:
            documentation_updates.append("Migration/upgrade guide")

        implementation_effort = round(
            estimated_minutes
            * (
                1
                + 0.05 * min(files_count + component_count, 10)
                + (0.1 if new_crypto else 0)
                + (0.12 if requires_migration else 0)
            ),
            2,
        )

        return {
            "complexity_score": round(complexity, 3),
            "implementation_effort": implementation_effort,
            "dependencies": sorted(dependencies),
            "breaking_changes": breaking_changes,
            "backward_compatible": backward_compatible,
            "testing_requirements": ", ".join(testing_requirements),
            "documentation_updates": documentation_updates,
        }

    def _analyze_financial_impact(
        self, proposal: Dict, historical_data: Optional[Dict] = None
    ) -> Dict:
        """Analyze financial implications with realistic production estimates."""
        tags = self._extract_tags(proposal)
        historical = historical_data or {}
        estimated_minutes = max(float(proposal.get("estimated_minutes", 0)), 0.0)
        specialized_roles = proposal.get("specialist_roles") or []
        role_count = len(specialized_roles) if isinstance(specialized_roles, (list, tuple, set)) else 0

        base_cost_per_minute = float(
            proposal.get("cost_per_minute")
            or historical.get("avg_cost_per_minute")
            or 3.0  # ≈$180/hour engineer cost
        )

        risk_multiplier = 1.0
        if "consensus" in tags or "p2p" in tags:
            risk_multiplier += 0.2
        if "wallet" in tags or proposal.get("handles_keys"):
            risk_multiplier += 0.15
        if proposal.get("requires_external_audit") or proposal.get("security_sensitive"):
            risk_multiplier += 0.1

        vendor_costs = float(proposal.get("external_contractors_cost", 0.0))
        implementation_cost = (
            estimated_minutes
            * base_cost_per_minute
            * (1 + 0.05 * min(role_count, 8))
            * risk_multiplier
            + vendor_costs
        )
        implementation_cost = round(implementation_cost, 2)

        maintenance_multiplier = 0.2 + 0.05 * risk_multiplier
        maintenance_cost = round(implementation_cost * maintenance_multiplier, 2)

        expected_savings = float(proposal.get("expected_annual_savings_usd") or 0.0)
        expected_revenue = float(proposal.get("expected_revenue_increase_usd") or 0.0)
        if not expected_savings and not expected_revenue:
            baseline_gain = estimated_minutes * base_cost_per_minute * (0.6 if "wallet" in tags else 0.4)
            expected_savings = max(baseline_gain, 5000.0 if "wallet" in tags else 2500.0)
        expected_benefit = expected_savings + expected_revenue

        expected_monthly_benefit = float(
            proposal.get("expected_monthly_benefit_usd") or (expected_benefit / 12.0)
        )
        expected_monthly_benefit = max(expected_monthly_benefit, 1.0)
        break_even_period = int(math.ceil(implementation_cost / expected_monthly_benefit))

        cost_benefit_ratio = (
            expected_benefit / implementation_cost if implementation_cost else 0.0
        )
        roi_summary = (
            f"Projected {cost_benefit_ratio:.2f}x return with breakeven in "
            f"{break_even_period} months"
        )

        return {
            "implementation_cost_usd": implementation_cost,
            "maintenance_cost_annual_usd": maintenance_cost,
            "expected_roi": roi_summary,
            "break_even_period_months": break_even_period,
            "cost_benefit_ratio": round(cost_benefit_ratio, 2),
        }

    def _assess_security_implications(self, proposal: Dict) -> Dict:
        """Assess security implications with granular attack surface analysis."""
        tags = self._extract_tags(proposal)
        description = str(proposal.get("description", "")).lower()
        attack_vectors_input = proposal.get("identified_attack_vectors", [])
        attack_vectors: List[str] = (
            list(attack_vectors_input)
            if isinstance(attack_vectors_input, (list, tuple, set))
            else ([attack_vectors_input] if isinstance(attack_vectors_input, str) else [])
        )

        handles_keys = bool(
            proposal.get("handles_keys")
            or "private key" in description
            or "seed phrase" in description
            or "wallet" in tags
        )
        touches_consensus = "consensus" in tags
        touches_api = "api" in tags or "endpoint" in description
        introduces_contracts = bool(proposal.get("deploys_contracts") or "contract" in description)
        privacy_sensitive = "privacy" in tags or "kyc" in description
        new_crypto = bool(proposal.get("introduces_new_crypto"))

        def _append_attack_vector(message: str) -> None:
            if message not in attack_vectors:
                attack_vectors.append(message)

        risk = 0.12
        if proposal.get("changes_validator_sets"):
            risk += 0.18
            _append_attack_vector("Validator set change could weaken finality/quorum assumptions")
        if proposal.get("introduces_new_ai_policy"):
            risk += 0.08
            _append_attack_vector("AI policy drift could bypass safety guardrails")
        if handles_keys:
            risk += 0.25
            _append_attack_vector("Key exposure / wallet compromise")
        if touches_consensus:
            risk += 0.2
            _append_attack_vector("Consensus regression leading to fork or double spend")
        if touches_api:
            risk += 0.1
            _append_attack_vector("API abuse, replay, or injection attacks")
        if introduces_contracts:
            risk += 0.08
            _append_attack_vector("Smart-contract level reentrancy or invariant violations")
        if new_crypto:
            risk += 0.15
            _append_attack_vector("Incorrect cryptographic parameterization")

        risk = min(risk, 0.95)
        security_score = self._clamp(1.0 - risk, 0.0, 0.99)
        requires_audit = risk >= 0.35 or bool(proposal.get("requires_external_audit"))

        security_controls = [
            "Input validation and strict schema enforcement",
            "Authenticated access with scoped API keys",
            "Rate limiting and anomaly detection on critical endpoints",
        ]
        if handles_keys:
            security_controls.append("Hardware-backed key storage or encrypted KMS")
        if touches_consensus:
            security_controls.append("Deterministic consensus simulations before rollout")
            security_controls.append("Require finality checkpoints and safety-liveness proofs")
        if introduces_contracts:
            security_controls.append("Static analysis and fuzzing of contract bytecode")
        if proposal.get("changes_validator_sets"):
            security_controls.append("On-chain validator attestation of new set and rollback plan")
        if proposal.get("introduces_new_ai_policy"):
            security_controls.append("Independent AI safety review with rollback if guardrails regress")

        encryption_requirements = "TLS 1.3 + encrypted state at rest"
        if handles_keys:
            encryption_requirements = "HSM-backed key wrapping with per-tenant secrets"
        elif privacy_sensitive:
            encryption_requirements = "End-to-end encryption for user data + secure enclaves"

        compliance_inputs = proposal.get("compliance_requirements", [])
        compliance_considerations = (
            list(compliance_inputs)
            if isinstance(compliance_inputs, (list, tuple, set))
            else ([compliance_inputs] if isinstance(compliance_inputs, str) else [])
        )
        if privacy_sensitive:
            compliance_considerations.append("Data privacy (GDPR/CCPA)")
        if handles_keys:
            compliance_considerations.append("Custodial controls / AML policies")
        if touches_consensus:
            compliance_considerations.append("Network finality SLAs")

        return {
            "security_score": round(security_score, 3),
            "requires_audit": requires_audit,
            "attack_vectors": attack_vectors,
            "security_controls": security_controls,
            "encryption_requirements": encryption_requirements,
            "compliance_considerations": compliance_considerations or ["Operational transparency"],
        }

    def _generate_recommendations(
        self,
        proposal: Dict,
        risk_assessment: Dict,
        community_impact: Dict,
        technical_analysis: Dict,
        security_assessment: Dict,
        financial_impact: Dict,
    ) -> List[str]:
        """Generate actionable recommendations anchored to the detected risks."""
        tags = self._extract_tags(proposal)
        recommendations: List[str] = []

        def _add(msg: str) -> None:
            if msg not in recommendations:
                recommendations.append(msg)

        if (
            risk_assessment["technical_risk"] >= 0.6
            or technical_analysis.get("complexity_score", 0.0) >= 0.6
        ):
            _add("RECOMMEND: Stage rollout behind feature flags and canary deploys")
        if technical_analysis.get("breaking_changes"):
            _add("RECOMMEND: Publish migration guides and automated upgrade tooling")
        if "consensus" in tags or "p2p" in tags:
            _add("RECOMMEND: Run multi-region testnets with deterministic replay coverage")

        if security_assessment.get("requires_audit") or risk_assessment["security_risk"] >= 0.5:
            _add("RECOMMEND: Commission independent security audit and threat modeling")
        if proposal.get("handles_keys") or "wallet" in tags:
            _add("RECOMMEND: Enforce hardware-backed key isolation before enabling globally")

        if risk_assessment["adoption_risk"] >= 0.5 or community_impact["adoption_likelihood"] <= 0.55:
            _add("RECOMMEND: Run community beta with opt-in migrations before hard cutover")
            _add("RECOMMEND: Ship comms plan with FAQs and explicit rollback paths")

        if financial_impact.get("cost_benefit_ratio", 0) < 1.0:
            _add("RECOMMEND: Re-scope deliverables or secure offsetting revenue to justify budget")
        if financial_impact.get("implementation_cost_usd", 0.0) > 500000:
            _add("RECOMMEND: Define phased budget checkpoints tied to measurable milestones")

        _add("RECOMMEND: Establish clear rollback procedures")
        _add("RECOMMEND: Monitor risk telemetry and public metrics post-deployment")

        return recommendations

    def _calculate_overall_score(
        self,
        risk_assessment: Dict,
        community_impact: Dict,
        technical_analysis: Dict,
        security_assessment: Dict,
        financial_impact: Dict,
    ) -> float:
        """Calculate overall proposal score (0-100)"""
        # Invert risk (low risk = high score)
        risk_score = (1.0 - risk_assessment["overall_risk_score"]) * 100

        # Community impact score
        community_score = community_impact["user_benefit_score"] * 100

        # Technical feasibility score
        technical_score = (1.0 - technical_analysis["complexity_score"]) * 100

        # Security score
        security_score = security_assessment["security_score"] * 100

        # Financial score rewards strong ROI and short breakeven periods
        roi_ratio = financial_impact.get("cost_benefit_ratio", 0.0)
        roi_score = self._clamp(min(max(roi_ratio, 0.0), 3.0) / 3.0)
        break_even = max(1, int(financial_impact.get("break_even_period_months", 1)))
        break_even_score = self._clamp(1.0 - min(break_even / 36.0, 1.0))
        financial_score = (roi_score * 0.65 + break_even_score * 0.35) * 100

        # Weighted average
        overall = (
            risk_score * 0.25
            + community_score * 0.2
            + technical_score * 0.2
            + security_score * 0.2
            + financial_score * 0.15
        )

        return round(overall, 2)

    def _determine_recommendation(self, overall_score: float) -> str:
        """Determine final recommendation based on score"""
        if overall_score >= 80:
            return "STRONGLY APPROVE"
        elif overall_score >= 65:
            return "APPROVE WITH CONDITIONS"
        elif overall_score >= 50:
            return "NEUTRAL - NEEDS IMPROVEMENT"
        elif overall_score >= 35:
            return "RECOMMEND REJECTION"
        else:
            return "STRONGLY REJECT"

    def _calculate_confidence(self, overall_score: float) -> float:
        """Calculate confidence in the analysis"""
        # Higher confidence for scores closer to extremes
        distance_from_middle = abs(overall_score - 50)
        confidence = min(0.5 + (distance_from_middle / 100), 0.95)
        return round(confidence, 2)

    def generate_analysis_report(self, analysis: Dict) -> str:
        """Generate human-readable analysis report"""
        report = f"""
{'='*80}
PROPOSAL IMPACT ANALYSIS REPORT
{'='*80}

Proposal ID: {analysis['proposal_id']}
Analysis ID: {analysis['analysis_id']}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(analysis['timestamp']))}

OVERALL ASSESSMENT
------------------
Score: {analysis['overall_score']}/100
Recommendation: {analysis['recommendation']}
Confidence: {analysis['confidence_level']*100:.1f}%

RISK ASSESSMENT
---------------
Overall Risk Score: {analysis['risk_assessment']['overall_risk_score']*100:.1f}/100
- Technical Risk: {analysis['risk_assessment']['technical_risk']*100:.1f}/100
- Security Risk: {analysis['risk_assessment']['security_risk']*100:.1f}/100
- Financial Risk: {analysis['risk_assessment']['financial_risk']*100:.1f}/100

Risk Factors:
{chr(10).join('  • ' + factor for factor in analysis['risk_assessment']['risk_factors'])}

Mitigation Strategies:
{chr(10).join('  • ' + strategy for strategy in analysis['risk_assessment']['mitigation_strategies'])}

COMMUNITY IMPACT
----------------
Adoption Likelihood: {analysis['community_impact']['adoption_likelihood']*100:.1f}%
User Benefit Score: {analysis['community_impact']['user_benefit_score']*100:.1f}/100
Affected Users: {analysis['community_impact']['affected_user_percentage']*100:.1f}%

FINANCIAL ANALYSIS
------------------
Implementation Cost: ${analysis['financial_impact']['implementation_cost_usd']:.2f}
Annual Maintenance: ${analysis['financial_impact']['maintenance_cost_annual_usd']:.2f}
Cost/Benefit Ratio: {analysis['financial_impact']['cost_benefit_ratio']:.2f}x
Break-even Period: {analysis['financial_impact']['break_even_period_months']} months

RECOMMENDATIONS
---------------
{chr(10).join('  • ' + rec for rec in analysis['recommendations'])}

{'='*80}
"""
        return report


class AIGovernance:
    """Simplified AI governance facade used by the pytest suite."""

    def __init__(self) -> None:
        self.proposals: Dict[str, Dict] = {}
        self.parameters: Dict[str, float] = {"quorum": 0.5, "timelock_days": 1.0}
        self.voter_type_weights = {
            VoterType.NODE_OPERATOR: 1.25,
            VoterType.MINER: 1.0,
            VoterType.AI_CONTRIBUTOR: 1.1,
            VoterType.HYBRID: 1.3,
        }
        # Add AI impact analyzer
        self.impact_analyzer = ProposalImpactAnalyzer()
        self.fraud_detector = GovernanceFraudDetector()
        self.workload_manager = AIWorkloadDistribution()
        self.execution_history: List[Dict[str, Any]] = []

    def _generate_proposal_id(self, title: str, proposer: str) -> str:
        seed = f"{title}-{proposer}-{time.time()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def create_proposal(
        self,
        proposer_address: str,
        title: str,
        description: str,
        proposal_type: str = "ai_improvement",
        estimated_minutes: float = 0.0,
    ) -> str:
        """Create a proposal record."""
        proposal_id = self._generate_proposal_id(title, proposer_address)
        timelock_seconds = self.parameters.get("timelock_days", 1.0) * 86400
        proposal = {
            "proposal_id": proposal_id,
            "title": title,
            "description": description,
            "proposer": proposer_address,
            "proposal_type": proposal_type,
            "status": "active",
            "votes": {},
            "timelock": time.time() + timelock_seconds,
            "execution_time": None,
            "last_tally": None,
            "fraud_alerts": [],
            "estimated_minutes": float(estimated_minutes or 0.0),
            "execution_history": [],
        }
        self.proposals[proposal_id] = proposal
        return proposal_id

    def register_ai_contribution(
        self,
        contributor_address: str,
        ai_model: str,
        minutes_contributed: float,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Register contributor AI minutes for future workload distribution.

        Returns a snapshot of the contributor state after the update.
        """
        ts = timestamp if timestamp is not None else time.time()
        self.workload_manager.add_contributor(contributor_address, ai_model, minutes_contributed, ts)
        snapshot = dict(self.workload_manager.contributor_pool.get(contributor_address, {}))
        return snapshot

    def cast_vote(
        self,
        proposal_id: str,
        voter_address: str,
        vote: str,
        voting_power: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record votes and guard against double voting."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False

        if voter_address in proposal["votes"]:
            return False

        proposal["votes"][voter_address] = {
            "vote": vote,
            "voting_power": voting_power,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        alerts = self.fraud_detector.record_vote(
            proposal_id, voter_address, voting_power, metadata
        )
        if alerts:
            proposal["fraud_alerts"].extend(alerts)
        return True

    def calculate_quadratic_power(self, amount: float) -> float:
        return math.sqrt(max(amount, 0.0))

    def calculate_voting_power(self, amount: float, days_ago: int = 0) -> float:
        base = self.calculate_quadratic_power(amount)
        decay = max(0.1, 1 - (days_ago / 365) * 0.1)
        return base * decay

    def get_voter_type_weight(self, voter_type: VoterType) -> float:
        return self.voter_type_weights.get(voter_type, 1.0)

    def tally_votes(self, proposal_id: str) -> Dict:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"passed": False}

        yes_power = sum(v["voting_power"] for v in proposal["votes"].values() if v["vote"] == "yes")
        no_power = sum(v["voting_power"] for v in proposal["votes"].values() if v["vote"] == "no")
        passed = yes_power > no_power and yes_power > 0

        result = {
            "passed": passed,
            "yes_power": yes_power,
            "no_power": no_power,
            "votes": len(proposal["votes"]),
        }

        proposal["status"] = "passed" if passed else "failed"
        proposal["last_tally"] = result
        return result

    def execute_proposal(self, proposal_id: str) -> Optional[Dict]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        result = self.tally_votes(proposal_id)
        now = time.time()
        execution_record: Dict[str, Any] = {
            "proposal_id": proposal_id,
            "attempted_at": now,
            "yes_power": result.get("yes_power"),
            "no_power": result.get("no_power"),
            "voter_count": result.get("votes"),
            "timelock_ready": now >= proposal["timelock"],
        }

        if not result["passed"]:
            execution_record["result"] = "failed_vote"
            proposal["execution_history"].append(execution_record)
            self.execution_history.append(dict(execution_record))
            return {"status": "failed", "executed": False}

        configured_timelock_seconds = max(
            0.0, float(self.parameters.get("timelock_days", 1.0)) * 86400
        )
        effective_ready_at = proposal["timelock"]
        if configured_timelock_seconds == 0:
            effective_ready_at = now
            proposal["timelock"] = now

        if now < effective_ready_at:
            execution_record["result"] = "timelock_pending"
            execution_record["ready_at"] = effective_ready_at
            proposal["execution_history"].append(execution_record)
            self.execution_history.append(dict(execution_record))
            proposal["status"] = "timelock_pending"
            return {"status": "timelock_pending", "ready_at": effective_ready_at}

        proposal["execution_time"] = now
        proposal["status"] = "executed"
        workload_plan: Optional[Dict[str, Any]] = None
        if (
            proposal.get("proposal_type") == "ai_improvement"
            and proposal.get("estimated_minutes", 0) > 0
        ):
            workload_plan = self.workload_manager.execute_distributed_task(
                proposal["title"], proposal.get("estimated_minutes", 0)
            )

        execution_record["result"] = "executed"
        execution_record["workload_plan"] = workload_plan
        proposal["execution_history"].append(execution_record)
        self.execution_history.append(dict(execution_record))
        return {"status": "executed", "executed": True, "workload_plan": workload_plan}

    def get_parameters(self) -> Dict[str, float]:
        return dict(self.parameters)

    def update_parameter(self, key: str, value: float) -> bool:
        self.parameters[key] = value
        return True

    def get_fraud_alerts(self, proposal_id: str) -> List[Dict[str, Any]]:
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return []
        alerts = self.fraud_detector.get_alerts(proposal_id)
        proposal["fraud_alerts"] = alerts
        return alerts

    def get_sybil_report(self, proposal_id: str) -> Dict[str, Any]:
        """Return normalized sybil risk report for a proposal."""
        if proposal_id not in self.proposals:
            return {"proposal_id": proposal_id, "risk_score": 0.0, "alert_count": 0, "alerts": []}
        return self.fraud_detector.evaluate_sybil_risk(proposal_id)

    def record_execution_feedback(
        self, proposal_id: str, feedback_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Attach post-execution telemetry and update contributor quality metrics.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "proposal_not_found"}
        if not feedback_entries:
            return {"success": False, "error": "no_feedback"}

        updates = self.workload_manager.apply_execution_feedback(feedback_entries)
        timestamp = time.time()
        feedback_record = {
            "proposal_id": proposal_id,
            "recorded_at": timestamp,
            "quality_updates": updates,
        }
        if proposal["execution_history"]:
            proposal["execution_history"][-1].setdefault("quality_updates", {}).update(updates)
        else:
            proposal["execution_history"].append({"result": "feedback", **feedback_record})
        self.execution_history.append({**feedback_record, "result": "feedback"})
        return {"success": True, "quality_updates": updates}

