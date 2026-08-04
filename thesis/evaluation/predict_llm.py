"""OPTIONAL LLM enrichment path — the artifact's `enrich-signal` logic, run offline.

Mirrors the platform's enrichment prompt so the gold-set scores the SAME reasoning the
product uses. Requires an OpenAI-compatible endpoint via env (as in CLARA's .env):
    AI_BASE_URL, AI_API_KEY, AI_MODEL
Writes evaluation/results/predictions_llm.json, which run_eval.py then scores beside the
baseline. No key -> prints how to set one and exits cleanly (the baseline still runs).

The corpus is public, paraphrased and de-identified, so sending it to a model endpoint
raises no personal-data concern; cost is ~190 short calls.
"""
from __future__ import annotations
import json
import os
import sys
import time
import urllib.request

from load_datasets import load

RESULTS = os.path.join(os.path.dirname(__file__), "results")

SYSTEM = (
    "You triage customer feedback for a feedback-to-action platform. "
    "For each signal return STRICT JSON with keys: sentiment (one of "
    "negative|neutral|positive), risk (one of low|medium|high|critical), "
    "theme (short snake_case), journey_stage (short snake_case), "
    "owner (short snake_case team). No prose, JSON only."
)

# Closed-set variant for journey_stage and owner. Free-form generation cannot be
# scored against the gold: the vocabularies barely intersect (journey ~15%,
# owner ~1% exact overlap), so an unconstrained run measures wording, not
# routing. Supplying the inventory matches how the platform is actually
# deployed — a workspace configures its owner list and journey taxonomy
# (§4.3, taxonomy governance) — and matches the closed-set treatment §3.5.2
# designed for exactly these two fields. Written to a SEPARATE predictions
# file so the production-config run backing §5A.3-5A.4 stays untouched.
SYSTEM_CONSTRAINED = (
    "You triage customer feedback for a feedback-to-action platform. "
    "For each signal return STRICT JSON with keys: journey_stage and owner. "
    "You MUST choose each value from the supplied inventory exactly as written. "
    "Do not invent new values. No prose, JSON only."
)


def _call(base, key, model, text, system=SYSTEM, prefix=""):
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{prefix}Signal: {text}"},
        ],
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # Gateways in front of OpenAI-compatible endpoints reject the default
            # Python-urllib agent (observed: 403/500 on every call).
            "User-Agent": "clara-thesis-eval/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return json.loads(data["choices"][0]["message"]["content"])


def main():
    base, key, model = (os.environ.get(k) for k in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL"))
    if not (base and key and model):
        print("LLM path skipped: set AI_BASE_URL, AI_API_KEY, AI_MODEL to run it.")
        print("The deterministic baseline in run_eval.py does not need this.")
        sys.exit(0)
    sigs = load()
    constrained = "--constrained" in sys.argv
    system, prefix, outfile = SYSTEM, "", "predictions_llm.json"
    if constrained:
        stages = sorted({s.journey_stage for s in sigs if s.journey_stage})
        owners = sorted({s.owner for s in sigs if s.owner})
        prefix = (f"Allowed journey_stage values: {', '.join(stages)}.\n"
                  f"Allowed owner values: {', '.join(owners)}.\n")
        system, outfile = SYSTEM_CONSTRAINED, "predictions_llm_taxonomy.json"
        print(f"constrained mode: {len(stages)} journey stages, {len(owners)} owners")

    out = []
    for i, s in enumerate(sigs, 1):
        # The endpoint 500s intermittently (~8% observed). Dropping those would
        # not lose a random sample — it would lose whichever signals happened to
        # fail — so retry rather than skip.
        for attempt in range(3):
            try:
                p = _call(base, key, model, s.text, system=system, prefix=prefix)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  [{i}/{len(sigs)}] {s.id} gave up after 3 tries: {e}")
                    p = None
                else:
                    time.sleep(2 ** attempt)
        if p is None:
            continue
        p["id"] = s.id
        out.append(p)
        if i % 20 == 0:
            print(f"  enriched {i}/{len(sigs)}")
    # Never write an empty/thin prediction file: run_eval.py would score it as a
    # result. A wholesale failure (bad key, blocked agent, endpoint down) must be
    # loud, not a silent zero.
    if len(out) < len(sigs) // 2:
        print(f"ABORT: only {len(out)}/{len(sigs)} signals enriched — not writing "
              "predictions. Fix the endpoint/credentials and re-run.")
        sys.exit(1)
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, outfile), "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {len(out)}/{len(sigs)} LLM predictions -> results/{outfile}")


if __name__ == "__main__":
    main()
