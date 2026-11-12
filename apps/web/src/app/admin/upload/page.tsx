"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ExamSubjectSelector, useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { Upload } from "lucide-react";

interface UploadRes {
  paper_id: string;
  questions_extracted: number;
  pages_extracted: number;
  spark_run_id: string;
  spark_dq_passed: boolean;
}

export default function AdminUploadPage() {
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [year, setYear] = useState(2025);
  const [setCode, setSetCode] = useState("SQP-1");
  const [sourceUrl, setSourceUrl] = useState("https://cbseacademic.nic.in");
  const [autoVerify, setAutoVerify] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadRes | null>(null);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF question paper to upload.");
      return;
    }
    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("exam_id", examId);
      form.append("subject_id", subjectId);
      form.append("year", String(year));
      form.append("set_code", setCode);
      form.append("source_url", sourceUrl);
      form.append("auto_verify", String(autoVerify));
      form.append("file", file);

      const res = await apiFetch<UploadRes>("/admin/documents/upload", {
        method: "POST",
        body: form,
      });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Document Ingestion &amp; PySpark Trigger</h1>
          <p className="text-sm text-slate-400">
            Upload a verified PDF question paper. EXAM X-RAY validates SHA-256 uniqueness, extracts
            questions with PyMuPDF, maps syllabus topics, and refreshes PySpark Gold Exam DNA.
          </p>
        </div>

        {error && <ErrorBanner message={error} />}
        {result && (
          <SuccessBanner
            message={`Ingested ${result.questions_extracted} questions across ${result.pages_extracted} page(s). PySpark Medallion DQ Passed: ${result.spark_dq_passed ? "YES" : "NO"}.`}
          />
        )}

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <ExamSubjectSelector
              exams={exams}
              selectedExamId={examId}
              selectedSubjectId={subjectId}
              onExamChange={handleExamChange}
              onSubjectChange={setSubjectId}
            />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-slate-400">Examination Year</label>
                <input
                  type="number"
                  min={2005}
                  max={2035}
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-400">Set Code</label>
                <input
                  value={setCode}
                  onChange={(e) => setSetCode(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-400">Official Source URL</label>
                <input
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs text-slate-400">Question Paper PDF</label>
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full rounded-xl border border-dashed border-slate-700 bg-slate-900/70 p-4 text-sm text-slate-300"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={autoVerify}
                onChange={(e) => setAutoVerify(e.target.checked)}
              />
              Mark extracted questions as verified immediately (otherwise route to human review queue)
            </label>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={uploading || !examId || !subjectId}>
                <Upload className="h-4 w-4" />
                {uploading ? "Extracting & Running PySpark..." : "Upload & Process with PySpark"}
              </Button>
              {result && (
                <Link href="/dashboard/exam-dna">
                  <Button variant="secondary" type="button">
                    View Updated Exam DNA
                  </Button>
                </Link>
              )}
            </div>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
