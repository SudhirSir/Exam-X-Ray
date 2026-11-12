"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Exam, Subject } from "@/lib/types";

export function useExamsRegistry() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<Exam[]>("/exams")
      .then((data) => {
        if (active) setExams(data);
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { exams, loading, error };
}

export function ExamSubjectSelector({
  exams,
  selectedExamId,
  selectedSubjectId,
  onExamChange,
  onSubjectChange,
}: {
  exams: Exam[];
  selectedExamId: string;
  selectedSubjectId: string;
  onExamChange: (examId: string) => void;
  onSubjectChange: (subjectId: string) => void;
}) {
  const currentExam = exams.find((e) => e.id === selectedExamId);
  const subjects: Subject[] = currentExam?.subjects || [];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div>
        <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-400">
          Examination
        </label>
        <select
          value={selectedExamId}
          onChange={(e) => onExamChange(e.target.value)}
          className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
        >
          {exams.map((ex) => (
            <option key={ex.id} value={ex.id}>
              {ex.name} {ex.class_level ? `(${ex.class_level})` : ""}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-slate-400">
          Subject
        </label>
        <select
          value={selectedSubjectId}
          onChange={(e) => onSubjectChange(e.target.value)}
          className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2.5 text-sm text-white focus:border-sky-400 focus:outline-none"
        >
          {subjects.map((sub) => (
            <option key={sub.id} value={sub.id}>
              {sub.name} {sub.subject_code_in_exam ? `(${sub.subject_code_in_exam})` : ""}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
