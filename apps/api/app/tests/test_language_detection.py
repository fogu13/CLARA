"""Tests for DE/EN language detection at ingestion (N6)."""

from __future__ import annotations

from app.services.language import detect_language
from app.services.signals import parse_signal_csv


class TestDetector:
    def test_german_by_umlaut(self) -> None:
        assert detect_language("Die Überweisung ist fehlgeschlagen") == "de"

    def test_german_by_stopwords_without_umlauts(self) -> None:
        assert detect_language("Ich kann mich nicht anmelden und die Seite geht nicht") == "de"

    def test_english_stays_english(self) -> None:
        assert detect_language("The checkout page crashes every time I try to pay") == "en"

    def test_short_or_empty_defaults(self) -> None:
        assert detect_language("") == "en"
        assert detect_language("ok") == "en"
        assert detect_language("   ") == "en"

    def test_english_with_german_loanword_not_misclassified(self) -> None:
        assert detect_language("The app feels like kindergarten software honestly") == "en"


class TestIngestionWiring:
    def test_csv_without_language_column_detects_german(self) -> None:
        csv_text = (
            "signal_id,feedback_text\n"
            "L-1,Meine Zahlung wurde nicht verarbeitet und der Support antwortet nicht\n"
            "L-2,The refund arrived quickly - great service\n"
        )
        signals = parse_signal_csv(csv_text)
        assert signals[0].language == "de"
        assert signals[1].language == "en"

    def test_explicit_language_column_wins(self) -> None:
        csv_text = "signal_id,feedback_text,language\nL-3,Alles kaputt und nichts geht,fr\n"
        assert parse_signal_csv(csv_text)[0].language == "fr"

    def test_zendesk_ticket_language_detected(self) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        connector = ZendeskSourceConnector()
        ticket = {
            "id": 7,
            "subject": "Anmeldung",
            "description": "Ich kann mich seit dem Update nicht mehr anmelden, bitte helfen Sie mir",
            "tags": [],
            "priority": "high",
            "status": "open",
            "requester_id": 1,
            "organization_id": 2,
            "created_at": "2026-07-01T10:00:00Z",
            "updated_at": "2026-07-01T11:00:00Z",
        }
        signal = connector._map_ticket(ticket, {}, {})
        assert signal is not None
        assert signal["language"] == "de"
