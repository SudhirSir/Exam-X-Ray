"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Button, Card, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { Activity, Database, FileCheck2, Upload } from "lucide-react";

interface DataQualitySummary {
  total_questions: number;
  verified_questions: number;
  pending_review_questions: number;
  unmapped_topic_questions: number;
  latest_spark_run?: {
    id: string;
    status: string;
    records_in: number;
    records_out: number;
    dq_passed: boolean;
    duration_seconds: number | null;
  } | null;
}

export default function AdminOverviewPage() {
  const [dq, setDq] = useState<DataQualitySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DataQualitySummary>("/admin/data-quality")
      .then(setDq)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">Admin Operations &amp; Lakehouse Console</h1>
            <p className="text-sm text-slate-400">
              Ingest verified PDFs, monitor PySpark Bronze/Silver/Gold runs, and curate question
              quality.
            </p>
          </div>
          <Link href="/admin/upload">
            <Button size="sm">
              <Upload className="h-4 w-4" /> Upload Exam PDF
            </Button>
          </Link>
        </div>

        {loading && <LoadingState label="Loading lakehouse health..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && dq && (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Card>
                <p className="text-xs text-slate-400">Total Questions</p>
                <p className="mt-1 text-2xl font-bold text-white">{dq.total_questions}</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Verified Questions</p>
                <p className="mt-1 text-2xl font-bold text-emerald-400">
                  {dq.verified_questions}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Pending Review Queue</p>
                <p className="mt-1 text-2xl font-bold text-amber-300">
                  {dq.pending_review_questions}
                </p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Latest PySpark Run</p>
                <div className="mt-2">
                  <Badge variant={dq.latest_spark_run?.dq_passed ? "emerald" : "cyan"}>
                    {dq.latest_spark_run
                      ? `${dq.latest_spark_run.status} (${dq.latest_spark_run.duration_seconds}s)`
                      : "Not Run Yet"}
                  </Badge>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Link href="/admin/upload">
                <Card className="hover:border-sky-400/40 transition-colors">
                  <Upload className="mb-2 h-5 w-5 text-sky-400" />
                  <h2 className="text-base font-semibold text-white">Document Upload</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    SHA-256 deduplicated PDF ingestion + PyMuPDF + PySpark Gold refresh.
                  </p>
                </Card>
              </Link>
              <Link href="/admin/processing">
                <Card className="hover:border-sky-400/40 transition-colors">
                  <Database className="mb-2 h-5 w-5 text-indigo-400" />
                  <h2 className="text-base font-semibold text-white">PySpark Monitoring</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Trigger Medallion runs and inspect Bronze/Silver/Gold counts.
                  </p>
                </Card>
              </Link>
              <Link href="/admin/verification">
                <Card className="hover:border-sky-400/40 transition-colors">
                  <FileCheck2 className="mb-2 h-5 w-5 text-emerald-400" />
                  <h2 className="text-base font-semibold text-white">Question Verification</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    Approve or edit newly extracted questions before publishing analytics.
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
