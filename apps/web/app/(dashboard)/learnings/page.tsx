"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { GraduationCap, TrendingUp, TrendingDown, Clock } from "lucide-react";

const FRESHNESS_VARIANT: Record<string, any> = {
  VALIDATED: "success",
  EMERGING: "warning",
  STALE: "secondary",
};

export default function LearningsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Learnings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Action-outcome learnings with confidence decay — fresher learnings surface first
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Confidence Decay</CardTitle></CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Exponential decay from last validation:</p>
            <code className="text-xs mt-2 block bg-muted p-2 rounded">base × 0.5^(age_days / half_life)</code>
            <p className="text-xs text-muted-foreground mt-2">Default half-life: 180 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Freshness Badges</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              <Badge variant="success">VALIDATED — within half-life</Badge>
              <Badge variant="warning">EMERGING — 1-2× half-life</Badge>
              <Badge variant="secondary">STALE — past 2× half-life</Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Verdict Types</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1 text-xs">
              <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3 text-emerald-500" /> worked</span>
              <span className="flex items-center gap-1"><TrendingUp className="h-3 w-3 text-amber-500" /> partially_worked</span>
              <span className="flex items-center gap-1"><TrendingDown className="h-3 w-3 text-destructive" /> did_not_work</span>
              <span className="flex items-center gap-1"><Clock className="h-3 w-3 text-muted-foreground" /> inconclusive</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Learning Repository</CardTitle></CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <GraduationCap className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              Learnings are generated when the triage pipeline completes with outcome measurement.
              Run the pipeline and measure outcomes to populate this view.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
