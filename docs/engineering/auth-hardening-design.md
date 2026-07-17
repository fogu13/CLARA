# Auth hardening — HttpOnly cookie sessions (external-review Phase D)

_Status: implemented behind `NEXT_PUBLIC_COOKIE_AUTH`; MFA is the documented
follow-up. Replaces the OWASP-flagged localStorage token storage
(`clara_access_token` + refresh token readable by any XSS)._

## Site topology (what makes this simple)

- Production web `clara.odradekai.com` and API `api.clara.odradekai.com` are
  **same-site** (the API is a subdomain of the web host). A cookie set with
  `Domain=clara.odradekai.com` is sent to the API, and `SameSite=Lax` applies —
  no third-party-cookie machinery, no BFF proxy hop through Vercel functions.
- Local dev `localhost:3000` ↔ `localhost:8000`: cookies ignore ports; a
  host-only `localhost` cookie flows. Works unchanged.
- **Vercel preview URLs (`*.vercel.app`) are cross-site with the API** — Lax
  cookies will not accompany fetches, and third-party cookies are being phased
  out anyway. This is WHY the mode is flag-gated: previews keep the legacy
  localStorage bearer flow; only the canonical domain flips the flag.

## Design

- **Next.js route handlers** own the GoTrue exchange server-side:
  `POST /api/auth/login` (password grant → set cookies), `POST /api/auth/refresh`
  (rotate via refresh cookie), `POST /api/auth/logout` (clear), and
  `GET /api/auth/session` (non-verifying decode for UI state: authenticated,
  email, role, expiry — the API does the real verification).
- **Cookies**: `clara_access_token` (maxAge = token lifetime) and
  `clara_refresh_token` (30 d), `HttpOnly; Secure; SameSite=Lax; Path=/`,
  `Domain` from `AUTH_COOKIE_DOMAIN` (unset ⇒ host-only, correct for
  localhost; prod sets `clara.odradekai.com`).
- **FastAPI** accepts the access token from the `clara_access_token` cookie
  whenever no `Authorization` header is present — additive, so bearer tokens
  (API keys, scripts, legacy mode) keep working unchanged.
- **CSRF posture**: cookies are `SameSite=Lax` (not sent on cross-site
  POST/fetch), and the API's CORS allowlist restricts readable origins.
  Cross-site form POSTs carry no cookie under Lax; no token-based CSRF layer is
  needed at this surface. Revisit if `SameSite=None` is ever introduced.
- **Client**: `auth-client.ts` hides the mode behind the same function
  signatures. Cookie mode keeps a module-level session cache primed from
  `/api/auth/session`, so `isAuthenticated()/currentUserRole()/hasRole()` stay
  synchronous for the guard and the role-gated UI. `client-api.ts` sends
  `credentials: "include"` and no bearer header in cookie mode.

## Rollout

1. Deploy (flag off everywhere) — pure no-op, bearer flow untouched.
2. Set `NEXT_PUBLIC_COOKIE_AUTH=1` + `AUTH_COOKIE_DOMAIN=clara.odradekai.com`
   on the Vercel production environment only. Sign-in now sets HttpOnly
   cookies; localStorage tokens are no longer written; existing sessions
   re-authenticate once.
3. Previews/local keep the legacy flow until intentionally migrated.

## Follow-up (not in this change)

- **MFA (TOTP)** via GoTrue enroll/challenge/verify: needs an enrollment UI
  (QR + code confirm) and a challenge step in the login flow; the cookie
  routes are already the right chokepoint to add it.
- Remove the legacy localStorage path once the canonical domain has run
  cookie-mode for a while and previews are handled (e.g. preview API proxy).
