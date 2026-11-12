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
import { ExamDnaReport } from "@/lib/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = ["#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#f472b6", "#2dd4bf"];

export default function ExamDnaPage() {
  const { exams, loading: examsLoading } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [yearFrom, setYearFrom] = useState<string>("");
  const [yearTo, setYearTo] = useState<string>("");
  const [report, setReport] = useState<ExamDnaReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (exams.length && !examId) {
      const cbse = exams.find((e) => e.code === "CBSE_10") || exams[0];
      setExamId(cbse.id);
      if (cbse.subjects.length) setSubjectId(cbse.subjects[0].id);
    }
  }, [exams, examId]);

  function handleExamChange(newId: string) {
    setExamId(newId);
    const ex = exams.find((e) => e.id === newId);
    setSubjectId(ex?.subjects?.[0]?.id || "");
  }

  useEffect(() => {
    if (!examId || !subjectId) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ exam_id: examId, subject_id: subjectId });
    if (yearFrom) params.set("year_from", yearFrom);
    if (yearTo) params.set("year_to", yearTo);

    apiFetch<ExamDnaReport>(`/analytics/exam-dna?${params.toString()}`)
      .then(setReport)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [examId, subjectId, yearFrom, yearTo]);

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Exam DNA Analyzer</h1>
            <p className="text-sm text-slate-400">
              Historical weightage, difficulty curves, and recurring syllabus concepts from
              verified papers.
            </p>
          </div>
          {report?.has_data && (
            <Badge variant="cyan">
              Engine: {report.computation_source === "gold_spark_delta" ? "PySpark Gold Delta" : "Live SQL"}
            </Badge>
          )}
        </div>

        <Card>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              {!examsLoading && (
                <ExamSubjectSelector
                  exams={exams}
                  selectedExamId={examId}
                  selectedSubjectId={subjectId}
                  onExamChange={handleExamChange}
                  onSubjectChange={setSubjectId}
                />
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-400">
                  From Year
                </label>
                <input
                  type="number"
                  placeholder="All"
                  value={yearFrom}
                  onChange={(e) => setYearFrom(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 text-sm text-white"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-400">
                  To Year
                </label>
                <input
                  type="number"
                  placeholder="All"
                  value={yearTo}
                  onChange={(e) => setYearTo(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2.5 text-sm text-white"
                />
              </div>
            </div>
          </div>
        </Card>

        {loading && <LoadingState label="Computing Exam DNA from PySpark Gold layer..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && report && !report.has_data && (
          <EmptyState
            title="No Verified Examination Papers Available Yet"
            description={`No verified historical papers have been ingested for ${report.exam_name} — ${report.subject_name} in this period. EXAM X-RAY never fabricates examination statistics.`}
          />
        )}

        {!loading && report && report.has_data && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Card>
                <p className="text-xs text-slate-400">Analyzed Papers</p>
                <p className="mt-1 text-2xl font-bold text-white">
                  {report.total_analyzed_papers}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Verified Questions</p>
                <p className="mt-1 text-2xl font-bold text-sky-400">
                  {report.total_verified_questions}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Data Confidence</p>
                <p className="mt-1 text-2xl font-bold text-emerald-400">
                  {Math.round(report.data_confidence_score * 100)}%
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Chapters Covered</p>
                <p className="mt-1 text-2xl font-bold text-indigo-300">
                  {report.chapter_weightage.length}
                </p>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card>
                <h2 className="mb-4 text-base font-semibold text-white">
                  Chapter-Wise Marks Distribution (%)
                </h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={report.chapter_weightage.slice(0, 10)}
                      layout="vertical"
                      margin={{ left: 20, right: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis type="number" stroke="#94a3b8" fontSize={11} />
                      <YAxis
                        dataKey="chapter_name"
                        type="category"
                        width={140}
                        stroke="#cbd5e1"
                        fontSize={11}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          border: "1px solid #334155",
                          borderRadius: "10px",
                        }}
                      />
                      <Bar dataKey="weightage_pct" fill="#38bdf8" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card>
                <h2 className="mb-4 text-base font-semibold text-white">
                  Question Format Breakdown
                </h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={report.question_type_distribution}
                        dataKey="question_count"
                        nameKey="question_type"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ name, percent }) =>
                          `${name} (${Math.round((percent || 0) * 100)}%)`
                        }
                      >
                        {report.question_type_distribution.map((_, idx) => (
                          <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          border: "1px solid #334155",
                          borderRadius: "10px",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card>
                <h2 className="mb-4 text-base font-semibold text-white">
                  Year-Wise Competency Share (%)
                </h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={report.yearly_trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="year" stroke="#94a3b8" fontSize={12} />
                      <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          border: "1px solid #334155",
                          borderRadius: "10px",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="competency_share_pct"
                        stroke="#34d399"
                        strokeWidth={2.5}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card>
                <h2 className="mb-4 text-base font-semibold text-white">
                  Difficulty Distribution
                </h2>
                <div className="space-y-3">
                  {report.difficulty_distribution.map((d) => (
                    <div key={d.difficulty} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="capitalize text-slate-200">{d.difficulty}</span>
                        <span className="text-slate-400">
                          {d.question_count} questions ({d.share_pct}%)
                        </span>
                      </div>
                      <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-sky-400 to-indigo-500"
                          style={{ width: `${Math.min(100, d.share_pct)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <Card>
              <h2 className="mb-4 text-base font-semibold text-white">
                Recurring Concepts &amp; Source Citations
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                    <tr>
                      <th className="py-2.5 pr-4">Chapter</th>
                      <th className="py-2.5 pr-4">Concept</th>
                      <th className="py-2.5 pr-4">Years</th>
                      <th className="py-2.5 pr-4">Marks</th>
                      <th className="py-2.5">Source References</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {report.recurring_concepts.map((rc, i) => (
                      <tr key={i}>
                        <td className="py-3 pr-4 font-medium text-white">{rc.chapter_name}</td>
                        <td className="py-3 pr-4 text-slate-300">{rc.topic_name}</td>
                        <td className="py-3 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {rc.years_appeared.map((y) => (
                              <Badge key={y} variant="cyan">
                                {y}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 pr-4 text-sky-300">{rc.total_marks_across_years}</td>
                        <td className="py-3 text-xs text-slate-400">
                          {rc.source_references.join(" • ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card>
              <h2 className="mb-3 text-base font-semibold text-white">
                Verified Source Coverage ({report.sources.length} Papers)
              </h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {report.sources.map((src) => (
                  <div
                    key={src.paper_id}
                    className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs"
                  >
                    <div>
                      <p className="font-medium text-white">{src.title}</p>
                      <p className="text-slate-400">
                        {src.question_count} questions • Confidence{" "}
                        {Math.round(src.extraction_confidence * 100)}%
                      </p>
                    </div>
                    <Badge variant={src.is_verified ? "emerald" : "amber"}>
                      {src.is_verified ? "Verified" : "Pending"}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>

            <DisclaimerNote text={report.disclaimer} />
          </>
        )}
      </div>
    </AppShell>
  );
}
