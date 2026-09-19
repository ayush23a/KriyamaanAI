import sys
from pathlib import Path

# Ensure kriyaman directory is on sys.path
kriyaman_root = Path(__file__).resolve().parent.parent
if str(kriyaman_root) not in sys.path:
    sys.path.insert(0, str(kriyaman_root))

