import { NextResponse, type NextRequest } from "next/server";
import {
  gotrue,
  gotrueConfigured,
  sessionFromToken,
  setSessionCookies,
} from "@/lib/auth-cookies";

export async function POST(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const body = await request.json().catch(() => ({}));
  const { email, password } = body ?? {};
  if (!email || !password) {
    return NextResponse.json({ error: "email and password are required" }, { status: 422 });
  }
  const upstream = await gotrue("/auth/v1/token?grant_type=password", { email, password });
  const data = await upstream.json().catch(() => null);
  if (!upstream.ok || !data?.access_token) {
    return NextResponse.json(
      { error: data?.error_description ?? data?.msg ?? "Sign-in failed" },
      { status: 401 }
    );
  }
  const res = NextResponse.json(sessionFromToken(data.access_token));
  setSessionCookies(res, data);
  return res;
}
