import { type NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE, clearSessionCookies, gotrueAuthed, gotrueConfigured } from "@/lib/auth-cookies";

// Clearing cookies alone left the GoTrue refresh token valid for its full
// 30-day life: a copied cookie jar kept minting access tokens after sign-out.
// Revoke the session server-side first (best-effort), then clear.
export async function POST(request: NextRequest) {
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  if (token && gotrueConfigured()) {
    try {
      await gotrueAuthed("/auth/v1/logout?scope=local", token, {});
    } catch {
      // Revocation is best-effort: the cookies are cleared regardless.
    }
  }
  const res = NextResponse.json({ ok: true });
  clearSessionCookies(res);
  return res;
}
