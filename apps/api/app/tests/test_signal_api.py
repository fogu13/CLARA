from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
        )
    )


def test_seed_signals_are_available_and_generate_candidates() -> None:
    client = make_client()

    signals = client.get("/signals").json()
    candidates = client.get("/problem-candidates").json()

    assert len(signals) == 3
    assert candidates
    assert candidates[0]["journey_stage"] == "Identity Verification"
    assert candidates[0]["signal_count"] == 3
    assert candidates[0]["evidence"]
    assert candidates[0]["review_status"] == "duplicate"
    assert candidates[0]["duplicate_problem_id"] == "PRB-108"


def test_taxonomy_catalogs_are_exposed_with_versioning_and_locks() -> None:
    client = make_client()

    taxonomies = client.get("/taxonomies").json()

    assert {catalog["taxonomy_type"] for catalog in taxonomies} == {
        "product",
        "journey",
        "contact_reason",
        "marketing",
        "compliance",
    }
    product_catalog = next(
        catalog for catalog in taxonomies if catalog["taxonomy_type"] == "product"
    )
    assert product_catalog["version"] == "product-2026.06"
    assert any(category["locked"] for category in product_catalog["categories"])
    assert product_catalog["categories"][0]["change_history"][0]["operation"] == "lock"


def test_terminology_dictionary_exposes_multilingual_aliases() -> None:
    client = make_client()

    dictionary = client.get("/terminology-dictionary").json()

    accepted_documents = next(
        entry for entry in dictionary if entry["term_id"] == "accepted_documents"
    )
    assert accepted_documents["canonical_term"] == "accepted documents"
    assert accepted_documents["taxonomy_type"] == "contact_reason"
    assert accepted_documents["category_ids"] == ["document_requirements"]
    assert {"de", "en"} == set(accepted_documents["languages"])
    assert "dokument akzeptiert" in accepted_documents["aliases"]


def test_language_quality_reports_german_english_readiness() -> None:
    client = make_client()

    report = client.get("/language-quality").json()

    rows = {row["language"]: row for row in report["languages"]}
    assert report["total_signals"] == 3
    assert report["german_english_ready"] is True
    assert rows["de"]["signal_count"] == 2
    assert rows["de"]["terminology_entries"] > 0
    assert rows["en"]["signal_count"] == 1
    assert rows["en"]["readiness"] == "ready"


def category_by_id(catalog: dict, category_id: str) -> dict:
    return next(category for category in catalog["categories"] if category["category_id"] == category_id)


def test_taxonomy_categories_can_be_renamed_with_version_history() -> None:
    client = make_client()

    response = client.post(
        "/taxonomies/journey/categories/rename",
        json={
            "category_id": "onboarding",
            "label": "Activation onboarding",
            "description": "Activation and first-run verification journey.",
            "actor": "research_lead",
        },
    )

    assert response.status_code == 200
    catalog = response.json()
    category = category_by_id(catalog, "onboarding")
    assert catalog["version"] == "journey-2026.06.rev1"
    assert category["label"] == "Activation onboarding"
    assert category["description"] == "Activation and first-run verification journey."
    assert category["change_history"][-1]["operation"] == "rename"
    assert category["change_history"][-1]["actor"] == "research_lead"


def test_taxonomy_categories_can_be_locked_and_then_protect_edits() -> None:
    client = make_client()

    response = client.post(
        "/taxonomies/contact_reason/categories/lock",
        json={"category_id": "payment_failure", "actor": "governance"},
    )

    assert response.status_code == 200
    catalog = response.json()
    category = category_by_id(catalog, "payment_failure")
    assert category["locked"] is True
    assert category["change_history"][-1]["operation"] == "lock"

    blocked_response = client.post(
        "/taxonomies/contact_reason/categories/rename",
        json={"category_id": "payment_failure", "label": "Card payment failure"},
    )

    assert blocked_response.status_code == 400
    assert "locked" in blocked_response.json()["detail"]


def test_taxonomy_categories_can_be_merged_into_new_category() -> None:
    client = make_client()

    response = client.post(
        "/taxonomies/journey/categories/merge",
        json={
            "source_category_ids": ["purchase_checkout", "retention"],
            "target_category_id": "lifecycle_friction",
            "target_label": "Lifecycle friction",
            "target_description": "Checkout and retention friction patterns.",
            "actor": "taxonomy_owner",
        },
    )

    assert response.status_code == 200
    catalog = response.json()
    target = category_by_id(catalog, "lifecycle_friction")
    checkout = category_by_id(catalog, "purchase_checkout")
    retention = category_by_id(catalog, "retention")
    assert catalog["version"] == "journey-2026.06.rev1"
    assert target["label"] == "Lifecycle friction"
    assert "checkout" in target["terms"]
    assert "renewal" in target["terms"]
    assert checkout["status"] == "merged"
    assert checkout["parent_id"] == "lifecycle_friction"
    assert retention["status"] == "merged"
    assert target["change_history"][-1]["operation"] == "merge"


def test_taxonomy_categories_can_be_split_into_children() -> None:
    client = make_client()

    response = client.post(
        "/taxonomies/contact_reason/categories/split",
        json={
            "source_category_id": "payment_failure",
            "categories": [
                {
                    "category_id": "card_decline",
                    "label": "Card decline",
                    "description": "Card issuer or decline failures.",
                    "terms": ["card", "declined"],
                },
                {
                    "category_id": "payment_authorization",
                    "label": "Payment authorization",
                    "description": "Authorization and transaction approval failures.",
                    "terms": ["authorization", "transaction failed"],
                },
            ],
            "actor": "support_ops",
        },
    )

    assert response.status_code == 200
    catalog = response.json()
    source = category_by_id(catalog, "payment_failure")
    card_decline = category_by_id(catalog, "card_decline")
    authorization = category_by_id(catalog, "payment_authorization")
    assert catalog["version"] == "contact-reason-2026.06.rev1"
    assert source["status"] == "split"
    assert card_decline["parent_id"] == "payment_failure"
    assert authorization["parent_id"] == "payment_failure"
    assert source["change_history"][-1]["operation"] == "split"


