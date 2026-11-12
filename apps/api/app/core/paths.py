from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_ENG_DIR = ROOT_DIR / "data-engineering"
API_DIR = ROOT_DIR / "apps" / "api"

def ensure_python_paths() -> None:
    """Ensure monorepo modules (intelligence, data-engineering/*, apps/api) are importable."""
    candidates = [
        str(ROOT_DIR),
        str(DATA_ENG_DIR),
        str(API_DIR),
    ]
    for path in candidates:
        if path not in sys.path:
            sys.path.insert(0, path)

ensure_python_paths()
