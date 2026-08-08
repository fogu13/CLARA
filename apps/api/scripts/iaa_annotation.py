"""Inter-annotator agreement tooling for the golden set (science review R2/F2).

Both evidence streams currently rest on single-annotator gold labels, and the
headline urgency claim is scored as nominal accuracy although urgency is
ordinal. This script closes both gaps with a second HUMAN annotator:

  export  — write a stratified subsample (language x urgency, deterministic
            seed) to CSV with the gold labels HIDDEN, for independent labelling.
  score   — read the completed CSV back and report per-field Cohen's kappa,
            plus quadratic-weighted kappa for urgency (an off-by-one
            medium/high disagreement must not count like low/critical).

Usage:
  cd apps/api
  python3 -m scripts.iaa_annotation export --n 30 --out /tmp/iaa_sheet.csv
  # ...second annotator fills sentiment/urgency columns without seeing gold...
  python3 -m scripts.iaa_annotation score --sheet /tmp/iaa_sheet_completed.csv

Interpretation guide (Landis & Koch bands, report alongside the raw value):
  <0 poor · 0-0.20 slight · 0.21-0.40 fair · 0.41-0.60 moderate ·
  0.61-0.80 substantial · 0.81-1.00 almost perfect.
The agreement target is the GOLD LABELS, so a low kappa is evidence of label
ambiguity, not annotator failure — adjudicate the disagreements and document.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

from app.evals.harness import load_golden_set

SEED = 20260808
URGENCY_ORDER = ["low", "medium", "high", "critical"]
SENTIMENTS = ["positive", "neutral", "negative", "mixed"]


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Nominal Cohen's kappa between two label vectors."""
    assert len(a) == len(b) and a
    n = len(a)
    labels = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def weighted_kappa(a: list[str], b: list[str], order: list[str]) -> float:
    """Quadratic-weighted kappa for ordinal labels."""
    assert len(a) == len(b) and a
    k = len(order)
    index = {lab: i for i, lab in enumerate(order)}
    n = len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[index[x]][index[y]] += 1 / n
    row = [sum(observed[i][j] for j in range(k)) for i in range(k)]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    weight = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    num = sum(weight[i][j] * observed[i][j] for i in range(k) for j in range(k))
    den = sum(weight[i][j] * row[i] * col[j] for i in range(k) for j in range(k))
    if den == 0:
        return 1.0
    return 1 - num / den


def stratified_sample(items: list[dict], n: int) -> list[dict]:
    """Deterministic sample stratified by (language, gold urgency)."""
    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in items:
        key = (item.get("language", "en"), item.get("expected", {}).get("urgency", "medium"))
        strata[key].append(item)
    rng = random.Random(SEED)
    for bucket in strata.values():
        rng.shuffle(bucket)
    # Round-robin across strata so small strata (DE critical) are represented.
    picked: list[dict] = []
    buckets = sorted(strata.items())
    i = 0
    while len(picked) < min(n, len(items)):
        key, bucket = buckets[i % len(buckets)]
        if bucket:
            picked.append(bucket.pop())
        i += 1
        if all(not b for _, b in buckets):
            break
    return picked


def cmd_export(n: int, out: Path) -> int:
    golden = load_golden_set()
    sample = stratified_sample(golden, n)
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        # Gold labels are deliberately absent — the second annotator must not see them.
        writer.writerow(["id", "language", "text", "sentiment", "urgency"])
        for item in sample:
            writer.writerow([item["id"], item.get("language", "en"), item["text"], "", ""])
    print(f"Wrote {len(sample)} items to {out}.")
    print("Second annotator: fill sentiment (positive|neutral|negative|mixed) and")
    print("urgency (low|medium|high|critical) WITHOUT consulting the golden set,")
    print("then run:  python3 -m scripts.iaa_annotation score --sheet <file>")
    return 0


def cmd_score(sheet: Path) -> int:
    golden = {item["id"]: item for item in load_golden_set()}
    ids: list[str] = []
    gold_sent, ann_sent, gold_urg, ann_urg = [], [], [], []
    skipped = 0
    with open(sheet, newline="") as f:
        for row in csv.DictReader(f):
            item = golden.get(row.get("id", ""))
            sent = (row.get("sentiment") or "").strip().lower()
            urg = (row.get("urgency") or "").strip().lower()
            if not item or sent not in SENTIMENTS or urg not in URGENCY_ORDER:
                skipped += 1
                continue
            ids.append(item["id"])
            gold_sent.append(item["expected"]["sentiment"])
            ann_sent.append(sent)
            gold_urg.append(item["expected"]["urgency"])
            ann_urg.append(urg)

    if len(gold_sent) < 10:
        print(f"Only {len(gold_sent)} usable rows ({skipped} skipped) — too few to report.",
              file=sys.stderr)
        return 1

    n = len(gold_sent)
    sent_agree = sum(1 for a, b in zip(gold_sent, ann_sent) if a == b) / n
    urg_agree = sum(1 for a, b in zip(gold_urg, ann_urg) if a == b) / n
    print(f"n = {n} double-coded items ({skipped} skipped)")
    print(f"sentiment: raw agreement {sent_agree:.2%}, Cohen's kappa {cohen_kappa(gold_sent, ann_sent):.3f}")
    print(f"urgency:   raw agreement {urg_agree:.2%}, Cohen's kappa {cohen_kappa(gold_urg, ann_urg):.3f},"
          f" quadratic-weighted kappa {weighted_kappa(gold_urg, ann_urg, URGENCY_ORDER):.3f}")
    disagreements = [
        (gid, g, a) for gid, g, a in zip(ids, gold_urg, ann_urg) if g != a
    ]
    if disagreements:
        print("\nUrgency disagreements to adjudicate (id, gold, annotator):")
    for gid, g, a in disagreements[:20]:
        print(f"  {gid}: {g} vs {a}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export")
    exp.add_argument("--n", type=int, default=30)
    exp.add_argument("--out", type=Path, default=Path("/tmp/iaa_sheet.csv"))
    sco = sub.add_parser("score")
    sco.add_argument("--sheet", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "export":
        return cmd_export(args.n, args.out)
    return cmd_score(args.sheet)


if __name__ == "__main__":
    raise SystemExit(main())
