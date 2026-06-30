"""Industry profiles — retune the triage's impact prioritisation per industry.

The 8-factor impact score (app/domain/scoring.py) is industry-neutral by default.
But what makes a problem "important" differs by sector: a brokerage weights
regulatory and financial exposure; a food-delivery marketplace weights reach and
recurrence; a B2B manufacturer weights account exposure over raw headcount. A
profile is just a set of weight overrides merged onto the defaults — no new model,
no fine-tuning — so the same engine adapts across industries (the USP claim).

Selection: env ``INDUSTRY_PROFILE`` (active, global) or
``WorkspaceSettings.industry_profile`` (persisted per workspace). Overrides from
``SCORING_WEIGHT_*`` still win on top, so any factor stays hand-tunable.

The weight emphases below are grounded in the real scraped datasets used for the
thesis (Trade Republic=fintech, Lieferando=food_delivery, Henkel=manufacturing_b2b).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.domain.scoring import DEFAULT_IMPACT_WEIGHTS


@dataclass(frozen=True)
class IndustryProfile:
    name: str
    description: str
    # factor -> weight; merged onto DEFAULT_IMPACT_WEIGHTS (unspecified factors keep default)
    weight_overrides: dict[str, float] = field(default_factory=dict)


INDUSTRY_PROFILES: dict[str, IndustryProfile] = {
    "default": IndustryProfile(
        "default", "Industry-neutral baseline weights.", {},
    ),
    "fintech": IndustryProfile(
        "fintech",
        "Brokerage / banking — regulatory and financial exposure dominate; every "
        "issue is high-stakes, so reach matters less than compliance and money.",
        {"regulatory_risk": 1.6, "financial_exposure": 1.5, "severity": 1.4,
         "evidence_confidence": 1.2, "customer_reach": 0.9},
    ),
    "food_delivery": IndustryProfile(
        "food_delivery",
        "High-volume B2C marketplace — reach, recurrence and journey criticality "
        "(the delivery flow) dominate; regulatory risk is comparatively low.",
        {"customer_reach": 1.4, "recurrence": 1.4, "journey_criticality": 1.4,
         "regulatory_risk": 0.8, "account_exposure": 0.7},
    ),
    "manufacturing_b2b": IndustryProfile(
        "manufacturing_b2b",
        "B2B / industrial — fewer, larger accounts, so account and financial "
        "exposure outweigh raw headcount reach.",
        {"account_exposure": 1.6, "financial_exposure": 1.3, "evidence_confidence": 1.2,
         "customer_reach": 0.6, "journey_criticality": 1.0},
    ),
    "saas": IndustryProfile(
        "saas",
        "Subscription software — usage breadth and journey criticality drive "
        "churn; recurring friction compounds.",
        {"customer_reach": 1.3, "journey_criticality": 1.4, "recurrence": 1.2,
         "regulatory_risk": 1.0},
    ),
}


def get_profile(name: str | None) -> IndustryProfile:
    """Resolve a profile by name, falling back to ``default`` for unknown names."""
    return INDUSTRY_PROFILES.get((name or "default").lower(), INDUSTRY_PROFILES["default"])


def weights_for_profile(name: str | None) -> dict[str, float]:
    """Full weight dict for a profile: overrides merged onto the defaults."""
    return {**DEFAULT_IMPACT_WEIGHTS, **get_profile(name).weight_overrides}


def resolve_profile_name() -> str:
    """Active profile name — env INDUSTRY_PROFILE, else 'default'."""
    return os.getenv("INDUSTRY_PROFILE", "default")
