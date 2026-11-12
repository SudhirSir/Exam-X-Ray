"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  LoadingState,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { Play } from "lucide-react";

interface ProcessingRun {
  id: string;
  pipeline_name: string;
  layer: string;
  status: string;
  trigger_type: string;
  records_in: number;
  records_out: number;
  dq_passed: boolean;
  duration_seconds: number | null;
  started_at: string;
  error_message: string | null;
}

export default function AdminProcessingPage() {
  const [runs, setRuns] = useState<ProcessingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  function fetchRuns() {
    setLoading(true);
    apiFetch<ProcessingRun[]>("/admin/processing-runs")
      .then(setRuns)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchRuns();
  }, []);

  async function triggerRun() {
    setTriggering(true);
    setErr(null);
    setMsg(null);
    try {
      const r = await apiFetch<ProcessingRun>("/admin/pipeline/run", { method: "POST" });
      setMsg(
        `PySpark Medallion run completed in ${r.duration_seconds}s (${r.records_in} Bronze -> ${r.records_out} Silver, DQ Passed: ${r.dq_passed}).`
      );
      fetchRuns();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Pipeline trigger failed");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white">PySpark Medallion Pipeline Monitoring</h1>
            <p className="text-sm text-slate-400">
              Monitor Bronze → Silver → Gold Spark runs, deduplication counts, and data quality
              gates.
            </p>
          </div>
          <Button onClick={triggerRun} disabled={triggering}>
            <Play className="h-4 w-4" />
            {triggering ? "Running PySpark..." : "Run Medallion Pipeline"}
          </Button>
        </div>

        {msg && <SuccessBanner message={msg} />}
        {err && <ErrorBanner message={err} />}
        {loading && <LoadingState label="Fetching PySpark processing runs..." />}

        {!loading && (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-2.5 pr-4">Pipeline</th>
                    <th className="py-2.5 pr-4">Trigger</th>
                    <th className="py-2.5 pr-4">Status</th>
                    <th className="py-2.5 pr-4">Bronze → Silver</th>
                    <th className="py-2.5 pr-4">DQ Gate</th>
                    <th className="py-2.5">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {runs.map((r) => (
                    <tr key={r.id}>
                      <td className="py-3 pr-4 font-medium text-white">{r.pipeline_name}</td>
                      <td className="py-3 pr-4 text-slate-300">{r.trigger_type}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={r.status === "completed" ? "emerald" : "rose"}>
                          {r.status}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-slate-200">
                        {r.records_in} → {r.records_out}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={r.dq_passed ? "cyan" : "rose"}>
                          {r.dq_passed ? "Passed" : "Failed"}
                        </Badge>
                      </td>
                      <td className="py-3 text-slate-300">
                        {r.duration_seconds !== null ? `${r.duration_seconds}s` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
