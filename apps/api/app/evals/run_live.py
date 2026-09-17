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
    the only valid held-out statement about exemplars.
  - The in-run A/B is the EXEMPLAR effect (ON vs OFF, same prompt). It cannot
    measure a prompt change (both arms carry it) or an exemplar edit (the OFF
    arm has no exemplars either way). The loop's accept gate is therefore a
    BETWEEN-run comparison, `--baseline-report PATH`: the ON arm's per-item
    correctness is joined to the baseline run's by golden id and tested with
    the same exact McNemar (`compare_reports`, written as `vs_baseline`).
    Because the model is not deterministic, that difference includes run
    noise from both runs — replication is still the standard for any claim
    carried outside the loop. Both reports must have scored the same golden
    set (config hashes are checked; a mismatch is refused).
  - Held-out per-item rows never enter the main report: they go to a sidecar
    `report_<ts>.held_out.json` (`held_out_sidecar`), the main report keeps
    optimisation-split rows plus held-out AGGREGATES only, and the printed
    report shows held-out failures only with --reveal-held-out. Every run
    scores the held-out split, so every `kind: eval` ledger row counts as one
    consultation (`held_out_consultations`); a reveal is recorded per row as
    `held_out_revealed`. history.jsonl is gitignored (app/evals/.gitignore),
    so the count is machine-local, not global.

Run:    cd apps/api && python3 -m app.evals.run_live [--publish] [--reveal-held-out]
                                                    [--baseline-report reports/report_<ts>.json]
Needs:  AI_BASE_URL / AI_API_KEY / AI_MODEL configured (cloud or local).
Writes: app/evals/reports/report_<ts>.json, report_<ts>.held_out.json and appends
        app/evals/history.jsonl (all gitignored)
"""

from __future__ import annotations

import argparse
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
    """The active exemplar set, or None when few-shot is off OR the set is
    empty: an enabled-but-empty list changes nothing in the prompt, so it is
    treated exactly like disabled (no OFF arm, no A/B)."""
    if not fewshot_enabled():
        return None
    exemplars = load_exemplars()
    return list(exemplars) if exemplars else None


AB_METRICS = ("sentiment", "urgency", "tag_exact")
AB_SCOPE_NOTE = "pooled over optimisation and held-out items; exploratory"
AB_DISABLED_NOTE = (
    "exemplars are disabled (ENRICH_FEWSHOT off, or an empty exemplar set), so "
    "the ON arm would be the same prompt as the OFF arm; an A/B of two identical "
    "arms measures model noise only and is not reported — enrichment_ab and "
    "by_split_ab are null"
)
# Report keys whose rows carry a `split`; the held-out rows of each go to the
# sidecar file, never to the main report.
PER_ITEM_KEYS = ("per_item", "per_item_off", "failures", "failures_off")
# config hashes two runs must share before their per-item rows may be joined.
COMPARABLE_HASHES = ("golden_set_sha256", "held_out_ids_sha256")
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


def _exemplars_sha256(exemplars: list[dict] | None) -> str | None:
    """Hash of the FULL exemplar objects (text and every label), order-free.

    Canonical JSON (sorted keys, compact separators) of the list sorted by
    text, so a label edit on an exemplar changes the hash while re-ordering
    the list does not. Hashing the texts alone missed sentiment / urgency /
    tag edits, which are exactly the knobs the loop turns.
    """
    if not exemplars:
        return None
    canonical = json.dumps(
        sorted(exemplars, key=lambda e: (str(e.get("text", "")), json.dumps(e, sort_keys=True, default=str))),
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Source files whose content decides what a run measures (the fingerprint
# hashes them so a dirty checkout is identified, not only its last commit).
HARNESS_SOURCE_FILES = (
    "app/services/enrichment.py",
    "app/services/exemplar_store.py",
    "app/services/tag_canon.py",
    "app/evals/harness.py",
    "app/evals/run_live.py",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str))


def _git_dirty() -> bool | None:
    """Whether the checkout has uncommitted changes under apps/api (None if
    git is unavailable)."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", "."], cwd=EVALS_DIR.parent.parent,
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())


