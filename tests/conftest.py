"""
Test configuration and fixtures
"""
import sys
import os
from pathlib import Path

# Add project root and src to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

import pytest
