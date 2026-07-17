"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  authConfigured,
  hasStoredSession,
  isAuthenticated,
  refreshSession,
  sessionExpiresInMs,
} from "@/lib/auth-client";

const CHECK_INTERVAL_MS = 60_000;
const REFRESH_AHEAD_MS = 10 * 60_000; // rotate 10 min before expiry

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // When auth isn't configured (no NEXT_PUBLIC_SUPABASE_* env), don't block; local dev
    // runs against an auth-disabled API. With auth configured, require a valid session.
    let cancelled = false;

    async function ensureSession() {
      if (!authConfigured) {
        setReady(true);
        return;
      }
      if (isAuthenticated()) {
        setReady(true);
        const remaining = sessionExpiresInMs();
        if (remaining !== null && remaining < REFRESH_AHEAD_MS) {
          void refreshSession(); // proactive rotation; failure caught next tick
        }
        return;
      }
      // Access token expired mid-session: try the refresh token before bouncing.
      if (await refreshSession()) {
        if (!cancelled) setReady(true);
        return;
      }
      // Only a browser that actually held a session gets "expired"; a first-time
      // visitor bouncing off a guarded URL just sees the plain sign-in page.
      if (!cancelled) router.replace(hasStoredSession() ? "/auth?reason=expired" : "/auth");
    }

    void ensureSession();
    const timer = setInterval(ensureSession, CHECK_INTERVAL_MS);
    const onFocus = () => void ensureSession();
    window.addEventListener("focus", onFocus);
    return () => {
      cancelled = true;
      clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background" role="status" aria-live="polite">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-sm font-bold text-primary-foreground">C</span>
          </div>
          <span className="text-sm">CLARA</span>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
