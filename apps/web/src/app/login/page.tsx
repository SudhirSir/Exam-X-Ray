"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { Button, Card, ErrorBanner } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { User } from "@/lib/types";
import { ScanLine } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function doLogin(loginEmail: string, loginPass: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<{ user: User }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: loginEmail, password: loginPass }),
      });
      if (res.user.role === "admin") {
        router.push("/admin");
      } else if (res.user.role === "teacher") {
        router.push("/teacher");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    doLogin(email, password);
  }

  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto flex max-w-md flex-col px-4 py-14">
        <Card className="p-7">
          <div className="mb-6 text-center">
            <ScanLine className="mx-auto mb-2 h-8 w-8 text-sky-400" />
            <h1 className="text-2xl font-bold text-white">Sign in to EXAM X-RAY</h1>
            <p className="mt-1 text-xs text-slate-400">
              HTTP-only JWT cookie authentication
            </p>
          </div>

          {error && <div className="mb-4"><ErrorBanner message={error} /></div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          <div className="mt-6 border-t border-slate-800 pt-5">
            <p className="mb-2.5 text-center text-[11px] uppercase tracking-wider text-slate-400">
              Quick Demo Access (Seeded Accounts)
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => doLogin("student@examxray.in", "Student@ExamXRay2026")}
              >
                Student
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => doLogin("teacher@examxray.in", "Teacher@ExamXRay2026")}
              >
                Teacher
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => doLogin("admin@examxray.in", "Admin@ExamXRay2026")}
              >
                Admin
              </Button>
            </div>
          </div>

          <p className="mt-5 text-center text-xs text-slate-400">
            New to EXAM X-RAY?{" "}
            <Link href="/register" className="text-sky-400 hover:underline">
              Create an account
            </Link>
          </p>
        </Card>
      </main>
    </div>
  );
}
