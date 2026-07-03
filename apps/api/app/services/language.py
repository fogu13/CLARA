"""Language detection for ingested feedback — DE/EN, dependency-free.

DACH pilots paste German tickets; the CSV path defaulted language to "unknown"
and the Zendesk connector hardcoded "en", so German handling (terminology
matching, language notes, DE readiness reporting) never fired on real pulls.

A stopword/marker heuristic is deliberate: it needs no model call, no new
dependency, and DE-vs-EN is the only distinction the product acts on today.
ponytail: returns "en" for anything non-German; add langdetect/lingua when a
third market language actually matters.
"""

from __future__ import annotations

import re

# High-frequency German function words that are rare in English text.
_DE_STOPWORDS = frozenset(
    "der die das und ist nicht ich ein eine einen dem den ohne mit für auf aus"
    " bei nach wird wurde werden kann keine kein mein meine sehr auch noch"
    " schon aber wenn dann seit gibt haben hatte bitte danke leider funktioniert"
    " geht immer wieder seite konto zahlung bestellung rechnung kündigen".split()
)
# Characters that only occur in German (among DE/EN).
_DE_CHARS = re.compile(r"[äöüßÄÖÜ]")

_WORD = re.compile(r"[a-zA-ZäöüßÄÖÜ]+")


def detect_language(text: str, *, default: str = "en") -> str:
    """Return "de" when the text reads as German, else the default ("en")."""
    if not text or not text.strip():
        return default

    if _DE_CHARS.search(text):
        return "de"

    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < 3:
        return default

    de_hits = sum(1 for w in words if w in _DE_STOPWORDS)
    # ≥15% German function words is far above chance for English text.
    return "de" if de_hits / len(words) >= 0.15 else default
