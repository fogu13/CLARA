"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authConfigured, signIn, verifyMfaLogin } from "@/lib/auth-client";
import { wrongOriginHint } from "@/lib/client-api";

function AuthForm() {
  const router = useRouter();
  const reason = useSearchParams().get("reason");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Set after a correct password when the account has a verified TOTP factor:
  // the session only exists once the code passes (/api/auth/mfa/verify).
  const [mfaFactorId, setMfaFactorId] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await signIn(email, password);
      if (result.mfaRequired && result.factorId) {
        setMfaFactorId(result.factorId);
        return;
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaSubmit(event: FormEvent) {
    event.preventDefault();
    if (!mfaFactorId) return;
    setError(null);
    setLoading(true);
    try {
      await verifyMfaLogin(mfaFactorId, mfaCode.trim());
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Code verification failed");
    } finally {
      setLoading(false);
    }
  }

  if (mfaFactorId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-sm space-y-6 rounded-lg border bg-card p-8 shadow-sm">
          <div className="space-y-1 text-center">
            <h1 className="text-2xl font-semibold">Two-factor code</h1>
            <p className="text-sm text-muted-foreground">
              Enter the 6-digit code from your authenticator app.
            </p>
          </div>
          <form className="space-y-4" onSubmit={handleMfaSubmit}>
            <div className="space-y-2">
              <Label htmlFor="mfa-code">Code</Label>
              <Input
                id="mfa-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]*"
                maxLength={6}
                value={mfaCode}
                onChange={(event) => setMfaCode(event.target.value)}
                required
                autoFocus
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading || mfaCode.trim().length < 6}>
              {loading ? "Verifying…" : "Verify"}
            </Button>
            <button
              type="button"
              className="w-full text-xs text-muted-foreground underline"
              onClick={() => {
                setMfaFactorId(null);
                setMfaCode("");
                setError(null);
              }}
            >
              Start over
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm space-y-6 rounded-lg border bg-card p-8 shadow-sm">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">CLARA</h1>
          <p className="text-sm text-muted-foreground">Sign in to your workspace</p>
        </div>

        {!authConfigured && (
          <p className="rounded-md bg-muted p-3 text-xs text-muted-foreground">
            Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and
            NEXT_PUBLIC_SUPABASE_ANON_KEY to enable sign-in.
          </p>
        )}
      {reason === "expired" ? (
        <p role="status" className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Your session expired. Please sign in again.{wrongOriginHint()}
        </p>
      ) : null}


        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading || !authConfigured}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            <a href="/reset-password" className="underline-offset-2 hover:text-foreground hover:underline">
              Forgot password?
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}


export default function AuthPage() {
  return (
    <Suspense fallback={null}>
      <AuthForm />
    </Suspense>
  );
}
