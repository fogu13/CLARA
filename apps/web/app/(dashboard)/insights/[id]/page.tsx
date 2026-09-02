"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertCircle, FileDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActionDecisionPanel } from "@/app/components/action-decision-panel";
import { ActionProposalEditor } from "@/app/components/action-proposal-editor";
import { AffectedContextPanel } from "@/app/components/affected-context-panel";
import { CustomerClosurePanel } from "@/app/components/customer-closure-panel";
import { DraftProblemEditor } from "@/app/components/draft-problem-editor";
import { EvidencePanel } from "@/app/components/evidence-panel";
import { OutcomeContractCard } from "@/app/components/outcome-contract-card";
import { OutcomeMeasurementPanel } from "@/app/components/outcome-measurement-panel";
import { ProblemLifecyclePanel } from "@/app/components/problem-lifecycle-panel";
import { WorksCouncilBanner } from "@/app/components/works-council-banner";
import { apiBaseUrl, apiHeaders, getPolicyRules, getProblem } from "@/lib/client-api";
import { percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type {
  ActionClass,
  ActionProposal,
  AudienceReadiness,
  GovernanceCheck,
  InterventionBrief,
  PolicyRule,
  ProblemRecord
} from "@/lib/types";


function label(value: string): string {
  return value.replaceAll("_", " ");
}

type PortfolioArea = {
  actionClass: ActionClass;
  titleKey: "areaStructural" | "areaRecovery" | "areaIntervention" | "areaResearch" | "areaGovernance";
  intentKey: "areaStructuralIntent" | "areaRecoveryIntent" | "areaInterventionIntent" | "areaResearchIntent" | "areaGovernanceIntent";
};

const portfolioAreas: PortfolioArea[] = [
  { actionClass: "structural", titleKey: "areaStructural", intentKey: "areaStructuralIntent" },
  { actionClass: "customer_recovery", titleKey: "areaRecovery", intentKey: "areaRecoveryIntent" },
  { actionClass: "journey_intervention", titleKey: "areaIntervention", intentKey: "areaInterventionIntent" },
  { actionClass: "research", titleKey: "areaResearch", intentKey: "areaResearchIntent" },
  { actionClass: "governance", titleKey: "areaGovernance", intentKey: "areaGovernanceIntent" }
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
  const { t } = useI18n();
  return (
    <div className="mt-3 rounded-lg border bg-muted/20 p-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-medium text-foreground">{t.detail.audienceReadiness}</p>
          <p className="mt-1">{t.detail.exportTarget}: {readiness.export_destination} / {readiness.export_format}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={readinessVariant(readiness)}>{label(readiness.readiness_status)}</Badge>
          <Badge variant={readiness.over_contact_risk === "high" ? "destructive" : "outline"}>
            {readiness.over_contact_risk} {t.detail.contactRisk}
          </Badge>
        </div>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-5">
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t.detail.estimated}</p>
          <p className="text-lg font-semibold text-foreground">{readiness.estimated_audience_size}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t.detail.eligible}</p>
          <p className="text-lg font-semibold text-foreground">{readiness.eligible_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t.detail.excluded}</p>
          <p className="text-lg font-semibold text-foreground">{readiness.excluded_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t.detail.consentReady}</p>
          <p className="text-lg font-semibold text-foreground">{readiness.consent_ready_customers}</p>
        </div>
        <div className="rounded-md border bg-background p-2">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{t.detail.suppressed}</p>
          <p className="text-lg font-semibold text-foreground">{readiness.suppression_excluded_customers}</p>
        </div>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <BriefList title={t.detail.readinessReasons} items={readiness.readiness_reasons} />
        <BriefList title={t.detail.activationConstraints} items={readiness.activation_constraints} />
        <BriefList title={t.detail.exportFields} items={readiness.export_fields} />
      </div>
    </div>
  );
}

function InterventionBriefCard({ brief }: { brief: InterventionBrief }) {
  const { t } = useI18n();
  return (
    <div className="mt-3 rounded-md border bg-background p-3 text-xs text-muted-foreground">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-medium text-foreground">{t.detail.interventionBrief}</p>
          <p className="mt-1">{brief.audience_summary}</p>
        </div>
        <Badge variant="outline">{brief.recommended_channel}</Badge>
      </div>
      {brief.audience_readiness ? <AudienceReadinessCard readiness={brief.audience_readiness} /> : null}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <BriefList title={t.detail.include} items={brief.inclusion_criteria} />
        <BriefList title={t.detail.exclude} items={brief.exclusion_criteria} />
        <div>
          <p className="font-medium text-foreground">{t.detail.trigger}</p>
          <p className="mt-1">{brief.trigger}</p>
        </div>
        <div>
          <p className="font-medium text-foreground">{t.detail.contentBrief}</p>
          <p className="mt-1">{brief.content_brief}</p>
        </div>
        <BriefList title={t.detail.personalization} items={brief.personalization_variables} />
        <div>
          <p className="font-medium text-foreground">{t.detail.measurement}</p>
          <p className="mt-1">{t.detail.primary}: {brief.primary_success_metric}</p>
          <p className="mt-1">{t.detail.control}: {brief.control_group}</p>
        </div>
        <BriefList title={t.detail.guardrails} items={brief.guardrail_metrics} />
        <BriefList title={t.detail.consent} items={brief.consent_notes} />
        <BriefList title={t.detail.governance} items={brief.governance_notes} />
      </div>
    </div>
  );
}

