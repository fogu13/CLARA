"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tags, Lock, GitBranch, Languages } from "lucide-react";
import { getLanguageQuality, getTaxonomies, getTerminologyDictionary } from "@/lib/client-api";
import type { LanguageQualityReport, TaxonomyCatalog, TerminologyDictionaryEntry } from "@/lib/types";

type TaxonomyState = {
  status: "loading" | "ready" | "error";
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
      } catch (error) {
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Could not load taxonomies.",
          catalogs: [],
          terms: []
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
        <h1 className="text-2xl font-bold">Taxonomy</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Versioned product, journey, contact-reason, marketing and compliance taxonomy catalogs.
        </p>
      </div>

      {state.status === "error" ? <div className="text-sm text-destructive">{state.message}</div> : null}

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
                            {category.status !== "active" ? <Badge variant="outline">{category.status}</Badge> : null}
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
