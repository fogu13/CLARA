-- Init script: enable extensions on first boot.
-- Mounted into /docker-entrypoint-initdb.d/ by docker-compose.supabase.yml.

-- pgvector: semantic search for taxonomy mapping + signal embedding
CREATE EXTENSION IF NOT EXISTS vector;

-- pg_cron: scheduled tasks (taxonomy governance, outcome measurement)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- pg_net: DB -> HTTP calls (trigger FastAPI agent service asynchronously)
CREATE EXTENSION IF NOT EXISTS pg_net;
