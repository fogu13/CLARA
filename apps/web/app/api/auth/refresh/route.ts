import { NextResponse, type NextRequest } from "next/server";
import {
  clearSessionCookies,
  gotrue,
  gotrueConfigured,
  REFRESH_COOKIE,
  sessionFromToken,
  setSessionCookies,
} from "@/lib/auth-cookies";

export async function POST(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.json({ error: "No session" }, { status: 401 });
  }
  const upstream = await gotrue("/auth/v1/token?grant_type=refresh_token", {
    refresh_token: refreshToken,
  });
  const data = await upstream.json().catch(() => null);
  if (!upstream.ok || !data?.access_token) {
    const res = NextResponse.json({ error: "Session refresh failed" }, { status: 401 });
    clearSessionCookies(res);
    return res;
  }
  const res = NextResponse.json(sessionFromToken(data.access_token));
  setSessionCookies(res, data);
  return res;
}
