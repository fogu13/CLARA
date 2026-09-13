"""Plain-assert checks for survey_analysis.py's reporting tiers (no data, no pytest).
Run: python3 thesis/evaluation/test_survey_analysis.py   (exits non-zero on failure)

13 September 2026 review, finding F9: the script issued CONFIRMED from n = 10
while the pre-registered rule (manuscript §5B.1) issues verdicts only from
n = 40. The rows below are synthetic and exercise the tiers at n = 9, 10, 39
and 40, missing answers (each hypothesis at its own usable denominator), a
fragile interval, a failed corroboration and a corroborating item that did
not reach n = 40.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import survey_analysis as S  # noqa: E402

LIKERT = ("H1", "H4", "H5", "H6", "H7", "H2_likert", "H8_likert")


def rows(n: int, answer: str = "Agree", *, sources: str = "7+", freq: str = "Rarely") -> list[dict]:
    return [
        {**{S.COLS[k]: answer for k in LIKERT}, S.COLS["H2_count"]: sources, S.COLS["H8_freq"]: freq}
        for _ in range(n)
    ]


def verdicts(data: list[dict]) -> dict[str, str]:
    return {hyp: label for hyp, _, _, label in S.analyse(data)}


def ns(data: list[dict]) -> dict[str, int]:
    return {hyp: n for hyp, _, n, _ in S.analyse(data)}


def test_tiers_at_9_10_39_and_40() -> None:
    assert set(verdicts(rows(9)).values()) == {"INSUFFICIENT N"}
    assert set(verdicts(rows(10)).values()) == {"DESCRIPTIVE ONLY (n < 40)"}
    assert set(verdicts(rows(39)).values()) == {"DESCRIPTIVE ONLY (n < 40)"}
    got = verdicts(rows(40))
    assert got["H1"] == "CONFIRMED" and got["H2"] == "CONFIRMED" and got["H8"] == "CONFIRMED", got
    assert all(v == "CONFIRMED" for v in got.values()), got
    # Not-supported and mixed bands still exist at the verdict tier.
    assert set(verdicts(rows(40, "Disagree", sources="1-3", freq="Always")).values()) == {"NOT SUPPORTED"}
    mixed = rows(20, "Agree") + rows(20, "Disagree")  # 50%: mixed, and fragile at n = 40
    assert set(verdicts(mixed).values()) == {"MIXED/REFINE (fragile)"}


def test_each_hypothesis_uses_its_own_usable_denominator() -> None:
    data = rows(40)
    for r in data[:2]:
        r[S.COLS["H4"]] = ""  # two respondents skipped H4
    got, n = verdicts(data), ns(data)
    assert n["H4"] == 38 and got["H4"] == "DESCRIPTIVE ONLY (n < 40)", (n, got)
    assert n["H1"] == 40 and got["H1"] == "CONFIRMED"
    # A screener "No" removes the respondent from every denominator.
    data = rows(41)
    data[0][S.COLS["screen"]] = "No"
    assert set(ns(data).values()) == {40}


def test_corroboration_must_reach_the_verdict_n_and_can_fail() -> None:
    data = rows(40)
    for r in data[:5]:
        r[S.COLS["H8_freq"]] = ""  # the corroborating item has n = 35
    got = verdicts(data)
    assert got["H8"] == "DESCRIPTIVE ONLY (corroboration n < 40)", got
    assert got["H2"] == "CONFIRMED"
    failed = rows(40, freq="Always")  # nobody measures rarely: corroboration fails
    assert verdicts(failed)["H8"] == "MIXED/REFINE"
    few_sources = rows(40, sources="1-3")
    assert verdicts(few_sources)["H2"] == "MIXED/REFINE"


def test_fragile_intervals_are_flagged_only_when_a_verdict_is_issued() -> None:
    data = rows(25, "Agree") + rows(15, "Disagree")  # 62.5% agree: interval straddles 60%
    got = verdicts(data)
    assert got["H1"] == "CONFIRMED (fragile)", got
    thin = rows(9, "Agree") + rows(6, "Disagree")  # 60% at n = 15: descriptive, never fragile
    assert verdicts(thin)["H1"] == "DESCRIPTIVE ONLY (n < 40)"
    label, fragile = S.verdict(0.625, 40, S.wilson(25, 40))
    assert (label, fragile) == ("CONFIRMED", True)
    label, fragile = S.verdict(0.625, 39, S.wilson(25, 40))
    assert (label, fragile) == ("DESCRIPTIVE ONLY (n < 40)", False)
    assert S.verdict(None, 0, (0.0, 0.0)) == ("no data", False)


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
