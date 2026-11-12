"use client";

import { Navbar } from "@/components/layout/Navbar";
import { Badge, Card } from "@/components/ui/primitives";
import { Lock, Cpu, ShieldCheck } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 py-14 sm:px-6">
        <Badge variant="cyan">Our Mission</Badge>
        <h1 className="mt-3 text-3xl font-bold text-white sm:text-4xl">
          Evidence-First Examination Preparation for India
        </h1>
        <p className="mt-4 text-base leading-relaxed text-slate-300">
          EXAM X-RAY was engineered to replace guesswork, rumor-driven &ldquo;important questions,&rdquo;
          and opaque coaching claims with verifiable examination intelligence. Every chart and
          diagnostic priority is grounded in historical question evidence, syllabus versions, and
          transparent prerequisite reasoning.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-3">
          <Card>
            <Cpu className="mb-3 h-6 w-6 text-sky-400" />
            <h2 className="text-base font-semibold text-white">Medallion Data Engineering</h2>
            <p className="mt-2 text-sm text-slate-400">
              Apache Spark + Delta Lake Bronze/Silver/Gold pipelines guarantee reproducible,
              auditable exam analytics at scale.
            </p>
          </Card>
          <Card>
            <ShieldCheck className="mb-3 h-6 w-6 text-emerald-400" />
            <h2 className="text-base font-semibold text-white">Honest AI Guardrails</h2>
            <p className="mt-2 text-sm text-slate-400">
              We never predict future board paper marks or fabricate statistics. Estimates are
              explicitly labeled with provenance.
            </p>
          </Card>
          <Card>
            <Lock className="mb-3 h-6 w-6 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">Student Privacy &amp; DPDP</h2>
            <p className="mt-2 text-sm text-slate-400">
              Analytical datasets use pseudonymous student IDs, minor guardian consent workflows,
              and one-click data export/deletion.
            </p>
          </Card>
        </div>
      </main>
    </div>
  );
}
