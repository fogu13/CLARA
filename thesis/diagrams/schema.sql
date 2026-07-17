-- Core data model — runnable, modifiable Postgres DDL (matches diagrams/06_data_model_er.mmd).
-- CLARA data model (Postgres + pgvector).
-- Multi-tenant by construction: every domain row carries workspace_id and is protected by RLS.
-- pgvector columns power semantic retrieval; the token-overlap fallback works without them.

create extension if not exists "pgcrypto";   -- gen_random_uuid()
-- create extension if not exists vector;     -- enable for CLARA / semantic retrieval

create table workspaces (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    created_at  timestamptz not null default now()
);

create table users (
    id            uuid primary key default gen_random_uuid(),
    workspace_id  uuid not null references workspaces(id) on delete cascade,
    email         text not null,
    role          text not null default 'member',   -- owner | admin | member | viewer
    unique (workspace_id, email)
);

-- Adaptive taxonomy: category -> theme -> subtheme, self-improving with decay.
create table taxonomy_nodes (
    id              uuid primary key default gen_random_uuid(),
    workspace_id    uuid not null references workspaces(id) on delete cascade,
    parent_id       uuid references taxonomy_nodes(id) on delete set null,
    level           int  not null check (level between 1 and 3),
    label           text not null,
    confidence      numeric not null default 0.5,
    last_validated_at timestamptz not null default now(),
    half_life_days  int  not null default 180
    -- , embedding vector(1536)   -- CLARA: hybrid matching
);

create table signals (
    id               uuid primary key default gen_random_uuid(),
    workspace_id     uuid not null references workspaces(id) on delete cascade,
    signal_type      text not null,             -- nps_survey | support_ticket | app_review | page_analytics | ...
    source           text,
    category         text,                      -- feedback | behavior | performance | sentiment
    text_content     text,
    original_language text,
    metric_name      text,                      -- quantitative signals
    metric_value     numeric,
    sentiment        text check (sentiment in ('negative','neutral','positive','mixed') or sentiment is null),
    sentiment_score  numeric,
    urgency          text check (urgency in ('low','medium','high','critical') or urgency is null),
    tags             jsonb not null default '[]',
    source_url       text,
    recorded_at      timestamptz,
    ingested_at      timestamptz not null default now()
    -- , embedding vector(1536)   -- CLARA: clustering / retrieval
);

create table signal_node_map (
    signal_id  uuid not null references signals(id) on delete cascade,
    node_id    uuid not null references taxonomy_nodes(id) on delete cascade,
    confidence numeric,
    primary key (signal_id, node_id)
);

create table insights (
    id             uuid primary key default gen_random_uuid(),
    workspace_id   uuid not null references workspaces(id) on delete cascade,
    title          text not null,
    severity_band  text check (severity_band in ('low','medium','high','critical')),
    severity_score numeric,        -- composite cross-signal severity (DP3)
    status         text not null default 'open',
    created_at     timestamptz not null default now()
);

create table insight_signals (   -- many-to-many: an insight is corroborated by many signals
    insight_id uuid not null references insights(id) on delete cascade,
    signal_id  uuid not null references signals(id) on delete cascade,
    primary key (insight_id, signal_id)
);

create table feedback_rules (
    id            uuid primary key default gen_random_uuid(),
    workspace_id  uuid not null references workspaces(id) on delete cascade,
    name          text not null,
    priority      int  not null default 100,    -- DP4: resolution by priority -> specificity -> action-type
    conditions    jsonb not null default '{}',
    action_type   text not null,
    auto_execute  boolean not null default false, -- DP4 / Art 14: false => human approval
    enabled       boolean not null default true
);

create table actions_log (
    id            uuid primary key default gen_random_uuid(),
    workspace_id  uuid not null references workspaces(id) on delete cascade,
    insight_id    uuid references insights(id) on delete set null,
    rule_id       uuid references feedback_rules(id) on delete set null,
    action_type   text not null,
    status        text not null default 'pending_approval', -- pending_approval | approved | executed | rejected | failed
    executor      text,                                     -- 'system_auto' | user id (Art 12 audit)
    params        jsonb not null default '{}',
    result        jsonb,
    retention_expires_at timestamptz,                       -- GDPR storage limitation
    created_at    timestamptz not null default now()
);

create table outcome_contracts (         -- DP1: closure is a contract, created WITH the action
    id                 uuid primary key default gen_random_uuid(),
    action_id          uuid not null references actions_log(id) on delete cascade,
    metric             text not null,
    baseline           numeric,
    window_days        int not null default 14,
    measurement_due_at timestamptz not null
);

create table outcome_measurements (
    id               uuid primary key default gen_random_uuid(),
    contract_id      uuid not null references outcome_contracts(id) on delete cascade,
    value            numeric,
    resolution_score numeric,
    closure_level    text check (closure_level in ('operational','customer','outcome')),
    measured_at      timestamptz not null default now()
);

create table ab_learnings (              -- DP2: perishable organisational memory
    id                uuid primary key default gen_random_uuid(),
    workspace_id      uuid not null references workspaces(id) on delete cascade,
    conclusion        text not null,
    base_confidence   numeric not null default 0.5,
    last_validated_at timestamptz not null default now(),
    half_life_days    int not null default 365,
    created_at        timestamptz not null default now()
    -- , embedding vector(1536)   -- CLARA: semantic retrieval (DP "relevant past-learnings")
);

create table events (                    -- evaluation telemetry (time-to-action, approvals, retrieval)
    id           uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references workspaces(id) on delete cascade,
    type         text not null,
    payload      jsonb not null default '{}',
    created_at   timestamptz not null default now()
);

-- Decayed confidence (DP2), computed on read rather than stored:
--   confidence_now = base_confidence * power(0.5, extract(epoch from (now() - last_validated_at))
--                                                  / (half_life_days * 86400));

-- Row-Level Security: enable on every domain table and scope to the caller's workspace, e.g.
--   alter table signals enable row level security;
--   create policy ws_isolation on signals
--     using (workspace_id = current_setting('app.workspace_id')::uuid);
