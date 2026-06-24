import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActionDecisionPanel } from "@/app/components/action-decision-panel";
import { ActionProposalEditor } from "@/app/components/action-proposal-editor";
import { AffectedContextPanel } from "@/app/components/affected-context-panel";
import { DraftProblemEditor } from "@/app/components/draft-problem-editor";
import { EvidencePanel } from "@/app/components/evidence-panel";
import { OutcomeMeasurementPanel } from "@/app/components/outcome-measurement-panel";
import { ProblemLifecyclePanel } from "@/app/components/problem-lifecycle-panel";
import { getActionQueueProblems } from "@/lib/api";

function percent(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function label(value: string): string {
  return value.replaceAll("_", " ");
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
  const problems = await getActionQueueProblems();
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

      <Card>
        <CardHeader>
          <CardTitle>Action Portfolio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {problem.action_proposals.map((action) => (
            <section key={action.action_id} className="rounded-lg border p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="text-sm font-semibold">{label(action.class)}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{action.proposal}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{action.destination}</Badge>
                  <Badge variant={action.risk_level === "critical" ? "destructive" : "secondary"}>
                    {action.risk_level}
                  </Badge>
                  <Badge variant="outline">{action.owner}</Badge>
                </div>
              </div>
              <ActionProposalEditor problemId={problem.problem_id} action={action} />
              <ActionDecisionPanel problemId={problem.problem_id} action={action} />
            </section>
          ))}
        </CardContent>
      </Card>

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
      <OutcomeMeasurementPanel problemId={problem.problem_id} contract={problem.outcome_contract} />
    </div>
  );
}
