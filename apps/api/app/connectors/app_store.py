"""Apple App Store reviews connector (pull); governed public listening, L1.

Fetches customer reviews from Apple's public per-country review feed and maps
them to canonical signal dicts. No auth, no scraping: this is an Apple-provided
public JSON feed, the cleanest possible entry into organic feedback.

Config = {
    "app_id": "1517121245",          # the numeric App Store id
    "countries": "de,at,ch",         # comma-separated or list; default "de,at,ch"
    "last_synced_at": "...",          # optional incremental cursor (ISO)
}

Field notes the retry logic encodes (verified against the live feed, Jul 2026):
the feed intermittently returns HTTP 200 with an entry-less body even when
reviews exist (so first-page emptiness is retried, not trusted); transient
403/429/5xx happen and resolve on retry; and the *German* storefront currently
serves no review entries at all — hence the "de,at,ch" default, so a
German-language app still gets coverage via AT/CH while DE is dark.

GDPR stance (see business-ops/competitive/social-listening-plan.md): reviewer
names are pseudonymized AT INGESTION — CLARA analyzes themes, never people.
The plaintext author name is never stored.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import ConnectorError
from app.services.common import normalize_timestamp
from app.services.language import detect_language

logger = logging.getLogger(__name__)

FEED_URL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
MAX_PAGES_PER_COUNTRY = 10  # Apple caps the feed at 10 pages x 50 reviews
FETCH_ATTEMPTS = 3  # per page: transient errors get the full budget
EMPTY_RETRY_ATTEMPTS = 2  # a 200-empty first page: retry once, then accept it
RETRY_WAIT_S = 1.0  # patched to 0 in tests
RETRYABLE_STATUSES = {403, 429, 500, 502, 503, 504}


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
    # Default includes AT/CH because the DE storefront currently serves no
    # review entries via this feed (see module docstring).
    raw = config.get("countries") or "de,at,ch"
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
        latest_by_country: dict[str, str] = {}
        dark: list[str] = []  # storefronts that answered 200 with no reviews
        try:
            with httpx.Client(timeout=30.0) as client:
                for country in countries:
                    country_reviews = 0
                    for page in range(1, MAX_PAGES_PER_COUNTRY + 1):
                        reviews = self._fetch_page(
                            client, app_id=app_id, country=country, page=page
                        )
                        if reviews is None:  # 404 past page 1: end of feed
                            break
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
                                country_reviews += 1
                                if updated:
                                    latest_by_country[country] = max(
                                        latest_by_country.get(country, ""), updated
                                    )
                        if stop_country:
                            break
                    if country_reviews == 0 and not cursor:
                        # First sync yielding nothing is suspicious, not normal —
                        # notably the DE storefront serves no entries at all.
                        dark.append(country)
                        logger.warning(
                            "app_store: 0 reviews from the '%s' storefront for app %s"
                            " (the 'de' feed currently serves no entries; consider"
                            " countries='de,at,ch')",
                            country,
                            app_id,
                        )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"App Store feed unreachable: {exc}", connector="app_store"
            ) from exc

        if signals and latest_by_country:
            # One shared cursor across countries: advance to the SLOWEST
            # country's newest review. max() would skip reviews in quieter
            # stores; min() never drops anything (dedup absorbs re-fetches).
            cursor_value = min(latest_by_country.values())
            signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = cursor_value

        if dark:
            # An entry-less 200 is indistinguishable from a genuinely
            # review-free app, so this can't be an error — but reporting it as a
            # contented "0 signals" sends people hunting for a bad app_id. Ride
            # the same side-channel as _sync_metadata; a note-only carrier when
            # nothing at all came back. Measured 2026-08-05: Apple served
            # entry-less 200s for every app tried (Instagram/WhatsApp included)
            # across de/at/ch/gb/us, so a total blank usually means Apple, not you.
            note = (
                f"App Store: the {', '.join(dark)} storefront(s) returned an empty feed"
                f" for app {app_id}. Apple's review feed serves entry-less responses"
                " intermittently — if the app does have written reviews, retry later."
            )
            if signals:
                signals[0]["_pull_note"] = note
            else:
                return [{"_pull_note": note}]
        return signals

    def _fetch_page(
        self, client: httpx.Client, *, app_id: str, country: str, page: int
    ) -> list[dict[str, Any]] | None:
        """Fetch one feed page with retries; returns review entries.

        Returns None for a 404 past page 1 (end of feed). Raises ConnectorError
        for a 404 on page 1 (app not in this storefront) and for persistent
        non-retryable errors. An empty-but-200 FIRST page is treated as a
        transient fault and retried (the live feed does this); deeper pages
        accept emptiness as the natural end.
        """
        url = FEED_URL.format(country=country, page=page, app_id=app_id)
        last_status: int | None = None
        for attempt in range(1, FETCH_ATTEMPTS + 1):
            if attempt > 1:
                time.sleep(RETRY_WAIT_S * (attempt - 1))
            try:
                resp = client.get(url, follow_redirects=True)
            except httpx.RequestError:
                if attempt == FETCH_ATTEMPTS:
                    raise
                continue
            last_status = resp.status_code
            if resp.status_code == 404:
                if page == 1:
                    raise ConnectorError(
                        f"App {app_id} not found in the '{country}' App Store",
                        connector="app_store",
                        status=404,
                    )
                return None
            if resp.status_code in RETRYABLE_STATUSES:
                continue
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
            if reviews or page > 1:
                return reviews
            # 200-but-empty first page: a transient feed fault OR a permanently
            # dark storefront (e.g. 'de'). Retry once; don't burn the full
            # error budget + cumulative sleeps on every sync of a dark store.
            if attempt >= EMPTY_RETRY_ATTEMPTS:
                return []
        if last_status in RETRYABLE_STATUSES:
            raise ConnectorError(
                f"App Store feed error {last_status} for '{country}'"
                f" after {FETCH_ATTEMPTS} attempts",
                connector="app_store",
                status=last_status,
            )
        return []  # first page stayed empty through all attempts

    def _map_review(self, entry: dict[str, Any], *, country: str) -> dict[str, Any] | None:
        review_id = _label(entry.get("id"))
        title = _label(entry.get("title"))
        content = _label(entry.get("content"))
        text = f"{title}\n{content}".strip() if title else content.strip()
        if not review_id or not text:
            return None

        author = _label((entry.get("author") or {}).get("name"))
        rating = _label(entry.get("im:rating"))
        timestamp, timestamp_defaulted = normalize_timestamp(_label(entry.get("updated")))
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
            "timestamp": timestamp,
            "metadata": {
                **({"timestamp_defaulted": "true"} if timestamp_defaulted else {}),
                "rating": rating,
                "app_version": _label(entry.get("im:version")),
                "country": country,
                "imported": "true",
            },
        }
