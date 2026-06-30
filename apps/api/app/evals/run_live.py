"""Live eval runner — drives the REAL LLM triage stages and scores them.

Unlike ``EvalHarness.run_full_eval()`` (which self-compares the golden set), this
calls the actual ``enrich_signals`` / ``synthesize_insights`` against a live
OpenAI-compatible endpoint and scores the real output. It is what the
eval-improve ``/loop`` runs each iteration.

Design notes (why the comparisons are structured the way they are):
  - The eval model (e.g. GLM 5.2, a 355B MoE) is NOT deterministic at
    temperature 0, so cross-run comparisons conflate a change with model noise.
    Every A/B here is therefore measured WITHIN one run:
      * enrichment exemplars: golden set is enriched twice (off vs on) and
        compared with a PAIRED McNemar test on the same items.
      * learning influence: synthesised twice with vs without the learning, and
        a same-input noise floor (two identical "off" calls) is subtracted so the
        reported effect is above model jitter.
  - Synthesis on 0 real clusters returns 0 honestly (the harness no longer
    fabricates golden-set numbers).

Run:    cd apps/api && python3 -m app.evals.run_live
Needs:  AI_BASE_URL / AI_API_KEY / AI_MODEL configured (cloud or local).
Writes: app/evals/reports/report_<ts>.json  and appends app/evals/history.jsonl
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Deterministic-as-possible eval: pin sampling unless the caller overrode it.
os.environ.setdefault("AI_TEMPERATURE", "0")

from app.evals.harness import (  # noqa: E402
    EvalHarness,
    bootstrap_ci,
    load_golden_set,
    mcnemar_exact,
)
from app.services.ai import AI_MODEL, AIProviderError  # noqa: E402
from app.services.enrichment import enrich_signals  # noqa: E402
from app.services.exemplar_store import fewshot_enabled, load_exemplars  # noqa: E402
from app.services.synthesis import synthesize_cluster, synthesize_insights  # noqa: E402

EVALS_DIR = Path(__file__).parent
REPORTS_DIR = EVALS_DIR / "reports"
HISTORY_PATH = EVALS_DIR / "history.jsonl"
DEMO_DIR = EVALS_DIR.parents[3] / "data" / "demo_datasets"

# Curated "worked" learnings per demo theme — used only by the influence probe to
# test whether an injected learning changes the recommended action.
PROBE_LEARNINGS: dict[str, str] = {
    "ecommerce_checkout": "Adding automatic payment retry with a fallback provider "
                          "recovered most failed checkouts last quarter — prefer that "
                          "over a generic investigation.",
    "saas_onboarding": "A guided in-product verification checklist cut onboarding "
                       "drop-off; prefer it over emailing the documentation.",
    "retention_cancellation": "Suppressing winback emails for already-cancelled users "
                              "and offering a direct call reduced complaints — prefer "
                              "suppression over re-engagement.",
}


def _exemplars() -> list[dict] | None:
    return load_exemplars() if fewshot_enabled() else None


# --------------------------------------------------------------------------- #
# Enrichment scoring (run once per exemplar setting for the in-run A/B)
# --------------------------------------------------------------------------- #

def _score_enrichment(*, exemplars: list[dict] | None) -> dict[str, Any]:
    """Run real enrichment over the golden set and score it vs the labels.

    Returns aggregate metrics plus per-item correctness vectors (sentiment,
    urgency, exact-tag-set) so the caller can run paired significance tests.
    """
    golden = load_golden_set()
    signals = [{"id": g["id"], "text": g["text"]} for g in golden]

    t0 = time.time()
    enrichments = enrich_signals(signals, exemplars=exemplars)
    elapsed_ms = (time.time() - t0) * 1000.0

    result = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=enrichments)

    by_id = {e.get("id"): e for e in enrichments}
    failures: list[dict] = []
    sentiment_correct: list[int] = []
    urgency_correct: list[int] = []
    tag_exact_correct: list[int] = []
    for g in golden:
        exp, act = g["expected"], by_id.get(g["id"], {})
        s_ok = act.get("sentiment") == exp.get("sentiment")
        u_ok = act.get("urgency") == exp.get("urgency")
        exp_tags, act_tags = exp.get("tags", []), act.get("tags", [])
        t_ok = set(exp_tags) == set(act_tags)
        sentiment_correct.append(int(s_ok))
        urgency_correct.append(int(u_ok))
        tag_exact_correct.append(int(t_ok))
        problems = []
        if not s_ok:
            problems.append(f"sentiment pred={act.get('sentiment')} exp={exp.get('sentiment')}")
        if not u_ok:
            problems.append(f"urgency pred={act.get('urgency')} exp={exp.get('urgency')}")
        if not t_ok:
            problems.append(f"tags pred={act_tags} exp={exp_tags}")
        if problems:
            failures.append({"id": g["id"], "problems": problems})

    return {
        "result": result,
        "failures": failures,
        "elapsed_ms": elapsed_ms,
        "vectors": {
            "sentiment": sentiment_correct,
            "urgency": urgency_correct,
            "tag_exact": tag_exact_correct,
        },
    }


def _mcnemar_ab(off_vec: list[int], on_vec: list[int]) -> dict[str, Any]:
    """Paired McNemar of two per-item correctness vectors (off vs on)."""
    b, c, p = mcnemar_exact([bool(x) for x in off_vec], [bool(x) for x in on_vec])
    return {"gained": c, "lost": b, "p_value": round(p, 4)}


# --------------------------------------------------------------------------- #
# Demo datasets (kept grouped by dataset = a guaranteed same-theme cluster)
# --------------------------------------------------------------------------- #

def _normalize_demo_signal(s: dict) -> dict:
    return {
        "id": s.get("signal_id", s.get("id")),
        "text": s.get("feedback_text", s.get("text", "")),
        "source": s.get("source", "unknown"),
        "signal_type": "qualitative",
        "contact_count": s.get("contact_count", 1),
        "timestamp": s.get("timestamp"),
    }


def _enrich_demo_groups() -> list[tuple[str, list[dict]]]:
    """Enrich all demo signals once; return them grouped by dataset id."""
    groups_raw: list[tuple[str, list[dict]]] = []
    for f in sorted(DEMO_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        sigs = [_normalize_demo_signal(s) for s in data.get("signals", [])]
        if sigs:
            groups_raw.append((data.get("dataset_id", f.stem), sigs))

    flat = [s for _, sigs in groups_raw for s in sigs]
    enrichments = enrich_signals(
        [{"id": s["id"], "text": s["text"]} for s in flat], exemplars=_exemplars()
    )
    by_id = {e.get("id"): e for e in enrichments}

    def _merge(s: dict) -> dict:
        e = by_id.get(s["id"], {})
        return {**s, "tags": e.get("tags", []), "sentiment": e.get("sentiment"),
                "sentiment_score": e.get("sentiment_score"), "urgency": e.get("urgency")}

    return [(dsid, [_merge(s) for s in sigs]) for dsid, sigs in groups_raw]


def _synth_metrics(insights: list[dict]) -> dict[str, Any]:
    r = EvalHarness().run_synthesis_eval(insights=insights)
    return {
        "total_insights": r.total_insights,
        "category_coverage": r.category_coverage,
        "severity_accuracy": r.severity_accuracy,
        "action_quality": r.action_quality_score,
        "avg_confidence": r.avg_confidence,
    }


# --------------------------------------------------------------------------- #
# Learning-influence probe (self-contained, noise-controlled)
# --------------------------------------------------------------------------- #

def _action_signature(insight: dict) -> str:
    return json.dumps(
        [{"type": a.get("type", ""), "title": a.get("title", ""),
          "description": a.get("description", "")}
         for a in insight.get("suggested_actions", [])],
        sort_keys=True,
    )


def _dominant_tag(signals: list[dict]) -> str:
    tags = [t for s in signals for t in s.get("tags", [])]
    return Counter(tags).most_common(1)[0][0] if tags else "general"


def _probe_learning(dataset_id: str, tag: str) -> dict[str, Any]:
    return {
        "topic": tag,
        "learning_status": "worked",
        "freshness": "VALIDATED",
        "base_confidence": 0.8,
        "summary": PROBE_LEARNINGS.get(dataset_id, f"A targeted fix for {tag} resolved it before."),
    }


# Generic / framing words that carry no remedy signal — excluded so alignment
# measures adoption of the learning's *recommendation*, not incidental overlap.
_STOP = {
    "prefer", "over", "that", "this", "with", "from", "into", "onto", "their",
    "them", "they", "resolved", "reduced", "recovered", "most", "last", "quarter",
    "generic", "instead", "before", "targeted", "action", "issue", "issues",
    "customer", "customers", "users", "user", "team", "still", "when", "where",
    "your", "ours", "have", "been", "will", "than", "more", "less", "some",
}


def _content_tokens(text: str) -> set[str]:
    """Distinctive content words (len>3, non-stop) — the remedy vocabulary."""
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(t) > 3 and t not in _STOP}


def _action_text(insight: dict) -> str:
    return " ".join(f"{a.get('title', '')} {a.get('description', '')}"
                    for a in insight.get("suggested_actions", []))


def _alignment(insight: dict, learning_tokens: set[str]) -> float:
    """Fraction of the learning's remedy vocabulary that surfaces in the action."""
    if not learning_tokens:
        return 0.0
    return len(_content_tokens(_action_text(insight)) & learning_tokens) / len(learning_tokens)


