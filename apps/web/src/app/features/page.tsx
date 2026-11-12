"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Badge, Button, Card } from "@/components/ui/primitives";
import { Dna, FilePlus2, GitCompare, Radar, Search, TrendingUp } from "lucide-react";

const FEATURE_BLOCKS = [
  {
    icon: Dna,
    tag: "Module 1",
    title: "Exam DNA Analyzer",
    points: [
      "Chapter-wise marks weightage computed from verified papers via PySpark Gold tables",
      "Question-type & difficulty distribution breakdowns with source provenance",
      "Recurring concept extraction showing exact years & paper set references",
    ],
  },
  {
    icon: Search,
    tag: "Module 2",
    title: "Question DNA & Semantic Intelligence",
    points: [
      "384-dimensional vector embeddings + metadata validation",
      "Explicitly classifies Exact Duplicate, Paraphrase, Same Concept, Same Pattern, and Difficulty Variation",
      "KMeans structural pattern clustering across multi-year question banks",
    ],
  },
  {
    icon: TrendingUp,
    tag: "Module 3",
    title: "Exam Trend Intelligence",
    points: [
      "Side-by-side comparison between any two examination years",
      "Tracks rising competency-based share & chapter shift deltas",
      "Transparent historical disclaimers with zero fabricated forecasts",
    ],
  },
  {
    icon: Radar,
    tag: "Module 4",
    title: "Personal Exam Vulnerability Scanner",
    points: [
      "Timed diagnostic assessments across chapter & difficulty tiers",
      "Classifies mistake types: conceptual gap, calculation error, time pressure, skipped",
      "Prerequisite-aware priority revision roadmap explaining WHY each topic matters",
    ],
  },
  {
    icon: FilePlus2,
    tag: "Module 5",
    title: "Smart Question Paper Generator",
    points: [
      "Google OR-Tools CP-SAT constraint optimization for exact blueprint marks",
      "Zero duplicate clusters, balanced chapter spread, and difficulty ratio control",
      "One-click printable Question Paper PDF, Answer Key PDF, and online attempt mode",
    ],
  },
  {
    icon: GitCompare,
    tag: "Module 6",
    title: "Exam Pattern Change Detector",
    points: [
      "Compares official exam versions & blueprints across academic years",
      "Highlights rationalised/removed syllabus topics so students avoid wasted effort",
      "Admin document ingestion & human-in-the-loop verification workflow",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="text-center">
          <Badge variant="cyan">Platform Capabilities</Badge>
          <h1 className="mt-3 text-3xl font-bold text-white sm:text-4xl">
            Every Module Built on Real Data Engineering
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-slate-400">
            From PyMuPDF extraction and PySpark Delta Lake pipelines to OR-Tools optimization and
            personalized diagnostics.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2">
          {FEATURE_BLOCKS.map((fb) => {
            const Icon = fb.icon;
            return (
              <Card key={fb.title}>
                <div className="flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <Badge variant="indigo">{fb.tag}</Badge>
                </div>
                <h2 className="mt-4 text-lg font-semibold text-white">{fb.title}</h2>
                <ul className="mt-3 space-y-2 text-sm text-slate-300">
                  {fb.points.map((pt) => (
                    <li key={pt} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <Link href="/register">
            <Button size="lg">Create Student or Teacher Account</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
