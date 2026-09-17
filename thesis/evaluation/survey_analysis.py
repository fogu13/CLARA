"""Analyse the supplementary survey (instruments/survey.md) -> per-hypothesis verdicts.

Reads the form's CSV export and computes, for each hypothesis, top-2-box agreement
(Agree + Strongly agree) with a 95% Wilson interval, plus the two non-Likert
corroborations (H2 source count, H8 measurement frequency), then prints/writes a
verdict per hypothesis.

Reporting tiers (pre-registered in the manuscript, §5B.0/§5B.1, and enforced
here — 13 September 2026 review, finding F9):
  n < 10          INSUFFICIENT N — only the number of answers is reported
  10 <= n < 40    DESCRIPTIVE ONLY — the proportion and its interval are
                  reported; no hypothesis verdict is issued
  n >= 40         a verdict is issued (rules below)
where n is each hypothesis's own usable denominator (the answers that item
received); for H2 and H8 the corroborating item must reach n >= 40 as well.

Verdict rules (n >= 40):
  CONFIRMED       top-2-box >= 60%   (and, for H2/H8, the corroboration holds too)
  MIXED/REFINE    40% <= top-2-box < 60%, or the Likert bar is met but the
                  corroboration fails
  NOT SUPPORTED   top-2-box < 40%
The Wilson interval is reported next to every proportion; a verdict whose interval
straddles the threshold it was decided on is marked "fragile" in the output.

The form's exact column headers vary by tool, so set them in COLS below (use the
question text Tally/Google Forms writes as the header). Run a logic check with no
data:  python evaluation/survey_analysis.py --demo
Real run:  python evaluation/survey_analysis.py path/to/responses.csv
"""
from __future__ import annotations
import csv, math, sys, os

# --- Map each item to its exact CSV column header (edit after you build the form) ---
COLS = {
    "H1": "We often understand what customers want but struggle to actually act on it.",
    "H2_likert": "Our customer feedback is spread across so many tools that it's hard to see the priorities in one place.",
    "H5": "When feedback calls for action, it's often unclear who owns the response.",
    "H4": "Where in the customer journey a problem happens changes how much we prioritise it.",
    "H6": "I'd be more comfortable letting software act on feedback automatically if a human approved the riskier actions first.",
    "H7": "I wouldn't trust software to act on feedback unless I could see and audit exactly what it did and why.",
    "H8_likert": "Being able to prove an action actually resolved the customer's problem would be valuable to me.",
    "H2_count": "Roughly how many separate tools/sources does your customer feedback live in?",
    "H8_freq": "After your team acts on customer feedback, how often do you measure whether it actually resolved the issue?",
    "screen": "Do you work with customer feedback (surveys, tickets, reviews, etc.)?",
}
AGREE = {"agree", "strongly agree"}
RARE = {"never", "rarely"}
MANY = {"4-6", "4–6", "7+"}
HI, LO = 0.60, 0.40          # top-2-box thresholds
H2_CORROBORATION = 0.50      # share reporting 4+ sources
H8_CORROBORATION = 0.50      # share measuring never/rarely
MIN_N = 10                   # below this only the number of answers is reported
VERDICT_MIN_N = 40           # the pre-registered n from which a verdict is issued
DESCRIPTIVE = "DESCRIPTIVE ONLY (n < %d)"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _share(rows, col, members):
    vals = [(r.get(col, "") or "").strip().lower() for r in rows]
    vals = [v for v in vals if v]
    members = {m.lower() for m in members}
    if not vals:
        return None, 0, (0.0, 0.0)
    k = sum(v in members for v in vals)
    return k / len(vals), len(vals), wilson(k, len(vals))


def top2(rows, col):
    return _share(rows, col, AGREE)


def frac(rows, col, members):
    return _share(rows, col, members)


def band(p):
    return "CONFIRMED" if p >= HI else ("MIXED/REFINE" if p >= LO else "NOT SUPPORTED")


def verdict(p, n, ci, corroborated=None, min_n=MIN_N, verdict_n=VERDICT_MIN_N,
            corroboration_n=None):
    """Tiered label from the Likert proportion, its n, its interval and (for
    H2/H8) the corroboration flag and the corroborating item's own n.
    Returns (label, fragile); fragile is only ever True when a verdict was
    issued."""
    if p is None:
        return "no data", False
    if n < min_n:
        return "INSUFFICIENT N", False
    if n < verdict_n:
        return DESCRIPTIVE % verdict_n, False
    if corroborated is not None and (corroboration_n is None or corroboration_n < verdict_n):
        # The corroborating item did not reach the pre-registered n: the
        # Likert bar alone cannot decide H2/H8.
        return f"DESCRIPTIVE ONLY (corroboration n < {verdict_n})", False
    v = band(p)
    if corroborated is False and v == "CONFIRMED":
        v = "MIXED/REFINE"  # the Likert bar alone does not confirm H2/H8
    threshold = HI if p >= HI else (LO if p >= LO else LO)
    fragile = ci[0] < threshold <= ci[1] or ci[0] <= threshold < ci[1]
    return v, fragile


def _fmt(p, ci):
    return f"{p:.0%} [{ci[0]:.0%}-{ci[1]:.0%}]" if p is not None else "—"