def _learning_influence_probe(groups: list[tuple[str, list[dict]]]) -> dict[str, Any]:
    """Does an injected learning steer the recommended action toward what worked?

    The eval model rewords every call, so comparing action *strings* is useless
    (off_a != off_b from jitter alone). Instead we measure ADOPTION: how much of
    the learning's remedy vocabulary surfaces in the action. For each demo theme:
      off_a, off_b  — no learning  -> baseline incidental overlap (max of two, a
                                       noise-robust floor)
      on            — same signals + a 'worked' learning
    A theme counts as adopted when the on-action covers materially more of the
    learning's remedy terms than the no-learning baseline. Self-contained and
    deterministic in design — no dependency on a separate seed run or string identity.
    """
    rows: list[dict[str, Any]] = []
    for dsid, signals in groups:
        tag = _dominant_tag(signals)
        learning = _probe_learning(dsid, tag)
        ltok = _content_tokens(learning["summary"])
        off_a = synthesize_cluster(tag, signals)
        off_b = synthesize_cluster(tag, signals)
        on = synthesize_cluster(tag, signals, learnings=[learning])
        if not (off_a and off_b and on):
            continue
        off_align = max(_alignment(off_a, ltok), _alignment(off_b, ltok))
        on_align = _alignment(on, ltok)
        rows.append({
            "theme": tag,
            "off_alignment": round(off_align, 3),
            "on_alignment": round(on_align, 3),
            # adopted = covers >=30% of the learning's remedy terms AND clearly
            # above the no-learning baseline (guards against incidental overlap).
            "adopted": on_align >= 0.30 and on_align > off_align + 0.10,
            "reworded": _action_signature(off_a) != _action_signature(off_b),
            "off_action": (off_a.get("suggested_actions") or [{}])[0].get("title", ""),
            "on_action": (on.get("suggested_actions") or [{}])[0].get("title", ""),
        })

    n = len(rows)
    return {
        "themes": n,
        "adoption_rate": sum(r["adopted"] for r in rows) / n if n else 0.0,
        "avg_off_alignment": round(sum(r["off_alignment"] for r in rows) / n, 3) if n else 0.0,
        "avg_on_alignment": round(sum(r["on_alignment"] for r in rows) / n, 3) if n else 0.0,
        "alignment_lift": round((sum(r["on_alignment"] - r["off_alignment"] for r in rows) / n), 3) if n else 0.0,
        "reworded_rate": sum(r["reworded"] for r in rows) / n if n else 0.0,
        "examples": rows[:3],
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def _print_report(report: dict) -> None:
    on = report["enrichment_on"]
    off = report["enrichment_off"]
    ab = report["enrichment_ab"]
    ci = report["ci"]
    print("\n=== Live triage eval ===")
    print(f"model: {report['model']}   timestamp: {report['timestamp']}")
    print(f"golden signals: {on['total_signals']}   (exemplars {'ON' if report['exemplars'] else 'OFF'})")

    print("\n[enrichment — production config (exemplars on), 95% bootstrap CI]")
    print(f"  sentiment_accuracy: {on['sentiment_accuracy']:.2%}  (CI {ci['sentiment'][0]:.0%}–{ci['sentiment'][1]:.0%})")
    print(f"  urgency_accuracy:   {on['urgency_accuracy']:.2%}  (CI {ci['urgency'][0]:.0%}–{ci['urgency'][1]:.0%})")
    print(f"  tag_f1:             {on['tag_f1']:.2%}  (exact {on['tag_f1_exact']:.2%})")
    print(f"  hallucination_rate: {on['hallucination_rate']:.2%}    pii_leak_count: {on['pii_leak_count']}")

    print("\n[exemplar A/B — in-run, paired McNemar (gained = exemplars fixed it)]")
    for metric in ("sentiment", "urgency", "tag_exact"):
        m = ab[metric]
        off_v = {"sentiment": off["sentiment_accuracy"], "urgency": off["urgency_accuracy"],
                 "tag_exact": off["tag_exact_accuracy"]}[metric]
        on_v = {"sentiment": on["sentiment_accuracy"], "urgency": on["urgency_accuracy"],
                "tag_exact": on["tag_exact_accuracy"]}[metric]
        sig = "SIGNIFICANT" if m["p_value"] < 0.05 and m["gained"] > m["lost"] else "not significant"
        print(f"  {metric:10s} off {off_v:.2%} -> on {on_v:.2%}  "
              f"(gained {m['gained']}, lost {m['lost']}, p={m['p_value']:.3f} → {sig})")
    print(f"  tag_f1 (fuzzy)  off {off['tag_f1']:.2%} -> on {on['tag_f1']:.2%}")

    syn = report["synthesis"]
    print(f"\n[synthesis on demo — {syn['total_insights']} real clusters formed]")
    if syn["total_insights"] == 0:
        print("  no clusters formed (demo too small for current tag sharpness) — "
              "structural metrics omitted to avoid fabrication")
    else:
        print(f"  category_coverage {syn['category_coverage']:.2%}  "
              f"severity_accuracy {syn['severity_accuracy']:.2%}  "
              f"action_quality {syn['action_quality']:.2%}  avg_conf {syn['avg_confidence']:.2f}")

    inf = report["learning_influence"]
    print(f"\n[learning influence probe — {inf['themes']} themes, adoption-based]")
    print(f"  adoption_rate {inf['adoption_rate']:.0%}   "
          f"learning-term coverage: off {inf['avg_off_alignment']:.0%} -> on {inf['avg_on_alignment']:.0%}  "
          f"(lift {inf['alignment_lift']:+.0%})")
    print(f"  (model reworded the action on {inf['reworded_rate']:.0%} of identical no-learning calls — "
          "why string-diff can't measure this)")
    for ex in inf["examples"]:
        mark = "✓ adopted" if ex["adopted"] else "· no adoption"
        print(f"    {mark}  {ex['theme']}  (coverage {ex['off_alignment']:.0%} -> {ex['on_alignment']:.0%})")
        print(f"        off: {ex['off_action']!r}")
        print(f"        on:  {ex['on_action']!r}")
    print("  (adoption = the recommendation took on the learning's remedy; proves the")
    print("   loop is active. Whether that remedy is BETTER needs measured outcomes.)")

    print(f"\n[per-item enrichment failures (exemplars on): {len(report['failures'])}/{on['total_signals']}]")
    for f in report["failures"]:
        print(f"  {f['id']}: " + "; ".join(f["problems"]))
    print(f"\nreport: {report['_report_path']}")


def _enr_dict(scored: dict, vectors: dict) -> dict[str, Any]:
    r = scored["result"]
    return {
        "total_signals": r.total_signals,
        "sentiment_accuracy": r.sentiment_accuracy,
        "urgency_accuracy": r.urgency_accuracy,
        "tag_exact_accuracy": sum(vectors["tag_exact"]) / len(vectors["tag_exact"]) if vectors["tag_exact"] else 0.0,
        "tag_f1": r.tag_f1,
        "tag_f1_exact": r.tag_f1_exact,
        "hallucination_rate": r.hallucination_rate,
        "pii_leak_count": r.pii_leak_count,
        "enrich_latency_ms": scored["elapsed_ms"],
    }


def main() -> int:
    if not AI_MODEL:
        print("AI_MODEL is unset — configure AI_BASE_URL/AI_API_KEY/AI_MODEL.", file=sys.stderr)
        return 2

    try:
        scored_on = _score_enrichment(exemplars=_exemplars())
        scored_off = _score_enrichment(exemplars=None)
    except AIProviderError as exc:
        print(f"LLM enrichment call failed: {exc}", file=sys.stderr)
        print("Check AI_BASE_URL / AI_API_KEY / AI_MODEL and that the endpoint is reachable.", file=sys.stderr)
        return 2

    on_vec, off_vec = scored_on["vectors"], scored_off["vectors"]
    enrichment_on = _enr_dict(scored_on, on_vec)
    enrichment_off = _enr_dict(scored_off, off_vec)
    enrichment_ab = {m: _mcnemar_ab(off_vec[m], on_vec[m]) for m in ("sentiment", "urgency", "tag_exact")}

    # Synthesis structural + influence probe (best-effort; enrichment is the priority).
    synthesis = {"total_insights": 0}
    influence = {"themes": 0, "adoption_rate": 0.0, "avg_off_alignment": 0.0,
                 "avg_on_alignment": 0.0, "alignment_lift": 0.0, "reworded_rate": 0.0, "examples": []}
    try:
        groups = _enrich_demo_groups()
        flat = [s for _, sigs in groups for s in sigs]
        synthesis = _synth_metrics(synthesize_insights(flat, min_cluster_size=2, min_sources=1))
        influence = _learning_influence_probe(groups)
    except Exception as exc:  # noqa: BLE001
        synthesis = {"total_insights": 0, "error": f"{type(exc).__name__}: {exc}"}

    now = datetime.now(timezone.utc)
    report: dict[str, Any] = {
        "kind": "eval",
        "timestamp": now.isoformat(),
        "model": AI_MODEL,
        "exemplars": bool(_exemplars()),
        "enrichment_on": enrichment_on,
        "enrichment_off": enrichment_off,
        "enrichment_ab": enrichment_ab,
        "ci": {"sentiment": list(bootstrap_ci(on_vec["sentiment"])),
               "urgency": list(bootstrap_ci(on_vec["urgency"]))},
        "synthesis": synthesis,
        "learning_influence": influence,
        "failures": scored_on["failures"],
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"report_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2))
    report["_report_path"] = str(report_path)

    ledger = {
        "kind": "eval",
        "timestamp": report["timestamp"],
        "model": AI_MODEL,
        "sentiment_accuracy": enrichment_on["sentiment_accuracy"],
        "urgency_accuracy": enrichment_on["urgency_accuracy"],
        "tag_f1": enrichment_on["tag_f1"],
        "tag_f1_exact": enrichment_on["tag_f1_exact"],
        "tag_exact_accuracy": enrichment_on["tag_exact_accuracy"],
        "exemplar_ab": enrichment_ab,
        "clusters": synthesis.get("total_insights"),
        "adoption_rate": influence["adoption_rate"],
        "alignment_lift": influence["alignment_lift"],
    }
    with open(HISTORY_PATH, "a") as fh:
        fh.write(json.dumps(ledger) + "\n")

    _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
