"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Button, Card, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { BarChart3, FilePlus2, Users } from "lucide-react";

interface TeacherOverview {
  total_students: number;
  diagnostics_completed: number;
  class_avg_readiness_pct: number;
  teacher_papers_created: number;
  chapter_performance: { chapter_name: string; avg_accuracy_pct: number; student_samples: number }[];
}

export default function TeacherOverviewPage() {
  const [data, setData] = useState<TeacherOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<TeacherOverview>("/teacher/overview")
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="teacher">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">Teacher Command Center</h1>
            <p className="text-sm text-slate-400">
              Monitor cohort topic mastery, identify collective weak chapters, and generate custom
              assessments.
            </p>
          </div>
          <Link href="/teacher/tests">
            <Button size="sm">
              <FilePlus2 className="h-4 w-4" /> Create Class Test
            </Button>
          </Link>
        </div>

        {loading && <LoadingState label="Loading cohort analytics..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && data && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Card>
                <p className="text-xs text-slate-400">Registered Students</p>
                <p className="mt-1 text-2xl font-bold text-white">{data.total_students}</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Diagnostics Completed</p>
                <p className="mt-1 text-2xl font-bold text-sky-400">
                  {data.diagnostics_completed}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Class Avg Readiness (Est.)</p>
                <p className="mt-1 text-2xl font-bold text-emerald-400">
                  {data.class_avg_readiness_pct}%
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Papers Created</p>
                <p className="mt-1 text-2xl font-bold text-indigo-300">
                  {data.teacher_papers_created}
                </p>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Link href="/teacher/performance">
                <Card className="hover:border-sky-400/40 transition-colors">
                  <BarChart3 className="mb-2 h-5 w-5 text-sky-400" />
                  <h2 className="text-base font-semibold text-white">Class Performance Heatmap</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Inspect chapter-by-chapter accuracy across all student diagnostics.
                  </p>
                </Card>
              </Link>
              <Link href="/teacher/students">
                <Card className="hover:border-sky-400/40 transition-colors">
                  <Users className="mb-2 h-5 w-5 text-emerald-400" />
                  <h2 className="text-base font-semibold text-white">Student Progress Reports</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Review individual diagnostic participation and latest readiness estimates.
                  </p>
                </Card>
              </Link>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
