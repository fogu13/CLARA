"""Lexical tag canonicalization — vocabulary anchoring without embeddings."""

from __future__ import annotations

from app.services.tag_canon import TagCanonicalizer


def test_failure_class_synonyms_map_to_vocabulary() -> None:
    canon = TagCanonicalizer(["sync_error", "billing_error"])
    assert canon.canonicalize("sync_failure") == "sync_error"
    assert canon.canonicalize("sync_issue") == "sync_error"
    assert canon.canonicalize("billing_problem") == "billing_error"


def test_stemming_merges_plural_and_ing_variants() -> None:
    canon = TagCanonicalizer(["slow_load", "analytics_feature"])
    assert canon.canonicalize("slow_loading") == "slow_load"
    assert canon.canonicalize("analytics_features") == "analytics_feature"


def test_near_miss_one_token_containment() -> None:
    canon = TagCanonicalizer(["app_freeze"])
    assert canon.canonicalize("mobile_app_freeze") == "app_freeze"


def test_distinct_themes_never_merge() -> None:
    canon = TagCanonicalizer(["checkout_failure", "app_freeze", "payment_error"])
    # Same class token but different theme token: stays itself.
    assert canon.canonicalize("signup_failure") == "signup_failure"
    # Two-token difference: stays itself.
    assert canon.canonicalize("app_crash") == "app_crash"
    assert canon.canonicalize("payment_retry") == "payment_retry"


def test_exact_vocabulary_tags_pass_through() -> None:
    canon = TagCanonicalizer(["churn_risk"])
    assert canon.canonicalize("churn_risk") == "churn_risk"
    assert canon.canonicalize("unknown_new_theme") == "unknown_new_theme"


def test_in_run_learning_converges_later_variants() -> None:
    canon = TagCanonicalizer([])
    first = canon.canonicalize_all(["dashboard_outage"])
    assert first == ["dashboard_outage"]
    # A later signal's variant converges on the earlier run-local name.
    assert canon.canonicalize_all(["dashboard_outages"]) == ["dashboard_outage"]


def test_first_registered_wins_and_dedup() -> None:
    canon = TagCanonicalizer(["service_outage"])
    out = canon.canonicalize_all(["service_outages", "service_outage"])
    assert out == ["service_outage"]  # merged variants dedup to one entry


def test_specific_tag_not_collapsed_onto_bare_single_token() -> None:
    # audit finding: checkout_crash must NOT drop "crash" onto a bare vocab
    # 'checkout' — a specific tag keeps its detail.
    canon = TagCanonicalizer(["checkout"])
    assert canon.canonicalize("checkout_crash") == "checkout_crash"


def test_vocabulary_growth_is_capped() -> None:
    canon = TagCanonicalizer([])
    for i in range(TagCanonicalizer._MAX_VOCAB + 50):
        canon.register(f"tag_{i}")
    assert len(canon._exact) == TagCanonicalizer._MAX_VOCAB
