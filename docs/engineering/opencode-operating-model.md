# OpenCode Operating Model

This is the version-one Odradek development-governance workflow. It governs agent use; it does not redesign the product.

## Workflow

1. Start from one material GitHub issue.
2. Use one branch and, for future parallel feature work, one isolated linked worktree.
3. Let Odradek Lead inspect evidence and prepare the smallest plan.
4. Human approves the plan before implementation.
5. Odradek Builder is the only normal writing agent.
6. Run deterministic checks before model review.
7. Route ordinary changes to Functional Reviewer.
8. Route privacy, GDPR, Supabase, migration, tenant, logging, AI-governance and workflow-permission concerns to Security, Privacy and Compliance Reviewer first.
9. Human triages review findings.
10. Human controls push, PR creation, merge and deployment.

## One-Writer Rule

Only one agent writes in a worktree. Planning and review agents remain read-only. If a second writer is needed, create a separate branch and linked worktree.

## Branch And Worktree Policy

Do not work directly on `main`. This setup task is approved on `chore/opencode-setup`; future material feature work should use isolated linked worktrees to avoid cross-agent conflicts.

## Model Routing

Default engineering work uses `openai/gpt-5.5` with `high` reasoning. Manually select `xhigh` for difficult architecture, debugging or final synthesis.

If GPT-5.5 xhigh is unavailable, rate-limited or credit-limited, manually select `anthropic/claude-opus-4-8` for high-value work only: architecture, complex debugging, high-risk security review, final adversarial review or difficult cross-system reasoning. Opus is not the routine default.

Functional review uses `anthropic/claude-sonnet-4-6` with `high` reasoning where possible. Use a different model from the implementer when practical.

GDPR, privacy and compliance-sensitive work begins with `mistral/mistral-medium-2604` using `high` reasoning. GPT-5.5 then checks feasibility and repository consistency. Claude Opus 4.8 may be manually requested for high-risk adversarial review.

No OpenCode configuration here performs automatic credit-aware fallback. Fallback is a documented manual switch.

### OpenCode Go Manual Routing

Use OpenCode Go only for task-specific, bounded, lower-risk tasks where frontier reasoning is unnecessary. Manually select it, or assign it to a dedicated economical worker; it is never a substitute for human approval.

- `opencode-go/deepseek-v4-flash` for fast exploration, file locating, code-path summaries, test-failure triage, second opinions and routine review assistance.
- `opencode-go/glm-5.2` for medium bounded implementation, structured code analysis, refactors, test generation, docs linked to code and planning after architecture approval.
- `opencode-go/mimo-v2.5` for UI or multimodal analysis, frontend suggestions, docs and visual consistency checks.
- Other OpenCode Go models require checking exact strengths and metadata first.

Escalate to GPT-5.5 for architecture, multi-system work, unclear assumptions, data contracts, Supabase/Postgres, agent permissions, complex debugging, thesis-critical work or failed attempts. Use Mistral first for GDPR, privacy, compliance, retention, data-subject rights, processors and EU AI Act concerns. Use Opus 4.8 only as manual high-risk adversarial fallback for unresolved difficult work or when GPT-5.5 xhigh is unavailable or credit-limited.

Do not rely on automatic fallback unless OpenCode explicitly supports it. OpenCode Go is never the final authority for security, GDPR, migrations, production architecture or other high-risk changes.

## Compliance Review Boundaries

Compliance review must separate repository evidence, technical controls, legal or regulatory interpretation, assumptions and unresolved human decisions. No model output is an authoritative legal determination.

## Deterministic Checks

Use the narrowest relevant check first:

- `npm run api:test`
- `npm run web:lint`
- `npm run web:build`
- `npm run check`

Run `npm run check` before final review or PR preparation unless there is a documented blocker.

## Review Triage

Review findings need evidence and severity. The human decides which findings are blocking. Do not send speculative findings automatically back to Builder.

## Human Approval Gates

Human approval is required before implementation, dependency installation, lockfile changes, commits, pushes, PR creation, merges, deployment, production database access or production configuration changes.

## Solo And Shared Repository Use

In solo mode, the human may perform final review triage and merge. In shared mode, require another human reviewer for high-risk areas such as migrations, privacy, security, model-provider handling and deployment configuration.

## Limitations

The framework cannot automatically detect model subscription allowance or remaining credit. Static permissions also cannot prove product correctness; deterministic checks and human validation remain required.

## Later Orchestration

Hermes and OpenClaw are postponed. Add orchestration only after the manual OpenCode workflow is reliable.
