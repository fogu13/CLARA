# Blind risk labelling: instructions for the second labeller

Written on 6 September 2026, before any label was assigned, so that the rubric is on
record ahead of the agreement statistic (Cohen's κ, `kappa_sample.py score`).

**Task.** `kappa_sample.csv` holds 40 short customer-feedback texts (paraphrased public
reviews about a brokerage app and about adhesive products). Fill the empty `blind_risk`
column for every row with exactly one of: `low`, `medium`, `high`, `critical`. Do not look
at any other file, and do not discuss the rows with the author until the file is returned.
Expect 30 to 45 minutes.

**What "risk" means here.** What is at stake for the customer or the company if nothing
is done about this signal. Judge from the text alone. It is not about how many customers
might be affected, and not about how quickly someone must respond.

| Level | Assign when the text describes... | Examples of cues |
|---|---|---|
| `critical` | money or account access lost or blocked; fraud; a data or privacy breach; a safety, legal or regulatory exposure; an unrecoverable loss; or the customer stating they are leaving | "cannot withdraw", "account blocked", "charged twice and no refund", "reported to the regulator", "cancelling my account" |
| `high` | a core function failed or the customer suffered real, recoverable detriment that needs someone to intervene; a strong signal the customer will leave if it is not fixed | "order never arrived", "transfer delayed for weeks", "support never answered", "product failed and damaged the surface" |
| `medium` | friction, a degraded or confusing experience, unclear communication, or a complaint with limited harm; something to fix, but nobody is materially worse off yet | "app is slow", "instructions unclear", "hard to find the export", "smell is strong" |
| `low` | praise, a neutral observation, a minor cosmetic issue, or a feature request with no harm described | "works well", "would like dark mode", "good value" |

**Tie-break rules.** Use the most severe level the text supports. If torn between two
levels, choose the lower one, unless money, account access, safety or legal exposure is
involved, in which case choose the higher. Mixed praise-and-complaint texts are labelled
for the complaint.

**Return.** The same CSV with `blind_risk` filled on all 40 rows and nothing else changed.
