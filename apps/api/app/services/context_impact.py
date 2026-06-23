from __future__ import annotations

from collections import defaultdict
from datetime import date

from app.domain.models import (
    AffectedCohort,
    AffectedAccountSummary,
    AffectedContextExplorer,
    ContextImpactSummary,
    ContextDataQualityWarning,
    ContextRoutingRecommendation,
    CustomerContextRecord,
    ImpactFactors,
    ProblemRecord,
)
from app.domain.scoring import impact_band, normalized_impact_score

HIGH_VALUE_ACCOUNT_THRESHOLD = 50_000.0
FULL_FINANCIAL_EXPOSURE_VALUE = 250_000.0
FULL_CUSTOMER_REACH = 250
FULL_ACCOUNT_EXPOSURE = 100
LOW_HEALTH_THRESHOLD = 0.65
RENEWAL_URGENCY_DAYS = 90
RENEWAL_GRACE_DAYS = 30
VALID_CONSENT_STATUSES = {"granted", "valid", "opted_in", "consented"}
HIGH_INFLUENCE_CONTACT_ROLES = {
    "admin",
    "billing_admin",
    "decision_maker",
    "economic_buyer",
    "executive_sponsor",
    "owner",
}
PRIORITY_LIFECYCLE_STAGES = {
    "adoption",
    "expansion",
    "implementation",
    "onboarding",
    "pilot",
    "renewal",
}
AT_RISK_LIFECYCLE_TERMS = {"at_risk", "churn", "cancellation", "downgrade"}


def has_valid_consent(record: CustomerContextRecord) -> bool:
    return record.consent_status.strip().lower() in VALID_CONSENT_STATUSES


def evidence_customer_ids(problem: ProblemRecord) -> set[str]:
    return {evidence.customer_id for evidence in problem.evidence}


def evidence_account_ids(problem: ProblemRecord) -> set[str]:
    return {evidence.account_id for evidence in problem.evidence}


def context_matches_problem(
    problem: ProblemRecord,
    context_record: CustomerContextRecord,
) -> bool:
    return (
        context_record.customer_id in evidence_customer_ids(problem)
        or context_record.account_id in evidence_account_ids(problem)
    )


def matched_context_records(
    problem: ProblemRecord,
    context_records: list[CustomerContextRecord],
) -> list[CustomerContextRecord]:
    return [
        record for record in context_records if context_matches_problem(problem, record)
    ]


def summarize_context_impact(
    problem: ProblemRecord,
    context_records: list[CustomerContextRecord],
) -> ContextImpactSummary | None:
    matched_records = matched_context_records(problem, context_records)
    if not matched_records:
        return None

    account_values: dict[str, float] = {}
    for record in matched_records:
        account_values[record.account_id] = max(
            account_values.get(record.account_id, 0.0),
            record.account_value,
        )

    health_scores = [
        record.health_score
        for record in matched_records
        if record.health_score is not None
    ]
    average_health_score = (
        round(sum(health_scores) / len(health_scores), 3) if health_scores else None
    )
    consent_risk_customers = sum(
        1 for record in matched_records if not has_valid_consent(record)
    )
    renewal_risk_account_ids = {
        record.account_id for record in matched_records if has_renewal_risk(record)
    }
    priority_lifecycle_account_ids = {
        record.account_id
        for record in matched_records
        if has_priority_lifecycle_stage(record)
    }
    at_risk_lifecycle_account_ids = {
        record.account_id
        for record in matched_records
        if has_at_risk_lifecycle_stage(record)
    }

    return ContextImpactSummary(
        matched_customers=len({record.customer_id for record in matched_records}),
        matched_accounts=len(account_values),
        high_value_accounts=sum(
            1 for account_value in account_values.values() if account_value >= HIGH_VALUE_ACCOUNT_THRESHOLD
        ),
        total_account_value=round(sum(account_values.values()), 2),
        average_health_score=average_health_score,
        consent_risk_customers=consent_risk_customers,
        renewal_risk_accounts=len(renewal_risk_account_ids),
        priority_lifecycle_accounts=len(priority_lifecycle_account_ids),
        at_risk_lifecycle_accounts=len(at_risk_lifecycle_account_ids),
        owners=sorted({record.owner for record in matched_records if record.owner}),
        product_owners=sorted(
            {record.product_owner for record in matched_records if record.product_owner}
        ),
        regions=sorted({record.region for record in matched_records if record.region}),
    )


