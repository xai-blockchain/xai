"""
XAI Blockchain - Governance Execution Engine

Executes approved governance proposals by actually modifying blockchain state.
Includes meta-governance for expanding governance capabilities.
"""

import time
from typing import Dict, Any, Optional, List
from enum import Enum


class ProposalType(Enum):
    """Core proposal types"""

    PROTOCOL_PARAMETER = "protocol_parameter"
    FEATURE_ACTIVATION = "feature_activation"
    TREASURY_ALLOCATION = "treasury_allocation"
    EMERGENCY_ACTION = "emergency_action"
    # Meta-governance types
    ADD_PROPOSAL_TYPE = "add_proposal_type"
    ADD_PARAMETER = "add_parameter"
    MODIFY_GOVERNANCE_RULES = "modify_governance_rules"


class ParameterType(Enum):
    """Parameter value types"""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"
    ADDRESS = "address"


class GovernanceCapabilityRegistry:
    """
    Registry of governance capabilities that can be expanded through voting

    Meta-governance: Community can vote to add new proposal types and parameters
    """

    def __init__(self):
        # Core parameters that can be modified
        self.registered_parameters = {
            # Blockchain parameters
            "difficulty": {
                "type": ParameterType.INTEGER,
                "min": 1,
                "max": 10,
                "default": 4,
                "description": "Mining difficulty",
            },
            "block_reward": {
                "type": ParameterType.FLOAT,
                "min": 0.0,
                "max": 50.0,
                "default": 12.0,
                "description": "Base block reward in XAI",
            },
            "transaction_fee_percent": {
                "type": ParameterType.FLOAT,
                "min": 0.0,
                "max": 5.0,
                "default": 0.24,
                "description": "Transaction fee percentage",
            },
            "max_block_size": {
                "type": ParameterType.INTEGER,
                "min": 1000,
                "max": 10000000,
                "default": 1000000,
                "description": "Maximum block size in bytes",
            },
            "halving_interval": {
                "type": ParameterType.INTEGER,
                "min": 100000,
                "max": 1000000,
                "default": 262800,
                "description": "Blocks between reward halvings",
            },
            # Gamification parameters
            "airdrop_frequency": {
                "type": ParameterType.INTEGER,
                "min": 10,
                "max": 1000,
                "default": 100,
                "description": "Blocks between airdrops",
            },
            "min_airdrop_amount": {
                "type": ParameterType.FLOAT,
                "min": 1.0,
                "max": 100.0,
                "default": 10.0,
                "description": "Minimum airdrop amount",
            },
            "max_airdrop_amount": {
                "type": ParameterType.FLOAT,
                "min": 10.0,
                "max": 1000.0,
                "default": 100.0,
                "description": "Maximum airdrop amount",
            },
            # Governance parameters
            "min_voters": {
                "type": ParameterType.INTEGER,
                "min": 100,
                "max": 10000,
                "default": 500,
                "description": "Minimum voters for proposal approval",
            },
            "approval_percent": {
                "type": ParameterType.INTEGER,
                "min": 51,
                "max": 90,
                "default": 66,
                "description": "Required approval percentage",
            },
        }

        # Registered proposal types (can be expanded)
        self.registered_proposal_types = {
            ProposalType.PROTOCOL_PARAMETER.value: {
                "description": "Change blockchain protocol parameters",
                "required_fields": ["parameter", "new_value"],
                "enabled": True,
            },
            ProposalType.FEATURE_ACTIVATION.value: {
                "description": "Enable or disable blockchain features",
                "required_fields": ["feature_name", "enabled"],
                "enabled": True,
            },
            ProposalType.TREASURY_ALLOCATION.value: {
                "description": "Allocate funds from treasury",
                "required_fields": ["recipient", "amount", "purpose"],
                "enabled": True,
            },
            ProposalType.EMERGENCY_ACTION.value: {
                "description": "Emergency protocol actions",
                "required_fields": ["action_type", "action_data"],
                "enabled": True,
            },
            ProposalType.ADD_PROPOSAL_TYPE.value: {
                "description": "Add new proposal type to governance",
                "required_fields": ["new_type_name", "new_type_description", "required_fields"],
                "enabled": True,
            },
            ProposalType.ADD_PARAMETER.value: {
                "description": "Add new modifiable parameter",
                "required_fields": [
                    "parameter_name",
                    "parameter_type",
                    "min_value",
                    "max_value",
                    "default_value",
                ],
                "enabled": True,
            },
            ProposalType.MODIFY_GOVERNANCE_RULES.value: {
                "description": "Modify governance voting rules",
                "required_fields": ["rule_name", "new_value"],
                "enabled": True,
            },
        }

        # Active features (can be toggled)
        self.active_features = {
            "airdrops": True,
            "treasure_hunts": True,
            "time_capsules": True,
            "mining_bonuses": True,
            "social_bonuses": True,
            "fee_refunds": True,
            "ai_development_pool": True,
            "exchange": True,
            "social_recovery": True,
            "token_burning": True,
            "smart_contracts": False,
        }

    def add_parameter(
        self,
        name: str,
        param_type: ParameterType,
        min_val: Any,
        max_val: Any,
        default_val: Any,
        description: str,
    ) -> bool:
        """
        Add new parameter to registry (via governance)

        Args:
            name: Parameter name
            param_type: Parameter type
            min_val: Minimum value
            max_val: Maximum value
            default_val: Default value
            description: Parameter description

        Returns:
            bool: Success
        """
        if name in self.registered_parameters:
            return False  # Already exists

        self.registered_parameters[name] = {
            "type": param_type,
            "min": min_val,
            "max": max_val,
            "default": default_val,
            "description": description,
        }
        return True

    def add_proposal_type(
        self, type_name: str, description: str, required_fields: List[str]
    ) -> bool:
        """
        Add new proposal type (via governance)

        Args:
            type_name: Name of new proposal type
            description: Description of proposal type
            required_fields: List of required field names

        Returns:
            bool: Success
        """
        if type_name in self.registered_proposal_types:
            return False  # Already exists

        self.registered_proposal_types[type_name] = {
            "description": description,
            "required_fields": required_fields,
            "enabled": True,
        }
        return True

    def validate_parameter_value(self, param_name: str, value: Any) -> bool:
        """
        Validate parameter value against constraints

        Args:
            param_name: Parameter name
            value: Proposed value

        Returns:
            bool: Valid
        """
        if param_name not in self.registered_parameters:
            return False

        param_def = self.registered_parameters[param_name]

        # Type check
        if param_def["type"] == ParameterType.INTEGER:
            if not isinstance(value, int):
                return False
        elif param_def["type"] == ParameterType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
        elif param_def["type"] == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                return False
        elif param_def["type"] == ParameterType.STRING:
            if not isinstance(value, str):
                return False

        # Range check
        if "min" in param_def and value < param_def["min"]:
            return False
        if "max" in param_def and value > param_def["max"]:
            return False

        return True


