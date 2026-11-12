import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EXAM X-RAY | Don't Just Prepare. Understand the Examination.",
  description:
    "India's AI-powered Examination Intelligence Platform built with PySpark, Delta Lake, semantic question DNA, and personalized vulnerability diagnostics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#050914] font-sans text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
