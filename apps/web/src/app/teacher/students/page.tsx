"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge, Card, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";

interface StudentProgressItem {
  student_pseudo_id: string;
  student_name: string;
  diagnostics_taken: number;
  latest_readiness_estimate: number | null;
  latest_accuracy_pct: number | null;
  last_active: string | null;
}

export default function TeacherStudentsPage() {
  const [items, setItems] = useState<StudentProgressItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<{ items: StudentProgressItem[] }>("/teacher/students-progress")
      .then((d) => setItems(d.items || []))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="teacher">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Student Progress Reports</h1>
          <p className="text-sm text-slate-400">
            Track diagnostic participation and latest readiness estimates across your students.
          </p>
        </div>

        {loading && <LoadingState label="Loading student progress..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && !error && (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-2.5 pr-4">Student</th>
                    <th className="py-2.5 pr-4">Pseudo ID</th>
                    <th className="py-2.5 pr-4">Diagnostics</th>
                    <th className="py-2.5 pr-4">Latest Readiness</th>
                    <th className="py-2.5">Latest Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {items.map((s) => (
                    <tr key={s.student_pseudo_id}>
                      <td className="py-3 pr-4 font-medium text-white">{s.student_name}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-slate-400">
                        {s.student_pseudo_id}
                      </td>
                      <td className="py-3 pr-4 text-slate-200">{s.diagnostics_taken}</td>
                      <td className="py-3 pr-4">
                        {s.latest_readiness_estimate !== null ? (
                          <Badge variant="cyan">{s.latest_readiness_estimate}%</Badge>
                        ) : (
                          <span className="text-xs text-slate-500">Not assessed</span>
                        )}
                      </td>
                      <td className="py-3 text-slate-200">
                        {s.latest_accuracy_pct !== null ? `${s.latest_accuracy_pct}%` : "—"}
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
