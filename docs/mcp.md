# CLARA MCP server

Read-only MCP access to a CLARA workspace for agentic tools (Claude Desktop,
Claude Code, Cursor, or anything speaking MCP over stdio). Strategy context:
W6/X8 — the app UI is a depreciating asset; the durable product is the
governed data layer agents call.

**Strictly read-only + ask.** No approvals, no executions, no writes — those
stay in the product where the policy gates, works-council redaction and audit
trail live. The MCP process is a thin client over the REST API, so RBAC, rate
limits and works-council mode apply exactly as for any client.

## Tools

| Tool | What it returns |
|---|---|
| `list_problems` | Problem summaries (impact, status, affected customers) |
| `get_problem` | Full problem detail incl. evidence and governance checks |
| `get_evidence_pack` | The audit-grade export, content-hashed |
| `get_outcome_board` | Outcome statuses, evidence grades, guardrails, learnings |
| `get_emerging_problems` | Emerging radar with the corroboration floor |
| `get_measurement_checkpoints` | Scheduled re-measurement checkpoints |
| `get_model_card_metrics` | Published eval quality (per-language, with n + date) |
| `ask_clara` | Grounded Q&A with citations; refuses on thin evidence |

## Setup against the hosted API

1. In CLARA → **Integrations → API keys**, mint a key with the **viewer** role
   (admin required; the plaintext is shown once).
2. Install and configure:

```bash
pip install -e "apps/api[mcp]"
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "clara": {
      "command": "python3",
      "args": ["-m", "app.mcp_server"],
      "cwd": "<repo>/apps/api",
      "env": {
        "CLARA_API_URL": "https://api.clara.odradekai.com",
        "CLARA_API_KEY": "<viewer API key>"
      }
    }
  }
}
```

Local dev (auth-disabled API): omit both credentials and leave
`CLARA_API_URL` unset (defaults to `http://localhost:8000`).

A Supabase JWT can be used instead of an API key via `CLARA_API_TOKEN`
(Bearer), but API keys are the intended machine credential: role-scoped,
revocable in the UI, and never expiring mid-session.

## Notes

- The fetch layer lives in `app/services/mcp_fetch.py` (tested in CI without
  the optional `mcp` dependency); the stdio server is `app/mcp_server.py`.
- Works-council mode applies: below-admin credentials receive role-redacted
  person fields, exactly like the UI.
- Rate limits apply to `ask_clara` like any `/ask` caller.
