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
import { Download, FilePlus2, RefreshCw } from "lucide-react";

export default function PaperGeneratorPage() {
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [totalMarks, setTotalMarks] = useState(25);
  const [questionCount, setQuestionCount] = useState(10);
  const [timeLimit, setTimeLimit] = useState(60);
  const [easyPct, setEasyPct] = useState(30);
  const [medPct, setMedPct] = useState(50);
  const [hardPct, setHardPct] = useState(20);
  const [paper, setPaper] = useState<GeneratedPaper | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attemptAnswers, setAttemptAnswers] = useState<Record<string, string>>({});
  const [attemptResult, setAttemptResult] = useState<{
    score_obtained: number;
    max_score: number;
    accuracy_pct: number;
  } | null>(null);

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

  async function generatePaper() {
    setLoading(true);
    setError(null);
    setAttemptResult(null);
    setAttemptAnswers({});
    try {
      const total = Math.max(1, easyPct + medPct + hardPct);
      const data = await apiFetch<GeneratedPaper>("/papers/generate", {
        method: "POST",
        body: JSON.stringify({
          exam_id: examId,
          subject_id: subjectId,
          total_marks: totalMarks,
          question_count: questionCount,
          time_limit_minutes: timeLimit,
          difficulty_distribution: {
            easy: easyPct / total,
            medium: medPct / total,
            hard: hardPct / total,
          },
          language: "English",
          include_ai_generated: false,
        }),
      });
      setPaper(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Paper generation failed");
    } finally {
      setLoading(false);
    }
  }

  async function submitAttempt() {
    if (!paper) return;
    try {
      const res = await apiFetch<{
        score_obtained: number;
        max_score: number;
        accuracy_pct: number;
      }>(`/papers/${paper.id}/attempt`, {
        method: "POST",
        body: JSON.stringify({
          time_taken_seconds: 600,
          answers: attemptAnswers,
        }),
      });
      setAttemptResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Attempt grading failed");
    }
  }

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Smart Question Paper Generator</h1>
          <p className="text-sm text-slate-400">
            Powered by Google OR-Tools CP-SAT constraint optimization—ensuring zero duplicate
            clusters, balanced topic coverage, and PDF export.
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

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div>
              <label className="mb-1 block text-xs text-slate-400">Target Marks</label>
              <input
                type="number"
                min={5}
                max={80}
                value={totalMarks}
                onChange={(e) => setTotalMarks(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Questions</label>
              <input
                type="number"
                min={3}
                max={40}
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Time (min)</label>
              <input
                type="number"
                min={15}
                max={240}
                value={timeLimit}
                onChange={(e) => setTimeLimit(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Easy %</label>
              <input
                type="number"
                min={0}
                max={100}
                value={easyPct}
                onChange={(e) => setEasyPct(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Medium %</label>
              <input
                type="number"
                min={0}
                max={100}
                value={medPct}
                onChange={(e) => setMedPct(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-400">Hard %</label>
              <input
                type="number"
                min={0}
                max={100}
                value={hardPct}
                onChange={(e) => setHardPct(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={generatePaper} disabled={loading || !examId || !subjectId}>
              <FilePlus2 className="h-4 w-4" />{" "}
              {paper ? "Regenerate Optimized Paper" : "Generate Question Paper"}
            </Button>
            {paper && (
              <>
                <a href={getExportUrl(paper.id, "paper_pdf")} target="_blank" rel="noreferrer">
                  <Button variant="secondary" type="button">
                    <Download className="h-4 w-4" /> Download Paper PDF
                  </Button>
                </a>
                <a
                  href={getExportUrl(paper.id, "answer_key_pdf")}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button variant="secondary" type="button">
                    <Download className="h-4 w-4" /> Download Answer Key PDF
                  </Button>
                </a>
              </>
            )}
          </div>
        </Card>

        {loading && <LoadingState label="Solving blueprint constraints with Google OR-Tools..." />}
        {error && <ErrorBanner message={error} />}
        {attemptResult && (
          <SuccessBanner
            message={`Paper Attempt Graded: ${attemptResult.score_obtained} / ${attemptResult.max_score} marks (${attemptResult.accuracy_pct}%)`}
          />
        )}

        {!loading && paper && (
          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">{paper.title}</h2>
                <p className="text-xs text-slate-400">
                  Actual Marks: {paper.actual_marks} • Questions: {paper.questions.length} •
                  Solver: {paper.solver_status}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={generatePaper}>
                <RefreshCw className="h-3.5 w-3.5" /> Regenerate
              </Button>
            </div>

            <div className="space-y-4">
              {paper.questions.map((q) => (
                <div
                  key={q.question_id}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="cyan">Q{q.order_index}</Badge>
                      <Badge variant="default">{q.section_name}</Badge>
                      <Badge variant="indigo">{q.chapter_name}</Badge>
                    </div>
                    <Badge variant="emerald">{q.allocated_marks} mark(s)</Badge>
                  </div>
                  <p className="text-sm text-white">{q.question_text}</p>
                  {q.options.length > 0 && (
                    <div className="grid grid-cols-1 gap-1.5 pl-3 text-xs text-slate-300 sm:grid-cols-2">
                      {q.options.map((o) => (
                        <div key={o.option_label}>
                          ({o.option_label}) {o.option_text}
                        </div>
                      ))}
                    </div>
                  )}
                  <input
                    value={attemptAnswers[q.question_id] || ""}
                    onChange={(e) =>
                      setAttemptAnswers((prev) => ({
                        ...prev,
                        [q.question_id]: e.target.value,
                      }))
                    }
                    placeholder="Attempt answer inline (optional)..."
                    className="w-full rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-1.5 text-xs text-white"
                  />
                </div>
              ))}
            </div>

            <div className="pt-2">
              <Button onClick={submitAttempt}>Grade Online Attempt</Button>
            </div>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
