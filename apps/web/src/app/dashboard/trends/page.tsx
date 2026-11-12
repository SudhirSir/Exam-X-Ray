"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ExamSubjectSelector, useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Card,
  DisclaimerNote,
  EmptyState,
  ErrorBanner,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface TrendRes {
  year_a: number;
  year_b: number;
  has_data: boolean;
  competency_shift_pct: number;
  chapter_shifts: { chapter_name: string; year_a_pct: number; year_b_pct: number; delta_pct: number }[];
  question_type_shifts: { question_type: string; year_a_pct: number; year_b_pct: number; delta_pct: number }[];
  disclaimer: string;
}

interface PatternChangeRes {
  previous_version?: { academic_year: string; total_marks: number; competency_share_pct: number } | null;
  current_version?: { academic_year: string; total_marks: number; competency_share_pct: number } | null;
  changes: {
    from_year: string;
    to_year: string;
    change_category: string;
    summary: string;
    previous_value: unknown;
    current_value: unknown;
    impact_on_preparation: string;
    supporting_sources: string[];
  }[];
  disclaimer: string;
}

export default function TrendsPage() {
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [yearA, setYearA] = useState(2022);
  const [yearB, setYearB] = useState(2024);
  const [trends, setTrends] = useState<TrendRes | null>(null);
  const [patterns, setPatterns] = useState<PatternChangeRes | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (exams.length && !examId) {
      const cbse = exams.find((e) => e.code === "CBSE_10") || exams[0];
      setExamId(cbse.id);
      if (cbse.subjects.length) setSubjectId(cbse.subjects[0].id);
    }
  }, [exams, examId]);

  function handleExamChange(id: string) {
    setExamId(id);
    const ex = exams.find((e) => e.id === id);
    setSubjectId(ex?.subjects?.[0]?.id || "");
  }

  useEffect(() => {
    if (!examId || !subjectId) return;
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch<TrendRes>(
        `/analytics/yearly-trends?exam_id=${examId}&subject_id=${subjectId}&year_a=${yearA}&year_b=${yearB}`
      ),
      apiFetch<PatternChangeRes>(
        `/analytics/pattern-changes?exam_id=${examId}&subject_id=${subjectId}`
      ),
    ])
      .then(([t, p]) => {
        setTrends(t);
        setPatterns(p);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [examId, subjectId, yearA, yearB]);

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Exam Trend Intelligence &amp; Pattern Change Detector
          </h1>
          <p className="text-sm text-slate-400">
            Compare historical weightage across two examination years and review official
            blueprint &amp; syllabus revisions.
          </p>
        </div>

        <Card>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ExamSubjectSelector
                exams={exams}
                selectedExamId={examId}
                selectedSubjectId={subjectId}
                onExamChange={handleExamChange}
                onSubjectChange={setSubjectId}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs uppercase text-slate-400">Year A</label>
                <select
                  value={yearA}
                  onChange={(e) => setYearA(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                >
                  {[2022, 2023, 2024, 2025].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs uppercase text-slate-400">Year B</label>
                <select
                  value={yearB}
                  onChange={(e) => setYearB(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                >
                  {[2022, 2023, 2024, 2025].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </Card>

        {loading && <LoadingState label="Comparing examination years & official blueprints..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && trends && !trends.has_data && (
          <EmptyState
            title="Insufficient Historical Data for Comparison"
            description="Select CBSE Class 10 Mathematics or Science (2022 vs 2024) or ingest additional year papers in the Admin console."
          />
        )}

        {!loading && trends && trends.has_data && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Card>
                <p className="text-xs text-slate-400">Comparison Window</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {trends.year_a} vs {trends.year_b}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Competency Question Shift</p>
                <p className="mt-1 text-xl font-bold text-emerald-400">
                  {trends.competency_shift_pct >= 0 ? "+" : ""}
                  {trends.competency_shift_pct}%
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Blueprint Changes Detected</p>
                <p className="mt-1 text-xl font-bold text-sky-400">
                  {patterns?.changes.length || 0}
                </p>
              </Card>
            </div>

            <Card>
              <h2 className="mb-4 text-base font-semibold text-white">
                Chapter Weightage Comparison ({trends.year_a} vs {trends.year_b})
              </h2>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trends.chapter_shifts.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="chapter_name" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "10px",
                      }}
                    />
                    <Legend />
                    <Bar dataKey="year_a_pct" name={`${trends.year_a} (%)`} fill="#818cf8" />
                    <Bar dataKey="year_b_pct" name={`${trends.year_b} (%)`} fill="#38bdf8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {patterns && patterns.changes.length > 0 && (
              <Card>
                <h2 className="mb-4 text-base font-semibold text-white">
                  Official Blueprint &amp; Syllabus Pattern Changes
                </h2>
                <div className="space-y-3">
                  {patterns.changes.map((c, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl border border-slate-800 bg-slate-900/70 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <Badge variant="amber">{c.change_category.replace(/_/g, " ")}</Badge>
                        <span className="text-xs text-slate-400">
                          {c.from_year} → {c.to_year}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-medium text-white">{c.summary}</p>
                      <p className="mt-1 text-xs text-sky-300">
                        Preparation Impact: {c.impact_on_preparation}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-400">
                        Sources: {c.supporting_sources.join(", ")}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            <DisclaimerNote text={trends.disclaimer} />
          </>
        )}
      </div>
    </AppShell>
  );
}
