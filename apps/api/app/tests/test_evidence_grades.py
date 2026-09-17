"""Evidence grades name realised designs, never substrings or promises
(13 September 2026 review, finding F4), and loop verdicts certify only
through the checkpoint a reading is bound to.
"""

from __future__ import annotations

import pytest

from app.services.outcome_engine import DESIGN_GRADES, evidence_grade, loop_verdict


@pytest.mark.parametrize(
    ("method", "realised", "expected"),
    [
        # Uncontrolled designs are D whatever they are called.
        ("uncontrolled_before_after", None, "D"),
        ("pre_post_signal_rate", None, "D"),
        ("before_after", None, "D"),
        ("pre_post", None, "D"),
        # Contracted A/B designs are not realised by CLARA: the instrumented
        # reading is an uncontrolled before/after.
        ("randomized_holdout", None, "D"),
        ("randomised_holdout", None, "D"),
        ("matched_control", None, "D"),
        ("difference_in_differences", None, "D"),
        ("synthetic_control", None, "D"),
        # ITS is C only once the fit exists; a sparse series is D.
        ("its_segmented_regression", "its", "C"),
        ("its_segmented_regression", None, "D"),
        ("its_segmented_regression", "delta_insufficient_data", "D"),
        ("its", "its", "C"),
        # Misspellings and unknown methods name no design: E.
        ("controll", None, "E"),
        ("holdout_typo_hodlout", None, "E"),
        ("sparse_its", None, "E"),
        ("randomized", None, "E"),
        ("unknown_method", None, "E"),
        ("", None, "E"),
        ("ITS_SEGMENTED_REGRESSION ", "its", "C"),  # case and whitespace tolerant
    ],
)
def test_instrumented_grades_follow_the_explicit_design_table(method: str, realised: str | None, expected: str) -> None:
    assert evidence_grade(comparison_method=method, measurement_source="instrumented", realised_method=realised) == expected


@pytest.mark.parametrize("method", sorted(DESIGN_GRADES) + ["unknown_method"])
def test_manual_and_unmeasured_readouts_are_grade_e_whatever_the_method(method: str) -> None:
    assert evidence_grade(comparison_method=method, measurement_source="manual", realised_method="its") == "E"
    assert evidence_grade(comparison_method=method, measurement_source=None) == "E"


def test_no_grade_a_or_b_is_reachable_today() -> None:
    reachable = {
        evidence_grade(comparison_method=method, measurement_source="instrumented", realised_method=realised)
        for method in [*DESIGN_GRADES, "control", "holdout"]
        for realised in (None, "its", "delta_insufficient_data", "holdout", "matched_control")
    }
    assert reachable == {"C", "D", "E"}


# ---------------------------------------------------------------------------
# Verdict binding
# ---------------------------------------------------------------------------


def _plan(plan_id: int, kind: str = "window", *, execution_id: str = "EXE-0001", status: str = "done") -> dict:
    return {"id": plan_id, "kind": kind, "status": status, "execution_id": execution_id, "problem_id": "p"}


def test_a_reading_certifies_only_through_the_plan_it_names() -> None:
    plans = [_plan(1), _plan(2, execution_id="EXE-0002")]
    own, _ = loop_verdict(outcome_status="target_met", plans=plans, measurement_source="instrumented", checkpoint_kind="window", plan_id=1, execution_id="EXE-0001")
    assert own == "loop_closed"
    # Another execution's completed plan is never borrowed.
    borrowed, note = loop_verdict(outcome_status="target_met", plans=plans, measurement_source="instrumented", checkpoint_kind="window", plan_id=2, execution_id="EXE-0001")
    assert borrowed == "on_track" and "not certified" in note
    # A plan id that is not among the problem's plans certifies nothing.
    missing, _ = loop_verdict(outcome_status="target_met", plans=plans, measurement_source="instrumented", checkpoint_kind="window", plan_id=42)
    assert missing == "on_track"
    # A pending plan of the right id is not done.
    pending, _ = loop_verdict(outcome_status="not_improved", plans=[_plan(1, status="pending")], measurement_source="instrumented", checkpoint_kind="window", plan_id=1)
    assert pending == "measuring"
    # The kind must match the reading's checkpoint kind.
    wrong_kind, _ = loop_verdict(outcome_status="target_met", plans=[_plan(1, "followup")], measurement_source="instrumented", checkpoint_kind="window", plan_id=1)
    assert wrong_kind == "on_track"


def test_a_reading_without_a_plan_id_certifies_only_through_a_unique_done_plan() -> None:
    unique = [_plan(1)]
    assert loop_verdict(outcome_status="target_met", plans=unique, measurement_source="instrumented", checkpoint_kind="window")[0] == "loop_closed"
    ambiguous = [_plan(1), _plan(2, execution_id="EXE-0002")]
    assert loop_verdict(outcome_status="target_met", plans=ambiguous, measurement_source="instrumented", checkpoint_kind="window")[0] == "on_track"
    foreign = [_plan(1, execution_id="EXE-0002")]
    assert loop_verdict(outcome_status="target_met", plans=foreign, measurement_source="instrumented", checkpoint_kind="window", execution_id="EXE-0001")[0] == "on_track"


def test_legacy_readings_have_unknown_provenance_and_manual_readings_never_certify() -> None:
    plans = [_plan(1)]
    verdict, note = loop_verdict(outcome_status="target_met", plans=plans, measurement_source="instrumented")
    assert verdict == "on_track" and "Provenance unknown" in note
    verdict, note = loop_verdict(outcome_status="not_improved", plans=plans, measurement_source="instrumented")
    assert verdict == "measuring" and "Provenance unknown" in note
    assert loop_verdict(outcome_status="target_met", plans=plans, measurement_source="manual", checkpoint_kind="window", plan_id=1)[0] == "on_track"


def test_verdict_notes_state_observation_and_attribution_separately() -> None:
    plans = [_plan(1)]
    _, note = loop_verdict(outcome_status="not_improved", plans=plans, measurement_source="instrumented", checkpoint_kind="window", plan_id=1, evidence_grade="D")
    assert "observed no improvement" in note
    assert "Attribution to the action is not established" in note
    assert "the fix did not land" not in note
    _, graded = loop_verdict(outcome_status="not_improved", plans=plans, measurement_source="instrumented", checkpoint_kind="window", plan_id=1, evidence_grade="C")
    assert "rests on the design (evidence grade C)" in graded
