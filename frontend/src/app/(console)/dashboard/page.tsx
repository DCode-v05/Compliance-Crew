"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Link2, ShieldCheck, ShieldAlert, ArrowUpRight } from "lucide-react";
import { api, API_BASE } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { RISK_COLOR } from "@/lib/agents";
import { Card, EmptyState, Kicker, SectionTitle, StatCard, ProgressBar } from "@/components/ui";

const DEPT_COLOR = "#2C7E84";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setStats).catch((e) => setError(String(e)));
  }, []);

  if (error) return <BackendOffline detail={error} />;
  if (!stats) return <LoadingBlock />;

  const maxDept = Math.max(1, ...stats.by_department.map((d) => d.count));
  const maxRisk = Math.max(1, ...stats.by_risk.map((d) => d.count));

  return (
    <div>
      <div className="mb-7 flex items-end justify-between gap-4">
        <div>
          <Kicker className="mb-2">Overview</Kicker>
          <h1 className="font-display text-[34px] font-semibold leading-none tracking-tight text-ink">
            Compliance posture
          </h1>
          <p className="mt-2.5 text-[14px] text-muted">
            Cumulative across {stats.total_runs} pipeline {stats.total_runs === 1 ? "run" : "runs"} ·{" "}
            {stats.circulars_available} circular{stats.circulars_available === 1 ? "" : "s"} on file
          </p>
        </div>
        <ChainPill intact={stats.chain_intact} entries={stats.audit_entries} />
      </div>

      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-5">
        <StatCard label="Controls derived" value={stats.controls_derived} delay={0} />
        <StatCard label="Approved" value={stats.controls_approved} tone="emerald" delay={60} />
        <StatCard label="Validator rejects" value={stats.validator_rejections} tone="gold" delay={120} hint="caught pre-evidence" />
        <StatCard label="Violations" value={stats.total_violations} tone="claret" delay={180} hint="in sample bank data" />
        <StatCard label="CCO escalations" value={stats.open_escalations} tone="clay" delay={240} />
      </div>

      <div className="mt-3.5 grid gap-3.5 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <SectionTitle kicker="Routing" title="Department workload" />
          {stats.by_department.length === 0 ? (
            <EmptyState title="No assignments yet" hint="Run the pipeline to route approved controls to departments." />
          ) : (
            <div className="flex flex-col gap-3.5">
              {stats.by_department.map((d) => (
                <div key={d.department}>
                  <div className="mb-1.5 flex items-center justify-between text-[13px]">
                    <span className="font-body font-medium text-ink">{d.department}</span>
                    <span className="font-mono text-muted tnum">{d.count}</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-paper-2">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${(d.count / maxDept) * 100}%`, background: DEPT_COLOR }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <SectionTitle kicker="Evidence" title="Compliance rate" />
          <div className="flex items-end gap-2">
            <span className="font-display text-[44px] font-semibold leading-none text-emerald tnum">
              {(stats.compliance_rate * 100).toFixed(0)}%
            </span>
            <span className="mb-1.5 text-[12px] text-subtle">checks passing</span>
          </div>
          <div className="mt-3.5">
            <ProgressBar value={stats.compliance_rate} />
          </div>
          <div className="kicker mb-2.5 mt-6">Risk distribution</div>
          {stats.by_risk.length === 0 ? (
            <div className="text-[12px] text-subtle">No controls yet.</div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {stats.by_risk.map((r) => (
                <div key={r.risk_category} className="flex items-center gap-2.5">
                  <span className="w-16 font-mono text-[10px] uppercase tracking-wider text-muted">{r.risk_category}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-paper-2">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(r.count / maxRisk) * 100}%`, background: RISK_COLOR[r.risk_category] ?? "#6C6557" }}
                    />
                  </div>
                  <span className="w-6 text-right font-mono text-[11px] text-muted tnum">{r.count}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-3.5 p-6">
        <SectionTitle
          kicker="Activity"
          title="Recent runs"
          right={
            <Link href="/pipeline" className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-emerald hover:underline">
              New run <ArrowUpRight className="h-3 w-3" />
            </Link>
          }
        />
        {stats.recent_runs.length === 0 ? (
          <EmptyState title="No runs recorded" hint="Head to Pipeline and launch the agents on a circular." />
        ) : (
          <div className="overflow-hidden rounded-xl border border-line">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-paper-2/60 font-mono text-[10px] uppercase tracking-wider text-subtle">
                <tr>
                  <th className="px-4 py-3 font-medium">Circular</th>
                  <th className="px-4 py-3 font-medium">Class</th>
                  <th className="px-3 py-3 text-right font-medium">Controls</th>
                  <th className="px-3 py-3 text-right font-medium">Approved</th>
                  <th className="px-3 py-3 text-right font-medium">Rejects</th>
                  <th className="px-3 py-3 text-right font-medium">Violations</th>
                  <th className="px-3 py-3 text-right font-medium">Esc.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {stats.recent_runs.map((r) => (
                  <tr key={r.run_id} className="transition-colors hover:bg-paper/50">
                    <td className="px-4 py-3">
                      <Link href={`/maps?run=${r.run_id}`} className="font-medium text-ink hover:text-emerald">
                        {r.circular}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted">{r.classification}</td>
                    <td className="px-3 py-3 text-right font-mono text-muted tnum">{r.total_maps}</td>
                    <td className="px-3 py-3 text-right font-mono text-emerald tnum">{r.approved}</td>
                    <td className="px-3 py-3 text-right font-mono text-gold tnum">{r.rejected}</td>
                    <td className="px-3 py-3 text-right font-mono text-claret tnum">{r.violations}</td>
                    <td className="px-3 py-3 text-right font-mono text-clay tnum">{r.escalations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function ChainPill({ intact, entries }: { intact: boolean; entries: number }) {
  return (
    <div
      className="flex items-center gap-2.5 rounded-xl border px-4 py-2.5"
      style={{
        borderColor: intact ? "rgba(15,110,80,0.25)" : "rgba(168,50,74,0.25)",
        background: intact ? "rgba(15,110,80,0.06)" : "rgba(168,50,74,0.06)",
      }}
    >
      {intact ? <ShieldCheck className="h-4 w-4 text-emerald" /> : <ShieldAlert className="h-4 w-4 text-claret" />}
      <div className="leading-tight">
        <div className="font-body text-[12.5px] font-semibold" style={{ color: intact ? "#0F6E50" : "#A8324A" }}>
          {intact ? "Audit chain intact" : "Chain broken"}
        </div>
        <div className="flex items-center gap-1 font-mono text-[9.5px] uppercase tracking-wider text-subtle">
          <Link2 className="h-2.5 w-2.5" /> {entries} SHA-256 entries
        </div>
      </div>
    </div>
  );
}

function LoadingBlock() {
  return (
    <div className="grid h-[60vh] place-items-center">
      <div className="flex flex-col items-center gap-3 text-muted">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-line-strong border-t-emerald" />
        <span className="font-mono text-[11px] uppercase tracking-widest">Loading posture…</span>
      </div>
    </div>
  );
}

function BackendOffline({ detail }: { detail: string }) {
  return (
    <div className="grid h-[70vh] place-items-center">
      <Card className="max-w-md p-7 text-center">
        <AlertTriangle className="mx-auto h-7 w-7 text-gold" />
        <h2 className="mt-3 font-display text-lg font-semibold text-ink">Backend unreachable</h2>
        <p className="mt-2 text-[13px] text-muted">
          The workspace can&apos;t reach the API at{" "}
          <code className="font-mono text-emerald">{API_BASE}</code>. Start it with:
        </p>
        <pre className="mt-3 overflow-x-auto rounded-xl border border-line bg-paper-2 p-3 text-left font-mono text-[11px] text-muted">
uvicorn api.main:app --reload --port 8000
        </pre>
        <p className="mt-3 font-mono text-[10px] text-subtle">{detail}</p>
      </Card>
    </div>
  );
}
