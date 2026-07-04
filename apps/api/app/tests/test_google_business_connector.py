"""Tests for L3b — Google Business Profile reviews connector."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.connectors.base import ConnectorError
from app.connectors.google_business import GoogleBusinessSourceConnector

PARENT = "accounts/123/locations/456"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVIEWS_URL = f"https://mybusiness.googleapis.com/v4/{PARENT}/reviews"

CONFIG = {
    "client_id": "cid",
    "client_secret": "sec",
    "refresh_token": "rt",
    "account_id": "123",
    "location_id": "456",
}


def _review(review_id: str, *, text: str, stars: str = "ONE", author: str = "Max M",
            anonymous: bool = False, updated: str = "2026-07-04T09:00:00Z") -> dict[str, Any]:
    return {
        "reviewId": review_id,
        "reviewer": {"displayName": author, "isAnonymous": anonymous},
        "starRating": stars,
        "comment": text,
        "createTime": updated,
        "updateTime": updated,
    }


def _mock_token(httpx_mock: Any) -> None:
    httpx_mock.add_response(url=TOKEN_URL, json={"access_token": "at-1"})


class TestConnector:
    def test_maps_and_pseudonymizes(self, httpx_mock: Any) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?pageSize=50",
            json={"reviews": [_review("r1", text="Die Filiale war unfreundlich und die Reklamation wurde ignoriert.")]},
        )
        signals = GoogleBusinessSourceConnector().pull(CONFIG)
        assert len(signals) == 1
        signal = signals[0]
        assert signal["signal_id"] == "gbp-r1"
        assert signal["source"] == "google_business"
        assert signal["language"] == "de"
        assert signal["metadata"]["rating"] == "1"  # enum ONE -> numeric
        assert "Max M" not in json.dumps(signal)
        assert signal["_sync_metadata"]["last_synced_at"] == "2026-07-04T09:00:00Z"

    def test_star_only_reviews_are_skipped_and_cursor_stops(self, httpx_mock: Any) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?pageSize=50",
            json={"reviews": [
                {"reviewId": "stars-only", "starRating": "FIVE", "comment": "",
                 "updateTime": "2026-07-04T10:00:00Z"},
                _review("new", text="Neue Beschwerde.", updated="2026-07-04T08:00:00Z"),
                _review("old", text="Alte Beschwerde.", updated="2026-06-01T08:00:00Z"),
            ]},
        )
        signals = GoogleBusinessSourceConnector().pull(
            {**CONFIG, "last_synced_at": "2026-07-01T00:00:00Z"}
        )
        assert [s["signal_id"] for s in signals] == ["gbp-new"]

    def test_anonymous_reviewer_pseudonym_from_review_id(self, httpx_mock: Any) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(
            url=f"{REVIEWS_URL}?pageSize=50",
            json={"reviews": [_review("anon1", text="Terrible service.", author="", anonymous=True)]},
        )
        signals = GoogleBusinessSourceConnector().pull(CONFIG)
        assert signals[0]["customer_id"].startswith("rev-")

    def test_error_paths(self, httpx_mock: Any) -> None:
        with pytest.raises(ConnectorError, match="Missing config"):
            GoogleBusinessSourceConnector().pull({"client_id": "x"})
        httpx_mock.add_response(url=TOKEN_URL, status_code=400)
        with pytest.raises(ConnectorError, match="rejected the OAuth credentials"):
            GoogleBusinessSourceConnector().pull(CONFIG)

    def test_permission_denied(self, httpx_mock: Any) -> None:
        _mock_token(httpx_mock)
        httpx_mock.add_response(url=f"{REVIEWS_URL}?pageSize=50", status_code=403)
        with pytest.raises(ConnectorError, match="must manage this location"):
            GoogleBusinessSourceConnector().pull(CONFIG)