def unique_sorted(values: list[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def normalized_contact_role(record: CustomerContextRecord) -> str | None:
    if record.contact_role is None:
        return None

    return record.contact_role.strip().lower().replace(" ", "_") or None


def has_high_influence_role(record: CustomerContextRecord) -> bool:
    role = normalized_contact_role(record)
    return role in HIGH_INFLUENCE_CONTACT_ROLES


def normalized_lifecycle_stage(record: CustomerContextRecord) -> str | None:
    if record.lifecycle_stage is None:
        return None

    return record.lifecycle_stage.strip().lower().replace("-", "_").replace(" ", "_") or None


def has_priority_lifecycle_stage(record: CustomerContextRecord) -> bool:
    stage = normalized_lifecycle_stage(record)
    if stage is None:
        return False

    return stage in PRIORITY_LIFECYCLE_STAGES or any(term in stage for term in AT_RISK_LIFECYCLE_TERMS)


def has_at_risk_lifecycle_stage(record: CustomerContextRecord) -> bool:
    stage = normalized_lifecycle_stage(record)
    if stage is None:
        return False

    return any(term in stage for term in AT_RISK_LIFECYCLE_TERMS)


def parsed_renewal_date(record: CustomerContextRecord) -> date | None:
    if record.renewal_date is None:
        return None

    try:
        return date.fromisoformat(record.renewal_date[:10])
    except ValueError:
        return None


def has_renewal_risk(record: CustomerContextRecord, *, today: date | None = None) -> bool:
    renewal_date = parsed_renewal_date(record)
    if renewal_date is None:
        return False

    current_date = today or date.today()
    days_until_renewal = (renewal_date - current_date).days
    return -RENEWAL_GRACE_DAYS <= days_until_renewal <= RENEWAL_URGENCY_DAYS


def average_health_score(records: list[CustomerContextRecord]) -> float | None:
    health_scores = [
        record.health_score for record in records if record.health_score is not None
    ]
    if not health_scores:
        return None

    return round(sum(health_scores) / len(health_scores), 3)


def build_account_summaries(
    records: list[CustomerContextRecord],
) -> list[AffectedAccountSummary]:
    grouped_records: dict[str, list[CustomerContextRecord]] = defaultdict(list)
    for record in records:
        grouped_records[record.account_id].append(record)

    summaries = []
    for account_id, account_records in grouped_records.items():
        account_value = max(record.account_value for record in account_records)
        account_names = unique_sorted([record.account_name for record in account_records])
        parent_account_ids = unique_sorted(
            [record.parent_account_id for record in account_records]
        )
        parent_account_names = unique_sorted(
            [record.parent_account_name for record in account_records]
        )
        summaries.append(
            AffectedAccountSummary(
                account_id=account_id,
                account_name=account_names[0] if account_names else None,
                parent_account_id=parent_account_ids[0] if parent_account_ids else None,
                parent_account_name=parent_account_names[0] if parent_account_names else None,
                customer_count=len({record.customer_id for record in account_records}),
                account_value=account_value,
                high_value=account_value >= HIGH_VALUE_ACCOUNT_THRESHOLD,
                consent_risk_customers=sum(
                    1 for record in account_records if not has_valid_consent(record)
                ),
                average_health_score=average_health_score(account_records),
                contact_roles=unique_sorted(
                    [record.contact_role for record in account_records]
                ),
                lifecycle_stages=unique_sorted(
                    [record.lifecycle_stage for record in account_records]
                ),
                plan_tiers=unique_sorted([record.plan_tier for record in account_records]),
                renewal_dates=unique_sorted(
                    [record.renewal_date for record in account_records]
                ),
                owners=unique_sorted([record.owner for record in account_records]),
                product_owners=unique_sorted(
                    [record.product_owner for record in account_records]
                ),
                regions=unique_sorted([record.region for record in account_records]),
            )
        )

    return sorted(
        summaries,
        key=lambda summary: (not summary.high_value, -summary.account_value, summary.account_id),
    )


def context_data_quality_warnings(
    *,
    problem: ProblemRecord,
    matched_records: list[CustomerContextRecord],
    missing_customer_ids: list[str],
    missing_account_ids: list[str],
) -> list[ContextDataQualityWarning]:
    warnings: list[ContextDataQualityWarning] = []

    if missing_customer_ids:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-customers",
                severity="warning",
                field="customer_id",
                message="Evidence references customers without imported context rows.",
                customer_ids=missing_customer_ids,
            )
        )

    if missing_account_ids:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-accounts",
                severity="warning",
                field="account_id",
                message="Evidence references accounts without imported context rows.",
                account_ids=missing_account_ids,
            )
        )

    consent_risk_records = [
        record for record in matched_records if not has_valid_consent(record)
    ]
    if consent_risk_records:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-consent-risk",
                severity="warning",
                field="consent_status",
                message="Some matched customers do not have valid contact consent.",
                customer_ids=sorted({record.customer_id for record in consent_risk_records}),
                account_ids=sorted({record.account_id for record in consent_risk_records}),
            )
        )

    missing_health_records = [
        record for record in matched_records if record.health_score is None
    ]
    if missing_health_records:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-health",
                severity="info",
                field="health_score",
                message="Some matched customers are missing health scores.",
                customer_ids=sorted({record.customer_id for record in missing_health_records}),
                account_ids=sorted({record.account_id for record in missing_health_records}),
            )
        )

    missing_value_records = [
        record for record in matched_records if record.account_value <= 0
    ]
    if missing_value_records:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-account-value",
                severity="info",
                field="account_value",
                message="Some matched accounts have no account value.",
                customer_ids=sorted({record.customer_id for record in missing_value_records}),
                account_ids=sorted({record.account_id for record in missing_value_records}),
            )
        )

    missing_role_records = [
        record for record in matched_records if record.contact_role is None
    ]
    if missing_role_records:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-contact-role",
                severity="info",
                field="contact_role",
                message="Some matched customers are missing contact roles for routing.",
                customer_ids=sorted({record.customer_id for record in missing_role_records}),
                account_ids=sorted({record.account_id for record in missing_role_records}),
            )
        )

    missing_product_owner_records = [
        record for record in matched_records if record.product_owner is None
    ]
    if missing_product_owner_records:
        warnings.append(
            ContextDataQualityWarning(
                warning_id=f"{problem.problem_id}-missing-product-owner",
                severity="info",
                field="product_owner",
                message="Some matched customers are missing product owners for routing.",
                customer_ids=sorted(
                    {record.customer_id for record in missing_product_owner_records}
                ),
                account_ids=sorted(
                    {record.account_id for record in missing_product_owner_records}
                ),
            )
        )

    return warnings


