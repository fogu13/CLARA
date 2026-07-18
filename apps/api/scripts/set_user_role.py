#!/usr/bin/env python3
"""Set a Supabase user's app-role (owner/admin/editor/viewer) without hand SQL.

CLARA reads a user's role from the JWT's app_metadata.user_role (see auth.py).
A user with none defaults to `viewer` — which locked the founder out of admin
features. Use this to provision teammates once you have DB access:

    DATABASE_URL=postgresql://... \
        python3 apps/api/scripts/set_user_role.py --email alice@example.com --role admin

Roles: owner | admin | editor | viewer. The user must sign out and back in
afterwards so a fresh JWT carries the new role. For the founder, prefer the
CLARA_OWNER_EMAILS env bootstrap (no DB write, can't lock you out) — this
script is for everyone else.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROLES = {"owner", "admin", "editor", "viewer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="defaults to $DATABASE_URL",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("error: set DATABASE_URL or pass --database-url", file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("error: psycopg not installed (pip install 'psycopg[binary]')", file=sys.stderr)
        return 2

    # Merge user_role into the existing app_metadata jsonb, per-email.
    patch = json.dumps({"user_role": args.role})
    with psycopg.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE auth.users
                SET raw_app_meta_data =
                    coalesce(raw_app_meta_data, '{}'::jsonb) || %s::jsonb
                WHERE lower(email) = lower(%s)
                RETURNING email, raw_app_meta_data->>'user_role'
                """,
                (patch, args.email),
            )
            row = cur.fetchone()
        conn.commit()

    if row is None:
        print(f"no user found with email {args.email!r}", file=sys.stderr)
        return 1
    print(f"set {row[0]} -> role={row[1]} (user must re-login to refresh their token)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
