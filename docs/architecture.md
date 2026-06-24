# Architecture

## Product Shape

The platform should be built as a governed workflow system, not as a dashboard package.

Core loop:

```text
signals -> problems -> action proposals -> approval -> execution -> outcome learning
```

## Logical Components

```text
Connectors
  Surveys, support, CRM, product analytics, reviews

Signal Store
  Normalized events, feedback text, metadata, evidence snippets

Context Graph
  Customer, account, product, journey, touchpoint, campaign, consent

Problem Engine
  Classification, clustering, impact scoring, root-cause hypotheses

Action Studio
  Structural fix, customer recovery, journey intervention, research task

Governance Engine
  Risk tier, approval rules, policy checks, audit trail, model routing

Execution Connectors
  Jira, Zendesk, HubSpot, Salesforce, Adobe, Braze, ServiceNow

Outcome Learning
  Resolution state, customer closure, metric movement, reusable action memory
```

## Initial Technical Stack

| Layer | Initial Choice |
| --- | --- |
| API | Python, FastAPI |
| Frontend | Next.js, TypeScript |
| Database | SQLite for local workflow state; PostgreSQL later |
| Vector search | pgvector later |
| Workflow | In-process prototype now; Temporal later |
| Model gateway | Provider abstraction later |
| Auth | Local development now; OIDC later |
| Observability | Structured logs now; OpenTelemetry later |

## Early Design Principles

- Every generated claim needs evidence.
- Every customer-facing action needs governance.
- Every approved action needs an outcome contract.
- The system should draft actions before it executes them.
- Integrations should be narrow and high-signal at first.

## Data Boundary

The MVP should store only the fields needed to explain, route, approve, and measure action. It should avoid copying full CRM or analytics datasets unless a customer use case requires it.

## Local Persistence

Seed problem records and policy rules are still loaded from JSON in the prototype. Signal intake, customer context, promoted draft problems and workflow state are durable:

- imported customer signals;
- imported customer/account context;
- promoted draft problems;
- approvals;
- lifecycle transitions;
- draft execution records;
- Jira issue drafts;
- outcome measurements.

The default database file is `apps/api/.data/clara.db`, ignored by git. This is sufficient for local demos and development; a later milestone should move seed problem records, signals, context, promoted drafts and workflow state into PostgreSQL with tenant boundaries.
