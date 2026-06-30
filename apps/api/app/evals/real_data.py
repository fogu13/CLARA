"""Real-data eval — run the live triage stages over scraped customer feedback and
report how the model performs, with NO hand-labelling required.

Unlike ``run_live`` (which scores a curated golden set), this consumes real
"combined import" CSVs — rows of either a qualitative ``text`` or a quantitative
``metric`` (star_rating_1_5), paired by a public_signal_id in the ``tags`` JSON.
The star rating is used as a PROXY ground-truth for sentiment (1-2★ negative,
3★ neutral, 4-5★ positive) — the only real label scraped feedback carries — so we
get a genuine sentiment accuracy plus label-free signals: urgency face-validity
(does urgency rise as stars fall?), tag grounding, industry vocabulary, and
whether real volume actually clusters in synthesis.

Path is a CLI argument (a combined CSV, or a directory of ``*combined*.csv``):
    cd apps/api && python3 -m app.evals.real_data ~/path/to/datasets
    cd apps/api && python3 -m app.evals.real_data data/foo_combined_import.csv

Needs AI_BASE_URL / AI_API_KEY / AI_MODEL configured (cloud or local).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# run_live pins AI_TEMPERATURE=0 for eval calls; reuse that side effect + helpers.
from app.evals.harness import check_hallucination  # noqa: E402
from app.services.ai import AI_MODEL, AIProviderError  # noqa: E402
from app.services.enrichment import enrich_signals  # noqa: E402
from app.services.exemplar_store import fewshot_enabled, load_exemplars  # noqa: E402
from app.services.synthesis import synthesize_insights  # noqa: E402

os.environ.setdefault("AI_TEMPERATURE", "0")

_URGENCY_ORD = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def load_combined_csv(path: str | Path) -> list[dict[str, Any]]:
    """Parse a combined-import CSV into signal dicts {id, text, star, source}.

    Rows come in two types sharing a public_signal_id: a qualitative row carries
    ``text``; a quantitative row carries ``metric_name=star_rating_1_5`` +
    ``metric_value``. We merge them per id and keep only ids that have text.
    Robust to a UTF-8 BOM and quoted header names.
    """
    by_id: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = {(k or "").lstrip("﻿").strip('"'): v for k, v in raw.items()}
            try:
                meta = json.loads(row.get("tags") or "{}")
            except (ValueError, TypeError):
                meta = {}
            sid = meta.get("public_signal_id") or meta.get("id") or row.get("id")
            if not sid:
                continue
            d = by_id.setdefault(sid, {"id": sid, "text": "", "star": None,
                                       "source": row.get("source")})
            if row.get("type") == "qualitative" and (row.get("text") or "").strip():
                d["text"] = row["text"].strip()
            if row.get("metric_name") == "star_rating_1_5" and (row.get("metric_value") or "").strip():
                try:
                    d["star"] = int(float(row["metric_value"]))
                except (ValueError, TypeError):
                    pass
    return [d for d in by_id.values() if d["text"]]


def star_to_sentiment(star: int | None) -> str | None:
    """Star rating -> proxy sentiment label (None if no rating)."""
    if star is None:
        return None
    if star <= 2:
        return "negative"
    if star == 3:
        return "neutral"
    return "positive"


def sentiment_agrees(predicted: str | None, proxy: str) -> bool:
    """Lenient agreement: a low-star review may read as negative OR mixed; a
    middling 3★ as neutral OR mixed; praise must be positive."""
    if proxy == "neutral":
        return predicted in ("neutral", "mixed")
    if proxy == "positive":
        return predicted == "positive"
    return predicted in ("negative", "mixed")


def score_dataset(signals: list[dict], enrichments: list[dict]) -> dict[str, Any]:
    """Pure scoring of enrichments vs the star proxy (no LLM, no synthesis)."""
    by_id = {e.get("id"): e for e in enrichments}
    polar_ok = polar_n = neutral_ok = neutral_n = grounded = scored = 0
    urgency = Counter()
    tags = Counter()
    by_star_urgency: dict[int, list[int]] = {}
    for s in signals:
        e = by_id.get(s["id"])
        if not e:
            continue
        scored += 1
        urgency[e.get("urgency")] += 1
        for t in e.get("tags", []):
            tags[t] += 1
        if not check_hallucination({"tags": e.get("tags", [])}, s["text"]):
            grounded += 1
        proxy = star_to_sentiment(s["star"])
        if proxy:
            ok = sentiment_agrees(e.get("sentiment"), proxy)
            if proxy == "neutral":
                neutral_n += 1
                neutral_ok += ok
            else:
                polar_n += 1
                polar_ok += ok
            if s["star"] is not None and e.get("urgency") in _URGENCY_ORD:
                by_star_urgency.setdefault(s["star"], []).append(_URGENCY_ORD[e["urgency"]])
    return {
        "n_signals": len(signals),
        "n_enriched": scored,
        "sentiment_polar": [polar_ok, polar_n],
        "sentiment_neutral": [neutral_ok, neutral_n],
        "grounded": [grounded, scored],
        "urgency_dist": dict(urgency),
        "mean_urgency_by_star": {st: round(sum(v) / len(v), 2)
                                 for st, v in sorted(by_star_urgency.items())},
        "top_tags": [t for t, _ in tags.most_common(8)],
    }


def _exemplars() -> list[dict] | None:
    return load_exemplars() if fewshot_enabled() else None


def evaluate(path: str | Path) -> dict[str, Any]:
    """Enrich + score + synthesize one combined CSV. Makes live LLM calls."""
    signals = load_combined_csv(path)
    if not signals:
        return {"dataset": Path(path).stem, "error": "no qualitative signals found"}
    enrichments = enrich_signals(
        [{"id": s["id"], "text": s["text"]} for s in signals], exemplars=_exemplars()
    )
    report = {"dataset": Path(path).stem, "model": AI_MODEL, **score_dataset(signals, enrichments)}

    by_id = {e.get("id"): e for e in enrichments}
    merged = [{**s, "tags": by_id[s["id"]].get("tags", []),
               "sentiment": by_id[s["id"]].get("sentiment"),
               "urgency": by_id[s["id"]].get("urgency")}
              for s in signals if s["id"] in by_id]
    insights = synthesize_insights(merged, min_cluster_size=2, min_sources=1)
    report["clusters"] = [
        {"category": i.get("category"), "severity": i.get("severity"),
         "n": len(i.get("signal_ids", [])), "title": i.get("title", "")}
        for i in insights
    ]
    report["signals_clustered"] = sum(len(i.get("signal_ids", [])) for i in insights)
    return report


def _print(report: dict) -> None:
    if report.get("error"):
        print(f"\n[{report['dataset']}] {report['error']}")
        return
    pol_ok, pol_n = report["sentiment_polar"]
    g_ok, g_n = report["grounded"]
    print("\n" + "=" * 72)
    print(f"{report['dataset']}  |  {report['n_signals']} signals  (model {report['model']})")
    if pol_n:
        print(f"  sentiment vs star-proxy (polar): {pol_ok}/{pol_n} ({pol_ok/pol_n:.0%})")
    print(f"  grounded: {g_ok}/{g_n}    urgency: {report['urgency_dist']}")
    print(f"  mean urgency by star (0=low..3=crit): {report['mean_urgency_by_star']}")
    print(f"  top tags: {report['top_tags']}")
    print(f"  CLUSTERS: {len(report['clusters'])}  "
          f"(covering {report['signals_clustered']}/{report['n_signals']} signals)")
    for c in report["clusters"][:6]:
        print(f"     - [{c['category']}/{c['severity']}] n={c['n']} :: {c['title'][:64]}")


def _resolve_paths(arg: str) -> list[Path]:
    p = Path(arg).expanduser()
    if p.is_dir():
        return sorted(p.glob("**/*combined*.csv"))
    return [p]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python3 -m app.evals.real_data <combined.csv | dir>", file=sys.stderr)
        return 2
    if not AI_MODEL:
        print("AI_MODEL unset — configure AI_BASE_URL/AI_API_KEY/AI_MODEL.", file=sys.stderr)
        return 2
    paths = _resolve_paths(argv[0])
    if not paths:
        print(f"no combined CSVs found under {argv[0]}", file=sys.stderr)
        return 2
    try:
        for path in paths:
            _print(evaluate(path))
    except AIProviderError as exc:
        print(f"LLM call failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
