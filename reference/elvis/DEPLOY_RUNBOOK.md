# Odradek — Deploy Runbook (get it live)

Run these to take the platform from "builds locally" to "running in your Supabase project."
Project ref: `zknvmcylnhkpfucxsmxs` (from `.env`).

## 0. Prerequisites
```bash
npm i -g supabase        # Supabase CLI
supabase login
```
Have an AI provider key ready (OpenAI, Google AI Studio, Groq, …) or a local model.

## 1. Database (migrations + seed)
```bash
supabase link --project-ref zknvmcylnhkpfucxsmxs
supabase db push          # applies the 5 new migrations in order
```
Then **sign up in the app once** (so your workspace exists), and run the seed:
- Supabase dashboard → SQL Editor → paste `supabase/seed.sql` → Run.

## 2. AI secrets (pick one provider)
```bash
# OpenAI (default base/model)
supabase secrets set AI_API_KEY=sk-xxxx AI_BASE_URL=https://api.openai.com/v1 AI_MODEL=gpt-4o-mini

# …or Google Gemini (same model the app shipped with)
# supabase secrets set AI_API_KEY=<google-key> AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai AI_MODEL=gemini-2.5-flash

supabase secrets unset LOVABLE_API_KEY   # old, unused
```

## 3. Deploy edge functions
```bash
for fn in evaluate-rules measure-outcomes extract-learnings enrich-signal synthesize-insights sync-source check-compliance; do
  supabase functions deploy $fn
done
supabase functions deploy ingest-webhook --no-verify-jwt   # public endpoint
```

## 4. Auth (optional)
Supabase dashboard → Authentication → Providers → **Google** → add client ID/secret + redirect URL.
(Email/password works without this.)

## 5. Run + smoke-test
```bash
npm run dev      # http://localhost:8080
```
- Log in. Screens populate after the seed (step 1).
- **Signals → Import** → upload `signals_sample.csv` → **Analyze** (enrich + synthesize).
- **Insights** → open one → **Run Rules** (watch conflict resolution) → **Measure now**.
- **Actions** → approve a pending action.
- **Learnings** → search + **Extract Learnings**.
- **Compliance** → run a check.

## 6. Merge
Review PR #1 → **Merge** to `main`.

## Troubleshooting
- Function 500 → `AI_*` secret missing/wrong, or check Supabase → Edge Functions → Logs.
- Empty screens → seed didn't run, or you're in a different workspace.
- `column … does not exist` → a migration didn't apply; re-run `supabase db push`.
