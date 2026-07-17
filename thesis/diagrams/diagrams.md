# Thesis Diagrams

All diagrams are **Mermaid** (plain text, edit anywhere). This file renders in Obsidian and GitHub. Each block is also a standalone `.mmd` file; PNG/SVG renders live in `rendered/`. The data model also ships as runnable Postgres DDL in `schema.sql`.


## Figure A — Logical system architecture (build-agnostic)

*source: `01_architecture_logical.mmd`*

```mermaid
flowchart LR
    subgraph SRC["Feedback sources (integrate, not rebuild)"]
        S1["Surveys<br/>NPS / CSAT / CES"]
        S2["Support<br/>Zendesk / Intercom"]
        S3["Reviews and social"]
        S4["Product analytics"]
    end

    subgraph ING["Ingestion"]
        I1["CSV / Webhook / Connectors"]
    end

    subgraph CORE["Governed loop · Signal to Insight to Action to Learning"]
        E["Enrichment<br/>sentiment · theme · urgency"]
        SY["Synthesis<br/>cross-signal severity"]
        R["Action engine<br/>rules · conflict resolution"]
        AP{"Human approval?"}
        EX["Execute action"]
        M["Measurement<br/>outcome contract · closure"]
        L["Learning store<br/>confidence decay"]
    end

    subgraph OUT["Execution targets (integrate)"]
        O1["Jira / Zendesk / CRM"]
    end

    subgraph GOV["Responsible-AI governance (cross-cutting)"]
        G1["Audit · Art 12"]
        G2["Transparency · Art 50"]
        G3["Compliance checker"]
        G4["Model sovereignty"]
    end

    S1 --> I1
    S2 --> I1
    S3 --> I1
    S4 --> I1
    I1 --> E --> SY --> R --> AP
    AP -->|"approved or auto"| EX
    AP -->|"queued"| EX
    EX --> O1
    EX --> M --> L
    L -.->|"informs"| R
    G1 -.-> EX
    G2 -.-> E
    G3 -.-> R
    G4 -.-> E
```


## Figure B — (retired) Odradek prototype architecture

*The earlier React/Vite + Supabase implementation was superseded in July 2026 when the manuscript settled on CLARA. Its diagram source and renders are archived in `../archive/odradek/`.*


## Figure C — Implementation: CLARA (Next.js + FastAPI + LangGraph)

*source: `03_architecture_clara.mmd`*

```mermaid
flowchart TB
    subgraph FE["Frontend · Vercel"]
        UI["Next.js + TypeScript<br/>shadcn/ui · Tailwind"]
    end

    subgraph API["Backend · Docker on an EU VPS (Caddy reverse proxy)"]
        FAST["FastAPI (Python)<br/>~43 REST endpoints"]
        subgraph LG["LangGraph orchestration"]
            N1["enrich node"]
            N2["synthesize node"]
            N3["evaluate-rules node"]
            INT{{"interrupt:<br/>human approval · Art 14"}}
            N4["execute node"]
            N5["measure node"]
            N6["learning node"]
        end
    end

    subgraph DATA["Data"]
        DB[("PostgreSQL + pgvector<br/>signals · insights · rules<br/>actions_log · outcome_* · ab_learnings · events")]
    end

    AI["ai.py · provider-agnostic LLM<br/>hosted or self-hosted (Ollama/vLLM)"]
    OBS["Langfuse<br/>LLM tracing / observability"]
    CONN["Connectors<br/>Zendesk · Jira · Slack · HubSpot"]

    UI --> FAST --> LG
    LG --> DB
    N1 & N2 & N6 --> AI
    LG --> OBS
    N3 --> INT --> N4 --> CONN
    N4 --> N5 --> N6
    N6 -. retrieval (pgvector) .-> N3
```


## Figure D — Data pipeline: Signal → Insight → Action → Learning

*source: `04_pipeline_flow.mmd`*

