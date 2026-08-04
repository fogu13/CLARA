// Lightweight Supabase auth via the GoTrue REST endpoint; no SDK dependency.
//
// Two modes behind one API (design: docs/engineering/auth-hardening-design.md):
//  - Legacy (default): tokens in localStorage, Bearer header to the API.
//  - Cookie mode (NEXT_PUBLIC_COOKIE_AUTH=1): the /api/auth/* route handlers
//    keep tokens in HttpOnly SameSite=Lax cookies the same-site API reads;
//    JS never sees a token. UI state comes from a cached /api/auth/session.

const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const cookieAuthEnabled = process.env.NEXT_PUBLIC_COOKIE_AUTH === "1";
export const authConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

const TOKEN_KEY = "clara_access_token";
const REFRESH_KEY = "clara_refresh_token";

type CookieSession = {
  authenticated: boolean;
  hadSession: boolean;
  email: string | null;
  role: string | null;
  expiresAt: number | null;
};

// Module-level cache so isAuthenticated()/hasRole() stay synchronous for the
// guard and role-gated UI. primeSession()/signIn()/refreshSession() update it.
let cookieSession: CookieSession | null = null;

const NO_SESSION: CookieSession = {
  authenticated: false,
  hadSession: false,
  email: null,
  role: null,
  expiresAt: null,
};

export async function primeSession(): Promise<void> {
  if (!cookieAuthEnabled || typeof window === "undefined") return;
  try {
    const response = await fetch("/api/auth/session", { cache: "no-store" });
    cookieSession = response.ok ? await response.json() : NO_SESSION;
  } catch {
    cookieSession = NO_SESSION;
  }
}

export type SignInResult = { mfaRequired: boolean; factorId?: string };

export async function signIn(email: string, password: string): Promise<SignInResult> {
  if (cookieAuthEnabled) {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(data?.error ?? `Sign-in failed (${response.status})`);
    }
    if (data?.mfaRequired) {
      // Password accepted, but no session exists until the TOTP code passes.
      return { mfaRequired: true, factorId: data.factorId };
    }
    cookieSession = data;
    return { mfaRequired: false };
  }

  const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error_description ?? data?.msg ?? `Sign-in failed (${response.status})`);
  }

  window.localStorage.setItem(TOKEN_KEY, data.access_token);
  if (data.refresh_token) {
    window.localStorage.setItem(REFRESH_KEY, data.refresh_token);
  }
  // Legacy mode performs no MFA challenge — MFA is a cookie-mode feature
  // (docs/engineering/auth-hardening-design.md).
  return { mfaRequired: false };
}

// ---------------------------------------------------------------------------
// MFA (TOTP) — cookie mode only: the flows depend on the HttpOnly session and
// the /api/auth/mfa/* route handlers.
// ---------------------------------------------------------------------------

function requireCookieMode(): void {
  if (!cookieAuthEnabled) {
    throw new Error("MFA requires cookie sessions (set NEXT_PUBLIC_COOKIE_AUTH=1)");
  }
}

async function mfaRequest(url: string, init?: RequestInit): Promise<any> {
  const response = await fetch(url, init);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error ?? `Request failed (${response.status})`);
  }
  return data;
}

export async function verifyMfaLogin(factorId: string, code: string): Promise<void> {
  requireCookieMode();
  cookieSession = await mfaRequest("/api/auth/mfa/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factorId, code }),
  });
}

export async function enrollMfa(): Promise<{
  factorId: string;
  qrCode: string | null;
  secret: string | null;
  uri: string | null;
}> {
  requireCookieMode();
  return mfaRequest("/api/auth/mfa/enroll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export async function confirmMfaEnrollment(factorId: string, code: string): Promise<void> {
  requireCookieMode();
  await mfaRequest("/api/auth/mfa/enroll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factorId, code }),
  });
  await primeSession();
}

export type MfaFactor = {
  id: string;
  friendlyName: string;
  factorType: string;
  status: string;
};

export async function listMfaFactors(): Promise<MfaFactor[]> {
  requireCookieMode();
  const data = await mfaRequest("/api/auth/mfa/factors", { cache: "no-store" });
  return data?.factors ?? [];
}

