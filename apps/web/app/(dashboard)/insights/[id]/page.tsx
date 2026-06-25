import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActionDecisionPanel } from "@/app/components/action-decision-panel";
import { ActionProposalEditor } from "@/app/components/action-proposal-editor";
import { AffectedContextPanel } from "@/app/components/affected-context-panel";
import { CustomerClosurePanel } from "@/app/components/customer-closure-panel";
import { DraftProblemEditor } from "@/app/components/draft-problem-editor";
import { EvidencePanel } from "@/app/components/evidence-panel";
import { OutcomeMeasurementPanel } from "@/app/components/outcome-measurement-panel";
import { ProblemLifecyclePanel } from "@/app/components/problem-lifecycle-panel";
import { getActionQueueProblems, getPolicyRules } from "@/lib/api";
import type {
  ActionClass,
  ActionProposal,
  AudienceReadiness,
  GovernanceCheck,
  InterventionBrief,
  PolicyRule,
  ProblemRecord
} from "@/lib/types";

function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function label(value: string): string {
  return value.replaceAll("_", " ");
}

type PortfolioArea = {
  actionClass: ActionClass;
  title: string;
  intent: string;
};

const portfolioAreas: PortfolioArea[] = [
  {
    actionClass: "structural",
    title: "Product Fix",
    intent: "Structural work that removes the root cause."
  },
  {
    actionClass: "customer_recovery",
    title: "Customer Recovery",
    intent: "Immediate recovery for affected customers."
  },
  {
    actionClass: "journey_intervention",
    title: "Journey Intervention",
    intent: "Governed audience or lifecycle intervention draft."
  },
  {
    actionClass: "research",
    title: "Research",
    intent: "Validation work for uncertain causes or solutions."
  },
  {
    actionClass: "governance",
    title: "Governance",
    intent: "Policy, evidence and approval readiness work."
  }
];

function matchingRules(action: ActionProposal, rules: PolicyRule[]): PolicyRule[] {
  return rules.filter(
    (rule) =>
      rule.applies_to_action_classes.includes(action.class) &&
      (action.class === "governance" || rule.applies_to_destinations.includes(action.destination))
  );
}

function checkForRule(rule: PolicyRule, checks: GovernanceCheck[]): GovernanceCheck | undefined {
  return checks.find((check) => (check.policy_rule_id ?? check.rule) === rule.rule_id);
}

