# Provenance record: the blind second risk rating (`kappa_sample.csv`, `kappa_risk.json`)

Written 12 September 2026 in response to the external review of that date. This record
states what the committed files are, what the repository history shows, what the owner has
attested, what is not recorded anywhere, and the rule for any further rating. It does not
modify `kappa_sample.csv` or `kappa_risk.json`, and it attributes no intent to anyone.

## 1. What the files are

| File | Content | Produced by |
|---|---|---|
| `kappa_sample.csv` | 40 rows (`public_signal_id`, `text`, `blind_risk`), drawn by `evaluation/kappa_sample.py draw` (seed 20260905, n = 40 from the 106 risk-labelled Trade Republic and Henkel signals); the seed labels are not in the file. All 40 `blind_risk` cells are filled. | Draw: the script. Labels: see §3. |
| `kappa_risk.json` | Cohen's κ between `blind_risk` and `risk_seed`: 0.554 unweighted (percentile-bootstrap 95% interval 0.3755–0.7246), 0.6957 linear-weighted (0.5644–0.8182); exact agreement 27 of 40; escalate-or-not agreement 38 of 40; 38 of 40 within one level; 4x4 confusion table. | `evaluation/kappa_sample.py score results/kappa_sample.csv` |
| `kappa_labelling_instructions.md` | The rubric the labeller works from. It states that it was "written on 6 September 2026, before any label was assigned" and instructs the labeller not to look at any other file and not to discuss the rows with the author until the file is returned. | Committed as described in §2. |

The `risk_seed` column the rating is compared against is the assistant-drafted seed label of
the datasets (manuscript §3.7): a language-model draft used as delivered, not a human label.
The κ therefore measures agreement between the rating in `kappa_sample.csv` and an
AI-generated label; what the rating itself is, is the question of this record.

## 2. Repository timeline (from `git log`; times in UTC)

| Commit | Time (UTC), 2026 | Recorded author field | Files |
|---|---|---|---|
| `33edcb6` | 5 Sep 18:45 | Claude | `kappa_sample.py` (draw/score helper) and the author checklist added. |
| `c2d6f57` | 6 Sep 16:43 | Claude | `kappa_labelling_instructions.md` added; `kappa_sample.py` changed so that a rating file named `kappa_sample_<tag>.csv` writes `kappa_risk_<tag>.json` and "never overwrites the human result in `kappa_risk.json`". |
| `24d56fc` | 6 Sep 17:12 | Elvis Shehi | `kappa_sample.csv` (40 rows, `blind_risk` filled) and `kappa_risk.json` (without bootstrap intervals) committed together. |
| `38dda00` | 6 Sep 17:15 | Claude | `kappa_sample.py` (docstring and scorer), and the κ result written into §3.7, §5A.4.2, §6.4 and Appendix D; the checklist notes "Open: who the rater was (person or model) decides the 'human check' wording". |
| `5ee0c35` | 6 Sep 17:19 | Elvis Shehi | `kappa_risk.json` re-written with the percentile-bootstrap intervals. |

The recorded author field is the git metadata as committed; it identifies the committing
identity, not who assigned the labels. Twenty-nine minutes separate the rubric commit from
the filled-sample commit. The rubric estimates 30 to 45 minutes for the task. Nothing in
the repository records when the file was handed over or returned.

`kappa_sample.py:7` permits the labelling to be done by "a second person (or the author after
a wash-out interval)", and since `c2d6f57` routes a model rating (for example
`kappa_sample_llm.csv`) to `kappa_risk_llm.json`, to be reported as cross-model agreement.
The committed result is in `kappa_risk.json`, the path reserved for the human result.

## 3. The owner's attestation

Asked on 12 September 2026 who produced the labels in `kappa_sample.csv`, the repository
owner answered: "another rater". This is read as: a second person, not the author, produced
the labels, which is consistent with §3.7 of the manuscript ("The rater was a second person,
not the author, working from the written rubric with the seed labels withheld") and with the
checklist entry of 6 September ("Step 5's rater was a second person"). The manuscript's
second-person statement rests on this attestation.

## 4. What is not recorded

None of the committed artefacts records:

- the rater's identity or role (the manuscript and this record deliberately do not name a
  person; what is missing is any record that a named or pseudonymous rater existed, such as
  a signed hand-over note);
