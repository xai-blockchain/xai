"""
XAI Blockchain - XAI Token Metrics

Provides real-time and historical data on XAI token supply, distribution, and other key metrics.
"""

from typing import Dict, Any, Optional, List
import time
from collections import defaultdict
from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.xai_token_manager import XAITokenManager, get_xai_token_manager


class XAITokenMetrics:
    """
    Tracks and provides various metrics for the XAI token.
    """

    def __init__(
        self,
        token_manager: Optional[XAITokenManager] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.token_manager = token_manager or get_xai_token_manager()
        self.logger = logger or get_structured_logger()
        self.historical_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.snapshot_interval = 3600  # 1 hour
        self.last_snapshot_time = 0
        self.logger.info("XAITokenMetrics initialized.")

    def take_snapshot(self):
        """
        Takes a snapshot of current token metrics and stores it historically.
        """
        current_time = int(time.time())
        metrics = self.token_manager.get_token_metrics()
        metrics["timestamp"] = current_time
        self.historical_data["supply_metrics"].append(metrics)
        self.logger.debug("Token metrics snapshot taken.", metrics=metrics)
        self.last_snapshot_time = current_time

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Returns the most current token metrics.
        """
        return self.token_manager.get_token_metrics()

    def get_historical_metrics(
        self, metric_type: str = "supply_metrics", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Returns historical token metrics.

        Args:
            metric_type: The type of metric to retrieve (e.g., 'supply_metrics').
            limit: The maximum number of historical entries to return.
        """
        return self.historical_data.get(metric_type, [])[-limit:]

    def get_distribution_data(self) -> Dict[str, float]:
        """
        Returns data on token distribution across addresses.
        """
        # This would typically involve iterating through the blockchain's UTXO set or
        # the token manager's internal balances.
        # For now, we'll use the balances from the XAIToken object.
        return self.token_manager.xai_token.balances

    def get_top_holders(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Returns a list of top token holders.
        """
        balances = self.get_distribution_data()
        sorted_holders = sorted(balances.items(), key=lambda item: item[1], reverse=True)
        top_holders = [{"address": addr, "balance": bal} for addr, bal in sorted_holders[:count]]
        return top_holders

    def update(self):
        """
        Periodically updates metrics.
        """
        if time.time() - self.last_snapshot_time >= self.snapshot_interval:
            self.take_snapshot()


# Global instance for convenience
_global_xai_token_metrics = None


def get_xai_token_metrics(
    token_manager: Optional[XAITokenManager] = None, logger: Optional[StructuredLogger] = None
) -> XAITokenMetrics:
    """
    Get global XAITokenMetrics instance.
    """
    global _global_xai_token_metrics
    if _global_xai_token_metrics is None:
        _global_xai_token_metrics = XAITokenMetrics(token_manager, logger)
    return _global_xai_token_metrics
