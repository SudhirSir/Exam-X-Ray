"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, Inbox } from "lucide-react";

export function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(" ");
}

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "xray-surface rounded-2xl p-5 shadow-lg shadow-black/30 backdrop-blur-sm",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: "default" | "cyan" | "emerald" | "amber" | "rose" | "indigo";
  className?: string;
}) {
  const styles: Record<string, string> = {
    default: "bg-slate-800/90 text-slate-200 border-slate-700",
    cyan: "bg-sky-500/15 text-sky-300 border-sky-500/30",
    emerald: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    rose: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    indigo: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}) {
  const variants: Record<string, string> = {
    primary:
      "bg-gradient-to-r from-sky-500 to-blue-600 text-white hover:from-sky-400 hover:to-blue-500 shadow-md shadow-sky-500/20",
    secondary:
      "bg-slate-800/90 text-slate-100 border border-slate-700 hover:bg-slate-700/80",
    ghost: "bg-transparent text-slate-300 hover:bg-slate-800/60 hover:text-white",
    danger: "bg-rose-600/90 text-white hover:bg-rose-500",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
  };
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </button>
  );
}

export function LoadingState({ label = "Analyzing examination intelligence..." }: { label?: string }) {
  return (
    <div className="xray-surface flex flex-col items-center justify-center rounded-2xl py-14 text-center">
      <Loader2 className="mb-3 h-8 w-8 animate-spin text-sky-400" />
      <p className="text-sm text-slate-300">{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="xray-surface flex flex-col items-center justify-center rounded-2xl px-6 py-12 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-sky-500/10 text-sky-400">
        <Inbox className="h-6 w-6" />
      </div>
      <h3 className="text-base font-semibold text-white">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-slate-400">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
      <span>{message}</span>
    </div>
  );
}

export function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
      <span>{message}</span>
    </div>
  );
}

export function DisclaimerNote({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-sky-500/20 bg-sky-950/30 px-4 py-3 text-xs text-sky-200/90">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />
      <span>{text}</span>
    </div>
  );
}
