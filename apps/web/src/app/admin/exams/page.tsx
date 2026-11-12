"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  LoadingState,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";

export default function AdminExamsPage() {
  const { exams, loading } = useExamsRegistry();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("board");
  const [classLevel, setClassLevel] = useState("Class 12");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function createExam(e: React.FormEvent) {
    e.preventDefault();
    if (!exams.length) return;
    setErr(null);
    setMsg(null);
    try {
      await apiFetch("/exams", {
        method: "POST",
        body: JSON.stringify({
          exam_body_id: exams[0].exam_body_id,
          code,
          name,
          category,
          class_level: classLevel,
        }),
      });
      setMsg(`Registered new examination '${name}' (${code}).`);
      setCode("");
      setName("");
    } catch (error: unknown) {
      setErr(error instanceof Error ? error.message : "Failed to register exam");
    }
  }

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Examination Registry Management</h1>
          <p className="text-sm text-slate-400">
            Configure Indian board and competitive examinations dynamically without code changes.
          </p>
        </div>

        {msg && <SuccessBanner message={msg} />}
        {err && <ErrorBanner message={err} />}

        <Card>
          <h2 className="mb-4 text-base font-semibold text-white">Register New Examination</h2>
          <form onSubmit={createExam} className="grid grid-cols-1 gap-3 sm:grid-cols-4">
            <input
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Code (e.g. GATE_CS)"
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            />
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Exam Name"
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            >
              <option value="board">Board</option>
              <option value="competitive">Competitive</option>
              <option value="govt">Government</option>
            </select>
            <Button type="submit">Add Examination</Button>
          </form>
        </Card>

        {loading ? (
          <LoadingState label="Loading registry..." />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {exams.map((ex) => (
              <Card key={ex.id}>
                <div className="flex items-center justify-between">
                  <Badge variant="cyan">{ex.code}</Badge>
                  <Badge variant="indigo">{ex.category}</Badge>
                </div>
                <h3 className="mt-2 text-base font-semibold text-white">{ex.name}</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Subjects linked: {ex.subjects.map((s) => s.name).join(", ") || "None yet"}
                </p>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