```mermaid
flowchart TD
    A["Raw signal<br/>(qualitative or quantitative)"] --> B["Enrich<br/>sentiment · theme · urgency · evidence<br/>+ PII masking"]
    B --> C["Map to taxonomy<br/>category → theme → subtheme"]
    C --> D["Synthesise insight<br/>cluster signals · composite cross-signal severity"]
    D --> E["Match rules<br/>priority → specificity → action-type dedupe"]
    E --> F{"Risk gate<br/>auto_execute?"}
    F -->|"true (low risk)"| H["Execute action"]
    F -->|"false (needs oversight)"| G["Approval queue<br/>human-in-the-loop · Art 14"]
    G -->|approve| H
    G -->|reject| X["Logged · no action"]
    H --> I["Write audit record<br/>params · executor · result · Art 12"]
    I --> J["Measure outcome<br/>vs contract · operational/customer/outcome closure"]
    J --> K{"Resolved?"}
    K -->|yes| L["Codify learning<br/>confidence + half-life"]
    K -->|no| E
    L -->|"decayed-confidence retrieval"| E

    classDef gov fill:#fde2e2,stroke:#c0392b,color:#7b1f1f;
    classDef llm fill:#e2ecfd,stroke:#3b6ea5,color:#1f3b5b;
    class G,I gov;
    class B,D llm;
```


## Figure E — Signal lifecycle with human-in-the-loop approval

*source: `05_sequence_hitl.mmd`*

```mermaid
sequenceDiagram
    autonumber
    actor Cust as Customer
    participant Src as Source (survey/ticket/review)
    participant Ing as Ingestion
    participant LLM as Enrichment (LLM)
    participant Eng as Action engine (rules)
    actor Op as Practitioner
    participant Sys as Execution + audit
    participant Meas as Measurement
    participant Mem as Learning store

    Cust->>Src: leaves feedback
    Src->>Ing: signal (CSV / webhook)
    Ing->>LLM: enrich (sentiment, theme, urgency)
    LLM->>Eng: insight + composite severity
    Eng->>Eng: match rules, resolve conflicts
    alt auto_execute = false (risk)
        Eng->>Op: queue for approval (Art 14)
        Op-->>Eng: approve / reject
    else auto_execute = true
        Note over Eng: proceed automatically
    end
    Eng->>Sys: execute action
    Sys->>Sys: write audit record (Art 12)
    Sys->>Meas: set outcome contract + window
    Meas-->>Meas: re-measure after window
    Meas->>Mem: codify learning (confidence + half-life)
    Mem-->>Eng: retrieved on next similar decision
```


## Figure F — Data model (ER); runnable DDL in schema.sql

*source: `06_data_model_er.mmd`*

```mermaid
erDiagram
    WORKSPACES ||--o{ SIGNALS : owns
    WORKSPACES ||--o{ TAXONOMY_NODES : owns
    WORKSPACES ||--o{ FEEDBACK_RULES : owns
    WORKSPACES ||--o{ INSIGHTS : owns
    WORKSPACES ||--o{ EVENTS : logs

    TAXONOMY_NODES ||--o{ TAXONOMY_NODES : "parent of"
    SIGNALS }o--o{ TAXONOMY_NODES : "mapped via SIGNAL_NODE_MAP"
    SIGNALS }o--o{ INSIGHTS : "clustered via INSIGHT_SIGNALS"

    INSIGHTS ||--o{ ACTIONS_LOG : triggers
    FEEDBACK_RULES ||--o{ ACTIONS_LOG : fires
    ACTIONS_LOG ||--|| OUTCOME_CONTRACTS : "binds at creation"
    OUTCOME_CONTRACTS ||--o{ OUTCOME_MEASUREMENTS : "measured by"
    INSIGHTS ||--o{ AB_LEARNINGS : "produces / informs"

    SIGNALS {
        uuid id PK
        uuid workspace_id FK
        text signal_type
        text source
        text category
        text text_content
        text original_language
        text metric_name
        numeric metric_value
        text sentiment
        text urgency
        timestamptz recorded_at
    }
    INSIGHTS {
        uuid id PK
        uuid workspace_id FK
        text title
        text severity_band
        numeric severity_score
        text status
    }
    FEEDBACK_RULES {
        uuid id PK
        uuid workspace_id FK
        int priority
        jsonb conditions
        text action_type
        bool auto_execute
    }
    ACTIONS_LOG {
        uuid id PK
        uuid insight_id FK
        uuid rule_id FK
        text status
        text executor
        jsonb params
        jsonb result
        timestamptz created_at
    }
    OUTCOME_CONTRACTS {
        uuid id PK
        uuid action_id FK
        text metric
        numeric baseline
        int window_days
        timestamptz measurement_due_at
    }
    OUTCOME_MEASUREMENTS {
        uuid id PK
        uuid contract_id FK
        numeric value
        numeric resolution_score
        text closure_level
    }
    AB_LEARNINGS {
        uuid id PK
        uuid workspace_id FK
        text conclusion
        numeric base_confidence
        timestamptz last_validated_at
        int half_life_days
    }
    TAXONOMY_NODES {
        uuid id PK
        uuid workspace_id FK
        uuid parent_id FK
        int level
        text label
        numeric confidence
        int half_life_days
    }
    EVENTS {
        uuid id PK
        uuid workspace_id FK
        text type
        jsonb payload
        timestamptz created_at
    }
```


