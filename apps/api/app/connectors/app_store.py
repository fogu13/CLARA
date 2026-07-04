"""Apple App Store reviews connector (pull); governed public listening, L1.

Fetches customer reviews from Apple's public per-country review feed and maps
them to canonical signal dicts. No auth, no scraping: this is an Apple-provided
public JSON feed, the cleanest possible entry into organic feedback.

Config = {
    "app_id": "1279625243",          # the numeric App Store id
    "countries": "de,at,ch",         # comma-separated or list; default "de"
    "last_synced_at": "...",          # optional incremental cursor (ISO)
}

GDPR stance (see business-ops/competitive/social-listening-plan.md): reviewer
names are pseudonymized AT INGESTION — CLARA analyzes themes, never people.
The plaintext author name is never stored.
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

FEED_URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
MAX_PAGES_PER_COUNTRY = 10  # Apple caps the feed at 10 pages x 50 reviews


def _label(node: Any) -> str:
    """Apple's RSS-JSON wraps every value as {"label": ...}."""
    if isinstance(node, dict):
        return str(node.get("label", "") or "")
    return ""


def _pseudonym(author: str) -> str:
    """Stable pseudonym for a reviewer; the name itself is never stored."""
    digest = hashlib.sha256(author.encode("utf-8")).hexdigest()[:10]
    return f"rev-{digest}"


def _parse_countries(config: dict[str, Any]) -> list[str]:
    raw = config.get("countries") or "de"
    if isinstance(raw, str):
        parts = [part.strip().lower() for part in raw.split(",")]
    else:
        parts = [str(part).strip().lower() for part in raw]
    countries = [part for part in parts if part.isalpha() and len(part) == 2]
    if not countries:
        raise ConnectorError(
            "No valid country codes in 'countries' (expected e.g. 'de,at,ch')",
            connector="app_store",
        )
    return countries


def _after_cursor(timestamp: str, cursor: str | None) -> bool:
    if not cursor:
        return True
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        cut = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        return ts > cut
    except ValueError:
        return True  # unparseable timestamps are kept; dedup catches repeats


class AppStoreSourceConnector:
    """Pulls App Store reviews and maps them to canonical signal dicts."""

    connector_type = "app_store"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        app_id = str(config.get("app_id", "")).strip()
        if not app_id.isdigit():
            raise ConnectorError(
                "Missing or invalid app_id (the numeric App Store id)",
                connector="app_store",
            )
        countries = _parse_countries(config)
        cursor = config.get("last_synced_at")

        signals: list[dict[str, Any]] = []
        latest = ""
        try:
            with httpx.Client(timeout=30.0) as client:
                for country in countries:
                    for page in range(1, MAX_PAGES_PER_COUNTRY + 1):
                        url = FEED_URL.format(country=country, page=page, app_id=app_id)
                        resp = client.get(url, follow_redirects=True)
                        if resp.status_code == 404:
                            raise ConnectorError(
                                f"App {app_id} not found in the '{country}' App Store",
                                connector="app_store",
                                status=404,
                            )
                        if resp.status_code != 200:
                            raise ConnectorError(
                                f"App Store feed error {resp.status_code} for '{country}'",
                                connector="app_store",
                                status=resp.status_code,
                            )

                        entries = (resp.json().get("feed") or {}).get("entry") or []
                        if isinstance(entries, dict):  # RSS-JSON quirk: single entry = object
                            entries = [entries]
                        # Entries without a rating are app-metadata rows, not reviews.
                        reviews = [e for e in entries if _label(e.get("im:rating"))]
                        if not reviews:
                            break

                        stop_country = False
                        for entry in reviews:
                            updated = _label(entry.get("updated"))
                            if updated and not _after_cursor(updated, cursor):
                                # Feed is most-recent-first: past the cursor -> done here.
                                stop_country = True
                                break
                            signal = self._map_review(entry, country=country)
                            if signal:
                                signals.append(signal)
                                if updated:
                                    latest = max(latest, updated)
                        if stop_country:
                            break
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"App Store feed unreachable: {exc}", connector="app_store"
            ) from exc

        if signals and latest:
            signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = latest
        return signals

    def _map_review(self, entry: dict[str, Any], *, country: str) -> dict[str, Any] | None:
        review_id = _label(entry.get("id"))
        title = _label(entry.get("title"))
        content = _label(entry.get("content"))
        text = f"{title}\n{content}".strip() if title else content.strip()
        if not review_id or not text:
            return None

        author = _label((entry.get("author") or {}).get("name"))
        rating = _label(entry.get("im:rating"))
        return {
            "signal_id": f"as-{country}-{review_id}",
            # Pseudonymized at ingestion; the reviewer's name is never stored.
            "customer_id": _pseudonym(author or review_id),
            "account_id": "public",
            "source": f"app_store:{country}",
            "journey": "public_reviews",
            "journey_stage": "app_store",
            "campaign_exposure": [],
            "product_events": [],
            "feedback_text": text[:2000],
            "language": detect_language(text),
            "timestamp": _label(entry.get("updated")) or "1970-01-01T00:00:00Z",
            "metadata": {
                "rating": rating,
                "app_version": _label(entry.get("im:version")),
                "country": country,
                "imported": "true",
            },
        }
