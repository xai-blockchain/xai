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
                return routes._error_response(
                    "Invalid contract ABI",
                    status=400,
                    code="invalid_contract_abi",
                    context={"error": str(exc)},
                )

        try:
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
        except Exception as exc:
            return routes._error_response(
                "Unable to build deployment transaction",
                status=400,
                code="contract_build_error",
                context={"error": str(exc)},
            )

        if not tx.verify_signature():
            return routes._error_response(
                "Invalid signature",
                status=400,
                code="invalid_signature",
                context={"sender": model.sender},
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
        except Exception as exc:
            return routes._error_response(
                "Unable to build contract call",
                status=400,
                code="contract_build_error",
                context={"error": str(exc)},
            )

        if not tx.verify_signature():
            return routes._error_response(
                "Invalid signature",
                status=400,
                code="invalid_signature",
                context={"sender": model.sender},
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
        if not blockchain.smart_contract_manager:
            return routes._error_response(
                "Smart-contract VM feature is disabled",
                status=503,
                code="vm_feature_disabled",
            )
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
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
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
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
        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
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
        try:
            limit, offset = routes._get_pagination_params(default_limit=50, max_limit=500)
        except Exception as exc:
            return routes._error_response(
                str(exc), status=400, code="invalid_pagination", event_type="contracts.invalid_paging"
            )

        try:
            normalized = sanitizer.validate_address(address)
        except ValueError as exc:
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
        except Exception as exc:
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