def routing_reason_for(records: list[CustomerContextRecord]) -> str:
    reasons = []
    if any(record.account_value >= HIGH_VALUE_ACCOUNT_THRESHOLD for record in records):
        reasons.append("high-value account exposure")
    if any(not has_valid_consent(record) for record in records):
        reasons.append("consent risk")
    if any(has_high_influence_role(record) for record in records):
        reasons.append("high-influence contact involved")
    average_health = average_health_score(records)
    if average_health is not None and average_health < LOW_HEALTH_THRESHOLD:
        reasons.append("low account health")
    if any(record.parent_account_id for record in records):
        reasons.append("parent-account relationship")

    return ", ".join(reasons) if reasons else "matched account owner"


def routing_priority_for(records: list[CustomerContextRecord]) -> str:
    if any(record.account_value >= HIGH_VALUE_ACCOUNT_THRESHOLD for record in records):
        return "high"
    if any(not has_valid_consent(record) for record in records):
        return "high"
    average_health = average_health_score(records)
    if average_health is not None and average_health < LOW_HEALTH_THRESHOLD:
        return "medium"

    return "medium" if any(has_high_influence_role(record) for record in records) else "low"


def build_routing_recommendations(
    records: list[CustomerContextRecord],
) -> list[ContextRoutingRecommendation]:
    grouped_records: dict[str, list[CustomerContextRecord]] = defaultdict(list)
    for record in records:
        if record.owner is None:
            continue
        grouped_records[record.owner].append(record)

    recommendations = [
        ContextRoutingRecommendation(
            owner=owner,
            priority=routing_priority_for(owner_records),
            reason=routing_reason_for(owner_records),
            customer_ids=sorted({record.customer_id for record in owner_records}),
            account_ids=sorted({record.account_id for record in owner_records}),
            contact_roles=unique_sorted(
                [record.contact_role for record in owner_records]
            ),
        )
        for owner, owner_records in grouped_records.items()
    ]

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        recommendations,
        key=lambda recommendation: (
            priority_rank.get(recommendation.priority, 3),
            recommendation.owner,
        ),
    )


