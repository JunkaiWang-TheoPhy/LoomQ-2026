"""Regression tests that ship inside the formal starter_kit archive.

The archive is evaluated with ``starter_kit/`` as its working root.  Adding that
same root during package discovery also makes ``python -m unittest discover``
from the repository root exercise the identical modules.
"""

from pathlib import Path
import sys


STARTER_ROOT = str(Path(__file__).resolve().parents[1])
if STARTER_ROOT not in sys.path:
    sys.path.insert(0, STARTER_ROOT)
