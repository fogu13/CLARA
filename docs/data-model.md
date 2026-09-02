# Data Model

## Core Entities

### Signal

A normalized customer signal from support, survey, research, product behavior, review, sales, or marketing systems.

Key fields:

- `signal_id`
- `source`
- `customer_id`
- `account_id`
- `journey`
- `journey_stage`
- `feedback_text`
- `language`
- `timestamp`
- `campaign_exposure`
- `product_events`

Signals can be imported as JSON, pasted CSV or uploaded CSV files. Uploaded CSVs can be mapped to the canonical fields in the UI. CSV imports require the same logical fields after mapping and support `;` or `|` delimiters for multi-value campaign and product-event columns.

CSV validation reports:

- total rows;
- importable rows;
- missing required values;
- duplicate signal IDs in the file;
- already-imported signal IDs that will be skipped;
- sparse behavioural or campaign context warnings.

### Demo Dataset

A packaged walkthrough scenario containing signals plus customer/account context.

Key fields:

- `dataset_id`
- `title`
- `description`
- `industry`
- `signals`
- `customer_context`

Demo datasets live under `data/demo_datasets/`. Importing one dataset adds its signals through the normal signal store and upserts its customer context rows through the context store.

### Customer Context

A lightweight customer/account context row attached by `customer_id` and `account_id`. This is intentionally smaller than a CRM replica; it carries only the fields needed to explain priority, route ownership and support governance.

Key fields:

- `customer_id`
- `account_id`
- `account_name`
- `parent_account_id`
- `parent_account_name`
- `segment`
- `lifecycle_stage`
- `plan_tier`
- `contact_role`
- `account_value`
- `renewal_date`
- `consent_status`
- `health_score`
- `owner`
- `product_owner`
- `region`

Customer context can be imported as JSON or pasted CSV. CSV validation reports missing required values, duplicate customer IDs in the file, numeric account-value and health-score errors, and existing customer IDs that will be updated.

### Customer Context Completeness Report

A source-readiness report for the imported context graph.

Key fields:

- `total_records`
- `total_accounts`
- `complete_records`
- `readiness_score`
- `readiness_level`
- `metrics`
- `warnings`

`metrics` provide field-level coverage for account value, consent status, health score, owner, product owner, contact role, lifecycle stage and other recommended context fields. `readiness_level` is `ready`, `usable` or `needs_attention`. Any warning prevents a `ready` classification even when the weighted score is high, because consent, owner, product-owner and account-value gaps can materially affect prioritization, routing or governance.

### Context Impact Summary

A read-side explanation attached to problem summaries and problem detail responses when evidence-linked customer or account IDs match imported context rows.

Key fields:

- `matched_customers`
- `matched_accounts`
- `high_value_accounts`
- `total_account_value`
- `average_health_score`
- `consent_risk_customers`
- `renewal_risk_accounts`
- `priority_lifecycle_accounts`
- `at_risk_lifecycle_accounts`
- `owners`
- `product_owners`
- `regions`
- `score_delta`
- `drivers`

The context impact summary is calculated from customer context rows whose `customer_id` appears in problem evidence or whose `account_id` belongs to an evidence-linked account. It can raise the problem's customer reach, account exposure, financial exposure, regulatory risk and low-health severity factors before the Action Queue sorts by priority. The stored draft problem is not mutated by this read-side enrichment.

### Affected Context Explorer

A per-problem read model used by the Action Queue to inspect the actual affected customers and accounts behind the context impact score.

Key fields:

- `problem_id`
- `context_impact`
- `accounts`
- `customers`
- `missing_customer_ids`
- `missing_account_ids`
- `warnings`
- `routing_recommendations`

`accounts` roll up matched customer context by `account_id`, including parent account, customer count, account value, high-value flag, consent-risk count, average health, contact roles, lifecycle stages, plan tiers, renewal dates, owners, product owners and regions. `routing_recommendations` group matched context by owner and explain priority drivers such as high-value exposure, consent risk, high-influence contacts, low account health and parent-account relationships. `warnings` report missing context for evidence customer/account IDs, consent gaps, missing health scores, missing account values, missing contact roles and missing product owners.

### Problem

A recurring customer problem supported by evidence.

Key fields:

- `problem_id`
- `title`
- `statement`
- `journey`
- `journey_stage`
- `impact_score`
- `impact_band`
- `evidence_confidence`
- `evidence`
- `affected_cohort`
- `context_impact`
- `root_cause_hypothesis`
- `known_limitations`

Problem evidence carries the source signal ID, source system, language, excerpt, customer ID, account ID and timestamp. The Action Queue renders these as reviewable evidence rows rather than a single quote.

Timeline and origin fields:

- `due_at` — resolution due date, set at promotion from `WorkspaceSettings.resolution_sla_days`; `ProblemSummary.overdue` is derived at read time (never for resolved problems, never for seed problems without a due date).
- `origin` — `journey_stage` (deterministic grouping) or `ai_theme` (accepted from an LLM triage theme).
- `theme_tag` — the canonical theme tag for `ai_theme` problems; their outcome contract metric is `signal_rate_per_day:theme/<tag>` and matches signals carrying the tag, whatever journey they came from.

### Problem Candidate

A deterministic pre-problem generated from imported signals before a human accepts it into the Action Queue.

Key fields:

- `candidate_id`
- `journey`
- `journey_stage`
- `signal_count`
- `customer_count`
- `account_count`
- `sources`
- `languages`
- `confidence`
- `evidence`
- `root_cause_hypothesis`
- `suggested_owner`
- `suggested_action`
- `review_status`
- `duplicate_problem_id`
- `duplicate_reason`
- `reviewer`
- `review_note`
- `reviewed_at`

