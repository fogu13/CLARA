"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CalendarClock, Play } from "lucide-react";
import { getMeasurements, runDueMeasurements, type MeasurementPlan } from "@/lib/client-api";

function statusVariant(status: string): "success" | "warning" | "secondary" | "outline" {
  if (status === "done") return "success";
  if (status === "manual_required") return "warning";
  if (status === "pending") return "secondary";
  return "outline";
}

export function MeasurementCheckpointsPanel() {
  const [plans, setPlans] = useState<MeasurementPlan[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    getMeasurements().then(setPlans).catch(() => setPlans([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runDue() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await runDueMeasurements();
      setMessage(
        `Measured ${result.measured} outcome${result.measured === 1 ? "" : "s"} from real signal data` +
          (result.manual_required > 0 ? `; ${result.manual_required} need a human-recorded value.` : ".")
      );
      load();
      window.dispatchEvent(new Event("clara:outcome-recorded"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Run failed.");
    } finally {
      setBusy(false);
    }
  }

  const pending = plans.filter((plan) => plan.status === "pending");
  const manual = plans.filter((plan) => plan.status === "manual_required");

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarClock className="h-4 w-4" /> Measurement checkpoints
          </CardTitle>
          <CardDescription>
            Scheduled automatically when an action is approved (T+7 and T+window). Signal-derived
            metrics are measured by CLARA from real data; business metrics become human tasks.
          </CardDescription>
        </div>
        <Button size="sm" disabled={busy} onClick={() => void runDue()}>
          <Play className="mr-1 h-3 w-3" /> {busy ? "Running…" : "Run due now"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        {plans.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No checkpoints yet — approve an action to start the clock.
          </p>
        ) : (
          <>
            {manual.length > 0 ? (
              <p className="text-xs text-amber-700">
                {manual.length} checkpoint{manual.length === 1 ? "" : "s"} waiting for a
                human-recorded measurement (CLARA never invents values for business metrics).
              </p>
            ) : null}
            <div className="space-y-2">
              {plans.slice(0, 12).map((plan) => (
                <div key={plan.id} className="flex items-start justify-between gap-2 rounded-md border p-2 text-sm">
                  <div>
                    <span className="font-medium">{plan.problem_id}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {plan.kind === "t7" ? "T+7 check" : "window close"} · due {plan.due_at.slice(0, 10)}
                    </span>
                    {plan.note ? (
                      <p className="mt-0.5 text-xs text-muted-foreground">{plan.note}</p>
                    ) : null}
                  </div>
                  <Badge variant={statusVariant(plan.status)}>{plan.status.replaceAll("_", " ")}</Badge>
                </div>
              ))}
            </div>
            {pending.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                {pending.length} pending — the background scheduler processes them automatically.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
