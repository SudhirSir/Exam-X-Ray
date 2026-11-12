"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Database,
  Dna,
  FilePlus2,
  GitCompare,
  Radar,
  ScanLine,
  Search,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Badge, Button, Card } from "@/components/ui/primitives";

const MODULES = [
  {
    icon: Dna,
    title: "Exam DNA Analyzer",
    desc: "Deconstructs historical board papers via PySpark Gold aggregations into chapter weightage, difficulty mix, and recurring concepts with source citations.",
  },
  {
    icon: Search,
    title: "Question DNA Engine",
    desc: "Semantic vector search & metadata validation distinguishing exact duplicates, paraphrases, difficulty variations, and shared concepts.",
  },
  {
    icon: TrendingUp,
    title: "Exam Trend Intelligence",
    desc: "Year-over-year comparison showing competency-based shifts and chapter weightage changes without fabricated predictions.",
  },
  {
    icon: Radar,
    title: "Personal Vulnerability Scanner",
    desc: "Diagnostic assessment + prerequisite gap tracing + explainable revision priorities telling you exactly WHY a topic needs attention.",
  },
  {
    icon: FilePlus2,
    title: "Smart Paper Generator",
    desc: "Google OR-Tools constraint-optimized mock papers matching target marks, difficulty balance, and zero duplicate clusters with PDF export.",
  },
  {
    icon: GitCompare,
    title: "Pattern Change Detector",
    desc: "Tracks official blueprint revisions, section format updates, and rationalised syllabus topic removals across academic years.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050914] bg-xray-grid bg-[length:28px_28px]">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 pb-20 pt-14 sm:px-6 lg:pt-20">
        {/* Hero */}
        <motion.section
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="text-center"
        >
          <Badge variant="cyan" className="mb-5 px-3.5 py-1 text-xs">
            <ScanLine className="h-3.5 w-3.5" /> Built on PySpark Medallion Lakehouse + OR-Tools + pgvector
          </Badge>

          <h1 className="mx-auto max-w-4xl text-4xl font-extrabold tracking-tight text-white sm:text-6xl">
            Don&apos;t Just Prepare.{" "}
            <span className="bg-gradient-to-r from-sky-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent">
              Understand the Examination.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
            EXAM X-RAY transforms verified past examination papers into actionable structural
            intelligence—revealing chapter weightage, recurring question DNA, pattern shifts,
            and your personal conceptual vulnerabilities.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link href="/register">
              <Button size="lg">
                Start Diagnostic Scan <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/exams">
              <Button variant="secondary" size="lg">
                Explore Supported Exams
              </Button>
            </Link>
          </div>
        </motion.section>

        {/* Architecture Highlights */}
        <section className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card className="xray-glow">
            <Database className="mb-3 h-6 w-6 text-sky-400" />
            <h3 className="text-base font-semibold text-white">PySpark Medallion Pipeline</h3>
            <p className="mt-1 text-sm text-slate-400">
              Bronze raw extraction, Silver deduplication &amp; DQ validation, and Gold Spark SQL
              analytical tables.
            </p>
          </Card>
          <Card>
            <ShieldCheck className="mb-3 h-6 w-6 text-emerald-400" />
            <h3 className="text-base font-semibold text-white">Zero Fabricated Statistics</h3>
            <p className="mt-1 text-sm text-slate-400">
              Every metric cites verified historical papers or displays an explicit empty state
              when unverified.
            </p>
          </Card>
          <Card>
            <Activity className="mb-3 h-6 w-6 text-indigo-400" />
            <h3 className="text-base font-semibold text-white">Explainable Student X-Ray</h3>
            <p className="mt-1 text-sm text-slate-400">
              Links diagnostic mistakes, time pressure, and prerequisite dependencies to historical
              exam relevance.
            </p>
          </Card>
        </section>

        {/* Six Core Modules */}
        <section className="mt-20">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              Six Interconnected Intelligence Modules
            </h2>
            <p className="mt-2 text-sm text-slate-400">
              Validated end-to-end on CBSE Class 10 Mathematics &amp; Science and extensible across
              Indian boards &amp; competitive exams.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {MODULES.map((m) => {
              const Icon = m.icon;
              return (
                <Card key={m.title} className="transition-transform hover:-translate-y-0.5">
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-semibold text-white">{m.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{m.desc}</p>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Verification Promise */}
        <section className="mt-20">
          <Card className="border-sky-500/30 bg-gradient-to-r from-[#0c1836] to-[#081024] p-8">
            <div className="flex flex-col items-start justify-between gap-6 lg:flex-row lg:items-center">
              <div>
                <h2 className="text-xl font-bold text-white sm:text-2xl">
                  Built for Students, Teachers &amp; Coaching Institutes
                </h2>
                <ul className="mt-4 space-y-2 text-sm text-slate-300">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    Configurable Exam Registry: CBSE 10/12, ICSE, JEE Main, NEET UG, UPSC, SSC &amp; RRB
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    PDF Question Ingestion with SHA-256 deduplication &amp; human verification queue
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    Indian DPDP-conscious privacy: pseudonymous analytics IDs &amp; student data export
                  </li>
                </ul>
              </div>
              <Link href="/login">
                <Button size="lg">
                  Launch Platform <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </Card>
        </section>
      </main>
    </div>
  );
}
