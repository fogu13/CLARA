"""Shared path resolution for the CLARA API.

Resolves the repo root both on dev machines (monorepo layout:
CLARA/apps/api/app/...) and inside containers (code at /app/app/...).

Priority: explicit CLARA_REPO_ROOT env var > monorepo parents[4] > /app.
"""

from __future__ import annotations

import os
from pathlib import Path


def find_repo_root() -> Path:
    env_root = os.getenv("CLARA_REPO_ROOT")
    if env_root:
        return Path(env_root)
    try:
        return Path(__file__).resolve().parents[4]
    except IndexError:
        return Path("/app")


REPO_ROOT = find_repo_root()
