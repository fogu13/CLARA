"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Database, Upload, Webhook, RefreshCw } from "lucide-react";

export default function SourcesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Sources</h1>
        <p className="text-sm text-muted-foreground mt-1">Signal ingestion sources and connectors</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">CSV Import</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">Upload CSV files with column mapping</p>
            <Button size="sm" variant="outline">Import CSV</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Webhook className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">Webhook</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">POST signals to a public endpoint</p>
            <code className="text-xs block bg-muted p-2 rounded">POST /signals/import</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                <CardTitle className="text-base">Zendesk</CardTitle>
              </div>
              <Badge variant="success">Available</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">Pull support tickets as signals</p>
            <Button size="sm" variant="outline">
              <RefreshCw className="h-3 w-3 mr-1" />
              Pull Now
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Demo Datasets</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Load pre-built demo data for testing:</p>
          <div className="flex gap-2 mt-3">
            <Button size="sm" variant="outline">SaaS Onboarding</Button>
            <Button size="sm" variant="outline">E-commerce Checkout</Button>
            <Button size="sm" variant="outline">Retention Cancellation</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
