from pathlib import Path
import sys

# Ensure project root is on sys.path during tests so top-level imports work.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
