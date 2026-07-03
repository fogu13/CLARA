"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tags, Lock, GitBranch, Languages, Pencil, Sparkles, Check, X } from "lucide-react";
import {
  bootstrapTaxonomy,
  getLanguageQuality,
  getTaxonomies,
  getTerminologyDictionary,
  lockTaxonomyCategory,
  renameTaxonomyCategory,
  reviewTaxonomyCategory
} from "@/lib/client-api";
import { fallbackTaxonomies, fallbackTerminologyDictionary } from "@/lib/sample-data";
import type {
  LanguageQualityReport,
  TaxonomyCatalog,
  TaxonomyCategory,
  TaxonomyType,
  TerminologyDictionaryEntry
} from "@/lib/types";

type TaxonomyState = {
  status: "loading" | "ready" | "fallback" | "error";
  message: string;
  catalogs: TaxonomyCatalog[];
  terms: TerminologyDictionaryEntry[];
  languageQuality?: LanguageQualityReport;
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export default function TaxonomyPage() {
  const [state, setState] = useState<TaxonomyState>({
    status: "loading",
    message: "Loading taxonomy catalogs...",
    catalogs: [],
    terms: []
  });
  const [editing, setEditing] = useState<{ type: TaxonomyType; categoryId: string } | null>(null);
  const [renameLabel, setRenameLabel] = useState("");
  const [renameDescription, setRenameDescription] = useState("");
  const [action, setAction] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  function applyCatalog(updated: TaxonomyCatalog) {
    setState((current) => ({
      ...current,
      catalogs: current.catalogs.map((catalog) =>
        catalog.taxonomy_type === updated.taxonomy_type ? updated : catalog
      )
    }));
  }

  function startRename(type: TaxonomyType, category: TaxonomyCategory) {
    setEditing({ type, categoryId: category.category_id });
    setRenameLabel(category.label);
    setRenameDescription(category.description);
    setAction(null);
  }

  async function submitRename(type: TaxonomyType, categoryId: string) {
    if (!renameLabel.trim()) return;
    setBusy(true);
    try {
      const updated = await renameTaxonomyCategory(type, {
        category_id: categoryId,
        label: renameLabel.trim(),
        description: renameDescription.trim() || undefined
      });
      applyCatalog(updated);
      setEditing(null);
      setAction({ tone: "ok", message: `Renamed to “${renameLabel.trim()}”.` });
    } catch (error) {
      setAction({ tone: "error", message: error instanceof Error ? error.message : "Rename failed." });
    } finally {
      setBusy(false);
    }
  }

  async function lockCategory(type: TaxonomyType, categoryId: string) {
    setBusy(true);
    try {
      applyCatalog(await lockTaxonomyCategory(type, categoryId));
      setAction({ tone: "ok", message: "Category locked." });
    } catch (error) {
      setAction({ tone: "error", message: error instanceof Error ? error.message : "Lock failed." });
    } finally {
      setBusy(false);
    }
  }

  async function runBootstrap() {
    setBusy(true);
    setAction(null);
    try {
      const report = await bootstrapTaxonomy();
      const catalogs = await getTaxonomies();
      setState((current) => ({ ...current, catalogs }));
      setAction({
        tone: "ok",
        message:
          report.proposed > 0
            ? `Proposed ${report.proposed} theme${report.proposed === 1 ? "" : "s"} from ${report.scanned} signals — review below.`
            : `Scanned ${report.scanned} signals — no new themes above the confidence threshold.`
      });
    } catch (error) {
      setAction({ tone: "error", message: error instanceof Error ? error.message : "Bootstrap failed." });
    } finally {
      setBusy(false);
    }
  }

  async function reviewCategory(type: TaxonomyType, categoryId: string, decision: "accept" | "reject") {
    setBusy(true);
    try {
      applyCatalog(await reviewTaxonomyCategory(type, { category_id: categoryId, decision }));
      setAction({ tone: "ok", message: decision === "accept" ? "Theme accepted into the taxonomy." : "Theme rejected (kept in audit history)." });
    } catch (error) {
      setAction({ tone: "error", message: error instanceof Error ? error.message : "Review failed." });
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const [catalogs, terms, languageQuality] = await Promise.all([
          getTaxonomies(),
          getTerminologyDictionary(),
          getLanguageQuality()
        ]);
        setState({
          status: "ready",
          message: "Taxonomy catalogs loaded from the API.",
          catalogs,
          terms,
          languageQuality
        });
      } catch {
        setState({
          status: "fallback",
          message: "API unreachable — showing sample taxonomy data.",
          catalogs: fallbackTaxonomies,
          terms: fallbackTerminologyDictionary
        });
      }
    }

    void load();
  }, []);

  const activeNodes = state.catalogs.reduce(
    (total, catalog) => total + catalog.categories.filter((category) => category.status === "active").length,
    0
  );
  const changedNodes = state.catalogs.reduce(
    (total, catalog) => total + catalog.categories.filter((category) => category.change_history.length > 0).length,
    0
  );
  const lockedNodes = state.catalogs.reduce(
    (total, catalog) => total + catalog.categories.filter((category) => category.locked).length,
    0
  );

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-bold">Taxonomy</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Versioned product, journey, contact-reason, marketing and compliance taxonomy catalogs.
            </p>
          </div>
          <Button disabled={busy} onClick={() => void runBootstrap()}>
            <Sparkles className="mr-1 h-4 w-4" />
            {busy ? "Working…" : "Bootstrap themes from signals"}
          </Button>
        </div>
      </div>

      {state.status === "error" ? <div className="text-sm text-destructive">{state.message}</div> : null}
      {state.status === "fallback" ? (
        <div className="rounded-md border border-dashed border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          {state.message}
        </div>
      ) : null}

      {action ? (
        <div
          className={`rounded-md border p-3 text-sm ${
            action.tone === "error"
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
          }`}
        >
          {action.message}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Catalogs</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{state.catalogs.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Active Nodes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{activeNodes}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Changed Nodes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{changedNodes}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Locked Nodes</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{lockedNodes}</div></CardContent>
        </Card>
      </div>


      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Languages className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">German / English Readiness</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {state.languageQuality ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge variant={state.languageQuality.german_english_ready ? "success" : "warning"}>
                  {state.languageQuality.german_english_ready ? "DE/EN ready" : "Needs language coverage"}
                </Badge>
                <Badge variant="outline">{state.languageQuality.total_signals} signals</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {state.languageQuality.languages.map((language) => (
                  <div key={language.language} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between">
                      <strong className="text-sm uppercase">{language.language}</strong>
                      <Badge variant={language.readiness === "ready" ? "success" : "secondary"}>
                        {language.readiness.replaceAll("_", " ")}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {language.signal_count} signals / {language.terminology_entries} terminology entries / {language.original_language_evidence} original-language evidence rows
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Language readiness is unavailable.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Tags className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Taxonomy Catalogs</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {state.status === "loading" ? (
            <p className="text-sm text-muted-foreground">{state.message}</p>
          ) : null}

          {state.catalogs.length === 0 && state.status !== "loading" ? (
            <p className="text-sm text-muted-foreground">No taxonomy catalogs available.</p>
          ) : (
            <div className="space-y-4">
              {state.catalogs.map((catalog) => (
                <section key={catalog.taxonomy_type} className="rounded-lg border p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h2 className="text-sm font-semibold capitalize">{label(catalog.taxonomy_type)}</h2>
                      <p className="text-xs text-muted-foreground">Version {catalog.version}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {catalog.locale_support.map((locale) => (
                        <Badge key={locale} variant="outline">{locale}</Badge>
                      ))}
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    {catalog.categories.map((category) => (
                      <div key={category.category_id} className="rounded-md bg-muted/40 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <strong className="text-sm">{category.label}</strong>
                          <div className="flex gap-1">
                            {category.locked ? <Badge variant="secondary"><Lock className="mr-1 h-3 w-3" />Locked</Badge> : null}
                            {category.status !== "active" ? (
                              <Badge variant={category.status === "proposed" ? "warning" : "outline"}>{category.status}</Badge>
                            ) : null}
                            {category.status === "proposed" && category.confidence != null ? (
                              <Badge variant="outline">
                                {Math.round(category.confidence * 100)}% conf · {category.evidence_count ?? 0} signals
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">{category.description}</p>
                        {category.terms.length > 0 ? (
                          <p className="mt-2 text-xs text-muted-foreground">Terms: {category.terms.slice(0, 5).join(", ")}</p>
                        ) : null}
                        {category.change_history[0] ? (
                          <p className="mt-2 text-xs text-muted-foreground">
                            <GitBranch className="mr-1 inline h-3 w-3" />
                            {category.change_history[0].description}
                          </p>
                        ) : null}
                        {editing?.categoryId === category.category_id &&
                        editing?.type === catalog.taxonomy_type ? (
                          <div className="mt-3 space-y-2">
                            <Input
                              value={renameLabel}
                              onChange={(event) => setRenameLabel(event.target.value)}
                              placeholder="Label"
                              className="h-8 text-sm"
                            />
                            <Input
                              value={renameDescription}
                              onChange={(event) => setRenameDescription(event.target.value)}
                              placeholder="Description (optional)"
                              className="h-8 text-sm"
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={busy || !renameLabel.trim()}
                                onClick={() => submitRename(catalog.taxonomy_type, category.category_id)}
                              >
                                Save
                              </Button>
                              <Button size="sm" variant="ghost" disabled={busy} onClick={() => setEditing(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : category.status === "proposed" ? (
                          <div className="mt-3 flex gap-2">
                            <Button
                              size="sm"
                              disabled={busy}
                              onClick={() => reviewCategory(catalog.taxonomy_type, category.category_id, "accept")}
                            >
                              <Check className="mr-1 h-3 w-3" /> Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busy}
                              onClick={() => reviewCategory(catalog.taxonomy_type, category.category_id, "reject")}
                            >
                              <X className="mr-1 h-3 w-3" /> Reject
                            </Button>
                          </div>
                        ) : (
                          <div className="mt-3 flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busy || category.locked}
                              onClick={() => startRename(catalog.taxonomy_type, category)}
                            >
                              <Pencil className="mr-1 h-3 w-3" /> Rename
                            </Button>
                            {!category.locked ? (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={busy}
                                onClick={() => lockCategory(catalog.taxonomy_type, category.category_id)}
                              >
                                <Lock className="mr-1 h-3 w-3" /> Lock
                              </Button>
                            ) : null}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {catalog.known_limitations.length > 0 ? (
                    <div className="mt-3 rounded-md border border-dashed p-3">
                      <strong className="text-xs uppercase text-muted-foreground">Known limitations</strong>
                      <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {catalog.known_limitations.map((limitation) => (
                          <li key={limitation}>{limitation}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </section>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Languages className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">Terminology Dictionary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {state.terms.length === 0 ? (
            <p className="text-sm text-muted-foreground">No terminology entries available.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {state.terms.map((term) => (
                <div key={term.term_id} className="rounded-lg border p-3">
                  <strong className="text-sm">{term.canonical_term}</strong>
                  <p className="mt-1 text-xs text-muted-foreground">{term.definition}</p>
                  <p className="mt-2 text-xs text-muted-foreground">Aliases: {term.aliases.join(", ") || "none"}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {term.languages.map((language) => (
                      <Badge key={language} variant="outline">{language}</Badge>
                    ))}
                    <Badge variant="secondary">{label(term.taxonomy_type)}</Badge>
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