function BriefList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;

  return (
    <div>
      <p className="font-medium text-foreground">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function readinessVariant(readiness: AudienceReadiness): "success" | "warning" | "destructive" {
  if (readiness.readiness_status === "ready_for_review") return "success";
  if (readiness.readiness_status === "blocked_by_policy") return "destructive";
  return "warning";
}

function AudienceReadinessCard({ readiness }: { readiness: AudienceReadiness }) {
  return (
    <div className="mt-3 rounded-lg border bg-muted/20 p-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-medium text-foreground">Audience readiness</p>
          <p className="mt-1">Export target: {readiness.export_destination} / {readiness.export_format}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={readinessVariant(readiness)}>{label(readiness.readiness_status)}</Badge>
          <Badge variant={readiness.over_contact_risk === "high" ? "destructive" : "outline"}>
            {readiness.over_contact_risk} contact risk
          </Badge>
        </div>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-5">
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">estimated</p>
          <p className="text-lg font-semibold text-foreground">{readiness.estimated_audience_size}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">eligible</p>
          <p className="text-lg font-semibold text-foreground">{readiness.eligible_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">excluded</p>
          <p className="text-lg font-semibold text-foreground">{readiness.excluded_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">consent ready</p>
          <p className="text-lg font-semibold text-foreground">{readiness.consent_ready_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">suppressed</p>
          <p className="text-lg font-semibold text-foreground">{readiness.suppression_excluded_customers}</p>
        </div>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <BriefList title="Readiness reasons" items={readiness.readiness_reasons} />
        <BriefList title="Activation constraints" items={readiness.activation_constraints} />
        <BriefList title="Export fields" items={readiness.export_fields} />
      </div>
    </div>
  );
}

function InterventionBriefCard({ brief }: { brief: InterventionBrief }) {
  return (
    <div className="mt-3 rounded-md border bg-background p-3 text-xs text-muted-foreground">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-medium text-foreground">Governed intervention brief</p>
          <p className="mt-1">{brief.audience_summary}</p>
        </div>
        <Badge variant="outline">{brief.recommended_channel}</Badge>
      </div>
      {brief.audience_readiness ? <AudienceReadinessCard readiness={brief.audience_readiness} /> : null}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <BriefList title="Include" items={brief.inclusion_criteria} />
        <BriefList title="Exclude" items={brief.exclusion_criteria} />
        <div>
          <p className="font-medium text-foreground">Trigger</p>
          <p className="mt-1">{brief.trigger}</p>
        </div>
        <div>
          <p className="font-medium text-foreground">Content brief</p>
          <p className="mt-1">{brief.content_brief}</p>
        </div>
        <BriefList title="Personalization" items={brief.personalization_variables} />
        <div>
          <p className="font-medium text-foreground">Measurement</p>
          <p className="mt-1">Primary: {brief.primary_success_metric}</p>
          <p className="mt-1">Control: {brief.control_group}</p>
        </div>
        <BriefList title="Guardrails" items={brief.guardrail_metrics} />
        <BriefList title="Consent" items={brief.consent_notes} />
        <BriefList title="Governance" items={brief.governance_notes} />
      </div>
    </div>
  );
}

function ActionPortfolioCard({ problem, policyRules }: { problem: ProblemRecord; policyRules: PolicyRule[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Action Portfolio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {portfolioAreas.map((area) => {
          const actions = problem.action_proposals.filter((action) => action.class === area.actionClass);

          return (
            <section key={area.actionClass} className="rounded-lg border p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-sm font-semibold">{area.title}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{area.intent}</p>
                </div>
                <Badge variant="outline">{actions.length || "no"} draft{actions.length === 1 ? "" : "s"}</Badge>
              </div>

              {actions.length > 0 ? (
                <div className="mt-4 space-y-4">
                  {actions.map((action) => {
                    const rules = matchingRules(action, policyRules);

                    return (
                      <div key={action.action_id} className="rounded-md border bg-muted/20 p-3">
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-sm font-semibold">{label(action.class)}</h3>
                            <p className="mt-1 text-sm text-muted-foreground">{action.proposal}</p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="outline">{action.destination}</Badge>
                            <Badge variant={action.risk_level === "critical" ? "destructive" : "secondary"}>
                              {action.risk_level}
                            </Badge>
                            <Badge variant="outline">{action.owner}</Badge>
                            <Badge variant="outline">{label(action.approval_state)}</Badge>
                          </div>
                        </div>
                        {action.intervention_brief ? (
                          <InterventionBriefCard brief={action.intervention_brief} />
                        ) : null}
                        <div className="mt-3 grid gap-3 text-xs text-muted-foreground md:grid-cols-2">
                          <p>
                            Evidence: {problem.evidence.length} excerpts / confidence{" "}
                            {percent(problem.evidence_confidence)} / {problem.affected_cohort.customers} customers
                          </p>
                          <div>
                            <p className="font-medium text-foreground">Dependencies</p>
                            {action.depends_on && action.depends_on.length > 0 ? (
                              <ul className="mt-1 space-y-1">
                                {action.depends_on.map((dependencyId) => {
                                  const dependency = problem.action_proposals.find(
                                    (item) => item.action_id === dependencyId
                                  );

                                  return (
                                    <li key={dependencyId}>
                                      {dependency ? label(dependency.class) : dependencyId}
                                    </li>
                                  );
                                })}
                              </ul>
                            ) : (
                              <p className="mt-1">None - can be approved independently.</p>
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-foreground">Policy checks</p>
                            {rules.length > 0 ? (
                              <ul className="mt-1 space-y-1">
                                {rules.map((rule) => {
                                  const check = checkForRule(rule, problem.governance_checks);

                                  return (
                                    <li key={rule.rule_id}>
                                      {rule.title}: {check ? label(check.status) : "not evaluated"}
                                      {check?.blocking ? " / blocking" : ""}
                                    </li>
                                  );
                                })}
                              </ul>
                            ) : (
                              <p className="mt-1">No matching policy rule attached yet.</p>
                            )}
                          </div>
                        </div>
                        <ActionProposalEditor problemId={problem.problem_id} action={action} />
                        <ActionDecisionPanel problemId={problem.problem_id} action={action} />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">No {area.title.toLowerCase()} draft yet.</p>
              )}
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}

function JourneyImpactCard({ problem }: { problem: Awaited<ReturnType<typeof getActionQueueProblems>>[number] }) {
  const impact = problem.journey_impact;
  if (!impact) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Journey Intelligence</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <div>
            <div className="text-2xl font-bold">{impact.matched_events}</div>
            <p className="text-xs text-muted-foreground">matched events</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{impact.friction_events}</div>
            <p className="text-xs text-muted-foreground">friction events</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{percent(impact.deviation_score)}</div>
            <p className="text-xs text-muted-foreground">deviation score</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{impact.matched_accounts}</div>
            <p className="text-xs text-muted-foreground">accounts</p>
          </div>
        </div>
        {impact.top_event_names.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {impact.top_event_names.map((eventName) => (
              <Badge key={eventName} variant="outline">{label(eventName)}</Badge>
            ))}
          </div>
        ) : null}
        {impact.drivers.length > 0 ? (
          <ul className="space-y-1 text-sm text-muted-foreground">
            {impact.drivers.map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default async function InsightDetailPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [problems, policyRules] = await Promise.all([getActionQueueProblems(), getPolicyRules()]);
  const problem = problems.find((item) => item.problem_id === id);

  if (!problem) notFound();

  const score = problem.impact_score ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Link href="/insights" className="text-sm text-muted-foreground hover:text-foreground">
            Back to insights
          </Link>
          <h1 className="mt-2 text-2xl font-bold">{problem.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {problem.journey} / {problem.journey_stage} / owner: {problem.owner}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={problem.status === "blocked_by_policy" ? "destructive" : "secondary"}>
            {label(problem.status)}
          </Badge>
          <Badge variant="outline">Impact {percent(score)}</Badge>
          <Badge variant="outline">Evidence {percent(problem.evidence_confidence)}</Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Impact Band</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{problem.impact_band ?? "unknown"}</div>
            <p className="mt-1 text-xs text-muted-foreground">{problem.approval_pressure ?? "ready"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Affected Cohort</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{problem.affected_cohort.customers}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {problem.affected_cohort.accounts} accounts / {problem.affected_cohort.high_value_accounts} high value
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Outcome Contract</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold">{problem.outcome_contract.primary_metric}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {problem.outcome_contract.comparison_method} / {problem.outcome_contract.measurement_window_days} days
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Problem Statement</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">{problem.statement}</p>
          <div>
            <h2 className="text-sm font-semibold">Root-cause hypothesis</h2>
            <p className="mt-1 text-sm text-muted-foreground">{problem.root_cause_hypothesis}</p>
          </div>
          {problem.known_limitations.length > 0 ? (
            <div>
              <h2 className="text-sm font-semibold">Known limitations</h2>
              <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                {problem.known_limitations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <DraftProblemEditor problem={problem} />

      <EvidencePanel
        evidence={problem.evidence}
        confidence={problem.evidence_confidence}
        affectedCohort={problem.affected_cohort}
        owner={problem.owner}
      />

      <AffectedContextPanel problemId={problem.problem_id} />
      <JourneyImpactCard problem={problem} />

      <ActionPortfolioCard problem={problem} policyRules={policyRules} />

      <Card>
        <CardHeader>
          <CardTitle>Governance Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {problem.governance_checks.map((check) => (
              <div key={check.check_id} className="rounded-lg border p-3">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{check.rule}</strong>
                  <Badge variant={check.blocking ? "destructive" : "secondary"}>
                    {label(check.status)}{check.blocking ? " / blocking" : ""}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{check.reason}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <ProblemLifecyclePanel problem={problem} />
      <CustomerClosurePanel problem={problem} />
      <OutcomeMeasurementPanel problemId={problem.problem_id} contract={problem.outcome_contract} />
    </div>
  );
}
