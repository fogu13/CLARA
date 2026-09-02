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

# No background measurement loop during tests — run_due is exercised explicitly.
os.environ["CLARA_SCHEDULER_ENABLED"] = "0"

# Same isolation rule for Postgres: with a real DATABASE_URL in the developer's
# environment (the live Supabase project), any test building an app without
# injected stores would write TEST DATA INTO PRODUCTION. Unit tests are
# SQLite-only; live-DB parity is proven by scripts/pg_parity_smoke.py.
# Set to "" rather than popping: app/services/ai.py calls
# load_dotenv(override=False) at import, which would RESURRECT a popped var
# from apps/api/.env — an empty value blocks that and database_url() treats
# it as unset.
os.environ["DATABASE_URL"] = ""

# Same again for auth: real Supabase credentials in apps/api/.env would flip
# AUTH_ENABLED at import time and 401 every role-gated route in the suite.
# Unit tests run with auth disabled; auth behavior has its own dedicated tests.
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""

# Tests and demos time-travel the measurement clock (POST /measurements/run-due
# {"now": ...}); production refuses a future clock without this flag.
os.environ["CLARA_ALLOW_CLOCK_OVERRIDE"] = "1"
