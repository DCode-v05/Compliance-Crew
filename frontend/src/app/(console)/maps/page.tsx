"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ChevronDown,
  Quote,
  ShieldCheck,
  ShieldAlert,
  Building2,
  Clock,
  GitBranch,
  Link2,
  FileText,
  Database,
  ListTree,
} from "lucide-react";
import { api } from "@/lib/api";
import type { AuditChainStatus, AuditEntry, MapRow, RunDetail, RunSummary } from "@/lib/types";
import { RISK_COLOR, PRIORITY_COLOR, agentMeta } from "@/lib/agents";
import { Card, EmptyState, Kicker, Badge, PillTag } from "@/components/ui";

type Tab = "controls" | "report" | "audit";

export default function MapsPage() {
  return (
    <Suspense fallback={<div className="text-[13px] text-muted">Loading…</div>}>
      <MapsInner />
    </Suspense>
  );
}

function MapsInner() {
  const params = useSearchParams();
  const runParam = params.get("run");

  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(runParam);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [maps, setMaps] = useState<MapRow[]>([]);
  const [tab, setTab] = useState<Tab>("controls");

  useEffect(() => {
    api
      .runs()
      .then((r) => {
        setRuns(r);
        if (!runId && r[0]) setRunId(r[0].run_id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!runId) return;
    api
      .run(runId)
      .then((d) => {
        setDetail(d);
        setMaps(d.maps);
      })
      .catch(() => {
        setDetail(null);
        setMaps([]);
      });
  }, [runId]);

  if (runs.length === 0 && !detail) {
    return (
      <div>
        <Header runs={runs} runId={runId} setRunId={setRunId} />
        <EmptyState title="No runs yet" hint="Run the pipeline first — its controls, report, and audit trail will appear here." />
      </div>
    );
  }

  return (
    <div>
      <Header runs={runs} runId={runId} setRunId={setRunId} detail={detail} />

      <div className="mb-5 inline-flex items-center gap-1 rounded-xl border border-line bg-surface p-1">
        {([["controls", "Controls", ListTree], ["report", "Report", FileText], ["audit", "Audit trail", Database]] as const).map(
          ([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 font-body text-[13px] font-medium transition-colors ${
                tab === key ? "bg-emerald-soft text-emerald" : "text-muted hover:text-ink"
              }`}
            >
              <Icon className="h-3.5 w-3.5" /> {label}
            </button>
          ),
        )}
      </div>

      {tab === "controls" && <ControlsTab maps={maps} />}
      {tab === "report" && <ReportTab markdown={detail?.report_markdown ?? ""} />}
      {tab === "audit" && <AuditTab />}
    </div>
  );
}

function Header({
  runs,
  runId,
  setRunId,
  detail,
}: {
  runs: RunSummary[];
  runId: string | null;
  setRunId: (id: string) => void;
  detail?: RunDetail | null;
}) {
  return (
    <div className="mb-7 flex items-end justify-between gap-4">
      <div>
        <Kicker className="mb-2">Controls</Kicker>
        <h1 className="font-display text-[34px] font-semibold leading-none tracking-tight text-ink">
          Mapped Action Policies
        </h1>
        <p className="mt-2.5 text-[14px] text-muted">
          {detail
            ? `${detail.circular} · ${detail.classification} · ${detail.approved}/${detail.total_maps} approved`
            : "Controls derived from the circular, with validation, routing, and evidence."}
        </p>
      </div>
      {runs.length > 0 && (
        <label className="flex flex-col gap-1.5">
          <span className="kicker">Run</span>
          <select
            value={runId ?? ""}
            onChange={(e) => setRunId(e.target.value)}
            className="max-w-[260px] rounded-xl border border-line bg-raised px-3 py-2 font-mono text-[11px] text-ink outline-none focus:border-emerald/50 focus:shadow-ring"
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.circular} · {new Date(r.created_at).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}

function ControlsTab({ maps }: { maps: MapRow[] }) {
  if (maps.length === 0) return <EmptyState title="No controls in this run" />;
  return (
    <div className="flex flex-col gap-3">
      {maps.map((m, i) => (
        <MapCard key={m.map_id} m={m} index={i} />
      ))}
    </div>
  );
}

function MapCard({ m, index }: { m: MapRow; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const approved = m.verdict === "approved";
  const riskColor = RISK_COLOR[m.risk_category] ?? "#6C6557";

  return (
    <Card className="animate-fade-up overflow-hidden">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3.5 px-5 py-4 text-left">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-line bg-paper-2 font-mono text-[12px] text-muted tnum">
          {String(index + 1).padStart(2, "0")}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-display text-[16px] font-semibold text-ink">{m.control_title}</span>
            {m.attempt_number > 1 && <Badge tone="warn">retry #{m.attempt_number}</Badge>}
          </div>
          <div className="mt-0.5 font-mono text-[10.5px] text-subtle">{m.paragraph_id}</div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <PillTag label={m.risk_category} color={riskColor} />
          {approved ? (
            <Badge tone="pass"><ShieldCheck className="h-2.5 w-2.5" /> approved</Badge>
          ) : (
            <Badge tone="flag"><ShieldAlert className="h-2.5 w-2.5" /> {m.verdict}</Badge>
          )}
          {m.escalated && <Badge tone="flag">CCO</Badge>}
          <ChevronDown className={`h-4 w-4 text-subtle transition-transform ${open ? "rotate-180" : ""}`} />
        </div>
      </button>

      {open && (
        <div className="border-t border-line px-5 py-4">
          <p className="text-[13.5px] leading-relaxed text-ink-soft">{m.control_description}</p>

          {m.citation && m.citation.verbatim_quote && (
            <div className="mt-3.5 rounded-xl border-l-2 border-emerald/50 bg-emerald-soft px-3.5 py-2.5">
              <div className="mb-1 flex items-center gap-1.5 font-mono text-[9.5px] uppercase tracking-wider text-emerald-deep">
                <Quote className="h-3 w-3 text-emerald" /> Verbatim citation · conf {(m.citation.confidence * 100).toFixed(0)}%
              </div>
              <p className="font-display text-[14px] italic leading-relaxed text-ink">
                &ldquo;{m.citation.verbatim_quote}&rdquo;
              </p>
            </div>
          )}

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-line bg-paper/50 p-3.5">
              <div className="kicker mb-2.5 flex items-center gap-1.5"><Building2 className="h-3 w-3" /> Assignment</div>
              {m.department ? (
                <div className="space-y-2 text-[13px]">
                  <Row label="Department" value={m.department} />
                  <Row label="Priority" value={<span style={{ color: PRIORITY_COLOR[m.priority ?? "routine"] }}>{m.priority}</span>} />
                  <Row label="Deadline" value={<span className="inline-flex items-center gap-1"><Clock className="h-3 w-3 text-subtle" /> {m.deadline_days}d</span>} />
                  {m.dependencies.length > 0 && (
                    <Row label="Depends on" value={<span className="inline-flex items-center gap-1"><GitBranch className="h-3 w-3 text-subtle" /> {m.dependencies.length}</span>} />
                  )}
                </div>
              ) : (
                <div className="text-[12px] text-subtle">Not routed (control not approved).</div>
              )}
            </div>

            <div className="rounded-xl border border-line bg-paper/50 p-3.5">
              <div className="kicker mb-2.5 flex items-center gap-1.5"><Database className="h-3 w-3" /> Evidence</div>
              {m.evidence_compliant === null || m.evidence_compliant === undefined ? (
                <div className="text-[12px] text-subtle">No evidence check.</div>
              ) : m.evidence_evaluated === false ? (
                <div className="flex items-center gap-2 text-[13px] text-gold"><ShieldAlert className="h-4 w-4" /> Not evaluated (rate-limited or query failed)</div>
              ) : m.evidence_compliant ? (
                <div className="flex items-center gap-2 text-[13.5px] text-emerald"><ShieldCheck className="h-4 w-4" /> Compliant — 0 violations</div>
              ) : (
                <div>
                  <div className="flex items-center gap-2 text-[13.5px] text-claret"><ShieldAlert className="h-4 w-4" /> {m.violations_found} violations</div>
                  {m.sample_violation_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.sample_violation_ids.slice(0, 8).map((id) => (
                        <span key={id} className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[9.5px] text-muted">{id}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              <div className="mt-2.5 font-mono text-[10px] uppercase tracking-wider text-subtle">type · {m.evidence_type}</div>
            </div>
          </div>

          {m.validation_reasoning && (
            <div className="mt-3 rounded-xl border border-line bg-paper/50 p-3.5">
              <div className="kicker mb-1.5">
                Validator verdict {m.rejection_category && m.rejection_category !== "none" ? `· ${m.rejection_category}` : ""}
              </div>
              <p className="text-[13px] leading-relaxed text-ink-soft">{m.validation_reasoning}</p>
              {m.cited_text && (
                <p className="mt-2 border-l-2 border-gold/40 pl-2.5 font-mono text-[11px] italic text-muted">&ldquo;{m.cited_text}&rdquo;</p>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10.5px] uppercase tracking-wider text-subtle">{label}</span>
      <span className="font-body font-medium text-ink">{value}</span>
    </div>
  );
}

function ReportTab({ markdown }: { markdown: string }) {
  if (!markdown) return <EmptyState title="No report" hint="The Auditor assembles the report at the end of a run." />;
  return (
    <Card className="p-8">
      <div className="md max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </Card>
  );
}

function AuditTab() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [chain, setChain] = useState<AuditChainStatus | null>(null);

  useEffect(() => {
    api.auditEntries(300).then(setEntries).catch(() => {});
    api.auditChain().then(setChain).catch(() => {});
  }, []);

  const meanLatency = useMemo(
    () => (entries.length ? Math.round(entries.reduce((a, e) => a + e.latency_ms, 0) / entries.length) : 0),
    [entries],
  );

  return (
    <div>
      <div className="mb-3.5 grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <MiniStat label="Audit entries" value={chain?.total ?? entries.length} />
        <MiniStat label="Mean latency" value={`${meanLatency}ms`} />
        <MiniStat label="Provider" value="Groq" />
        <div className={`rounded-2xl border p-4 ${chain?.intact ? "border-emerald/25 bg-emerald-soft" : "border-claret/25 bg-claret/[0.06]"}`}>
          <div className="kicker">Chain</div>
          <div className="mt-1.5 flex items-center gap-1.5 font-display text-[18px] font-semibold" style={{ color: chain?.intact ? "#0F6E50" : "#A8324A" }}>
            <Link2 className="h-3.5 w-3.5" /> {chain?.intact ? "Intact" : "Broken"}
          </div>
        </div>
      </div>

      <Card className="overflow-hidden">
        <div className="max-h-[560px] overflow-auto">
          <table className="w-full text-left text-[12.5px]">
            <thead className="sticky top-0 bg-surface/95 font-mono text-[9.5px] uppercase tracking-wider text-subtle backdrop-blur">
              <tr className="border-b border-line">
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-3 py-3 font-medium">Provider</th>
                <th className="px-3 py-3 text-right font-medium">Latency</th>
                <th className="px-3 py-3 font-medium">Entry hash</th>
                <th className="px-4 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {entries.map((e) => {
                const meta = agentMeta(e.agent_name);
                return (
                  <tr key={e.entry_id} className="hover:bg-paper/50">
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
                        <span className="font-body font-medium" style={{ color: meta.color }}>{meta.label}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-muted">{e.provider}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-muted tnum">{e.latency_ms}ms</td>
                    <td className="px-3 py-2.5 font-mono text-[10px] text-subtle">{e.entry_hash.slice(0, 16)}…</td>
                    <td className="px-4 py-2.5 font-mono text-[10px] text-subtle">{new Date(e.timestamp).toLocaleTimeString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      {chain && <p className="mt-2 font-mono text-[10px] text-subtle">{chain.detail}</p>}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="kicker">{label}</div>
      <div className="mt-1.5 font-display text-[22px] font-semibold text-ink tnum">{value}</div>
    </div>
  );
}
