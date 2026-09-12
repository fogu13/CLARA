"""Tests for run_live's report building: per-split paired A/B, OFF-arm
persistence, config provenance, held-out protection (sidecar, reveal flag,
consultation count), the between-run comparison the accept gate reads
(`compare_reports` / `vs_baseline` with its guards), the published snapshot and
ledger row, and the exemplars-disabled / empty null case. No model is called:
`enrich_signals` is monkeypatched with fakes that return the golden labels
(with chosen errors), the pattern test_learning_influence.py uses."""

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


def _score(monkeypatch, wrong: set[str], exemplars):
    monkeypatch.setattr(rl, "enrich_signals", _fake_enrich(wrong))
    return rl._score_enrichment(exemplars=exemplars)


@pytest.fixture
def scored_pair(monkeypatch):
    """OFF arm: held-out split loses 5 sentiment items; ON arm: perfect.
    The optimisation split is identical in both arms (no effect there)."""
    scored_off = _score(monkeypatch, WRONG_ON_OFF, None)
    scored_on = _score(monkeypatch, set(), EXEMPLARS)
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
        # exemplar hash is order-free
        rev = rl._run_config(list(reversed(EXEMPLARS)))
        assert rev["exemplars_sha256"] == a["exemplars_sha256"]
        assert rl._run_config(EXEMPLARS[:1])["exemplars_sha256"] != a["exemplars_sha256"]

    def test_exemplar_hash_covers_labels_not_only_texts(self) -> None:
        """C1: same texts, different labels -> different hash (a label edit
        is a change to the exemplars the loop must be able to see)."""
        base = rl._run_config(EXEMPLARS)["exemplars_sha256"]
        relabelled = [dict(EXEMPLARS[0], urgency="critical"), EXEMPLARS[1]]
        retagged = [EXEMPLARS[0], dict(EXEMPLARS[1], tags=["positive_trend"])]
        resentimented = [dict(EXEMPLARS[0], sentiment="mixed"), EXEMPLARS[1]]
        for variant in (relabelled, retagged, resentimented):
            assert [e["text"] for e in variant] == [e["text"] for e in EXEMPLARS]
            assert rl._run_config(variant)["exemplars_sha256"] != base
        # order invariance kept, and the hash is of the canonical objects
        assert rl._exemplars_sha256(list(reversed(relabelled))) == rl._exemplars_sha256(relabelled)
        canonical = json.dumps(sorted(EXEMPLARS, key=lambda e: (e["text"], json.dumps(e, sort_keys=True))),
                               sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert base == hashlib.sha256(canonical.encode()).hexdigest()


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

    def test_split_report_prints_sidecar_failures_only_on_reveal(self, scored_pair, capsys) -> None:
        scored_off, _ = scored_pair
        main, sidecar = rl.split_held_out(
            rl.build_report(scored_on=scored_off, scored_off=scored_off, exemplars=EXEMPLARS))
        main["_report_path"] = "<test>"
        main["held_out_sidecar"] = "<sidecar>"
        rl._print_report(main, held_out=sidecar)
        out = capsys.readouterr().out
        assert "5 held-out failure(s) withheld" in out and "held_out_revealed" in out
        for hid in WRONG_ON_OFF:
            assert f"  {hid}:" not in out
        rl._print_report(main, held_out=sidecar, reveal_held_out=True)
        out = capsys.readouterr().out
        for hid in WRONG_ON_OFF:
            assert f"  {hid}:" in out

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

    def test_empty_exemplar_list_is_disabled(self, scored_pair, monkeypatch) -> None:
        """C16: an enabled-but-empty list changes nothing in the prompt, so
        it is exactly the disabled case — no second arm, A/B null."""
        scored_off, scored_on = scored_pair
        for off in (None, scored_off):
            report = rl.build_report(scored_on=scored_on, scored_off=off, exemplars=[])
            assert report["enrichment_ab"] is None and report["by_split_ab"] is None
            assert report["enrichment_off"] is None and report["per_item_off"] is None
            assert report["exemplars"] is False
            assert report["config"]["exemplars_enabled"] is False
            assert report["config"]["exemplar_count"] == 0
            assert report["config"]["exemplars_sha256"] is None
            assert report["ab_note"] == rl.AB_DISABLED_NOTE
        monkeypatch.setattr(rl, "fewshot_enabled", lambda: True)
        monkeypatch.setattr(rl, "load_exemplars", lambda: [])
        assert rl._exemplars() is None
        monkeypatch.setattr(rl, "load_exemplars", lambda: EXEMPLARS)
        assert rl._exemplars() == EXEMPLARS


class TestHeldOutLedger:
    def test_consultation_count_is_every_prior_eval_row_plus_one(self, tmp_path) -> None:
        """C17: every prior kind:eval row scored the held-out split (the
        runner always enriched the whole set), flagged or not."""
        path = tmp_path / "history.jsonl"
        assert rl._held_out_consultations(path) == 1  # no ledger yet
        rows = [{"kind": "eval", "held_out_scored": True},
                {"kind": "accept"},  # not a scoring row
                {"kind": "reject", "held_out_scored": True},  # not an eval row either
                {"kind": "eval", "held_out_scored": True},
                {"kind": "eval"}]    # pre-flag eval row: counted
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        assert rl._held_out_consultations(path) == 4

    def test_ledger_row_records_reveal_guards_and_hashes(self, report) -> None:
        """C3 / C14: the ledger row carries held_out_revealed, both guards and
        the config hashes."""
        report["held_out_sidecar"] = "/x/report.held_out.json"
        for revealed in (True, False):
            row = rl.ledger_row(report, held_out_consultations=7, held_out_revealed=revealed)
            assert row["held_out_revealed"] is revealed
            assert row["held_out_scored"] is True and row["held_out_consultations"] == 7
            assert row["kind"] == "eval"
            assert row["hallucination_rate"] == report["enrichment_on"]["hallucination_rate"]
            assert row["hallucination_eligible"] == report["enrichment_on"]["hallucination_eligible"]
            assert row["hallucination_excluded"] == report["enrichment_on"]["hallucination_excluded"]
            assert row["pii_leak_count"] == 0
            cfg = report["config"]
            assert row["golden_set_sha256"] == cfg["golden_set_sha256"]
            assert row["held_out_ids_sha256"] == cfg["held_out_ids_sha256"]
            assert row["exemplars_sha256"] == cfg["exemplars_sha256"]
            assert row["held_out_sidecar"] == "/x/report.held_out.json"
            json.dumps(row)


class TestHeldOutSidecar:
    """C3: held-out per-item rows leave the main report for a sidecar."""

    def test_split_moves_every_held_out_row(self, report) -> None:
        main, sidecar = rl.split_held_out(report)
        held = set(HELD_OUT)
        for key in rl.PER_ITEM_KEYS:
            assert not any(r["id"] in held for r in main[key]), key
            assert all(r["split"] == "held_out" for r in sidecar[key]), key
        assert {r["id"] for r in main["per_item"]} == set(OPTIMIZATION)
        assert {r["id"] for r in sidecar["per_item"]} == held
        assert {r["id"] for r in sidecar["per_item_off"]} == held
        assert {f["id"] for f in sidecar["failures_off"]} == WRONG_ON_OFF
        assert main["failures_off"] == [] and main["failures"] == []
        assert sidecar["kind"] == "eval_held_out" and sidecar["config"] == report["config"]
        # the main report keeps the held-out AGGREGATES
        assert main["by_split"]["held_out"]["n"] == 30
        assert main["by_split_ab"]["held_out"]["sentiment"]["gained"] == 5
        assert "held_out" not in json.dumps({k: main[k] for k in rl.PER_ITEM_KEYS})

    def test_null_keys_stay_null(self, scored_pair) -> None:
        _, scored_on = scored_pair
        main, sidecar = rl.split_held_out(
            rl.build_report(scored_on=scored_on, scored_off=None, exemplars=None))
        assert main["per_item_off"] is None and sidecar["per_item_off"] is None
        assert main["failures_off"] is None and sidecar["failures_off"] is None
        assert len(main["per_item"]) == 70 and len(sidecar["per_item"]) == 30

    def test_load_report_attaches_sidecar(self, report, tmp_path) -> None:
        main, sidecar = rl.split_held_out(report)
        path = tmp_path / "report_x.json"
        side = tmp_path / "report_x.held_out.json"
        main["held_out_sidecar"] = str(side)
        path.write_text(json.dumps(main))
        side.write_text(json.dumps(sidecar))
        loaded = rl.load_report(path)
        assert {r["id"] for r in loaded["_held_out"]["per_item"]} == set(HELD_OUT)
        assert {r["id"] for r in loaded["per_item"]} == set(OPTIMIZATION)
        side.unlink()
        assert "_held_out" not in rl.load_report(path)


class TestCompareReports:
    """C2 / C15: the between-run comparison the accept gate reads."""

    @pytest.fixture
    def regression(self, monkeypatch):
        """Baseline: ON perfect. New run: ON loses 8 optimisation items, while
        its OFF arm loses 15 optimisation + 5 held-out items — so the in-run
        ON-vs-OFF A/B on the optimisation split is still a significant gain
        (7 gained, 0 lost) although the ON arm REGRESSED against baseline."""
        base_off = _score(monkeypatch, WRONG_ON_OFF, None)
        base_on = _score(monkeypatch, set(), EXEMPLARS)
        baseline = rl.build_report(scored_on=base_on, scored_off=base_off, exemplars=EXEMPLARS)
        new_off = _score(monkeypatch, set(OPTIMIZATION[:15]) | WRONG_ON_OFF, None)
        new_on = _score(monkeypatch, set(OPTIMIZATION[:8]), EXEMPLARS)
        new = rl.build_report(scored_on=new_on, scored_off=new_off, exemplars=EXEMPLARS)
        return baseline, new

    def test_optimisation_regression_is_visible_only_between_runs(self, regression) -> None:
        baseline, new = regression
        in_run = new["by_split_ab"]["optimization"]["sentiment"]
        assert in_run["gained"] == 7 and in_run["lost"] == 0 and in_run["p_value"] < 0.05
        vs = rl.compare_reports(baseline, new)
        opt = vs["optimization"]["sentiment"]
        assert opt["n"] == 70
        assert opt["lost"] == 8 and opt["gained"] == 0
        assert opt["lost"] > opt["gained"]
        assert opt["p_value"] == round(2 / 256, 4) and opt["p_value"] < 0.05
        assert opt["baseline_accuracy"] == 1.0 and opt["new_accuracy"] == round(62 / 70, 4)
        assert opt["diff"] == round(-8 / 70, 4)
        lo, hi = opt["diff_ci95"]
        assert lo <= opt["diff"] <= hi < 0.0
        assert set(opt) == {"n", "baseline_accuracy", "new_accuracy", "gained", "lost",
                            "p_value", "diff", "diff_ci95"}
        for metric in ("urgency", "tag_exact"):
            assert vs["optimization"][metric]["gained"] == vs["optimization"][metric]["lost"] == 0
        # held-out block: an aggregate (n=30, no change), present because the
        # unsplit reports carry the rows
        assert vs["held_out"]["sentiment"] == {
            "n": 30, "baseline_accuracy": 1.0, "new_accuracy": 1.0, "gained": 0, "lost": 0,
            "p_value": 1.0, "diff": 0.0, "diff_ci95": [0.0, 0.0]}
        assert vs["baseline"]["n_joined"] == 100 and vs["baseline"]["timestamp"] == baseline["timestamp"]
        json.dumps(vs)

    def test_hash_mismatch_is_refused(self, regression) -> None:
        baseline, new = regression
        for key in rl.COMPARABLE_HASHES:
            tampered = {**new, "config": {**new["config"], key: "0" * 64}}
            with pytest.raises(ValueError, match=key):
                rl.compare_reports(baseline, tampered)
            with pytest.raises(ValueError, match="missing"):
                rl.compare_reports(baseline, {**new, "config": {**new["config"], key: None}})
        with pytest.raises(ValueError, match="missing"):
            rl.compare_reports({**baseline, "config": None}, new)

    def test_held_out_aggregate_comes_from_the_sidecar(self, regression) -> None:
        baseline, new = regression
        b_main, b_side = rl.split_held_out(baseline)
        n_main, n_side = rl.split_held_out(new)
        # main reports alone: no held-out rows to join -> no held_out block
        vs = rl.compare_reports(b_main, n_main)
        assert "held_out" not in vs and vs["optimization"]["sentiment"]["lost"] == 8
        assert vs["baseline"]["n_joined"] == 70
        # sidecars attached (as load_report does): the aggregate appears
        vs = rl.compare_reports({**b_main, "_held_out": b_side}, {**n_main, "_held_out": n_side})
        assert vs["held_out"]["sentiment"]["n"] == 30
        assert vs["baseline"]["n_joined"] == 100 and vs["baseline"]["held_out_from_sidecar"] is True
        assert set(rl._vs_baseline_splits(vs)) == {"optimization", "held_out"}

    def test_guards_never_treat_null_as_zero(self, regression) -> None:
        baseline, new = regression
        baseline["enrichment_on"]["hallucination_rate"] = 0.02
        new["enrichment_on"]["hallucination_rate"] = 0.05
        new["enrichment_on"]["pii_leak_count"] = 1
        g = rl.compare_reports(baseline, new)["guards"]
        assert g["hallucination"] == {"baseline": 0.02, "new": 0.05, "status": "rose",
                                      "baseline_eligible": 72, "new_eligible": 72}
        assert g["pii"] == {"baseline": 0, "new": 1, "status": "leak"}
        new["enrichment_on"]["hallucination_rate"] = 0.02
        new["enrichment_on"]["pii_leak_count"] = 0
        g = rl.compare_reports(baseline, new)["guards"]
        assert g["hallucination"]["status"] == "ok" and g["pii"]["status"] == "ok"
        new["enrichment_on"]["hallucination_rate"] = None
        g = rl.compare_reports(baseline, new)["guards"]
        assert g["hallucination"]["status"] == "not_evaluated" and g["hallucination"]["new"] is None
        baseline["enrichment_on"]["hallucination_rate"] = None
        new["enrichment_on"]["hallucination_rate"] = 0.0
        assert rl.compare_reports(baseline, new)["guards"]["hallucination"]["status"] == "not_evaluated"

    def test_printed_report_shows_vs_baseline(self, regression, capsys) -> None:
        baseline, new = regression
        new["vs_baseline"] = rl.compare_reports(baseline, new)
        new["_report_path"] = "<test>"
        rl._print_report(new)
        out = capsys.readouterr().out
        assert "[vs baseline" in out and "SIGNIFICANT LOSS" in out
        assert "guards: hallucination" in out


class TestPublishedSnapshot:
    def test_carries_hallucination_fields_and_config(self, report) -> None:
        """C14: the model-card snapshot carries the guard with its
        denominators (null = not evaluated) and the config block."""
        pub = rl.published_snapshot(report, 3)
        on = report["enrichment_on"]
        assert pub["overall"]["hallucination_rate"] == on["hallucination_rate"] == 0.0
        assert pub["overall"]["hallucination_eligible"] == 72
        assert pub["overall"]["hallucination_excluded"] == 28
        assert pub["overall"]["hallucination_unassessed"] == 0
        assert pub["overall"]["pii_leak_count"] == 0
        assert pub["config"] == report["config"]
        assert pub["held_out_consultations"] == 3 and pub["by_split_ab"] is report["by_split_ab"]
        report["enrichment_on"]["hallucination_rate"] = None
        assert rl.published_snapshot(report, 3)["overall"]["hallucination_rate"] is None
        json.dumps(pub)


class TestMainEndToEnd:
    """main() with a fake model: sidecar written, main report free of held-out
    ids, ledger flags, --baseline-report -> vs_baseline, --publish fields."""

    @pytest.fixture
    def env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rl, "AI_MODEL", "fake-model")
        monkeypatch.setattr(rl, "EVALS_DIR", tmp_path)
        monkeypatch.setattr(rl, "REPORTS_DIR", tmp_path / "reports")
        monkeypatch.setattr(rl, "HISTORY_PATH", tmp_path / "history.jsonl")
        monkeypatch.setattr(rl, "fewshot_enabled", lambda: True)
        monkeypatch.setattr(rl, "load_exemplars", lambda: EXEMPLARS)
        return tmp_path

    def test_two_runs_with_baseline(self, env, monkeypatch, capsys) -> None:
        monkeypatch.setattr(rl, "enrich_signals", _fake_enrich(set()))
        assert rl.main([]) == 0
        reports = sorted((env / "reports").glob("report_*.json"))
        main_paths = [p for p in reports if not p.name.endswith(".held_out.json")]
        side_paths = [p for p in reports if p.name.endswith(".held_out.json")]
        assert len(main_paths) == 1 and len(side_paths) == 1
        first = json.loads(main_paths[0].read_text())
        side = json.loads(side_paths[0].read_text())
        assert first["held_out_sidecar"] == str(side_paths[0])
        assert {r["id"] for r in first["per_item"]} == set(OPTIMIZATION)
        assert {r["id"] for r in first["per_item_off"]} == set(OPTIMIZATION)
        assert {r["id"] for r in side["per_item"]} == set(HELD_OUT)
        assert "vs_baseline" not in first
        rows = [json.loads(line) for line in (env / "history.jsonl").read_text().splitlines()]
        assert rows[0]["held_out_revealed"] is False and rows[0]["held_out_consultations"] == 1
        assert rows[0]["baseline_report"] is None

        # second run regresses on 8 optimisation items; compared to the first
        monkeypatch.setattr(rl, "enrich_signals", _fake_enrich(set(OPTIMIZATION[:8])))
        rc = rl.main(["--baseline-report", str(main_paths[0]), "--reveal-held-out", "--publish"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "SIGNIFICANT LOSS" in out
        second_path = sorted(p for p in (env / "reports").glob("report_*.json")
                             if not p.name.endswith(".held_out.json"))[-1]
        second = json.loads(second_path.read_text())
        opt = second["vs_baseline"]["optimization"]["sentiment"]
        assert opt["lost"] == 8 and opt["gained"] == 0 and opt["p_value"] < 0.05
        assert second["vs_baseline"]["held_out"]["sentiment"]["n"] == 30  # from the sidecar
        assert second["vs_baseline"]["guards"]["hallucination"]["status"] == "ok"
        assert second["vs_baseline"]["baseline"]["report_path"] == str(main_paths[0])
        rows = [json.loads(line) for line in (env / "history.jsonl").read_text().splitlines()]
        assert rows[1]["held_out_revealed"] is True and rows[1]["held_out_consultations"] == 2
        assert rows[1]["vs_baseline_optimization"]["sentiment"]["lost"] == 8
        assert rows[1]["vs_baseline_guards"]["pii"]["new"] == 0
        assert rows[1]["baseline_report"] == str(main_paths[0])
        published = json.loads((env / "published_metrics.json").read_text())
        assert published["overall"]["hallucination_rate"] == 0.0
        assert published["overall"]["hallucination_eligible"] == 72
        assert published["overall"]["hallucination_excluded"] == 28
        assert published["config"]["golden_set_sha256"] == second["config"]["golden_set_sha256"]

    def test_baseline_with_other_golden_set_is_refused_before_scoring(self, env, monkeypatch, capsys) -> None:
        calls = {"n": 0}

        def counting(signals, *, exemplars=None, batch_size=25):
            calls["n"] += 1
            return _fake_enrich(set())(signals, exemplars=exemplars)

        monkeypatch.setattr(rl, "enrich_signals", counting)
        stale = env / "stale.json"
        stale.write_text(json.dumps({
            "timestamp": "t", "model": "m", "enrichment_on": {},
            "config": {**rl._run_config(EXEMPLARS), "golden_set_sha256": "f" * 64},
            "per_item": []}))
        assert rl.main(["--baseline-report", str(stale)]) == 2
        assert calls["n"] == 0
        assert "golden_set_sha256 differs" in capsys.readouterr().err
        assert not (env / "history.jsonl").exists()
