"""Selective-prediction + citation-entailment eval for Ask CLARA (R9/F10).

/ask's signature feature is refusing instead of guessing, and capping its
confidence by retrieval strength — but neither the refusal threshold nor the
confidence has ever been validated against outcomes. This harness measures:

1. **Selective prediction**: over an authored QA set (answerable questions
   whose evidence lives in the demo datasets + unanswerable ones whose topic
   appears nowhere), sweep the confidence threshold and report the
   coverage/accuracy curve. "Accuracy" is programmatic: an answerable question
   is right when it answers AND cites at least one signal from the dataset that
   holds the evidence; an unanswerable one is right when it refuses. This
   validates the REFUSAL system, deliberately not free-text answer quality.
2. **Citation entailment (LLM-judge)**: for each answered question, a judge
   model checks per citation whether the cited excerpt actually supports the
   answer. Reported as a rate with its LLM-judge caveat attached — treat it as
   a smoke alarm, not a proof.

Run:  cd apps/api && python3 -m scripts.ask_eval
Needs AI_* configured (chat + embeddings). Writes app/evals/ask_eval.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import SignalRecord
from app.services import ai
from app.services.ask import ask_clara

EVALS_DIR = Path(__file__).resolve().parents[1] / "app" / "evals"
DEMO_DIR = Path(__file__).resolve().parents[3] / "data" / "demo_datasets"
OUT_PATH = EVALS_DIR / "ask_eval.json"

# Answerable: the topic demonstrably exists in the named demo dataset.
# Unanswerable: the topic appears in none of them — the only right move is refusal.
QA_SET: list[dict] = [
    {"q": "What is going wrong with identity verification?", "expect": "answer",
     "dataset": "fintech_identity"},
    {"q": "Was sagen Kund:innen über die Identitätsprüfung?", "expect": "answer",
     "dataset": "fintech_identity"},
    {"q": "Are customers complaining about card payments at checkout?", "expect": "answer",
     "dataset": "ecommerce_checkout"},
    {"q": "Why are cancelled customers still being contacted?", "expect": "answer",
     "dataset": "retention_cancellation"},
    {"q": "What problems do customers report during onboarding verification?", "expect": "answer",
     "dataset": "saas_onboarding"},
    {"q": "What do customers think about our loyalty points program?", "expect": "refuse"},
    {"q": "Are there complaints about the mobile app crashing on Android 15?", "expect": "refuse"},
    {"q": "How do customers rate our phone support wait times in France?", "expect": "refuse"},
    {"q": "What feedback exists about the new dark-mode design?", "expect": "refuse"},
]

JUDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "judge_citation",
        "parameters": {
            "type": "object",
            "properties": {
                "supported": {"type": "boolean",
                              "description": "true only if the excerpt supports the answer"},
            },
            "required": ["supported"],
        },
    },
}


def _load_signals() -> tuple[list[SignalRecord], dict[str, str]]:
    signals: list[SignalRecord] = []
    dataset_of: dict[str, str] = {}
    for path in sorted(DEMO_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        for raw in data.get("signals", []):
            record = SignalRecord.model_validate(raw)
            signals.append(record)
            dataset_of[record.signal_id] = data.get("dataset_id", path.stem)
    return signals, dataset_of


def _grade(item: dict, result: dict, dataset_of: dict[str, str]) -> bool:
    if item["expect"] == "refuse":
        return bool(result.get("refused"))
    if result.get("refused"):
        return False
    cited_datasets = {dataset_of.get(c["signal_id"]) for c in result.get("citations", [])}
    return item["dataset"] in cited_datasets


def _entailment(answer: str, citations: list[dict]) -> tuple[int, int]:
    supported = 0
    for citation in citations:
        verdict = ai.call_tool(
            system=("You verify citations. Given an ANSWER about customer feedback and one "
                    "cited EXCERPT, decide whether the excerpt genuinely supports the answer. "
                    "Topical overlap is not support."),
            user=f"ANSWER: {answer}\n\nEXCERPT [{citation['signal_id']}]: {citation['excerpt']}",
            tool=JUDGE_TOOL,
            tool_name="judge_citation",
            trace_name="ask_eval:entailment",
        )
        supported += 1 if verdict.get("supported") else 0
    return supported, len(citations)


def main() -> int:
    signals, dataset_of = _load_signals()
    print(f"Corpus: {len(signals)} demo signals across {len(set(dataset_of.values()))} datasets")

    rows = []
    supported_total = 0
    cited_total = 0
    for item in QA_SET:
        result = ask_clara(item["q"], signals)
        correct = _grade(item, result, dataset_of)
        entail = None
        if not result.get("refused") and result.get("citations"):
            supported, cited = _entailment(result.get("answer") or "", result["citations"])
            supported_total += supported
            cited_total += cited
            entail = {"supported": supported, "cited": cited}
        rows.append({
            "question": item["q"],
            "expect": item["expect"],
            "refused": bool(result.get("refused")),
            "confidence": result.get("confidence", 0.0),
            "correct": correct,
            "entailment": entail,
        })
        print(f"  [{'OK ' if correct else 'MISS'}] expect={item['expect']:6s}"
              f" refused={str(bool(result.get('refused'))):5s}"
              f" conf={result.get('confidence', 0.0):0.2f}  {item['q'][:60]}")

    # Selective-prediction curve: treat "answer only above threshold t" as the
    # policy; refusals and below-threshold answers count as not covered.
    curve = []
    for threshold in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        answered = [r for r in rows if not r["refused"] and r["confidence"] >= threshold]
        answerable = [r for r in answered if r["expect"] == "answer"]
        curve.append({
            "threshold": threshold,
            "coverage": round(len(answered) / len(rows), 3),
            "accuracy_on_answered": round(
                sum(r["correct"] for r in answerable) / len(answered), 3
            ) if answered else None,
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": ai.effective_model(),
        "embed_model": ai.effective_embed_model(),
        "n_questions": len(rows),
        "overall_correct": sum(r["correct"] for r in rows),
        "refusal_correct": sum(r["correct"] for r in rows if r["expect"] == "refuse"),
        "refusal_total": sum(1 for r in rows if r["expect"] == "refuse"),
        "citation_entailment": {
            "supported": supported_total,
            "cited": cited_total,
            "rate": round(supported_total / cited_total, 3) if cited_total else None,
            "caveat": "LLM-judge verdicts — a smoke alarm, not a proof of faithfulness",
        },
        "selective_prediction_curve": curve,
        "rows": rows,
        "notes": [
            "Grading is programmatic: answerable = answered + cites the evidence-"
            "holding dataset; unanswerable = refused. Validates the refusal system,"
            " not free-text answer quality.",
            "QA set is authored against the demo datasets; rerun after changing"
            " them or any ask threshold (ASK_MIN_SIMILARITY).",
        ],
    }
    OUT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nCorrect: {report['overall_correct']}/{report['n_questions']}"
          f" (refusals {report['refusal_correct']}/{report['refusal_total']});"
          f" citation entailment {report['citation_entailment']['rate']}")
    print(f"Report written to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
