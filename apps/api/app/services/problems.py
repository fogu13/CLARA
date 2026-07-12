from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import (
    ActionProposal,
    ActionProposalUpdateRequest,
    OutcomeContract,
    OutcomeContractUpdateRequest,
    ProblemRecord,
    ProblemStatus,
    ProblemUpdateRequest,
)
from app.domain.scoring import approval_pressure
from app.services.common import SerializedConnection, action_snapshot  # re-exported for existing importers, SerializedConnection


def with_approval_pressure(problem: ProblemRecord) -> ProblemRecord:
    blocking_failures = sum(
        1
        for check in problem.governance_checks
        if check.blocking and check.status.value == "fail"
    )

    return problem.model_copy(
        update={"approval_pressure": approval_pressure(problem.status.value, blocking_failures)}
    )


def apply_problem_update(problem: ProblemRecord, update: ProblemUpdateRequest) -> ProblemRecord:
    updates = update.model_dump(exclude_unset=True, exclude_none=True)
    return with_approval_pressure(problem.model_copy(update=updates))


def apply_action_proposal_update(
    problem: ProblemRecord,
    action_id: str,
    update: ActionProposalUpdateRequest,
) -> ProblemRecord | None:
    updates = update.model_dump(exclude_unset=True, exclude_none=True)
    updated_actions = []
    found_action = False

    for action in problem.action_proposals:
        if action.action_id != action_id:
            updated_actions.append(action)
            continue

        found_action = True
        if updates and action.original_snapshot is None:
            updates["original_snapshot"] = action_snapshot(action)
        payload = action.model_dump(by_alias=True)
        payload.update(updates)
        updated_actions.append(ActionProposal.model_validate(payload))

    if not found_action:
        return None

    return with_approval_pressure(problem.model_copy(update={"action_proposals": updated_actions}))


def apply_problem_status(problem: ProblemRecord, status: ProblemStatus) -> ProblemRecord:
    return with_approval_pressure(problem.model_copy(update={"status": status}))


def apply_outcome_contract_update(
    problem: ProblemRecord,
    update: OutcomeContractUpdateRequest,
) -> ProblemRecord:
    merged = problem.outcome_contract.model_dump()
    merged.update(update.model_dump(exclude_unset=True, exclude_none=True))
    return problem.model_copy(
        update={"outcome_contract": OutcomeContract.model_validate(merged)}
    )


GDPR_ERASED = "[erased under GDPR Art. 17]"


def scrub_customer_evidence(problem: ProblemRecord, customer_id: str) -> ProblemRecord | None:
    """Erase a customer's personal content from a problem's evidence.

    The evidence entry stays (aggregate counts remain honest) but the excerpt and
    customer identifier are removed. Returns None when nothing matched.
    """
    if not any(evidence.customer_id == customer_id for evidence in problem.evidence):
        return None
    scrubbed = [
        evidence.model_copy(update={"customer_id": "erased", "excerpt": GDPR_ERASED})
        if evidence.customer_id == customer_id
        else evidence
        for evidence in problem.evidence
    ]
    return problem.model_copy(update={"evidence": scrubbed})


