"use client";

// Dependency-free i18n: a typed dictionary pair (de must structurally match en,
// enforced by the compiler — a missing German key is a build error, so the UI
// can never ship half-translated), a context provider persisting the choice,
// and a small toggle. Domain DATA (feedback text, problem statements) is never
// translated — only the product chrome.

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

const en = {
  nav: {
    dashboard: "Dashboard",
    work: "Work",
    signals: "Signals",
    insights: "Insights",
    actions: "Actions",
    learnings: "Learnings",
    setup: "Setup",
    sources: "Sources",
    integrations: "Integrations",
    taxonomy: "Taxonomy",
    rules: "Rules",
    govern: "Govern",
    compliance: "Compliance",
    settings: "Settings",
    tagline: "Feedback-to-Action Platform",
    signOut: "Sign out",
  },
  common: {
    loading: "Loading…",
    working: "Working…",
    save: "Save",
    cancel: "Cancel",
    accept: "Accept",
    reject: "Reject",
    rename: "Rename",
    lock: "Lock",
    locked: "Locked",
    split: "Split",
    merge: "Merge",
    customers: "customers",
    signals: "signals",
    sources: "sources",
    confidence: "confidence",
    status: "Status",
    owner: "Owner",
  },
  dashboard: {
    overview: "Overview",
    subtitle:
      "The highest-impact customer problems, the actions proposed for them, and whether those actions worked.",
    customersAffected: "Customers affected",
    outcomesMeasured: "Outcomes measured",
    highImpact: "High-Impact Problems",
    highImpactDetail: "total problems in queue",
    governanceBlockers: "Governance Blockers",
    governanceBlockersDetail: "Require policy or privacy decision",
    pendingDecisions: "Pending Decisions",
    pendingDecisionsDetail: "approval decisions recorded",
    outcomesImproving: "Outcomes improving",
    connectors: "Connectors",
    connectorsDetail: "Active integrations",
    signalVolume: "Signal volume (30 days)",
    signalVolumeEmpty: "No timestamped signals yet — import feedback to see the trend.",
    emergingProblems: "Emerging problems",
    emergingEmpty: "No emerging candidates right now.",
    score: "score",
    needsAttention: "Needs attention",
    openInsights: "Open insights",
    outcomes: "Outcomes",
    targetMet: "Target met",
    improving: "Improving",
    notImproved: "Not improved",
    notMeasured: "Not measured",
    workload: "Workload by owner",
    readiness: "Readiness",
    reviewPortfolio: "Review action portfolio",
    headlineNone: "No open problems right now.",
    headlineBlockedOne: "problem needs a decision before work can start.",
    headlineBlockedMany: "problems need a decision before work can start.",
    headlineImprovingOne: "outcome is improving or on target.",
    headlineImprovingMany: "outcomes are improving or on target.",
    headlineTop: "is the highest-impact problem right now.",
    reasonBlocked: "Blocking governance gate",
    reasonReview: "Approval or owner review needed",
    reasonWatch: "customers represented",
    actionTypes: "Action types",
    approved: "Approved",
    draftExecutions: "Draft executions",
    interventionsReady: "Interventions ready",
    measuredPending: "measured, {pending} pending",
    topIssue: "Top issue",
    affected: "affected customers",
    blockedCount: "blocked",
    issues: "issues",
    interventions: "Interventions",
    learningRecords: "Learning records",
    activeConnectors: "Active connectors",
    humanApprovals: "Human approvals",
  },
  insights: {
    title: "Insights",
    subtitle: "AI-synthesized problem insights from customer signals",
    empty: "No insights yet. Run the triage pipeline on signals to generate insights.",
    loadFailed: "Failed to load insights",
    validation: "Validation",
    needsApproval: "Needs Approval",
    inProgress: "In Progress",
    resolved: "Resolved",
    blocked: "Blocked",
    impact: "Impact",
  },
  ask: {
    title: "Ask CLARA",
    subtitle:
      "Answers come only from your feedback signals, with citations and a confidence score — CLARA refuses rather than guesses when the evidence is thin.",
    placeholder: 'e.g. "What are customers saying about refunds?"',
    button: "Ask",
    asking: "Asking…",
    refusedTitle: "Not enough evidence to answer.",
    citations: "Citations",
    match: "match",
    failed: "Question failed.",
  },
  taxonomy: {
    title: "Taxonomy",
    subtitle: "Versioned product, journey, contact-reason, marketing and compliance taxonomy catalogs.",
    bootstrap: "Bootstrap themes from signals",
    hygiene: "Hygiene check",
    hygieneFindings: "Hygiene findings",
    duplicatesSkipped: "Duplicate check skipped — embedding provider unavailable.",
    possibleDuplicates: "Possible duplicates",
    useMergeAbove: "use Merge… above",
    staleProposals: "Stale proposals",
    unreviewedFor: "unreviewed for",
    daysAcceptOrReject: "days — accept or reject below",
    driftingCategories: "Drifting categories",
    driftHint: "no matching signals — update terms, rename, or retire",
    catalogs: "Catalogs",
    activeNodes: "Active Nodes",
    changedNodes: "Changed Nodes",
    lockedNodes: "Locked Nodes",
    version: "Version",
    terms: "Terms",
    cancelMerge: "Cancel merge",
    mergeHint: "Select two or more categories below, then name the merged category.",
    selected: "Selected",
    mergedLabelPlaceholder: "Merged category label",
    descriptionPlaceholder: "Description (optional)",
    mergeCount: "Merge {n} categories",
    splitHint: "Split into two categories (both need a label and description):",
    labelPlaceholder: "Label",
  },
  learnings: {
    title: "Learnings",
    subtitle: "Track whether approved actions improved outcomes and capture reviewed learning conclusions.",
    checkpoints: "Measurement checkpoints",
    checkpointsSubtitle:
      "Scheduled automatically when an action is approved (T+7 and T+window). Signal-derived metrics are measured by CLARA from real data; business metrics become human tasks.",
    runDue: "Run due now",
    running: "Running…",
    noCheckpoints: "No checkpoints yet — approve an action to start the clock.",
    manualNote: "checkpoint(s) waiting for a human-recorded measurement (CLARA never invents values for business metrics).",
    pendingNote: "pending — the background scheduler processes them automatically.",
    t7Check: "T+7 check",
    windowClose: "window close",
    due: "due",
  },
  compliance: {
    title: "Compliance",
    subtitle: "EU AI Act + GDPR assessment for customer feedback AI processing",
    downloadAudit: "Download audit log",
    exporting: "Exporting…",
    overallScore: "Overall Score",
    outOf: "out of 100",
    modelCard: "Model card",
    modelCardSubtitle: "Live configuration of the AI layer — read from the running API",
    model: "Model",
    endpoint: "Inference endpoint",
    apiAuth: "API authentication",
    enabled: "enabled",
    disabledDev: "disabled (dev)",
    configUnavailable: "System config unavailable.",
    residency: "Data residency",
    residencySubtitle: "Where customer data lives and what it never touches",
    rights: "Data-subject rights (GDPR Art. 17 / Art. 20)",
    rightsSubtitle: "Built into the product — no support ticket required",
    exportsBi: "Data exports (BI)",
    exportsBiSubtitle: "Flat CSVs for your own warehouse or BI tool — export, not sync",
    assessment: "Compliance Assessment",
    assessmentSubtitle: "Key requirements for AI-powered customer feedback processing",
    governanceArchitecture: "Governance Architecture",
  },
  outcomeBoard: {
    title: "Outcome Board",
    loading: "Loading outcome board…",
    unavailable: "Outcome board unavailable",
    empty: "No outcome contracts available",
    notMeasured: "Not measured",
    targetMet: "Target met",
    improving: "Improving",
    notImproved: "Not improved",
    higherBetter: "Higher is better",
    lowerBetter: "Lower is better",
    notReviewed: "Not reviewed",
    impact: "Impact",
    metric: "Metric",
    latest: "Latest",
    target: "Target",
    direction: "Direction",
    learning: "Learning",
  },
  settings: {
    title: "Settings",
    subtitle: "Workspace configuration",
    workspace: "Workspace",
    workspaceSubtitle: "General workspace settings",
    workspaceName: "Workspace Name",
    slug: "Slug",
    notificationEmail: "Notification Email",
    saveChanges: "Save Changes",
    saving: "Saving…",
    saved: "Settings saved.",
    saveFailed: "Couldn't save settings.",
    measurement: "Measurement",
    measurementSubtitle: "Outcome measurement defaults",
    windowDays: "Default Measurement Window (days)",
    halfLifeDays: "Learning Half-Life (days)",
    aiConfig: "AI Configuration",
    aiConfigSubtitle: "Provider-agnostic LLM settings — managed via env vars on the API server",
    aiConfigNote: "These are read from the API server's environment and can't be changed here.",
    authLabel: "Authentication",
  },
  actionsPage: {
    title: "Actions",
    subtitle: "Review proposed actions, record decisions and inspect execution history.",
    audienceReadiness: "Audience readiness",
    actionProposals: "Action Proposals",
    executionHistory: "Execution History",
    connectorPipeline: "Connector Pipeline",
    humanApproval: "Human approval",
    triage: "Triage",
    governance: "Governance",
  },
  rulesPage: {
    title: "Rules",
    subtitle: "Automation rules for triage and action routing",
    name: "Name",
    priority: "Priority",
    howItWorks: "How rules are applied",
    ruleOrder1: "Priority — higher priority rules win",
    ruleOrder2: "Specificity — more conditions = more specific",
    ruleOrder3: "Action-type dedupe — one action per type per insight",
  },
} as const;

