# CLARA Agent Rules

CLARA is a governed customer-feedback intelligence and orchestration product. Preserve evidence, confidence, limitations and auditability. Consequential execution starts as draft-plus-human-approval; do not make this a chat-first analytics product, autonomous customer-contact system, CDP or campaign-delivery platform.

Repository shape: `apps/web` is the Next.js frontend, `apps/api` is the FastAPI backend, `apps/api/migrations` contains PostgreSQL/Supabase-compatible persistence, `apps/api/app/tests` contains API tests, and `docs` contains product and architecture context.

Authoritative checks:

- `npm run api:test`
- `npm run web:lint`
- `npm run web:build`
- `npm run check`

Git rules: future material feature work uses one GitHub issue, one branch and one isolated linked worktree. Only one writing agent works in a worktree. Never work directly on `main`. Agents do not push, merge or deploy by default.

Scope rules: make the smallest approved change, avoid unrelated refactors, distinguish repository evidence from assumptions, and stop when an approved plan's assumption proves false.

Security and data rules: never read or disclose secrets, minimise personal data, treat customer feedback as potentially sensitive, treat model output as untrusted, preserve approval boundaries, never weaken tenant isolation or future RLS controls, and never modify an existing production migration casually.

Definition of done: acceptance criteria met, deterministic checks pass, relevant independent review completed, human validation completed, and no unresolved blocking findings.

See `docs/engineering/opencode-operating-model.md` for the full OpenCode workflow.
