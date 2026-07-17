"""Analyse the supplementary survey (instruments/survey.md) → per-hypothesis verdicts.

Reads the form's CSV export and computes, for each hypothesis, top-2-box agreement
(Agree + Strongly agree) plus the two non-Likert corroborations (H2 source count,
H8 measurement frequency), then prints/writes a confirmed / mixed / not-supported verdict.

The form's exact column headers vary by tool, so set them in COLS below (use the
question text Tally/Google Forms writes as the header). Run a logic check with no
data:  python evaluation/survey_analysis.py --demo
Real run:  python evaluation/survey_analysis.py path/to/responses.csv
"""
from __future__ import annotations
import csv, sys, os

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


def top2(rows, col):
    vals = [(r.get(col, "") or "").strip().lower() for r in rows]
    vals = [v for v in vals if v]
    if not vals:
        return None, 0
    return sum(v in AGREE for v in vals) / len(vals), len(vals)


def frac(rows, col, members):
    vals = [(r.get(col, "") or "").strip().lower() for r in rows]
    vals = [v for v in vals if v]
    members = {m.lower() for m in members}
    if not vals:
        return None, 0
    return sum(v in members for v in vals) / len(vals), len(vals)


def verdict(p, lo=0.40, hi=0.60):
    if p is None:
        return "no data"
    return "CONFIRMED" if p >= hi else ("MIXED/REFINE" if p >= lo else "NOT SUPPORTED")


def analyse(rows):
    # keep only qualified respondents if the screener column is present
    if any(COLS["screen"] in r for r in rows):
        rows = [r for r in rows if (r.get(COLS["screen"], "") or "").strip().lower() != "no"]
    out = []
    for hyp, col in [("H1", "H1"), ("H4", "H4"), ("H5", "H5"), ("H6", "H6"), ("H7", "H7")]:
        p, n = top2(rows, COLS[col])
        out.append((hyp, f"{p:.0%}" if p is not None else "—", n, verdict(p)))
    # H2 = likert AND >=50% report 4+ sources
    p2, n2 = top2(rows, COLS["H2_likert"]); pc, _ = frac(rows, COLS["H2_count"], MANY)
    v2 = "CONFIRMED" if (p2 and p2 >= 0.60 and pc and pc >= 0.50) else verdict(p2)
    out.append(("H2", f"{p2:.0%} agree / {pc:.0%} 4+ src" if p2 is not None else "—", n2, v2))
    # H8 = >=50% Never/Rarely measure AND >=60% value proving closure
    pr, _ = frac(rows, COLS["H8_freq"], RARE); pv, n8 = top2(rows, COLS["H8_likert"])
    v8 = "CONFIRMED" if (pr and pr >= 0.50 and pv and pv >= 0.60) else "MIXED/REFINE"
    out.append(("H8", f"{pr:.0%} rarely / {pv:.0%} value" if pv is not None else "—", n8, v8))
    return out


def main():
    if "--demo" in sys.argv:
        rows = [  # synthetic rows just to prove the logic runs
            {COLS["H1"]: "Strongly agree", COLS["H5"]: "Agree", COLS["H4"]: "Agree",
             COLS["H6"]: "Agree", COLS["H7"]: "Agree", COLS["H2_likert"]: "Agree",
             COLS["H2_count"]: "4-6", COLS["H8_likert"]: "Strongly agree", COLS["H8_freq"]: "Rarely"},
            {COLS["H1"]: "Agree", COLS["H5"]: "Neutral", COLS["H4"]: "Agree",
             COLS["H6"]: "Strongly agree", COLS["H7"]: "Agree", COLS["H2_likert"]: "Strongly agree",
             COLS["H2_count"]: "7+", COLS["H8_likert"]: "Agree", COLS["H8_freq"]: "Never"},
        ]
        res = analyse(rows)
        assert dict((h, v) for h, _, _, v in res)["H1"] == "CONFIRMED"
        assert dict((h, v) for h, _, _, v in res)["H2"] == "CONFIRMED"
        print("demo OK — logic runs:")
    else:
        if len(sys.argv) < 2:
            print(__doc__); sys.exit(1)
        with open(sys.argv[1], encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        res = analyse(rows)
    print(f"\n{'Hyp':4} {'Result':28} {'n':>4}  Verdict")
    for hyp, val, n, v in res:
        print(f"{hyp:4} {val:28} {n:>4}  {v}")
    if "--demo" not in sys.argv:
        os.makedirs("evaluation/results", exist_ok=True)
        with open("evaluation/results/survey_verdicts.csv", "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["hypothesis", "result", "n", "verdict"]); w.writerows(res)
        print("\nwrote evaluation/results/survey_verdicts.csv")


if __name__ == "__main__":
    main()
