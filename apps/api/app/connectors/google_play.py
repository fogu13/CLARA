"""Google Play reviews connector (pull) — governed public listening, L3.

Fetches the customer's OWN app's Play Store reviews through the official
Play Developer API using the customer's own service account ("own-presence
listening": owner-only by design — the API only works for apps the service
account is granted access to in the customer's Play Console).

Config = {
    "package_name": "com.example.app",
    "service_account_json": "{...}",   # the full service-account key JSON
    "last_synced_at": "...",            # optional incremental cursor (ISO)
}

Caveat carried from Google's docs: the Reviews API primarily returns reviews
from the recent window (roughly the last week). With the hourly source sync
this is complete coverage going forward; historical backfill is a CSV job.

GDPR stance: author names are pseudonymized AT INGESTION — themes, not people.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import jwt

from app.connectors.base import ConnectorError, validate_external_url
from app.services.language import detect_language

logger = logging.getLogger(__name__)

API_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
MAX_RESULTS = 100
MAX_PAGES = 10


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


def _access_token(client: httpx.Client, service_account: dict[str, Any]) -> str:
    """Service-account OAuth: signed JWT grant, no SDK dependency."""
    try:
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": service_account["client_email"],
                "scope": SCOPE,
                "aud": service_account["token_uri"],
                "iat": now,
                "exp": now + 3600,
            },
            service_account["private_key"],
            algorithm="RS256",
        )
    except (KeyError, ValueError) as exc:
        raise ConnectorError(
            "Invalid service_account_json: missing or malformed key fields",
            connector="google_play",
        ) from exc

    # token_uri comes from the admin-supplied service-account JSON; guard it
    # like jira's base URL so a malicious/misconfigured account can't make the
    # server POST the signed assertion at an internal/metadata host (SSRF).
    token_uri = validate_external_url(
        service_account["token_uri"], connector="google_play"
    )
    response = client.post(
        token_uri,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
    )
    if response.status_code != 200:
        raise ConnectorError(
            "Google rejected the service account credentials. Check that the"
            " account is linked in the Play Console with 'View app information'.",
            connector="google_play",
            status=response.status_code,
        )
    token = response.json().get("access_token")
    if not token:
        raise ConnectorError("Google returned no access token", connector="google_play")
    return token


class GooglePlaySourceConnector:
    """Pulls the customer's own Play Store reviews via their service account."""

    connector_type = "google_play"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        package = str(config.get("package_name", "")).strip()
        raw_account = config.get("service_account_json") or ""
        if not package or not raw_account:
            raise ConnectorError(
                "Missing package_name or service_account_json", connector="google_play"
            )
        try:
            service_account = (
                raw_account if isinstance(raw_account, dict) else json.loads(raw_account)
            )
        except ValueError as exc:
            raise ConnectorError(
                "service_account_json is not valid JSON", connector="google_play"
            ) from exc
        cursor = config.get("last_synced_at")

        signals: list[dict[str, Any]] = []
        latest = ""
        try:
            with httpx.Client(timeout=30.0) as client:
                token = _access_token(client, service_account)
                page_token: str | None = None
                for _ in range(MAX_PAGES):
                    params: dict[str, Any] = {"maxResults": MAX_RESULTS}
                    if page_token:
                        params["token"] = page_token
                    resp = client.get(
                        f"{API_BASE}/applications/{package}/reviews",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code in (401, 403):
                        raise ConnectorError(
                            "Play API access denied: link the service account to this"
                            " app in the Play Console (Users and permissions).",
                            connector="google_play",
                            status=resp.status_code,
                        )
                    if resp.status_code == 404:
                        raise ConnectorError(
                            f"App '{package}' not found for this service account",
                            connector="google_play",
                            status=404,
                        )
                    if resp.status_code != 200:
                        raise ConnectorError(
                            f"Play API error {resp.status_code}",
                            connector="google_play",
                            status=resp.status_code,
                        )

                    body = resp.json()
                    stop = False
                    for review in body.get("reviews") or []:
                        signal = self._map_review(review, package=package)
                        if signal is None:
                            continue
                        if not _after_cursor(signal["timestamp"], cursor):
                            stop = True
                            continue  # reviews are not strictly ordered; keep scanning the page
                        signals.append(signal)
                        latest = max(latest, signal["timestamp"])

                    page_token = (body.get("tokenPagination") or {}).get("nextPageToken")
                    if stop or not page_token:
                        break
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Play API unreachable: {exc}", connector="google_play"
            ) from exc

        if signals and latest:
            signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = latest
        return signals

    def _map_review(self, review: dict[str, Any], *, package: str) -> dict[str, Any] | None:
        review_id = str(review.get("reviewId") or "")
        comments = review.get("comments") or []
        user_comment = next(
            (c.get("userComment") for c in comments if c.get("userComment")), None
        )
        if not review_id or not user_comment:
            return None
        text = str(user_comment.get("text") or "").strip()
        if not text:
            return None

        seconds = (user_comment.get("lastModified") or {}).get("seconds")
        try:
            timestamp = (
                datetime.fromtimestamp(int(seconds), tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except (TypeError, ValueError):
            timestamp = "1970-01-01T00:00:00Z"

        reviewer_language = str(user_comment.get("reviewerLanguage") or "")[:2].lower()
        language = reviewer_language if reviewer_language in ("de", "en") else detect_language(text)
        rating = user_comment.get("starRating")
        author = str(review.get("authorName") or "")
        return {
            "signal_id": f"gp-{review_id}",
            # Pseudonymized at ingestion — the reviewer's name is never stored.
            "customer_id": _pseudonym(author or review_id),
            "account_id": "public",
            "source": "google_play",
            "journey": "public_reviews",
            "journey_stage": "google_play",
            "campaign_exposure": [],
            "product_events": [],
            "feedback_text": text[:2000],
            "language": language,
            "timestamp": timestamp,
            "metadata": {
                "rating": str(rating) if rating is not None else "",
                "app_version": str(user_comment.get("appVersionName") or ""),
                "device": str(user_comment.get("device") or ""),
                "package": package,
                "imported": "true",
            },
        }
