"""Regressions for evidence-pack tamper evidence (external-review item 17):
canonical content hashing + the hash stamped on approval records."""

from app.domain.models import ApprovalDecision, ApprovalDecisionStatus
from app.services.evidence_pack import build_evidence_pack
from app.services.seed import load_seed_problems
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore


def _pack(problem, store):
    return build_evidence_pack(problem, store.state_for_problem(problem))


def test_content_hash_is_stable_across_reexports() -> None:
    problem = load_seed_problems()[0]
    store = WorkflowStore()
    first = build_evidence_pack(
        problem, store.state_for_problem(problem), generated_at="2026-07-01T00:00:00Z"
    )
    second = build_evidence_pack(
        problem, store.state_for_problem(problem), generated_at="2026-07-02T00:00:00Z"
    )
    assert first["content_hash"] == second["content_hash"]
    assert first["generated_at"] != second["generated_at"]


def test_content_hash_changes_when_state_changes() -> None:
    problem = load_seed_problems()[0]
    store = WorkflowStore()
    before = _pack(problem, store)["content_hash"]
    store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id=problem.action_proposals[0].action_id,
            decision=ApprovalDecisionStatus.approved,
            reviewer="auditor@example.com",
        ),
    )
    after = _pack(problem, store)["content_hash"]
    assert before != after


def test_approval_stamps_pack_hash_append_only(tmp_path) -> None:
    problem = load_seed_problems()[0]
    for store in (WorkflowStore(), SQLiteWorkflowStore(tmp_path / "wf.db")):
        record = store.record_approval(
            problem=problem,
            decision=ApprovalDecision(
                action_id=problem.action_proposals[0].action_id,
                decision=ApprovalDecisionStatus.approved,
                reviewer="auditor@example.com",
            ),
            evidence_pack_hash="deadbeef" * 8,
        )
        assert record.evidence_pack_hash == "deadbeef" * 8
        stored = [a for a in store.list_approvals() if a.problem_id == problem.problem_id]
        assert stored and stored[-1].evidence_pack_hash == "deadbeef" * 8
