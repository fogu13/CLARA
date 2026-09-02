#!/usr/bin/env python3
"""Post-deploy smoke for the hosted CLARA stack — verifies the external-review
fixes are actually SERVING, not just merged.

Run after every VPS/Vercel deploy:

    python3 scripts/live_smoke.py
    python3 scripts/live_smoke.py --web https://... --api https://...

Read-only (GET/HEAD only). Exit 0 when every check passes; INFO rows are
informational (state that legitimately differs before/after the Phase B flip).
stdlib-only so it runs from any machine without installing anything.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

DEFAULT_WEB = "https://clara.odradekai.com"
DEFAULT_API = "https://api.clara.odradekai.com"

RESULTS: list[tuple[str, str, str]] = []  # (status, name, detail)


def record(status: str, name: str, detail: str = "") -> None:
    RESULTS.append((status, name, detail))
    print(f"  [{status:4}] {name}" + (f" — {detail}" if detail else ""))


def fetch(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "clara-live-smoke"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 — https URLs only
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def check(name: str, condition: bool, detail: str = "") -> None:
    record("PASS" if condition else "FAIL", name, detail if not condition else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", default=DEFAULT_WEB)
    parser.add_argument("--api", default=DEFAULT_API)
    args = parser.parse_args()
    web, api = args.web.rstrip("/"), args.api.rstrip("/")

    print(f"\n== Web: {web} ==")
    status, headers, body_bytes = fetch(f"{web}/")
    body = body_bytes.decode("utf-8", errors="replace")
    check("landing responds 200", status == 200, f"got {status}")
    check("canonical is the real domain", f'href="{web}/"' in body or "clara.odradekai.com" in body)
    check("no clara.eu leakage", "clara.eu" not in body, "clara.eu found in landing HTML")
    check(
        "no unshipped-integration claims",
        all(term not in body for term in ("Intercom", "Salesforce", "HubSpot")),
        "landing still names unshipped connectors",
    )
    check(
        '"measure", not "prove"',
        "measure whether it worked" in body,
        "claims-discipline hero line missing",
    )
    check(
        "Zendesk claimed as listening only",
        "Executes in Zendesk" not in body and "Zendesk · Jira · Slack" not in body,
        "landing claims execution in Zendesk (it is ingest-only)",
    )
    # Absence, not just presence: two "prove"-family strings survived the
    # original sweep because only the hero line was asserted. \b keeps
    # "approve"/"approvals" legal.
    check(
        'no "prove"-family claims',
        re.search(r"\bprov(?:e[sdn]?|ing)\b", body, re.IGNORECASE) is None,
        'a "prove/proving/proven" claim is live on the landing',
    )
    check(
        "no CRM-as-shipped claim",
        "and your CRM" not in body,
        'landing claims CRM execution ("and your CRM") while the connector is roadmap',
    )
    for header in ("content-security-policy", "x-content-type-options", "x-frame-options"):
        check(f"web header {header}", header in headers, "missing")

    status, _, _ = fetch(f"{web}/security")
    check("/security trust page live", status == 200, f"got {status}")

    status, _, _ = fetch(f"{web}/legal/impressum")
    if status == 404:
        record("INFO", "/legal/impressum is 404", "expected until the Fachanwalt flip publishes it")
    else:
        record("INFO", f"/legal/impressum is {status}", "legal pages appear PUBLISHED")

    status, headers, body_bytes = fetch(f"{web}/api/auth/session")
    try:
        session = json.loads(body_bytes)
        cookie_routes = status == 200 and "authenticated" in session
    except json.JSONDecodeError:
        cookie_routes = False
    check("cookie-auth routes deployed (/api/auth/session)", cookie_routes, f"got {status}")

    print(f"\n== API: {api} ==")
    status, headers, _ = fetch(f"{api}/problems")
    for header in ("strict-transport-security", "x-content-type-options", "x-frame-options"):
        check(f"api header {header}", header in headers, "missing — API runs pre-review code?")
    check(
        "auth fail-closed (unauthenticated /problems -> 401)",
        status == 401,
        f"got {status}" + (" — AUTH APPEARS DISABLED" if status == 200 else ""),
    )

    status, _, _ = fetch(f"{api}/health")
    check("liveness probe (/health -> 200)", status == 200, f"got {status}")
    status, _, body_bytes = fetch(f"{api}/ready")
    try:
        ready = json.loads(body_bytes)
    except json.JSONDecodeError:
        ready = {}
    check(
        "readiness probe (/ready -> 200, status ok: DB round-trip + AI residency)",
        status == 200 and ready.get("status") == "ok",
        f"got {status} {ready}",
    )

    status, _, _ = fetch(f"{api}/model-card/metrics")
    check(
        "model-card metrics endpoint present (401, not 404)",
        status == 401,
        f"got {status}" + (" — endpoint missing: old code" if status == 404 else ""),
    )

    status, _, _ = fetch(f"{api}/docs")
    check("swagger disabled in prod (/docs -> 404)", status == 404, f"got {status}")

    failures = [r for r in RESULTS if r[0] == "FAIL"]
    print(f"\n{len(RESULTS) - len(failures)}/{len(RESULTS)} checks OK, {len(failures)} FAIL")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