def build_affected_context_explorer(
    problem: ProblemRecord,
    context_records: list[CustomerContextRecord],
) -> AffectedContextExplorer:
    matched_records = matched_context_records(problem, context_records)
    context_customer_ids = {record.customer_id for record in context_records}
    context_account_ids = {record.account_id for record in context_records}
    missing_customer_ids = sorted(evidence_customer_ids(problem) - context_customer_ids)
    missing_account_ids = sorted(evidence_account_ids(problem) - context_account_ids)

    return AffectedContextExplorer(
        problem_id=problem.problem_id,
        context_impact=enrich_problem_with_context(problem, context_records).context_impact,
        accounts=build_account_summaries(matched_records),
        customers=sorted(
            matched_records,
            key=lambda record: (record.account_id, record.customer_id),
        ),
        missing_customer_ids=missing_customer_ids,
        missing_account_ids=missing_account_ids,
        warnings=context_data_quality_warnings(
            problem=problem,
            matched_records=matched_records,
            missing_customer_ids=missing_customer_ids,
            missing_account_ids=missing_account_ids,
        ),
        routing_recommendations=build_routing_recommendations(matched_records),
    )


def factor_drivers(
    original_factors: ImpactFactors,
    adjusted_factors: ImpactFactors,
) -> list[str]:
    drivers = []
    if adjusted_factors.customer_reach > original_factors.customer_reach:
        drivers.append("customer reach")
    if adjusted_factors.account_exposure > original_factors.account_exposure:
        drivers.append("account exposure")
    if adjusted_factors.financial_exposure > original_factors.financial_exposure:
        drivers.append("financial exposure")
    if adjusted_factors.regulatory_risk > original_factors.regulatory_risk:
        drivers.append("consent risk")
    if adjusted_factors.severity > original_factors.severity:
        drivers.append("account health")

    return drivers


def context_driver_labels(
    context_impact: ContextImpactSummary,
    original_factors: ImpactFactors,
    adjusted_factors: ImpactFactors,
) -> list[str]:
    drivers: list[str] = []
    if (
        context_impact.renewal_risk_accounts > 0
        and adjusted_factors.financial_exposure > original_factors.financial_exposure
    ):
        drivers.append("renewal risk")
    if (
        context_impact.priority_lifecycle_accounts > 0
        and adjusted_factors.journey_criticality > original_factors.journey_criticality
    ):
        drivers.append("lifecycle stage")
    if (
        context_impact.at_risk_lifecycle_accounts > 0
        and adjusted_factors.severity > original_factors.severity
    ):
        drivers.append("at-risk lifecycle")

    return drivers


