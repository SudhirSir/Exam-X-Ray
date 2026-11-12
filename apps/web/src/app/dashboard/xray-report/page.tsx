"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  DisclaimerNote,
  EmptyState,
  ErrorBanner,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { XRayReport } from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Radar } from "lucide-react";

function XRayReportContent() {
  const searchParams = useSearchParams();
  const testId = searchParams.get("test_id");
  const [report, setReport] = useState<XRayReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    if (testId) {
      apiFetch<XRayReport>(`/diagnostics/${testId}/results`)
        .then(setReport)
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    } else {
      apiFetch<{ has_data: boolean; latest_report: XRayReport | null }>(
        "/students/me/vulnerability"
      )
        .then((res) => setReport(res.latest_report))
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [testId]);

  if (loading) return <LoadingState label="Generating Personal Exam X-Ray Report..." />;
  if (error) return <ErrorBanner message={error} />;
  if (!report) {
    return (
      <EmptyState
        title="No X-Ray Report Available"
        description="Complete a diagnostic assessment first to inspect your chapter mastery heatmap, mistake breakdown, and explainable revision roadmap."
        action={
          <Link href="/dashboard/diagnostic">
            <Button>
              <Radar className="h-4 w-4" /> Start Diagnostic Assessment
            </Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Personal Exam X-Ray Report</h1>
          <p className="text-sm text-slate-400">
            Diagnostic readiness estimate, chapter mastery heatmap, and explainable priorities.
          </p>
        </div>
        <Badge variant="cyan">{report.readiness_label}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="xray-glow">
          <p className="text-xs text-slate-400">Estimated Readiness</p>
          <p className="mt-1 text-3xl font-extrabold text-sky-400">
            {report.estimated_readiness_score}%
          </p>
        </Card>
        <Card>
          <p className="text-xs text-slate-400">Diagnostic Accuracy</p>
          <p className="mt-1 text-3xl font-bold text-white">{report.accuracy_pct}%</p>
          <p className="text-xs text-slate-400">
            {report.correct_count}/{report.total_questions} correct
          </p>
        </Card>
        <Card>
          <p className="text-xs text-slate-400">Avg Time / Question</p>
          <p className="mt-1 text-3xl font-bold text-emerald-400">
            {report.avg_time_per_question_seconds}s
          </p>
        </Card>
        <Card>
          <p className="text-xs text-slate-400">Next Practice Focus</p>
          <p className="mt-1 truncate text-base font-semibold text-amber-300">
            {report.next_practice_session?.focus_chapter || "Balanced Review"}
          </p>
          <p className="text-xs text-slate-400">
            {report.next_practice_session?.suggested_minutes || 20} min session
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-base font-semibold text-white">Chapter Mastery Heatmap</h2>
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {report.chapter_heatmap.map((ch) => {
              const color =
                ch.avg_mastery_pct >= 75
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : ch.avg_mastery_pct >= 45
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                  : "border-rose-500/40 bg-rose-500/10 text-rose-300";
              return (
                <div key={ch.chapter_name} className={`rounded-xl border p-3.5 ${color}`}>
                  <p className="text-sm font-semibold text-white">{ch.chapter_name}</p>
                  <p className="mt-1 text-lg font-bold">{ch.avg_mastery_pct}% mastery</p>
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <h2 className="mb-4 text-base font-semibold text-white">
            Difficulty &amp; Question-Type Performance
          </h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={report.difficulty_performance}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="difficulty" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "10px",
                  }}
                />
                <Bar dataKey="accuracy_pct" name="Accuracy %" fill="#38bdf8" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Explainable Recommendations */}
      <Card>
        <h2 className="mb-4 text-base font-semibold text-white">
          Priority Revision List (With Prerequisite &amp; Evidence Explanations)
        </h2>
        <div className="space-y-3">
          {report.recommendations.map((rec) => (
            <div
              key={rec.topic_id}
              className="rounded-xl border border-slate-800 bg-slate-900/70 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="cyan">Priority #{rec.priority_rank}</Badge>
                  <span className="text-sm font-semibold text-white">
                    {rec.topic_name} ({rec.chapter_name})
                  </span>
                </div>
                <Badge variant="amber">Est. {rec.estimated_hours} hrs</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-200">{rec.reason_explanation}</p>
            </div>
          ))}
        </div>
      </Card>

      {report.mistake_breakdown.length > 0 && (
        <Card>
          <h2 className="mb-3 text-base font-semibold text-white">Mistake Pattern Analysis</h2>
          <div className="flex flex-wrap gap-3">
            {report.mistake_breakdown.map((m) => (
              <div
                key={m.mistake_type}
                className="rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2.5 text-sm"
              >
                <span className="capitalize text-slate-300">
                  {m.mistake_type.replace(/_/g, " ")}:
                </span>{" "}
                <strong className="text-rose-300">{m.count}</strong>
              </div>
            ))}
          </div>
        </Card>
      )}

      <DisclaimerNote text={report.estimate_disclaimer} />
    </div>
  );
}

export default function XRayReportPage() {
  return (
    <AppShell section="student">
      <Suspense fallback={<LoadingState label="Loading X-Ray Report..." />}>
        <XRayReportContent />
      </Suspense>
    </AppShell>
  );
}
