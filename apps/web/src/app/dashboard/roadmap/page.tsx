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
import { apiFetch } from "@/lib/api";
import { Clock, Compass, Radar } from "lucide-react";

interface RecItem {
  id: string;
  topic_id: string;
  chapter_name: string;
  topic_name: string;
  priority_rank: number;
  priority_score: number;
  reason_explanation: string;
  estimated_hours: number;
  recommended_question_ids: string[];
}

export default function RoadmapPage() {
  const [items, setItems] = useState<RecItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<{ has_data: boolean; items: RecItem[] }>("/students/me/recommendations")
      .then((d) => setItems(d.items || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Personalized Revision Roadmap</h1>
          <p className="text-sm text-slate-400">
            Ordered by vulnerability index, prerequisite importance, and historical exam marks
            weightage.
          </p>
        </div>

        {loading && <LoadingState label="Building revision roadmap..." />}

        {!loading && items.length === 0 && (
          <EmptyState
            title="No Revision Plan Generated Yet"
            description="Complete a diagnostic scan so EXAM X-RAY can build a personalized topic sequence."
            action={
              <Link href="/dashboard/diagnostic">
                <Button>
                  <Radar className="h-4 w-4" /> Take Diagnostic Scan
                </Button>
              </Link>
            }
          />
        )}

        {!loading && items.length > 0 && (
          <div className="space-y-4">
            {items.map((item) => (
              <Card key={item.id} className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="cyan">Step #{item.priority_rank}</Badge>
                    <Badge variant="indigo">{item.chapter_name}</Badge>
                    <span className="flex items-center gap-1 text-xs text-slate-400">
                      <Clock className="h-3.5 w-3.5" /> {item.estimated_hours} hrs
                    </span>
                  </div>
                  <h2 className="text-base font-semibold text-white">{item.topic_name}</h2>
                  <p className="text-sm text-slate-300">{item.reason_explanation}</p>
                </div>
                <Link href="/dashboard/paper-generator" className="shrink-0">
                  <Button variant="secondary" size="sm">
                    <Compass className="h-4 w-4" /> Practice Chapter
                  </Button>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
