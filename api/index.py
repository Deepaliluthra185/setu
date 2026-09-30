import sys
from pathlib import Path

# Ensure project root directory is in sys.path so modules (db, nlu, scoring) are found
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from main import app
