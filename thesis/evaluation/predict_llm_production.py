"""Run the thesis corpus through CLARA's PRODUCTION enrichment path (decision 2a).

`predict_llm.py` scores a generic three-class prompt. This script scores the
artifact itself: the same `enrich_signals` function the platform calls (batching,
system prompt, tool schema, injection guard, output sanitiser, tag canonicaliser,
PII redaction at the model boundary), with the same configuration flags a
deployment would have. The two runs answer different questions and are scored
under different keys by run_eval.py (`*_llm` vs `*_llm_production`).

Pre-registered scoring rules (fixed here before the run, not after):
  sentiment  production emits positive | neutral | negative | mixed; the gold is
             three-class (from star ratings). PRIMARY rule: mixed -> neutral.
             The raw label is kept as `sentiment_raw` so run_eval.py also reports
             the sensitivity variant that drops the mixed items.
  risk       production emits urgency on the same four-point scale as the gold
             risk_seed (low | medium | high | critical); it is scored as `risk`
             unchanged, with the raw value kept as `urgency_raw`.
  missing    an item the model dropped (sanitiser rejection, failed batch) is
             NOT imputed; it is absent from the file and run_eval.py scores the
             intersection, reporting the n it actually scored.

Requires the API package importable (run from the repo root, or set PYTHONPATH
to apps/api) and the same env as the platform: AI_BASE_URL, AI_API_KEY, AI_MODEL.
Flags: --exemplars auto|on|off (default auto = ENRICH_FEWSHOT, i.e. production
default), --batch-size N (default 25 = production), --limit N (smoke test).

Writes evaluation/results/predictions_llm_production.json and a sidecar
predictions_llm_production.meta.json recording model, flags, timestamp and n.
The corpus is public, paraphrased and de-identified; cost is ~8 batched calls.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "apps", "api"))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")

SENTIMENT_PRIMARY_RULE = {  # pre-registered: mixed -> neutral
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "mixed": "neutral",
}


def map_enrichment(enrichment: dict) -> dict:
    """Production enrichment dict -> the prediction row run_eval.py scores.

    Pure so it can be tested without an endpoint. Unknown/None sentiment stays
    None (scored as a miss by run_eval.py's `or "neutral"` default, and counted
    in sentiment_raw_label_counts), never silently coerced to a class.
    """
    raw_sentiment = enrichment.get("sentiment")
    raw_urgency = enrichment.get("urgency")
    return {
        "id": str(enrichment["id"]),
        "sentiment": SENTIMENT_PRIMARY_RULE.get(raw_sentiment) if raw_sentiment else None,
        "sentiment_raw": raw_sentiment,
        "sentiment_score": enrichment.get("sentiment_score"),
        "risk": raw_urgency,
        "urgency_raw": raw_urgency,
        "tags": list(enrichment.get("tags") or []),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exemplars", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--batch-size", type=int, default=25)
    ap.add_argument("--limit", type=int, default=0, help="score only the first N signals (smoke test)")
    args = ap.parse_args()

    missing = [k for k in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL") if not os.environ.get(k)]
    if missing:
        print(f"production path skipped: set {', '.join(missing)} (same values as the platform's .env).")
        return 0

    sys.path.insert(0, API_DIR)
    from load_datasets import load  # noqa: E402  (thesis corpus)
    from app.services.ai import effective_model  # noqa: E402
    from app.services.enrichment import enrich_signals  # noqa: E402
    from app.services.exemplar_store import fewshot_enabled, load_exemplars  # noqa: E402

    sigs = load()
    if args.limit:
        sigs = sigs[: args.limit]
    use_exemplars = {"auto": fewshot_enabled(), "on": True, "off": False}[args.exemplars]
    exemplars = load_exemplars() if use_exemplars else None
    signals = [{"id": s.id, "text": s.text} for s in sigs if s.text]
    print(f"production path: {len(signals)} signals, model={effective_model()}, "
          f"exemplars={'on' if use_exemplars else 'off'}, batch_size={args.batch_size}")

    t0 = time.time()
    # Production configuration: no journey inventory and no workspace vocabulary
    # are passed, matching a fresh workspace (closed-set routing is a flag-on
    # iteration and is not part of the §5A claim).
    enrichments = enrich_signals(signals, batch_size=args.batch_size, exemplars=exemplars)
    elapsed = time.time() - t0
    rows = [map_enrichment(e) for e in enrichments]
    wanted = {s["id"] for s in signals}
    rows = [r for r in rows if r["id"] in wanted]

    # Never write a thin prediction file: run_eval.py would score it as a result.
    if len(rows) < len(signals) // 2:
        print(f"ABORT: only {len(rows)}/{len(signals)} signals enriched — not writing predictions.")
        return 1
    os.makedirs(RESULTS, exist_ok=True)
    out = os.path.join(RESULTS, "predictions_llm_production.json")
    with open(out, "w") as fh:
        json.dump(rows, fh, indent=2)
    meta = {
        "written_at": datetime.now(timezone.utc).isoformat(),
        "model": effective_model(),
        "exemplars": use_exemplars,
        "batch_size": args.batch_size,
        "n_signals": len(signals),
        "n_scored": len(rows),
        "n_missing": len(signals) - len(rows),
        "elapsed_s": round(elapsed, 1),
        "sentiment_rule": "primary: mixed -> neutral (pre-registered); sensitivity: drop mixed",
        "risk_rule": "production urgency scored as risk, unchanged",
        "raw_sentiment_counts": {
            k: sum(1 for r in rows if r["sentiment_raw"] == k)
            for k in ("positive", "neutral", "negative", "mixed", None)
        },
    }
    with open(os.path.join(RESULTS, "predictions_llm_production.meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2, default=str)
    print(f"wrote {len(rows)}/{len(signals)} production predictions -> {out}")
    print(json.dumps(meta, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
