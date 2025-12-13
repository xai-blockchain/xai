from __future__ import annotations

import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Dict, Optional, Tuple, Any, Type

from flask import request

from xai.core.input_validation_schemas import (
    ContractDeployInput,
    ContractCallInput,
    ContractFeatureToggleInput,
)
from xai.core.request_validator_middleware import validate_request
from xai.core.config import Config
from xai.core.governance_execution import ProposalType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes, InputSanitizer


def register_contract_routes(routes: "NodeAPIRoutes", sanitizer: Type["InputSanitizer"]) -> None:
    """Expose the smart-contract operations when the VM is enabled."""
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/contracts/deploy", methods=["POST"])
    @validate_request(routes.request_validator, ContractDeployInput)
    def deploy_contract() -> Tuple[Dict[str, Any], int]:
        """Deploy a smart contract to the blockchain (admin only).

        Creates and broadcasts a contract deployment transaction. The contract
        address is deterministically derived from sender address and nonce.

        This endpoint requires API authentication and VM features enabled.

        Request Body (ContractDeployInput):
            {
                "sender": "deployer address",
                "bytecode": "hex-encoded contract bytecode",
                "value": float (initial contract balance),
                "fee": float (transaction fee),
                "gas_limit": int,
                "public_key": "sender public key",
                "signature": "transaction signature",
                "nonce": int (optional),
                "metadata": {
                    "abi": [] (optional contract ABI),
                    ...
                }
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains txid and derived contract_address
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If VM feature is disabled (503).
            ValidationError: If deployment data is invalid (400).
            ValueError: If signature is invalid or ABI malformed (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        if not blockchain.smart_contract_manager:
            return routes._error_response(
                "Smart-contract VM feature is disabled",
                status=503,
                code="vm_feature_disabled",
            )
        model: Optional[ContractDeployInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response(
                "Invalid contract deployment payload", status=400, code="invalid_payload"
            )

        nonce = model.nonce if model.nonce is not None else blockchain.nonce_tracker.get_next_nonce(
            model.sender
        )
        contract_address = blockchain.derive_contract_address(model.sender, nonce)

        metadata = dict(model.metadata or {})
        metadata["data"] = bytes.fromhex(model.bytecode)
        metadata["gas_limit"] = model.gas_limit
        metadata["contract_address"] = contract_address
        if "abi" in metadata:
            try:
                metadata["abi"] = blockchain.normalize_contract_abi(metadata.get("abi"))
            except ValueError as exc:
                logger.warning(
                    "ValueError in deploy_contract",
                    error_type="ValueError",
                    error=str(exc),
                    function="deploy_contract",
                )
                return routes._error_response(
                    "Invalid contract ABI",
                    status=400,
                    code="invalid_contract_abi",
                    context={"error": str(exc)},
                )

        from xai.core.blockchain import Transaction

        tx = Transaction(
            sender=model.sender,
            recipient=contract_address,
            amount=model.value,
            fee=model.fee,
            public_key=model.public_key,
            nonce=nonce,
            tx_type="contract_deploy",
            outputs=[{"address": contract_address, "amount": model.value}],
        )
        tx.metadata = metadata
        tx.signature = model.signature

        # Verify signature - now raises exceptions
        try:
            tx.verify_signature()
        except Exception as e:
            from xai.core.transaction import (
                SignatureVerificationError,
                MissingSignatureError,
                InvalidSignatureError,
                SignatureCryptoError
            )

            if isinstance(e, MissingSignatureError):
                return routes._error_response(
                    "Missing signature or public key",
                    status=400,
                    code="missing_signature",
                    context={"sender": model.sender, "error": str(e)}
                )
            elif isinstance(e, InvalidSignatureError):
                return routes._error_response(
                    "Invalid signature",
                    status=400,
                    code="invalid_signature",
                    context={"sender": model.sender, "error": str(e)}
                )
            elif isinstance(e, SignatureCryptoError):
                return routes._error_response(
                    "Signature verification error",
                    status=500,
                    code="crypto_error",
                    context={"sender": model.sender, "error": str(e)}
                )
            else:
                return routes._error_response(
                    "Unexpected signature verification error",
                    status=500,
                    code="verification_error",
                    context={"sender": model.sender, "error": str(e)}
                )

        if blockchain.add_transaction(tx):
            routes.node.broadcast_transaction(tx)
            return routes._success_response(
                {
                    "txid": tx.txid,
                    "contract_address": contract_address,
                    "message": "Contract deployment queued",
                }
            )

        return routes._error_response(
            "Contract deployment rejected",
            status=400,
            code="contract_rejected",
            context={"contract_address": contract_address, "sender": model.sender},
        )

    @app.route("/contracts/call", methods=["POST"])
    @validate_request(routes.request_validator, ContractCallInput)
    def call_contract() -> Tuple[Dict[str, Any], int]:
        """Call a deployed smart contract function (admin only).

        Executes a contract function by creating a contract call transaction.
        Can include payment (value) to payable contract functions.

        This endpoint requires API authentication and VM features enabled.

        Request Body (ContractCallInput):
            {
                "sender": "caller address",
                "contract_address": "target contract address",
                "value": float (amount to send),
                "fee": float (transaction fee),
                "gas_limit": int,
                "payload": {} (JSON function call data) OR "data": "hex",
                "public_key": "sender public key",
                "signature": "transaction signature",
                "nonce": int (optional),
                "metadata": {} (optional)
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains txid and confirmation message
                - http_status_code: 200 on success, 400/401/503 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ServiceUnavailable: If VM feature is disabled (503).
            ValidationError: If call data is invalid (400).
            ValueError: If signature invalid or payload malformed (400).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        if not blockchain.smart_contract_manager:
            return routes._error_response(
                "Smart-contract VM feature is disabled",
                status=503,
                code="vm_feature_disabled",
            )
        model: Optional[ContractCallInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response(
                "Invalid contract call payload", status=400, code="invalid_payload"
            )

        nonce = model.nonce if model.nonce is not None else blockchain.nonce_tracker.get_next_nonce(
            model.sender
        )
        try:
            data_bytes = (
                json.dumps(model.payload).encode("utf-8")
                if model.payload is not None
                else bytes.fromhex(model.data or "")
            )
        except ValueError as exc:
            logger.warning(
                "ValueError in call_contract",
                error_type="ValueError",
                error=str(exc),
                function="call_contract",
            )
            return routes._error_response(
                "Contract payload serialization failed",
                status=400,
                code="contract_payload_error",
                context={"error": str(exc)},
            )

        metadata = dict(model.metadata or {})
        metadata["data"] = data_bytes
        metadata["gas_limit"] = model.gas_limit

        try:
            from xai.core.blockchain import Transaction

            tx = Transaction(
                sender=model.sender,
                recipient=model.contract_address,
                amount=model.value,
                fee=model.fee,
                public_key=model.public_key,
                nonce=nonce,
                tx_type="contract_call",
                outputs=[{"address": model.contract_address, "amount": model.value}],
            )
            tx.metadata = metadata
            tx.signature = model.signature
        except (ValueError, TypeError, AttributeError) as exc:
            return routes._error_response(
                "Unable to build contract call",
                status=400,
                code="contract_build_error",
                context={"error": str(exc)},
            )

        # Verify signature - now raises exceptions
        try:
            tx.verify_signature()
        except Exception as e:
            from xai.core.transaction import (
                SignatureVerificationError,
                MissingSignatureError,
                InvalidSignatureError,
                SignatureCryptoError
            )

            if isinstance(e, MissingSignatureError):
                return routes._error_response(
                    "Missing signature or public key",
                    status=400,
                    code="missing_signature",
                    context={"sender": model.sender, "error": str(e)}
                )
            elif isinstance(e, InvalidSignatureError):
                return routes._error_response(
                    "Invalid signature",
                    status=400,
                    code="invalid_signature",
                    context={"sender": model.sender, "error": str(e)}
                )
            elif isinstance(e, SignatureCryptoError):
                return routes._error_response(
                    "Signature verification error",
                    status=500,
                    code="crypto_error",
                    context={"sender": model.sender, "error": str(e)}
                )
            else:
                return routes._error_response(
                    "Unexpected signature verification error",
                    status=500,
                    code="verification_error",
                    context={"sender": model.sender, "error": str(e)}
                )

        if blockchain.add_transaction(tx):
            routes.node.broadcast_transaction(tx)
            return routes._success_response({"txid": tx.txid, "message": "Contract call queued"})

        return routes._error_response(
            "Contract call rejected",
            status=400,
            code="contract_rejected",
            context={"contract_address": model.contract_address, "sender": model.sender},
        )

    @app.route("/contracts/<address>/state", methods=["GET"])
    def contract_state(address: str) -> Tuple[Dict[str, Any], int]:
        """Get current state storage of a deployed contract.

        Returns the contract's state variables and storage data.

        Path Parameters:
            address (str): The contract address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains contract_address and state object
                - http_status_code: 200 on success, 400/404/503 on error

        Raises:
            ValidationError: If address format is invalid (400).
            NotFound: If contract doesn't exist (404).
            ServiceUnavailable: If VM feature is disabled (503).
        """
        if not blockchain.smart_contract_manager:
            return routes._error_response(
                "Smart-contract VM feature is disabled",
                status=503,
                code="vm_feature_disabled",
            )
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
            logger.warning(
                "ValueError in contract_state",
                error_type="ValueError",
                error=str(exc),
                function="contract_state",
            )
            return routes._error_response(
                str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
            )
        state = blockchain.get_contract_state(normalized)
        if not state:
            return routes._error_response(
                "Contract not found", status=404, code="contract_not_found"
            )
        return routes._success_response({"contract_address": normalized, "state": state})

    @app.route("/contracts/<address>/abi", methods=["GET"])
    def contract_abi(address: str) -> Tuple[Dict[str, Any], int]:
        """Get contract ABI (Application Binary Interface).

        Returns the contract's ABI defining its functions, events, and data structures.

        Path Parameters:
            address (str): The contract address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains contract_address and ABI data
                - http_status_code: 200 on success, 400/404 on error

        Raises:
            ValidationError: If address format is invalid (400).
            NotFound: If contract ABI not found (404).
        """
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
            logger.warning(
                "ValueError in contract_abi",
                error_type="ValueError",
                error=str(exc),
                function="contract_abi",
            )
            return routes._error_response(
                str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
            )

        abi_payload = blockchain.get_contract_abi(normalized)
        if not abi_payload:
            return routes._error_response(
                "Contract ABI not found", status=404, code="contract_abi_missing"
            )
        response = {"contract_address": normalized, **abi_payload}
        return routes._success_response(response)

    @app.route("/contracts/<address>/interfaces", methods=["GET"])
    def contract_interfaces(address: str) -> Tuple[Dict[str, Any], int]:
        """Detect supported ERC interfaces for a contract.

        Probes contract for ERC-165 interface support and caches results.
        Returns which standard interfaces (ERC-20, ERC-721, etc.) the contract implements.

        Path Parameters:
            address (str): The contract address

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains contract_address, interfaces list, and metadata
                - http_status_code: 200 on success, 400/404/503 on error

        Response includes:
            - interfaces: List of supported ERC interface IDs
            - metadata.cached: Whether result was from cache
            - metadata.source: Detection method ("erc165_probe" or cache)
            - metadata.detected_at: Timestamp of detection

        Raises:
            ValidationError: If address format is invalid (400).
            NotFound: If contract doesn't exist (404).
            ServiceUnavailable: If VM feature is disabled (503).
        """
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
            logger.warning(
                "ValueError in contract_interfaces",
                error_type="ValueError",
                error=str(exc),
                function="contract_interfaces",
            )
            return routes._error_response(
                str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
            )

        if normalized.upper() not in blockchain.contracts:
            return routes._error_response(
                "Contract not found", status=404, code="contract_not_found"
            )

        cached_metadata = blockchain.get_contract_interface_metadata(normalized)
        served_from_cache = bool(cached_metadata)
        interfaces = cached_metadata["supports"] if cached_metadata else None

        if interfaces is None:
            if not blockchain.smart_contract_manager:
                return routes._error_response(
                    "Smart-contract VM feature is disabled",
                    status=503,
                    code="vm_feature_disabled",
                )
            try:
                interfaces = routes._detect_contract_interfaces(normalized)
            except RuntimeError as exc:
                logger.warning(
                    "RuntimeError in contract_interfaces",
                    error_type="RuntimeError",
                    error=str(exc),
                    function="contract_interfaces",
                )
                return routes._error_response(
                    str(exc),
                    status=503,
                    code="vm_feature_disabled",
                )
            cached_metadata = blockchain.update_contract_interface_metadata(
                normalized, interfaces, source="erc165_probe"
            )

        return routes._success_response(
            {
                "contract_address": normalized,
                "interfaces": interfaces,
                "metadata": {
                    "detected_at": cached_metadata.get("detected_at") if cached_metadata else None,
                    "source": (cached_metadata or {}).get("source", "unknown"),
                    "cached": served_from_cache,
                },
            }
        )

    @app.route("/contracts/<address>/events", methods=["GET"])
    def contract_events(address: str) -> Tuple[Dict[str, Any], int]:
        """Get contract events with pagination.

        Returns events emitted by the contract during execution, with pagination support.

        Path Parameters:
            address (str): The contract address

        Query Parameters:
            limit (int, optional): Maximum events to return (default: 50, max: 500)
            offset (int, optional): Number of events to skip (default: 0)

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains events array, counts, and pagination info
                - http_status_code: 200 on success, 400 on error

        Response includes:
            - contract_address: The queried contract
            - events: List of event objects
            - count: Number of events in this response
            - total: Total events for this contract
            - limit: Applied limit
            - offset: Applied offset

        Raises:
            ValidationError: If address or pagination params invalid (400).
        """
        try:
            limit, offset = routes._get_pagination_params(default_limit=50, max_limit=500)
        except ValueError as exc:
            logger.warning(
                "ValueError in contract_events",
                error_type="ValueError",
                error=str(exc),
                function="contract_events",
            )
            return routes._error_response(
                str(exc), status=400, code="invalid_pagination", event_type="contracts.invalid_paging"
            )

        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
            logger.warning(
                "ValueError in contract_events",
                error_type="ValueError",
                error=str(exc),
                function="contract_events",
            )
            return routes._error_response(
                str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
            )

        events, total = blockchain.get_contract_events(normalized, limit, offset)
        return routes._success_response(
            {
                "contract_address": normalized,
                "events": events,
                "count": len(events),
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )

    @app.route("/contracts/governance/status", methods=["GET"])
    def contract_feature_status() -> Tuple[Dict[str, Any], int]:
        """Expose smart-contract feature enablement status across config/governance/manager."""
        executor = getattr(blockchain, "governance_executor", None)
        feature_enabled = bool(
            executor and executor.is_feature_enabled("smart_contracts")
        )
        config_enabled = bool(getattr(Config, "FEATURE_FLAGS", {}).get("vm", False))
        manager_ready = bool(
            feature_enabled and config_enabled and blockchain.smart_contract_manager
        )
        return routes._success_response(
            {
                "feature_name": "smart_contracts",
                "config_enabled": config_enabled,
                "governance_enabled": feature_enabled,
                "contract_manager_ready": manager_ready,
                "contracts_tracked": len(blockchain.contracts),
                "receipts_tracked": len(blockchain.contract_receipts),
            }
        )

    @app.route("/contracts/governance/feature", methods=["POST"])
    @validate_request(routes.request_validator, ContractFeatureToggleInput)
    def contract_feature_toggle() -> Tuple[Dict[str, Any], int]:
        """Enable or disable smart contract feature via governance (admin only).

        Executes a governance proposal to enable/disable the smart contract VM feature.
        Creates and immediately executes a feature activation proposal.

        This endpoint requires admin authentication.

        Request Body (ContractFeatureToggleInput):
            {
                "enabled": bool (true to enable, false to disable),
                "reason": "optional explanation"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Contains proposal_id and governance_result
                - http_status_code: 200 on success, 400/403/500 on error

        Raises:
            AdminAuthError: If admin authentication fails (403).
            ServiceError: If governance executor unavailable (500).
            ValidationError: If toggle data is invalid (400).
            GovernanceError: If proposal execution fails (400).
        """
        if not blockchain.governance_executor:
            return routes._error_response(
                "Governance execution engine unavailable",
                status=500,
                code="governance_unavailable",
            )
        admin_allowed, admin_error = routes.api_auth.authorize_admin(request)
        if not admin_allowed:
            return routes._error_response(
                "Admin authentication failed",
                status=403,
                code="admin_auth_failed",
                context={"reason": admin_error},
            )

        model: Optional[ContractFeatureToggleInput] = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response(
                "Request must be a JSON object",
                status=400,
                code="invalid_payload",
            )

        enabled = model.enabled
        proposal_id = f"smart-contracts-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        proposal_data = {
            "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
            "feature_name": "smart_contracts",
            "enabled": enabled,
            "reason": model.reason or "",
        }

        try:
            execution_result = blockchain.governance_executor.execute_proposal(
                proposal_id, proposal_data
            )
        except (RuntimeError, ValueError, KeyError) as exc:
            return routes._handle_exception(exc, "contract_feature_toggle")

        if not execution_result.get("success"):
            return routes._error_response(
                "Governance toggle rejected",
                status=400,
                code="governance_toggle_rejected",
                context={"details": execution_result},
            )

        blockchain.sync_smart_contract_vm()
        routes._log_event(
            "contracts_governance_toggle",
            {
                "proposal_id": proposal_id,
                "feature": "smart_contracts",
                "enabled": enabled,
                "requester": getattr(request, "remote_addr", "unknown"),
            },
            severity="INFO",
        )

        return routes._success_response(
            {"proposal_id": proposal_id, "governance_result": execution_result}
        )
