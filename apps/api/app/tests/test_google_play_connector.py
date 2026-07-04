"""Tests for L3 — Google Play reviews connector (owner service account)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.connectors.base import ConnectorError
from app.connectors.google_play import GooglePlaySourceConnector

PACKAGE = "com.example.app"
TOKEN_URL = "https://oauth2.example.com/token"
REVIEWS_URL = (
    f"https://androidpublisher.googleapis.com/androidpublisher/v3"
    f"/applications/{PACKAGE}/reviews"
)


@pytest.fixture(scope="module")
def service_account() -> dict[str, Any]:
    # Throwaway RSA key so the JWT grant signs offline.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return {
        "client_email": "smoke@project.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": TOKEN_URL,
    }


def _config(service_account: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "package_name": PACKAGE,
        "service_account_json": json.dumps(service_account),
        **extra,
    }


def _review(review_id: str, *, text: str, stars: int = 1, seconds: int = 1783152000,
            language: str = "de", author: str = "Max M") -> dict[str, Any]:
    return {
        "reviewId": review_id,
        "authorName": author,
        "comments": [{
            "userComment": {
                "text": text,
                "starRating": stars,
                "lastModified": {"seconds": str(seconds)},
                "reviewerLanguage": language,
                "appVersionName": "3.2.1",
                "device": "oriole",
            }
        }],
    }


def _mock_token(httpx_mock: Any) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json={"access_token": "at-123"})


class TestConnector:
    def test_maps_and_pseudonymizes(self, httpx_mock: Any, service_account: dict) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?maxResults=100",
            json={"reviews": [_review("r1", text="Anmeldung schlägt seit dem Update fehl.")]},
        )
        signals = GooglePlaySourceConnector().pull(_config(service_account))
        assert len(signals) == 1
        signal = signals[0]
        assert signal["signal_id"] == "gp-r1"
        assert signal["source"] == "google_play"
        assert signal["language"] == "de"  # reviewerLanguage wins
        assert signal["metadata"]["rating"] == "1"
        assert signal["timestamp"].endswith("Z")
        assert "Max M" not in json.dumps(signal)
        assert signal["customer_id"].startswith("rev-")
        assert signal["_sync_metadata"]["last_synced_at"] == signal["timestamp"]

    def test_cursor_skips_old_reviews(self, httpx_mock: Any, service_account: dict) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?maxResults=100",
            json={"reviews": [
                _review("new", text="Neues Problem mit Benachrichtigungen.", seconds=1783152000),
                _review("old", text="Altes Problem.", seconds=1780300800),
            ]},
        )
        signals = GooglePlaySourceConnector().pull(
            _config(service_account, last_synced_at="2026-07-03T00:00:00Z")
        )
        assert [s["signal_id"] for s in signals] == ["gp-new"]

    def test_reviews_without_text_are_skipped(self, httpx_mock: Any, service_account: dict) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?maxResults=100",
            json={"reviews": [
                {"reviewId": "silent", "authorName": "X", "comments": [{"userComment": {"text": "", "starRating": 5}}]},
                _review("r2", text="Crashes on startup since yesterday.", language="en"),
            ]},
        )
        signals = GooglePlaySourceConnector().pull(_config(service_account))
        assert [s["signal_id"] for s in signals] == ["gp-r2"]
        assert signals[0]["language"] == "en"

    def test_credential_errors_are_actionable(self, httpx_mock: Any, service_account: dict) -> None:
        with pytest.raises(ConnectorError, match="Missing package_name"):
            GooglePlaySourceConnector().pull({"package_name": "", "service_account_json": "{}"})
        with pytest.raises(ConnectorError, match="not valid JSON"):
            GooglePlaySourceConnector().pull(
                {"package_name": PACKAGE, "service_account_json": "not-json"}
            )
        httpx_mock.add_response(url=TOKEN_URL, status_code=401)
        with pytest.raises(ConnectorError, match="rejected the service account"):
            GooglePlaySourceConnector().pull(_config(service_account))

    def test_api_permission_error(self, httpx_mock: Any, service_account: dict) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{REVIEWS_URL}?maxResults=100", status_code=403)
        with pytest.raises(ConnectorError, match="link the service account"):
            GooglePlaySourceConnector().pull(_config(service_account))
