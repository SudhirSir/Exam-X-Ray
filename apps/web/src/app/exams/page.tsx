"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Badge, Button, Card, ErrorBanner, LoadingState } from "@/components/ui/primitives";
import { useExamsRegistry } from "@/components/ExamSubjectSelector";
import { BookOpen, CheckCircle2, Clock } from "lucide-react";

export default function SupportedExamsPage() {
  const { exams, loading, error } = useExamsRegistry();

  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="mb-10">
          <Badge variant="cyan">Configurable Examination Registry</Badge>
          <h1 className="mt-3 text-3xl font-bold text-white">Supported Examinations</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            All Indian board and competitive exams are driven by data configuration. CBSE Class 10
            Mathematics &amp; Science are currently loaded with verified multi-year question banks.
          </p>
        </div>

        {loading && <LoadingState label="Loading examination registry..." />}
        {error && <ErrorBanner message={error} />}

        {!loading && !error && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {exams.map((ex) => {
              const verifiedCount = ex.config_json?.verified_subjects?.length || 0;
              return (
                <Card key={ex.id} className="flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="indigo">{ex.exam_body_code || ex.category}</Badge>
                      {verifiedCount > 0 ? (
                        <Badge variant="emerald">
                          <CheckCircle2 className="h-3 w-3" /> Verified Dataset Ready
                        </Badge>
                      ) : (
                        <Badge variant="amber">
                          <Clock className="h-3 w-3" /> Registry Ready (Awaiting PDFs)
                        </Badge>
                      )}
                    </div>
                    <h2 className="mt-3 text-lg font-semibold text-white">{ex.name}</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      Category: {ex.category.toUpperCase()} • Level: {ex.class_level || "All"}
                    </p>
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {ex.subjects.map((s) => (
                        <span
                          key={s.id}
                          className="inline-flex items-center gap-1 rounded-lg bg-slate-800/80 px-2.5 py-1 text-xs text-slate-200"
                        >
                          <BookOpen className="h-3 w-3 text-sky-400" /> {s.name}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="mt-5 pt-4 border-t border-slate-800/80">
                    <Link href="/dashboard/exam-dna">
                      <Button variant="secondary" size="sm" className="w-full">
                        Inspect Exam DNA
                      </Button>
                    </Link>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
