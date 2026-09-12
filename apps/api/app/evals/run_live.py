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

  - The golden set carries an optimisation split (the loop may tune on it) and a
    held-out split (a frozen guardrail). The pooled A/B mixes both and is
    exploratory; `by_split_ab` carries the per-split paired effect, which is
    the only valid held-out statement about exemplars. The printed report
    withholds per-item held-out failures unless --reveal-held-out is passed;
    the JSON report keeps them. Every run that scores the held-out split is
    counted in the history.jsonl ledger (`held_out_consultations`) so the
    number of looks is on record — that file is gitignored
    (app/evals/.gitignore), so the count is machine-local, not global.

Run:    cd apps/api && python3 -m app.evals.run_live [--publish] [--reveal-held-out]
Needs:  AI_BASE_URL / AI_API_KEY / AI_MODEL configured (cloud or local).
Writes: app/evals/reports/report_<ts>.json  and appends app/evals/history.jsonl
        (both gitignored)
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Deterministic-as-possible eval: pin sampling unless the caller overrode it.
os.environ.setdefault("AI_TEMPERATURE", "0")

from app.evals.harness import (  # noqa: E402
    GOLDEN_SET_PATH,
    EvalHarness,
    load_golden_set,
    wilson_interval,
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


AB_METRICS = ("sentiment", "urgency", "tag_exact")
AB_SCOPE_NOTE = "pooled over optimisation and held-out items; exploratory"
AB_DISABLED_NOTE = (
    "exemplars are disabled (ENRICH_FEWSHOT off), so the ON arm would be the "
    "same prompt as the OFF arm; an A/B of two identical arms measures model "
    "noise only and is not reported — enrichment_ab and by_split_ab are null"
)
EMPTY_INFLUENCE: dict[str, Any] = {
    "themes": 0, "adoption_rate": 0.0, "avg_off_alignment": 0.0,
    "avg_on_alignment": 0.0, "alignment_lift": 0.0, "reworded_rate": 0.0, "examples": [],
}


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
    # Full per-item predictions, persisted in the report so future calibration
    # work (model-score -> correctness mapping) can pool dated runs instead of
    # reconstructing predictions from the failures list.
    per_item: list[dict] = []
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
        split = g.get("split") or "unsplit"
        if problems:
            failures.append({"id": g["id"], "split": split, "problems": problems})
        per_item.append({
            "id": g["id"],
            "language": g.get("language", "en"),
            "split": split,
            "pred": {
                "sentiment": act.get("sentiment"),
                "sentiment_score": act.get("sentiment_score"),
                "urgency": act.get("urgency"),
                "tags": act_tags,
            },
            "correct": {"sentiment": s_ok, "urgency": u_ok, "tag_exact": t_ok},
        })

    return {
        "result": result,
        "failures": failures,
        "per_item": per_item,
        "elapsed_ms": elapsed_ms,
        "vectors": {
            "sentiment": sentiment_correct,
            "urgency": urgency_correct,
            "tag_exact": tag_exact_correct,
        },
        # Aligned with the vectors: golden-item language per position, so the
        # caller can report per-language (DE vs EN) accuracy with denominators.
        "languages": [g.get("language", "en") for g in golden],
        # Aligned likewise: the item's split, so the held-out guardrail stratum
        # can be reported separately from the pooled figure.
        "splits": [g.get("split") or "unsplit" for g in golden],
    }


def _by_stratum(vectors: dict[str, list[int]], strata: list[str]) -> dict[str, Any]:
    """Per-stratum accuracy breakdown with explicit denominators (n) and
    95% Wilson intervals for sentiment and urgency."""
    out: dict[str, Any] = {}
    for stratum in sorted(set(strata)):
        idx = [i for i, item_stratum in enumerate(strata) if item_stratum == stratum]
        n = len(idx)
        entry: dict[str, Any] = {"n": n}
        for metric, vec in vectors.items():
            entry[f"{metric}_accuracy"] = round(sum(vec[i] for i in idx) / n, 4) if n else None
        for metric in ("sentiment", "urgency"):
            hits = sum(vectors[metric][i] for i in idx)
            entry[f"{metric}_ci"] = list(wilson_interval(hits, n)) if n >= 5 else None
        out[stratum] = entry
    return out


def _by_language(vectors: dict[str, list[int]], languages: list[str]) -> dict[str, Any]:
    """Per-language accuracy breakdown (DE vs EN)."""
    return _by_stratum(vectors, languages)


def _mcnemar_ab(off_vec: list[int], on_vec: list[int]) -> dict[str, Any]:
    """Paired McNemar of two per-item correctness vectors (off vs on)."""
    b, c, p = mcnemar_exact([bool(x) for x in off_vec], [bool(x) for x in on_vec])
    return {"gained": c, "lost": b, "p_value": round(p, 4)}


def _paired_bootstrap_diff_ci(
    off_vec: list[int],
    on_vec: list[int],
    *,
    n_resamples: int = 2000,
    seed: int = 12345,
    ci: float = 0.95,
) -> list[float] | None:
    """Percentile bootstrap CI for the mean paired difference (on - off).

    Resamples ITEMS with replacement (the pairing is kept), so the interval is
    for the accuracy difference on the same items, not for two independent
    accuracies. Fixed seed -> reproducible. None on an empty stratum.
    """
    n = len(off_vec)
    if n == 0 or n != len(on_vec):
        return None
    diffs = [on_vec[i] - off_vec[i] for i in range(n)]
    rng = random.Random(seed)
    means = sorted(
        sum(diffs[rng.randrange(n)] for _ in range(n)) / n
        for _ in range(n_resamples)
    )
    lo_i = int((1 - ci) / 2 * n_resamples)
    hi_i = min(n_resamples - 1, int((1 + ci) / 2 * n_resamples))
    return [round(means[lo_i], 4), round(means[hi_i], 4)]


def _by_split_ab(
    off_vectors: dict[str, list[int]],
    on_vectors: dict[str, list[int]],
    splits: list[str],
) -> dict[str, Any]:
    """Per-split paired exemplar effect: {split: {metric: {...}}}.

    For each split and metric: n, off/on accuracy, exact McNemar (gained =
    on right & off wrong, lost = the reverse, p), the accuracy difference
    and its 95 % paired-bootstrap interval. The held-out row is the only
    valid statement about the exemplars' effect on items the loop never
    tuned on; the pooled figure mixes both strata.
    """
    out: dict[str, Any] = {}
    for split in sorted(set(splits)):
        idx = [i for i, s in enumerate(splits) if s == split]
        n = len(idx)
        entry: dict[str, Any] = {}
        for metric in AB_METRICS:
            off = [off_vectors[metric][i] for i in idx]
            on = [on_vectors[metric][i] for i in idx]
            off_acc = round(sum(off) / n, 4) if n else None
            on_acc = round(sum(on) / n, 4) if n else None
            entry[metric] = {
                "n": n,
                "off_accuracy": off_acc,
                "on_accuracy": on_acc,
                **_mcnemar_ab(off, on),
                "diff": round((sum(on) - sum(off)) / n, 4) if n else None,
                "diff_ci95": _paired_bootstrap_diff_ci(off, on),
            }
        out[split] = entry
    return out


def _sha256_lines(lines: list[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _git_commit() -> str | None:
    """`git rev-parse HEAD` of the checkout the harness runs from; None if unavailable."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=EVALS_DIR,
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _run_config(exemplars: list[dict] | None, golden: list[dict] | None = None) -> dict[str, Any]:
    """Provenance of one run: what was scored, with what, on which items.

    The hashes let two reports be compared for identical inputs (golden set
    bytes, held-out id list, exemplar texts) without diffing the files.
    """
    golden = golden if golden is not None else load_golden_set()
    held_out_ids = sorted(str(g["id"]) for g in golden if g.get("split") == "held_out")
    return {
        "model": AI_MODEL,
        "temperature": os.environ.get("AI_TEMPERATURE"),
        "exemplars_enabled": exemplars is not None,
        "exemplar_count": len(exemplars) if exemplars else 0,
        "exemplars_sha256": (
            _sha256_lines(sorted(str(e.get("text", "")) for e in exemplars)) if exemplars else None
        ),
        "golden_set_sha256": (
            hashlib.sha256(GOLDEN_SET_PATH.read_bytes()).hexdigest()
            if GOLDEN_SET_PATH.exists() else None
        ),
        "held_out_ids_sha256": _sha256_lines(held_out_ids),
        "split_counts": dict(Counter(g.get("split") or "unsplit" for g in golden)),
        "harness_git_commit": _git_commit(),
    }


def _held_out_consultations(history_path: Path) -> int:
    """How many times the held-out split has been scored on this machine,
    counting this run: prior ledger rows flagged `held_out_scored` + 1.

    history.jsonl is gitignored (app/evals/.gitignore), so this is a
    machine-local count of looks at the guardrail set, not a global one; a
    fresh clone starts again at 1. It exists so the number of consultations
    is on record at all — a validation set consulted on every iteration is
    not an independent final test, and the count is what says how far from
    one it has drifted.
    """
    prior = 0
    if history_path.exists():
        for line in history_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("held_out_scored"):
                prior += 1
    return prior + 1


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

def _print_report(report: dict, *, reveal_held_out: bool = False) -> None:
    """Print the operator summary.

    Held-out protection: per-item failures are printed for the optimisation
    split only; the held-out split appears as aggregate accuracies and as the
    per-split paired A/B. Pass reveal_held_out=True (--reveal-held-out) to
    print held-out ids — every such reveal is a look at the guardrail set.
    """
    on = report["enrichment_on"]
    off = report.get("enrichment_off")
    ab = report.get("enrichment_ab_pooled")
    ci = report["ci"]
    print("\n=== Live triage eval ===")
    print(f"model: {report['model']}   timestamp: {report['timestamp']}")
    print(f"golden signals: {on['total_signals']}   (exemplars {'ON' if report['exemplars'] else 'OFF'})")
    cfg = report.get("config") or {}
    if cfg:
        print(f"config: golden_set {str(cfg.get('golden_set_sha256'))[:12]}  "
              f"held_out_ids {str(cfg.get('held_out_ids_sha256'))[:12]}  "
              f"exemplars {str(cfg.get('exemplars_sha256'))[:12]} (n={cfg.get('exemplar_count')})  "
              f"commit {str(cfg.get('harness_git_commit'))[:12]}")

    print("\n[enrichment — production config (exemplars on), 95% Wilson interval]")
    print(f"  sentiment_accuracy: {on['sentiment_accuracy']:.2%}  (CI {ci['sentiment'][0]:.0%}–{ci['sentiment'][1]:.0%})")
    print(f"  urgency_accuracy:   {on['urgency_accuracy']:.2%}  (CI {ci['urgency'][0]:.0%}–{ci['urgency'][1]:.0%})")
    print(f"  tag_f1:             {on['tag_f1']:.2%}  (exact {on['tag_f1_exact']:.2%})")
    if on.get("hallucination_rate") is None:
        hall = (f"not evaluated (0 eligible EN items; "
                f"{on.get('hallucination_excluded', 0)} non-EN excluded)")
    else:
        hall = (f"{on['hallucination_rate']:.2%} over {on.get('hallucination_eligible', '?')} EN items "
                f"({on.get('hallucination_excluded', 0)} non-EN excluded)")
    print(f"  hallucination_rate: {hall}    pii_leak_count: {on['pii_leak_count']}")

    if ab is None or off is None:
        print("\n[exemplar A/B — not run]")
        print(f"  {report.get('ab_note') or 'no OFF arm was scored'}")
    else:
        print(f"\n[exemplar A/B — in-run, paired McNemar (gained = exemplars fixed it); "
              f"{report.get('ab_scope_note', AB_SCOPE_NOTE)}]")
        for metric in AB_METRICS:
            m = ab[metric]
            off_v = {"sentiment": off["sentiment_accuracy"], "urgency": off["urgency_accuracy"],
                     "tag_exact": off["tag_exact_accuracy"]}[metric]
            on_v = {"sentiment": on["sentiment_accuracy"], "urgency": on["urgency_accuracy"],
                    "tag_exact": on["tag_exact_accuracy"]}[metric]
            sig = "SIGNIFICANT" if m["p_value"] < 0.05 and m["gained"] > m["lost"] else "not significant"
            print(f"  {metric:10s} off {off_v:.2%} -> on {on_v:.2%}  "
                  f"(gained {m['gained']}, lost {m['lost']}, p={m['p_value']:.3f} → {sig})")
        print(f"  tag_f1 (fuzzy)  off {off['tag_f1']:.2%} -> on {on['tag_f1']:.2%}")

        print("\n[exemplar A/B by split — paired; the held_out row is the only valid held-out "
              "statement about exemplars. Accept/reject reads the optimization row.]")
        for split, metrics in (report.get("by_split_ab") or {}).items():
            for metric, m in metrics.items():
                lo, hi = m["diff_ci95"] if m["diff_ci95"] else (float("nan"), float("nan"))
                print(f"  {split:13s} {metric:10s} n={m['n']:3d}  off {m['off_accuracy']:.2%} -> "
                      f"on {m['on_accuracy']:.2%}  diff {m['diff']:+.2%} "
                      f"(95% paired-bootstrap {lo:+.1%}..{hi:+.1%}; "
                      f"gained {m['gained']}, lost {m['lost']}, p={m['p_value']:.3f})")

    held = (report.get("by_split") or {}).get("held_out")
    if held:
        print(f"\n[held-out split (frozen guardrail, n={held['n']}) — aggregate only, not inspected per item]")
        print(f"  sentiment_accuracy {held['sentiment_accuracy']:.2%}  "
              f"urgency_accuracy {held['urgency_accuracy']:.2%}  "
              f"tag_exact_accuracy {held['tag_exact_accuracy']:.2%}")
        if report.get("held_out_consultations") is not None:
            print(f"  held-out consultations on this machine (incl. this run): "
                  f"{report['held_out_consultations']}")

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

    failures = report["failures"]
    shown = [f for f in failures if reveal_held_out or f.get("split") != "held_out"]
    withheld = len(failures) - len(shown)
    scope = "all splits" if reveal_held_out else "optimization split only"
    print(f"\n[per-item enrichment failures (exemplars on, {scope}): "
          f"{len(shown)} shown of {len(failures)}/{on['total_signals']}]")
    for f in shown:
        print(f"  {f['id']}: " + "; ".join(f["problems"]))
    if withheld:
        print(f"  ({withheld} held-out failure(s) withheld — the held-out split is a frozen "
              f"guardrail; pass --reveal-held-out to print them, which counts as a look)")
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
        # None = not evaluated (no eligible EN item); see harness.EnrichmentEvalResult.
        "hallucination_rate": r.hallucination_rate,
        "hallucination_eligible": r.hallucination_eligible,
        "hallucination_excluded": r.hallucination_excluded,
        "pii_leak_count": r.pii_leak_count,
        "enrich_latency_ms": scored["elapsed_ms"],
    }


def build_report(
    *,
    scored_on: dict[str, Any],
    scored_off: dict[str, Any] | None,
    exemplars: list[dict] | None,
    synthesis: dict[str, Any] | None = None,
    influence: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the report dict from the scored arms (pure; no model calls).

    scored_on is the production configuration (exemplars as given). scored_off
    is the exemplar-free arm, or None when exemplars are disabled — then the
    two arms would be identical and no A/B is reported (enrichment_ab,
    by_split_ab, enrichment_off, per_item_off are null with `ab_note`).
    """
    now = timestamp or datetime.now(timezone.utc)
    on_vec = scored_on["vectors"]
    enrichment_on = _enr_dict(scored_on, on_vec)
    ab_enabled = exemplars is not None and scored_off is not None

    report: dict[str, Any] = {
        "kind": "eval",
        "timestamp": now.isoformat(),
        "model": AI_MODEL,
        "exemplars": exemplars is not None,
        "config": _run_config(exemplars),
        "enrichment_on": enrichment_on,
    }
    if ab_enabled:
        off_vec = scored_off["vectors"]
        assert scored_off["splits"] == scored_on["splits"], "arms scored different golden sets"
        pooled = {m: _mcnemar_ab(off_vec[m], on_vec[m]) for m in AB_METRICS}
        report.update({
            "enrichment_off": _enr_dict(scored_off, off_vec),
            # `enrichment_ab` is kept for compatibility; it IS the pooled test.
            "enrichment_ab": pooled,
            "enrichment_ab_pooled": pooled,
            "ab_scope_note": AB_SCOPE_NOTE,
            "ab_note": None,
        })
    else:
        report.update({
            "enrichment_off": None,
            "enrichment_ab": None,
            "enrichment_ab_pooled": None,
            "ab_scope_note": AB_SCOPE_NOTE,
            "ab_note": AB_DISABLED_NOTE,
        })
    report.update({
        "ci_method": "wilson_score_95",
        "ci": {"sentiment": list(wilson_interval(sum(on_vec["sentiment"]), len(on_vec["sentiment"]))),
               "urgency": list(wilson_interval(sum(on_vec["urgency"]), len(on_vec["urgency"])))},
        "by_language": _by_language(on_vec, scored_on["languages"]),
        # The golden set is split into an optimisation stratum (the loop may
        # tune on it) and a locked held-out stratum. The pooled figure above
        # mixes both; the held-out row is the guardrail number.
        "by_split": _by_stratum(on_vec, scored_on["splits"]),
        "by_split_off": _by_stratum(scored_off["vectors"], scored_off["splits"]) if ab_enabled else None,
        # Per-split paired effect: the only valid held-out statement about exemplars.
        "by_split_ab": _by_split_ab(scored_off["vectors"], on_vec, scored_on["splits"]) if ab_enabled else None,
        "synthesis": synthesis if synthesis is not None else {"total_insights": 0},
        "learning_influence": influence if influence is not None else dict(EMPTY_INFLUENCE),
        "failures": scored_on["failures"],
        "per_item": scored_on["per_item"],
        "failures_off": scored_off["failures"] if ab_enabled else None,
        "per_item_off": scored_off["per_item"] if ab_enabled else None,
    })
    return report


def main() -> int:
    if not AI_MODEL:
        print("AI_MODEL is unset — configure AI_BASE_URL/AI_API_KEY/AI_MODEL.", file=sys.stderr)
        return 2
    reveal_held_out = "--reveal-held-out" in sys.argv

    exemplars = _exemplars()
    try:
        scored_on = _score_enrichment(exemplars=exemplars)
        # No OFF arm when exemplars are disabled: it would be the same prompt
        # twice, and an A/B of identical arms only measures model noise.
        scored_off = _score_enrichment(exemplars=None) if exemplars is not None else None
    except AIProviderError as exc:
        print(f"LLM enrichment call failed: {exc}", file=sys.stderr)
        print("Check AI_BASE_URL / AI_API_KEY / AI_MODEL and that the endpoint is reachable.", file=sys.stderr)
        return 2

    # Synthesis structural + influence probe (best-effort; enrichment is the priority).
    synthesis: dict[str, Any] = {"total_insights": 0}
    influence: dict[str, Any] = dict(EMPTY_INFLUENCE)
    try:
        groups = _enrich_demo_groups()
        flat = [s for _, sigs in groups for s in sigs]
        synthesis = _synth_metrics(synthesize_insights(flat, min_cluster_size=2, min_sources=1))
        # Bootstrap cluster stability (R8): low ARI means which problems exist
        # is sampling noise — reported next to accuracy, same report.
        from app.evals.harness import cluster_stability_ari

        synthesis["cluster_stability"] = cluster_stability_ari(flat)
        influence = _learning_influence_probe(groups)
    except Exception as exc:  # noqa: BLE001
        synthesis = {"total_insights": 0, "error": f"{type(exc).__name__}: {exc}"}

    now = datetime.now(timezone.utc)
    report = build_report(
        scored_on=scored_on, scored_off=scored_off, exemplars=exemplars,
        synthesis=synthesis, influence=influence, timestamp=now,
    )
    enrichment_on = report["enrichment_on"]
    # Every run scores the held-out split; the ledger keeps count of the looks.
    held_out_consultations = _held_out_consultations(HISTORY_PATH)
    report["held_out_consultations"] = held_out_consultations

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"report_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    report_path.write_text(json.dumps(report, indent=2))
    report["_report_path"] = str(report_path)

    if "--publish" in sys.argv:
        # Committed model-card snapshot: what /compliance shows buyers. Only
        # written on an explicit flag so casual loop runs don't churn it.
        published = {
            "published_at": report["timestamp"],
            "model": AI_MODEL,
            "dataset": {
                "total_items": enrichment_on["total_signals"],
                "note": (
                    "Curated golden set; DE stratum authored + adversarially "
                    "verified. Production config (few-shot exemplars on). "
                    "Hallucination heuristic covers EN items only. Intervals "
                    "are 95% Wilson score intervals. 'overall' pools the "
                    "optimisation and held-out strata; by_split.held_out is "
                    "the locked guardrail figure. by_split_ab is the paired "
                    "exemplar effect per split; held_out_consultations is the "
                    "machine-local count of runs that scored the held-out split."
                ),
            },
            "overall": {
                "sentiment_accuracy": enrichment_on["sentiment_accuracy"],
                "sentiment_ci95": report["ci"]["sentiment"],
                "urgency_accuracy": enrichment_on["urgency_accuracy"],
                "urgency_ci95": report["ci"]["urgency"],
                "tag_f1_fuzzy": enrichment_on["tag_f1"],
            },
            "by_language": report["by_language"],
            "by_split": report["by_split"],
            "held_out_consultations": held_out_consultations,
        }
        if report["by_split_ab"] is not None:
            published["by_split_ab"] = report["by_split_ab"]
            published["ab_scope_note"] = report["ab_scope_note"]
        else:
            published["ab_note"] = report["ab_note"]
        (EVALS_DIR / "published_metrics.json").write_text(json.dumps(published, indent=2) + "\n")
        print(f"published model-card metrics -> {EVALS_DIR / 'published_metrics.json'}")

    ledger = {
        "kind": "eval",
        "timestamp": report["timestamp"],
        "model": AI_MODEL,
        "sentiment_accuracy": enrichment_on["sentiment_accuracy"],
        "urgency_accuracy": enrichment_on["urgency_accuracy"],
        "tag_f1": enrichment_on["tag_f1"],
        "tag_f1_exact": enrichment_on["tag_f1_exact"],
        "tag_exact_accuracy": enrichment_on["tag_exact_accuracy"],
        "exemplar_ab": report["enrichment_ab"],
        "by_split_ab": report["by_split_ab"],
        "clusters": synthesis.get("total_insights"),
        "adoption_rate": influence["adoption_rate"],
        "alignment_lift": influence["alignment_lift"],
        # The held-out split was scored by this run; the running count is the
        # number of looks taken on this machine (history.jsonl is gitignored).
        "held_out_scored": True,
        "held_out_consultations": held_out_consultations,
    }
    with open(HISTORY_PATH, "a") as fh:
        fh.write(json.dumps(ledger) + "\n")

    _print_report(report, reveal_held_out=reveal_held_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
