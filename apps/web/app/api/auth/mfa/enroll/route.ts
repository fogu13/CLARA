import { NextResponse, type NextRequest } from "next/server";
import {
  ACCESS_COOKIE,
  challengeAndVerify,
  gotrueAuthed,
  gotrueConfigured,
  sessionFromToken,
  setSessionCookies,
} from "@/lib/auth-cookies";

// POST {} -> begin TOTP enrollment: returns factorId + QR/secret to bind an
// authenticator app. POST {factorId, code} -> confirm the factor; GoTrue
// returns an upgraded (AAL2) session which replaces the cookies.
export async function POST(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  }
  const body = (await request.json().catch(() => ({}))) ?? {};

  if (body.factorId && body.code) {
    const result = await challengeAndVerify(token, String(body.factorId), String(body.code));
    if (!result.ok || !result.session) {
      return NextResponse.json({ error: result.error ?? "Invalid code" }, { status: 401 });
    }
    const res = NextResponse.json({ ok: true, ...sessionFromToken(result.session.access_token) });
    setSessionCookies(res, result.session);
    return res;
  }

  const upstream = await gotrueAuthed("/auth/v1/factors", token, {
    body: { factor_type: "totp", friendly_name: body.friendlyName ?? "CLARA TOTP" },
  });
  const data = await upstream.json().catch(() => null);
  if (!upstream.ok || !data?.id) {
    return NextResponse.json(
      { error: data?.error_description ?? data?.msg ?? "Enrollment failed" },
      { status: upstream.status === 401 ? 401 : 400 }
    );
  }
  return NextResponse.json({
    factorId: data.id,
    qrCode: data.totp?.qr_code ?? null,
    secret: data.totp?.secret ?? null,
    uri: data.totp?.uri ?? null,
  });
}
