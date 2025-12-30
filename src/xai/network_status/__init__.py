"""
XAI Network Status Module

Provides public-facing network status and health monitoring.
"""

from .status_page import app, collect_status

__all__ = ["app", "collect_status"]
