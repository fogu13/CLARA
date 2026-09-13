"""Consistency checks between the manuscript, the claim ledger, the committed
results files and the code the manuscript describes.

Each check pins one correction from the 12 September 2026 review response so
that a later edit cannot silently reintroduce the error. Run from the
repository root with ``python3 -m pytest thesis/test_manuscript_consistency.py``
or directly with ``python3 thesis/test_manuscript_consistency.py``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "thesis" / "manuscript"
LEDGER = ROOT / "thesis" / "CLAIM_LEDGER.md"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _ledger_row(row_id: str) -> str:
    rows = [line for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.startswith(f"| {row_id} ")]
    assert len(rows) == 1, f"ledger row {row_id} missing or duplicated"
    return rows[0]


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


# D1 — the McNemar pairs of the deployment-configuration comparison


def test_mcnemar_pairs_are_cited_only_where_the_files_carry_them() -> None:
    summary = json.loads(_read("thesis/evaluation/results/summary.json"))
    pair_names = [name for block in summary["mcnemar_paired"].values() for name in block]
    assert not any("mistral" in name.lower() for name in pair_names), (
        "summary.json now carries a Mistral pair; the sentence in §5A.4.2 can be restored"
    )
    chapter = _read("thesis/manuscript/05_evaluation_results.md")
    assert "summary.json` under `mcnemar" not in chapter
    assert "summary.json under mcnemar" not in chapter
    pairs_csv = _read("thesis/evaluation/results/compare_runs_pairs.csv")
    assert "glm_production_vs_mistral_production" in pairs_csv
    assert "glm_production_vs_mistral_production" in chapter
    for row_id in ("R4.1", "R4.3"):
        assert "carries no Mistral pair" in _ledger_row(row_id), row_id


# D2 — the two Braun & Clarke (2021) records


def test_braun_and_clarke_2021_records_are_not_conflated() -> None:
    references = _read("thesis/manuscript/references.md").splitlines()
    one_size = [line for line in references if "One size fits all?" in line]
    assert len(one_size) == 1
    assert "*Qualitative Research in Psychology*, 18(3), 328–352" in one_size[0]
    assert "Counselling and Psychotherapy Research" not in one_size[0]
    cpr = [line for line in references if "Counselling and Psychotherapy Research" in line]
    for line in cpr:
        assert "Can I use TA?" in line, line
        assert "21(1), 37–47" in line
    for relative in (
        "thesis/manuscript/03_methodology.md",
        "thesis/manuscript/05_evaluation_results.md",
        "thesis/instruments/codebook_template.md",
    ):
        text = _read(relative)
        assert "2021a" in text, relative
        assert not re.search(r"Braun (?:&|and) Clarke,? \(?(?:2019, )?2021[^ab]", text), relative
    assert "online verification" in _ledger_row("R3.1")


# D3 — the defence deck binary


def test_ledger_records_the_rebuilt_deck_and_the_fit_check() -> None:
    for row_id in ("R0.4", "R2.3"):
        row = _ledger_row(row_id)
        assert "7b26334" in row and "d3f1ecf" in row, row_id
        assert "check_fit.js" in row and "was run" in row, row_id
        # The rebuild and the fit check are recorded as done, never as unverified
        # (the rating's provenance, a different matter, is unverified by design).
        assert not re.search(r"(?:fit check|rebuil\w+)[^.;]{0,60}unverified|unverified[^.;]{0,60}(?:fit check|rebuil\w+)", row), row_id


# D4 — what the gold-set evaluation is scored against


def test_introduction_does_not_call_the_reference_labels_human() -> None:
    intro = _read("thesis/manuscript/01_introduction.md")
    assert "human-labelled feedback" not in intro
    sentence = next(line for line in intro.splitlines() if "RQ3a and RQ3b are answered" in line)
    assert "star rating" in sentence
    assert "language-model assistant" in sentence
    assert "D4" in _ledger_row("D4.1")


# D5 — the held-out split's history


def test_held_out_split_history_matches_git() -> None:
    manuscript_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(MANUSCRIPT.rglob("*.md"))
    )
    assert "defined on 18 July" not in manuscript_text
    # The split's history lives once, in Appendix G.3; the chapters point at it.
    log = _read("thesis/manuscript/appendices/G_provenance_log.md")
    assert "17 July 2026" in log and "18 EN / 6 DE" in log and "23 EN / 7 DE" in log
    for relative in (
        "thesis/manuscript/03_methodology.md",
        "thesis/manuscript/05_evaluation_results.md",
    ):
        text = _read(relative)
        assert "G.3" in text, relative
    assert "23 EN / 7 DE" in _read("thesis/manuscript/05_evaluation_results.md")  # where the numbers are read
    row = _ledger_row("R1.5")
    for commit in ("a1c1b8e", "58504f3", "5d250fb", "bf26f3d"):
        assert commit in row, commit
    history = _git("log", "--format=%h", "--", "apps/api/app/evals/golden_set.json")
    if history:
        commits = history.splitlines()
        assert commits[-1].startswith("a1c1b8e")
        assert any(c.startswith("58504f3") for c in commits)


# D6 — the weighted-kappa interval


def test_weighted_kappa_interval_matches_the_results_file() -> None:
    kappa = json.loads(_read("thesis/evaluation/results/kappa_risk.json"))
    low, high = kappa["kappa_linear_weighted_ci95"]
    expected = f"{low:.2f}–{high:.2f}"
    methodology = _read("thesis/manuscript/03_methodology.md")
    assert expected in methodology
    for relative in (
        *(str(path.relative_to(ROOT)) for path in MANUSCRIPT.rglob("*.md")),
        "thesis/defense/make_deck.js",
        "thesis/board/board_spec.json",
        "thesis/CLAIM_LEDGER.md",
    ):
        text = _read(relative)
        assert "0.56–0.81" not in text and "0.56-0.81" not in text, relative


# D7 — ledger commits are the last commits that touched each artefact


_CANDIDATE_PREFIXES = (
    "",
    "apps/api/app/",
    "apps/api/",
    "apps/api/app/evals/",
    "apps/api/app/services/",
    "apps/api/app/tests/",
    "thesis/evaluation/results/",
    "thesis/evaluation/",
    "thesis/",
)


def _resolve(path: str) -> Path | None:
    for prefix in _CANDIDATE_PREFIXES:
        candidate = ROOT / (prefix + path)
        if candidate.exists():
            return candidate
    return None


def test_ledger_commits_are_the_last_to_touch_each_artefact() -> None:
    head = _git("rev-parse", "HEAD")
    if not head:
        return
    ledger = LEDGER.read_text(encoding="utf-8")
    group = r"((?:`[^`]+`(?:\s*\([^)]*\))?(?:,\s*|\s*\+\s*|\s+and\s+)?)+)\s*@\s*([0-9a-f]{7})\b"
    mismatches: list[str] = []
    checked = 0
    for match in re.finditer(group, ledger):
        items = re.sub(r"\([^)]*\)", "", match.group(1))
        cited = match.group(2)
        for path in re.findall(r"`([^`]+)`", items):
            resolved = _resolve(path)
            if resolved is None or resolved.is_dir():
                continue
            last = _git("log", "-1", "--format=%H", "--", str(resolved.relative_to(ROOT)))
            if last is None:
                continue
            checked += 1
            if not last.startswith(cited):
                mismatches.append(f"{path}: ledger cites {cited}, last touched in {last[:7]}")
    assert checked > 0
    assert not mismatches, "\n".join(mismatches)


def test_ledger_line_references_point_at_the_sentences_they_name() -> None:
    anchors = {
        "R0.1": ("03_methodology.md", "kappa_risk.json"),
        "R1.5": ("03_methodology.md", "held-out split"),
        "R4.1": ("05_evaluation_results.md", "compare_runs_pairs.csv"),
        "C1": ("04_artifact.md", "Human-in-the-loop approval"),
        "C2": ("04_artifact.md", "Failure modes"),
        "C3": ("04_artifact.md", "Outcome contract and closure levels"),
        "D-1": ("04_artifact.md", "approval-interrupt defect"),
    }
    for row_id, (file_name, needle) in anchors.items():
        row = _ledger_row(row_id)
        numbers = re.findall(rf"`{re.escape(file_name)}:([0-9]+(?:, [0-9]+)*)`", row)
        assert numbers, f"{row_id} does not cite {file_name}"
        lines = (MANUSCRIPT / file_name).read_text(encoding="utf-8").splitlines()
        cited = [int(n) for n in numbers[0].split(", ")]
        assert any(needle in lines[n - 1] for n in cited), f"{row_id}: {file_name}:{cited} lacks {needle!r}"


# D8 — governance sentences match the merged code


def test_governance_sentences_match_the_code() -> None:
    scheduler = _read("apps/api/app/services/measurement_scheduler.py")
    origins = re.search(r'PLAN_ORIGINS = frozenset\(\{([^}]*)\}\)', scheduler)
    assert origins is not None
    origin_names = re.findall(r'"([a-z]+)"', origins.group(1))
    assert set(origin_names) == {"approval", "dispatch", "implementation"}
    methodology = _read("thesis/manuscript/03_methodology.md")
    model_line = next(line for line in methodology.splitlines() if line.startswith("**Model.**"))
    for word in origin_names:
        assert word in model_line, word
    assert "failed push" in model_line
    contracts_line = next(line for line in methodology.splitlines() if line.startswith("**Outcome contracts.**"))
    assert "revision" in contracts_line and "in force" in contracts_line
    artifact = _read("thesis/manuscript/04_artifact.md").splitlines()
    hitl = next(line for line in artifact if line.startswith("- **Human-in-the-loop approval.**"))
    assert "approved revision" in hitl and "retry" in hitl
    contract = next(line for line in artifact if line.startswith("- **Outcome contract and closure levels.**"))
    assert "revision" in contract and "dispatch" in contract
    approvals = next(line for line in artifact if line.startswith("- **Attributable, tamper-evident approvals.**"))
    assert "snapshot" in approvals
    failure = next(line for line in artifact if line.startswith("**Failure modes.**"))
    assert "instrumented" in failure and "manual" in failure
    ledger = LEDGER.read_text(encoding="utf-8")
    for row_id, commit in (("C1", "63a4c57"), ("C2", "3c286db"), ("C3", "3c286db"), ("C4", "3c286db")):
        assert commit in _ledger_row(row_id), row_id
    assert "4bd1af8" not in "".join(_ledger_row(r) for r in ("C1", "C2", "C3", "C4", "E1", "E2"))
    assert "being made outside this worktree" not in ledger


# F8 (13 September 2026) — the second risk rating is second-rating agreement, not a human check


_RATING_DOCUMENTS = (
    "thesis/manuscript/00_front_matter.md",
    "thesis/manuscript/02_literature_review.md",
    "thesis/manuscript/03_methodology.md",
    "thesis/manuscript/05_evaluation_results.md",
    "thesis/manuscript/06_discussion.md",
    "thesis/manuscript/appendices/D_traceability_matrix.md",
    "thesis/defense/make_deck.js",
    "thesis/board/board_spec.json",
    "thesis/board/canvas.html",
)
_FORBIDDEN_RATING_PHRASES = (
    "the one human check",
    "the only human check",
    "blind human rating",
    "second person's rating on the owner's attestation",
    "blind second rating",
    "blind second rater",
    "blind double-labelling",
    "Inter-annotator agreement",
    "rests on attestation",
)


def test_second_rating_is_reported_with_unverified_provenance_not_as_a_human_check() -> None:
    for relative in _RATING_DOCUMENTS:
        text = _read(relative)
        for phrase in _FORBIDDEN_RATING_PHRASES:
            assert phrase not in text, f"{relative} still says {phrase!r}"
        if relative != "thesis/manuscript/00_front_matter.md":  # the abstract no longer mentions the rating
            assert "provenance" in text and "unverified" in text, relative
    for relative, needle in (
        ("thesis/manuscript/03_methodology.md", "second-rating agreement with independent human provenance unverified"),
        ("thesis/manuscript/05_evaluation_results.md", "independent human provenance unverified"),
        ("thesis/manuscript/06_discussion.md", "independent human provenance is unverified"),
        ("thesis/manuscript/appendices/D_traceability_matrix.md", "independent human provenance unverified"),
        ("thesis/manuscript/02_literature_review.md", "independent human provenance is unverified"),
        ("thesis/defense/make_deck.js", "independent human provenance is unverified"),
        ("thesis/board/board_spec.json", "independent human provenance unverified"),
    ):
        assert needle in _read(relative), relative
    log = _read("thesis/manuscript/appendices/G_provenance_log.md")
    assert "Fill blind risk labels" in log and "another rater" in log  # observed vs attested, stated once
    assert "G.1" in _read("thesis/manuscript/03_methodology.md")
    provenance = _read("thesis/evaluation/results/PROVENANCE_kappa.md")
    assert "01a077a7-b101-78c0-accc-97f813223a23" in provenance
    assert "kept apart" in provenance
    for row_id in ("R0.1", "R0.2", "R0.3", "R0.4"):
        assert "unverified" in _ledger_row(row_id), row_id
    # The statistic itself is untouched: the files the rows cite are the 6 September ones.
    assert "24d56fc" in _ledger_row("R0.1") and "5ee0c35" in _ledger_row("R0.1")


# F9 — the survey script issues verdicts only from the pre-registered n


def test_survey_tiers_match_the_script() -> None:
    sys.path.insert(0, str(ROOT / "thesis" / "evaluation"))
    import survey_analysis as survey  # noqa: E402

    assert survey.MIN_N == 10 and survey.VERDICT_MIN_N == 40
    assert survey.verdict(0.9, 39, (0.8, 0.95)) == ("DESCRIPTIVE ONLY (n < 40)", False)
    assert survey.verdict(0.9, 40, (0.8, 0.95))[0] == "CONFIRMED"
    chapter = _read("thesis/manuscript/05_evaluation_results.md")
    rule = next(line for line in chapter.splitlines() if "**Survey tiers depend only on the survey n.**" in line)
    assert "n ≥ 40" in rule and "DESCRIPTIVE ONLY (n < 40)" in rule
    assert "writes a support label from n = 10" not in rule
    assert "VERDICT_MIN_N = 40" in _ledger_row("R3.2")


# August-vs-September — a configuration contrast, not "the pipeline only"


def test_generic_versus_production_pair_is_a_configuration_contrast() -> None:
    chapter = _read("thesis/manuscript/05_evaluation_results.md")
    for phrase in (
        "only difference from the \"LLM path\" row is the pipeline",
        "only thing that differs from the generic-prompt row is the pipeline",
        "the *pipeline* effect",
        "the pipeline barely moves",
        "the pipeline effect above holds",
    ):
        assert phrase not in chapter, phrase
    assert "prompt/pipeline × run date" in chapter
    assert "run date" in _ledger_row("R4.5")
    agreement = _read("thesis/evaluation/results/compare_runs_agreement.csv")
    for pair in ("glm_generic_run0_vs_glm_generic_run1", "glm_generic_run0_vs_glm_generic_run2", "glm_generic_run0_vs_glm_generic_run3"):
        assert pair in agreement, pair


# F4 — the grade sentence matches the explicit grade table; the verdict label attributes nothing


def test_evidence_grade_sentence_matches_the_grade_table() -> None:
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    from app.services.outcome_engine import DESIGN_GRADES, REALISABLE_GRADES, evidence_grade  # noqa: E402

    assert REALISABLE_GRADES == frozenset({"C", "D"})
    assert {DESIGN_GRADES[m] for m in ("randomized_holdout", "randomised_holdout")} == {"A"}
    assert evidence_grade(comparison_method="randomized_holdout", measurement_source="instrumented") == "D"
    assert evidence_grade(comparison_method="matched_control", measurement_source="instrumented") == "D"
    assert evidence_grade(comparison_method="uncontrolled_before_after", measurement_source="instrumented") == "D"
    assert evidence_grade(comparison_method="controll", measurement_source="instrumented") == "E"
    assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="instrumented") == "D"
    assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="instrumented", realised_method="its") == "C"
    assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="manual", realised_method="its") == "E"
    methodology = _read("thesis/manuscript/03_methodology.md")
    grading = next(line for line in methodology.splitlines() if line.startswith("**Grading and bounding the measurement itself.**"))
    assert "explicit table" in grading and "not produced by the platform" in grading and "never C" in grading
    failure = next(line for line in _read("thesis/manuscript/04_artifact.md").splitlines() if line.startswith("**Failure modes.**"))
    assert "*no improvement observed*" in failure and "*fix did not land*" not in failure
    assert "fixed observation interval" in failure
    assert "No improvement observed" in _read("apps/web/lib/i18n.tsx")


# F7 — the held-out split is a safety-validation set used in selection; no alpha by replication


def test_held_out_split_is_named_a_safety_validation_set() -> None:
    methodology = _read("thesis/manuscript/03_methodology.md")
    assert "safety-validation set" in methodology and "substitute for alpha control" in methodology
    chapter = _read("thesis/manuscript/05_evaluation_results.md")
    assert "never optimised against" not in chapter
    assert "safety veto" in chapter and "safety-validation set" in chapter
    assert "safety-validation set" in _read("apps/api/app/evals/LOOP_PROMPT.md")
    deck = _read("thesis/defense/make_deck.js")
    assert "do not replace alpha control" in deck and "three consecutive significant runs" not in deck


# F1–F3 — the governance sentences name the outbound binding, frozen terms and fixed intervals


def test_contract_sentences_name_frozen_terms_fixed_intervals_and_the_outbound_binding() -> None:
    methodology = _read("thesis/manuscript/03_methodology.md")
    contracts_line = next(line for line in methodology.splitlines() if line.startswith("**Outcome contracts.**"))
    for needle in ("frozen on the plan", "fixed observation interval", "measurement_replanned", "blocked"):
        assert needle in contracts_line, needle
    artifact = _read("thesis/manuscript/04_artifact.md").splitlines()
    hitl = next(line for line in artifact if line.startswith("- **Human-in-the-loop approval.**"))
    assert "outbound" in hitl and "claimed at the store" in hitl
    contract = next(line for line in artifact if line.startswith("- **Outcome contract and closure levels.**"))
    assert "frozen when they were scheduled" in contract
    assert "def replan_after_amendment" in _read("apps/api/app/services/measurement_scheduler.py")
    assert '"measurement_replanned"' in _read("apps/api/app/routers/problems.py")  # the audit event the sentence names
    for row_id in ("F1", "F2/F3", "F4", "F7", "F8", "F9"):
        _ledger_row(row_id)


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
