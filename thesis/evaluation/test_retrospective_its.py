"""Plain-assert checks for retrospective_its.py on synthetic dated signals (temp dir only).
Run: python3 thesis/evaluation/test_retrospective_its.py   (exits non-zero on failure)

A clear step change (8/day for 40 days, then 3/day for 25 days) must fit the segmented
regression (grade C, negative effect, interval excluding zero); a series with three
pre-intervention days must be refused (grade D, labelled delta, no interval).
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys
import tempfile
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrospective_its as R  # noqa: E402

T0 = datetime(2026, 5, 14, tzinfo=UTC)


def _write_signals(path: str, *, pre_days: int, post_days: int, pre_rate: int, post_rate: int) -> None:
    rng = random.Random(7)
    rows = []
    n = 0
    for day in range(-pre_days, post_days):
        rate = pre_rate if day < 0 else post_rate
        for _ in range(rate):
            n += 1
            stamp = T0 + timedelta(days=day, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            rows.append({"signal_id": f"S-{n}", "customer_id": f"C-{n % 50}", "source": "trustpilot",
                         "journey": "Checkout", "journey_stage": "Payment", "language": "en",
                         "timestamp": stamp.isoformat().replace("+00:00", "Z"),
                         "feedback_text": "payment failed at checkout"})
    # An unrelated journey that must be ignored by the scope filter.
    rows.append({"signal_id": "X-1", "customer_id": "C-1", "source": "trustpilot", "journey": "onboarding",
                 "journey_stage": "signup", "language": "en", "timestamp": T0.isoformat().replace("+00:00", "Z"),
                 "feedback_text": "signup is slow"})
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_step_change_is_fitted_and_graded_c() -> None:
    tmp = tempfile.mkdtemp(prefix="clara_retro_its_")
    csv_path = os.path.join(tmp, "signals.csv")
    _write_signals(csv_path, pre_days=40, post_days=25, pre_rate=8, post_rate=3)
    out = os.path.join(tmp, "readout.json")
    series = os.path.join(tmp, "series.csv")
    assert R.main(["--csv", csv_path, "--intervention", "2026-05-14", "--journey", "checkout", "--stage", "payment",
                   "--window", "25", "--out", out, "--series-out", series]) == 0
    report = json.load(open(out, encoding="utf-8"))
    assert report["result"]["method"] == "its" and report["evidence_grade"] == "C", report["result"]
    assert report["result"]["effect"] < -3 and report["result"]["ci_high"] < 0
    assert report["signals_in_scope"] == 40 * 8 + 25 * 3
    assert report["signals_pre_28d"] == 28 * 8 and report["signals_post_window"] == 25 * 3
    assert "does not attribute" in report["interpretation"]
    with open(series, encoding="utf-8") as fh:
        days = list(csv.DictReader(fh))
    assert len(days) == 65 and days[0]["signals"] == "8" and days[-1]["signals"] == "3"


def test_sparse_pre_window_is_refused_and_graded_d() -> None:
    tmp = tempfile.mkdtemp(prefix="clara_retro_its_")
    csv_path = os.path.join(tmp, "signals.csv")
    _write_signals(csv_path, pre_days=3, post_days=20, pre_rate=6, post_rate=2)
    out = os.path.join(tmp, "readout.json")
    assert R.main(["--csv", csv_path, "--intervention", "2026-05-14T00:00:00Z", "--journey", "checkout",
                   "--stage", "payment", "--window", "20", "--out", out]) == 0
    report = json.load(open(out, encoding="utf-8"))
    assert report["result"]["method"] == "delta_insufficient_data" and report["evidence_grade"] == "D"
    assert "ci_low" not in report["result"] and "Fit refused" in report["interpretation"]
    assert report["result"]["delta"] < 0


def test_unknown_scope_is_an_explicit_exit() -> None:
    tmp = tempfile.mkdtemp(prefix="clara_retro_its_")
    csv_path = os.path.join(tmp, "signals.csv")
    _write_signals(csv_path, pre_days=12, post_days=6, pre_rate=2, post_rate=2)
    try:
        R.main(["--csv", csv_path, "--intervention", "2026-05-14", "--journey", "billing", "--stage", "invoice",
                "--out", os.path.join(tmp, "x.json")])
    except SystemExit as exc:
        assert "no signals for journey" in str(exc)
    else:
        raise AssertionError("an unknown journey/stage must exit with a message")


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
