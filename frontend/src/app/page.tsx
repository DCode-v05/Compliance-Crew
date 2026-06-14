"use client";

import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck, Quote, GitBranch, Lock } from "lucide-react";
import Link from "next/link";
import { AGENT_ORDER } from "@/lib/types";
import { agentMeta } from "@/lib/agents";

const PILLARS = [
  { icon: Quote, title: "Cited reasoning", body: "Every control quotes the regulation verbatim. Hallucinated citations are auto-rejected by a hash check before review." },
  { icon: GitBranch, title: "Adversarial review", body: "The Validator rejects flawed controls; the Mapper retries with cited feedback until the interpretation holds." },
  { icon: Lock, title: "Tamper-proof trail", body: "Every model call is chained with SHA-256. Any edit to history breaks the chain and is provably detectable." },
];

const fade = (d: number) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6, delay: d },
});

export default function Splash() {
  return (
    <div className="relative min-h-screen">
      <div className="mx-auto flex min-h-screen max-w-[1080px] flex-col px-7">
        {/* Masthead */}
        <motion.header {...fade(0)} className="flex items-center justify-between border-b border-line py-6">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg border border-emerald/25 bg-emerald-soft">
              <ShieldCheck className="h-[18px] w-[18px] text-emerald" strokeWidth={2.2} />
            </span>
            <span className="font-display text-[17px] font-semibold tracking-tight">
              Compliance<span className="italic text-emerald">Crew</span>
            </span>
          </div>
          <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-subtle">
            SuRaksha Cyber Hackathon 2.0
          </div>
        </motion.header>

        {/* Hero */}
        <div className="flex flex-1 flex-col justify-center py-14">
          <motion.div {...fade(0.06)} className="mb-6 flex items-center gap-3">
            <span className="kicker">Reserve Bank of India · KYC / AML</span>
            <span className="h-px flex-1 bg-line" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-emerald">Real-time</span>
          </motion.div>

          <motion.h1
            {...fade(0.12)}
            className="max-w-3xl font-display text-[56px] font-semibold leading-[1.03] tracking-tight text-ink md:text-[68px]"
          >
            An AI compliance team
            <br />
            you can <span className="italic text-emerald">audit</span>.
          </motion.h1>

          <motion.p {...fade(0.2)} className="mt-7 max-w-2xl text-[16px] leading-relaxed text-muted">
            Six specialist agents read an RBI circular, derive control requirements, validate each
            other&apos;s interpretations against the source text, route work to departments, test
            sample bank data, and assemble an audit-ready report — every claim cited to a verbatim
            paragraph of the regulation.
          </motion.p>

          {/* Agent ledger */}
          <motion.div {...fade(0.28)} className="mt-9 flex flex-wrap items-center gap-x-1 gap-y-3">
            {AGENT_ORDER.map((k, i) => {
              const m = agentMeta(k);
              return (
                <div key={k} className="flex items-center gap-1">
                  <span
                    className="inline-flex items-center gap-2 rounded-lg border bg-surface px-3 py-1.5 font-body text-[12.5px] font-medium"
                    style={{ borderColor: `${m.color}33`, color: m.color }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
                    {m.label}
                  </span>
                  {i < AGENT_ORDER.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-subtle" />}
                </div>
              );
            })}
          </motion.div>

          <motion.div {...fade(0.36)} className="mt-10 flex flex-wrap items-center gap-3">
            <Link
              href="/dashboard"
              className="group inline-flex items-center gap-2 rounded-xl bg-ink px-6 py-3.5 font-body text-[14px] font-semibold text-paper transition-transform hover:-translate-y-0.5"
            >
              Open the workspace
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/pipeline"
              className="inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface px-6 py-3.5 font-body text-[14px] font-medium text-ink transition-colors hover:border-emerald/45"
            >
              Run the pipeline
            </Link>
          </motion.div>
        </div>

        {/* Pillars */}
        <motion.div {...fade(0.44)} className="grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-3 mb-12">
          {PILLARS.map((p) => {
            const Icon = p.icon;
            return (
              <div key={p.title} className="bg-surface p-6">
                <Icon className="h-5 w-5 text-emerald" strokeWidth={2} />
                <div className="mt-3.5 font-display text-[16px] font-semibold text-ink">{p.title}</div>
                <div className="mt-2 text-[13px] leading-relaxed text-muted">{p.body}</div>
              </div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}
