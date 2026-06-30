"""Test the pure fabrication logic of the outcome simulation harness."""

from __future__ import annotations

from app.evals.simulate_outcomes import _fabricate_measured


def test_improved_drops_below_baseline() -> None:
    contract = {"baseline": 10.0}
    assert _fabricate_measured(contract, "improved", 0) < 10.0


def test_regressed_rises_above_baseline() -> None:
    contract = {"baseline": 10.0}
    assert _fabricate_measured(contract, "regressed", 0) > 10.0


def test_no_change_equals_baseline() -> None:
    contract = {"baseline": 10.0}
    assert _fabricate_measured(contract, "no_change", 0) == 10.0


def test_mixed_cycles_scenarios() -> None:
    contract = {"baseline": 10.0}
    vals = [_fabricate_measured(contract, "mixed", i) for i in range(3)]
    # one improved (<10), one no_change (==10), one regressed (>10)
    assert min(vals) < 10.0 and max(vals) > 10.0 and 10.0 in vals
