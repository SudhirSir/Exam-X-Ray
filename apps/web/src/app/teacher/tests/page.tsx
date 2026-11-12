"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ExamSubjectSelector, useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  LoadingState,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch, getExportUrl } from "@/lib/api";
import { GeneratedPaper } from "@/lib/types";
import { Download, FilePlus2 } from "lucide-react";

export default function TeacherTestCreationPage() {
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [title, setTitle] = useState("Class 10 Weekly Unit Assessment");
  const [totalMarks, setTotalMarks] = useState(30);
  const [questionCount, setQuestionCount] = useState(12);
  const [paper, setPaper] = useState<GeneratedPaper | null>(null);
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

  async function createTest() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<GeneratedPaper>("/papers/generate", {
        method: "POST",
        body: JSON.stringify({
          exam_id: examId,
          subject_id: subjectId,
          title,
          total_marks: totalMarks,
          question_count: questionCount,
          time_limit_minutes: 60,
          language: "English",
        }),
      });
      setPaper(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Test creation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell section="teacher">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Teacher Test &amp; Blueprint Builder</h1>
          <p className="text-sm text-slate-400">
            Generate balanced classroom assessments with answer keys using OR-Tools optimization.
          </p>
        </div>

        <Card className="space-y-4">
          <ExamSubjectSelector
            exams={exams}
            selectedExamId={examId}
            selectedSubjectId={subjectId}
            onExamChange={handleExamChange}
            onSubjectChange={setSubjectId}
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-slate-400">Test Title</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Total Marks</label>
              <input
                type="number"
                value={totalMarks}
                onChange={(e) => setTotalMarks(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Questions</label>
              <input
                type="number"
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <Button onClick={createTest} disabled={loading || !examId || !subjectId}>
            <FilePlus2 className="h-4 w-4" /> Generate Classroom Test
          </Button>
        </Card>

        {loading && <LoadingState label="Optimizing test blueprint..." />}
        {error && <ErrorBanner message={error} />}

        {paper && (
          <div className="space-y-4">
            <SuccessBanner
              message={`Generated '${paper.title}' (${paper.actual_marks} marks, ${paper.questions.length} questions).`}
            />
            <Card className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <a href={getExportUrl(paper.id, "paper_pdf")} target="_blank" rel="noreferrer">
                  <Button variant="secondary" size="sm">
                    <Download className="h-4 w-4" /> Question Paper PDF
                  </Button>
                </a>
                <a href={getExportUrl(paper.id, "answer_key_pdf")} target="_blank" rel="noreferrer">
                  <Button variant="secondary" size="sm">
                    <Download className="h-4 w-4" /> Teacher Answer Key PDF
                  </Button>
                </a>
              </div>
              <div className="space-y-2 pt-2">
                {paper.questions.map((q) => (
                  <div key={q.question_id} className="rounded-lg bg-slate-900/70 p-3 text-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="cyan">Q{q.order_index}</Badge>
                      <Badge variant="default">{q.allocated_marks}m</Badge>
                      <span className="text-xs text-slate-400">{q.chapter_name}</span>
                    </div>
                    <p className="text-slate-100">{q.question_text}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>
    </AppShell>
  );
}
