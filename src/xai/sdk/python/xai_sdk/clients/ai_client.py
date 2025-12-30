from __future__ import annotations

"""
AI Client for XAI SDK

Handles all AI-related operations including:
- Personal AI assistant operations
- Smart contract creation and deployment
- Transaction optimization
- Blockchain and wallet analysis
- Node setup recommendations
"""

from typing import Any, Iterator

from ..exceptions import APIError
from ..http_client import HTTPClient


class AIClient:
    """Client for AI operations on XAI blockchain."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize AI Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def atomic_swap(
        self,
        from_currency: str,
        to_currency: str,
        amount: float,
        recipient_address: str,
    ) -> dict[str, Any]:
        """
        Execute atomic swap with AI assistance.

        Args:
            from_currency: Source currency (e.g., "XAI", "BTC")
            to_currency: Target currency
            amount: Amount to swap
            recipient_address: Destination address

        Returns:
            Swap execution result

        Raises:
            APIError: If swap fails
        """
        payload = {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "recipient_address": recipient_address,
        }
        return self.http_client.post("/personal-ai/atomic-swap", data=payload)

    def create_contract(
        self,
        contract_type: str,
        parameters: dict[str, Any],
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Create smart contract with AI assistance.

        Args:
            contract_type: Type of contract (e.g., "token", "nft", "escrow")
            parameters: Contract parameters
            description: Optional description of contract purpose

        Returns:
            Created contract details

        Raises:
            APIError: If contract creation fails
        """
        payload = {
            "contract_type": contract_type,
            "parameters": parameters,
        }
        if description:
            payload["description"] = description
        return self.http_client.post("/personal-ai/smart-contract/create", data=payload)

    def deploy_contract(
        self,
        contract_code: str,
        constructor_args: list[Any] | None = None,
        gas_limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Deploy smart contract with AI optimization.

        Args:
            contract_code: Contract bytecode or source
            constructor_args: Optional constructor arguments
            gas_limit: Optional gas limit

        Returns:
            Deployment result with contract address

        Raises:
            APIError: If deployment fails
        """
        payload = {
            "contract_code": contract_code,
        }
        if constructor_args:
            payload["constructor_args"] = constructor_args
        if gas_limit:
            payload["gas_limit"] = gas_limit
        return self.http_client.post("/personal-ai/smart-contract/deploy", data=payload)

    def optimize_transaction(
        self,
        transaction: dict[str, Any],
        optimization_goals: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Optimize transaction with AI.

        Args:
            transaction: Transaction to optimize
            optimization_goals: Optional goals like ["low_fee", "fast_confirmation"]

        Returns:
            Optimized transaction details

        Raises:
            APIError: If optimization fails
        """
        payload = {
            "transaction": transaction,
        }
        if optimization_goals:
            payload["optimization_goals"] = optimization_goals
        return self.http_client.post("/personal-ai/transaction/optimize", data=payload)

    def analyze_blockchain(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze blockchain with AI.

        Args:
            query: Analysis query or question
            context: Optional additional context

        Returns:
            Analysis results

        Raises:
            APIError: If analysis fails
        """
        payload = {"query": query}
        if context:
            payload["context"] = context
        return self.http_client.post("/personal-ai/analyze", data=payload)

    def analyze_wallet(self, address: str) -> dict[str, Any]:
        """
        Analyze wallet with AI.

        Args:
            address: Wallet address to analyze

        Returns:
            Wallet analysis results

        Raises:
            APIError: If analysis fails
        """
        return self.http_client.post("/personal-ai/wallet/analyze", data={"address": address})

    def wallet_recovery_advice(
        self,
        partial_info: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Get wallet recovery advice from AI.

        Args:
            partial_info: Partial wallet information (e.g., mnemonic words, dates)

        Returns:
            Recovery recommendations

        Raises:
            APIError: If recovery advice fails
        """
        return self.http_client.post("/personal-ai/wallet/recovery", data=partial_info)

    def node_setup_recommendations(
        self,
        hardware_specs: dict[str, Any] | None = None,
        use_case: str | None = None,
    ) -> dict[str, Any]:
        """
        Get node setup recommendations from AI.

        Args:
            hardware_specs: Optional hardware specifications
            use_case: Optional use case (e.g., "mining", "validator", "archive")

        Returns:
            Setup recommendations

        Raises:
            APIError: If recommendations fail
        """
        payload: dict[str, Any] = {}
        if hardware_specs:
            payload["hardware_specs"] = hardware_specs
        if use_case:
            payload["use_case"] = use_case
        return self.http_client.post("/personal-ai/node/setup", data=payload)

    def liquidity_alert(
        self,
        pool_id: str,
        alert_type: str,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        """
        Set up liquidity pool alert with AI monitoring.

        Args:
            pool_id: Liquidity pool identifier
            alert_type: Type of alert (e.g., "price_change", "volume", "impermanent_loss")
            threshold: Optional threshold value

        Returns:
            Alert configuration result

        Raises:
            APIError: If alert setup fails
        """
        payload = {
            "pool_id": pool_id,
            "alert_type": alert_type,
        }
        if threshold is not None:
            payload["threshold"] = threshold
        return self.http_client.post("/personal-ai/liquidity/alert", data=payload)

    def list_assistants(self) -> list[dict[str, Any]]:
        """
        List available AI assistants.

        Returns:
            List of available AI assistants

        Raises:
            APIError: If listing fails
        """
        response = self.http_client.get("/personal-ai/assistants")
        return response.get("assistants", [])

    def stream(
        self,
        prompt: str,
        assistant_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """
        Stream AI response chunks.

        Args:
            prompt: User prompt
            assistant_id: Optional specific assistant to use
            context: Optional context

        Yields:
            Response chunks

        Raises:
            APIError: If streaming fails
        """
        payload = {"prompt": prompt}
        if assistant_id:
            payload["assistant_id"] = assistant_id
        if context:
            payload["context"] = context

        # Use streaming endpoint
        response = self.http_client.post_stream("/personal-ai/stream", data=payload)
        for chunk in response:
            yield chunk
