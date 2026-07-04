"""Trustpilot Business connector (pull) — governed public listening, L2.

Fetches the customer's OWN business unit's public reviews through Trustpilot's
official API using the customer's own API key ("own-presence listening": the
product never scrapes; scraping violates Trustpilot ToS).

Config = {
    "api_key": "...",                # the customer's Trustpilot API key
    "business_unit_id": "...",       # their business unit id
    "last_synced_at": "...",          # optional incremental cursor (ISO)
}

GDPR stance (see business-ops/competitive/social-listening-plan.md): reviewer
display names are pseudonymized AT INGESTION — CLARA analyzes themes, never
people. The plaintext name is never stored.
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

API_BASE = "https://api.trustpilot.com/v1"
PER_PAGE = 100
MAX_PAGES = 20  # 2000 reviews per sync; the cursor makes later pulls cheap


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
        return True  # unparseable timestamps are kept; dedup catches repeats


class TrustpilotSourceConnector:
    """Pulls the customer's own Trustpilot reviews via their API key."""

    connector_type = "trustpilot"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        api_key = str(config.get("api_key", "")).strip()
        unit_id = str(config.get("business_unit_id", "")).strip()
        if not api_key or not unit_id:
            raise ConnectorError(
                "Missing api_key or business_unit_id", connector="trustpilot"
            )
        cursor = config.get("last_synced_at")

        signals: list[dict[str, Any]] = []
        latest = ""
        try:
            with httpx.Client(timeout=30.0) as client:
                for page in range(1, MAX_PAGES + 1):
                    resp = client.get(
                        f"{API_BASE}/business-units/{unit_id}/reviews",
                        params={
                            "page": page,
                            "perPage": PER_PAGE,
                            "orderBy": "createdat.desc",
                        },
                        headers={"apikey": api_key},
                    )
                    if resp.status_code in (401, 403):
                        raise ConnectorError(
                            "Trustpilot rejected the API key. Check the key in your"
                            " Trustpilot Business account.",
                            connector="trustpilot",
                            status=resp.status_code,
                        )
                    if resp.status_code == 404:
                        raise ConnectorError(
                            f"Business unit '{unit_id}' not found",
                            connector="trustpilot",
                            status=404,
                        )
                    if resp.status_code != 200:
                        raise ConnectorError(
                            f"Trustpilot API error {resp.status_code}",
                            connector="trustpilot",
                            status=resp.status_code,
                        )

                    reviews = resp.json().get("reviews") or []
                    if not reviews:
                        break

                    stop = False
                    for review in reviews:
                        created = str(review.get("createdAt") or "")
                        if created and not _after_cursor(created, cursor):
                            # createdat.desc: past the cursor means we're done.
                            stop = True
                            break
                        signal = self._map_review(review)
                        if signal:
                            signals.append(signal)
                            if created:
                                latest = max(latest, created)
                    if stop or len(reviews) < PER_PAGE:
                        break
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Trustpilot unreachable: {exc}", connector="trustpilot"
            ) from exc

        if signals and latest:
            signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = latest
        return signals

    def _map_review(self, review: dict[str, Any]) -> dict[str, Any] | None:
        review_id = str(review.get("id") or "")
        title = str(review.get("title") or "").strip()
        body = str(review.get("text") or "").strip()
        text = f"{title}\n{body}".strip() if title else body
        if not review_id or not text:
            return None

        consumer = review.get("consumer") or {}
        author = str(consumer.get("displayName") or "")
        stars = review.get("stars")
        return {
            "signal_id": f"tp-{review_id}",
            # Pseudonymized at ingestion — the reviewer's name is never stored.
            "customer_id": _pseudonym(author or review_id),
            "account_id": "public",
            "source": "trustpilot",
            "journey": "public_reviews",
            "journey_stage": "trustpilot",
            "campaign_exposure": [],
            "product_events": [],
            "feedback_text": text[:2000],
            "language": detect_language(text),
            "timestamp": str(review.get("createdAt") or "1970-01-01T00:00:00Z"),
            "metadata": {
                "rating": str(stars) if stars is not None else "",
                "location": str((consumer.get("displayLocation") or "")),
                "imported": "true",
            },
        }
