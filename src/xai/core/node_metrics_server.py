from __future__ import annotations

"""
XAI Node - Prometheus Metrics Server Integration
Automatically starts Prometheus metrics server with the node
"""

import logging

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

class MetricsServer:
    """Manages Prometheus metrics HTTP server for XAI blockchain node"""

    def __init__(self, port: int = 8000):
        """
        Initialize metrics server

        Args:
            port: Port to expose metrics endpoint (default: 8000)
        """
        self.port = port
        self.started = False

    def start(self):
        """Start Prometheus metrics HTTP server"""
        if self.started:
            logger.warning(f"Metrics server already running on port {self.port}")
            return

        try:
            start_http_server(self.port)
            self.started = True
            print(f"✓ XAI Prometheus metrics server started on http://localhost:{self.port}/metrics")
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Port {self.port} already in use, metrics server not started")
                print(f"⚠ Port {self.port} already in use - metrics server not started")
            else:
                logger.error(f"Failed to start metrics server: {e}")
                print(f"✗ Failed to start metrics server: {e}")
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(f"Unexpected error starting metrics server: {e}", extra={"error_type": type(e).__name__})
            print(f"✗ Metrics server error: {e}")

# Global metrics server instance
_metrics_server: MetricsServer | None = None

def get_metrics_server(port: int = 8000) -> MetricsServer:
    """
    Get or create global metrics server instance

    Args:
        port: Port for metrics endpoint

    Returns:
        MetricsServer instance
    """
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer(port=port)
    return _metrics_server

def start_metrics_server_if_enabled(port: int = 8000, enabled: bool = True):
    """
    Start Prometheus metrics server if enabled

    Args:
        port: Port for metrics endpoint
        enabled: Whether to start the server
    """
    if not enabled:
        logger.info("Prometheus metrics server disabled")
        return

    server = get_metrics_server(port=port)
    server.start()
