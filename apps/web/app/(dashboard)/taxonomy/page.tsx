"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tags, Sparkles, GitBranch, Archive } from "lucide-react";

export default function TaxonomyPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Taxonomy</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adaptive semantic taxonomy with pgvector + auto-discovery
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline">
            <Sparkles className="h-4 w-4 mr-2" />
            Discover Themes
          </Button>
          <Button size="sm" variant="outline">
            <GitBranch className="h-4 w-4 mr-2" />
            Run Governance
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Active Nodes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Candidates</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Archived</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">—</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Tags className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Taxonomy Tree</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            3-level hierarchy with embeddings (vector(768)) and HNSW index.
            Nodes are: uploaded, seeded, or discovered. Governance auto-promotes
            candidates above confidence 0.80 with size ≥ 5, auto-merges near-duplicates
            (cosine ≥ 0.95), and archives stale discovered nodes (&gt; 90 days unmatched).
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="success">active</Badge>
              <span className="text-sm">Product / Checkout / Payment Failure</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="success">active</Badge>
              <span className="text-sm">Product / Onboarding / Setup Friction</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="warning">candidate</Badge>
              <span className="text-sm">Product / Billing / Refund Delay (discovered)</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Governance</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 text-sm md:grid-cols-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span>Auto-promote (conf ≥ 0.80, size ≥ 5)</span>
            </div>
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-blue-500" />
              <span>Auto-merge (cosine ≥ 0.95)</span>
            </div>
            <div className="flex items-center gap-2">
              <Archive className="h-4 w-4 text-muted-foreground" />
              <span>Decay (&gt; 90 days unmatched)</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
