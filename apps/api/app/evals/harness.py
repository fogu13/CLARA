"""Evaluation harness — measures triage quality for the thesis.

This is thesis-critical: the MSc thesis requires measured evidence that the
agentic AI triage pipeline produces quality results. The eval harness runs
the enrichment and synthesis nodes against a golden set of labeled signals
and computes:

  - Classification precision/recall/F1 (sentiment, urgency, tags)
  - Synthesis quality (insight relevance, severity accuracy)
  - Hallucination checks (no fabricated evidence)
  - PII leak checks (no personal data in LLM outputs)
  - Latency tracking (time-to-enrichment, time-to-synthesis)

Golden set: a set of labeled signals where the "correct" enrichment is known.
The eval harness compares LLM output against the golden labels and scores it.

Usage:
  from app.evals.harness import EvalHarness
  harness = EvalHarness()
  results = harness.run_enrichment_eval()
  print(results.summary())
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from math import comb
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


@dataclass
class EvalResult:
    """Result of a single evaluation metric."""

    name: str
    value: float
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.name}: {self.value:.4f} — {self.detail}"


@dataclass
class EnrichmentEvalResult:
    """Results of enrichment evaluation against a golden set."""

    total_signals: int = 0
    correctly_classified: int = 0
    sentiment_accuracy: float = 0.0
    urgency_accuracy: float = 0.0
    tag_precision: float = 0.0
    tag_recall: float = 0.0
    tag_f1: float = 0.0
    # Strict exact-match tag scores, reported alongside the fuzzy primaries above.
    tag_precision_exact: float = 0.0
    tag_recall_exact: float = 0.0
    tag_f1_exact: float = 0.0
    hallucination_rate: float = 0.0
    pii_leak_count: int = 0
    avg_latency_ms: float = 0.0
    results: list[EvalResult] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "=== Enrichment Evaluation ===",
            f"Signals evaluated: {self.total_signals}",
            f"Sentiment accuracy: {self.sentiment_accuracy:.2%}",
            f"Urgency accuracy: {self.urgency_accuracy:.2%}",
            f"Tag precision: {self.tag_precision:.2%} (exact {self.tag_precision_exact:.2%})",
            f"Tag recall: {self.tag_recall:.2%} (exact {self.tag_recall_exact:.2%})",
            f"Tag F1: {self.tag_f1:.2%} (exact {self.tag_f1_exact:.2%})",
            f"Hallucination rate: {self.hallucination_rate:.2%}",
            f"PII leaks: {self.pii_leak_count}",
            f"Avg latency: {self.avg_latency_ms:.0f}ms",
        ]
        return "\n".join(lines)


@dataclass
class SynthesisEvalResult:
    """Results of synthesis evaluation."""

    total_insights: int = 0
    severity_accuracy: float = 0.0
    category_coverage: float = 0.0
    action_quality_score: float = 0.0
    avg_confidence: float = 0.0
    results: list[EvalResult] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "=== Synthesis Evaluation ===",
            f"Insights generated: {self.total_insights}",
            f"Severity accuracy: {self.severity_accuracy:.2%}",
            f"Category coverage: {self.category_coverage:.2%}",
            f"Action quality: {self.action_quality_score:.2%}",
            f"Avg confidence: {self.avg_confidence:.2f}",
        ]
        return "\n".join(lines)


def load_golden_set(split: str | None = None) -> list[dict[str, Any]]:
    """Load the golden set of labeled signals for evaluation.

    Pass split="optimization" (items the loop may tune on) or split="held_out"
    (locked guardrail set, never optimized against) to filter. Default returns
    all items.
    """
    if not GOLDEN_SET_PATH.exists():
        return []
    with open(GOLDEN_SET_PATH) as f:
        data = json.load(f)
    if split is not None:
        return [item for item in data if item.get("split") == split]
    return data


def _tag_tokens(tag: str) -> set[str]:
    """Tokens of a snake_case tag worth matching on (drops short filler tokens)."""
    return {t for t in tag.lower().split("_") if len(t) >= 4}


def _tags_match(a: str, b: str) -> bool:
    """Fuzzy tag equality: exact, or sharing a >=4-char token.

    # ponytail: lexical stem match — `payment_error` ~ `payment_failure` via the
    # shared `payment` token. Swap for embedding cosine if it proves too loose.
    """
    if a == b:
        return True
    return bool(_tag_tokens(a) & _tag_tokens(b))


def _precision_recall_f1(
    predicted: list[str],
    golden: list[str],
    *,
    fuzzy: bool = False,
) -> tuple[float, float, float]:
    """Compute precision, recall, and F1 for tag sets.

    With fuzzy=True a predicted/golden tag counts as matched when it shares a
    stem token with any tag on the other side (see _tags_match) — so a real
    LLM isn't zeroed for near-miss tags like payment_failure vs payment_error.
    """
    pred_set = set(predicted)
    golden_set = set(golden)

    if not pred_set and not golden_set:
        return 1.0, 1.0, 1.0

    if fuzzy:
        matched_pred = sum(1 for p in pred_set if any(_tags_match(p, g) for g in golden_set))
        matched_golden = sum(1 for g in golden_set if any(_tags_match(g, p) for p in pred_set))
        precision = matched_pred / len(pred_set) if pred_set else 0.0
        recall = matched_golden / len(golden_set) if golden_set else 0.0
    else:
        tp = len(pred_set & golden_set)
        fp = len(pred_set - golden_set)
        fn = len(golden_set - pred_set)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


PII_PATTERNS = [
    r"\b\S+@\S+\.\S+\b",  # email
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IP
    r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)",  # phone
]


def check_pii_leak(text: str) -> int:
    """Check if text contains PII patterns. Returns count of matches."""
    import re

    count = 0
    for pattern in PII_PATTERNS:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def check_hallucination(
    enrichment: dict[str, Any],
    original_text: str,
) -> bool:
    """Check if an enrichment contains fabricated information.

    A hallucination is defined as:
      - Tags that don't appear as substrings or semantic matches in the original text
      - Sentiment that contradicts obvious textual cues (e.g. "great" -> negative)

    This is a heuristic check — not a full hallucination detector, but catches
    obvious fabrication for the thesis evaluation.
    """
    tags = enrichment.get("tags", [])
    text_lower = original_text.lower()

    # Check that at least one tag has some connection to the text
    # (either as a substring or a reasonable semantic match)
    for tag in tags:
        tag_parts = tag.split("_")
        if any(part in text_lower for part in tag_parts if len(part) > 3):
            return False  # at least one tag is grounded

    # If no tags are grounded but tags exist, it might be a hallucination
    if tags and len(tags) > 0:
        return True

    return False


def bootstrap_ci(
    per_item: list[float],
    *,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 12345,
) -> tuple[float, float]:
    """Bootstrap confidence interval for the MEAN of per-item scores.

    Resamples the per-item scores (e.g. 0/1 correctness) with replacement to
    estimate uncertainty. On a 10-item golden set the CI is honestly wide
    (~±0.3) — that width is the point: it stops the loop chasing noise.
    Deterministic (fixed seed) so the eval is reproducible.
    """
    n = len(per_item)
    if n == 0:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(
        sum(per_item[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(n_resamples)
    )
    lo_i = int((1 - ci) / 2 * n_resamples)
    hi_i = min(n_resamples - 1, int((1 + ci) / 2 * n_resamples))
    return (means[lo_i], means[hi_i])


def mcnemar_exact(
    a_correct: list[bool],
    b_correct: list[bool],
) -> tuple[int, int, float]:
    """Exact McNemar test on two classifiers' PAIRED per-item correctness.

    Use to decide whether variant B is significantly better than A on the same
    items (the right test for tiny eval sets — far better than comparing raw
    accuracies). Returns (b, c, p_value):
      b = A right & B wrong, c = A wrong & B right,
      p = two-sided exact binomial(n=b+c, 0.5).
    A small p with c > b means B is significantly better.
    """
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return b, c, min(1.0, 2 * tail)


class EvalHarness:
    """Evaluation harness for the triage pipeline.

    Runs enrichment and synthesis against a golden set and computes metrics.
    Uses mocked LLM calls (via the golden set) so it works without a running
    LLM server — the golden set contains both the inputs AND the expected outputs.
    """

    def __init__(self, golden_set: list[dict[str, Any]] | None = None) -> None:
        self.golden_set = golden_set if golden_set is not None else load_golden_set()

    def run_enrichment_eval(
        self,
        *,
        enrichments: list[dict[str, Any]] | None = None,
    ) -> EnrichmentEvalResult:
        """Evaluate enrichment quality against the golden set.

        If enrichments are provided (from a real LLM run), compare them against
        the golden labels. If not, use the golden labels themselves to compute
        inter-rater agreement and metric definitions.
        """
        result = EnrichmentEvalResult(total_signals=len(self.golden_set))

        if not self.golden_set:
            return result

        sentiment_correct = 0
        urgency_correct = 0
        tag_precisions: list[float] = []
        tag_recalls: list[float] = []
        tag_precisions_exact: list[float] = []
        tag_recalls_exact: list[float] = []
        hallucination_count = 0
        pii_count = 0
        latencies: list[float] = []

        for item in self.golden_set:
            golden_enrichment = item.get("expected", {})
            # enrichments is None -> self-comparison mode (golden vs golden = 100%, the
            # metric-definition baseline). enrichments provided but MISSING this item ->
            # a real run dropped it: score against {} (wrong), never fall back to the
            # golden labels, which would silently inflate accuracy to 100%.
            if enrichments is None:
                actual_enrichment = golden_enrichment
            else:
                actual_enrichment = next(
                    (e for e in enrichments if e.get("id") == item["id"]), {}
                )

            # Sentiment accuracy
            if actual_enrichment.get("sentiment") == golden_enrichment.get("sentiment"):
                sentiment_correct += 1

            # Urgency accuracy
            if actual_enrichment.get("urgency") == golden_enrichment.get("urgency"):
                urgency_correct += 1

            # Tag precision/recall
            pred_tags = actual_enrichment.get("tags", [])
            golden_tags = golden_enrichment.get("tags", [])
            p, r, _ = _precision_recall_f1(pred_tags, golden_tags, fuzzy=True)
            tag_precisions.append(p)
            tag_recalls.append(r)
            pe, re_, _ = _precision_recall_f1(pred_tags, golden_tags, fuzzy=False)
            tag_precisions_exact.append(pe)
            tag_recalls_exact.append(re_)

            # Hallucination check
            if check_hallucination(actual_enrichment, item.get("text", "")):
                hallucination_count += 1

            # PII leak check
            pii_count += check_pii_leak(
                json.dumps(actual_enrichment)
            )

            # Simulated latency (real evals would measure actual call time)
            latencies.append(item.get("latency_ms", 150))

        n = len(self.golden_set)
        result.correctly_classified = sentiment_correct
        result.sentiment_accuracy = sentiment_correct / n if n > 0 else 0
        result.urgency_accuracy = urgency_correct / n if n > 0 else 0
        result.tag_precision = sum(tag_precisions) / n if n > 0 else 0
        result.tag_recall = sum(tag_recalls) / n if n > 0 else 0
        result.tag_f1 = (
            2 * result.tag_precision * result.tag_recall
            / (result.tag_precision + result.tag_recall)
            if (result.tag_precision + result.tag_recall) > 0
            else 0
        )
        result.tag_precision_exact = sum(tag_precisions_exact) / n if n > 0 else 0
        result.tag_recall_exact = sum(tag_recalls_exact) / n if n > 0 else 0
        result.tag_f1_exact = (
            2 * result.tag_precision_exact * result.tag_recall_exact
            / (result.tag_precision_exact + result.tag_recall_exact)
            if (result.tag_precision_exact + result.tag_recall_exact) > 0
            else 0
        )
        result.hallucination_rate = hallucination_count / n if n > 0 else 0
        result.pii_leak_count = pii_count
        result.avg_latency_ms = sum(latencies) / n if n > 0 else 0

        result.results = [
            EvalResult(
                "sentiment_accuracy",
                result.sentiment_accuracy,
                f"{sentiment_correct}/{n} correct",
            ),
            EvalResult(
                "urgency_accuracy",
                result.urgency_accuracy,
                f"{urgency_correct}/{n} correct",
            ),
            EvalResult("tag_precision", result.tag_precision),
            EvalResult("tag_recall", result.tag_recall),
            EvalResult("tag_f1", result.tag_f1),
            EvalResult(
                "hallucination_rate",
                result.hallucination_rate,
                f"{hallucination_count} flagged",
            ),
            EvalResult("pii_leaks", float(pii_count), f"{pii_count} matches"),
            EvalResult("avg_latency_ms", result.avg_latency_ms),
        ]

        return result

    def run_synthesis_eval(
        self,
        *,
        insights: list[dict[str, Any]] | None = None,
    ) -> SynthesisEvalResult:
        """Evaluate synthesis quality.

        Checks that insights cover expected categories, severity is computed
        deterministically (not LLM-set), and suggested actions are reasonable.
        """
        result = SynthesisEvalResult()

        # insights is None  -> legacy/offline self-comparison: derive from golden labels.
        # insights == []     -> a real run produced ZERO clusters: report that honestly,
        #                       never silently fabricate golden-set numbers.
        if insights is None:
            insights = [
                {
                    "category": item.get("expected", {}).get("category", "ux_friction"),
                    "severity": item.get("expected", {}).get("severity", "medium"),
                    "confidence": 0.8,
                    "suggested_actions": [{"type": "create_ticket"}],
                }
                for item in self.golden_set
            ]

        result.total_insights = len(insights)

        if not insights:
            return result

        # Category coverage
        expected_categories = {
            "ux_friction", "product_issue", "churn_risk", "campaign_performance",
        }
        actual_categories = {i.get("category", "") for i in insights}
        result.category_coverage = (
            len(actual_categories & expected_categories) / len(expected_categories)
        )

        # Severity accuracy (all severities should be from the deterministic function)
        severity_ok = sum(
            1 for i in insights
            if i.get("severity") in ("low", "medium", "high", "critical")
        )
        result.severity_accuracy = severity_ok / len(insights)

        # Action quality (actions should have type, title, description, priority)
        action_ok = sum(
            1 for i in insights
            for a in i.get("suggested_actions", [])
            if all(k in a for k in ("type", "title", "description", "priority"))
        )
        total_actions = sum(len(i.get("suggested_actions", [])) for i in insights)
        result.action_quality_score = action_ok / total_actions if total_actions > 0 else 0

        # Average confidence
        result.avg_confidence = sum(i.get("confidence", 0) for i in insights) / len(insights)

        result.results = [
            EvalResult("severity_accuracy", result.severity_accuracy),
            EvalResult("category_coverage", result.category_coverage),
            EvalResult("action_quality", result.action_quality_score),
            EvalResult("avg_confidence", result.avg_confidence),
        ]

        return result

    def run_full_eval(self) -> dict[str, Any]:
        """Run all evaluations and return a combined report."""
        enrichment = self.run_enrichment_eval()
        synthesis = self.run_synthesis_eval()

        return {
            "enrichment": {
                "sentiment_accuracy": enrichment.sentiment_accuracy,
                "urgency_accuracy": enrichment.urgency_accuracy,
                "tag_precision": enrichment.tag_precision,
                "tag_recall": enrichment.tag_recall,
                "tag_f1": enrichment.tag_f1,
                "tag_precision_exact": enrichment.tag_precision_exact,
                "tag_recall_exact": enrichment.tag_recall_exact,
                "tag_f1_exact": enrichment.tag_f1_exact,
                "hallucination_rate": enrichment.hallucination_rate,
                "pii_leak_count": enrichment.pii_leak_count,
                "avg_latency_ms": enrichment.avg_latency_ms,
            },
            "synthesis": {
                "severity_accuracy": synthesis.severity_accuracy,
                "category_coverage": synthesis.category_coverage,
                "action_quality": synthesis.action_quality_score,
                "avg_confidence": synthesis.avg_confidence,
            },
            "total_signals": enrichment.total_signals,
            "total_insights": synthesis.total_insights,
        }
