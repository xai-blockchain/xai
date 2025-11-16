import os
import sys
from pathlib import Path

# Add stubs directory to path for test stubs
stubs = Path(__file__).parent / "stubs"
if stubs.exists():
    sys.path.insert(0, str(stubs))

# Add src directory to path so tests can import aixn.core modules
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, src_path)
