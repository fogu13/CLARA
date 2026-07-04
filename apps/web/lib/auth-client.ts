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

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return false;
  const exp = decodeExp(token);
  // Fail closed: a token whose exp we can't decode (malformed / not a real JWT) is
  // untrustworthy and must NOT count as authenticated. Supabase access tokens always
  // carry exp, so requiring a valid, future exp is correct.
  // ponytail: no silent auto-refresh; an expired access token (~1h) re-routes to /auth.
  // Add refresh_token rotation here if longer sessions are needed.
  return exp !== null && exp * 1000 > Date.now();
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
