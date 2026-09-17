# Review of 12 September 2026: prepared alternative wording for the blind risk rating (NOT applied)

Purpose. The manuscript treats the 40-item blind second risk rating (`evaluation/results/
kappa_sample.csv`, `kappa_risk.json`) as a blind human rating on the owner's attestation
("another rater", 12 September 2026; `evaluation/results/PROVENANCE_kappa.md`). If the
owner later confirms that the labels in `kappa_sample.csv` were produced by an AI model
rather than a person, the wording below is applied verbatim, without re-analysis: the
statistic (κ = 0.55 unweighted, 0.38–0.72; 0.70 linear-weighted, 0.56–0.82; 27/40 exact;
38/40 escalate-or-not; 38/40 within one level; seven of ten seed-critical items at high)
is unchanged and is retained as **cross-model agreement**, and every "human check" phrase is
replaced. Nothing in this file is applied now; it exists so that the change is mechanical.

**13 September 2026, superseded in part.** The follow-up review of that date names the AI-assistant
task record ("Fill blind risk labels", id `01a077a7-b101-78c0-accc-97f813223a23`, all 40 rows
identical to the committed file). Without waiting for the owner's confirmation, the manuscript,
ledger, deck and board now describe the rating as *second-rating agreement with independent
human provenance unverified* (`PROVENANCE_kappa.md` §5), so the "human check" search strings
quoted below no longer occur. The cross-model wording below still states what changes if the
owner confirms that a model produced the labels; its search strings would need re-anchoring to
the 13 September sentences before it is applied.

Preconditions if applied:

1. A new commit records the confirmation (date, wording as given) in `PROVENANCE_kappa.md`
   §3, and the model's name and the session in which the labels were produced, if known,
   in §4. `kappa_sample.csv` and `kappa_risk.json` are not edited; a copy of the rating may
   be committed as `kappa_sample_llm.csv` / `kappa_risk_llm.json` so that the scorer's
   naming convention (`kappa_sample.py:93–97`) matches what the file is.
2. Every replacement below is applied in the same commit, and `CLAIM_LEDGER.md` rows
   R0.1–R0.4 are re-statused: evidence type "AI-generated labels vs AI-generated labels
   (cross-model agreement)"; status "narrowed; no human check on the risk labels".

Search strings are exact; each occurs once in the file named.

---

## 03_methodology.md

**§3.5.4, line 71.** Replace

> for the risk field the blind double-labelling of §3.7 is the only human check on them, a second person's rating on the owner's attestation, whose provenance record (`evaluation/results/PROVENANCE_kappa.md`) does not capture whether the rater saw any AI-generated suggestion.

with

> for the risk field no human check on them exists: the blind second rating of §3.7 was produced by a language model and is reported as cross-model agreement (`evaluation/results/PROVENANCE_kappa.md`).

**§3.7, line 126.** Replace

> and the blind double-labelling of a 40-signal risk sample (drawn on 6 September 2026 with the seed labels withheld; `evaluation/kappa_sample.py`) is the one human check on them. Returned the same day, it gives Cohen's κ = 0.55 unweighted

with

> and no human check on them exists. A blind second rating of a 40-signal risk sample (drawn on 6 September 2026 with the seed labels withheld; `evaluation/kappa_sample.py`) was produced by a language model working from the written rubric, so it is a cross-model agreement statistic, not a human check. Returned the same day, it gives Cohen's κ = 0.55 unweighted

and replace

> That is moderate agreement on the exact level and substantial agreement on the ordering, and the disagreement has a shape: the rater placed

with

> That is moderate agreement on the exact level and substantial agreement on the ordering between two language models' readings of the same texts, and the disagreement has a shape: the second model placed

and replace

> The seed labels' ordering holds up; their calibration of the top and bottom thresholds does not, which is the direction of the production stage's shift in §5A.4.2 and bounds how much of that shift can be charged to the artifact. The rater was a second person, not the author, working from the written rubric with the seed labels withheld. The rating's provenance record is `evaluation/results/PROVENANCE_kappa.md`: the second-person statement is the owner's attestation of 12 September 2026, the committed files record neither the rater's identity nor the return time, and whether the rater had access to any AI-generated suggestion for these rows was not recorded, so the rating is treated as a blind human rating on the owner's attestation and no more.

with

> The seed labels' ordering is shared by a second model; their calibration of the top and bottom thresholds is not, which is the direction of the production stage's shift in §5A.4.2. Because both readings are model readings, this bounds nothing about the labels' validity against a human judgement, and the same-family bias of §3.5.4 applies to the agreement statistic as much as to the labels. The rating's provenance record is `evaluation/results/PROVENANCE_kappa.md`; the model that produced it and the date are recorded there.

## 05_evaluation_results.md

**§5A.4.2, line 100.** Replace

> The blind second rating of the risk seeds (§3.7; a second person's rating on the owner's attestation, with exposure to AI-generated suggestions unrecorded, `evaluation/results/PROVENANCE_kappa.md`) points the same way: on a 40-item sample the rater placed seven of the ten seed-*critical* items at *high*, so part of the shift is the seed labels' own calibration of the top level rather than the artifact's.

with

> The blind second model rating of the risk seeds (§3.7; cross-model agreement, `evaluation/results/PROVENANCE_kappa.md`) points the same way: on a 40-item sample the second model placed seven of the ten seed-*critical* items at *high*, so the calibration of the top level differs between models as well as between the seed labels and the artifact; whether a human would side with either is unmeasured.

## 06_discussion.md

**§6.4 item 1, line 49.** Replace

