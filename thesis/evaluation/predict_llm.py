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


def _call(base, key, model, text):
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Signal: {text}"},
        ],
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
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
    out = []
    for i, s in enumerate(sigs, 1):
        try:
            p = _call(base, key, model, s.text)
        except Exception as e:  # keep going; partial cache is still useful
            print(f"  [{i}/{len(sigs)}] {s.id} error: {e}")
            continue
        p["id"] = s.id
        out.append(p)
        if i % 20 == 0:
            print(f"  enriched {i}/{len(sigs)}")
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "predictions_llm.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {len(out)} LLM predictions -> results/predictions_llm.json")


if __name__ == "__main__":
    main()
