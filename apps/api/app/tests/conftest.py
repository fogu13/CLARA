"""Test isolation: never touch the developer's real .data/clara.db.

Every default store (signals, workflow, telemetry, connector configs, ...)
resolves its SQLite path via CLARA_DB_PATH (see app.main.default_db_path).
Without this, tests that build an app without injecting stores read/write the
shared dev database — which surfaced as a real bug: a Jira connector configured
in the dev UI leaked into an approval test and triggered a real network push.

Set at import time (before any test builds an app) so the whole run uses one
throwaway file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_DB_DIR = tempfile.mkdtemp(prefix="clara_test_db_")
os.environ["CLARA_DB_PATH"] = str(Path(_TEST_DB_DIR) / "clara_test.db")
