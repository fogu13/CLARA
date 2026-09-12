"""Tests for run_live's report building: per-split paired A/B, OFF-arm
persistence, config provenance, held-out protection in the printed report and
the exemplars-disabled null case. No model is called: `enrich_signals` is
monkeypatched with fakes that return the golden labels (with chosen errors),
the pattern test_learning_influence.py uses."""

from __future__ import annotations

import hashlib
import json

import pytest

import app.evals.run_live as rl
from app.evals.harness import load_golden_set

GOLDEN = load_golden_set()
EXPECTED = {g["id"]: g["expected"] for g in GOLDEN}
HELD_OUT = [g["id"] for g in GOLDEN if g.get("split") == "held_out"]
OPTIMIZATION = [g["id"] for g in GOLDEN if g.get("split") == "optimization"]
EXEMPLARS = [{"text": "The signup button does nothing.", "sentiment": "negative",
              "urgency": "high", "tags": ["signup_failure"]},
             {"text": "Love the new dashboard.", "sentiment": "positive",
              "urgency": "low", "tags": ["praise"]}]
WRONG_ON_OFF = set(HELD_OUT[:5])  # the OFF arm gets sentiment wrong on 5 held-out items


def _fake_enrich(wrong_sentiment: set[str]):
    def fake(signals, *, exemplars=None, batch_size=25):
        out = []
        for s in signals:
            exp = EXPECTED[s["id"]]
            row = {"id": s["id"], **exp, "sentiment_score": 0.0}
            if s["id"] in wrong_sentiment:
                row["sentiment"] = "neutral" if exp["sentiment"] != "neutral" else "positive"
            out.append(row)
        return out
    return fake


@pytest.fixture
def scored_pair(monkeypatch):
    """OFF arm: held-out split loses 5 sentiment items; ON arm: perfect.
    The optimisation split is identical in both arms (no effect there)."""
    monkeypatch.setattr(rl, "enrich_signals", _fake_enrich(WRONG_ON_OFF))
    scored_off = rl._score_enrichment(exemplars=None)
    monkeypatch.setattr(rl, "enrich_signals", _fake_enrich(set()))
    scored_on = rl._score_enrichment(exemplars=EXEMPLARS)
    return scored_off, scored_on


@pytest.fixture
def report(scored_pair):
    scored_off, scored_on = scored_pair
    return rl.build_report(scored_on=scored_on, scored_off=scored_off, exemplars=EXEMPLARS)


class TestBySplitAB:
    def test_held_out_gains_and_optimisation_does_not(self, report) -> None:
        ab = report["by_split_ab"]
        assert set(ab) == {"held_out", "optimization"}
        ho = ab["held_out"]["sentiment"]
        assert ho["n"] == len(HELD_OUT) == 30
        assert ho["gained"] == 5 and ho["lost"] == 0
        assert ho["p_value"] == round(2 / 32, 4)  # exact McNemar, b=0, c=5
        assert ho["off_accuracy"] == round(25 / 30, 4) and ho["on_accuracy"] == 1.0
        assert ho["diff"] == round(5 / 30, 4)
        lo, hi = ho["diff_ci95"]
        assert 0.0 <= lo <= ho["diff"] <= hi <= 1.0
        opt = ab["optimization"]["sentiment"]
        assert opt["n"] == len(OPTIMIZATION) == 70
        assert opt["gained"] == 0 and opt["lost"] == 0 and opt["p_value"] == 1.0
        assert opt["diff"] == 0.0 and opt["diff_ci95"] == [0.0, 0.0]
        for split in ab.values():
            for metric in ("sentiment", "urgency", "tag_exact"):
                assert set(split[metric]) == {"n", "off_accuracy", "on_accuracy", "gained",
                                              "lost", "p_value", "diff", "diff_ci95"}

    def test_pooled_key_kept_and_labelled(self, report) -> None:
        assert report["enrichment_ab"] == report["enrichment_ab_pooled"]
        assert report["enrichment_ab"]["sentiment"]["gained"] == 5
        assert report["ab_scope_note"] == "pooled over optimisation and held-out items; exploratory"
        assert report["ab_note"] is None
        assert "held_out" in report["by_split_off"] and report["by_split_off"]["held_out"]["n"] == 30

    def test_paired_bootstrap_is_deterministic(self) -> None:
        off = [0, 1, 1, 0, 1, 1, 1, 0]
        on = [1, 1, 1, 0, 1, 1, 1, 1]
        assert rl._paired_bootstrap_diff_ci(off, on) == rl._paired_bootstrap_diff_ci(off, on)
        lo, hi = rl._paired_bootstrap_diff_ci(off, on)
        assert lo <= 0.25 <= hi


