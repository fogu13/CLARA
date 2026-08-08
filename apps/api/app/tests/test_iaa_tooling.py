"""Kappa math + stratified export for the second-annotator workflow (R2)."""

from __future__ import annotations

import csv

from scripts.iaa_annotation import (
    URGENCY_ORDER,
    cohen_kappa,
    cmd_export,
    stratified_sample,
    weighted_kappa,
)


def test_perfect_agreement_is_one() -> None:
    labels = ["low", "high", "critical", "medium"] * 5
    assert cohen_kappa(labels, list(labels)) == 1.0
    assert weighted_kappa(labels, list(labels), URGENCY_ORDER) == 1.0


def test_kappa_corrects_for_chance() -> None:
    # 50% raw agreement on a two-label task with 50/50 marginals is chance -> kappa 0.
    a = ["low", "low", "high", "high"]
    b = ["low", "high", "low", "high"]
    assert abs(cohen_kappa(a, b)) < 1e-9


def test_weighted_kappa_penalizes_distance() -> None:
    gold = ["low", "low", "low", "low", "medium", "high", "critical", "critical"]
    near = ["medium", "low", "low", "low", "medium", "high", "critical", "high"]
    far = ["critical", "low", "low", "low", "medium", "high", "critical", "low"]
    near_k = weighted_kappa(gold, near, URGENCY_ORDER)
    far_k = weighted_kappa(gold, far, URGENCY_ORDER)
    assert near_k > far_k  # same number of disagreements, larger ordinal distance


def test_export_is_stratified_deterministic_and_blind(tmp_path) -> None:
    out = tmp_path / "sheet.csv"
    assert cmd_export(30, out) == 0
    rows = list(csv.DictReader(open(out)))
    assert len(rows) == 30
    assert {"id", "language", "text", "sentiment", "urgency"} == set(rows[0].keys())
    assert all(r["sentiment"] == "" and r["urgency"] == "" for r in rows)  # blind
    assert {r["language"] for r in rows} == {"en", "de"}  # both strata present
    from app.evals.harness import load_golden_set
    again = stratified_sample(load_golden_set(), 30)
    assert [r["id"] for r in rows] == [item["id"] for item in again]  # deterministic
