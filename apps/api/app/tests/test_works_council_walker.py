"""W1 Betriebsrat-Modus (§87(1) Nr. 6 BetrVG): the plan's acceptance test.

With works_council_mode on, a walker hits EVERY GET endpoint with a non-admin
token and asserts no response contains a per-user performance-capable field:
none of the seeded person identifiers appear anywhere, and every
REDACTED_FIELDS key holds nothing but its fixed role label. Counter-tests pin
the boundaries: admin keeps full identities (incl. /audit-export), and the
flag OFF keeps identities for everyone.

Auth is flipped ON via the light pattern from test_tenant_identity (module
globals patched; the rest of the suite stays auth-disabled). Routes are
enumerated in-process from app.routes — /openapi.json is disabled when auth
is on.
"""

from __future__ import annotations

import re
import time

import jwt
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.workflow import WorkflowStore
from app.services.works_council import REDACTED_FIELDS, k_suppress, redact
from app.services.workspace import SQLiteWorkspaceStore

SECRET = "works-council-test-secret"
EDITOR_SUB = "deadbeef-dead-beef-dead-beefdeadbeef"  # -> actor "user-deadbeef"

APPROVAL_REVIEWER = "wc-reviewer@example.com"
CANDIDATE_REVIEWER = "wc-candidate-reviewer@example.com"
TAXONOMY_ACTOR = "wc-taxonomist-anna"
CLOSURE_ACTOR = "user-deadbeef"  # _actor_identifier(EDITOR_SUB)

# Every distinctive person identifier seeded through real flows below. Seed
# problem owners (team labels) are covered by the structural check instead.
SEEDED_IDENTIFIERS = (
    APPROVAL_REVIEWER,
    CANDIDATE_REVIEWER,
    TAXONOMY_ACTOR,
    CLOSURE_ACTOR,
)

PROBLEM_ID = "PRB-108"

CLOSURE_BODY = {
    "operational_status": "released",
    "customer_status": "draft_ready",
    "owner": "cx_operations",
    "verified_resolution_facts": ["Resolution released."],
    "unresolved_customers": 1,
    "follow_up_channel": "zendesk",
    "limitations": [],
}

# The walker must prove it exercised the known person-bearing read surfaces;
# a walker that silently skipped them would prove nothing.
REQUIRED_COVERAGE = {
    "/approvals",
    "/problems/{problem_id}/workflow",
    "/problems/{problem_id}/evidence-pack",
    "/outcome-board",
    "/problems",
    "/problem-candidates",
    "/taxonomies",
}


def _token(role: str, sub: str = EDITOR_SUB) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "email": f"wc-{role}@example.com",
            "exp": int(time.time()) + 3600,
            "app_metadata": {"workspace_id": 1, "user_role": role},
        },
        SECRET,
        algorithm="HS256",
    )


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(role)}"}


EDITOR = "editor"
ADMIN = "admin"


