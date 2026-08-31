"use client";

// Candidate review for /sources. Signal imports live on /signals (CSV upload
// with column mapping and batch undo) — this panel deliberately does not carry
// a second import path. The demo-dataset importer only appears while the
// workspace has no signals at all, so demo tooling stays out of the way of
// live data.

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Database, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  acceptProblemCandidate,
  getDemoDatasets,
  getProblemCandidates,
  getSignals,
  importDemoDataset,
  rejectProblemCandidate
} from "../../lib/client-api";
import type { DemoDatasetSummary, ProblemCandidate } from "../../lib/types";
import { currentUserEmail } from "../../lib/auth-client";
import { percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type IntakeState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  signalCount: number;
  candidates: ProblemCandidate[];
  demoDatasets: DemoDatasetSummary[];
};

const statusVariant: Record<ProblemCandidate["review_status"], "warning" | "secondary" | "success" | "outline"> = {
  pending: "warning",
  duplicate: "secondary",
  accepted: "success",
  rejected: "outline"
};

function candidateStatusLabels(t: ReturnType<typeof useI18n>["t"]): Record<ProblemCandidate["review_status"], string> {
  return {
    pending: t.intake.statusPending,
    duplicate: t.intake.statusDuplicate,
    accepted: t.intake.statusAccepted,
    rejected: t.intake.statusRejected
  };
}

