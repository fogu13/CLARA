"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MessageSquare, Upload, Sparkles } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SignalsPage() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_URL}/signals`);
        if (res.ok) setSignals(await res.json());
      } catch { /* API not running */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading signals...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signals</h1>
          <p className="text-sm text-muted-foreground mt-1">Customer feedback signals from all sources</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Upload className="h-4 w-4 mr-2" />
            Import CSV
          </Button>
          <Button size="sm">
            <Sparkles className="h-4 w-4 mr-2" />
            Run Triage
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Signals</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{signals.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Sources</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(signals.map(s => s.source)).size}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Enriched</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {signals.filter(s => s.enriched).length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Signal Feed</CardTitle></CardHeader>
        <CardContent>
          {signals.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No signals yet. Import CSV or connect a source.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {signals.slice(0, 20).map(s => (
                <div key={s.signal_id} className="flex items-start gap-3 border-b pb-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.feedback_text?.slice(0, 200)}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className="text-xs">{s.source}</Badge>
                      <span className="text-xs text-muted-foreground">{s.journey} / {s.journey_stage}</span>
                      {s.sentiment && (
                        <Badge variant={s.sentiment === "negative" ? "destructive" : s.sentiment === "positive" ? "success" : "secondary"}>
                          {s.sentiment}
                        </Badge>
                      )}
                      {s.urgency && s.urgency !== "medium" && (
                        <Badge variant={s.urgency === "critical" ? "destructive" : "warning"}>
                          {s.urgency}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
