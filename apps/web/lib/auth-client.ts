// Lightweight Supabase auth via the GoTrue REST endpoint; no SDK dependency.
// Stores the access token under "clara_access_token", which lib/client-api.ts already
// sends as the Bearer token to the FastAPI backend.

const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const authConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

const TOKEN_KEY = "clara_access_token";
const REFRESH_KEY = "clara_refresh_token";

export async function signIn(email: string, password: string): Promise<void> {
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
}

export function signOut(): void {
  if (typeof window === "undefined") return;
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
  return Boolean(
    window.localStorage.getItem(TOKEN_KEY) || window.localStorage.getItem(REFRESH_KEY)
  );
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
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

export function currentUserRole(): string | null {
  // Role from the JWT's app_metadata (admin-controlled, not user-editable).
  // null when auth is unconfigured or no session exists.
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload?.app_metadata?.user_role ?? payload?.user_role ?? "viewer";
  } catch {
    return null;
  }
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

export function currentUserEmail(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.email === "string" ? payload.email : null;
  } catch {
    return null;
  }
}
