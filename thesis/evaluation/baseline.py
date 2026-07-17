"""Deterministic, transparent baselines for the enrichment fields.

These are lexicon/keyword classifiers (the pre-LLM tradition; Taboada et al., 2011).
They establish an honest FLOOR against which the LLM enrichment path (predict_llm.py)
is compared, and they require no API key, so the evaluation is reproducible offline.

Bilingual (EN + DE) because the corpus is English and German.
"""
from __future__ import annotations
import re

# --- Sentiment lexicon (polarity), EN + DE ----------------------------------
POS = {
    # EN
    "good", "great", "excellent", "love", "loved", "perfect", "easy", "fast",
    "reliable", "helpful", "best", "works", "working", "smooth", "happy",
    "recommend", "recommended", "intuitive", "satisfied", "amazing", "solid",
    "strong", "quick", "convenient", "clear", "nice", "awesome", "pleased",
    # DE
    "gut", "super", "toll", "perfekt", "einfach", "schnell", "zuverlässig",
    "hilfreich", "beste", "funktioniert", "zufrieden", "empfehlen", "klasse",
    "praktisch", "stark", "prima", "spitze", "gerne",
}
NEG = {
    # EN
    "bad", "terrible", "awful", "hate", "broken", "fail", "failed", "error",
    "errors", "slow", "crash", "crashes", "bug", "blocked", "locked", "frozen",
    "scam", "fraud", "stolen", "unauthorized", "refund", "cancelled", "canceled",
    "delay", "delayed", "missing", "lost", "worst", "useless", "frustrating",
    "disappointed", "wrong", "charged", "unable", "cannot", "problem", "issue",
    "complaint", "poor", "horrible", "rejected", "stuck", "ignored",
    # DE
    "schlecht", "schlimm", "fehler", "langsam", "abgelehnt", "gesperrt",
    "betrug", "problem", "probleme", "verloren", "storniert", "verspätung",
    "kaputt", "funktioniert nicht", "katastrophe", "enttäuscht", "unmöglich",
    "keine", "nicht", "mangelhaft", "ärgerlich", "miserabel",
}

# --- Risk/severity keywords (mapped to the gold {low,medium,high,critical}) ---
CRITICAL = {
    "fraud", "scam", "stolen", "unauthorized", "blocked", "locked", "frozen",
    "lost money", "can't access", "cannot access", "account closed", "no access",
    "betrug", "gesperrt", "kein zugriff", "konto gesperrt", "geld weg",
}
HIGH = {
    "refund", "failed", "failure", "error", "broken", "missing", "charged",
    "cancelled", "canceled", "crash", "delay", "not delivered", "wrong",
    "fehler", "storniert", "nicht geliefert", "verspätung", "kaputt", "abgelehnt",
}
MEDIUM = {
    "slow", "confusing", "unclear", "difficult", "hard", "complicated",
    "langsam", "unklar", "kompliziert", "schwierig",
}

_word = re.compile(r"[\wäöüß']+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _word.findall(text or "")]


def predict_sentiment(text: str) -> str:
    """Lexicon polarity with light negation handling -> negative|neutral|positive."""
    toks = _tokens(text)
    score = 0
    neg_window = 0
    negators = {"not", "no", "never", "nicht", "kein", "keine"}
    for t in toks:
        flip = -1 if neg_window > 0 else 1
        if t in POS:
            score += 1 * flip
        elif t in NEG:
            score -= 1 * flip
        neg_window = 2 if t in negators else max(0, neg_window - 1)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def predict_risk(text: str) -> str:
    """Keyword severity -> low|medium|high|critical (first match wins, strongest first)."""
    low = (text or "").lower()
    if any(k in low for k in CRITICAL):
        return "critical"
    if any(k in low for k in HIGH):
        return "high"
    if any(k in low for k in MEDIUM):
        return "medium"
    return "low"


def gold_sentiment_from_stars(star: int | None) -> str | None:
    """Independent sentiment gold from the 1-5 star rating (non-circular check)."""
    if star is None:
        return None
    if star <= 2:
        return "negative"
    if star == 3:
        return "neutral"
    return "positive"
