"""Blind double-labelling of the risk seeds: draw the sample, then score kappa.

Step 1 (draw, no labels shown):
    python kappa_sample.py draw            -> results/kappa_sample.csv
    Columns: public_signal_id, text, blind_risk (empty). Fill blind_risk with
    low | medium | high | critical WITHOUT looking at the seed labels; a second
    person (or the author after a wash-out interval) does the labelling.

Step 2 (score):
    python kappa_sample.py score results/kappa_sample.csv
    -> Cohen's kappa (unweighted and linear-weighted) between the blind labels
       and risk_seed, the 4x4 confusion table, and the binary escalate agreement,
       written to results/kappa_risk.json and printed (a rating file named
       kappa_sample_<tag>.csv writes kappa_risk_<tag>.json instead). The rubric the
       labeller works from is results/kappa_labelling_instructions.md.

The sample is fixed by seed so the draw is reproducible (n = 40 from the 106
risk-labelled Trade Republic + Henkel signals). The seed labels never enter the
draw file, so the blind labeller cannot see them.
"""
from __future__ import annotations
import csv
import json
import os
import random
import sys

from load_datasets import load

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
RISK = ["low", "medium", "high", "critical"]
SEED = 20260905
N = 40


def draw() -> None:
    have = [s for s in load() if s.risk in RISK and s.text]
    sample = random.Random(SEED).sample(have, min(N, len(have)))
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "kappa_sample.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["public_signal_id", "text", "blind_risk"])
        for s in sample:
            w.writerow([s.id, s.text, ""])
    print(f"wrote {len(sample)} signals (seed labels withheld) -> {path}")


def score(path: str) -> None:
    from sklearn.metrics import cohen_kappa_score, confusion_matrix

    gold = {s.id: s.risk for s in load() if s.risk in RISK}
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))
    pairs = [(gold[r["public_signal_id"]], r["blind_risk"].strip().lower())
             for r in rows if r["public_signal_id"] in gold and r["blind_risk"].strip().lower() in RISK]
    if len(pairs) < 10:
        sys.exit(f"only {len(pairs)} usable rows; fill blind_risk with one of {RISK}")
    a = [g for g, _ in pairs]
    b = [x for _, x in pairs]

    def esc(v: str) -> bool:
        return v in ("high", "critical")

    out = {
        "n": len(pairs),
        "kappa_unweighted": round(cohen_kappa_score(a, b), 4),
        "kappa_linear_weighted": round(cohen_kappa_score(a, b, labels=RISK, weights="linear"), 4),
        "exact_agreement": round(sum(g == x for g, x in pairs) / len(pairs), 4),
        "escalate_agreement": round(sum(esc(g) == esc(x) for g, x in pairs) / len(pairs), 4),
        "confusion_seed_rows_blind_cols": {
            g: dict(zip(RISK, map(int, row)))
            for g, row in zip(RISK, confusion_matrix(a, b, labels=RISK))
        },
    }
    os.makedirs(RESULTS, exist_ok=True)
    # Output name follows the input name, so a second rating file (for example
    # kappa_sample_llm.csv, a model rating reported as cross-model agreement)
    # never overwrites the human result in kappa_risk.json.
    stem = os.path.splitext(os.path.basename(path))[0]
    out_name = "kappa_risk" + stem.replace("kappa_sample", "") + ".json"
    with open(os.path.join(RESULTS, out_name), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "draw":
        draw()
    elif len(sys.argv) >= 3 and sys.argv[1] == "score":
        score(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