> and a blind second rating of a 40-item risk sample agrees with them at κ = 0.55 unweighted and 0.70 linear-weighted, the disagreement concentrated at the critical/high boundary; that rating is a second person's on the owner's attestation, with the rater's exposure to AI-generated suggestions unrecorded, `evaluation/results/PROVENANCE_kappa.md`);

with

> and a blind second rating of a 40-item risk sample by a second language model agrees with them at κ = 0.55 unweighted and 0.70 linear-weighted, the disagreement concentrated at the critical/high boundary; no human rating of the risk labels exists, `evaluation/results/PROVENANCE_kappa.md`);

## appendices/D_traceability_matrix.md

**Reading paragraph, line 33.** Replace

> and the blind second rating of §3.7 is the one human check on the risk labels (κ = 0.55 unweighted, 0.70 linear-weighted, n = 40; 38 of 40 within one level; seven of ten seed-critical items rated high; a second person's rating on the owner's attestation, with exposure to AI-generated suggestions unrecorded, `evaluation/results/PROVENANCE_kappa.md`).

with

> and no human check on the risk labels exists; the blind second rating of §3.7 is cross-model agreement (κ = 0.55 unweighted, 0.70 linear-weighted, n = 40; 38 of 40 within one level; seven of ten seed-critical items rated high; produced by a language model, `evaluation/results/PROVENANCE_kappa.md`).

## 02_literature_review.md

**§2.13, line 335.** Replace

> a same-family bias that the human-origin star rating and the blind second rating (κ = 0.55; a second person's rating on the owner's attestation, §3.7) bound but do not remove.

with

> a same-family bias that the human-origin star rating bounds for sentiment and that nothing bounds for risk, journey stage and owner: the blind second rating of the risk seeds (κ = 0.55, §3.7) is a second language model's reading and shares the bias rather than bounding it.

## 00_front_matter.md

**Abstract, line 20.** Replace

> a calibration difference that a blind second rating partly shares,

with

> a calibration difference that a second language model's blind rating partly shares,

## defense/make_deck.js

**Slide 9, line 206.** Replace

> a blind second rater put seven of ten seed-critical items at high (kappa 0.55, weighted 0.70).

with

> a second language model, rating blind, put seven of ten seed-critical items at high (kappa 0.55, weighted 0.70); no human rating exists.

**Slide 8 notes, line 191.** Replace

> the one agreement number is the 40-item blind second risk rating (kappa 0.55 unweighted, 0.70 weighted), attested as a second person's, with its provenance recorded in PROVENANCE_kappa.md and the rater's exposure to AI suggestions unrecorded; there is none behind the in-repo golden set, and that remains the most attackable gap.

with

> the one agreement number, kappa 0.55 on the 40-item blind risk rating, is cross-model agreement (a second language model rated the sample, PROVENANCE_kappa.md); there is no human agreement number behind either gold standard, and that is the most attackable gap in the thesis.

**Slide 15 table, line 297.** Replace

> ["Inter-annotator agreement", "Measured once, on attestation", "40-item blind risk rating: kappa 0.55 unweighted, 0.70 weighted; a second person on the owner's attestation, AI exposure unrecorded; none on the golden set"],

with

> ["Inter-annotator agreement", "Pending (cross-model only)", "40-item blind risk rating by a second language model: kappa 0.55 unweighted, 0.70 weighted; no human rating on either gold standard"],

**Slide 16 limitations, line 314.** Replace

> "One agreement number exists: kappa 0.55 on a 40-item blind risk rating, a second person's on the owner's attestation, with the rater's exposure to AI suggestions unrecorded. None exists behind the golden set.",

with

> "No human inter-annotator agreement number exists behind either gold standard; the one kappa (0.55, 40 risk items) is between two language models.",

**Slide 16 next, line 323, and slide 17 ask 3, line 336.** Replace the parenthetical

> the existing kappa rests on attestation

with

> the existing kappa is cross-model

in both places (the string occurs twice by design), and on line 323 replace

> with rater and date recorded: the existing kappa rests on attestation, and repeats on the same forty items would not be replication.

with

> with rater and date recorded: the existing kappa is between two language models, and a human rating does not yet exist.

## board/board_spec.json (then `python3 thesis/board/build_canvas.py`)

**Card `ladder`, field `lede`.** Replace

> DP1 demonstrated. Hardening partly measured. One kappa, on attestation. Zero interviews.

with

> DP1 demonstrated. Hardening partly measured. No human kappa. Zero interviews.

**Card `ladder`, field `note`.** Replace

> Kappa 0.55 on 40 blind risk items; a second person on the owner's attestation, AI exposure unrecorded. The RQ4 row is what the asks are about

with

> Kappa 0.55 on 40 blind risk items is between two language models. The RQ4 and agreement rows are what the asks are about

## evaluation/results/PROVENANCE_kappa.md

Append to §3: the date and wording of the confirmation. Replace the last sentence of §4
("Because AI exposure was not recorded … carries that qualifier") with: "The labels were
produced by a language model (confirmed <date>); the manuscript reports the statistic as
cross-model agreement and states that no human check on the risk labels exists." Mark §5
resolved with the same date.

## What does not change

The statistic, its intervals, the confusion table, the 38-of-40 escalate agreement, the
seven-of-ten observation, and the sentence in §5A.4.2 that part of the production stage's
shift is the seed labels' own calibration (it becomes "the calibration of the top level
differs between models"). The star rating remains the only human-origin reference in §5A,
which is already what §3.7, §5A.6, §5A.7 and Appendix D say.
