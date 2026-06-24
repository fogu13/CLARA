"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Workspace configuration</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>General workspace settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="name">Workspace Name</Label>
            <Input id="name" className="mt-1" defaultValue="My Workspace" />
          </div>
          <div>
            <Label htmlFor="slug">Slug</Label>
            <Input id="slug" className="mt-1" defaultValue="my-workspace" />
          </div>
          <div>
            <Label htmlFor="email">Notification Email</Label>
            <Input id="email" type="email" className="mt-1" placeholder="alerts@company.com" />
          </div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Configuration</CardTitle>
          <CardDescription>Provider-agnostic LLM settings (env vars)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI_BASE_URL</span>
              <code className="bg-muted px-2 py-0.5 rounded">http://localhost:11434/v1</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI_MODEL</span>
              <code className="bg-muted px-2 py-0.5 rounded">llama3.1</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI_EMBED_MODEL</span>
              <code className="bg-muted px-2 py-0.5 rounded">nomic-embed-text</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">AI_EMBED_DIM</span>
              <code className="bg-muted px-2 py-0.5 rounded">768</code>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Langfuse</span>
              <code className="bg-muted px-2 py-0.5 rounded">self-hosted :3000</code>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            These are set as environment variables on the API server. Local-first by default (Ollama).
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Measurement</CardTitle>
          <CardDescription>Outcome measurement defaults</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="window">Default Measurement Window (days)</Label>
            <Input id="window" type="number" className="mt-1" defaultValue={14} />
          </div>
          <div>
            <Label htmlFor="half-life">Learning Half-Life (days)</Label>
            <Input id="half-life" type="number" className="mt-1" defaultValue={180} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
