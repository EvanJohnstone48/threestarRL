"""Shared pytest fixtures for threestarRL.

Add fixtures here that span multiple subsystems. Per-subsystem fixtures live in
the subsystem's own conftest.py (e.g., tests/unit/sandbox_core/conftest.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make 'app' the import root so tests can `import sandbox_core`, `import barracks`,
# `import cartographer` without packaging the project first.
REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
