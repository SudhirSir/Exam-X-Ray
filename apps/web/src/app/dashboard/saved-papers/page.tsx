"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  LoadingState,
} from "@/components/ui/primitives";
import { apiFetch, getExportUrl } from "@/lib/api";
import { GeneratedPaper } from "@/lib/types";
import { Download, FilePlus2 } from "lucide-react";

export default function SavedPapersPage() {
  const [papers, setPapers] = useState<GeneratedPaper[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<GeneratedPaper[]>("/papers")
      .then(setPapers)
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Saved Practice Papers</h1>
            <p className="text-sm text-slate-400">
              Download previously generated papers and answer keys or review question blueprints.
            </p>
          </div>
          <Link href="/dashboard/paper-generator">
            <Button size="sm">
              <FilePlus2 className="h-4 w-4" /> Generate New Paper
            </Button>
          </Link>
        </div>

        {loading && <LoadingState label="Loading saved practice papers..." />}

        {!loading && papers.length === 0 && (
          <EmptyState
            title="No Saved Practice Papers"
            description="Generate your first blueprint-optimized paper using the OR-Tools Smart Paper Generator."
            action={
              <Link href="/dashboard/paper-generator">
                <Button>Open Paper Generator</Button>
              </Link>
            }
          />
        )}

        {!loading && papers.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {papers.map((p) => (
              <Card key={p.id} className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="cyan">{p.actual_marks} Marks</Badge>
                  <Badge variant="default">{p.questions.length} Questions</Badge>
                </div>
                <h2 className="text-base font-semibold text-white">{p.title}</h2>
                <p className="text-xs text-slate-400">
                  Created {new Date(p.created_at).toLocaleDateString()} • {p.time_limit_minutes} mins
                </p>
                <div className="flex flex-wrap gap-2 pt-2">
                  <a href={getExportUrl(p.id, "paper_pdf")} target="_blank" rel="noreferrer">
                    <Button variant="secondary" size="sm">
                      <Download className="h-3.5 w-3.5" /> Paper PDF
                    </Button>
                  </a>
                  <a href={getExportUrl(p.id, "answer_key_pdf")} target="_blank" rel="noreferrer">
                    <Button variant="ghost" size="sm">
                      <Download className="h-3.5 w-3.5" /> Answer Key
                    </Button>
                  </a>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
