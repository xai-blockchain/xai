"""
Batch Transaction API Routes

Provides endpoints for bulk transaction operations:
- Batch transaction submission
- Batch address generation
- CSV/JSON batch import support
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)

# Maximum transactions per batch
MAX_BATCH_SIZE = 100
# Maximum addresses per batch generation
MAX_ADDRESS_BATCH = 50


def register_batch_routes(routes: "NodeAPIRoutes") -> None:
    """Register batch transaction routes."""
    app = routes.app
    blockchain = routes.blockchain

    @app.route("/api/v1/transactions/batch", methods=["POST"])
    def batch_submit_transactions() -> tuple[dict[str, Any], int]:
        """
        Submit multiple transactions in a single request.

        Request body format:
        {
            "transactions": [
                {
                    "sender": "XAI...",
                    "recipient": "XAI...",
                    "amount": 10.0,
                    "fee": 0.001,
                    "public_key": "...",
                    "signature": "...",
                    "nonce": 1
                },
                ...
            ],
            "options": {
                "atomic": false,  // If true, fail all if any fails
                "continue_on_error": true  // Process remaining on error
            }
        }

        Returns:
            {
                "success": true,
                "submitted": 5,
                "failed": 1,
                "results": [
                    {"index": 0, "success": true, "txid": "..."},
                    {"index": 1, "success": false, "error": {...}}
                ]
            }
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        paused = routes._reject_if_paused("batch_submit")
        if paused:
            return paused

        data = request.get_json(silent=True) or {}
        transactions = data.get("transactions", [])
        options = data.get("options", {})

        if not transactions:
            return routes._error_response(
                "No transactions provided",
                status=400,
                code="empty_batch",
            )

        if len(transactions) > MAX_BATCH_SIZE:
            return routes._error_response(
                f"Batch size exceeds maximum of {MAX_BATCH_SIZE}",
                status=400,
                code="batch_too_large",
                context={"max_size": MAX_BATCH_SIZE, "provided": len(transactions)},
            )

        atomic = options.get("atomic", False)
        continue_on_error = options.get("continue_on_error", True)

        results: list[dict[str, Any]] = []
        submitted_count = 0
        failed_count = 0
        all_txids: list[str] = []

        for idx, tx_data in enumerate(transactions):
            try:
                result = _process_single_transaction(
                    routes, blockchain, tx_data, idx
                )
                results.append(result)

                if result.get("success"):
                    submitted_count += 1
                    if result.get("txid"):
                        all_txids.append(result["txid"])
                else:
                    failed_count += 1
                    if atomic:
                        # Rollback not possible for submitted tx, but stop processing
                        logger.warning(
                            "Atomic batch failed at index %d, stopping",
                            idx,
                        )
                        break
                    if not continue_on_error:
                        break

            except (ValueError, TypeError, KeyError) as e:
                error_result = {
                    "index": idx,
                    "success": False,
                    "error": {
                        "code": "processing_error",
                        "message": str(e),
                    },
                }
                results.append(error_result)
                failed_count += 1

                if atomic or not continue_on_error:
                    break

        logger.info(
            "Batch transaction complete",
            extra={
                "submitted": submitted_count,
                "failed": failed_count,
                "total": len(transactions),
            },
        )

        return (
            jsonify(
                {
                    "success": failed_count == 0 or submitted_count > 0,
                    "submitted": submitted_count,
                    "failed": failed_count,
                    "total": len(transactions),
                    "results": results,
                    "txids": all_txids,
                }
            ),
            200 if submitted_count > 0 else 400,
        )

    @app.route("/api/v1/transactions/batch/import", methods=["POST"])
    def batch_import_transactions() -> tuple[dict[str, Any], int]:
        """
        Import transactions from CSV or JSON file format.

        Supports:
        - JSON array of transaction objects
        - CSV with columns: sender, recipient, amount, fee

        Request:
            Content-Type: application/json or multipart/form-data
            - For JSON: {"data": [...], "format": "json"}
            - For CSV: Form upload with file field

        Returns:
            Parsed transactions ready for batch submission
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        content_type = request.content_type or ""

        if "multipart/form-data" in content_type:
            # Handle file upload
            if "file" not in request.files:
                return routes._error_response(
                    "No file provided",
                    status=400,
                    code="missing_file",
                )

            file = request.files["file"]
            filename = file.filename or ""

            try:
                content = file.read().decode("utf-8")
            except UnicodeDecodeError as e:
                return routes._error_response(
                    f"Invalid file encoding: {e}",
                    status=400,
                    code="invalid_encoding",
                )

            if filename.endswith(".csv"):
                transactions = _parse_csv_transactions(content)
            elif filename.endswith(".json"):
                transactions = _parse_json_transactions(content)
            else:
                return routes._error_response(
                    "Unsupported file format. Use .csv or .json",
                    status=400,
                    code="unsupported_format",
                )
        else:
            # Handle JSON body
            data = request.get_json(silent=True) or {}
            raw_data = data.get("data", [])
            fmt = data.get("format", "json")

            if fmt == "csv":
                transactions = _parse_csv_transactions(raw_data)
            else:
                transactions = raw_data if isinstance(raw_data, list) else []

        if not transactions:
            return routes._error_response(
                "No valid transactions found in import",
                status=400,
                code="empty_import",
            )

        if len(transactions) > MAX_BATCH_SIZE:
            return routes._error_response(
                f"Import size exceeds maximum of {MAX_BATCH_SIZE}",
                status=400,
                code="import_too_large",
                context={"max_size": MAX_BATCH_SIZE, "found": len(transactions)},
            )

        return (
            jsonify(
                {
                    "success": True,
                    "parsed_count": len(transactions),
                    "transactions": transactions,
                    "message": "Use /api/v1/transactions/batch to submit",
                }
            ),
            200,
        )

    @app.route("/api/v1/addresses/batch", methods=["POST"])
    def batch_generate_addresses() -> tuple[dict[str, Any], int]:
        """
        Generate multiple wallet addresses in a single request.

        Request body:
        {
            "count": 10,
            "format": "default"  // optional
        }

        Returns:
            {
                "success": true,
                "count": 10,
                "addresses": [
                    {"address": "XAI...", "public_key": "..."},
                    ...
                ]
            }
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}
        count = data.get("count", 1)

        if not isinstance(count, int) or count < 1:
            return routes._error_response(
                "Invalid count",
                status=400,
                code="invalid_count",
            )

        if count > MAX_ADDRESS_BATCH:
            return routes._error_response(
                f"Count exceeds maximum of {MAX_ADDRESS_BATCH}",
                status=400,
                code="batch_too_large",
                context={"max_count": MAX_ADDRESS_BATCH},
            )

        try:
            from xai.core.wallet import Wallet

            addresses = []
            for _ in range(count):
                wallet = Wallet()
                addresses.append(
                    {
                        "address": wallet.address,
                        "public_key": wallet.public_key,
                    }
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "count": len(addresses),
                        "addresses": addresses,
                    }
                ),
                200,
            )

        except (ImportError, ValueError, RuntimeError) as e:
            logger.error("Address generation failed: %s", e)
            return routes._error_response(
                "Address generation failed",
                status=500,
                code="generation_error",
            )


