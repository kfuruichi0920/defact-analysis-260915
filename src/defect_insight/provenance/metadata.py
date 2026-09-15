"""Provenance and reproducibility metadata tracking."""

from __future__ import annotations

import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import importlib.metadata


def calculate_file_hash(path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_system_provenance() -> Dict[str, Any]:
    """Collects runtime and dependency provenance without external network calls."""
    deps = {}
    for pkg in ["duckdb", "openpyxl", "pyyaml", "pytest"]:
        try:
            deps[pkg] = importlib.metadata.version(pkg)
        except Exception:
            deps[pkg] = "unknown"

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "os": sys.platform,
        "dependencies": deps,
        "app_version": "0.1.0",
        "query_plan_schema_version": "1.0.0",
    }