def _harness_source_sha256() -> str | None:
    """One hash over the source files that decide what a run measures."""
    root = EVALS_DIR.parent.parent  # apps/api
    parts = []
    for relative in HARNESS_SOURCE_FILES:
        path = root / relative
        if not path.exists():
            return None
        parts.append(f"{relative}\n{path.read_text(encoding='utf-8')}")
    return _sha256_text("\n".join(parts))


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() not in ("0", "false", "no", "")


def run_inputs(exemplars: list[dict] | None, golden: list[dict] | None = None) -> dict[str, Any]:
    """Every input that decides what a run measures, split into the knobs the
    loop turns (``experimental``: what an accepted change is allowed to
    differ in) and the conditions it does not (``nuisance``: what must NOT
    differ between two runs that are compared). Hashes only — no prompt
    text, no exemplar text and no secret reaches the report.
    """
    from app.services.enrichment import DEFAULT_BATCH_SIZE, build_system_prompt

    golden = golden if golden is not None else load_golden_set()
    held_out_ids = sorted(str(g["id"]) for g in golden if g.get("split") == "held_out")
    system_prompt, tool, _vocabulary = build_system_prompt(exemplars=exemplars or None)
    return {
        "experimental": {
            "model": AI_MODEL,
            "temperature": os.environ.get("AI_TEMPERATURE"),
            "batch_size": DEFAULT_BATCH_SIZE,
            # The effective system prompt as sent (base prompt + few-shot
            # block in order + injection guard) and the tool schema.
            "system_prompt_sha256": _sha256_text(system_prompt),
            "tool_schema_sha256": _sha256_json(tool),
            "exemplars_enabled": bool(exemplars),
            "exemplar_count": len(exemplars) if exemplars else 0,
            # Order-free (a label edit changes it) and ordered (a reorder of
            # the few-shot block changes it: the model reads them in order).
            "exemplars_sha256": _exemplars_sha256(exemplars),
            "exemplars_ordered_sha256": _sha256_json(list(exemplars)) if exemplars else None,
            "fewshot_enabled": _flag("ENRICH_FEWSHOT", "1"),
            "tag_canon_enabled": _flag("ENRICH_TAG_CANON", "1"),
            "routing_closed_set_enabled": _flag("ENRICH_ROUTING_CLOSED_SET", "0"),
        },
        "nuisance": {
            "golden_set_sha256": (
                hashlib.sha256(GOLDEN_SET_PATH.read_bytes()).hexdigest()
                if GOLDEN_SET_PATH.exists() else None
            ),
            "held_out_ids_sha256": _sha256_lines(held_out_ids),
            "split_counts": dict(Counter(g.get("split") or "unsplit" for g in golden)),
            "harness_git_commit": _git_commit(),
            "harness_git_dirty": _git_dirty(),
            "harness_source_sha256": _harness_source_sha256(),
            "python_version": sys.version.split()[0],
        },
    }


def _run_config(exemplars: list[dict] | None, golden: list[dict] | None = None) -> dict[str, Any]:
    """Provenance of one run: what was scored, with what, on which items.

    The flat keys are kept for older readers (compare_reports joins on
    golden_set_sha256 / held_out_ids_sha256); ``inputs`` carries the full
    fingerprint of the effective inputs (13 Sep 2026 review, F6): the prompt
    as sent, the tool schema, the exemplars in order, the enrichment flags,
    the batch size, the dataset/split hashes and the source identity of the
    checkout, split into experimental knobs and nuisance conditions.
    An empty exemplar list counts as disabled (see _exemplars).
    """
    golden = golden if golden is not None else load_golden_set()
    inputs = run_inputs(exemplars, golden)
    return {
        "model": AI_MODEL,
        "temperature": os.environ.get("AI_TEMPERATURE"),
        "exemplars_enabled": bool(exemplars),
        "exemplar_count": len(exemplars) if exemplars else 0,
        "exemplars_sha256": _exemplars_sha256(exemplars),
        "golden_set_sha256": inputs["nuisance"]["golden_set_sha256"],
        "held_out_ids_sha256": inputs["nuisance"]["held_out_ids_sha256"],
        "split_counts": inputs["nuisance"]["split_counts"],
        "harness_git_commit": inputs["nuisance"]["harness_git_commit"],
        "inputs": inputs,
    }


