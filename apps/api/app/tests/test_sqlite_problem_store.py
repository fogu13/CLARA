from pathlib import Path

from app.services.problems import SQLiteProblemStore
from app.services.seed import load_seed_problems, load_seed_signals
from app.services.signals import build_candidates, promote_candidate


def test_sqlite_problem_store_persists_promoted_drafts(tmp_path: Path) -> None:
    db_path = tmp_path / "problems.db"
    seed_problems = load_seed_problems()
    candidate = build_candidates(load_seed_signals())[0]
    promoted_problem = promote_candidate(candidate)

    first_store = SQLiteProblemStore(db_path, seed_problems)
    first_store.upsert_problem(promoted_problem)

    second_store = SQLiteProblemStore(db_path, seed_problems)
    loaded_problem = second_store.get_problem(promoted_problem.problem_id)

    assert loaded_problem is not None
    assert loaded_problem.problem_id == promoted_problem.problem_id
    assert loaded_problem.status == "validation_required"
    assert len(second_store.list_problems()) == len(seed_problems) + 1