export async function removeMfaFactor(factorId: string): Promise<void> {
  requireCookieMode();
  await mfaRequest("/api/auth/mfa/factors", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factorId }),
  });
}

export function signOut(): void {
  if (typeof window === "undefined") return;
  if (cookieAuthEnabled) {
    cookieSession = NO_SESSION;
    void fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
  }
  // Also in cookie mode: a browser that signed in under legacy mode still holds
  // real tokens here. Leaving them is both a credential-hygiene problem and the
  // source of stale-Bearer 401s (see browserAccessToken in client-api).
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

function decodeExp(token: string): number | null {
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = part.padEnd(part.length + ((4 - (part.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

export function hasStoredSession(): boolean {
  // True when this browser held a session at some point (tokens still stored),
  // so an auth bounce can honestly say "expired" instead of showing that to
  // first-time visitors who never signed in.
  if (typeof window === "undefined") return false;
  if (cookieAuthEnabled) return cookieSession?.hadSession ?? false;
  return Boolean(
    window.localStorage.getItem(TOKEN_KEY) || window.localStorage.getItem(REFRESH_KEY)
  );
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  if (cookieAuthEnabled) {
    return Boolean(
      cookieSession?.authenticated &&
        cookieSession.expiresAt !== null &&
        cookieSession.expiresAt > Date.now()
    );
  }
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return false;
  const exp = decodeExp(token);
  // Fail closed: a token whose exp we can't decode (malformed / not a real JWT) is
  // untrustworthy and must NOT count as authenticated. Supabase access tokens always
  // carry exp, so requiring a valid, future exp is correct.
  return exp !== null && exp * 1000 > Date.now();
}

export function sessionExpiresInMs(): number | null {
  if (typeof window === "undefined") return null;
  if (cookieAuthEnabled) {
    return cookieSession?.expiresAt == null ? null : cookieSession.expiresAt - Date.now();
  }
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const exp = decodeExp(token);
  return exp === null ? null : exp * 1000 - Date.now();
}

let refreshInFlight: Promise<boolean> | null = null;

export async function refreshSession(): Promise<boolean> {
  // Rotate the access token with the stored refresh token. Deduplicated:
  // GoTrue rotates refresh tokens on use, so two parallel refreshes would
  // invalidate each other.
  if (typeof window === "undefined" || !authConfigured) return false;
  if (refreshInFlight) return refreshInFlight;

  if (cookieAuthEnabled) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch("/api/auth/refresh", { method: "POST" });
        const data = await response.json().catch(() => null);
        if (!response.ok || !data?.authenticated) {
          cookieSession = { ...NO_SESSION, hadSession: cookieSession?.hadSession ?? false };
          return false;
        }
        cookieSession = data;
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
    return refreshInFlight;
  }

  const refreshToken = window.localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return false;

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
        method: "POST",
        headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.access_token) return false;
      window.localStorage.setItem(TOKEN_KEY, data.access_token);
      if (data.refresh_token) {
        window.localStorage.setItem(REFRESH_KEY, data.refresh_token);
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function decodedPayload(): Record<string, unknown> | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function currentUserEmail(): string | null {
  if (cookieAuthEnabled) return cookieSession?.email ?? null;
  const payload = decodedPayload();
  return typeof payload?.email === "string" ? payload.email : null;
}

export function currentUserRole(): string | null {
  // Role from the JWT's app_metadata (admin-controlled, not user-editable).
  // null when auth is unconfigured or no session exists.
  if (cookieAuthEnabled) return cookieSession?.authenticated ? cookieSession.role : null;
  const payload = decodedPayload();
  if (payload === null) return null;
  const appMetadata = payload.app_metadata as Record<string, unknown> | undefined;
  return (appMetadata?.user_role as string) ?? (payload.user_role as string) ?? "viewer";
}

const ROLE_LEVEL: Record<string, number> = { viewer: 0, editor: 1, admin: 2, owner: 3 };

export function hasRole(required: "viewer" | "editor" | "admin" | "owner"): boolean {
  // Purely cosmetic gating (hide controls a request would 403 on) — the API
  // stays authoritative. No session (dev mode / auth off) shows everything,
  // matching the API's permissive local default.
  const role = currentUserRole();
  if (role === null) return true;
  return (ROLE_LEVEL[role] ?? 0) >= ROLE_LEVEL[required];
}
