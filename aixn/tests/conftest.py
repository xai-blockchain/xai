import os
import sys
from pathlib import Path

stubs = Path(__file__).parent / 'stubs'
if stubs.exists():
    sys.path.insert(0, str(stubs))

core_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, core_path)
