"""Plain-assert checks for prediction_validation (no corpus, no pytest).
Run: python3 thesis/evaluation/test_prediction_validation.py   (exits non-zero on failure)

Each case is one of the ways the old scorer inflated or silently reshaped a
result (defect E1): an id-only row, duplicate ids, unknown ids, missing ids,
invalid label strings, and int/str id mismatches. The final case shows the
end-to-end accuracy falling below the coverage-conditioned one exactly when
rows are missing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import metrics as M  # noqa: E402
from prediction_validation import validate_predictions  # noqa: E402

SENT = ["negative", "neutral", "positive"]
RISK = ["low", "medium", "high", "critical"]


def _e2e_accuracy(vs, gold: dict[str, str]) -> float:
    correct = sum(1 for sid, lab in vs.by_id.items() if gold[sid] == lab)
    return correct / vs.n_expected


def test_id_only_row_is_invalid_not_a_free_neutral():
    # Old behaviour: {"id": "x"} scored as "neutral" / "low" and hit a neutral/low
    # gold item -> 100 %. Now it is invalid on both tasks and scores 0 end-to-end.
    rows = [{"id": "x"}]
    gold_s, gold_r = {"x": "neutral"}, {"x": "low"}
    vs = validate_predictions(rows, expected_ids=["x"], field="sentiment", labels=SENT)
    vr = validate_predictions(rows, expected_ids=["x"], field="risk", labels=RISK)
    assert vs.by_id == {} and vr.by_id == {}, (vs, vr)
    assert vs.n_invalid == 1 and vr.n_invalid == 1
    assert vs.n_valid == 0 and vs.n_missing == 0 and vs.n_expected == 1
    assert vs.invalid_examples == [("x", None)], vs.invalid_examples
    assert _e2e_accuracy(vs, gold_s) == 0.0 and _e2e_accuracy(vr, gold_r) == 0.0
    # empty string is invalid too (the `or default` path used to swallow it)
    ve = validate_predictions([{"id": "x", "sentiment": ""}], expected_ids=["x"],
                              field="sentiment", labels=SENT)
    assert ve.n_invalid == 1 and ve.by_id == {}


def test_duplicate_ids_first_wins_and_are_counted():
    rows = [{"id": "a", "sentiment": "positive"},
            {"id": "a", "sentiment": "negative"},   # later row must NOT overwrite
            {"id": "a", "sentiment": "neutral"}]
    vs = validate_predictions(rows, expected_ids=["a"], field="sentiment", labels=SENT)
    assert vs.by_id == {"a": "positive"}, vs.by_id
    assert vs.n_returned == 3 and vs.n_duplicate_ids == 2 and vs.duplicate_ids == ["a"]
    assert vs.n_valid == 1 and vs.n_invalid == 0 and vs.n_missing == 0
    # first occurrence wins even when it is invalid: the id stays invalid
    vi = validate_predictions([{"id": "a", "sentiment": "Positive"},
                               {"id": "a", "sentiment": "positive"}],
                              expected_ids=["a"], field="sentiment", labels=SENT)
    assert vi.by_id == {} and vi.n_invalid == 1 and vi.n_duplicate_ids == 1


def test_unknown_ids_are_counted_and_never_scored():
    rows = [{"id": "a", "sentiment": "positive"},
            {"id": "ghost", "sentiment": "positive"},
            {"id": "ghost", "sentiment": "negative"},
            {"sentiment": "positive"}]  # no id at all
    vs = validate_predictions(rows, expected_ids=["a"], field="sentiment", labels=SENT)
    assert vs.by_id == {"a": "positive"}
    assert vs.n_returned == 4
    assert vs.n_unknown_ids == 3, vs.n_unknown_ids
    assert vs.unknown_ids == ["ghost", ""], vs.unknown_ids
    assert vs.n_duplicate_ids == 0  # unknown rows are not duplicates of anything scored
    assert vs.n_expected == 1 and vs.n_valid == 1


def test_missing_ids_stay_in_the_denominator():
    rows = [{"id": "a", "sentiment": "positive"}]
    vs = validate_predictions(rows, expected_ids=["a", "b", "c"], field="sentiment", labels=SENT)
    assert vs.n_expected == 3 and vs.n_valid == 1 and vs.n_missing == 2
    assert vs.missing_ids == ["b", "c"]
    assert vs.coverage == round(1 / 3, 4)
    assert vs.n_valid + vs.n_invalid + vs.n_missing == vs.n_expected


def test_invalid_label_strings_are_not_admitted():
    rows = [{"id": "1", "sentiment": "mixed"},      # production 4-class label, unmapped
            {"id": "2", "sentiment": "Positive"},   # wrong case
            {"id": "3", "sentiment": None},
            {"id": "4", "sentiment": ["positive"]},  # wrong type
            {"id": "5", "sentiment": "positive "},   # stray whitespace
            {"id": "6", "sentiment": "neg"},
            {"id": "7", "sentiment": "negative"}]
    vs = validate_predictions(rows, expected_ids=list("1234567"), field="sentiment", labels=SENT)
    assert vs.by_id == {"7": "negative"}, vs.by_id
    assert vs.n_invalid == 6 and vs.n_valid == 1
    assert len(vs.invalid_examples) == 5, vs.invalid_examples  # capped at five
    assert vs.invalid_examples[0] == ("1", "mixed")
    # and the macro average stays on the fixed class set: scoring the valid
    # rows with labels= never sees "mixed"
    sc = M.score(["negative"], ["negative"], SENT)
    assert sc["accuracy"] == 1.0


def test_int_and_str_ids_are_compared_as_str():
    rows = [{"id": 7, "risk": "high"}, {"id": "8", "risk": "low"}]
    vr = validate_predictions(rows, expected_ids=["7", 8], field="risk", labels=RISK)
    assert vr.by_id == {"7": "high", "8": "low"}, vr.by_id
    assert vr.n_valid == 2 and vr.n_missing == 0 and vr.n_unknown_ids == 0


def test_end_to_end_is_below_coverage_conditioned_when_rows_are_missing():
    gold = {"a": "positive", "b": "negative", "c": "neutral", "d": "positive"}
    rows = [{"id": "a", "sentiment": "positive"},
            {"id": "b", "sentiment": "negative"},
            {"id": "c", "sentiment": "positive"}]   # d is missing; c is wrong
    vs = validate_predictions(rows, expected_ids=list(gold), field="sentiment", labels=SENT)
    y_true = [gold[s] for s in vs.by_id]
    y_pred = [vs.by_id[s] for s in vs.by_id]
    coverage_conditioned = M.score(y_true, y_pred, SENT)["accuracy"]   # 2/3
    end_to_end = _e2e_accuracy(vs, gold)                                # 2/4
    assert abs(coverage_conditioned - 2 / 3) < 1e-3, coverage_conditioned  # metrics round to 4 dp
    assert end_to_end == 0.5, end_to_end
    assert end_to_end < coverage_conditioned
    assert vs.counts()["coverage"] == 0.75
    # no rows missing and none invalid -> the two views coincide
    full = validate_predictions(rows + [{"id": "d", "sentiment": "negative"}],
                                expected_ids=list(gold), field="sentiment", labels=SENT)
    assert full.n_missing == 0 and full.n_invalid == 0
    assert _e2e_accuracy(full, gold) == M.score([gold[s] for s in full.by_id],
                                                [full.by_id[s] for s in full.by_id],
                                                SENT)["accuracy"]


if __name__ == "__main__":
    test_id_only_row_is_invalid_not_a_free_neutral()
    test_duplicate_ids_first_wins_and_are_counted()
    test_unknown_ids_are_counted_and_never_scored()
    test_missing_ids_stay_in_the_denominator()
    test_invalid_label_strings_are_not_admitted()
    test_int_and_str_ids_are_compared_as_str()
    test_end_to_end_is_below_coverage_conditioned_when_rows_are_missing()
    print("OK: all prediction-validation self-checks passed")
