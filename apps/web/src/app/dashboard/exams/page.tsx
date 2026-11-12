"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
import { BookOpen, CheckCircle2 } from "lucide-react";

export default function ExamSelectionPage() {
  const router = useRouter();
  const { exams, loading, error } = useExamsRegistry();
  const [selectedExamId, setSelectedExamId] = useState("");
  const [targetYear, setTargetYear] = useState(2026);
  const [studyMinutes, setStudyMinutes] = useState(90);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  useEffect(() => {
    if (exams.length && !selectedExamId) {
      const cbse = exams.find((e) => e.code === "CBSE_10") || exams[0];
      setSelectedExamId(cbse.id);
    }
  }, [exams, selectedExamId]);

  async function saveProfile(examId: string) {
    setSaving(true);
    setSaveErr(null);
    setSuccess(null);
    try {
      await apiFetch("/auth/profile/exam", {
        method: "POST",
        body: JSON.stringify({
          exam_id: examId,
          target_year: targetYear,
          daily_study_minutes: studyMinutes,
          preferred_language: "English",
          is_primary: true,
        }),
      });
      setSuccess("Target examination profile updated.");
    } catch (err: unknown) {
      setSaveErr(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Examination Registry &amp; Target Setup</h1>
          <p className="text-sm text-slate-400">
            Select your target Indian board or competitive examination and configure your daily
            study cadence.
          </p>
        </div>

        {loading && <LoadingState label="Fetching examination registry..." />}
        {error && <ErrorBanner message={error} />}
        {saveErr && <ErrorBanner message={saveErr} />}
        {success && <SuccessBanner message={success} />}

        {!loading && (
          <>
            <Card>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-xs text-slate-400">Target Exam</label>
                  <select
                    value={selectedExamId}
                    onChange={(e) => setSelectedExamId(e.target.value)}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                  >
                    {exams.map((ex) => (
                      <option key={ex.id} value={ex.id}>
                        {ex.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-400">Target Year</label>
                  <input
                    type="number"
                    min={2025}
                    max={2032}
                    value={targetYear}
                    onChange={(e) => setTargetYear(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-400">
                    Daily Study Budget (Minutes)
                  </label>
                  <input
                    type="number"
                    min={15}
                    max={600}
                    value={studyMinutes}
                    onChange={(e) => setStudyMinutes(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                  />
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  disabled={saving || !selectedExamId}
                  onClick={() => saveProfile(selectedExamId)}
                >
                  {saving ? "Saving..." : "Save Target Profile"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => router.push("/dashboard/exam-dna")}
                >
                  Open Exam DNA Analyzer
                </Button>
              </div>
            </Card>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {exams.map((ex) => {
                const verified = (ex.config_json?.verified_subjects?.length || 0) > 0;
                return (
                  <Card
                    key={ex.id}
                    className={selectedExamId === ex.id ? "border-sky-400/50" : ""}
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="indigo">{ex.exam_body_code || ex.category}</Badge>
                      <Badge variant={verified ? "emerald" : "amber"}>
                        {verified ? "Verified Data Ready" : "Registry Configured"}
                      </Badge>
                    </div>
                    <h3 className="mt-3 text-base font-semibold text-white">{ex.name}</h3>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {ex.subjects.map((s) => (
                        <span
                          key={s.id}
                          className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-300"
                        >
                          <BookOpen className="h-3 w-3 text-sky-400" /> {s.name}
                        </span>
                      ))}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-4 w-full"
                      onClick={() => {
                        setSelectedExamId(ex.id);
                        saveProfile(ex.id);
                      }}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Select as Target
                    </Button>
                  </Card>
                );
              })}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
