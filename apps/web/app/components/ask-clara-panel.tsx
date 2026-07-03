"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageCircleQuestion, ShieldAlert } from "lucide-react";
import { askClara, type AskAnswer } from "@/lib/client-api";

export function AskClaraPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await askClara(trimmed));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageCircleQuestion className="h-4 w-4" /> Ask CLARA
        </CardTitle>
        <CardDescription>
          Answers come only from your feedback signals, with citations and a confidence score —
          CLARA refuses rather than guesses when the evidence is thin.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void submit();
            }}
            placeholder='e.g. "What are customers saying about refunds?"'
            maxLength={500}
          />
          <Button disabled={busy || !question.trim()} onClick={() => void submit()}>
            {busy ? "Asking…" : "Ask"}
          </Button>
        </div>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {result?.refused ? (
          <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-sm">
            <ShieldAlert className="mt-0.5 h-4 w-4 text-amber-600" />
            <div>
              <p className="font-medium">Not enough evidence to answer.</p>
              <p className="text-xs text-muted-foreground">{result.reason}</p>
            </div>
          </div>
        ) : null}

        {result && !result.refused ? (
          <div className="space-y-3">
            <div className="rounded-md border bg-muted/30 p-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <p>{result.answer}</p>
                <Badge variant="outline" className="shrink-0">
                  {Math.round(result.confidence * 100)}% conf
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Citations ({result.citations.length})
              </p>
              <div className="mt-1 space-y-1">
                {result.citations.map((citation) => (
                  <div key={citation.signal_id} className="rounded border p-2 text-xs">
                    <span className="font-mono font-medium">{citation.signal_id}</span>
                    <span className="ml-2 text-muted-foreground">
                      {citation.source} · {citation.language} · {citation.timestamp.slice(0, 10)} ·{" "}
                      {Math.round(citation.similarity * 100)}% match
                    </span>
                    <p className="mt-0.5 text-muted-foreground">“{citation.excerpt}”</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
