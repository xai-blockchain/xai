"""
Fixtures for chaos testing
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
def chaos_blockchain_dir():
    """Create temporary directory for chaos blockchain testing"""
    temp_dir = tempfile.mkdtemp(prefix="chaos_blockchain_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
