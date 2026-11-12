"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Badge, Button, Card } from "@/components/ui/primitives";

const PLANS = [
  {
    name: "Student Explorer",
    price: "₹0",
    period: "forever",
    badge: "Free Tier",
    features: [
      "Exam DNA & Chapter Weightage Explorer",
      "Question DNA Semantic Search",
      "2 Diagnostic Vulnerability Scans / month",
      "Blueprint Trend Comparison",
    ],
  },
  {
    name: "Scholar Pro",
    price: "₹299",
    period: "per month",
    badge: "Most Popular",
    highlight: true,
    features: [
      "Unlimited Diagnostic Vulnerability Scans",
      "Full Personal X-Ray & Prerequisite Gap Map",
      "Unlimited Smart Paper Generator + PDF Export",
      "Pattern Change Alerts & Revision Roadmap",
    ],
  },
  {
    name: "School & Coaching",
    price: "₹4,999",
    period: "per month",
    badge: "Institutes",
    features: [
      "Teacher Class Performance Analytics",
      "Custom Batch Diagnostic & Practice Papers",
      "Admin PDF Paper Ingestion & Verification Queue",
      "Dedicated PySpark Analytics & DPDP Controls",
    ],
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#050914]">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="text-center">
          <Badge variant="cyan">Transparent Pricing</Badge>
          <h1 className="mt-3 text-3xl font-bold text-white sm:text-4xl">
            Accessible Examination Intelligence for Every Learner
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Start free with verified CBSE Class 10 intelligence. Upgrade for unlimited mocks and
            institutional batches.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {PLANS.map((p) => (
            <Card
              key={p.name}
              className={`flex flex-col justify-between ${
                p.highlight ? "border-sky-400/50 xray-glow" : ""
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-white">{p.name}</h2>
                  <Badge variant={p.highlight ? "cyan" : "default"}>{p.badge}</Badge>
                </div>
                <div className="mt-4 flex items-baseline gap-1.5">
                  <span className="text-3xl font-extrabold text-white">{p.price}</span>
                  <span className="text-xs text-slate-400">/ {p.period}</span>
                </div>
                <ul className="mt-6 space-y-2.5 text-sm text-slate-300">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-8">
                <Link href="/register">
                  <Button
                    variant={p.highlight ? "primary" : "secondary"}
                    className="w-full"
                  >
                    Get Started
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
