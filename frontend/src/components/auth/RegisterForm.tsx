"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { supabase } from "@/lib/supabase";
import { authApi } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth";
import { getErrorMessage } from "@/lib/api";

export default function RegisterForm() {
  const router = useRouter();
  const setProfile = useAuthStore((s) => s.setProfile);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"student" | "professor">("student");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Step 1: Create the Supabase Auth account
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName }, // stored in Supabase user_metadata
      },
    });

    if (signUpError) {
      if (signUpError.message.toLowerCase().includes("already")) {
        setError("An account with this email address is already registered.");
      } else {
        setError(signUpError.message);
      }
      setLoading(false);
      return;
    }

    if (!data.session) {
      // Supabase email confirmation is ON — tell the user to check their inbox
      setError(null);
      setLoading(false);
      alert("Check your email to confirm your account, then log in.");
      return;
    }

    // Step 2: Sync the profile (role) to our FastAPI database
    try {
      const res = await authApi.syncProfile({ email, full_name: fullName, role });
      setProfile(res.data);
      router.push("/dashboard");
    } catch (err) {
      setError("Account created but profile sync failed: " + getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="reg-name">Full Name</Label>
        <Input
          id="reg-name"
          type="text"
          placeholder="Bikram Sharma"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          autoComplete="name"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="reg-email">Email</Label>
        <Input
          id="reg-email"
          type="email"
          placeholder="you@university.edu"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="reg-password">Password</Label>
        <Input
          id="reg-password"
          type="password"
          placeholder="Minimum 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          minLength={8}
        />
      </div>

      <div className="space-y-2">
        <Label>I am a</Label>
        <div className="flex gap-3">
          {(["student", "professor"] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRole(r)}
              className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium capitalize transition-colors ${
                role === r
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input bg-background hover:bg-secondary"
              }`}
              aria-pressed={role === r}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? "Creating account…" : "Create Account"}
      </Button>
    </form>
  );
}