function ActionPortfolioCard({ problem, policyRules }: { problem: ProblemRecord; policyRules: PolicyRule[] }) {
  const { t } = useI18n();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.detail.actionPortfolio}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {portfolioAreas.map((area) => {
          const actions = problem.action_proposals.filter((action) => action.class === area.actionClass);

          return (
            <section key={area.actionClass} className="rounded-lg border p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-sm font-semibold">{t.detail[area.titleKey]}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{t.detail[area.intentKey]}</p>
                </div>
                <Badge variant="outline">{actions.length || t.detail.noDraft} {actions.length === 1 ? t.detail.draft : t.detail.drafts}</Badge>
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
                            {t.detail.evidenceLine
                              .replace("{n}", String(problem.evidence.length))
                              .replace("{c}", percent(problem.evidence_confidence))
                              .replace("{k}", String(problem.affected_cohort.customers))}
                          </p>
                          <div>
                            <p className="font-medium text-foreground">{t.detail.dependencies}</p>
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
                              <p className="mt-1">{t.detail.noDependencies}</p>
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{t.detail.policyChecks}</p>
                            {rules.length > 0 ? (
                              <ul className="mt-1 space-y-1">
                                {rules.map((rule) => {
                                  const check = checkForRule(rule, problem.governance_checks);

                                  return (
                                    <li key={rule.rule_id}>
                                      {rule.title}: {check ? label(check.status) : t.detail.notEvaluated}
                                      {check?.blocking ? t.detail.blockingSuffix : ""}
                                    </li>
                                  );
                                })}
                              </ul>
                            ) : (
                              <p className="mt-1">{t.detail.noPolicyRule}</p>
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
                <p className="mt-4 text-sm text-muted-foreground">{t.detail.noAreaDraftYet.replace("{area}", t.detail[area.titleKey])}</p>
              )}
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}

function JourneyImpactCard({ problem }: { problem: ProblemRecord }) {
  const { t } = useI18n();
  const impact = problem.journey_impact;
  if (!impact) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.detail.journeyIntelligence}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <div>
            <div className="text-2xl font-bold">{impact.matched_events}</div>
            <p className="text-xs text-muted-foreground">{t.detail.matchedEvents}</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{impact.friction_events}</div>
            <p className="text-xs text-muted-foreground">{t.detail.frictionEvents}</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{percent(impact.deviation_score)}</div>
            <p className="text-xs text-muted-foreground">{t.detail.deviationScore}</p>
          </div>
          <div>
            <div className="text-2xl font-bold">{impact.matched_accounts}</div>
            <p className="text-xs text-muted-foreground">{t.detail.accounts}</p>
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

export default function InsightDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [problem, setProblem] = useState<ProblemRecord | null>(null);
  const [policyRules, setPolicyRules] = useState<PolicyRule[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [packBusy, setPackBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [loadedProblem, loadedRules] = await Promise.all([getProblem(id), getPolicyRules()]);
        if (cancelled) return;
        setProblem(loadedProblem);
        setPolicyRules(loadedRules);
        setStatus("ready");
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "";
        // client-api surfaces the backend detail ("Problem not found") rather
        // than the numeric status, so match both forms.
        if (message.includes("404") || /not found/i.test(message)) {
          setStatus("missing");
        } else {
          setErrorDetail(message);
          setStatus("error");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (status === "loading") return <div className="text-muted-foreground">{t.common.loading}</div>;

  if (status === "missing" || status === "error" || !problem) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            {status === "missing" ? t.detail.notFound : `${t.detail.loadFailed}${errorDetail ? `: ${errorDetail}` : ""}`}
          </p>
          <Link href="/insights" className="mt-3 inline-block text-sm text-primary hover:underline">
            {t.detail.back}
          </Link>
        </CardContent>
      </Card>
    );
  }

  const score = problem.impact_score ?? 0;
  const dueDate = problem.due_at ? new Date(problem.due_at) : null;
  const overdue = Boolean(dueDate) && problem.status !== "resolved" && (dueDate as Date).getTime() < Date.now();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Link href="/insights" className="text-sm text-muted-foreground hover:text-foreground">
            {t.detail.back}
          </Link>
          <h1 className="mt-2 text-2xl font-bold">{problem.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {problem.journey} / {problem.journey_stage} / {t.detail.ownerLabel}: {problem.owner}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={problem.status === "blocked_by_policy" ? "destructive" : "secondary"}>
            {label(problem.status)}
          </Badge>
          <Badge variant="outline">{t.detail.impact} {percent(score)}</Badge>
          <Badge variant="outline">{t.detail.evidence} {percent(problem.evidence_confidence)}</Badge>
          <Badge variant="outline" title={problem.theme_tag ?? undefined}>
            {problem.origin === "ai_theme" ? t.detail.originTheme : t.detail.originStage}
          </Badge>
          {dueDate ? (
            <Badge variant={overdue ? "destructive" : "secondary"} title={dueDate.toISOString()}>
              {overdue ? `${t.detail.overdue} · ` : `${t.detail.dueDate} `}
              {dueDate.toLocaleDateString()}
            </Badge>
          ) : null}
          <button
            type="button"
            disabled={packBusy}
            onClick={async () => {
              setPackBusy(true);
              // Anchor in a new tab would 401 when auth is on: fetch with the
              // session headers and open the blob instead.
              try {
                const res = await fetch(
                  `${apiBaseUrl()}/problems/${problem.problem_id}/evidence-pack`,
                  { credentials: "include", headers: apiHeaders() }
                );
                if (!res.ok) throw new Error(`${res.status}`);
                const url = URL.createObjectURL(await res.blob());
                window.open(url, "_blank", "noopener");
                setTimeout(() => URL.revokeObjectURL(url), 60_000);
              } catch {
                window.alert(t.detail.loadFailed);
              } finally {
                setPackBusy(false);
              }
            }}
            className="inline-flex items-center rounded-md border px-3 py-1 text-xs font-medium hover:bg-muted"
          >
            <FileDown className="mr-1 h-3 w-3" /> {packBusy ? t.common.working : t.detail.evidencePack}
          </button>
        </div>
      </div>

      <nav
        aria-label="Sections"
        className="sticky top-0 z-10 -mx-2 flex gap-1 overflow-x-auto border-b bg-background/95 px-2 py-2 backdrop-blur"
      >
        {[
          ["statement", t.detail.navStatement],
          ["evidence", t.detail.navEvidence],
          ["portfolio", t.detail.navPortfolio],
          ["governance", t.detail.navGovernance],
          ["outcome", t.detail.navOutcome],
        ].map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            className="whitespace-nowrap rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            {label}
          </a>
        ))}
      </nav>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">{t.detail.impactBand}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{problem.impact_band ?? t.common.unknown}</div>
            <p className="mt-1 text-xs text-muted-foreground">{problem.approval_pressure ?? t.common.ready}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">{t.detail.affectedCohort}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{problem.affected_cohort.customers}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {problem.affected_cohort.accounts} {t.detail.accountsHighValue.replace("{n}", String(problem.affected_cohort.high_value_accounts))}
            </p>
          </CardContent>
        </Card>
        <OutcomeContractCard problem={problem} />
      </div>

      <Card id="statement" className="scroll-mt-14">
        <CardHeader>
          <CardTitle>{t.detail.problemStatement}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">{problem.statement}</p>
          <div>
            <h2 className="text-sm font-semibold">{t.detail.rootCause}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{problem.root_cause_hypothesis}</p>
          </div>
          {problem.known_limitations.length > 0 ? (
            <div>
              <h2 className="text-sm font-semibold">{t.detail.knownLimitations}</h2>
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

      <div id="evidence" className="scroll-mt-14" />
      <EvidencePanel
        evidence={problem.evidence}
        confidence={problem.evidence_confidence}
        affectedCohort={problem.affected_cohort}
        owner={problem.owner}
      />

      <AffectedContextPanel problemId={problem.problem_id} />
      <JourneyImpactCard problem={problem} />

      <div id="portfolio" className="scroll-mt-14" />
      <WorksCouncilBanner />
      <ActionPortfolioCard problem={problem} policyRules={policyRules} />

      <Card id="governance" className="scroll-mt-14">
        <CardHeader>
          <CardTitle>{t.detail.governanceChecks}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {problem.governance_checks.map((check) => (
              <div key={check.check_id} className="rounded-lg border p-3">
                <div className="flex items-center justify-between gap-3">
                  <strong className="text-sm">{check.rule}</strong>
                  <Badge variant={check.blocking ? "destructive" : "secondary"}>
                    {label(check.status)}{check.blocking ? t.detail.blockingSuffix : ""}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{check.reason}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div id="outcome" className="scroll-mt-14" />
      <ProblemLifecyclePanel problem={problem} />
      <CustomerClosurePanel problem={problem} />
      <OutcomeMeasurementPanel problemId={problem.problem_id} contract={problem.outcome_contract} />
    </div>
  );
}