Candidates have an `origin`: `journey_stage` (grouped by the imported journey/stage columns) or `ai_theme` (a theme `POST /triage/run` sorted signals into; persisted per workspace and tag, latest run wins). AI-theme candidates carry `theme_tag`, `theme_summary`, `triage_impact_score` (deterministic cross-signal severity), `triage_urgency` and `triage_run_id`; their evidence and counts are recomputed from the signals that still exist.

Candidate review statuses are `pending`, `duplicate`, `accepted`, and `rejected`. Duplicate detection compares candidate journey and journey stage against existing Action Queue problems. Accepting a non-duplicate candidate creates a durable `validation_required` draft `Problem` with evidence, initial action proposals, governance checks and an outcome contract. Rejected decisions are persisted so the candidate review list survives local restarts. In the prototype, promoted drafts are persisted in SQLite while seed problems still load from JSON.

Promoted draft problems can be edited before approval. Editable fields currently include:

- title;
- statement;
- owner;
- root-cause hypothesis.

Problem status changes are lifecycle transitions, not content edits. A transition records the source status, target status, actor, optional note and timestamp. Workflow state returns a merged timeline built from lifecycle transitions, approvals, execution drafts, outcome measurements and learning conclusions. Seed problems are read-only.

### Action Proposal

A recommended action linked to one problem.

Action classes:

- `structural`
- `customer_recovery`
- `journey_intervention`
- `research`
- `governance`

Key fields:

- `action_id`
- `class`
- `owner`
- `destination`
- `proposal`
- `risk_level`
- `approval_state`

For promoted draft problems, these action fields can be refined before approval. Seed problem action proposals stay read-only demo data.

### Governance Check

A machine-readable check used before action execution.

Key fields:

- `check_id`
- `rule`
- `policy_rule_id`
- `status`
- `reason`
- `blocking`

### Policy Rule

A reusable governance rule that a problem-level check can reference. The prototype seeds these from `data/sample_policy_rules.json`.

Key fields:

- `rule_id`
- `title`
- `description`
- `category`
- `severity`
- `applies_to_action_classes`
- `applies_to_destinations`
- `required_evidence`
- `default_blocking`
- `owner`
- `version`
- `status`

### Outcome Contract

The measurement promise attached to an approved action.

Key fields:

- `primary_metric`
- `baseline`
- `success_threshold`
- `measurement_window_days`
- `comparison_method`
- `guardrail_metrics`
- `responsible_owner`

Outcome read models expose an inferred `improvement_direction` for the current prototype. A target above or equal to the baseline means higher values are better; a target below the baseline means lower values are better.

### Jira Issue Draft

A local execution artifact created when a Jira-targeted action is approved. It is a reviewable draft, not a live Jira issue.

Key fields:

- `draft_id`
- `problem_id`
- `action_id`
- `execution_id`
- `project_key`
- `issue_type`
- `summary`
- `description`
- `labels`
- `assignee`
- `status`
- `created_at`

### Outcome Measurement

The observed metric value recorded after an intervention.

Key fields:

- `problem_id`
- `metric`
- `observed_value`
- `measured_at`
- `notes`

The outcome snapshot compares the latest measurement with the contract direction and returns `not_measured`, `not_improved`, `improving`, or `target_met`.

### Learning Conclusion

A human-reviewed conclusion about what the measured outcome taught the team. It can only be recorded after an outcome exists.

Key fields:

- `conclusion_id`
- `problem_id`
- `tenant_id`
- `learning_status`
- `reviewer`
- `reviewed_at`
- `retention_expires_at`
- `summary`
- `limitations`
- `next_step`

Learning statuses are `worked`, `partially_worked`, `did_not_work`, `inconclusive` and `measurement_invalid`. Free-text fields are reviewer-authored, not AI-generated; common email, phone, IP, address and customer/account ID patterns are redacted. `reviewer` and `tenant_id` come from trusted workflow headers and must be pseudonymized identifiers. `retention_expires_at` is currently set to 730 days after review.

### Outcome Board

A queue-level read model that combines each problem's identity, impact score, lifecycle status and latest outcome snapshot.

Key fields:

- `total`
- `not_measured`
- `not_improved`
- `improving`
- `target_met`
- `learning_worked`
- `learning_partially_worked`
- `learning_did_not_work`
- `learning_inconclusive`
- `learning_measurement_invalid`
- `items`

Each item carries the problem ID, title, owner, impact score, impact band, primary metric, baseline, target, latest value, outcome status, latest learning status, measurement window and responsible outcome owner.


### Owner Route

A workspace team-routing rule (`WorkspaceSettings.owner_routes`, first match wins):

- `match` — case-insensitive substring compared against the journey stage and the AI theme tag
- `owner` — the owning team identifier
- `destination` — default destination for the team's structural action (optional)
- `jira_project_key`, `slack_channel` — per-team overrides layered over the workspace connector config at push time; credentials are never overridable

### Loop Verdict

Derived at read time on `OutcomeSnapshot` and `OutcomeBoardItem` from the contract status and the scheduled checkpoints (T+7, window, follow-up = window + 30 days):

- `not_measured`, `measuring`, `manual_required`
- `on_track` — an early or manual read met the target; not proof yet
- `loop_closed` — the window or follow-up checkpoint met the target on real post-fix inflow
- `fix_did_not_land` — the closing checkpoint showed no improvement

### Learning Memory Item

`GET /learnings` returns the retrievable learnings synthesis reads (`rank_learnings`): `topic`, `pattern`, `learning_status`, `summary`, `limitations`, `resolution_actions` (the approved actions' text), `base_confidence`, `decayed_confidence`, `freshness` (`VALIDATED` / `EMERGING` / `STALE`) and `retrieval_eligible` (false for auto-derived `reviewer=system` learnings, which are shown but never steer the model).
