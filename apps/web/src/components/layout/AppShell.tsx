"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  Compass,
  Database,
  Dna,
  FileCheck2,
  FilePlus2,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Radar,
  ScanLine,
  Search,
  Settings,
  ShieldCheck,
  TrendingUp,
  Upload,
  User as UserIcon,
  Users,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Badge, Button, LoadingState } from "@/components/ui/primitives";

const STUDENT_NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/exams", label: "Exam Registry", icon: BookOpen },
  { href: "/dashboard/exam-dna", label: "Exam DNA Analyzer", icon: Dna },
  { href: "/dashboard/questions", label: "Question DNA Search", icon: Search },
  { href: "/dashboard/trends", label: "Trend Intelligence", icon: TrendingUp },
  { href: "/dashboard/diagnostic", label: "Diagnostic Scan", icon: Radar },
  { href: "/dashboard/xray-report", label: "Personal X-Ray Report", icon: Activity },
  { href: "/dashboard/roadmap", label: "Revision Roadmap", icon: Compass },
  { href: "/dashboard/paper-generator", label: "Paper Generator", icon: FilePlus2 },
  { href: "/dashboard/saved-papers", label: "Saved Papers", icon: FileText },
  { href: "/dashboard/profile", label: "Student Profile", icon: UserIcon },
];

const TEACHER_NAV = [
  { href: "/teacher", label: "Teacher Overview", icon: GraduationCap },
  { href: "/teacher/performance", label: "Class Performance", icon: BarChart3 },
  { href: "/teacher/tests", label: "Create Practice Test", icon: FilePlus2 },
  { href: "/teacher/students", label: "Student Progress", icon: Users },
];

const ADMIN_NAV = [
  { href: "/admin", label: "Admin Overview", icon: ShieldCheck },
  { href: "/admin/upload", label: "Document Upload", icon: Upload },
  { href: "/admin/processing", label: "PySpark Monitoring", icon: Database },
  { href: "/admin/verification", label: "Question Verification", icon: FileCheck2 },
  { href: "/admin/exams", label: "Exam Management", icon: Settings },
  { href: "/admin/data-quality", label: "Data Quality", icon: Activity },
];

export function AppShell({
  children,
  section = "student",
}: {
  children: React.ReactNode;
  section?: "student" | "teacher" | "admin";
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems =
    section === "admin"
      ? ADMIN_NAV
      : section === "teacher"
      ? TEACHER_NAV
      : STUDENT_NAV;

  async function handleLogout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // ignore
    }
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050914] p-6">
        <div className="w-full max-w-md">
          <LoadingState label="Verifying your EXAM X-RAY session..." />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#050914] p-6 text-center">
        <div className="xray-surface max-w-md rounded-2xl p-8">
          <ScanLine className="mx-auto mb-3 h-10 w-10 text-sky-400" />
          <h2 className="text-xl font-bold text-white">Sign in required</h2>
          <p className="mt-2 text-sm text-slate-400">
            Access personalized Exam DNA, vulnerability diagnostics, and smart paper generation.
          </p>
          <div className="mt-5 flex justify-center gap-3">
            <Link href="/login">
              <Button>Sign In</Button>
            </Link>
            <Link href="/register">
              <Button variant="secondary">Create Account</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between">
      <div>
        <div className="flex items-center justify-between px-4 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-blue-600">
              <ScanLine className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-bold tracking-tight text-white">
              EXAM <span className="text-sky-400">X-RAY</span>
            </span>
          </Link>
          <Badge variant="cyan">{user.role}</Badge>
        </div>

        <div className="mx-3 mb-3 flex gap-1 rounded-xl bg-slate-900/90 p-1 text-xs">
          <Link
            href="/dashboard"
            className={`flex-1 rounded-lg py-1.5 text-center font-medium ${
              section === "student" ? "bg-sky-500/20 text-sky-300" : "text-slate-400 hover:text-white"
            }`}
          >
            Student
          </Link>
          {(user.role === "teacher" || user.role === "admin") && (
            <Link
              href="/teacher"
              className={`flex-1 rounded-lg py-1.5 text-center font-medium ${
                section === "teacher" ? "bg-sky-500/20 text-sky-300" : "text-slate-400 hover:text-white"
              }`}
            >
              Teacher
            </Link>
          )}
          {user.role === "admin" && (
            <Link
              href="/admin"
              className={`flex-1 rounded-lg py-1.5 text-center font-medium ${
                section === "admin" ? "bg-sky-500/20 text-sky-300" : "text-slate-400 hover:text-white"
              }`}
            >
              Admin
            </Link>
          )}
        </div>

        <nav className="space-y-1 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-sky-500/15 text-sky-300 border border-sky-500/30"
                    : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-slate-800/80 p-4">
        <div className="mb-3 truncate text-xs">
          <p className="font-medium text-white truncate">{user.full_name}</p>
          <p className="text-slate-400 truncate">{user.email}</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          onClick={handleLogout}
        >
          <LogOut className="h-3.5 w-3.5" /> Sign Out
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-[#050914]">
      <aside className="hidden w-64 shrink-0 border-r border-slate-800/80 bg-[#070d1d] lg:block">
        {sidebarContent}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="w-64 bg-[#070d1d] border-r border-slate-800">
            {sidebarContent}
          </div>
          <div
            className="flex-1 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800/80 bg-[#070d1d]/80 px-4 py-3 lg:hidden">
          <button
            aria-label="Open Navigation"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-2 text-slate-300 hover:bg-slate-800"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="text-sm font-bold text-white">
            EXAM <span className="text-sky-400">X-RAY</span>
          </span>
          <Badge variant="cyan">{user.role}</Badge>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
