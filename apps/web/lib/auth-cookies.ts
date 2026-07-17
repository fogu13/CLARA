// Server-side session-cookie helpers for the /api/auth/* route handlers.
// Design: docs/engineering/auth-hardening-design.md — HttpOnly SameSite=Lax
// cookies scoped (via AUTH_COOKIE_DOMAIN) so the same-site API receives them.
import type { NextResponse } from "next/server";

const SUPABASE_URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const ACCESS_COOKIE = "clara_access_token";
export const REFRESH_COOKIE = "clara_refresh_token";

export function gotrueConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

export async function gotrue(path: string, body: unknown): Promise<Response> {
  return fetch(`${SUPABASE_URL}${path}`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
    // Unset => host-only (right for localhost). Production sets
    // AUTH_COOKIE_DOMAIN=clara.odradekai.com so api.clara.* receives it.
    ...(process.env.AUTH_COOKIE_DOMAIN ? { domain: process.env.AUTH_COOKIE_DOMAIN } : {}),
  };
}

export function setSessionCookies(
  res: NextResponse,
  data: { access_token: string; refresh_token?: string; expires_in?: number }
): void {
  res.cookies.set(ACCESS_COOKIE, data.access_token, cookieOptions(data.expires_in ?? 3600));
  if (data.refresh_token) {
    res.cookies.set(REFRESH_COOKIE, data.refresh_token, cookieOptions(60 * 60 * 24 * 30));
  }
}

export function clearSessionCookies(res: NextResponse): void {
  res.cookies.set(ACCESS_COOKIE, "", cookieOptions(0));
  res.cookies.set(REFRESH_COOKIE, "", cookieOptions(0));
}

export type SessionInfo = {
  authenticated: boolean;
  hadSession: boolean;
  email: string | null;
  role: string | null;
  expiresAt: number | null; // epoch ms
};

// Non-verifying decode for UI state only — the API verifies signatures.
export function sessionFromToken(token: string | undefined): SessionInfo {
  if (!token) {
    return { authenticated: false, hadSession: false, email: null, role: null, expiresAt: null };
  }
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(Buffer.from(part, "base64").toString("utf8"));
    const expiresAt = typeof payload.exp === "number" ? payload.exp * 1000 : null;
    return {
      authenticated: expiresAt !== null && expiresAt > Date.now(),
      hadSession: true,
      email: typeof payload.email === "string" ? payload.email : null,
      role: payload?.app_metadata?.user_role ?? payload?.user_role ?? "viewer",
      expiresAt,
    };
  } catch {
    return { authenticated: false, hadSession: true, email: null, role: null, expiresAt: null };
  }
}
