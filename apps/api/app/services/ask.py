"""Ask CLARA — scoped Q&A over the workspace's signals, with receipts.

The deliberate counter-design to a free-roaming chat assistant:
  - retrieval-grounded: the model sees ONLY the top-matching signal excerpts
  - every answer carries citations (signal ids) and a confidence score
  - explicit refusal when the evidence is thin — no confident hallucinations
  - one question, one answer: no memory, no persistent chat, no model switcher

Local-first retrieval: embeds the question + recent signals in one batch and
ranks by cosine similarity (same primitives as the taxonomy bootstrap). The
pgvector path can replace retrieval on DB-connected deployments later without
changing the contract.
"""

from __future__ import annotations

import logging
from typing import Any

# Live module reference (see taxonomy_bootstrap): test reloads of app.services.ai
# must not break exception identity or monkeypatching.
import app.services.ai as ai
from app.domain.models import SignalRecord
from app.services.semantic_taxonomy import cosine_sim
from app.services.taxonomies import searchable_text

logger = logging.getLogger(__name__)

MAX_SIGNALS = 500  # most recent; one embed batch
TOP_K = 8
MIN_MATCHES = 3  # fewer matching excerpts than this -> refuse
MIN_SIMILARITY = 0.30

ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "answer_question",
        "description": "Answer a question strictly from the provided customer-feedback excerpts",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Concise answer grounded ONLY in the excerpts; cite signal ids inline like [S-1]",
                },
                "confidence": {
                    "type": "number",
                    "description": "0-1: how well the excerpts support the answer",
                },
                "insufficient_evidence": {
                    "type": "boolean",
                    "description": "true when the excerpts do not contain enough information to answer",
                },
            },
            "required": ["answer", "confidence", "insufficient_evidence"],
        },
    },
}

SYSTEM_PROMPT = (
    "You answer questions about customer feedback using ONLY the numbered excerpts "
    "provided. Cite the excerpts you rely on by their signal id (e.g. [zd-101]). "
    "If the excerpts do not contain the answer, set insufficient_evidence=true and "
    "say what is missing instead of guessing. Never invent counts, dates or quotes."
)



def _recency_key(signal) -> str:
    """Chronological key that survives mixed Z / +02:00 / -07:00 timestamps
    (App Store reviews arrive with Apple's -07:00 offset)."""
    from datetime import datetime, timezone

    try:
        parsed = datetime.fromisoformat((signal.timestamp or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""

def _refusal(reason: str, matches: int) -> dict[str, Any]:
    return {
        "refused": True,
        "reason": reason,
        "matches": matches,
        "answer": None,
        "confidence": 0.0,
        "citations": [],
    }


def ask_clara(
    question: str,
    signals: list[SignalRecord],
    *,
    top_k: int = TOP_K,
    min_matches: int = MIN_MATCHES,
    min_similarity: float = MIN_SIMILARITY,
) -> dict[str, Any]:
    """Answer a question from signal evidence, or refuse honestly.

    Raises ai.AIProviderError upward (route maps it to 502) — a degraded answer
    is worse than a visible failure.
    """
    scoped = sorted(signals, key=_recency_key, reverse=True)[:MAX_SIGNALS]
    pairs = [(s, searchable_text(s)) for s in scoped]
    pairs = [(s, text) for s, text in pairs if text.strip()]
    if not pairs:
        return _refusal("No signals in the workspace yet.", 0)

    vectors = ai.embed([question, *[text for _, text in pairs]])
    question_vec, signal_vecs = vectors[0], vectors[1:]

    ranked = sorted(
        (
            (cosine_sim(question_vec, vec), signal)
            for vec, (signal, _) in zip(signal_vecs, pairs)
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    matches = [(score, signal) for score, signal in ranked[:top_k] if score >= min_similarity]

    if len(matches) < min_matches:
        return _refusal(
            "Not enough matching feedback to answer this reliably "
            f"({len(matches)} excerpt(s) above the similarity threshold).",
            len(matches),
        )

    excerpts = "\n".join(
        f"[{signal.signal_id}] ({signal.source}, {signal.language}, "
        f"{signal.timestamp[:10]}): {signal.feedback_text[:400]}"
        for _, signal in matches
    )
    result = ai.call_tool(
        system=SYSTEM_PROMPT,
        user=f"Question: {question}\n\nExcerpts:\n{excerpts}",
        tool=ANSWER_TOOL,
        tool_name="answer_question",
        trace_name="ask:answer",
    )

    if result.get("insufficient_evidence"):
        return _refusal("The matching feedback does not contain enough information to answer.", len(matches))

    retrieval_strength = sum(score for score, _ in matches) / len(matches)
    model_confidence = max(0.0, min(float(result.get("confidence", 0.0)), 1.0))

    return {
        "refused": False,
        "answer": result.get("answer", ""),
        # Overall confidence = the weaker of "how relevant was the evidence" and
        # "how sure was the model" — an answer can't be more trustworthy than its evidence.
        "confidence": round(min(model_confidence, retrieval_strength), 3),
        "model_confidence": round(model_confidence, 3),
        "retrieval_strength": round(retrieval_strength, 3),
        "matches": len(matches),
        "citations": [
            {
                "signal_id": signal.signal_id,
                "source": signal.source,
                "language": signal.language,
                "timestamp": signal.timestamp,
                "excerpt": signal.feedback_text[:200],
                "similarity": round(score, 3),
            }
            for score, signal in matches
        ],
    }
