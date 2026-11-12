"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  DisclaimerNote,
  EmptyState,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { useExamsRegistry } from "@/components/ExamSubjectSelector";
import { XRayReport } from "@/lib/types";
import {
  ArrowRight,
  Compass,
  Dna,
  FilePlus2,
  Radar,
  Search,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function StudentDashboardPage() {
  const { exams } = useExamsRegistry();
  const [vuln, setVuln] = useState<{
    has_data: boolean;
    disclaimer: string;
    latest_report: XRayReport | null;
  } | null>(null);
  const [progress, setProgress] = useState<{
    tests_completed: number;
    timeline: { submitted_at: string; estimated_readiness_score: number; accuracy_pct: number }[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch<{ has_data: boolean; disclaimer: string; latest_report: XRayReport | null }>(
        "/students/me/vulnerability"
      ),
      apiFetch<{
        tests_completed: number;
        timeline: { submitted_at: string; estimated_readiness_score: number; accuracy_pct: number }[];
      }>("/students/me/progress"),
    ])
      .then(([v, p]) => {
        setVuln(v);
        setProgress(p);
      })
      .finally(() => setLoading(false));
  }, []);

  const report = vuln?.latest_report;

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Student Intelligence Hub</h1>
            <p className="text-sm text-slate-400">
              Understand historical examination DNA and track your conceptual readiness.
            </p>
          </div>
          <div className="flex gap-2.5">
            <Link href="/dashboard/diagnostic">
              <Button size="sm">
                <Radar className="h-4 w-4" /> Start Diagnostic
              </Button>
            </Link>
            <Link href="/dashboard/exam-dna">
              <Button variant="secondary" size="sm">
                <Dna className="h-4 w-4" /> Exam DNA
              </Button>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <p className="text-xs text-slate-400">Diagnostics Completed</p>
            <p className="mt-1 text-2xl font-bold text-white">
              {progress?.tests_completed ?? 0}
            </p>
            <Badge variant="cyan" className="mt-2">
              Verified Tracking
            </Badge>
          </Card>
          <Card>
            <p className="text-xs text-slate-400">Estimated Readiness</p>
            <p className="mt-1 text-2xl font-bold text-sky-400">
              {report ? `${report.estimated_readiness_score}%` : "Not Assessed"}
            </p>
            <p className="mt-2 text-[11px] text-slate-400">
              {report ? report.readiness_label : "Take a diagnostic scan"}
            </p>
          </Card>
          <Card>
            <p className="text-xs text-slate-400">Active Exams in Registry</p>
            <p className="mt-1 text-2xl font-bold text-white">{exams.length}</p>
            <p className="mt-2 text-[11px] text-slate-400">
              CBSE 10 Math &amp; Science verified
            </p>
          </Card>
          <Card>
            <p className="text-xs text-slate-400">Priority Revision Focus</p>
            <p className="mt-1 truncate text-base font-semibold text-amber-300">
              {report?.recommendations?.[0]?.chapter_name || "Run Diagnostic"}
            </p>
            <Link
              href="/dashboard/roadmap"
              className="mt-2 inline-flex items-center gap-1 text-xs text-sky-400 hover:underline"
            >
              View roadmap <ArrowRight className="h-3 w-3" />
            </Link>
          </Card>
        </div>

        {loading ? (
          <LoadingState label="Loading your diagnostic readiness..." />
        ) : !report ? (
          <EmptyState
            title="No Diagnostic Scan Completed Yet"
            description="Launch a short 10-question diagnostic assessment to generate your Personal Exam X-Ray Report, weakness heatmap, and prerequisite-aware study roadmap."
            action={
              <Link href="/dashboard/diagnostic">
                <Button>
                  <Radar className="h-4 w-4" /> Take First Diagnostic Scan
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-white">
                  Readiness Estimate Trajectory
                </h2>
                <Link href="/dashboard/xray-report">
                  <Button variant="ghost" size="sm">
                    Full X-Ray Report
                  </Button>
                </Link>
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={(progress?.timeline || []).map((t, idx) => ({
                      name: `Test #${idx + 1}`,
                      readiness: t.estimated_readiness_score,
                      accuracy: t.accuracy_pct,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                    <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "12px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="readiness"
                      stroke="#38bdf8"
                      fill="#0ea5e9"
                      fillOpacity={0.2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <h2 className="mb-3 text-base font-semibold text-white">
                Top Priority Revision Recommendations
              </h2>
              <div className="space-y-3">
                {report.recommendations.slice(0, 3).map((rec) => (
                  <div
                    key={rec.topic_id}
                    className="rounded-xl border border-slate-800 bg-slate-900/70 p-3.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-white">
                        #{rec.priority_rank} {rec.topic_name}
                      </span>
                      <Badge variant="amber">{rec.estimated_hours} hrs</Badge>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-300">
                      {rec.reason_explanation}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Link href="/dashboard/questions">
            <Card className="h-full hover:border-sky-400/40 transition-colors">
              <Search className="mb-2 h-5 w-5 text-sky-400" />
              <h3 className="text-sm font-semibold text-white">Question DNA Search</h3>
              <p className="mt-1 text-xs text-slate-400">
                Find paraphrased variants and recurring conceptual patterns across board years.
              </p>
            </Card>
          </Link>
          <Link href="/dashboard/paper-generator">
            <Card className="h-full hover:border-sky-400/40 transition-colors">
              <FilePlus2 className="mb-2 h-5 w-5 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">OR-Tools Paper Generator</h3>
              <p className="mt-1 text-xs text-slate-400">
                Build custom blueprint-compliant mock papers with PDF &amp; answer key export.
              </p>
            </Card>
          </Link>
          <Link href="/dashboard/roadmap">
            <Card className="h-full hover:border-sky-400/40 transition-colors">
              <Compass className="mb-2 h-5 w-5 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white">Personal Revision Roadmap</h3>
              <p className="mt-1 text-xs text-slate-400">
                Follow prerequisite-ordered study blocks tailored to your weak chapters.
              </p>
            </Card>
          </Link>
        </div>

        {vuln?.disclaimer && <DisclaimerNote text={vuln.disclaimer} />}
      </div>
    </AppShell>
  );
}