function CandidateIntelligence({ candidate }: { candidate: ProblemCandidate }) {
  const classifications = candidate.classifications ?? [];
  const limitations = candidate.known_limitations ?? [];
  const contradictions = candidate.contradictory_evidence ?? [];
  const rootCauseAnalysis = candidate.root_cause_analysis;

  if (!rootCauseAnalysis && !classifications.length && !limitations.length && !contradictions.length) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 rounded-md border bg-muted/20 p-3 text-xs text-muted-foreground">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium uppercase tracking-wide">Trusted intelligence</span>
        <span className="font-semibold text-foreground">
          {percent(candidate.emerging_problem_score ?? 0)} emerging score
        </span>
      </div>
      {rootCauseAnalysis ? (
        <div>
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-foreground">Root cause</span>
            <span>{percent(rootCauseAnalysis.confidence)}</span>
          </div>
          <p className="mt-1">{rootCauseAnalysis.hypothesis}</p>
          {rootCauseAnalysis.factors[0] ? <p className="mt-1">{rootCauseAnalysis.factors[0].explanation}</p> : null}
          {rootCauseAnalysis.validation_questions[0] ? (
            <p className="mt-1">Validate: {rootCauseAnalysis.validation_questions[0]}</p>
          ) : null}
        </div>
      ) : null}
      {classifications.length ? (
        <ul className="space-y-1.5">
          {classifications.map((classification) => (
            <li key={`${classification.taxonomy_type}-${classification.category_id}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-foreground">{classification.label}</span>
                <span>{percent(classification.confidence)}</span>
              </div>
              <p>
                {classification.taxonomy_type.replaceAll("_", " ")} /{" "}
                {classification.matched_terms.slice(0, 4).join(", ")}
              </p>
              {classification.language_notes[0] ? <p>{classification.language_notes[0]}</p> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {contradictions[0] ? <p className="text-amber-700 dark:text-amber-400">{contradictions[0]}</p> : null}
      {limitations[0] ? <p>Limit: {limitations[0]}</p> : null}
    </div>
  );
}

async function loadIntakeState(): Promise<Pick<IntakeState, "signalCount" | "candidates" | "demoDatasets">> {
  const [signals, candidates, demoDatasets] = await Promise.all([
    getSignals(),
    getProblemCandidates(),
    getDemoDatasets()
  ]);
  return { signalCount: signals.length, candidates, demoDatasets };
}

export function SignalIntakePanel() {
  const { t } = useI18n();
  const [selectedDemoDatasetId, setSelectedDemoDatasetId] = useState("");
  const [state, setState] = useState<IntakeState>({
    status: "loading",
    message: "",
    signalCount: 0,
    candidates: [],
    demoDatasets: []
  });

  useEffect(() => {
    loadIntakeState()
      .then(({ signalCount, candidates, demoDatasets }) => {
        setState({ status: "ready", message: "", signalCount, candidates, demoDatasets });
        setSelectedDemoDatasetId((current) => current || demoDatasets[0]?.dataset_id || "");
      })
      .catch((error) => {
        // A failed load stays a visible failure — never sample data in live
        // counters (the same rule the dashboard enforces).
        setState({
          status: "error",
          message: error instanceof Error ? error.message : t.common.error,
          signalCount: 0,
          candidates: [],
          demoDatasets: []
        });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refresh(message: string) {
    const { signalCount, candidates, demoDatasets } = await loadIntakeState();
    setState({ status: "ready", message, signalCount, candidates, demoDatasets });
  }

  async function importSelectedDemoDataset() {
    const datasetId = selectedDemoDatasetId || state.demoDatasets[0]?.dataset_id;
    if (!datasetId) return;

    setState((current) => ({ ...current, status: "saving", message: "Importing demo dataset..." }));
    try {
      const result = await importDemoDataset(datasetId);
      await refresh(
        `Imported ${result.title}: ${result.signals.imported} signals, ` +
          `${result.signals.skipped_duplicates} signal duplicates, ` +
          `${result.customer_context.imported} context rows.`
      );
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import demo dataset."
      }));
    }
  }

  async function acceptCandidate(candidate: ProblemCandidate) {
    if (candidate.review_status !== "pending") return;
    setState((current) => ({ ...current, status: "saving", message: "Creating draft problem..." }));
    try {
      const problem = await acceptProblemCandidate(candidate.candidate_id, {
        reviewer: currentUserEmail() ?? "local-user",
        note: "Accepted from candidate review."
      });
      await refresh(`Created draft problem ${problem.problem_id}.`);
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not promote candidate."
      }));
    }
  }

  async function rejectCandidate(candidate: ProblemCandidate) {
    if (candidate.review_status === "accepted" || candidate.review_status === "rejected") return;
    setState((current) => ({ ...current, status: "saving", message: "Rejecting candidate..." }));
    try {
      await rejectProblemCandidate(candidate.candidate_id, {
        reviewer: currentUserEmail() ?? "local-user",
        note:
          candidate.review_status === "duplicate"
            ? `Duplicate of ${candidate.duplicate_problem_id}.`
            : "Rejected from candidate review."
      });
      await refresh(`Rejected candidate ${candidate.candidate_id}.`);
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not reject candidate."
      }));
    }
  }

  if (state.status === "loading") {
    return <div className="text-muted-foreground">{t.intake.loadingCandidates}...</div>;
  }

  const busy = state.status === "saving";
  const pendingCandidates = state.candidates.filter((candidate) => candidate.review_status === "pending").length;
  const duplicateCandidates = state.candidates.filter((candidate) => candidate.review_status === "duplicate").length;
  const selectedDemoDataset =
    state.demoDatasets.find((dataset) => dataset.dataset_id === selectedDemoDatasetId) ?? state.demoDatasets[0];
  const emptyWorkspace = state.status !== "error" && state.signalCount === 0;

  return (
    <div className="space-y-6">
      {state.status === "error" ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          {t.intake.apiUnavailable}: {state.message}
        </div>
      ) : state.message ? (
        <div
          className={cn(
            "rounded-md border p-3 text-sm",
            busy
              ? "border-border bg-muted text-muted-foreground"
              : "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
          )}
        >
          {state.message}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">{t.intake.problemCandidates}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{state.candidates.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">{t.intake.statusPending}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingCandidates}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">{t.intake.statusDuplicate}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{duplicateCandidates}</div>
          </CardContent>
        </Card>
      </div>

      {emptyWorkspace && state.demoDatasets.length > 0 ? (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">{t.intake.demoDataset}</CardTitle>
            </div>
            <p className="text-sm text-muted-foreground">
              Import packaged demo signals and customer context for a repeatable walkthrough. This
              option disappears once the workspace holds real signals.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              className="h-9 w-full max-w-md rounded-md border bg-background px-2 text-sm"
              aria-label={t.intake.demoDataset}
              value={selectedDemoDataset?.dataset_id ?? ""}
              onChange={(event) => setSelectedDemoDatasetId(event.target.value)}
            >
              {state.demoDatasets.map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.title}
                </option>
              ))}
            </select>
            {selectedDemoDataset ? (
              <p className="text-xs text-muted-foreground">
                {selectedDemoDataset.industry} · {selectedDemoDataset.signal_count} signals /{" "}
                {selectedDemoDataset.context_count} context rows · {selectedDemoDataset.description}
              </p>
            ) : null}
            <Button size="sm" disabled={busy || !selectedDemoDataset} onClick={importSelectedDemoDataset}>
              {t.intake.importDemo}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <CardTitle className="text-base">{t.intake.candidateReview}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{t.intake.candidateReviewHint}</p>
          </div>
          <Badge variant="secondary">
            {pendingCandidates} {t.intake.pending}
          </Badge>
        </CardHeader>
        <CardContent>
          {state.candidates.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm font-medium">{t.intake.noCandidates}</p>
              <p className="mt-1 text-sm text-muted-foreground">{t.intake.importOnSignals}</p>
              <Link
                href="/signals"
                className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
              >
                {t.nav.signals}
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </div>
          ) : (
            <ul className="space-y-4">
              {state.candidates.map((candidate) => (
                <li key={candidate.candidate_id} className="rounded-lg border p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={statusVariant[candidate.review_status]}>
                          {candidateStatusLabels(t)[candidate.review_status]}
                        </Badge>
                        <span className="text-sm font-semibold">{candidate.title}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {candidate.candidate_id} / {candidate.journey} / {candidate.journey_stage}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold">{percent(candidate.confidence)}</p>
                      <p className="text-xs text-muted-foreground">
                        {candidate.signal_count} {t.common.signals}
                      </p>
                    </div>
                  </div>

                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
                    <div>
                      <dt className="text-muted-foreground">{t.common.customers}</dt>
                      <dd className="font-medium">{candidate.customer_count}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Accounts</dt>
                      <dd className="font-medium">{candidate.account_count}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">{t.common.sources}</dt>
                      <dd className="font-medium">{candidate.sources.join(", ")}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">{t.common.owner}</dt>
                      <dd className="font-medium">{candidate.suggested_owner}</dd>
                    </div>
                  </dl>

                  {candidate.duplicate_problem_id ? (
                    <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                      Duplicate match: {candidate.duplicate_problem_id}. {candidate.duplicate_reason}
                    </p>
                  ) : null}
                  <p className="mt-2 text-sm text-muted-foreground">{candidate.root_cause_hypothesis}</p>
                  {candidate.evidence[0] ? (
                    <blockquote className="mt-2 border-l-2 pl-3 text-sm italic text-muted-foreground">
                      &quot;{candidate.evidence[0].excerpt}&quot;
                    </blockquote>
                  ) : null}
                  <CandidateIntelligence candidate={candidate} />
                  {candidate.review_note ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Reviewed by {candidate.reviewer}: {candidate.review_note}
                    </p>
                  ) : null}

                  <div className="mt-3 flex gap-2">
                    <Button
                      size="sm"
                      disabled={busy || candidate.review_status !== "pending"}
                      onClick={() => acceptCandidate(candidate)}
                    >
                      <Check className="mr-1 h-3 w-3" /> {t.intake.acceptIntoQueue}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={
                        busy || candidate.review_status === "accepted" || candidate.review_status === "rejected"
                      }
                      onClick={() => rejectCandidate(candidate)}
                    >
                      <X className="mr-1 h-3 w-3" /> {t.common.reject}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
