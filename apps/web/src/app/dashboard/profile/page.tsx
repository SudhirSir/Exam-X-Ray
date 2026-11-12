"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  SuccessBanner,
} from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/useAuth";
import { Download, Shield, Trash2 } from "lucide-react";

export default function StudentProfilePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function handleExportData() {
    setErr(null);
    try {
      const data = await apiFetch<Record<string, unknown>>("/auth/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "exam_xray_personal_data_export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMsg("Personal data export downloaded.");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Export failed");
    }
  }

  async function handleDeleteAccount() {
    if (!confirm("Are you sure? This will permanently anonymize and deactivate your account.")) {
      return;
    }
    try {
      await apiFetch("/auth/me", { method: "DELETE" });
      router.push("/");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Account deletion failed");
    }
  }

  return (
    <AppShell section="student">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Student Profile &amp; Privacy Controls</h1>
          <p className="text-sm text-slate-400">
            Manage your account identity, pseudonymous analytics ID, and Indian DPDP data rights.
          </p>
        </div>

        {msg && <SuccessBanner message={msg} />}
        {err && <ErrorBanner message={err} />}

        {user && (
          <Card className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs text-slate-400">Full Name</p>
                <p className="text-sm font-medium text-white">{user.full_name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Email</p>
                <p className="text-sm font-medium text-white">{user.email}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Role</p>
                <Badge variant="cyan">{user.role}</Badge>
              </div>
              <div>
                <p className="text-xs text-slate-400">Pseudonymous Analytics ID (Used in Spark)</p>
                <code className="text-xs text-sky-300">{user.analytics_pseudo_id}</code>
              </div>
            </div>
          </Card>
        )}

        <Card className="space-y-4">
          <div className="flex items-center gap-2 text-white">
            <Shield className="h-5 w-5 text-emerald-400" />
            <h2 className="text-base font-semibold">Data Protection &amp; DPDP Rights</h2>
          </div>
          <p className="text-xs text-slate-400">
            Your personally identifiable information is never stored in PySpark analytical tables.
            You may export or permanently anonymize your profile at any time.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={handleExportData}>
              <Download className="h-4 w-4" /> Export My Data (JSON)
            </Button>
            <Button variant="danger" onClick={handleDeleteAccount}>
              <Trash2 className="h-4 w-4" /> Anonymize &amp; Delete Account
            </Button>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
