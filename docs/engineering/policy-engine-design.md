# Policy Evaluation Engine — design and parity notes

Status: implemented (thin slice of roadmap Phase 6).
Code: `apps/api/app/services/policy_engine.py`.
Tests: `apps/api/app/tests/test_policy_engine.py`, `test_policy_decision_audit.py`,
`test_policy_evaluate_api.py`, plus unchanged regression coverage in
`test_workflow_api.py` and `test_triage_graph.py`.

## Why

Before this change CLARA had three disconnected pieces of governance logic:

1. `assert_governance_allows_decision` in `services/workflow.py` — the real
   approval gate, driven by a hardcoded destination→required-rules map
   (`GOVERNANCE_RULES_BY_DESTINATION`) that carried its own note admitting it
   should be data.
2. `governance_node` in `agents/triage_graph.py` — an acknowledged stub that
   hardcoded a single category check and never read `PolicyRuleStore`.
3. `PolicyRuleStore` + `data/sample_policy_rules.json` — rules that were
   displayed and referenced by checks, but never themselves evaluated.

The thesis names the gap (§6.4: "an advisory compliance checker, not a formal
policy engine… policy-as-code… is design-forward, not yet built") and Phase 6
of the roadmap scopes the module. This slice makes one evaluator answer "may
this consequential call proceed?" for every enforcement point, without
changing any enforcement outcome.

## Shape

- `GovernedCall` — a normalized envelope describing one proposed consequential
  call: source (workflow approval, triage graph, api, mcp, external agent),
  actor type (human/system/agent), action class, destination, risk level,
  data categories, existing governance checks, and an audit reference (entity
  ids only, never personal data).
- `PolicyEngine.evaluate(call) -> PolicyDecision` — allow / needs_review /
  block, with the applicable rule ids, per-rule findings and reasons.
- `before_call` / `after_call` — the per-call interface for any surface that
  executes calls: `before_call` gates (block means do not execute);
  `after_call` only annotates — it never blocks retroactively, because the
  call already happened. Any future agentic surface adopts these two hooks
  without redesign; the deliberate design constraint is that CLARA itself has
  no runtime model-chosen tool calls (thesis DP5 — the model is a component to
  be contained), so today's callers are the two deterministic gates plus the
  evaluate endpoint.
- Rules stay `PolicyRule` rows (now with `applies_to_categories`); the
  destination map is seed data (`data/sample_destination_policies.json`)
  validated against the rules at load time.

## Three matching paths

1. **Destination path** — the destination selects required rule ids from the
   destination-policies seed; for governed action classes
   (customer_recovery, journey_intervention, governance) with an unmapped
   destination, the union of all mapped rules applies. A required rule whose
   governance check is missing, failed, or review_required is a blocking
   finding. This reproduces the historical approval gate exactly.
2. **Check path** — when the destination path does not apply, existing
   governance checks are read directly: a blocking failed check blocks; other
   non-pass checks are advisory (needs_review). Historically only blocking
   failures stopped an approval; that is preserved.
3. **Category path** — rules whose `applies_to_categories` overlap the call's
   `data_categories` fire on their own: blocking rules produce failures,
   advisory rules request review. This is what makes the triage governance
   gate rule-driven — `compliance_concern_requires_review` in the seed
   reproduces the old hardcoded stub behaviour as governed data.

## Parity guarantees

- The approval 409 (`"Action cannot be approved while blocking governance
  checks are failing"`) fires for exactly the same scenarios as before; the
  detail string is byte-identical. `test_workflow_api.py` passes unmodified.
- The triage gate's output contract (`governance_checks` dicts,
  `governance_passed`, `status`, `approval_decision`, errors) is unchanged;
  `TestTriageGraphGovernance` passes unmodified.
- Checks are keyed `policy_rule_id or rule`, preserving legacy checks without
  a `policy_rule_id`.
- Workflow envelopes carry no `data_categories`, so the category path is a
  no-op on the approval gate.

## Known divergence, deliberately preserved

The seed destination map is verbatim the previously hardcoded constant, and it
disagrees with the rules' own `applies_to_destinations` metadata:

| Divergence | Effect of "fixing" it |
| --- | --- |
| Map requires `sensitive_attribute_inference_prohibited` for `salesforce` and `adobe_experience_platform`; the rule's metadata lists neither | Deriving from metadata would weaken gating on those destinations |
| `policy_review` is a map key no rule claims as a destination | Deriving would stop blocking the seeded PRB-109 scenario |
| `jira` / `research_panel` appear in rule metadata but not in the map | Deriving would start gating jira approvals that are ungated today |

Reconciling map and metadata changes enforcement behaviour and is a separate,
deliberate decision — not part of this slice.

## Decision audit

Every gated consequential path appends a `policy_decision` telemetry event
(append-only, never raises, EU-resident by design): the approval gate on
allow and block, the triage run once per evaluated batch, and each
`/policy/evaluate` call. Metadata is structured only — source, decision,
applicable/blocking rule ids, entity reference, actor type. No free text, no
personal data.

## The evaluate endpoint

`POST /policy/evaluate` (editor-gated, rate-limited) evaluates a caller-
supplied envelope against workspace-global rules and returns the decision. It
is side-effect-free apart from the audit event: it reads no signals, problems
or customer data, and it cannot execute or approve anything. It exists so any
external surface preparing a consequential call — an integration, an MCP
consumer, a demonstration agent — can consult the same evaluator the product
enforces with, per call, before acting. The MCP tool surface is unchanged
(still read-only, still pinned by test).

## Deferred (post-funding Phase 6)

- Map/metadata reconciliation (above).
- Rule authoring/versioning UI and staged rollout; rule simulation and
  conflict detection.
- A dedicated persisted decisions table (migration 013+) if evidence packs
  need to embed decisions; telemetry carries them today.
- Evidence-confidence thresholds, consent lookups, PII detection and
  risk-tier matrices as first-class rule predicates.
- Runtime-configurable policy rules (the store is seed-backed and read-only
  in product today; the engine takes whatever rules it is given).
