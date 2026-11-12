"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/Navbar";
import { Button, Card, ErrorBanner } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { User } from "@/lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [isMinor, setIsMinor] = useState(false);
  const [guardianEmail, setGuardianEmail] = useState("");
  const [consent, setConsent] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<{ user: User }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          role,
          is_minor: isMinor,
          guardian_email: isMinor ? guardianEmail : null,
          consent_accepted: consent,
        }),
      });
      router.push(res.user.role === "teacher" ? "/teacher" : "/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto flex max-w-md flex-col px-4 py-12">
        <Card className="p-7">
          <h1 className="text-2xl font-bold text-white">Create your EXAM X-RAY account</h1>
          <p className="mt-1 text-xs text-slate-400">
            Includes pseudonymous analytics ID and Indian DPDP privacy controls.
          </p>

          {error && <div className="mt-4"><ErrorBanner message={error} /></div>}

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">Full Name</label>
              <input
                required
                minLength={2}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Ananya Deshmukh"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ananya@student.in"
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">
                Password (min 8 chars)
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-300">Account Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as "student" | "teacher")}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              >
                <option value="student">Student</option>
                <option value="teacher">Teacher / Educator</option>
              </select>
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={isMinor}
                onChange={(e) => setIsMinor(e.target.checked)}
                className="rounded border-slate-600 bg-slate-900"
              />
              I am under 18 years of age (requires parent/guardian email)
            </label>

            {isMinor && (
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">
                  Parent / Guardian Email
                </label>
                <input
                  type="email"
                  required
                  value={guardianEmail}
                  onChange={(e) => setGuardianEmail(e.target.value)}
                  placeholder="parent@example.com"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
                />
              </div>
            )}

            <label className="flex items-start gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                required
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5 rounded border-slate-600 bg-slate-900"
              />
              <span>
                I consent to processing my learning diagnostics for personalized study roadmaps.
              </span>
            </label>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Creating account..." : "Create Account"}
            </Button>
          </form>

          <p className="mt-5 text-center text-xs text-slate-400">
            Already registered?{" "}
            <Link href="/login" className="text-sky-400 hover:underline">
              Sign in
            </Link>
          </p>
        </Card>
      </main>
    </div>
  );
}
