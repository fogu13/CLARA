from pathlib import Path

from app.domain.models import CandidateDecisionStatus
from app.services.seed import load_seed_signals
from app.services.signals import SQLiteSignalStore


def test_sqlite_signal_store_persists_imports(tmp_path: Path) -> None:
    db_path = tmp_path / "signals.db"
    first_store = SQLiteSignalStore(db_path)
    first_store.import_signals(load_seed_signals())

    second_store = SQLiteSignalStore(db_path)

    assert len(second_store.list_signals()) == 3
    assert second_store.candidates()[0].signal_count == 3


def test_sqlite_signal_store_persists_candidate_decisions(tmp_path: Path) -> None:
    db_path = tmp_path / "signals.db"
    first_store = SQLiteSignalStore(db_path)
    first_store.record_candidate_decision(
        candidate_id="CAND-CHECKOUT-PAYMENT",
        decision=CandidateDecisionStatus.rejected,
        reviewer="test_reviewer",
        note="Not enough evidence.",
    )

    second_store = SQLiteSignalStore(db_path)
    decision = second_store.get_candidate_decision("CAND-CHECKOUT-PAYMENT")

    assert decision is not None
    assert decision.decision == CandidateDecisionStatus.rejected
    assert decision.reviewer == "test_reviewer"
    assert decision.note == "Not enough evidence."