def inputs_changed(baseline_config: dict[str, Any] | None, new_config: dict[str, Any] | None) -> dict[str, list[str]]:
    """Which fingerprint keys differ between two runs, by group; an older
    report without ``inputs`` yields {"unknown": ["inputs"]}."""
    b = (baseline_config or {}).get("inputs") or {}
    n = (new_config or {}).get("inputs") or {}
    if not b or not n:
        return {"unknown": ["inputs"]}
    changed: dict[str, list[str]] = {}
    for group in ("experimental", "nuisance"):
        keys = sorted(set(b.get(group, {})) | set(n.get(group, {})))
        diff = [k for k in keys if b.get(group, {}).get(k) != n.get(group, {}).get(k)]
        if diff:
            changed[group] = diff
    return changed


def _append_ledger_row(history_path: Path, row: dict[str, Any]) -> None:
    """Append one JSON row to the machine-local ledger (creating the file)."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "a") as fh:
        fh.write(json.dumps(row) + "\n")


def _held_out_consultations(history_path: Path) -> int:
    """How many times the held-out split has been scored on this machine,
    counting this run: every prior `kind: "eval"` ledger row + 1.

    Every eval row is a consultation, whether or not it carries the
    `held_out_scored` / `held_out_revealed` flags added later: the runner has
    always enriched the golden set as a whole, so every eval run scored the
    held-out split, including the rows written before the flags existed.
    Counting only flagged rows under-reported the looks taken.

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
            if isinstance(row, dict) and row.get("kind") in ("eval", "eval_failed"):
                # eval_failed: the ON arm scored the golden set (held-out
                # included) before a later step failed; the look happened.
                prior += 1
    return prior + 1


# --------------------------------------------------------------------------- #
# Held-out sidecar and between-run comparison (pure; no model calls)
# --------------------------------------------------------------------------- #