## Figure G — Real-data gold-set evaluation harness (Ch 5 §5A)

*source: `07_evaluation_pipeline.mmd`*

```mermaid
flowchart LR
    subgraph DATA["Real public datasets (Thesis_ChatGPT/)"]
        D1["Trade Republic · 67 · fintech · EN"]
        D2["Henkel · 39 · B2B industrial · DE"]
        D3["Lieferando · 82 · food delivery · DE/EN"]
    end
    GOLD["Gold labels (human seeds)<br/>theme · journey_stage · owner · action · risk · star"]
    D1 & D2 & D3 --> LOAD["load_datasets.py<br/>188 labelled signals"]
    LOAD --> GOLD

    subgraph PRED["Predictors (same gold labels)"]
        P1["Rule-based floor<br/>lexicon + keywords"]
        P2["Classical ML<br/>TF-IDF + LogReg · 5-fold CV"]
        P3["LLM enrichment path<br/>artifact's enrich-signal (needs API key)"]
    end
    LOAD --> P1 & P2 & P3

    P1 & P2 & P3 --> METR["metrics.py<br/>P/R/F1 · confusion · per sector/language"]
    GOLD --> METR
    METR --> RES["results/*.csv + figures + summary.json"]

    classDef pending fill:#f3f3f3,stroke:#999,color:#555,stroke-dasharray:4 3;
    class P3 pending;
```


## Figure H — Design Science Research method (Hevner cycles + DSRM)

*source: `08_dsr_method.mmd`*

```mermaid
flowchart LR
    subgraph ENV["Environment (Relevance)"]
        E1["Feedback-to-action gap<br/>practitioners · VoC practice"]
        E2["EU regulatory context<br/>EU AI Act · GDPR"]
    end
    subgraph DS["Design Science (Design cycle)"]
        B["Build<br/>artifact + 5 design decisions"]
        EV["Evaluate<br/>gold-set (RQ3) + practitioner study (RQ4)"]
        B <--> EV
    end
    subgraph KB["Knowledge base (Rigour)"]
        K1["VoC · NLP · BI · workflow · org learning"]
        K2["DSR methodology<br/>Hevner 2004 · Peffers 2007 · Gregor & Hevner 2013"]
        K3["Responsible-AI literature"]
    end

    ENV -->|"requirements / field test"| DS
    DS -->|"design principles + artifact"| ENV
    KB -->|"grounding"| DS
    DS -->|"additions to the knowledge base"| KB

    subgraph DSRM["DSRM activities (Peffers et al., 2007)"]
        A1["1 Problem"] --> A2["2 Objectives"] --> A3["3 Design & develop"] --> A4["4 Demonstrate"] --> A5["5 Evaluate"] --> A6["6 Communicate"]
    end
```