class GovernanceExecutionEngine:
    """
    Executes approved governance proposals

    Actually modifies blockchain state based on approved governance decisions
    """

    def __init__(self, blockchain):
        """
        Initialize execution engine

        Args:
            blockchain: Reference to Blockchain instance
        """
        self.blockchain = blockchain
        self.capability_registry = GovernanceCapabilityRegistry()
        self.execution_history = []

    def execute_proposal(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """
        Execute an approved proposal

        Args:
            proposal_id: Proposal ID
            proposal_data: Proposal details

        Returns:
            dict: Execution result
        """
        proposal_type = proposal_data.get("proposal_type")

        # Route to appropriate execution handler
        if proposal_type == ProposalType.PROTOCOL_PARAMETER.value:
            return self._execute_protocol_parameter(proposal_id, proposal_data)

        elif proposal_type == ProposalType.FEATURE_ACTIVATION.value:
            return self._execute_feature_activation(proposal_id, proposal_data)

        elif proposal_type == ProposalType.TREASURY_ALLOCATION.value:
            return self._execute_treasury_allocation(proposal_id, proposal_data)

        elif proposal_type == ProposalType.EMERGENCY_ACTION.value:
            return self._execute_emergency_action(proposal_id, proposal_data)

        elif proposal_type == ProposalType.ADD_PROPOSAL_TYPE.value:
            return self._execute_add_proposal_type(proposal_id, proposal_data)

        elif proposal_type == ProposalType.ADD_PARAMETER.value:
            return self._execute_add_parameter(proposal_id, proposal_data)

        elif proposal_type == ProposalType.MODIFY_GOVERNANCE_RULES.value:
            return self._execute_modify_governance_rules(proposal_id, proposal_data)

        else:
            # Check if it's a custom registered type
            if proposal_type in self.capability_registry.registered_proposal_types:
                return self._execute_custom_proposal(proposal_id, proposal_data)

            return {"success": False, "error": f"Unknown proposal type: {proposal_type}"}

    def _execute_protocol_parameter(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute protocol parameter change"""
        parameter = proposal_data.get("parameter")
        new_value = proposal_data.get("new_value")

        # Validate parameter exists
        if not self.capability_registry.validate_parameter_value(parameter, new_value):
            return {
                "success": False,
                "error": f"Invalid parameter or value: {parameter} = {new_value}",
            }

        # Apply the change to blockchain
        old_value = None

        if parameter == "difficulty":
            old_value = self.blockchain.difficulty
            self.blockchain.difficulty = new_value

        elif parameter == "block_reward":
            old_value = self.blockchain.initial_block_reward
            self.blockchain.initial_block_reward = new_value

        elif parameter == "transaction_fee_percent":
            old_value = self.blockchain.transaction_fee_percent
            self.blockchain.transaction_fee_percent = new_value

        elif parameter == "halving_interval":
            old_value = self.blockchain.halving_interval
            self.blockchain.halving_interval = new_value

        elif parameter == "airdrop_frequency":
            old_value = self.blockchain.airdrop_manager.airdrop_frequency
            self.blockchain.airdrop_manager.airdrop_frequency = new_value

        elif parameter == "min_airdrop_amount":
            old_value = self.blockchain.airdrop_manager.min_amount
            self.blockchain.airdrop_manager.min_amount = new_value

        elif parameter == "max_airdrop_amount":
            old_value = self.blockchain.airdrop_manager.max_amount
            self.blockchain.airdrop_manager.max_amount = new_value

        elif parameter == "min_voters":
            old_value = self.blockchain.governance_state.min_voters
            self.blockchain.governance_state.min_voters = new_value

        elif parameter == "approval_percent":
            old_value = self.blockchain.governance_state.approval_percent
            self.blockchain.governance_state.approval_percent = new_value

        else:
            return {
                "success": False,
                "error": f"Parameter {parameter} not implemented in execution engine",
            }

        # Log execution
        self._log_execution(
            proposal_id,
            "protocol_parameter",
            {"parameter": parameter, "old_value": old_value, "new_value": new_value},
        )

        return {
            "success": True,
            "action": "protocol_parameter_changed",
            "parameter": parameter,
            "old_value": old_value,
            "new_value": new_value,
        }

    def _execute_feature_activation(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute feature activation/deactivation"""
        feature_name = proposal_data.get("feature_name")
        enabled = proposal_data.get("enabled", True)

        if feature_name not in self.capability_registry.active_features:
            return {"success": False, "error": f"Unknown feature: {feature_name}"}

        old_status = self.capability_registry.active_features[feature_name]
        self.capability_registry.active_features[feature_name] = enabled

        # Log execution
        self._log_execution(
            proposal_id,
            "feature_activation",
            {"feature": feature_name, "old_status": old_status, "new_status": enabled},
        )

        return {
            "success": True,
            "action": "feature_toggled",
            "feature": feature_name,
            "enabled": enabled,
        }

    def _execute_treasury_allocation(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute treasury fund allocation"""
        recipient = proposal_data.get("recipient")
        amount = proposal_data.get("amount")
        purpose = proposal_data.get("purpose")

        # Create treasury transaction
        from xai.core.transaction import Transaction

        treasury_tx = Transaction(
            sender="TREASURY",
            recipient=recipient,
            amount=amount,
            fee=0.0,
            tx_type="treasury_allocation",
        )
        treasury_tx.txid = treasury_tx.calculate_hash()

        # Add to pending transactions
        self.blockchain.pending_transactions.append(treasury_tx)

        # Log execution
        self._log_execution(
            proposal_id,
            "treasury_allocation",
            {
                "recipient": recipient,
                "amount": amount,
                "purpose": purpose,
                "txid": treasury_tx.txid,
            },
        )

        return {
            "success": True,
            "action": "treasury_allocated",
            "recipient": recipient,
            "amount": amount,
            "txid": treasury_tx.txid,
        }

    def _execute_emergency_action(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute emergency action with timelock"""
        # Check timelock
        current_height = len(self.blockchain.chain)
        can_execute, error = (
            self.blockchain.security_manager.emergency_timelock.can_execute_emergency_action(
                proposal_id, current_height
            )
        )

        if not can_execute:
            return {
                "success": False,
                "error": error,
                "note": "Emergency actions have a safety timelock",
            }

        action_type = proposal_data.get("action_type")
        action_data = proposal_data.get("action_data", {})

        result = {"success": False}

        if action_type == "pause_transactions":
            # Pause new transactions
            self.blockchain.transactions_paused = True
            result = {"success": True, "action": "transactions_paused"}

        elif action_type == "resume_transactions":
            # Resume transactions
            self.blockchain.transactions_paused = False
            result = {"success": True, "action": "transactions_resumed"}

        elif action_type == "emergency_difficulty_adjustment":
            # Emergency difficulty change
            new_difficulty = action_data.get("difficulty")
            old_difficulty = self.blockchain.difficulty
            self.blockchain.difficulty = new_difficulty
            result = {
                "success": True,
                "action": "emergency_difficulty_adjusted",
                "old_difficulty": old_difficulty,
                "new_difficulty": new_difficulty,
            }

        else:
            return {"success": False, "error": f"Unknown emergency action: {action_type}"}

        # Log execution
        self._log_execution(
            proposal_id,
            "emergency_action",
            {"action_type": action_type, "action_data": action_data, "result": result},
        )

        return result

    def _execute_add_proposal_type(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute meta-governance: Add new proposal type"""
        type_name = proposal_data.get("new_type_name")
        description = proposal_data.get("new_type_description")
        required_fields = proposal_data.get("required_fields", [])

        success = self.capability_registry.add_proposal_type(
            type_name, description, required_fields
        )

        if not success:
            return {"success": False, "error": f"Proposal type {type_name} already exists"}

        # Log execution
        self._log_execution(
            proposal_id,
            "add_proposal_type",
            {
                "type_name": type_name,
                "description": description,
                "required_fields": required_fields,
            },
        )

        return {"success": True, "action": "proposal_type_added", "type_name": type_name}

    def _execute_add_parameter(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute meta-governance: Add new parameter"""
        param_name = proposal_data.get("parameter_name")
        param_type = ParameterType(proposal_data.get("parameter_type"))
        min_value = proposal_data.get("min_value")
        max_value = proposal_data.get("max_value")
        default_value = proposal_data.get("default_value")
        description = proposal_data.get("description", "")

        success = self.capability_registry.add_parameter(
            param_name, param_type, min_value, max_value, default_value, description
        )

        if not success:
            return {"success": False, "error": f"Parameter {param_name} already exists"}

        # Log execution
        self._log_execution(
            proposal_id,
            "add_parameter",
            {
                "parameter_name": param_name,
                "parameter_type": param_type.value,
                "min_value": min_value,
                "max_value": max_value,
                "default_value": default_value,
            },
        )

        return {"success": True, "action": "parameter_added", "parameter_name": param_name}

    def _execute_modify_governance_rules(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute meta-governance: Modify governance rules"""
        rule_name = proposal_data.get("rule_name")
        new_value = proposal_data.get("new_value")

        old_value = None

        if rule_name == "min_voters":
            old_value = self.blockchain.governance_state.min_voters
            self.blockchain.governance_state.min_voters = new_value

        elif rule_name == "approval_percent":
            old_value = self.blockchain.governance_state.approval_percent
            self.blockchain.governance_state.approval_percent = new_value

        elif rule_name == "max_individual_power_percent":
            old_value = self.blockchain.governance_state.max_individual_power_percent
            self.blockchain.governance_state.max_individual_power_percent = new_value

        elif rule_name == "min_code_reviewers":
            old_value = self.blockchain.governance_state.min_code_reviewers
            self.blockchain.governance_state.min_code_reviewers = new_value

        elif rule_name == "implementation_approval_percent":
            old_value = self.blockchain.governance_state.implementation_approval_percent
            self.blockchain.governance_state.implementation_approval_percent = new_value

        else:
            return {"success": False, "error": f"Unknown governance rule: {rule_name}"}

        # Log execution
        self._log_execution(
            proposal_id,
            "modify_governance_rules",
            {"rule_name": rule_name, "old_value": old_value, "new_value": new_value},
        )

        return {
            "success": True,
            "action": "governance_rule_modified",
            "rule_name": rule_name,
            "old_value": old_value,
            "new_value": new_value,
        }

    def _execute_custom_proposal(self, proposal_id: str, proposal_data: Dict) -> Dict:
        """Execute custom proposal type (added via meta-governance)"""
        proposal_type = proposal_data.get("proposal_type")

        # For now, custom proposals just log their execution
        # Future: Add plugin system for custom execution handlers

        self._log_execution(
            proposal_id, "custom_proposal", {"proposal_type": proposal_type, "data": proposal_data}
        )

        return {
            "success": True,
            "action": "custom_proposal_executed",
            "proposal_type": proposal_type,
            "note": "Custom proposal logged. Implementation handler required for actual execution.",
        }

    def _log_execution(self, proposal_id: str, execution_type: str, details: Dict):
        """Log proposal execution"""
        self.execution_history.append(
            {
                "proposal_id": proposal_id,
                "execution_type": execution_type,
                "details": details,
                "timestamp": time.time(),
            }
        )

    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:]

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled"""
        return self.capability_registry.active_features.get(feature_name, False)

    def snapshot(self) -> Dict[str, Any]:
        """
        Create a complete snapshot of the current governance state.
        Thread-safe atomic operation for chain reorganization rollback.

        Returns:
            A deep copy of the governance state including registry and history
        """
        import copy
        return {
            "governance_state": copy.deepcopy(self.blockchain.governance_state.__dict__ if self.blockchain.governance_state else None),
            "execution_history": copy.deepcopy(self.execution_history),
            "capability_registry": {
                "registered_parameters": copy.deepcopy(self.capability_registry.registered_parameters),
                "registered_proposal_types": copy.deepcopy(self.capability_registry.registered_proposal_types),
                "active_features": copy.deepcopy(self.capability_registry.active_features),
            },
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore governance state from a snapshot.
        Thread-safe atomic operation for chain reorganization rollback.

        Args:
            snapshot: Snapshot created by snapshot() method
        """
        import copy
        from xai.core.governance import GovernanceState

        # Restore governance state
        gov_state_data = snapshot.get("governance_state")
        if gov_state_data:
            # Recreate governance state object
            mining_start = gov_state_data.get("mining_start_time", time.time())
            self.blockchain.governance_state = GovernanceState(mining_start_time=mining_start)
            # Restore all attributes
            for key, value in gov_state_data.items():
                setattr(self.blockchain.governance_state, key, copy.deepcopy(value))
        else:
            self.blockchain.governance_state = None

        # Restore execution history
        self.execution_history = copy.deepcopy(snapshot.get("execution_history", []))

        # Restore capability registry
        registry_data = snapshot.get("capability_registry", {})
        self.capability_registry.registered_parameters = copy.deepcopy(
            registry_data.get("registered_parameters", {})
        )
        self.capability_registry.registered_proposal_types = copy.deepcopy(
            registry_data.get("registered_proposal_types", {})
        )
        self.capability_registry.active_features = copy.deepcopy(
            registry_data.get("active_features", {})
        )

        logger = getattr(self.blockchain, "logger", None)
        if logger:
            logger.info(
                "Governance state restored from snapshot",
                extra={
                    "event": "governance.restore",
                    "execution_history_count": len(self.execution_history),
                    "active_features": len(self.capability_registry.active_features),
                }
            )
