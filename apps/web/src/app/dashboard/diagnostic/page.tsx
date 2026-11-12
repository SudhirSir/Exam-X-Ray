"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { ExamSubjectSelector, useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { Clock, Radar } from "lucide-react";

interface DiagQuestion {
  question_id: string;
  order_index: number;
  question_text: string;
  question_type: string;
  marks: number;
  difficulty: string;
  chapter_name?: string | null;
  topic_name?: string | null;
  expected_time_seconds: number;
  options: { option_label: string; option_text: string }[];
}

interface StartedTest {
  id: string;
  exam_id: string;
  subject_id: string;
  time_limit_minutes?: number | null;
  questions: DiagQuestion[];
}

export default function DiagnosticPage() {
  const router = useRouter();
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [questionCount, setQuestionCount] = useState(8);
  const [test, setTest] = useState<StartedTest | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [timings, setTimings] = useState<Record<string, number>>({});
  const [activeIdx, setActiveIdx] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const qStartRef = useRef<number>(Date.now());

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

  useEffect(() => {
    if (!test || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [test, secondsLeft]);

  function recordTimeForCurrent() {
    if (!test) return;
    const currQ = test.questions[activeIdx];
    if (!currQ) return;
    const delta = Math.max(1, Math.round((Date.now() - qStartRef.current) / 1000));
    setTimings((prev) => ({
      ...prev,
      [currQ.question_id]: (prev[currQ.question_id] || 0) + delta,
    }));
    qStartRef.current = Date.now();
  }

  async function startDiagnostic() {
    setLoading(true);
    setError(null);
    try {
      const started = await apiFetch<StartedTest>("/diagnostics/start", {
        method: "POST",
        body: JSON.stringify({
          exam_id: examId,
          subject_id: subjectId,
          question_count: questionCount,
          time_limit_minutes: 20,
        }),
      });
      setTest(started);
      setAnswers({});
      setTimings({});
      setActiveIdx(0);
      setSecondsLeft((started.time_limit_minutes || 20) * 60);
      qStartRef.current = Date.now();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not start diagnostic test");
    } finally {
      setLoading(false);
    }
  }

  async function submitTest() {
    if (!test) return;
    recordTimeForCurrent();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        answers: test.questions.map((q) => ({
          question_id: q.question_id,
          submitted_answer: answers[q.question_id] || "",
          time_spent_seconds: timings[q.question_id] || 45,
        })),
      };
      await apiFetch(`/diagnostics/${test.id}/submit`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push(`/dashboard/xray-report?test_id=${test.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setSubmitting(false);
    }
  }

  const currentQ = test?.questions[activeIdx];
  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Personal Exam Vulnerability Scanner</h1>
          <p className="text-sm text-slate-400">
            Complete a timed diagnostic scan to uncover weak topics, prerequisite gaps, and
            mistake patterns.
          </p>
        </div>

        {error && <ErrorBanner message={error} />}

        {!test && !loading && (
          <Card className="space-y-5">
            <ExamSubjectSelector
              exams={exams}
              selectedExamId={examId}
              selectedSubjectId={subjectId}
              onExamChange={handleExamChange}
              onSubjectChange={setSubjectId}
            />
            <div>
              <label className="mb-1.5 block text-xs uppercase text-slate-400">
                Diagnostic Length (Questions)
              </label>
              <select
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
                className="w-full max-w-xs rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-white"
              >
                <option value={6}>Quick Scan (6 Questions)</option>
                <option value={8}>Standard Scan (8 Questions)</option>
                <option value={10}>Deep Scan (10 Questions)</option>
              </select>
            </div>
            <Button onClick={startDiagnostic} disabled={!examId || !subjectId}>
              <Radar className="h-4 w-4" /> Launch Diagnostic Assessment
            </Button>
          </Card>
        )}

        {loading && <LoadingState label="Selecting balanced diagnostic questions..." />}

        {test && currentQ && (
          <div className="space-y-5">
            <Card className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Badge variant="cyan">
                  Question {activeIdx + 1} of {test.questions.length}
                </Badge>
                {currentQ.chapter_name && (
                  <Badge variant="indigo">{currentQ.chapter_name}</Badge>
                )}
                <Badge variant="default">
                  {currentQ.marks} mark(s) • {currentQ.difficulty}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5 text-sm font-mono text-sky-300">
                <Clock className="h-4 w-4" />
                {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
              </div>
            </Card>

            <Card className="space-y-4">
              <p className="text-base font-medium leading-relaxed text-white">
                {currentQ.question_text}
              </p>

              {currentQ.options.length > 0 ? (
                <div className="space-y-2.5">
                  {currentQ.options.map((opt) => {
                    const selected = answers[currentQ.question_id] === opt.option_label;
                    return (
                      <button
                        key={opt.option_label}
                        type="button"
                        onClick={() =>
                          setAnswers((prev) => ({
                            ...prev,
                            [currentQ.question_id]: opt.option_label,
                          }))
                        }
                        className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition-colors ${
                          selected
                            ? "border-sky-400 bg-sky-500/15 text-white"
                            : "border-slate-800 bg-slate-900/70 text-slate-300 hover:border-slate-700"
                        }`}
                      >
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-slate-600 text-xs font-semibold">
                          {opt.option_label}
                        </span>
                        <span>{opt.option_text}</span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div>
                  <label className="mb-1.5 block text-xs text-slate-400">
                    Your Answer (numerical value, key formula, or concise steps)
                  </label>
                  <textarea
                    rows={3}
                    value={answers[currentQ.question_id] || ""}
                    onChange={(e) =>
                      setAnswers((prev) => ({
                        ...prev,
                        [currentQ.question_id]: e.target.value,
                      }))
                    }
                    placeholder="Enter your answer..."
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm text-white focus:border-sky-400 focus:outline-none"
                  />
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={activeIdx === 0}
                    onClick={() => {
                      recordTimeForCurrent();
                      setActiveIdx((i) => Math.max(0, i - 1));
                    }}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={activeIdx === test.questions.length - 1}
                    onClick={() => {
                      recordTimeForCurrent();
                      setActiveIdx((i) => Math.min(test.questions.length - 1, i + 1));
                    }}
                  >
                    Next
                  </Button>
                </div>

                <Button onClick={submitTest} disabled={submitting}>
                  {submitting ? "Generating X-Ray Report..." : "Submit & Generate X-Ray Report"}
                </Button>
              </div>
            </Card>

            <div className="flex flex-wrap gap-2">
              {test.questions.map((q, idx) => (
                <button
                  key={q.question_id}
                  type="button"
                  onClick={() => {
                    recordTimeForCurrent();
                    setActiveIdx(idx);
                  }}
                  className={`h-8 w-8 rounded-lg text-xs font-semibold ${
                    idx === activeIdx
                      ? "bg-sky-500 text-white"
                      : answers[q.question_id]
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