def apply_context_to_factors(
    factors: ImpactFactors,
    context_impact: ContextImpactSummary,
) -> ImpactFactors:
    factor_updates = factors.model_dump()
    factor_updates["customer_reach"] = max(
        factors.customer_reach,
        min(1.0, context_impact.matched_customers / FULL_CUSTOMER_REACH),
    )
    factor_updates["account_exposure"] = max(
        factors.account_exposure,
        min(1.0, context_impact.matched_accounts / FULL_ACCOUNT_EXPOSURE),
    )
    factor_updates["financial_exposure"] = max(
        factors.financial_exposure,
        min(1.0, context_impact.total_account_value / FULL_FINANCIAL_EXPOSURE_VALUE),
    )
    matched_account_count = max(context_impact.matched_accounts, 1)
    if context_impact.renewal_risk_accounts > 0:
        factor_updates["financial_exposure"] = max(
            factor_updates["financial_exposure"],
            min(1.0, context_impact.renewal_risk_accounts / matched_account_count),
        )

    if context_impact.matched_customers > 0:
        factor_updates["regulatory_risk"] = max(
            factors.regulatory_risk,
            context_impact.consent_risk_customers / context_impact.matched_customers,
        )

    if (
        context_impact.average_health_score is not None
        and context_impact.average_health_score < LOW_HEALTH_THRESHOLD
    ):
        factor_updates["severity"] = max(
            factors.severity,
            min(1.0, 1.0 - context_impact.average_health_score),
        )

    if context_impact.priority_lifecycle_accounts > 0:
        factor_updates["journey_criticality"] = max(
            factor_updates["journey_criticality"],
            min(1.0, context_impact.priority_lifecycle_accounts / matched_account_count),
        )

    if context_impact.at_risk_lifecycle_accounts > 0:
        factor_updates["severity"] = max(
            factor_updates["severity"],
            min(1.0, context_impact.at_risk_lifecycle_accounts / matched_account_count),
        )

    return ImpactFactors.model_validate(factor_updates)


def enrich_problem_with_context(
    problem: ProblemRecord,
    context_records: list[CustomerContextRecord],
) -> ProblemRecord:
    context_impact = summarize_context_impact(problem, context_records)
    if context_impact is None:
        return problem

    adjusted_factors = apply_context_to_factors(problem.impact_factors, context_impact)
    base_score = problem.impact_score or normalized_impact_score(problem.impact_factors.model_dump())
    adjusted_score = normalized_impact_score(adjusted_factors.model_dump())
    adjusted_score = max(base_score, adjusted_score)
    score_delta = round(adjusted_score - base_score, 3)
    drivers = factor_drivers(problem.impact_factors, adjusted_factors)
    for driver in context_driver_labels(context_impact, problem.impact_factors, adjusted_factors):
        if driver not in drivers:
            drivers.append(driver)
    context_impact = context_impact.model_copy(
        update={
            "score_delta": score_delta,
            "drivers": drivers,
        }
    )
    affected_cohort = problem.affected_cohort.model_copy(
        update={
            "customers": max(
                problem.affected_cohort.customers,
                context_impact.matched_customers,
            ),
            "accounts": max(
                problem.affected_cohort.accounts,
                context_impact.matched_accounts,
            ),
            "high_value_accounts": max(
                problem.affected_cohort.high_value_accounts,
                context_impact.high_value_accounts,
            ),
        }
    )

    return problem.model_copy(
        update={
            "impact_factors": adjusted_factors,
            "impact_score": adjusted_score,
            "impact_band": impact_band(adjusted_score),
            "affected_cohort": AffectedCohort.model_validate(affected_cohort),
            "context_impact": context_impact,
        }
    )
