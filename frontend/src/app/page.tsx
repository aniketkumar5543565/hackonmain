"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import LoginForm from "@/components/auth/LoginForm";
import RegisterForm from "@/components/auth/RegisterForm";
import { supabase } from "@/lib/supabase";

type View = "landing" | "login" | "register" | "demo-select";

// Demo accounts with different roles
const DEMO_ACCOUNTS = [
  {
    email: "demo.student@campusos.app",
    password: "demo1234",
    role: "STUDENT",
    name: "Student",
    description: "View timetable, assignments, events",
  },
  {
    email: "demo.admin@campusos.app",
    password: "demo1234",
    role: "ACADEMIC_ADMIN",
    name: "Academic Admin",
    description: "Upload timetables, manage schedules",
  },
  {
    email: "demo.professor@campusos.app",
    password: "demo1234",
    role: "FACULTY",
    name: "Professor",
    description: "Post notices, upload assignments",
  },
];

export default function LandingPage() {
  const router = useRouter();
  const [view, setView] = useState<View>("landing");
  const [demoLoading, setDemoLoading] = useState<string | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  async function handleTryDemo(demoAccount: typeof DEMO_ACCOUNTS[0]) {
    setDemoError(null);
    setDemoLoading(demoAccount.email);

    const { error } = await supabase.auth.signInWithPassword({
      email: demoAccount.email,
      password: demoAccount.password,
    });

    if (error) {
      setDemoError(`${demoAccount.name} demo account unavailable. Please try again later.`);
      setDemoLoading(null);
      return;
    }

    router.push("/dashboard");
  }

  if (view === "login") {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Sign In</CardTitle>
            <CardDescription>Welcome back to CampusOS</CardDescription>
          </CardHeader>
          <CardContent>
            <LoginForm />
            <p className="mt-4 text-center text-sm text-muted-foreground">
              No account?{" "}
              <button
                onClick={() => setView("register")}
                className="text-primary underline-offset-4 hover:underline"
              >
                Register
              </button>
            </p>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              <button
                onClick={() => setView("landing")}
                className="text-primary underline-offset-4 hover:underline"
              >
                Back
              </button>
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (view === "register") {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Create Account</CardTitle>
            <CardDescription>Join CampusOS today</CardDescription>
          </CardHeader>
          <CardContent>
            <RegisterForm />
            <p className="mt-4 text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <button
                onClick={() => setView("login")}
                className="text-primary underline-offset-4 hover:underline"
              >
                Sign In
              </button>
            </p>
            <p className="mt-2 text-center text-sm text-muted-foreground">
              <button
                onClick={() => setView("landing")}
                className="text-primary underline-offset-4 hover:underline"
              >
                Back
              </button>
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (view === "demo-select") {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 to-blue-100 p-4">
        <Card className="w-full max-w-2xl">
          <CardHeader>
            <CardTitle className="text-2xl">Try CampusOS</CardTitle>
            <CardDescription>
              Select a role to explore the system with demo data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {demoError && (
              <div className="flex gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>{demoError}</div>
              </div>
            )}

            <div className="grid gap-3 md:grid-cols-3">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.email}
                  onClick={() => handleTryDemo(account)}
                  disabled={demoLoading !== null}
                  className="group relative overflow-hidden rounded-lg border-2 border-muted bg-card p-4 text-left transition hover:border-primary hover:shadow-lg disabled:opacity-50"
                >
                  <div className="space-y-2">
                    <h3 className="font-semibold group-hover:text-primary">
                      👤 {account.name}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {account.description}
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">
                      {account.email}
                    </p>
                  </div>
                  {demoLoading === account.email && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/10">
                      <div className="text-xs text-white">Logging in...</div>
                    </div>
                  )}
                </button>
              ))}
            </div>

            <div className="border-t pt-4 flex gap-2">
              <Button
                variant="outline"
                onClick={() => setView("landing")}
                className="flex-1"
              >
                Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-6 text-center">
      <div className="max-w-2xl space-y-8">
        <div className="space-y-2">
          <div className="text-5xl font-bold tracking-tight text-foreground">
            Campus<span className="text-primary">OS</span>
          </div>
          <h1 className="text-xl text-muted-foreground font-medium">
            Your AI Operating System For Student Life
          </h1>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm text-left sm:grid-cols-4">
          {[
            { icon: "📅", label: "Timetable OCR" },
            { icon: "📢", label: "AI Summaries" },
            { icon: "🎉", label: "Event Reminders" },
            { icon: "🌅", label: "Daily Briefing" },
          ].map((f) => (
            <div
              key={f.label}
              className="flex items-center gap-2 rounded-lg border bg-white/70 px-3 py-2 backdrop-blur"
            >
              <span aria-hidden>{f.icon}</span>
              <span className="font-medium">{f.label}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button size="lg" onClick={() => setView("login")}>
            Login
          </Button>
          <Button size="lg" variant="outline" onClick={() => setView("register")}>
            Register
          </Button>
          <Button
            size="lg"
            variant="secondary"
            onClick={() => setView("demo-select")}
          >
            Try Demo
          </Button>
        </div>
      </div>
    </main>
  );
}
