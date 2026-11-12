"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Card, EmptyState, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function TeacherPerformancePage() {
  const [chapters, setChapters] = useState<
    { chapter_name: string; avg_accuracy_pct: number; student_samples: number }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<{
      chapter_performance: { chapter_name: string; avg_accuracy_pct: number; student_samples: number }[];
    }>("/teacher/overview")
      .then((d) => setChapters(d.chapter_performance || []))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="teacher">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Class Chapter Performance</h1>
          <p className="text-sm text-slate-400">
            Aggregated topic accuracy derived from real student diagnostic submissions.
          </p>
        </div>

        {loading && <LoadingState label="Aggregating class accuracy..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && chapters.length === 0 && (
          <EmptyState
            title="No Cohort Diagnostic Data Yet"
            description="Once students complete diagnostic assessments, chapter-level accuracy trends will appear here."
          />
        )}

        {!loading && chapters.length > 0 && (
          <Card>
            <h2 className="mb-4 text-base font-semibold text-white">
              Average Accuracy by Chapter (%)
            </h2>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chapters}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="chapter_name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: "10px",
                    }}
                  />
                  <Bar dataKey="avg_accuracy_pct" name="Avg Accuracy %" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
