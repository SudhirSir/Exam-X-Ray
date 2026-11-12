"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, ScanLine, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/primitives";

const NAV_LINKS = [
  { href: "/features", label: "Features" },
  { href: "/exams", label: "Supported Exams" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
];

export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#050914]/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 shadow-lg shadow-sky-500/25">
            <ScanLine className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-white">
              EXAM <span className="text-sky-400">X-RAY</span>
            </span>
            <p className="hidden text-[10px] uppercase tracking-widest text-slate-400 sm:block">
              Examination Intelligence
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm font-medium transition-colors ${
                pathname === item.href
                  ? "text-sky-400"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get Started Free</Button>
          </Link>
        </div>

        <button
          aria-label="Toggle Menu"
          onClick={() => setOpen((v) => !v)}
          className="rounded-lg p-2 text-slate-300 hover:bg-slate-800 md:hidden"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-800 bg-[#080f21] px-4 py-4 md:hidden">
          <div className="flex flex-col gap-3">
            {NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-2 flex gap-2">
              <Link href="/login" className="flex-1">
                <Button variant="secondary" className="w-full" size="sm">
                  Sign In
                </Button>
              </Link>
              <Link href="/register" className="flex-1">
                <Button className="w-full" size="sm">
                  Register
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