class ProblemStore:
    def __init__(self, seed_problems: list[ProblemRecord]) -> None:
        self._seed_problems = {problem.problem_id: problem for problem in seed_problems}
        self._draft_problems: dict[str, ProblemRecord] = {}

    def list_problems(self) -> list[ProblemRecord]:
        return [*self._seed_problems.values(), *self._draft_problems.values()]

    def get_problem(self, problem_id: str) -> ProblemRecord | None:
        return self._draft_problems.get(problem_id) or self._seed_problems.get(problem_id)

    def upsert_problem(self, problem: ProblemRecord) -> ProblemRecord:
        existing = self.get_problem(problem.problem_id)
        if existing is not None:
            return existing

        self._draft_problems[problem.problem_id] = problem
        return problem

    def scrub_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: erase a customer's evidence content from draft problems."""
        scrubbed = 0
        for problem_id, problem in list(self._draft_problems.items()):
            updated = scrub_customer_evidence(problem, customer_id)
            if updated is not None:
                self._draft_problems[problem_id] = updated
                scrubbed += 1
        return scrubbed

    def update_problem(
        self,
        problem_id: str,
        update: ProblemUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self._draft_problems.get(problem_id)
        if existing is None:
            return None

        updated_problem = apply_problem_update(existing, update)
        self._draft_problems[problem_id] = updated_problem
        return updated_problem

    def update_action_proposal(
        self,
        problem_id: str,
        action_id: str,
        update: ActionProposalUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self._draft_problems.get(problem_id)
        if existing is None:
            return None

        updated_problem = apply_action_proposal_update(existing, action_id, update)
        if updated_problem is None:
            return None

        self._draft_problems[problem_id] = updated_problem
        return updated_problem

    def transition_problem_status(
        self,
        problem_id: str,
        status: ProblemStatus,
    ) -> ProblemRecord | None:
        existing = self._draft_problems.get(problem_id)
        if existing is None:
            return None

        updated_problem = apply_problem_status(existing, status)
        self._draft_problems[problem_id] = updated_problem
        return updated_problem

    def update_outcome_contract(
        self,
        problem_id: str,
        update: OutcomeContractUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self._draft_problems.get(problem_id)
        if existing is None:
            return None

        updated_problem = apply_outcome_contract_update(existing, update)
        self._draft_problems[problem_id] = updated_problem
        return updated_problem


class SQLiteProblemStore:
    def __init__(self, path: Path, seed_problems: list[ProblemRecord]) -> None:
        self.path = path
        self.seed_problems = {problem.problem_id: problem for problem in seed_problems}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS draft_problems (
                problem_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.commit()

    def list_problems(self) -> list[ProblemRecord]:
        rows = self._connection.execute(
            "SELECT payload FROM draft_problems ORDER BY created_at"
        ).fetchall()
        draft_problems = [
            ProblemRecord.model_validate(json.loads(row["payload"])) for row in rows
        ]

        return [*self.seed_problems.values(), *draft_problems]

    def get_problem(self, problem_id: str) -> ProblemRecord | None:
        seed_problem = self.seed_problems.get(problem_id)
        if seed_problem is not None:
            return seed_problem

        row = self._connection.execute(
            "SELECT payload FROM draft_problems WHERE problem_id = ?",
            (problem_id,),
        ).fetchone()
        if row is None:
            return None

        return ProblemRecord.model_validate(json.loads(row["payload"]))

    def upsert_problem(self, problem: ProblemRecord) -> ProblemRecord:
        existing = self.get_problem(problem.problem_id)
        if existing is not None:
            return existing

        payload = json.dumps(problem.model_dump(mode="json", by_alias=True))
        self._connection.execute(
            """
            INSERT INTO draft_problems (problem_id, payload)
            VALUES (?, ?)
            """,
            (problem.problem_id, payload),
        )
        self._connection.commit()
        return problem

    def scrub_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: erase a customer's evidence content from draft problems."""
        rows = self._connection.execute(
            "SELECT problem_id, payload FROM draft_problems"
        ).fetchall()
        scrubbed = 0
        for row in rows:
            problem = ProblemRecord.model_validate(json.loads(row["payload"]))
            updated = scrub_customer_evidence(problem, customer_id)
            if updated is None:
                continue
            self._connection.execute(
                "UPDATE draft_problems SET payload = ?, updated_at = CURRENT_TIMESTAMP"
                " WHERE problem_id = ?",
                (json.dumps(updated.model_dump(mode="json", by_alias=True)), row["problem_id"]),
            )
            scrubbed += 1
        self._connection.commit()
        return scrubbed

    def update_problem(
        self,
        problem_id: str,
        update: ProblemUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problems:
            return None

        updated_problem = apply_problem_update(existing, update)
        payload = json.dumps(updated_problem.model_dump(mode="json", by_alias=True))
        self._connection.execute(
            """
            UPDATE draft_problems
            SET payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE problem_id = ?
            """,
            (payload, problem_id),
        )
        self._connection.commit()
        return updated_problem

    def update_action_proposal(
        self,
        problem_id: str,
        action_id: str,
        update: ActionProposalUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problems:
            return None

        updated_problem = apply_action_proposal_update(existing, action_id, update)
        if updated_problem is None:
            return None

        payload = json.dumps(updated_problem.model_dump(mode="json", by_alias=True))
        self._connection.execute(
            """
            UPDATE draft_problems
            SET payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE problem_id = ?
            """,
            (payload, problem_id),
        )
        self._connection.commit()
        return updated_problem

    def transition_problem_status(
        self,
        problem_id: str,
        status: ProblemStatus,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problems:
            return None

        updated_problem = apply_problem_status(existing, status)
        payload = json.dumps(updated_problem.model_dump(mode="json", by_alias=True))
        self._connection.execute(
            """
            UPDATE draft_problems
            SET payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE problem_id = ?
            """,
            (payload, problem_id),
        )
        self._connection.commit()
        return updated_problem

    def update_outcome_contract(
        self,
        problem_id: str,
        update: OutcomeContractUpdateRequest,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problems:
            return None

        updated_problem = apply_outcome_contract_update(existing, update)
        payload = json.dumps(updated_problem.model_dump(mode="json", by_alias=True))
        self._connection.execute(
            """
            UPDATE draft_problems
            SET payload = ?, updated_at = CURRENT_TIMESTAMP
            WHERE problem_id = ?
            """,
            (payload, problem_id),
        )
        self._connection.commit()
        return updated_problem
