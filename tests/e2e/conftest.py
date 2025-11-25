"""
Fixtures for E2E testing
"""

import os
import sys
from pathlib import Path

# Add src directory to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, src_path)

import pytest
import tempfile
import shutil


@pytest.fixture
def e2e_blockchain_dir():
    """Create temporary directory for E2E blockchain"""
    temp_dir = tempfile.mkdtemp(prefix="e2e_blockchain_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def e2e_multi_node_dirs(tmp_path):
    """Create multiple blockchain directories for E2E tests"""
    dirs = []
    for i in range(3):
        node_dir = tmp_path / f"e2e_node_{i}"
        node_dir.mkdir()
        dirs.append(node_dir)
    return dirs
