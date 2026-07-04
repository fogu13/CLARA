"""Google Business Profile reviews connector (pull) — governed listening, L3b.

Fetches the customer's OWN location's Google reviews through the official
Business Profile API using the customer's own OAuth credentials (the
business.manage scope only works for locations the authorizing account
manages — owner-only by design).

Config = {
    "client_id": "...",           # the customer's OAuth client
    "client_secret": "...",
    "refresh_token": "...",       # from a one-time consent for business.manage
    "account_id": "123",          # Business Profile account number
    "location_id": "456",         # location number
    "last_synced_at": "...",       # optional incremental cursor (ISO)
}

GDPR stance: reviewer display names are pseudonymized AT INGESTION; anonymous
reviewers stay anonymous. Themes, not people.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import ConnectorError
from app.services.language import detect_language

logger = logging.getLogger(__name__)

API_BASE = "https://mybusiness.googleapis.com/v4"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PAGE_SIZE = 50  # API maximum
MAX_PAGES = 20

STAR_VALUES = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5"}


def _pseudonym(author: str) -> str:
    digest = hashlib.sha256(author.encode("utf-8")).hexdigest()[:10]
    return f"rev-{digest}"


def _after_cursor(timestamp: str, cursor: str | None) -> bool:
    if not cursor:
        return True
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        cut = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        return ts > cut
    except ValueError:
        return True


def _access_token(client: httpx.Client, config: dict[str, Any]) -> str:
    response = client.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": config["refresh_token"],
        },
    )
    if response.status_code != 200:
        raise ConnectorError(
            "Google rejected the OAuth credentials. Re-run the one-time consent"
            " for the business.manage scope and update the refresh token.",
            connector="google_business",
            status=response.status_code,
        )
    token = response.json().get("access_token")
    if not token:
        raise ConnectorError("Google returned no access token", connector="google_business")
    return token


class GoogleBusinessSourceConnector:
    """Pulls the customer's own Google reviews via their OAuth credentials."""

    connector_type = "google_business"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        required = ("client_id", "client_secret", "refresh_token", "account_id", "location_id")
        missing = [key for key in required if not str(config.get(key, "")).strip()]
        if missing:
            raise ConnectorError(
                f"Missing config: {', '.join(missing)}", connector="google_business"
            )
        cursor = config.get("last_synced_at")
        parent = f"accounts/{config['account_id']}/locations/{config['location_id']}"

        signals: list[dict[str, Any]] = []
        latest = ""
        try:
            with httpx.Client(timeout=30.0) as client:
                token = _access_token(client, config)
                page_token: str | None = None
                for _ in range(MAX_PAGES):
                    params: dict[str, Any] = {"pageSize": PAGE_SIZE}
                    if page_token:
                        params["pageToken"] = page_token
                    resp = client.get(
                        f"{API_BASE}/{parent}/reviews",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code in (401, 403):
                        raise ConnectorError(
                            "Business Profile access denied: the authorizing account"
                            " must manage this location.",
                            connector="google_business",
                            status=resp.status_code,
                        )
                    if resp.status_code == 404:
                        raise ConnectorError(
                            f"Location '{parent}' not found", connector="google_business", status=404
                        )
                    if resp.status_code != 200:
                        raise ConnectorError(
                            f"Business Profile API error {resp.status_code}",
                            connector="google_business",
                            status=resp.status_code,
                        )

                    body = resp.json()
                    stop = False
                    for review in body.get("reviews") or []:
                        signal = self._map_review(review, location=parent)
                        if signal is None:
                            continue
                        if not _after_cursor(signal["timestamp"], cursor):
                            # Default order is updateTime desc: past the cursor -> done.
                            stop = True
                            break
                        signals.append(signal)
                        latest = max(latest, signal["timestamp"])

                    page_token = body.get("nextPageToken")
                    if stop or not page_token:
                        break
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Business Profile API unreachable: {exc}", connector="google_business"
            ) from exc

        if signals and latest:
            signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = latest
        return signals

    def _map_review(self, review: dict[str, Any], *, location: str) -> dict[str, Any] | None:
        review_id = str(review.get("reviewId") or "")
        text = str(review.get("comment") or "").strip()
        if not review_id or not text:
            return None  # star-only reviews carry no analyzable feedback

        reviewer = review.get("reviewer") or {}
        author = "" if reviewer.get("isAnonymous") else str(reviewer.get("displayName") or "")
        rating = STAR_VALUES.get(str(review.get("starRating") or ""), "")
        timestamp = str(review.get("updateTime") or review.get("createTime") or "1970-01-01T00:00:00Z")
        return {
            "signal_id": f"gbp-{review_id[:64]}",
            # Pseudonymized at ingestion — the reviewer's name is never stored.
            "customer_id": _pseudonym(author or review_id),
            "account_id": "public",
            "source": "google_business",
            "journey": "public_reviews",
            "journey_stage": "google_business",
            "campaign_exposure": [],
            "product_events": [],
            "feedback_text": text[:2000],
            "language": detect_language(text),
            "timestamp": timestamp,
            "metadata": {
                "rating": rating,
                "location": location,
                "imported": "true",
            },
        }
