"""Regression tests for the security-review fixes: read-endpoint auth gating +
connector SSRF guards."""

from __future__ import annotations

import importlib
import os

import pytest

from app.connectors import get_source
from app.connectors.base import ConnectorError, validate_external_url
from app.tests.test_api_rbac import make_auth_client, token


@pytest.fixture(autouse=True)
def _reset_auth_modules():
    """make_auth_client enables auth by reloading modules with a JWT secret set;
    reset to the auth-disabled default afterwards so no later test file inherits
    a gated (401-ing) app. Pop the env ourselves — do not rely on monkeypatch
    teardown ordering."""
    yield
    os.environ.pop("SUPABASE_JWT_SECRET", None)
    import app.auth
    import app.main
    import app.rate_limit
    import app.rbac
    for mod in (app.auth, app.rbac, app.rate_limit, app.main):
        importlib.reload(mod)


class TestReadEndpointsRequireAuth:
    """With auth enabled, GET data endpoints must reject unauthenticated reads."""

    def test_reads_rejected_without_token(self, monkeypatch) -> None:
        client = make_auth_client(monkeypatch)
        for path in ("/signals", "/problems", "/outcome-board", "/approvals",
                     "/taxonomies", "/emerging-problems", "/jira-drafts"):
            assert client.get(path).status_code == 401, f"{path} should require auth"

    def test_health_stays_public(self, monkeypatch) -> None:
        client = make_auth_client(monkeypatch)
        assert client.get("/health").status_code == 200

    def test_viewer_token_can_read(self, monkeypatch) -> None:
        client = make_auth_client(monkeypatch)
        headers = {"Authorization": f"Bearer {token('viewer')}"}
        assert client.get("/signals", headers=headers).status_code == 200
        assert client.get("/problems", headers=headers).status_code == 200


class TestSsrfGuard:
    def test_blocks_internal_and_metadata_hosts(self) -> None:
        for bad in (
            "http://169.254.169.254/latest/meta-data/",  # cloud metadata
            "http://127.0.0.1/admin",
            "http://10.1.2.3/",
            "http://192.168.0.1/",
            "http://[::1]/",
            "http://localhost/x",
            "http://db.internal/",
            "file:///etc/passwd",
            "gopher://127.0.0.1/",
        ):
            with pytest.raises(ConnectorError):
                validate_external_url(bad, connector="jira")

    def test_allows_normal_public_https(self) -> None:
        assert validate_external_url("https://company.atlassian.net", connector="jira")

    def test_zendesk_rejects_subdomain_injection(self) -> None:
        src = get_source("zendesk")
        assert src is not None
        for bad_sub in ("evil.com/", "a.b", "169.254.169.254", "x@y"):
            with pytest.raises(ConnectorError):
                src.pull({"subdomain": bad_sub, "email": "a@b.c", "api_token": "t"})