def _process_single_transaction(
    routes: "NodeAPIRoutes",
    blockchain: Any,
    tx_data: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    """Process a single transaction from a batch."""
    required = ["sender", "recipient", "amount"]
    missing = [f for f in required if f not in tx_data]

    if missing:
        return {
            "index": index,
            "success": False,
            "error": {
                "code": "missing_fields",
                "message": f"Missing required fields: {missing}",
                "details": {"missing": missing},
            },
        }

    try:
        from xai.core.blockchain import Transaction

        tx = Transaction(
            sender=tx_data.get("sender"),
            recipient=tx_data.get("recipient"),
            amount=tx_data.get("amount"),
            fee=tx_data.get("fee", 0.001),
            public_key=tx_data.get("public_key"),
            nonce=tx_data.get("nonce"),
        )

        if tx_data.get("signature"):
            tx.signature = tx_data.get("signature")
        if tx_data.get("timestamp"):
            tx.timestamp = tx_data.get("timestamp")
        else:
            tx.timestamp = time.time()

        tx.txid = tx_data.get("txid") or tx.calculate_hash()

        # Validate and add
        if blockchain.add_transaction(tx):
            routes.node.broadcast_transaction(tx)
            return {
                "index": index,
                "success": True,
                "txid": tx.txid,
            }
        else:
            return {
                "index": index,
                "success": False,
                "error": {
                    "code": "validation_failed",
                    "message": "Transaction validation failed",
                },
            }

    except (ValueError, TypeError, KeyError) as e:
        return {
            "index": index,
            "success": False,
            "error": {
                "code": "transaction_error",
                "message": str(e),
            },
        }


def _parse_csv_transactions(content: str) -> list[dict[str, Any]]:
    """Parse CSV content into transaction objects."""
    transactions = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            tx = {
                "sender": row.get("sender", "").strip(),
                "recipient": row.get("recipient", "").strip(),
                "amount": float(row.get("amount", 0)),
                "fee": float(row.get("fee", 0.001)),
            }
            if row.get("public_key"):
                tx["public_key"] = row["public_key"].strip()
            if row.get("signature"):
                tx["signature"] = row["signature"].strip()
            if row.get("nonce"):
                tx["nonce"] = int(row["nonce"])

            transactions.append(tx)
    except (ValueError, KeyError, csv.Error) as e:
        logger.warning("CSV parse error: %s", e)

    return transactions


def _parse_json_transactions(content: str) -> list[dict[str, Any]]:
    """Parse JSON content into transaction objects."""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "transactions" in data:
            return data["transactions"]
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error: %s", e)

    return []
