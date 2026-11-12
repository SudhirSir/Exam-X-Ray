"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  LoadingState,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { Check, X } from "lucide-react";

interface ReviewItem {
  id: string;
  question_number: string;
  question_text: string;
  question_type: string;
  marks: number;
  difficulty: string;
  confidence_score: number;
  verification_status: string;
  paper_title: string | null;
  year: number | null;
}

export default function AdminVerificationPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  function loadQueue() {
    setLoading(true);
    apiFetch<{ items: ReviewItem[] }>("/admin/review-queue?status_filter=pending")
      .then((d) => setItems(d.items || []))
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadQueue();
  }, []);

  async function handleDecision(id: string, status: "verified" | "rejected") {
    setErr(null);
    setMsg(null);
    try {
      await apiFetch(`/admin/questions/${id}/verify`, {
        method: "POST",
        body: JSON.stringify({ verification_status: status }),
      });
      setMsg(`Question marked as ${status}.`);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Verification action failed");
    }
  }

  return (
    <AppShell section="admin">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Human Question Verification Queue</h1>
          <p className="text-sm text-slate-400">
            Review extracted questions before promoting them to verified Gold analytics.
          </p>
        </div>

        {msg && <SuccessBanner message={msg} />}
        {err && <ErrorBanner message={err} />}
        {loading && <LoadingState label="Loading review queue..." />}

        {!loading && items.length === 0 && (
          <EmptyState
            title="Verification Queue Clear"
            description="All extracted questions have been reviewed. Upload a new PDF paper to queue additional items."
          />
        )}

        {!loading && items.length > 0 && (
          <div className="space-y-3">
            {items.map((q) => (
              <Card key={q.id} className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="amber">Pending Review</Badge>
                    <Badge variant="default">
                      {q.paper_title} • Q{q.question_number}
                    </Badge>
                    <Badge variant="cyan">
                      Confidence: {Math.round(q.confidence_score * 100)}%
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => handleDecision(q.id, "verified")}>
                      <Check className="h-3.5 w-3.5" /> Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDecision(q.id, "rejected")}
                    >
                      <X className="h-3.5 w-3.5" /> Reject
                    </Button>
                  </div>
                </div>
                <p className="text-sm text-white">{q.question_text}</p>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
