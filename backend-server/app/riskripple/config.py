"""Shared path configuration.

Paths default relative to this file's location inside backend-server/app/riskripple/,
with env var overrides so deployment can repoint them without a code change.
"""
from __future__ import annotations

import os
from pathlib import Path

_BACKEND_SERVER_ROOT = Path(__file__).resolve().parents[2]  # app/riskripple/ -> backend-server/

FIXTURES_DIR = Path(os.environ.get("RISKRIPPLE_FIXTURES_DIR", _BACKEND_SERVER_ROOT / "data" / "fixtures"))
REPORTS_DIR = Path(os.environ.get("RISKRIPPLE_REPORTS_DIR", _BACKEND_SERVER_ROOT / "data" / "analysis" / "reports"))
