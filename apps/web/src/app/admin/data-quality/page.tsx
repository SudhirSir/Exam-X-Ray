"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Card, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";

interface DQResponse {
  total_questions: number;
  verified_questions: number;
  pending_review_questions: number;
  unmapped_topic_questions: number;
  latest_spark_run?: {
    id: string;
    dq_passed: boolean;
    dq_report_json?: Record<string, unknown> | null;
  } | null;
}

export default function AdminDataQualityPage() {
  const [dq, setDq] = useState<DQResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DQResponse>("/admin/data-quality")
      .then(setDq)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Quality &amp; Provenance Monitoring</h1>
          <p className="text-sm text-slate-400">
            Track schema validation, topic mapping completeness, and PySpark Silver DQ gates.
          </p>
        </div>

        {loading && <LoadingState label="Auditing data quality..." />}
        {err && <ErrorBanner message={err} />}

        {!loading && dq && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Card>
                <p className="text-xs text-slate-400">Total Questions</p>
                <p className="mt-1 text-2xl font-bold text-white">{dq.total_questions}</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Verified</p>
                <p className="mt-1 text-2xl font-bold text-emerald-400">{dq.verified_questions}</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Pending Review</p>
                <p className="mt-1 text-2xl font-bold text-amber-300">
                  {dq.pending_review_questions}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Unmapped Topics</p>
                <p className="mt-1 text-2xl font-bold text-rose-300">
                  {dq.unmapped_topic_questions}
                </p>
              </Card>
            </div>

            <Card>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold text-white">
                  Latest PySpark Silver DQ Report
                </h2>
                <Badge variant={dq.latest_spark_run?.dq_passed ? "emerald" : "amber"}>
                  {dq.latest_spark_run?.dq_passed ? "DQ Gate Passed" : "No Spark Run Recorded"}
                </Badge>
              </div>
              <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-sky-300">
                {JSON.stringify(dq.latest_spark_run?.dq_report_json || {}, null, 2)}
              </pre>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
