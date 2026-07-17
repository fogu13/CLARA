import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_COOKIE, gotrueAuthed, gotrueConfigured } from "@/lib/auth-cookies";

export async function GET(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  const upstream = await gotrueAuthed("/auth/v1/factors", token, { method: "GET" });
  const data = await upstream.json().catch(() => null);
  if (!upstream.ok || !Array.isArray(data)) {
    return NextResponse.json({ factors: [] });
  }
  return NextResponse.json({
    factors: data.map((f: { id: string; friendly_name?: string; factor_type: string; status: string }) => ({
      id: f.id,
      friendlyName: f.friendly_name ?? "",
      factorType: f.factor_type,
      status: f.status,
    })),
  });
}

export async function DELETE(request: NextRequest) {
  if (!gotrueConfigured()) {
    return NextResponse.json({ error: "Auth is not configured" }, { status: 501 });
  }
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  const { factorId } = (await request.json().catch(() => ({}))) ?? {};
  if (!factorId) return NextResponse.json({ error: "factorId is required" }, { status: 422 });
  const upstream = await gotrueAuthed(`/auth/v1/factors/${factorId}`, token, { method: "DELETE" });
  if (!upstream.ok) {
    const data = await upstream.json().catch(() => null);
    return NextResponse.json(
      { error: data?.error_description ?? data?.msg ?? "Could not remove the factor" },
      { status: 400 }
    );
  }
  return NextResponse.json({ ok: true });
}
