"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { authConfigured, isAuthenticated } from "@/lib/auth-client";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // When auth isn't configured (no NEXT_PUBLIC_SUPABASE_* env), don't block — local dev
    // runs against an auth-disabled API. With auth configured, require a valid session.
    if (!authConfigured || isAuthenticated()) {
      setReady(true);
    } else {
      router.replace("/auth");
    }
  }, [router]);

  if (!ready) return null;
  return <>{children}</>;
}