def test_problem_candidates_include_trusted_classification_context() -> None:
    client = make_client()

    candidate = client.get("/problem-candidates").json()[0]

    assert candidate["taxonomy_version"]
    assert candidate["classifications"]
    assert {classification["taxonomy_type"] for classification in candidate["classifications"]}
    assert candidate["terminology_hits"]
    assert "accepted documents" in candidate["terminology_hits"]
    assert candidate["root_cause_analysis"]["confidence"] > 0
    assert "Identity Verification" in candidate["root_cause_analysis"]["hypothesis"]
    assert candidate["root_cause_analysis"]["factors"]
    assert candidate["root_cause_analysis"]["validation_questions"]
    assert candidate["known_limitations"]
    assert candidate["evaluation_notes"]
    assert candidate["emerging_problem_score"] > 0


def test_emerging_problem_report_ranks_candidate_drivers() -> None:
    client = make_client()

    report = client.get("/emerging-problems").json()

    assert report["candidate_count"] >= 1
    assert report["signals"]
    top_signal = report["signals"][0]
    assert top_signal["candidate_id"]
    assert top_signal["emerging_score"] >= 0.48
    assert top_signal["trend_label"] in {"watch", "action"}
    assert top_signal["drivers"]
    assert top_signal["recommended_next_step"]
    assert "Identity Verification" in top_signal["journey_stage"]


def test_signal_import_skips_duplicates() -> None:
    client = make_client()
    new_signal = {
        "signal_id": "SIG-NEW-1",
        "customer_id": "C-999",
        "account_id": "A-999",
        "source": "csv_upload",
        "journey": "customer_onboarding",
        "journey_stage": "identity_verification",
        "campaign_exposure": [],
        "product_events": ["verification_started"],
        "feedback_text": "I uploaded the document but the instructions are still unclear.",
        "language": "en",
        "timestamp": "2026-06-21T09:00:00Z",
    }

    first_response = client.post("/signals/import", json={"signals": [new_signal]})
    second_response = client.post("/signals/import", json={"signals": [new_signal]})

    assert first_response.status_code == 200
    assert first_response.json()["imported"] == 1
    assert second_response.json()["imported"] == 0
    assert second_response.json()["skipped_duplicates"] == 1
    assert second_response.json()["total_signals"] == 4


def test_problem_candidate_can_be_promoted_into_action_queue() -> None:
    client = make_client()
    candidate = client.get("/problem-candidates").json()[0]

    promotion_response = client.post(f"/problem-candidates/{candidate['candidate_id']}/promote")
    problems = client.get("/problems").json()

    assert promotion_response.status_code == 200
    promoted_problem = promotion_response.json()
    assert promoted_problem["problem_id"].startswith("PRB-DRAFT-")
    assert promoted_problem["status"] == "validation_required"
    assert promoted_problem["action_proposals"]
    assert any(problem["problem_id"] == promoted_problem["problem_id"] for problem in problems)


def test_duplicate_candidate_accept_is_rejected() -> None:
    client = make_client()
    candidate = client.get("/problem-candidates").json()[0]

    response = client.post(
        f"/problem-candidates/{candidate['candidate_id']}/accept",
        json={"reviewer": "test_reviewer", "note": "Do not duplicate existing problem."},
    )

    assert response.status_code == 409
    assert "PRB-108" in response.json()["detail"]


def test_problem_candidate_can_be_rejected() -> None:
    client = make_client()
    candidate = client.get("/problem-candidates").json()[0]

    response = client.post(
        f"/problem-candidates/{candidate['candidate_id']}/reject",
        json={"reviewer": "test_reviewer", "note": "Covered by existing problem."},
    )

    assert response.status_code == 200
    rejected = response.json()
    assert rejected["review_status"] == "rejected"
    assert rejected["reviewer"] == "test_reviewer"
    assert rejected["review_note"] == "Covered by existing problem."


def test_unique_candidate_can_be_accepted_into_action_queue() -> None:
    client = make_client()
    new_signal = {
        "signal_id": "SIG-CHECKOUT-1",
        "customer_id": "C-777",
        "account_id": "A-777",
        "source": "csv_upload",
        "journey": "checkout",
        "journey_stage": "payment",
        "campaign_exposure": ["cart_recovery"],
        "product_events": ["payment_started", "payment_failed"],
        "feedback_text": "Payment fails after I enter my card.",
        "language": "en",
        "timestamp": "2026-06-21T10:00:00Z",
    }
    client.post("/signals/import", json={"signals": [new_signal]})
    candidate = next(
        candidate
        for candidate in client.get("/problem-candidates").json()
        if candidate["candidate_id"] == "CAND-CHECKOUT-PAYMENT"
    )

    response = client.post(
        f"/problem-candidates/{candidate['candidate_id']}/accept",
        json={"reviewer": "test_reviewer", "note": "Create the checkout draft."},
    )

    assert response.status_code == 200
    promoted_problem = response.json()
    assert promoted_problem["problem_id"] == "PRB-DRAFT-CHECKOUT-PAYMENT"

    accepted_candidate = next(
        candidate
        for candidate in client.get("/problem-candidates").json()
        if candidate["candidate_id"] == "CAND-CHECKOUT-PAYMENT"
    )
    assert accepted_candidate["review_status"] == "accepted"
    assert accepted_candidate["reviewer"] == "test_reviewer"