class TestOffArmPersistence:
    def test_per_item_off_and_failures_off_saved(self, report) -> None:
        assert len(report["per_item_off"]) == len(GOLDEN)
        assert len(report["per_item"]) == len(GOLDEN)
        assert {f["id"] for f in report["failures_off"]} == WRONG_ON_OFF
        assert all(f["split"] == "held_out" for f in report["failures_off"])
        assert report["failures"] == []

    def test_every_per_item_row_carries_its_split(self, report) -> None:
        for key in ("per_item", "per_item_off"):
            for row in report[key]:
                assert row["split"] in ("optimization", "held_out"), row
        by_id = {r["id"]: r["split"] for r in report["per_item_off"]}
        assert all(by_id[i] == "held_out" for i in HELD_OUT)


class TestConfig:
    def test_config_block_present_and_stable(self, scored_pair) -> None:
        scored_off, scored_on = scored_pair
        a = rl.build_report(scored_on=scored_on, scored_off=scored_off, exemplars=EXEMPLARS)["config"]
        b = rl.build_report(scored_on=scored_on, scored_off=scored_off, exemplars=EXEMPLARS)["config"]
        assert a == b
        assert set(a) >= {"model", "temperature", "exemplars_enabled", "exemplar_count",
                          "exemplars_sha256", "golden_set_sha256", "held_out_ids_sha256",
                          "split_counts", "harness_git_commit"}
        assert a["exemplars_enabled"] is True and a["exemplar_count"] == 2
        assert len(a["exemplars_sha256"]) == 64 and len(a["golden_set_sha256"]) == 64
        expected_ho = hashlib.sha256("\n".join(sorted(HELD_OUT)).encode()).hexdigest()
        assert a["held_out_ids_sha256"] == expected_ho
        assert a["split_counts"] == {"optimization": 70, "held_out": 30}
        # exemplar hash is over the sorted texts, so order does not matter
        rev = rl._run_config(list(reversed(EXEMPLARS)))
        assert rev["exemplars_sha256"] == a["exemplars_sha256"]
        assert rl._run_config(EXEMPLARS[:1])["exemplars_sha256"] != a["exemplars_sha256"]


class TestPrintedReport:
    def test_failure_table_withholds_held_out_by_default(self, scored_pair, capsys) -> None:
        # Make the ON arm fail on one optimisation item and one held-out item
        # so both kinds of failure exist in the printed table's source.
        scored_off, _ = scored_pair
        report = rl.build_report(scored_on=scored_off, scored_off=scored_off, exemplars=EXEMPLARS)
        report["_report_path"] = "<test>"
        rl._print_report(report)
        out = capsys.readouterr().out
        assert "95% Wilson interval" in out
        assert "95% bootstrap CI" not in out
        for hid in WRONG_ON_OFF:
            assert f"  {hid}:" not in out
        assert "withheld" in out and "--reveal-held-out" in out
        # aggregate held-out accuracies ARE printed
        assert "held-out split" in out

    def test_failure_table_reveals_held_out_with_flag(self, scored_pair, capsys) -> None:
        scored_off, _ = scored_pair
        report = rl.build_report(scored_on=scored_off, scored_off=scored_off, exemplars=EXEMPLARS)
        report["_report_path"] = "<test>"
        rl._print_report(report, reveal_held_out=True)
        out = capsys.readouterr().out
        for hid in WRONG_ON_OFF:
            assert f"  {hid}:" in out
        assert "withheld" not in out

    def test_hallucination_not_evaluated_prints(self, scored_pair, capsys) -> None:
        scored_off, scored_on = scored_pair
        scored_on["result"].hallucination_rate = None
        scored_on["result"].hallucination_eligible = 0
        report = rl.build_report(scored_on=scored_on, scored_off=scored_off, exemplars=EXEMPLARS)
        assert report["enrichment_on"]["hallucination_rate"] is None
        report["_report_path"] = "<test>"
        rl._print_report(report)
        assert "not evaluated" in capsys.readouterr().out


class TestExemplarsDisabled:
    def test_no_ab_of_identical_arms(self, scored_pair, capsys) -> None:
        _, scored_on = scored_pair
        report = rl.build_report(scored_on=scored_on, scored_off=None, exemplars=None)
        assert report["enrichment_ab"] is None
        assert report["enrichment_ab_pooled"] is None
        assert report["by_split_ab"] is None
        assert report["enrichment_off"] is None and report["per_item_off"] is None
        assert report["ab_note"] and "identical" in report["ab_note"]
        assert report["config"]["exemplars_enabled"] is False
        assert report["config"]["exemplars_sha256"] is None
        assert report["exemplars"] is False
        report["_report_path"] = "<test>"
        rl._print_report(report)
        assert "not run" in capsys.readouterr().out


class TestHeldOutLedger:
    def test_consultation_count_is_prior_flagged_rows_plus_one(self, tmp_path) -> None:
        path = tmp_path / "history.jsonl"
        assert rl._held_out_consultations(path) == 1  # no ledger yet
        rows = [{"kind": "eval", "held_out_scored": True},
                {"kind": "accept"},  # not a scoring row
                {"kind": "eval", "held_out_scored": True},
                {"kind": "eval"}]    # pre-flag row: not counted
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        assert rl._held_out_consultations(path) == 3
