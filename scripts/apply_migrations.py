"""Apply apps/api/migrations/*.sql to a PostgreSQL database in the documented order.

    python scripts/apply_migrations.py DATABASE_URL            # the full chain
    python scripts/apply_migrations.py DATABASE_URL --only 017 # one pending file
    python scripts/apply_migrations.py DATABASE_URL --skip 012 # omit a file
    python scripts/apply_migrations.py DATABASE_URL --dry-run  # print the plan

Order (DEPLOY.md, plus the ORDERING notes in 011, 013, 014, 016 and 017):
004 runs before 003 (003's unmapped_signals() needs the workspace_id column
004 adds), 013 -> 014 -> 015 -> 016 -> 017 (each replaces or extends the
previous one's objects), and 012 last because it is conditional on the
embedding model (DEPLOY.md: only for 1024-dimension models such as
mistral-embed, which production uses; pass --skip 012 for a 768-dimension
deployment).

The API's own boot DDL runs between 008 and 009, where it sits in
production's history: 009, 011 and 014 alter clara_journey_events and
clara_feedback_rules, tables only the API creates at boot, and 004 must
come BEFORE the API DDL because 004 adds the core tables' workspace_id as
INTEGER (its policies call is_current_workspace(integer)) while the API DDL
creates missing tables with BIGINT columns — on a database the API booted on
first, 004's policies fail with "is_current_workspace(bigint) does not
exist". Pass --no-api-ddl for a database the API already booted on.

Each file runs in its own transaction: the first failure rolls that file
back, stops the run and names the file. Server NOTICE/WARNING output is
printed (011 warns when pg_cron is unavailable and the tick stays in-process).

This is for disposable databases (the CI service, a scratch server) and the
DEPLOY.md release step. Point it at production only as that step describes,
after a backup, never to "see what happens".
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "apps" / "api" / "migrations"
API_DIR = REPO_ROOT / "apps" / "api"

# The documented order, by file-name prefix; API_DDL marks the API's boot DDL.
API_DDL = "api-ddl"
ORDER: tuple[str, ...] = (
    "001",
    "002",
    "004",
    "003",
    "005",
    "006",
    "007",
    "008",
    API_DDL,
    "009",
    "010",
    "011",
    "013",
    "014",
    "015",
    "016",
    "017",
    "012",
)
# Files that need the vector extension (003 creates it; 012 retypes a vector column).
NEEDS_PGVECTOR = {"003", "012"}


def migration_files() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        prefix = path.name[:3]
        if prefix in files:
            raise SystemExit(f"two migration files share the prefix {prefix}: {files[prefix].name}, {path.name}")
        files[prefix] = path
    return files


def plan(only: list[str] | None = None, skip: list[str] | None = None, api_ddl: bool = True) -> list[Path | str]:
    """The steps to run: migration file paths, with the API_DDL marker where
    the API's boot DDL belongs. --only drops the DDL step (a single pending
    file is applied to a database the API already runs against)."""
    files = migration_files()
    unordered = sorted(set(files) - set(ORDER))
    if unordered:
        raise SystemExit(
            f"migration file(s) {', '.join(unordered)} are not in the documented ORDER of this script; "
            "add them (and the DEPLOY.md list) before applying"
        )
    chosen = [step for step in ORDER if step in files or step == API_DDL]
    if only:
        missing = [p for p in only if p not in files]
        if missing:
            raise SystemExit(f"no migration file with prefix {', '.join(missing)}")
        chosen = [step for step in chosen if step in only]
    if skip:
        chosen = [step for step in chosen if step not in skip]
    if not api_ddl:
        chosen = [step for step in chosen if step != API_DDL]
    return [files[step] if step != API_DDL else API_DDL for step in chosen]


def _print_notice(diag) -> None:
    print(f"    [{diag.severity}] {diag.message_primary}")


def run_api_ddl(url: str) -> None:
    """The API's boot-time DDL: PostgresConnectionMixin._run_schema_ddl (the
    tables the stores own, self-healed columns and tenant-first keys) plus the
    one table a store creates in its constructor (clara_feedback_rules)."""
    sys.path.insert(0, str(API_DIR))
    from app.services.postgres import PostgresConnectionMixin, PostgresRuleStore, normalize_database_url

    probe = PostgresConnectionMixin.__new__(PostgresConnectionMixin)
    probe.url = normalize_database_url(url)
    probe._run_schema_ddl()
    PostgresRuleStore(url)


def apply_file(url: str, path: Path) -> None:
    import psycopg

    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(url) as conn:  # one transaction per file; commit on clean exit
        conn.add_notice_handler(_print_notice)
        # No parameters: psycopg sends the whole file with the simple query
        # protocol, so multi-statement files and $$ bodies run as written.
        conn.execute(sql)


def pgvector_available(url: str) -> bool:
    import psycopg

    with psycopg.connect(url) as conn:
        row = conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'").fetchone()
    return row is not None


def measurement_state(url: str) -> dict[str, object]:
    sys.path.insert(0, str(API_DIR))
    import psycopg

    from app.services.postgres import measurement_schema_state

    with psycopg.connect(url) as conn:
        return measurement_schema_state(conn)


def _label(step: Path | str) -> str:
    return "API boot DDL" if step == API_DDL else step.name[:3]


def apply(url: str, *, only: list[str] | None = None, skip: list[str] | None = None, api_ddl: bool = True,
          dry_run: bool = False, out=sys.stdout) -> list[Path]:
    steps = plan(only, skip, api_ddl=api_ddl)
    print(f"plan: {', '.join(_label(s) for s in steps)}", file=out)
    files = [s for s in steps if s != API_DDL]
    if dry_run:
        return files
    needs_vector = [p for p in files if p.name[:3] in NEEDS_PGVECTOR]
    if needs_vector and not pgvector_available(url):
        raise SystemExit(
            f"{', '.join(p.name for p in needs_vector)} need the vector extension and this server cannot "
            "provide it (pg_available_extensions has no 'vector'): install pgvector (CI uses the "
            "pgvector/pgvector:pg16 image) or pass --skip 003 --skip 012 for a database without the "
            "semantic taxonomy. Nothing was applied."
        )
    applied: list[Path] = []
    for step in steps:
        print(f"  {_label(step) if step == API_DDL else step.name}", file=out)
        try:
            if step == API_DDL:
                run_api_ddl(url)
                continue
            apply_file(url, step)
        except Exception as exc:  # noqa: BLE001 — name the step, then stop
            print(f"FAILED at {_label(step)}: {type(exc).__name__}: {exc}", file=out)
            print(f"applied before the failure: {', '.join(p.name[:3] for p in applied) or 'nothing'}", file=out)
            raise SystemExit(1) from exc
        applied.append(step)
    state = measurement_state(url)
    print(
        "measurement schema: function_version="
        f"{state['function_version']} tick={state['backend_tick']} columns_missing={state['columns_missing']}",
        file=out,
    )
    return applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", nargs="?", default=os.getenv("CLARA_TEST_DATABASE_URL"),
                        help="PostgreSQL URL (default: $CLARA_TEST_DATABASE_URL)")
    parser.add_argument("--only", action="append", metavar="NNN", help="apply only this prefix (repeatable)")
    parser.add_argument("--skip", action="append", metavar="NNN", help="omit this prefix (repeatable)")
    parser.add_argument("--no-api-ddl", action="store_true", help="do not run the API boot DDL first")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = parser.parse_args(argv)
    if not args.url:
        parser.error("give a database URL or set CLARA_TEST_DATABASE_URL")
    apply(args.url, only=args.only, skip=args.skip, api_ddl=not args.no_api_ddl, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