// Widen literal string types so `de` can hold different strings while the
// compiler still enforces that every key present in `en` exists in `de`.
type Widen<T> = { [K in keyof T]: T[K] extends string ? string : Widen<T[K]> };
type Dict = Widen<typeof en>;

const de: Dict = {
  nav: {
    dashboard: "Übersicht",
    work: "Arbeit",
    signals: "Signale",
    insights: "Erkenntnisse",
    actions: "Maßnahmen",
    learnings: "Learnings",
    setup: "Einrichtung",
    sources: "Quellen",
    integrations: "Integrationen",
    taxonomy: "Taxonomie",
    rules: "Regeln",
    govern: "Governance",
    compliance: "Compliance",
    settings: "Einstellungen",
    tagline: "Feedback-zu-Maßnahme-Plattform",
    signOut: "Abmelden",
  },
  common: {
    loading: "Wird geladen…",
    working: "In Arbeit…",
    save: "Speichern",
    cancel: "Abbrechen",
    accept: "Annehmen",
    reject: "Ablehnen",
    rename: "Umbenennen",
    lock: "Sperren",
    locked: "Gesperrt",
    split: "Aufteilen",
    merge: "Zusammenführen",
    customers: "Kund:innen",
    signals: "Signale",
    sources: "Quellen",
    confidence: "Konfidenz",
    status: "Status",
    owner: "Verantwortlich",
  },
  dashboard: {
    overview: "Übersicht",
    subtitle:
      "Die Kundenprobleme mit dem größten Impact, die vorgeschlagenen Maßnahmen — und ob sie gewirkt haben.",
    customersAffected: "Betroffene Kund:innen",
    outcomesMeasured: "Gemessene Ergebnisse",
    highImpact: "Probleme mit hohem Impact",
    highImpactDetail: "Probleme insgesamt in der Warteschlange",
    governanceBlockers: "Governance-Blocker",
    governanceBlockersDetail: "Erfordern Richtlinien- oder Datenschutzentscheidung",
    pendingDecisions: "Offene Entscheidungen",
    pendingDecisionsDetail: "Freigabeentscheidungen erfasst",
    outcomesImproving: "Ergebnisse verbessern sich",
    connectors: "Konnektoren",
    connectorsDetail: "Aktive Integrationen",
    signalVolume: "Signalvolumen (30 Tage)",
    signalVolumeEmpty: "Noch keine Signale mit Zeitstempel — Feedback importieren, um den Trend zu sehen.",
    emergingProblems: "Aufkommende Probleme",
    emergingEmpty: "Derzeit keine aufkommenden Kandidaten.",
    score: "Score",
    needsAttention: "Braucht Aufmerksamkeit",
    openInsights: "Erkenntnisse öffnen",
    outcomes: "Ergebnisse",
    targetMet: "Ziel erreicht",
    improving: "Verbessert sich",
    notImproved: "Nicht verbessert",
    notMeasured: "Nicht gemessen",
    workload: "Auslastung nach Verantwortlichen",
    readiness: "Bereitschaft",
    reviewPortfolio: "Maßnahmenportfolio prüfen",
    headlineNone: "Derzeit keine offenen Probleme.",
    headlineBlockedOne: "Problem braucht eine Entscheidung, bevor die Arbeit starten kann.",
    headlineBlockedMany: "Probleme brauchen eine Entscheidung, bevor die Arbeit starten kann.",
    headlineImprovingOne: "Ergebnis verbessert sich oder liegt im Ziel.",
    headlineImprovingMany: "Ergebnisse verbessern sich oder liegen im Ziel.",
    headlineTop: "ist aktuell das Problem mit dem größten Impact.",
    reasonBlocked: "Blockierendes Governance-Gate",
    reasonReview: "Freigabe oder Prüfung durch Verantwortliche nötig",
    reasonWatch: "Kund:innen betroffen",
    actionTypes: "Maßnahmentypen",
    approved: "Freigegeben",
    draftExecutions: "Entwurfs-Ausführungen",
    interventionsReady: "Interventionen bereit",
    measuredPending: "gemessen, {pending} ausstehend",
    topIssue: "Top-Thema",
    affected: "betroffene Kund:innen",
    blockedCount: "blockiert",
    issues: "Themen",
    interventions: "Interventionen",
    learningRecords: "Learning-Einträge",
    activeConnectors: "Aktive Konnektoren",
    humanApprovals: "Menschliche Freigaben",
  },
  insights: {
    title: "Erkenntnisse",
    subtitle: "KI-synthetisierte Problem-Erkenntnisse aus Kundensignalen",
    empty: "Noch keine Erkenntnisse. Triage-Pipeline auf Signalen ausführen, um Erkenntnisse zu erzeugen.",
    loadFailed: "Erkenntnisse konnten nicht geladen werden",
    validation: "Validierung",
    needsApproval: "Freigabe nötig",
    inProgress: "In Bearbeitung",
    resolved: "Gelöst",
    blocked: "Blockiert",
    impact: "Impact",
  },
  ask: {
    title: "CLARA fragen",
    subtitle:
      "Antworten stammen ausschließlich aus Ihren Feedback-Signalen — mit Quellenangaben und Konfidenz. Bei dünner Evidenz lehnt CLARA ab, statt zu raten.",
    placeholder: 'z. B. „Was sagen Kund:innen über Rückerstattungen?“',
    button: "Fragen",
    asking: "Wird gefragt…",
    refusedTitle: "Nicht genug Evidenz für eine Antwort.",
    citations: "Quellen",
    match: "Übereinstimmung",
    failed: "Anfrage fehlgeschlagen.",
  },
  taxonomy: {
    title: "Taxonomie",
    subtitle: "Versionierte Kataloge für Produkt, Journey, Kontaktgrund, Marketing und Compliance.",
    bootstrap: "Themen aus Signalen ableiten",
    hygiene: "Hygiene-Check",
    hygieneFindings: "Hygiene-Befunde",
    duplicatesSkipped: "Duplikatprüfung übersprungen — Embedding-Dienst nicht verfügbar.",
    possibleDuplicates: "Mögliche Duplikate",
    useMergeAbove: "oben über „Zusammenführen…“ lösen",
    staleProposals: "Liegengebliebene Vorschläge",
    unreviewedFor: "ungeprüft seit",
    daysAcceptOrReject: "Tagen — unten annehmen oder ablehnen",
    driftingCategories: "Driftende Kategorien",
    driftHint: "keine passenden Signale — Begriffe anpassen, umbenennen oder ausmustern",
    catalogs: "Kataloge",
    activeNodes: "Aktive Knoten",
    changedNodes: "Geänderte Knoten",
    lockedNodes: "Gesperrte Knoten",
    version: "Version",
    terms: "Begriffe",
    cancelMerge: "Zusammenführen abbrechen",
    mergeHint: "Zwei oder mehr Kategorien auswählen, dann die neue Kategorie benennen.",
    selected: "Ausgewählt",
    mergedLabelPlaceholder: "Name der zusammengeführten Kategorie",
    descriptionPlaceholder: "Beschreibung (optional)",
    mergeCount: "{n} Kategorien zusammenführen",
    splitHint: "In zwei Kategorien aufteilen (beide brauchen Name und Beschreibung):",
    labelPlaceholder: "Name",
  },
  learnings: {
    title: "Learnings",
    subtitle: "Verfolgen, ob freigegebene Maßnahmen die Ergebnisse verbessert haben, und geprüfte Schlussfolgerungen festhalten.",
    checkpoints: "Mess-Checkpoints",
    checkpointsSubtitle:
      "Automatisch geplant bei Freigabe einer Maßnahme (T+7 und T+Fenster). Signalbasierte Metriken misst CLARA aus echten Daten; Geschäftsmetriken werden zu Aufgaben für Menschen.",
    runDue: "Fällige jetzt ausführen",
    running: "Läuft…",
    noCheckpoints: "Noch keine Checkpoints — eine Maßnahme freigeben, um die Uhr zu starten.",
    manualNote: "Checkpoint(s) warten auf eine von Menschen erfasste Messung (CLARA erfindet niemals Werte für Geschäftsmetriken).",
    pendingNote: "ausstehend — der Hintergrund-Scheduler verarbeitet sie automatisch.",
    t7Check: "T+7-Prüfung",
    windowClose: "Fensterschluss",
    due: "fällig",
  },
  compliance: {
    title: "Compliance",
    subtitle: "EU-AI-Act- und DSGVO-Bewertung für KI-gestützte Feedback-Verarbeitung",
    downloadAudit: "Audit-Log herunterladen",
    exporting: "Wird exportiert…",
    overallScore: "Gesamtwert",
    outOf: "von 100",
    modelCard: "Modellkarte",
    modelCardSubtitle: "Live-Konfiguration der KI-Schicht — direkt aus der laufenden API",
    model: "Modell",
    endpoint: "Inferenz-Endpunkt",
    apiAuth: "API-Authentifizierung",
    enabled: "aktiviert",
    disabledDev: "deaktiviert (Dev)",
    configUnavailable: "Systemkonfiguration nicht verfügbar.",
    residency: "Datenresidenz",
    residencySubtitle: "Wo Kundendaten liegen — und was sie nie berühren",
    rights: "Betroffenenrechte (DSGVO Art. 17 / Art. 20)",
    rightsSubtitle: "Im Produkt eingebaut — kein Support-Ticket nötig",
    exportsBi: "Datenexporte (BI)",
    exportsBiSubtitle: "Flache CSVs für Ihr eigenes Warehouse oder BI-Tool — Export, kein Sync",
    assessment: "Compliance-Bewertung",
    assessmentSubtitle: "Zentrale Anforderungen an KI-gestützte Feedback-Verarbeitung",
    governanceArchitecture: "Governance-Architektur",
  },
  outcomeBoard: {
    title: "Ergebnis-Board",
    loading: "Ergebnis-Board wird geladen…",
    unavailable: "Ergebnis-Board nicht verfügbar",
    empty: "Keine Ergebnis-Kontrakte vorhanden",
    notMeasured: "Nicht gemessen",
    targetMet: "Ziel erreicht",
    improving: "Verbessert sich",
    notImproved: "Nicht verbessert",
    higherBetter: "Höher ist besser",
    lowerBetter: "Niedriger ist besser",
    notReviewed: "Nicht geprüft",
    impact: "Impact",
    metric: "Metrik",
    latest: "Aktuell",
    target: "Ziel",
    direction: "Richtung",
    learning: "Learning",
  },
  settings: {
    title: "Einstellungen",
    subtitle: "Workspace-Konfiguration",
    workspace: "Workspace",
    workspaceSubtitle: "Allgemeine Workspace-Einstellungen",
    workspaceName: "Workspace-Name",
    slug: "Kürzel",
    notificationEmail: "Benachrichtigungs-E-Mail",
    saveChanges: "Änderungen speichern",
    saving: "Wird gespeichert…",
    saved: "Einstellungen gespeichert.",
    saveFailed: "Einstellungen konnten nicht gespeichert werden.",
    measurement: "Messung",
    measurementSubtitle: "Standardwerte für die Ergebnismessung",
    windowDays: "Standard-Messfenster (Tage)",
    halfLifeDays: "Learning-Halbwertszeit (Tage)",
    aiConfig: "KI-Konfiguration",
    aiConfigSubtitle: "Anbieterunabhängige LLM-Einstellungen — verwaltet über Env-Variablen des API-Servers",
    aiConfigNote: "Diese Werte stammen aus der Server-Umgebung und können hier nicht geändert werden.",
    authLabel: "Authentifizierung",
  },
  actionsPage: {
    title: "Maßnahmen",
    subtitle: "Vorgeschlagene Maßnahmen prüfen, Entscheidungen erfassen und die Ausführungshistorie einsehen.",
    audienceReadiness: "Zielgruppen-Bereitschaft",
    actionProposals: "Maßnahmenvorschläge",
    executionHistory: "Ausführungshistorie",
    connectorPipeline: "Konnektor-Pipeline",
    humanApproval: "Menschliche Freigabe",
    triage: "Triage",
    governance: "Governance",
  },
  rulesPage: {
    title: "Regeln",
    subtitle: "Automatisierungsregeln für Triage und Maßnahmen-Routing",
    name: "Name",
    priority: "Priorität",
    howItWorks: "So werden Regeln angewendet",
    ruleOrder1: "Priorität — Regeln mit höherer Priorität gewinnen",
    ruleOrder2: "Spezifität — mehr Bedingungen = spezifischer",
    ruleOrder3: "Maßnahmentyp-Dedupe — eine Maßnahme pro Typ und Erkenntnis",
  },
};

const DICTIONARIES: Record<"en" | "de", Dict> = { en, de };
export type Locale = keyof typeof DICTIONARIES;
const STORAGE_KEY = "clara_locale";

type I18nContextValue = { locale: Locale; t: Dict; setLocale: (locale: Locale) => void };

const I18nContext = createContext<I18nContextValue>({
  locale: "en",
  t: en,
  setLocale: () => undefined,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "de" || stored === "en") setLocaleState(stored);
    } catch {
      // localStorage unavailable — stay on the default
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // non-fatal
    }
  }, []);

  return (
    <I18nContext.Provider value={{ locale, t: DICTIONARIES[locale], setLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  return useContext(I18nContext);
}

export function LanguageToggle() {
  const { locale, setLocale } = useI18n();
  return (
    <div className="flex items-center rounded-md border text-xs font-medium" role="group" aria-label="Language">
      {(["en", "de"] as const).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => setLocale(option)}
          className={
            "px-2 py-1 uppercase transition-colors " +
            (locale === option
              ? "bg-primary text-primary-foreground rounded-[5px]"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          {option}
        </button>
      ))}
    </div>
  );
}
