"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ExamSubjectSelector, useExamsRegistry } from "@/components/ExamSubjectSelector";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { QuestionItem, SimilarQuestionResult } from "@/lib/types";
import { Search, Sparkles } from "lucide-react";

const REL_COLORS: Record<string, "cyan" | "emerald" | "amber" | "indigo" | "rose"> = {
  exact_duplicate: "rose",
  paraphrase: "amber",
  same_concept: "cyan",
  same_pattern: "indigo",
  difficulty_variation: "emerald",
};

export default function QuestionSearchPage() {
  const { exams } = useExamsRegistry();
  const [examId, setExamId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [query, setQuery] = useState("quadratic equation equal roots discriminant");
  const [results, setResults] = useState<SimilarQuestionResult[]>([]);
  const [browseItems, setBrowseItems] = useState<QuestionItem[]>([]);
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

  async function runSemanticSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ q: query.trim(), top_k: "10" });
      if (examId) params.set("exam_id", examId);
      if (subjectId) params.set("subject_id", subjectId);
      const data = await apiFetch<{ results: SimilarQuestionResult[] }>(
        `/questions/search?${params.toString()}`
      );
      setResults(data.results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function findRelated(questionId: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ results: SimilarQuestionResult[] }>(
        `/questions/similar?question_id=${questionId}&top_k=6`
      );
      setResults(data.results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Similarity lookup failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!examId || !subjectId) return;
    apiFetch<{ items: QuestionItem[] }>(
      `/questions?exam_id=${examId}&subject_id=${subjectId}&page=1&page_size=12`
    )
      .then((d) => setBrowseItems(d.items))
      .catch(() => setBrowseItems([]));
  }, [examId, subjectId]);

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Question DNA &amp; Semantic Search</h1>
          <p className="text-sm text-slate-400">
            Search across verified papers by concept, formula, or problem framing. Distinguishes
            exact duplicates, paraphrases, difficulty variations, and shared concepts.
          </p>
        </div>

        <Card>
          <div className="space-y-4">
            <ExamSubjectSelector
              exams={exams}
              selectedExamId={examId}
              selectedSubjectId={subjectId}
              onExamChange={handleExamChange}
              onSubjectChange={setSubjectId}
            />
            <form onSubmit={runSemanticSearch} className="flex flex-col gap-3 sm:flex-row">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search concepts, equations (e.g. sin^2 theta + cos^2 theta, Ohm's law, BPT)..."
                className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
              />
              <Button type="submit" disabled={loading}>
                <Search className="h-4 w-4" /> Semantic Search
              </Button>
            </form>
          </div>
        </Card>

        {loading && <LoadingState label="Computing 384-dim semantic vector matches..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && results.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-white">
              Semantic Matches ({results.length})
            </h2>
            {results.map((r) => (
              <Card key={r.question.id} className="space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={REL_COLORS[r.relationship_type] || "cyan"}>
                      {r.relationship_type.replace("_", " ")}
                    </Badge>
                    <Badge variant="default">
                      Confidence: {Math.round(r.combined_confidence * 100)}%
                    </Badge>
                    <Badge variant="default">
                      {r.question.year} • {r.question.marks}m • {r.question.difficulty}
                    </Badge>
                    {r.question.chapter_name && (
                      <Badge variant="indigo">{r.question.chapter_name}</Badge>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => findRelated(r.question.id)}
                  >
                    <Sparkles className="h-3.5 w-3.5" /> Similar Variants
                  </Button>
                </div>
                <p className="text-sm text-white">{r.question.question_text}</p>
                <p className="text-xs text-sky-300/90">Why matched: {r.explanation}</p>
                <p className="text-[11px] text-slate-400">
                  Source: {r.question.source_reference}
                </p>
              </Card>
            ))}
          </div>
        )}

        {!loading && results.length === 0 && (
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-white">
              Verified Question Bank ({browseItems.length} shown)
            </h2>
            {browseItems.length === 0 ? (
              <EmptyState
                title="No Questions Found"
                description="Select CBSE Class 10 Mathematics or Science, or upload a verified paper in the Admin console."
              />
            ) : (
              browseItems.map((q) => (
                <Card key={q.id} className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="cyan">{q.year} • Q{q.question_number}</Badge>
                      <Badge variant="default">{q.question_type} • {q.marks}m</Badge>
                      {q.chapter_name && <Badge variant="indigo">{q.chapter_name}</Badge>}
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => findRelated(q.id)}>
                      Find Related Questions
                    </Button>
                  </div>
                  <p className="text-sm text-slate-100">{q.question_text}</p>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