@pytest.fixture
def wc(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr("app.auth.AUTH_ENABLED", True)
    monkeypatch.setattr("app.auth.SUPABASE_JWT_SECRET", SECRET)
    app = create_app(
        problem_store=ProblemStore(load_seed_problems()),
        workflows=WorkflowStore(),
        signals=SQLiteSignalStore(tmp_path / "signals.db"),  # isolated candidates
        workspace=SQLiteWorkspaceStore(tmp_path / "workspace.db"),
    )
    client = TestClient(app)
    _seed_person_data(client)
    return app, client


def _seed_person_data(client: TestClient) -> None:
    """Push distinctive person identifiers through the REAL write flows."""
    editor = _bearer(EDITOR)

    # Approval -> ApprovalRecord.reviewer + ExecutionRecord.reviewed_by +
    # jira draft assignee + timeline actor.
    approved = client.post(
        f"/problems/{PROBLEM_ID}/approvals",
        json={
            "action_id": "ACT-501",
            "decision": "approved",
            "reviewer": APPROVAL_REVIEWER,
            "note": "Works-council walker seed.",
        },
        headers=editor,
    )
    assert approved.status_code == 200, approved.text

    # Candidate review -> ProblemCandidate.reviewer/reviewed_at.
    candidates = client.get("/problem-candidates", headers=editor).json()
    assert candidates, "walker seed needs at least one problem candidate"
    rejectable = next(c for c in candidates if c["review_status"] != "accepted")
    rejected = client.post(
        f"/problem-candidates/{rejectable['candidate_id']}/reject",
        json={"reviewer": CANDIDATE_REVIEWER, "note": "Rejected for walker seed."},
        headers=editor,
    )
    assert rejected.status_code == 200, rejected.text

    # Taxonomy change -> categories[].change_history[].actor.
    catalog = client.get("/taxonomies", headers=editor).json()[0]
    category = next(c for c in catalog["categories"] if not c["locked"])
    renamed = client.post(
        f"/taxonomies/{catalog['taxonomy_type']}/categories/rename",
        json={
            "category_id": category["category_id"],
            "label": f"{category['label']} (walker)",
            "actor": TAXONOMY_ACTOR,
        },
        headers=editor,
    )
    assert renamed.status_code == 200, renamed.text

    # Closure -> ClosureRecord.actor, bound to the editor JWT (user-deadbeef).
    closed = client.post(
        f"/problems/{PROBLEM_ID}/closure", json=CLOSURE_BODY, headers=editor
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["actor"] == CLOSURE_ACTOR


def _set_flag(client: TestClient, enabled: bool) -> None:
    # Toggling the flag is admin-only: an editor flipping it off would defeat
    # the very control the mode exists for (see test below).
    response = client.put(
        "/workspace", json={"works_council_mode": enabled}, headers=_bearer(ADMIN)
    )
    assert response.status_code == 200, response.text
    assert response.json()["works_council_mode"] is enabled


def test_editor_cannot_toggle_works_council_mode(wc) -> None:
    _, client = wc
    _set_flag(client, True)
    response = client.put(
        "/workspace", json={"works_council_mode": False}, headers=_bearer(EDITOR)
    )
    assert response.status_code == 403
    editor_view = client.get("/workspace", headers=_bearer(EDITOR)).json()
    assert editor_view["works_council_mode"] is True
    # Benign fields stay editor-editable; merge keeps the flag intact.
    renamed = client.put(
        "/workspace", json={"name": "Walker WS"}, headers=_bearer(EDITOR)
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["works_council_mode"] is True
    assert renamed.json()["name"] == "Walker WS"


def _assert_no_person_fields(payload, where: str) -> None:
    """Structural check: any REDACTED_FIELDS key must hold its role label."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in REDACTED_FIELDS and isinstance(value, str) and value:
                assert value == REDACTED_FIELDS[key], (
                    f"{where}: field '{key}' holds {value!r} instead of the "
                    f"role label {REDACTED_FIELDS[key]!r}"
                )
            _assert_no_person_fields(value, f"{where}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _assert_no_person_fields(item, f"{where}[{index}]")


def _assert_clean_json_response(response, where: str) -> None:
    body = response.text
    for identifier in SEEDED_IDENTIFIERS:
        assert identifier not in body, f"{identifier!r} leaked in {where}"
    _assert_no_person_fields(response.json(), where)


def test_walker_every_get_endpoint_is_person_free_for_editor(wc) -> None:
    """The plan's acceptance test, verbatim: flag on, non-admin token, every
    read endpoint, no per-user performance-capable field in any response."""
    app, client = wc
    editor = _bearer(EDITOR)

    # Flag OFF first: prove the seeded identifiers ARE served to an editor —
    # a walker over data that never contained them would prove nothing.
    assert APPROVAL_REVIEWER in client.get("/approvals", headers=editor).text

    _set_flag(client, True)

    path_values = {
        "problem_id": PROBLEM_ID,
        "rule_id": client.get("/policy-rules", headers=editor).json()[0]["rule_id"],
        "customer_id": "CUST-0001",  # admin-only route; editor gets 403
        "entity": "problems",  # admin-only route; editor gets 403
    }

    get_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and "GET" in route.methods
    ]
    assert get_routes, "no GET routes enumerated from app.routes"

    covered_json: set[str] = set()
    for route in get_routes:
        params = re.findall(r"{(\w+)[^}]*}", route.path)
        missing = [name for name in params if name not in path_values]
        assert not missing, f"walker cannot fill path params {missing} for {route.path}"
        url = route.path
        for name in params:
            url = re.sub(rf"{{{name}[^}}]*}}", str(path_values[name]), url)

        response = client.get(url, headers=editor)
        assert response.status_code < 500, f"GET {url} -> {response.status_code}"
        if not (200 <= response.status_code < 300):
            continue  # admin-only surfaces 403 for the editor: not readable at all
        if not response.headers.get("content-type", "").startswith("application/json"):
            continue  # HTML/CSV variants are covered by dedicated tests below
        _assert_clean_json_response(response, f"GET {route.path}")
        covered_json.add(route.path)

    # The evidence pack defaults to HTML; its JSON variant must be walked too.
    pack_path = "/problems/{problem_id}/evidence-pack"
    pack = client.get(
        f"/problems/{PROBLEM_ID}/evidence-pack",
        params={"format": "json"},
        headers=editor,
    )
    assert pack.status_code == 200
    assert pack.headers["content-type"].startswith("application/json")
    _assert_clean_json_response(pack, f"GET {pack_path}?format=json")
    covered_json.add(pack_path)

    missing_coverage = REQUIRED_COVERAGE - covered_json
    assert not missing_coverage, (
        f"walker silently skipped person-bearing surfaces: {sorted(missing_coverage)}"
    )


def test_evidence_pack_html_is_redacted_for_editor(wc) -> None:
    """The one surface the JSON middleware cannot cover: the HTML rendering."""
    _, client = wc
    _set_flag(client, True)

    html = client.get(f"/problems/{PROBLEM_ID}/evidence-pack", headers=_bearer(EDITOR))
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    for identifier in SEEDED_IDENTIFIERS:
        assert identifier not in html.text
    assert "approver" in html.text  # approvals table shows the role label


def test_admin_keeps_full_identities_with_flag_on(wc) -> None:
    """Role-redacted for routine users, full identity for the designated admin
    role — the works-council agreement names who holds that access."""
    _, client = wc
    _set_flag(client, True)
    admin = _bearer(ADMIN)

    assert APPROVAL_REVIEWER in client.get("/approvals", headers=admin).text
    assert CANDIDATE_REVIEWER in client.get("/problem-candidates", headers=admin).text

    audit = client.get("/audit-export", headers=admin)
    assert audit.status_code == 200
    assert APPROVAL_REVIEWER in audit.text

    html = client.get(f"/problems/{PROBLEM_ID}/evidence-pack", headers=admin)
    assert APPROVAL_REVIEWER in html.text


def test_flag_off_keeps_identities_for_editor(wc) -> None:
    _, client = wc  # flag defaults to off
    editor = _bearer(EDITOR)

    assert APPROVAL_REVIEWER in client.get("/approvals", headers=editor).text
    assert CANDIDATE_REVIEWER in client.get("/problem-candidates", headers=editor).text
    workflow = client.get(f"/problems/{PROBLEM_ID}/workflow", headers=editor)
    assert CLOSURE_ACTOR in workflow.text


def test_redact_helper_boundaries() -> None:
    payload = {"reviewer": "anna@example.com", "note": "kept", "nested": [{"owner": "bob"}]}

    assert redact(payload, enabled=False, role="viewer") is payload  # flag off: no-op
    assert redact(payload, enabled=True, role="admin") is payload  # admin: no-op
    assert redact(payload, enabled=True, role="owner") is payload  # owner: no-op

    redacted = redact(payload, enabled=True, role="editor")
    assert redacted == {"reviewer": "approver", "note": "kept", "nested": [{"owner": "owner"}]}
    assert payload["reviewer"] == "anna@example.com"  # input not mutated
    # Unknown role fails closed.
    assert redact(payload, enabled=True, role=None)["reviewer"] == "approver"


def test_k_suppress_floor() -> None:
    ok = [{"group": "approvers", "count": 5}, {"group": "editors", "count": 9}]
    assert k_suppress(ok) == ok
    # ONE small group suppresses the whole table, not just the small row.
    assert k_suppress([*ok, {"group": "owners", "count": 4}]) == []
    assert k_suppress([]) == []
