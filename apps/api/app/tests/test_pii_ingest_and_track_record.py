"""Tests for the two features ported from Elvis_thesis_lovable:

1. PII masking at signal ingestion (GDPR data-minimisation) — Elvis _shared/pii.ts,
   folded into the existing ``redact_common_pii`` + a ``SignalRecord`` validator.
2. Track-record weighting in ``rank_learnings`` — Elvis's recScore
   ``similarity × decayed_confidence × (1 + avg_resolution)``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.models import SignalRecord, redact_common_pii
from app.services.learning_engine import rank_learnings, track_record


# --- 1. PII masking at ingestion ---

def test_redactor_masks_iban_and_card() -> None:
    out = redact_common_pii("pay to DE89370400440532013000 card 4111 1111 1111 1111")
    assert "DE89370400440532013000" not in out
    assert "4111 1111 1111 1111" not in out
    assert "[IBAN REDACTED]" in out
    assert "[CARD REDACTED]" in out


def test_signal_masks_pii_on_ingest() -> None:
    sig = SignalRecord(
        signal_id="s1",
        feedback_text="email me at a@b.com or call +49 151 23456789",
    )
    # Guarantee is "no raw PII persisted", not a specific label: a long phone run overlaps
    # the card pattern, so the number may be tagged [PHONE REDACTED] or [CARD REDACTED].
    assert "a@b.com" not in sig.feedback_text
    assert "23456789" not in sig.feedback_text
    assert "[EMAIL REDACTED]" in sig.feedback_text
    assert ("[PHONE REDACTED]" in sig.feedback_text) or ("[CARD REDACTED]" in sig.feedback_text)


def test_masking_is_idempotent() -> None:
    # A row read back from the DB re-runs the validator; masking already-masked text
    # must be a no-op (no double-masking, no PII leak).
    once = SignalRecord(signal_id="s1", feedback_text="reach a@b.com").feedback_text
    twice = SignalRecord(signal_id="s1", feedback_text=once).feedback_text
    assert once == twice
    assert "a@b.com" not in twice


def test_env_off_switch_disables_masking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_MASK_PII_ON_INGEST", "false")
    sig = SignalRecord(signal_id="s1", feedback_text="reach a@b.com")
    assert sig.feedback_text == "reach a@b.com"  # raw retained when opted out


# --- 2. Track-record weighting ---

def _learning(topic: str, *, base: float = 0.8, resolution: float | None = None) -> dict:
    ev: dict = {"confidence": base}
    if resolution is not None:
        ev["resolution_score"] = resolution
    return {
        "topic": topic,
        "pattern": f"{topic} handling",
        "base_confidence": base,
        "last_validated_at": datetime.now(UTC).isoformat(),
        "evidence": ev,
    }


def test_track_record_defaults_neutral_when_unproven() -> None:
    assert track_record({"topic": "x"}) == 0.0  # no data -> factor (1 + 0) = 1.0


def test_track_record_clamps() -> None:
    assert track_record({"avg_resolution": 5}) == 1.0
    assert track_record({"avg_resolution": -1}) == 0.0
    assert track_record({"avg_resolution": "bad"}) == 0.0


def test_proven_learning_outranks_equal_unproven_one() -> None:
    # Two learnings with identical topic/decay; the one whose action actually resolved
    # well must rank first once track-record weighting is applied.
    unproven = _learning("checkout", resolution=0.0)
    proven = _learning("checkout", resolution=0.9)
    ranked = rank_learnings([unproven, proven], "checkout", k=2)
    assert ranked[0] is proven