- the time the file was handed to the rater or returned;
- whether the rater had access to any AI-generated suggestion for these rows (for example a
  model's rating of the same 40 texts) while labelling, or was told not to use one; the rubric
  forbids looking at other files but does not mention AI assistance;
- whether the rater is the same person who ran the AI-assisted session that the external
  review describes (§5);
- the environment in which the labels were entered (a spreadsheet, an editor, a chat session).

Because AI exposure was not recorded, the manuscript treated the rating, between 12 and 13
September 2026, as a blind human rating on the owner's attestation; since the follow-up
review's observation (§5) it is described as second-rating agreement with independent
human provenance unverified, and no document calls it a human check.

## 5. The external reviews' observation (12 and 13 September 2026; unresolved)

The external review of 12 September 2026 stated that the committed labels are identical to a
label set produced in an AI-assisted session titled "Fill blind risk labels". The follow-up
review of 13 September 2026 names the record: an assistant task with that title, id
`01a077a7-b101-78c0-accc-97f813223a23`, whose 40 rows match `kappa_sample.csv` row for row.
The repository can neither confirm nor refute it: no such task record, transcript or label
set is committed, and the repository holds only the one filled sample.

Observed evidence and attestation, kept apart:

| | Source | What it says |
|---|---|---|
| Observed (repository) | `git log`, §2 | The filled sample and its κ file were committed together 29 minutes after the rubric, under the author's git identity; nothing committed identifies a rater, a hand-over or a return time. |
| Observed (reported by the reviewer) | the 13 September review | An AI-assistant task record titled "Fill blind risk labels" (id above) whose 40 labels are identical to the committed file. Reported, not committed; unverifiable here. |
| Attested | the owner, 12 September 2026 | "another rater": a second person, not the author, produced the labels. |

The two are not reconciled. Until they are, every document in this repository describes the
rating as **second-rating agreement with independent human provenance unverified**: the
statistic stands (it is reproducible from the files, which are unchanged), it says how a
second reading of the rubric orders these 40 texts, and it is not called a human check, a
blind human rating or an inter-annotator agreement anywhere (manuscript abstract, §2.13,
§3.5.4, §3.7, §5A.4.2, §6.4 item 1 and Appendix D; `CLAIM_LEDGER.md` R0.1–R0.4; the defence
deck; the board). Two readings remain compatible with everything the repository shows: a
person produced the labels and a model, asked separately, produced the same 40; or the
labels in the file are the model's. This record does not choose.

What would resolve it: (a) the owner supplies the rater's role, the hand-over and return
dates and a statement of AI access, as §6.3 requires for any new rating, after which the
manuscript may call the rating a human check on the owner's record; or (b) the owner
confirms that the task record produced the file, in which case the statistic is retained
as cross-model agreement and the prepared wording in
`thesis/review-2026-09-12-response-notes.md` is applied. Neither had happened at the time
of writing (13 September 2026).

## 6. Rule for any further rating

Any new human rating of the risk seeds, or of any other gold field, is collected and stored
separately from the files above:

1. a new draw or a new sample file (`kappa_sample_<tag>.csv`), never an edit of
   `kappa_sample.csv`;
2. a new commit for the filled file and its `kappa_risk_<tag>.json`, never an amendment of
   `24d56fc` or `5ee0c35`;
3. the rater's role (not necessarily name), the date handed over and the date returned, and a
   statement of whether any AI-generated suggestion was available to the rater, recorded in a
   provenance note committed with the file;
4. a rating produced by a model is named as such in the file tag and reported as cross-model
   agreement, never as a human check.

A repeat rating of the same 40 items by the same or another rater bounds rater noise; it is
not replication over new items, and a replication claim needs a new draw.