def split_held_out(report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Move every held-out per-item row out of the report into a sidecar dict.

    Returns (main, sidecar). `main` keeps the optimisation-split rows under
    PER_ITEM_KEYS (a null key stays null) and every aggregate; `sidecar`
    holds the held-out rows of both arms plus the run's identity, so the
    held-out items can be joined to a later run by id without the main
    report ever carrying them.
    """
    main = dict(report)
    sidecar: dict[str, Any] = {
        "kind": "eval_held_out",
        "timestamp": report.get("timestamp"),
        "model": report.get("model"),
        "config": report.get("config"),
        "note": ("held-out per-item rows of both arms; the frozen guardrail split. "
                 "Not for inspection by the loop — compare_reports reads it for the "
                 "held-out aggregate only."),
    }
    for key in PER_ITEM_KEYS:
        rows = report.get(key)
        if rows is None:
            main[key] = None
            sidecar[key] = None
            continue
        main[key] = [r for r in rows if r.get("split") != "held_out"]
        sidecar[key] = [r for r in rows if r.get("split") == "held_out"]
    return main, sidecar


def load_report(path: Path | str) -> dict[str, Any]:
    """Read a report JSON and, when its held-out sidecar exists, attach it as
    `_held_out` so compare_reports can produce the held-out aggregate."""
    path = Path(path)
    report = json.loads(path.read_text())
    if not isinstance(report, dict):
        raise ValueError(f"{path}: not a report object")
    report.setdefault("_report_path", str(path))
    candidates = []
    if report.get("held_out_sidecar"):
        candidates.append(Path(report["held_out_sidecar"]))
    candidates.append(path.with_name(path.name[:-len(".json")] + ".held_out.json")
                      if path.name.endswith(".json") else path.with_suffix(".held_out.json"))
    for candidate in candidates:
        if candidate.exists():
            sidecar = json.loads(candidate.read_text())
            if isinstance(sidecar, dict):
                report["_held_out"] = sidecar
            break
    return report


def check_comparable(baseline_config: dict[str, Any] | None, new_config: dict[str, Any] | None) -> None:
    """Refuse to join two runs that did not score the same items."""
    for key in COMPARABLE_HASHES:
        b = (baseline_config or {}).get(key)
        n = (new_config or {}).get(key)
        if not b or not n:
            raise ValueError(
                f"cannot compare runs: config.{key} is missing "
                f"(baseline={b!r}, new={n!r}); both reports need a config block"
            )
        if b != n:
            raise ValueError(
                f"cannot compare runs: config.{key} differs (baseline {str(b)[:12]}…, "
                f"new {str(n)[:12]}…) — the runs scored different items; re-run the "
                f"baseline on the current golden set before comparing"
            )


def _per_item_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """ON-arm per-item rows by id: the main report's plus the sidecar's."""
    rows: dict[str, dict[str, Any]] = {}
    for source in (report.get("per_item") or [], (report.get("_held_out") or {}).get("per_item") or []):
        for row in source:
            if isinstance(row, dict) and row.get("id") is not None:
                rows.setdefault(str(row["id"]), row)
    return rows


HALLUCINATION_LIMIT = 0.05  # LOOP_PROMPT target: hallucination_rate <= 0.05 when evaluated
GUARD_SCOPE = (
    "pooled over the optimisation and held-out splits: the held-out split is a "
    "safety-validation set used in selection through the veto, not an untouched test set; "
    "the accuracy decision reads the optimisation split only"
)


def _guards(baseline: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Safety guards between two runs. `null` means not evaluated, never 0."""
    b_on = baseline.get("enrichment_on") or {}
    n_on = new.get("enrichment_on") or {}
    b_h, n_h = b_on.get("hallucination_rate"), n_on.get("hallucination_rate")
    b_el, n_el = b_on.get("hallucination_eligible"), n_on.get("hallucination_eligible")
    # Statuses are explicit about WHICH side is missing: a baseline that was
    # never evaluated must not read as a pass for a new run that flags items.
    # "rose" needs both the rate and the flagged COUNT to go up, so a shifted
    # denominator (one more unassessed item) alone cannot trip it.
    if n_h is None:
        h_status = "new_not_evaluated"
    elif b_h is None:
        h_status = "baseline_not_evaluated"
    else:
        b_flagged = round(b_h * (b_el or 0)) if b_el else None
        n_flagged = round(n_h * (n_el or 0)) if n_el else None
        count_rose = (b_flagged is None or n_flagged is None) or n_flagged > b_flagged
        h_status = "rose" if (n_h > b_h and count_rose) else "ok"
    h_limit_ok = None if n_h is None else bool(n_h <= HALLUCINATION_LIMIT)
    b_p, n_p = b_on.get("pii_leak_count"), n_on.get("pii_leak_count")
    if n_p is None:
        p_status = "not_evaluated"
    elif n_p > 0:
        p_status = "leak"
    else:
        p_status = "ok"
    b_split = b_on.get("hallucination_by_split") or {}
    n_split = n_on.get("hallucination_by_split") or {}
    held_out_flagged = (b_split.get("held_out") or {}).get("flagged", 0) + (n_split.get("held_out") or {}).get("flagged", 0)
    return {
        "hallucination": {
            "baseline": b_h, "new": n_h, "status": h_status,
            "baseline_eligible": b_el,
            "new_eligible": n_el,
            # The hard ceiling from the loop targets, checked on the NEW run
            # whenever it was evaluated (null = not assessable, never 0).
            "limit": HALLUCINATION_LIMIT, "limit_ok": h_limit_ok,
            # Per-split provenance of the pooled figures (counts only).
            "by_split": {"baseline": b_split, "new": n_split},
        },
        "pii": {"baseline": b_p, "new": n_p, "status": p_status},
        # The guards are pooled over every scored item, so the held-out split
        # takes part in selection through the safety veto: it is a safety-
        # validation set used in selection, not an untouched test set. The
        # accuracy decision (vs_baseline.optimization) never reads it.
        "scope": GUARD_SCOPE,
        "held_out_contributes": held_out_flagged > 0 or (b_split.get("held_out") or {}).get("eligible", 0) > 0
        or (n_split.get("held_out") or {}).get("eligible", 0) > 0,
    }


def compare_reports(baseline: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Between-run paired comparison of the ON arm, joined by golden id.

    Returns {split: {metric: {n, baseline_accuracy, new_accuracy, gained,
    lost, p_value, diff, diff_ci95}}} plus `guards` (hallucination / PII,
    see _guards) and `baseline` (identity of the joined run). gained = new
    right & baseline wrong, lost = the reverse, p = exact McNemar; diff =
    new - baseline accuracy with a 95 % paired-bootstrap interval (seed
    12345). The held-out split, when both reports carry it (main rows in an
    older report, or the sidecar), is an aggregate only. Refuses (ValueError)
    when the two runs did not score the same golden set.
    """
    check_comparable(baseline.get("config"), new.get("config"))
    b_rows = _per_item_rows(baseline)
    n_rows = _per_item_rows(new)
    shared = [i for i in n_rows if i in b_rows]
    out: dict[str, Any] = {}
    for split in sorted({n_rows[i].get("split") or "unsplit" for i in shared}):
        ids = [i for i in shared if (n_rows[i].get("split") or "unsplit") == split]
        n = len(ids)
        entry: dict[str, Any] = {}
        for metric in AB_METRICS:
            b_vec = [int(bool((b_rows[i].get("correct") or {}).get(metric))) for i in ids]
            n_vec = [int(bool((n_rows[i].get("correct") or {}).get(metric))) for i in ids]
            entry[metric] = {
                "n": n,
                "baseline_accuracy": round(sum(b_vec) / n, 4) if n else None,
                "new_accuracy": round(sum(n_vec) / n, 4) if n else None,
                **_mcnemar_ab(b_vec, n_vec),
                "diff": round((sum(n_vec) - sum(b_vec)) / n, 4) if n else None,
                "diff_ci95": _paired_bootstrap_diff_ci(b_vec, n_vec),
            }
        out[split] = entry
    out["guards"] = _guards(baseline, new)
    out["baseline"] = {
        "timestamp": baseline.get("timestamp"),
        "model": baseline.get("model"),
        "report_path": baseline.get("_report_path"),
        "n_joined": len(shared),
        "n_only_in_new": len(n_rows) - len(shared),
        "n_only_in_baseline": len(b_rows) - len(shared),
        "held_out_from_sidecar": bool((baseline.get("_held_out") or {}).get("per_item")),
    }
    if out["baseline"]["n_only_in_new"] and not out["baseline"]["held_out_from_sidecar"]:
        # Rows the new run scored that the baseline could not supply (its
        # sidecar is missing): say so instead of silently reporting a partial
        # or absent held-out aggregate — the final held-out declaration
        # quotes this block.
        out["held_out_note"] = (
            "baseline sidecar missing: the held-out aggregate could not be joined; "
            "re-run with a baseline report whose .held_out.json sidecar exists"
        )
    return out


def _vs_baseline_splits(vs: dict[str, Any]) -> dict[str, Any]:
    """The split entries of a vs_baseline block (drops `guards`, `baseline`
    and any note)."""
    return {k: v for k, v in vs.items() if k not in ("guards", "baseline") and isinstance(v, dict)}


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

def _print_report(
    report: dict,
    *,
    reveal_held_out: bool = False,
    held_out: dict[str, Any] | None = None,
) -> None:
    """Print the operator summary.

    Held-out protection: per-item failures are printed for the optimisation
    split only; the held-out split appears as aggregate accuracies, as the
    per-split paired A/B and as the vs_baseline aggregate. Pass
    reveal_held_out=True (--reveal-held-out) to print held-out ids (from the
    `held_out` sidecar dict, or from an unsplit report's own rows) — every
    such reveal is a look at the guardrail set and is recorded in the ledger.
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
                f"{on.get('hallucination_excluded', 0)} non-EN excluded, "
                f"{on.get('hallucination_unassessed', 0)} EN unassessed)")
    else:
        hall = (f"{on['hallucination_rate']:.2%} over {on.get('hallucination_eligible', '?')} EN items "
                f"({on.get('hallucination_excluded', 0)} non-EN excluded, "
                f"{on.get('hallucination_unassessed', 0)} EN unassessed)")
    print(f"  hallucination_rate: {hall}    pii_leak_count: {on['pii_leak_count']}")

    vs = report.get("vs_baseline")
    if vs:
        base = vs.get("baseline") or {}
        print(f"\n[vs baseline — between-run, ON arm joined by golden id to "
              f"{base.get('timestamp')} ({base.get('model')}); exact McNemar; "
              f"n_joined={base.get('n_joined')}. ACCEPT reads the optimization rows; "
              f"the held_out rows are an aggregate, not part of the decision]")
        for split, metrics in _vs_baseline_splits(vs).items():
            for metric, m in metrics.items():
                lo, hi = m["diff_ci95"] if m["diff_ci95"] else (float("nan"), float("nan"))
                if split != "optimization":
                    # Held-out (or unsplit) rows are an aggregate on record,
                    # never a verdict: no GAIN/LOSS label to act on.
                    sig = "aggregate only (not a decision)"
                elif m["p_value"] < 0.05 and m["gained"] > m["lost"]:
                    sig = "SIGNIFICANT GAIN"
                elif m["p_value"] < 0.05 and m["lost"] > m["gained"]:
                    sig = "SIGNIFICANT LOSS"
                else:
                    sig = "not significant"
                print(f"  {split:13s} {metric:10s} n={m['n']:3d}  baseline {m['baseline_accuracy']:.2%} -> "
                      f"new {m['new_accuracy']:.2%}  diff {m['diff']:+.2%} "
                      f"(95% paired-bootstrap {lo:+.1%}..{hi:+.1%}; gained {m['gained']}, "
                      f"lost {m['lost']}, p={m['p_value']:.3f} → {sig})")
        g = vs.get("guards") or {}
        h, pii = g.get("hallucination") or {}, g.get("pii") or {}

        def fmt(v: Any) -> str:
            return "null" if v is None else (f"{v:.2%}" if isinstance(v, float) else str(v))

        print(f"  guards: hallucination {fmt(h.get('baseline'))} -> {fmt(h.get('new'))} "
              f"[{h.get('status')}]   pii {pii.get('baseline')} -> {pii.get('new')} [{pii.get('status')}]")
        if g.get("scope"):
            by_split = (h.get("by_split") or {}).get("new") or {}
            held = by_split.get("held_out") or {}
            print(f"  guard scope: {g['scope']}"
                  f" (new run: held-out {held.get('flagged', 0)} flagged of {held.get('eligible', 0)} eligible)")

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

        print("\n[exemplar A/B by split — paired ON vs OFF; the exemplar-effect estimate, "
              "reported, never the accept gate (that is vs_baseline). The held_out row is "
              "the only valid held-out statement about exemplars.]")
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

    # Held-out failures live in the sidecar (a split report) or, for an
    # unsplit report, among its own rows; either way they print only on reveal.
    failures = list(report.get("failures") or []) + list((held_out or {}).get("failures") or [])
    shown = [f for f in failures if reveal_held_out or f.get("split") != "held_out"]
    withheld = len(failures) - len(shown)
    scope = "all splits" if reveal_held_out else "optimization split only"
    print(f"\n[per-item enrichment failures (exemplars on, {scope}): "
          f"{len(shown)} shown of {len(failures)}/{on['total_signals']}]")
    for f in shown:
        print(f"  {f['id']}: " + "; ".join(f["problems"]))
    if withheld:
        print(f"  ({withheld} held-out failure(s) withheld — the held-out split is a frozen "
              f"guardrail; pass --reveal-held-out to print them, which counts as a look "
              f"and is recorded in the ledger as held_out_revealed)")
    if report.get("held_out_sidecar"):
        print(f"  (held-out per-item rows: {report['held_out_sidecar']} — not for the loop to open)")
    print(f"\nreport: {report['_report_path']}")


def _hallucination_by_split(scored: dict) -> dict[str, dict[str, int]]:
    """Eligible and flagged counts per split (counts only: no held-out id
    reaches the main report)."""
    r = scored["result"]
    golden = load_golden_set()
    split_of = {str(g["id"]): (g.get("split") or "unsplit") for g in golden}
    out: dict[str, dict[str, int]] = {}
    for gid in getattr(r, "hallucination_eligible_ids", []) or []:
        out.setdefault(split_of.get(gid, "unsplit"), {"eligible": 0, "flagged": 0})["eligible"] += 1
    for gid in getattr(r, "hallucination_flagged_ids", []) or []:
        out.setdefault(split_of.get(gid, "unsplit"), {"eligible": 0, "flagged": 0})["flagged"] += 1
    return out


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
        "hallucination_unassessed": getattr(r, "hallucination_unassessed", 0),
        # Which split the eligible / flagged items came from: the guard pools
        # both splits, so the held-out split takes part in the safety veto.
        "hallucination_by_split": _hallucination_by_split(scored),
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
    by_split_ab, enrichment_off, per_item_off are null with `ab_note`). An
    empty exemplar list is disabled: the arms would be identical too.
    """
    now = timestamp or datetime.now(timezone.utc)
    on_vec = scored_on["vectors"]
    enrichment_on = _enr_dict(scored_on, on_vec)
    exemplars = list(exemplars) if exemplars else None
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


def published_snapshot(report: dict[str, Any], held_out_consultations: int) -> dict[str, Any]:
    """The committed model-card snapshot (published_metrics.json) for a report.

    Carries the hallucination guard with its denominators (`null` rate = not
    evaluated), the PII count and the run's `config` block, so the snapshot
    is citable on its own.
    """
    on = report["enrichment_on"]
    published: dict[str, Any] = {
        "published_at": report["timestamp"],
        "model": report["model"],
        "dataset": {
            "total_items": on["total_signals"],
            "note": (
                "Curated golden set; DE stratum authored + adversarially "
                "verified. Production config (few-shot exemplars on). "
                "Hallucination heuristic covers EN items only: its rate is over "
                "hallucination_eligible EN items with a tagged enrichment; "
                "null means not evaluated. Intervals are 95% Wilson score "
                "intervals. 'overall' pools the optimisation and held-out "
                "strata; by_split.held_out is the locked guardrail figure. "
                "by_split_ab is the paired exemplar effect per split; "
                "held_out_consultations is the machine-local count of runs "
                "that scored the held-out split. The hallucination and PII "
                "guards pool both splits, so the held-out split is a "
                "safety-validation set used in selection through the veto, "
                "not an untouched test set."
            ),
        },
        "overall": {
            "sentiment_accuracy": on["sentiment_accuracy"],
            "sentiment_ci95": report["ci"]["sentiment"],
            "urgency_accuracy": on["urgency_accuracy"],
            "urgency_ci95": report["ci"]["urgency"],
            "tag_f1_fuzzy": on["tag_f1"],
            "hallucination_rate": on.get("hallucination_rate"),
            "hallucination_eligible": on.get("hallucination_eligible"),
            "hallucination_excluded": on.get("hallucination_excluded"),
            "hallucination_unassessed": on.get("hallucination_unassessed"),
            "pii_leak_count": on.get("pii_leak_count"),
        },
        "by_language": report["by_language"],
        "by_split": report["by_split"],
        "held_out_consultations": held_out_consultations,
        "config": report.get("config"),
    }
    if report.get("by_split_ab") is not None:
        published["by_split_ab"] = report["by_split_ab"]
        published["ab_scope_note"] = report["ab_scope_note"]
    else:
        published["ab_note"] = report["ab_note"]
    return published


def ledger_row(
    report: dict[str, Any],
    *,
    held_out_consultations: int,
    held_out_revealed: bool,
) -> dict[str, Any]:
    """The history.jsonl row for a run: headline metrics, both guards, the
    config hashes that make the run citable, the between-run gate result when
    a baseline was given, and whether held-out ids were revealed."""
    on = report["enrichment_on"]
    cfg = report.get("config") or {}
    synthesis = report.get("synthesis") or {}
    influence = report.get("learning_influence") or {}
    vs = report.get("vs_baseline") or {}
    return {
        "kind": "eval",
        "timestamp": report["timestamp"],
        "model": report["model"],
        "sentiment_accuracy": on["sentiment_accuracy"],
        "urgency_accuracy": on["urgency_accuracy"],
        "tag_f1": on["tag_f1"],
        "tag_f1_exact": on["tag_f1_exact"],
        "tag_exact_accuracy": on["tag_exact_accuracy"],
        "hallucination_rate": on.get("hallucination_rate"),
        "hallucination_eligible": on.get("hallucination_eligible"),
        "hallucination_excluded": on.get("hallucination_excluded"),
        "hallucination_unassessed": on.get("hallucination_unassessed"),
        "pii_leak_count": on.get("pii_leak_count"),
        "exemplar_ab": report.get("enrichment_ab"),
        "by_split_ab": report.get("by_split_ab"),
        "vs_baseline_optimization": vs.get("optimization"),
        "vs_baseline_guards": vs.get("guards"),
        "baseline_report": (vs.get("baseline") or {}).get("report_path"),
        "clusters": synthesis.get("total_insights"),
        "adoption_rate": influence.get("adoption_rate"),
        "alignment_lift": influence.get("alignment_lift"),
        "golden_set_sha256": cfg.get("golden_set_sha256"),
        "held_out_ids_sha256": cfg.get("held_out_ids_sha256"),
        "exemplars_sha256": cfg.get("exemplars_sha256"),
        "harness_git_commit": cfg.get("harness_git_commit"),
        # The full fingerprint of the effective inputs; a reject row written
        # by the operator must copy this block so a rejected candidate is
        # as identifiable as an accepted one.
        "inputs": cfg.get("inputs"),
        "guards_scope": (vs.get("guards") or {}).get("scope"),
        # The held-out split was scored by this run; the running count is the
        # number of looks taken on this machine (history.jsonl is gitignored).
        "held_out_scored": True,
        "held_out_revealed": bool(held_out_revealed),
        "held_out_consultations": held_out_consultations,
        "held_out_sidecar": report.get("held_out_sidecar"),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python3 -m app.evals.run_live",
                                 description="Live triage eval against the golden set.")
    ap.add_argument("--publish", action="store_true",
                    help="also write the committed model-card snapshot (published_metrics.json)")
    ap.add_argument("--reveal-held-out", action="store_true",
                    help="print held-out per-item failures (a recorded look at the guardrail set)")
    ap.add_argument("--baseline-report", type=Path, default=None, metavar="PATH",
                    help="previous report to compare against (between-run paired test -> vs_baseline)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if not AI_MODEL:
        print("AI_MODEL is unset — configure AI_BASE_URL/AI_API_KEY/AI_MODEL.", file=sys.stderr)
        return 2
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    reveal_held_out = args.reveal_held_out

    exemplars = _exemplars()
    baseline: dict[str, Any] | None = None
    if args.baseline_report is not None:
        # Refuse BEFORE any model call when the baseline scored different items.
        try:
            baseline = load_report(args.baseline_report)
            check_comparable(baseline.get("config"), _run_config(exemplars))
        except (OSError, ValueError) as exc:
            print(f"--baseline-report {args.baseline_report}: {exc}", file=sys.stderr)
            return 2
    scored_on = None
    try:
        scored_on = _score_enrichment(exemplars=exemplars)
        # No OFF arm when exemplars are disabled (or empty): it would be the
        # same prompt twice, and an A/B of identical arms only measures noise.
        scored_off = _score_enrichment(exemplars=None) if exemplars else None
    except AIProviderError as exc:
        print(f"LLM enrichment call failed: {exc}", file=sys.stderr)
        print("Check AI_BASE_URL / AI_API_KEY / AI_MODEL and that the endpoint is reachable.", file=sys.stderr)
        if scored_on is not None:
            # The ON arm already scored the whole golden set: that look at the
            # held-out split happened and must be on record even though no
            # report is written.
            _append_ledger_row(HISTORY_PATH, {
                "kind": "eval_failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": AI_MODEL,
                "held_out_scored": True,
                "held_out_revealed": False,
                "reason": f"OFF arm failed: {exc}"[:300],
                # The failed candidate is identified like any other run.
                "config": _run_config(exemplars),
            })
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
    # Every run scores the held-out split; the ledger keeps count of the looks.
    held_out_consultations = _held_out_consultations(HISTORY_PATH)
    report["held_out_consultations"] = held_out_consultations
    if baseline is not None:
        # Joined while the new report still holds every row (before the split).
        report["vs_baseline"] = compare_reports(baseline, report)

    # Held-out per-item rows go to the sidecar; the main report keeps the
    # optimisation rows and the held-out aggregates only.
    main_report, sidecar = split_held_out(report)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    report_path = REPORTS_DIR / f"report_{stamp}.json"
    sidecar_path = REPORTS_DIR / f"report_{stamp}.held_out.json"
    main_report["held_out_sidecar"] = str(sidecar_path)
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    report_path.write_text(json.dumps(main_report, indent=2))
    main_report["_report_path"] = str(report_path)

    if args.publish:
        # Committed model-card snapshot: what /compliance shows buyers. Only
        # written on an explicit flag so casual loop runs don't churn it.
        published = published_snapshot(main_report, held_out_consultations)
        (EVALS_DIR / "published_metrics.json").write_text(json.dumps(published, indent=2) + "\n")
        print(f"published model-card metrics -> {EVALS_DIR / 'published_metrics.json'}")

    ledger = ledger_row(main_report, held_out_consultations=held_out_consultations,
                        held_out_revealed=reveal_held_out)
    _append_ledger_row(HISTORY_PATH, ledger)

    _print_report(main_report, reveal_held_out=reveal_held_out, held_out=sidecar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
