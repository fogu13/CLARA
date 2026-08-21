import { NextResponse, type NextRequest } from "next/server";
import {
  challengeAndVerify,
  clearMfaCookie,
  gotrueConfigured,
  MFA_COOKIE,
  sessionFromToken,
  setSessionCookies,
} from "@/lib/auth-cookies";

// Second login step: TOTP code against the pending AAL1 token; success mints
// the real (AAL2) session cookies.
export async function POST(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const pending = request.cookies.get(MFA_COOKIE)?.value;
  if (!pending) {
    return NextResponse.json({ error: "No pending sign-in, start over" }, { status: 401 });
  }
  const { factorId, code } = (await request.json().catch(() => ({}))) ?? {};
  if (!factorId || !code) {
    return NextResponse.json({ error: "factorId and code are required" }, { status: 422 });
  }
  const result = await challengeAndVerify(pending, String(factorId), String(code));
  if (!result.ok || !result.session) {
    return NextResponse.json({ error: result.error ?? "Invalid code" }, { status: 401 });
  }
  const res = NextResponse.json(sessionFromToken(result.session.access_token));
  setSessionCookies(res, result.session);
  clearMfaCookie(res);
  return res;
}