def analyse(rows, min_n=MIN_N, verdict_n=VERDICT_MIN_N):
    # keep only qualified respondents if the screener column is present
    if any(COLS["screen"] in r for r in rows):
        rows = [r for r in rows if (r.get(COLS["screen"], "") or "").strip().lower() != "no"]
    out = []
    for hyp in ("H1", "H4", "H5", "H6", "H7"):
        p, n, ci = top2(rows, COLS[hyp])
        v, fragile = verdict(p, n, ci, min_n=min_n, verdict_n=verdict_n)
        out.append((hyp, _fmt(p, ci), n, v + (" (fragile)" if fragile else "")))
    # H2 = Likert band AND >= 50% report 4+ sources (each at its own usable n)
    p2, n2, ci2 = top2(rows, COLS["H2_likert"])
    pc, nc, cic = frac(rows, COLS["H2_count"], MANY)
    corr2 = (pc is not None and pc >= H2_CORROBORATION)
    v2, fragile2 = verdict(p2, n2, ci2, corroborated=corr2, min_n=min_n,
                           verdict_n=verdict_n, corroboration_n=nc)
    out.append(("H2", f"{_fmt(p2, ci2)} agree / {_fmt(pc, cic)} 4+ src", n2,
                v2 + (" (fragile)" if fragile2 else "")))
    # H8 = Likert band (value of proving closure) AND >= 50% never/rarely measure
    pv, n8, civ = top2(rows, COLS["H8_likert"])
    pr, nr, cir = frac(rows, COLS["H8_freq"], RARE)
    corr8 = (pr is not None and pr >= H8_CORROBORATION)
    v8, fragile8 = verdict(pv, n8, civ, corroborated=corr8, min_n=min_n,
                           verdict_n=verdict_n, corroboration_n=nr)
    out.append(("H8", f"{_fmt(pr, cir)} rarely / {_fmt(pv, civ)} value", n8,
                v8 + (" (fragile)" if fragile8 else "")))
    return out


def _demo_rows(copies: int = 1):
    """Twelve synthetic rows that exercise every branch (repeated ``copies``
    times to reach the verdict tier); not data."""
    agree = ["Strongly agree", "Agree", "Agree", "Agree", "Strongly agree", "Agree",
             "Agree", "Neutral", "Agree", "Agree", "Disagree", "Agree"]      # 10/12 agree
    mixed = ["Agree", "Neutral", "Agree", "Disagree", "Agree", "Neutral",
             "Agree", "Agree", "Disagree", "Neutral", "Agree", "Disagree"]   # 6/12 agree
    weak = ["Disagree", "Neutral", "Agree", "Disagree", "Disagree", "Neutral",
            "Disagree", "Agree", "Disagree", "Neutral", "Disagree", "Disagree"]  # 2/12
    sources = ["4-6", "7+", "1-3", "4-6", "4-6", "7+", "1-3", "4-6", "7+", "4-6", "1-3", "4-6"]  # 9/12
    freq = ["Rarely", "Never", "Sometimes", "Rarely", "Always", "Sometimes",
            "Rarely", "Never", "Sometimes", "Often", "Rarely", "Sometimes"]      # 6/12 -> 50%
    rows = []
    for _ in range(copies):
        for i in range(12):
            rows.append({COLS["H1"]: agree[i], COLS["H4"]: mixed[i], COLS["H5"]: weak[i],
                         COLS["H6"]: agree[i], COLS["H7"]: agree[i],
                         COLS["H2_likert"]: agree[i], COLS["H2_count"]: sources[i],
                         COLS["H8_likert"]: agree[i], COLS["H8_freq"]: freq[i]})
    return rows


def main():
    if "--demo" in sys.argv:
        # Twelve rows sit in the descriptive tier: no verdict.
        got = {h: v for h, _, _, v in analyse(_demo_rows())}
        assert all(v.startswith("DESCRIPTIVE ONLY") for v in got.values()), got
        # Forty-eight rows (four copies) reach the verdict tier.
        res = analyse(_demo_rows(copies=4))
        got = {h: v for h, _, _, v in res}
        assert got["H1"].startswith("CONFIRMED"), got
        assert got["H4"].startswith("MIXED/REFINE"), got
        assert got["H5"].startswith("NOT SUPPORTED"), got
        assert got["H2"].startswith("CONFIRMED"), got
        assert got["H8"].startswith("CONFIRMED"), got
        # Corroboration failing turns a confirmed Likert bar into MIXED/REFINE,
        # and too few answers into INSUFFICIENT N.
        rows = _demo_rows(copies=4)
        for r in rows:
            r[COLS["H8_freq"]] = "Always"
        assert {h: v for h, _, _, v in analyse(rows)}["H8"].startswith("MIXED/REFINE")
        assert {h: v for h, _, _, v in analyse(rows[:4])}["H1"] == "INSUFFICIENT N"
        print("demo OK — logic runs:")
    else:
        if len(sys.argv) < 2:
            print(__doc__); sys.exit(1)
        with open(sys.argv[1], encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        res = analyse(rows)
    print(f"\n{'Hyp':4} {'Result (95% Wilson)':44} {'n':>4}  Verdict")
    for hyp, val, n, v in res:
        print(f"{hyp:4} {val:44} {n:>4}  {v}")
    if "--demo" not in sys.argv:
        os.makedirs("evaluation/results", exist_ok=True)
        with open("evaluation/results/survey_verdicts.csv", "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["hypothesis", "result", "n", "verdict"]); w.writerows(res)
        print("\nwrote evaluation/results/survey_verdicts.csv")


if __name__ == "__main__":
    main()
