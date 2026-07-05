# Runbook — dedicated non-BYPASSRLS `clara_app` role (make tenant RLS enforce)

**Problem.** The API connects as Supabase's `postgres` role, which has `BYPASSRLS = true`.
`BYPASSRLS` overrides `FORCE ROW LEVEL SECURITY`, so the workspace-isolation policies on the
`clara_*` tables are **inert** — a connection with `app.tenant_id = 1` can still read another
workspace's rows. (No impact while there is a single workspace, but the intended isolation
does not actually enforce.)

**Fix (Option A).** Create a `clara_app` role that **can log in, is subject to RLS, and owns
the `clara_*` tables**. The app self-heals its schema on boot with owner-only DDL
(`ALTER`/`CREATE POLICY`/`FORCE`), so the connecting role must own those tables; a non-bypassing
owner under `FORCE` is finally bound by the policies.

**Why scoping to `clara_*` is sufficient.** The FastAPI backend queries **no** non-`clara_`
tables (verified: 0 references to `workspaces`/`user_roles`/`profiles`/`taxonomy_nodes`/…) and
resolves the tenant from the **JWT** (`app_metadata.workspace_id`), not a `workspaces` lookup.
The pg_cron jobs and the `handle_new_user` trigger run as `postgres` / `SECURITY DEFINER` and
are unaffected.

**⚠️ One live-test gate.** Whether Supabase's pooler (Supavisor) accepts `clara_app.<PROJECT_REF>`
as a login. **Run the smoke (step 7) before flipping the deployment (step 8)**; if the login is
rejected, use Option B (a `SET ROLE` change in `PostgresConnectionMixin._connect`) instead.
Keep the rollback ready.

Pooler host for this deployment: `aws-1-eu-central-1.pooler.supabase.com:5432` (EU-Frankfurt).

---

## Steps 1–5 — run in the **Supabase SQL Editor**

The Supabase connection pooler blocks role management (`GRANT role TO …` drops the connection),
so role/ownership changes must go through the SQL Editor (a direct connection), not psql via the
pooler.

```sql
begin;

-- 1) The app role. Replace the password; reuse it in DATABASE_URL (step 6).
create role clara_app login password '<PASSWORD>' nobypassrls;

-- 2) postgres must be a member of clara_app to reassign ownership to it; this also lets the
--    pg_cron jobs (which run as postgres) keep writing the clara_ tables via inheritance.
--    postgres keeps its own BYPASSRLS.
grant clara_app to postgres;

-- 3) clara_app owns the clara_* tables + their id sequences.
--    owner + FORCE + NOBYPASSRLS = RLS binds the app; owner = boot DDL works.
do $$
declare t text;
begin
  for t in select tablename   from pg_tables
           where schemaname='public' and tablename   like 'clara\_%'
  loop execute format('alter table public.%I owner to clara_app', t); end loop;

  for t in select sequencename from pg_sequences
           where schemaname='public' and sequencename like 'clara\_%'
  loop execute format('alter sequence public.%I owner to clara_app', t); end loop;
end $$;

-- 4) Boot schema self-heal runs CREATE TABLE IF NOT EXISTS → needs CREATE on the schema.
grant usage, create on schema public to clara_app;

-- 5) EXECUTE on the functions the policies/app call (PUBLIC by default; explicit for safety).
grant execute on function
  public.is_current_workspace(integer),
  public.current_workspace_id(),
  public.clara_safe_ts(text),
  public.clara_run_due_measurements(integer, timestamptz)
to clara_app;

commit;
```

### Verify the role (after commit, still in the SQL Editor)

```sql
select rolname, rolcanlogin, rolbypassrls from pg_roles where rolname='clara_app';
--   expect: clara_app | t | f

select count(*) as clara_tables_owned
from pg_tables
where schemaname='public' and tablename like 'clara\_%' and tableowner='clara_app';
--   expect: 14
```

---

## Step 6 — update `DATABASE_URL` (deployment env + local `apps/api/.env`)

```
postgresql://clara_app.<PROJECT_REF>:<PASSWORD>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
```

Only the user + password change vs the current `postgres.<PROJECT_REF>` URL. Update local first
for the step-7 test; flip the deployment last.

---

## Step 7 — TEST before trusting production

```bash
cd apps/api
DATABASE_URL='postgresql://clara_app.<PROJECT_REF>:<PASSWORD>@aws-1-eu-central-1.pooler.supabase.com:5432/postgres' \
  python3 scripts/pg_parity_smoke.py
```

- **Pass:** reaches `All N parity checks passed …`, and the `cross-tenant store read hides the
  row` / `raw select as owner is RLS-filtered too (FORCE)` checks now **pass** (they fail as
  `postgres`). That is the proof isolation enforces. The smoke cleans up its own rows.
- **Can't connect** (Supavisor rejects `clara_app.<ref>`): stop, revert local `.env`, use Option B.

---

## Step 8 — flip the deployment + verify live

1. Set the `clara_app` `DATABASE_URL` on the API host (Render/Railway) → redeploy.
2. `curl https://<api-url>/health` → `{"status":"ok"}` (booting confirms the owner DDL ran).
3. Sign in / hit a read endpoint → workspace-1 data loads under the JWT tenant.

---

## Rollback

- **Immediate:** point `DATABASE_URL` back at the `postgres.<PROJECT_REF>` pooler URL, redeploy.
  Returns to prior behavior at once; the role/ownership changes are harmless to leave.
- **Full revert (SQL Editor):** `alter table … owner to postgres` for the `clara_*` tables +
  sequences, then `revoke clara_app from postgres; drop role clara_app;` (revoke its object
  privileges first if `drop role` complains).

---

## Residual notes
- Separate gate: a *usable* second workspace also needs composite entity keys (`signal_id`,
  `problem_id`, `connector_type`… are global PKs). This fix makes isolation *enforce*, not
  second-tenant *usable*.
- If a semantic-taxonomy feature that hits `taxonomy_nodes`/`signal_node_map` is enabled later,
  `clara_app` will need grants on those (it doesn't touch them today).
- `service_role` keeps `BYPASSRLS` for admin/dashboard access — unchanged.
