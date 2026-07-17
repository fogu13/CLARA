"""Load the three REAL public feedback datasets into one labelled corpus.

Source of truth: each dataset's `04_*_detailed_research_table.csv`, which carries the
human-curated gold ("seed") labels. Synthetic datasets are intentionally NOT loaded.

A record has: id, sector, source, language, star_rating (int|None), text,
and gold labels: theme, journey_stage, owner, action, risk (risk may be None
for Lieferando, which ships company_response_pattern instead of risk_seed).
"""
from __future__ import annotations
import csv
import os
from dataclasses import dataclass, asdict
from typing import Optional

# Resolve the datasets relative to this file so the harness is path-independent.
THESIS_CHATGPT = os.environ.get(
    "THESIS_DATA_DIR",
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Thesis_ChatGPT")),
)

DATASETS = {
    "trade_republic": "trade_republic_public_feedback_test_dataset/04_trade_republic_detailed_research_table.csv",
    "henkel": "henkel_adhesives_public_feedback_test_dataset/04_henkel_adhesives_detailed_research_table.csv",
    "lieferando": "lieferando_public_feedback_test_dataset/04_lieferando_detailed_research_table.csv",
}

SECTOR = {
    "trade_republic": "fintech",
    "henkel": "b2b_industrial",
    "lieferando": "food_delivery",
}


@dataclass
class Signal:
    id: str
    dataset: str
    sector: str
    source: str
    language: str
    star_rating: Optional[int]
    text: str
    theme: str
    journey_stage: str
    owner: str
    action: str
    risk: Optional[str]


def _int_or_none(s: str) -> Optional[int]:
    s = (s or "").strip()
    return int(s) if s.isdigit() else None


def load() -> list[Signal]:
    out: list[Signal] = []
    for name, rel in DATASETS.items():
        path = os.path.join(THESIS_CHATGPT, rel)
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                out.append(
                    Signal(
                        id=r.get("public_signal_id", "").strip(),
                        dataset=name,
                        sector=SECTOR[name],
                        source=(r.get("source") or "").strip(),
                        language=(r.get("language") or "").strip().lower(),
                        star_rating=_int_or_none(r.get("star_rating_1_5", "")),
                        text=(r.get("paraphrased_signal") or "").strip(),
                        theme=(r.get("theme_seed") or "").strip(),
                        journey_stage=(r.get("journey_stage_seed") or "").strip(),
                        owner=(r.get("recommended_owner_seed") or "").strip(),
                        action=(r.get("recommended_action_seed") or "").strip(),
                        risk=(r.get("risk_seed") or "").strip() or None,
                    )
                )
    return out


if __name__ == "__main__":
    sigs = load()
    print(f"loaded {len(sigs)} signals from {len(DATASETS)} real datasets")
    for s in sigs[:2]:
        print(asdict(s))
