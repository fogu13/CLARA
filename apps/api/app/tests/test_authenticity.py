"""Tests for the ingestion-time authenticity review.

Several of these tests exist to PREVENT a feature rather than to verify one:
the measured evidence (see services/authenticity docstring) says per-comment
AI-authorship attribution on customer verbatims produces ~15% false positives
with a 3x language disparity, so tests here pin the refusal in place. If someone
later adds a per-signal style classifier, `test_articulate_customer_is_never_flagged`
and `test_no_signal_is_ever_dropped` are the tests that should stop them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.models import SignalRecord
from app.services.authenticity import (
    LOW_INFORMATION_WORDS,
    MIN_ASSESSABLE_WORDS,
    assess_batch,
    channel_trust,
    flag_rate_by_language,
)


def _sig(sid: str, text: str, *, source: str = "csv_upload", language: str = "en",
         days_ago: int = 0) -> SignalRecord:
    ts = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")
    return SignalRecord(signal_id=sid, feedback_text=text, source=source,
                        language=language, timestamp=ts)


class TestAbstention:
    def test_short_text_is_abstained_not_guessed(self) -> None:
        batch = [_sig("s-1", "App broken again")]
        result = assess_batch(batch)
        verdict = result.verdicts["s-1"]
        assert verdict.state == "insufficient_text"
        assert result.abstained == 1
        assert result.assessed == 0
        assert batch[0].metadata["authenticity_state"] == "insufficient_text"

    def test_long_enough_text_is_assessed(self) -> None:
        text = " ".join(["the checkout flow failed and support never answered my emails"] * 2)
        result = assess_batch([_sig("s-1", text)])
        assert result.verdicts["s-1"].state == "assessable"
        assert result.assessed == 1

    def test_abstention_threshold_is_word_based(self) -> None:
        short = _sig("s-1", " ".join(["word"] * (MIN_ASSESSABLE_WORDS - 1)))
        longer = _sig("s-2", " ".join(["word"] * (MIN_ASSESSABLE_WORDS + 1)))
        result = assess_batch([short, longer])
        assert result.verdicts["s-1"].state == "insufficient_text"
        assert result.verdicts["s-2"].state == "assessable"


class TestTierOneKnownFacts:
    def test_declared_ai_authorship_is_flagged(self) -> None:
        text = "As an AI language model I cannot process your refund request properly"
        result = assess_batch([_sig("s-1", text)])
        assert "declared_ai_generated" in result.verdicts["s-1"].codes
        assert result.verdicts["s-1"].band == "review_suggested"

    def test_german_declaration_is_flagged(self) -> None:
        text = "Diese Bewertung wurde KI-generiert und beschreibt die Probleme mit der Lieferung"
        result = assess_batch([_sig("s-1", text, language="de")])
        assert "declared_ai_generated" in result.verdicts["s-1"].codes

    def test_exact_duplicate_of_existing_signal_is_flagged(self) -> None:
        text = "The delivery never arrived and customer support refused to issue any refund"
        existing = [_sig("old-1", text)]
        new = [_sig("s-1", text.upper())]
        result = assess_batch(new, existing)
        assert "exact_duplicate" in result.verdicts["s-1"].codes
        assert "old-1" in result.verdicts["s-1"].reasons[0].evidence

    def test_duplicates_inside_one_batch_are_caught(self) -> None:
        text = "The application crashes every single time I try to authorise a payment"
        result = assess_batch([_sig("s-1", text), _sig("s-2", text)])
        assert "exact_duplicate" not in result.verdicts["s-1"].codes
        assert "exact_duplicate" in result.verdicts["s-2"].codes


class TestQualityNotesAreNotAccusations:
    def test_low_information_is_noted_but_not_review_suggested(self) -> None:
        result = assess_batch([_sig("s-1", "Super")])
        verdict = result.verdicts["s-1"]
        assert "low_information" in verdict.codes
        # a five-word review is useless for synthesis but not suspicious
        assert verdict.band == "routine"

    def test_low_information_threshold(self) -> None:
        text = " ".join(["ok"] * (LOW_INFORMATION_WORDS + 2))
        result = assess_batch([_sig("s-1", text)])
        assert "low_information" not in result.verdicts["s-1"].codes


class TestBatchLevelClaimsOnly:
    def _batch(self, n: int, words: int, source: str = "csv_upload") -> list[SignalRecord]:
        # distinct content, near-identical length: isolates the uniformity signal
        # from the duplicate signal.
        return [
            _sig(f"s-{i}", " ".join([f"topic{i}"] + ["reported issue"] * (words // 2)), source=source)
            for i in range(n)
        ]

    def test_uniform_untrusted_batch_is_flagged_at_batch_level(self) -> None:
        records = self._batch(30, 20)
        result = assess_batch(records)
        codes = [r.code for r in result.batch_reasons]
        assert "uniform_batch_structure" in codes
        assert all(r.scope == "batch" for r in result.batch_reasons)
        # a cohort finding must NOT become a verdict on any individual comment
        assert all(v.band == "routine" for v in result.verdicts.values())
        assert records[0].metadata["authenticity_batch_flags"] == "uniform_batch_structure"

    def test_platform_sourced_batch_is_not_style_judged(self) -> None:
        """Platform connectors pull from sources that run their own fraud
        enforcement; we measured zero near-duplicates in 6,154 such reviews."""
        result = assess_batch(self._batch(30, 20, source="trustpilot"))
        assert [r.code for r in result.batch_reasons] == []

    def test_small_batches_get_no_uniformity_claim(self) -> None:
        """A variance statistic over a handful of texts is noise."""
        result = assess_batch(self._batch(5, 20))
        assert "uniform_batch_structure" not in [r.code for r in result.batch_reasons]

    def test_varied_batch_is_not_flagged(self) -> None:
        records = [
            _sig(f"s-{i}", " ".join(["problem"] * length))
            for i, length in enumerate([10, 45, 12, 80, 15, 33, 60, 11, 25, 95] * 3)
        ]
        result = assess_batch(records)
        assert "uniform_batch_structure" not in [r.code for r in result.batch_reasons]


class TestBurstIsAQuestionNotAVerdict:
    def test_volume_spike_against_own_history_is_surfaced(self) -> None:
        existing = [
            _sig(f"old-{d}-{i}", "the app keeps logging me out unexpectedly", source="webhook", days_ago=d + 1)
            for d in range(10) for i in range(1)
        ]
        new = [_sig(f"s-{i}", f"issue number {i} with the payment flow today", source="webhook")
               for i in range(30)]
        result = assess_batch(new, existing, channel="webhook")
        codes = [r.code for r in result.batch_reasons]
        assert "volume_burst" in codes
        burst = next(r for r in result.batch_reasons if r.code == "volume_burst")
        # the wording must not accuse: launches and incidents produce real spikes
        assert "launch" in burst.evidence.lower() or "incident" in burst.evidence.lower()

    def test_no_burst_without_history(self) -> None:
        new = [_sig(f"s-{i}", "the payment flow failed for me today again", source="webhook")
               for i in range(30)]
        result = assess_batch(new, [], channel="webhook")
        assert "volume_burst" not in [r.code for r in result.batch_reasons]


class TestEquityGuardrail:
    def test_uneven_language_flagging_raises_a_warning(self) -> None:
        dupe = "exactly the same complaint text repeated many times over here"
        records = []
        # 60 German signals, all exact duplicates -> flagged
        for i in range(60):
            records.append(_sig(f"de-{i}", dupe, language="de"))
        # 60 English signals, all distinct -> not flagged
        for i in range(60):
            records.append(_sig(f"en-{i}", f"unique english complaint number {i} about billing errors", language="en"))
        result = assess_batch(records)
        assert result.disparity_warning is not None
        assert "de" in result.disparity_warning
        assert result.flag_rate_by_language["de"] > result.flag_rate_by_language["en"]

    def test_even_flagging_raises_no_warning(self) -> None:
        records = [
            _sig(f"{lang}-{i}", f"a perfectly ordinary and quite distinct complaint {lang} {i} about the service",
                 language=lang)
            for lang in ("de", "en") for i in range(60)
        ]
        result = assess_batch(records)
        assert result.disparity_warning is None

    def test_flag_rate_helper_reports_per_language(self) -> None:
        records = [_sig(f"de-{i}", "text here", language="de") for i in range(60)]
        for r in records[:15]:
            r.metadata["authenticity_band"] = "review_suggested"
        for r in records[15:]:
            r.metadata["authenticity_band"] = "routine"
        assert flag_rate_by_language(records)["de"] == 0.25


class TestRefusalsAreLoadBearing:
    def test_articulate_customer_is_never_flagged(self) -> None:
        """THE regression test for this feature.

        This is a real, human-written complaint style: long, clean, calm,
        third-person-ish, no typos, no emoji. A stylometric AI detector flags
        exactly this kind of text — and we measured that such filters skew toward
        angrier, more detailed complaints (2.21 vs 2.70 mean stars). Feedback
        intelligence that silences its most articulate critics is worse than
        useless, so this must never be flagged on style alone."""
        text = (
            "I have now contacted customer service on four separate occasions regarding "
            "the duplicate charge on my account. Each representative confirmed that a "
            "refund had been approved, and each time the amount was subsequently "
            "re-debited without explanation. The total is a five-figure sum and I have "
            "received no written confirmation of the investigation."
        )
        result = assess_batch([_sig("s-1", text)])
        verdict = result.verdicts["s-1"]
        assert verdict.band == "routine", f"articulate human flagged via {verdict.codes}"
        assert verdict.codes == []

    def test_no_signal_is_ever_dropped(self) -> None:
        records = [
            _sig("s-1", "As an AI language model, here is your feedback about the service"),
            _sig("s-2", "hi"),
            _sig("s-3", "the checkout flow is broken and nobody at support will help me"),
        ]
        before = [r.signal_id for r in records]
        result = assess_batch(records)
        assert [r.signal_id for r in records] == before
        assert set(result.verdicts) == set(before)

    def test_no_probability_is_ever_exposed(self) -> None:
        """The product renamed 'confidence' to 'model score' because an
        uncalibrated heuristic must not look like a probability. This verdict has
        no calibrated probability at all, so it exposes none."""
        result = assess_batch([_sig("s-1", "As an AI language model I must decline to answer that")])
        stamped = result.verdicts["s-1"]
        assert not hasattr(stamped, "probability")
        assert not hasattr(stamped, "score")
        for reason in stamped.reasons:
            assert "%" not in reason.message or "volume" in reason.code


class TestMetadataContract:
    def test_metadata_values_are_flat_strings(self) -> None:
        record = _sig("s-1", "As an AI language model here is a complaint about billing")
        assess_batch([record])
        assert record.metadata["authenticity_state"] in {"assessable", "insufficient_text"}
        assert record.metadata["authenticity_band"] in {"routine", "review_suggested"}
        for key, value in record.metadata.items():
            assert isinstance(value, str), f"{key} must stay a flat string"

    def test_channel_trust_classification(self) -> None:
        assert channel_trust("trustpilot") == "platform_verified"
        assert channel_trust("app_store") == "platform_verified"
        assert channel_trust("webhook") == "authenticated_channel"
        assert channel_trust("csv_upload") == "unverified"
        assert channel_trust("") == "unverified"

    def test_summary_shape_is_serialisable(self) -> None:
        result = assess_batch([_sig("s-1", "the payment failed today and nobody at support has responded to my emails")])
        summary = result.summary()
        assert summary["assessed"] == 1
        assert summary["channel_trust"] == "unverified"
        assert "flag_rate_by_language" in summary


class TestBackfillOfExistingSignals:
    """Signals stored before this review existed can be assessed after the fact,
    but only for what is true of the signal itself."""

    def test_backfill_makes_no_cohort_claim(self) -> None:
        """Batch findings are statements about an ingestion batch. The batches
        behind already-stored signals cannot be reconstructed, so inventing them
        from source or date would be manufacturing evidence."""
        from app.services.authenticity import assess_existing

        # 30 uniform signals that WOULD trigger the batch uniformity finding at import
        records = [
            _sig(f"s-{i}", " ".join([f"topic{i}"] + ["reported issue"] * 10))
            for i in range(30)
        ]
        result = assess_existing(records)
        assert result.batch_reasons == []
        assert result.channel == "backfill"

    def test_backfill_still_finds_signal_level_facts(self) -> None:
        from app.services.authenticity import assess_existing

        dupe = "the payment failed twice and support closed my ticket without a word"
        records = [
            _sig("s-1", dupe),
            _sig("s-2", dupe),
            _sig("s-3", "As an AI language model I cannot complete that refund request"),
            _sig("s-4", "hi"),
        ]
        result = assess_existing(records)
        assert "exact_duplicate" in result.verdicts["s-2"].codes
        assert "exact_duplicate" not in result.verdicts["s-1"].codes
        assert "declared_ai_generated" in result.verdicts["s-3"].codes
        assert result.verdicts["s-4"].state == "insufficient_text"

    def test_backfill_marks_the_later_copy_not_the_first(self) -> None:
        """Ordered by timestamp, so the original is left clean and later copies
        are annotated, matching what import would have done."""
        from app.services.authenticity import assess_existing

        dupe = "the delivery never arrived and nobody answered the support line"
        first = _sig("older", dupe, days_ago=5)
        second = _sig("newer", dupe, days_ago=1)
        result = assess_existing([second, first])  # deliberately out of order
        assert "exact_duplicate" not in result.verdicts["older"].codes
        assert "exact_duplicate" in result.verdicts["newer"].codes

    def test_backfill_is_idempotent(self) -> None:
        from app.services.authenticity import assess_existing

        records = [_sig("s-1", "the checkout page failed three times in a row today")]
        assess_existing(records)
        first = dict(records[0].metadata)
        assess_existing(records)
        assert records[0].metadata == first
