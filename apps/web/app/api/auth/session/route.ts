import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_COOKIE, sessionFromToken } from "@/lib/auth-cookies";

// UI session state derived from the HttpOnly cookie (non-verifying decode —
// signature verification happens at the API on every request).
export async function GET(request: NextRequest) {
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  return NextResponse.json(sessionFromToken(token), {
    headers: { "Cache-Control": "no-store" },
  });
}
