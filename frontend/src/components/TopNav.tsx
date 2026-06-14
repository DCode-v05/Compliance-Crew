"use client";

import clsx from "clsx";
import { ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LlmStatus } from "@/lib/types";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/circulars", label: "Circulars" },
  { href: "/maps", label: "Controls" },
  { href: "/chat", label: "Assistant" },
];

export default function TopNav() {
  const pathname = usePathname();
  const [llm, setLlm] = useState<LlmStatus | null>(null);

  useEffect(() => {
    api.llmStatus().then(setLlm).catch(() => setLlm(null));
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1180px] items-center gap-6 px-7">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg border border-emerald/25 bg-emerald-soft">
            <ShieldCheck className="h-[18px] w-[18px] text-emerald" strokeWidth={2.2} />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-display text-[17px] font-semibold tracking-tight text-ink">
              Compliance<span className="italic text-emerald">Crew</span>
            </span>
            <span className="mt-0.5 font-mono text-[8.5px] uppercase tracking-[0.2em] text-subtle">
              Regulatory Intelligence
            </span>
          </span>
        </Link>

        {/* Nav */}
        <nav className="ml-4 hidden items-center gap-1 md:flex">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "relative px-3.5 py-2 font-body text-[13.5px] font-medium transition-colors",
                  active ? "text-ink" : "text-muted hover:text-ink",
                )}
              >
                {item.label}
                {active && (
                  <span className="absolute inset-x-3 -bottom-[1px] h-[2px] origin-left animate-draw-in rounded-full bg-emerald" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Status */}
        <div className="ml-auto flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 sm:flex">
            <span
              className={clsx(
                "h-1.5 w-1.5 rounded-full",
                llm?.configured ? "animate-breathe bg-emerald" : "bg-subtle",
              )}
            />
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
              {llm?.configured ? "Groq · online" : "Groq · offline"}
            </span>
          </div>
          <Link
            href="/pipeline"
            className="inline-flex items-center rounded-lg bg-ink px-3.5 py-2 font-body text-[12.5px] font-semibold text-paper transition-transform hover:-translate-y-px"
          >
            Run analysis
          </Link>
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-line px-5 py-1.5 md:hidden">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "whitespace-nowrap rounded-md px-3 py-1.5 font-body text-[13px] font-medium",
                active ? "bg-emerald-soft text-emerald" : "text-muted",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
