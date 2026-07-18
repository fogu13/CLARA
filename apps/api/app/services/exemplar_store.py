"""Few-shot exemplars for enrichment — teach the label vocabulary + urgency calibration.

GLM 5.2 (and any model) invents its own tag wording (`checkout_crash` vs the
canonical `checkout_failure`), which tanks exact tag-match and fragments
clustering. A handful of labelled reference examples in the prompt pins the model
to the project's vocabulary and urgency rubric.

Model-agnostic by design: exemplars are plain prompt text, so they work with ANY
OpenAI-compatible chat model (cloud or local) and need NO embeddings endpoint —
important since some gateways (e.g. OpenCode Zen) are chat-only. The set is
curated for coverage across sentiments, urgencies, and tag styles, and is kept
distinct from golden_set.json so there is no train/test leakage.

Upgrade path (Phase B+): per-workspace exemplar stores with embedding-based
(Set-BSR coverage) selection, once an embeddings provider is configured.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Coverage-balanced across sentiment (pos/neg/neutral/mixed) and urgency
# (low/medium/high/critical). Scenarios are deliberately different from the
# golden set; only the *conventions* (snake_case `_failure`/`_error`/`_concern`,
# `positive_trend` for praise, `churn_risk` for cancellation intent) are taught.
DEFAULT_EXEMPLARS: list[dict[str, Any]] = [
    {"text": "The signup button does nothing when I click it — I cannot create an account.",
     "sentiment": "negative", "urgency": "high",
     "tags": ["signup_failure", "broken_button"]},
    {"text": "Honestly the best release yet — the new keyboard shortcuts make me twice as fast.",
     "sentiment": "positive", "urgency": "low",
     "tags": ["positive_trend", "keyboard_shortcuts"]},
    {"text": "Cancel my account. Three outages this month and we've lost trust completely.",
     "sentiment": "negative", "urgency": "critical",
     "tags": ["churn_risk", "service_outage"]},
    {"text": "The migration was painful and poorly documented, but it works well now.",
     "sentiment": "mixed", "urgency": "medium",
     "tags": ["migration_friction", "documentation_gap"]},
    {"text": "Is there a way to schedule reports to send automatically each week?",
     "sentiment": "neutral", "urgency": "low",
     "tags": ["scheduling_question"]},
    {"text": "Why am I being shown ads for the enterprise plan when I'm already on it?",
     "sentiment": "negative", "urgency": "medium",
     "tags": ["irrelevant_campaign", "targeting_error"]},
    {"text": "I can see another customer's invoices in my billing page — a serious privacy breach.",
     "sentiment": "negative", "urgency": "critical",
     "tags": ["security_concern", "data_breach"]},
    # Churn-musing calibration (eval 2026-07-17, eval-077-class disputes):
    # CONDITIONAL, future-tense leaving talk is medium — only explicit,
    # decided cancellation (exemplar above) is critical. Fresh text, no
    # golden-set leakage.
    {"text": "If the reporting module stays this slow after the next release, we'll "
             "probably have to look around for something else eventually.",
     "sentiment": "negative", "urgency": "medium",
     "tags": ["performance_degradation", "churn_risk"]},
    # German coverage (eval 2026-07-17: DE urgency 80% vs EN 86.7%; the set was
    # EN-only). Teaches the critical-vs-high rule (unrecoverable loss happening
    # now = critical) and the positive_trend praise-tag convention on German
    # text. Fresh texts — deliberately NOT golden-set items (no leakage).
    {"text": "Die Abbuchung ist erfolgt, aber mein Guthaben ist verschwunden und ich komme nicht "
             "mehr in mein Konto — seit zwei Tagen antwortet niemand.",
     "sentiment": "negative", "urgency": "critical",
     "tags": ["payment_error", "account_access"]},
    {"text": "Kompliment an das Team: Die neue Suche ist deutlich schneller und der Support hat "
             "meine Frage in wenigen Minuten gelöst.",
     "sentiment": "positive", "urgency": "low",
     "tags": ["positive_trend", "good_support"]},
]


def fewshot_enabled() -> bool:
    """Few-shot exemplars are on by default; disable with ENRICH_FEWSHOT=0."""
    return os.getenv("ENRICH_FEWSHOT", "1").lower() not in ("0", "false", "no", "")


def load_exemplars() -> list[dict[str, Any]]:
    """Return the active exemplar set (curated default; per-workspace later)."""
    return DEFAULT_EXEMPLARS


def format_fewshot(exemplars: list[dict[str, Any]]) -> str:
    """Render exemplars as a few-shot block to prepend to the enrichment prompt."""
    lines = [
        "Reference examples of correctly-labelled feedback. Reuse this tag "
        "vocabulary (concise snake_case naming the concrete problem) and urgency "
        "calibration:"
    ]
    for ex in exemplars:
        lines.append(
            f'\nFeedback: "{ex["text"]}"'
            f'\n-> sentiment: {ex["sentiment"]}, urgency: {ex["urgency"]}, '
            f'tags: {json.dumps(ex["tags"])}'
        )
    return "\n".join(lines)
