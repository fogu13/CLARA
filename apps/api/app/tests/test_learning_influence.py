"""Tests for the noise-controlled learning-influence probe and the in-run
enrichment A/B helpers in run_live (the USP-evidence + significance machinery)."""

from __future__ import annotations

import app.evals.run_live as rl
from app.evals.harness import load_golden_set


def _insight(title: str) -> dict:
    return {"suggested_actions": [{"type": "create_ticket", "title": title, "description": "d"}]}


# ecommerce_checkout learning mentions: automatic payment retry / fallback provider.
_GROUP = [("ecommerce_checkout", [{"tags": ["checkout_failure"], "text": "a"},
                                  {"tags": ["checkout_failure"], "text": "b"}])]


class TestInfluenceProbe:
    def test_adoption_detected_despite_rewording(self, monkeypatch) -> None:
        # off rewords every call (pure jitter, no remedy terms); on adopts the
        # learning's remedy vocabulary. Adoption must register even though strings
        # change on every call (reworded == True).
        calls = {"n": 0}

        def fake(tag, signals, *, learnings=None):
            calls["n"] += 1
            if learnings:
                return _insight("Deploy automatic payment retry with fallback provider")
            return _insight(f"Investigate pipeline variant {calls['n']}")

        monkeypatch.setattr(rl, "synthesize_cluster", fake)
        r = rl._learning_influence_probe(_GROUP)
        assert r["themes"] == 1
        assert r["adoption_rate"] == 1.0
        assert r["reworded_rate"] == 1.0          # model jitter present...
        assert r["alignment_lift"] > 0.0          # ...but adoption is measured anyway
        assert r["examples"][0]["adopted"] is True

    def test_no_adoption_when_action_ignores_learning(self, monkeypatch) -> None:
        # on-action shares no remedy terms with the learning -> not adopted.
        def fake(tag, signals, *, learnings=None):
            return _insight("Schedule a generic stakeholder meeting")

        monkeypatch.setattr(rl, "synthesize_cluster", fake)
        r = rl._learning_influence_probe(_GROUP)
        assert r["adoption_rate"] == 0.0
        assert r["examples"][0]["adopted"] is False

    def test_failed_synthesis_drops_the_theme(self, monkeypatch) -> None:
        monkeypatch.setattr(rl, "synthesize_cluster", lambda *a, **k: None)
        r = rl._learning_influence_probe(_GROUP)
        assert r["themes"] == 0
        assert r["adoption_rate"] == 0.0


class TestAlignment:
    def test_alignment_counts_learning_terms_in_action(self) -> None:
        ltok = rl._content_tokens("automatic payment retry with fallback provider")
        full = _insight("automatic payment retry fallback provider")
        assert rl._alignment(full, ltok) == 1.0
        assert rl._alignment(_insight("unrelated meeting notes"), ltok) == 0.0

    def test_content_tokens_drops_stopwords_and_short(self) -> None:
        toks = rl._content_tokens("Prefer the automatic retry over a generic fix")
        assert "automatic" in toks and "retry" in toks
        assert "prefer" not in toks and "the" not in toks and "over" not in toks


class TestProbeHelpers:
    def test_action_signature_ignores_order_insensitive_fields(self) -> None:
        a = {"suggested_actions": [{"type": "t", "title": "x", "description": "d", "priority": 1}]}
        b = {"suggested_actions": [{"type": "t", "title": "x", "description": "d", "priority": 9}]}
        assert rl._action_signature(a) == rl._action_signature(b)  # priority not part of signature

    def test_action_signature_distinguishes_titles(self) -> None:
        assert rl._action_signature(_insight("x")) != rl._action_signature(_insight("y"))

    def test_dominant_tag_picks_most_common(self) -> None:
        sigs = [{"tags": ["a", "b"]}, {"tags": ["a"]}, {"tags": ["c"]}]
        assert rl._dominant_tag(sigs) == "a"

    def test_dominant_tag_empty(self) -> None:
        assert rl._dominant_tag([{"tags": []}]) == "general"

    def test_probe_learning_uses_curated_text_when_available(self) -> None:
        learning = rl._probe_learning("ecommerce_checkout", "checkout_failure")
        assert learning["learning_status"] == "worked"
        assert learning["topic"] == "checkout_failure"
        assert "retry" in learning["summary"]


class TestEnrichmentAB:
    def test_mcnemar_ab_maps_gained_and_lost(self) -> None:
        # off wrong on two items that on gets right; nothing regresses.
        r = rl._mcnemar_ab([0, 0, 1], [1, 1, 1])
        assert r["gained"] == 2
        assert r["lost"] == 0

    def test_score_enrichment_perfect_labels(self, monkeypatch) -> None:
        golden = load_golden_set()
        expected = {g["id"]: g["expected"] for g in golden}

        def fake_enrich(signals, *, exemplars=None, batch_size=25):
            return [{"id": s["id"], **expected[s["id"]],
                     "sentiment_score": 0.0} for s in signals]

        monkeypatch.setattr(rl, "enrich_signals", fake_enrich)
        scored = rl._score_enrichment(exemplars=None)
        v = scored["vectors"]
        assert sum(v["sentiment"]) == len(golden)
        assert sum(v["urgency"]) == len(golden)
        assert sum(v["tag_exact"]) == len(golden)   # perfect tag set match
        assert scored["failures"] == []
