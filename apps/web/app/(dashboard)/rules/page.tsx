"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollText, Plus, Sparkles } from "lucide-react";

export default function RulesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Rules</h1>
          <p className="text-sm text-muted-foreground mt-1">Automation rules for triage and action routing</p>
        </div>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-2" />
          New Rule
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Rule Engine</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Rules define conditions that trigger actions. Conflict resolution uses
            priority → specificity → action-type dedupe.
          </p>
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <p className="text-sm font-medium">High-severity checkout issues → Jira ticket</p>
                <p className="text-xs text-muted-foreground">If severity = high AND category = ux_friction → create_ticket</p>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <p className="text-sm font-medium">Churn risk → Slack alert + segment</p>
                <p className="text-xs text-muted-foreground">If category = churn_risk → notify + create_segment</p>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Compliance concern → manual review</p>
                <p className="text-xs text-muted-foreground">If category = compliance_concern → blocking governance check</p>
              </div>
              <Badge variant="warning">Auto-block</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Conflict Resolution</CardTitle></CardHeader>
        <CardContent>
          <div className="text-xs space-y-1 text-muted-foreground">
            <p>1. <strong>Priority</strong> — higher priority rules win</p>
            <p>2. <strong>Specificity</strong> — more conditions = more specific</p>
            <p>3. <strong>Action-type dedupe</strong> — one action per type per insight</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
