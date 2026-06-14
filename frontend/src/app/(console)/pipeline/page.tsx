"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Play, Square, FileText, CheckCircle2, AlertOctagon } from "lucide-react";
import { api } from "@/lib/api";
import type { Circular, RunSummary, StreamEvent } from "@/lib/types";
import AgentFlow from "@/components/AgentFlow";
import EventStream from "@/components/EventStream";
import CircularUpload from "@/components/CircularUpload";
import { Card, EmptyState, Kicker, SectionTitle, Badge } from "@/components/ui";

export default function PipelinePage() {
  const [circulars, setCirculars] = useState<Circular[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [maxParas, setMaxParas] = useState(6);

  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [seen, setSeen] = useState<Set<string>>(new Set());
  const [done, setDone] = useState<RunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    api
      .circulars()
      .then((cs) => {
        setCirculars(cs);
        if (cs[0]) setSelected(cs[0].path);
      })
      .catch(() => {});
    return () => esRef.current?.close();
  }, []);

  function start() {
    if (!selected) return;
    esRef.current?.close();
    setEvents([]);
    setActive(null);
    setSeen(new Set());
    setDone(null);
    setError(null);
    setRunning(true);

    const es = new EventSource(api.streamUrl(selected, maxParas));
    esRef.current = es;

    es.addEventListener("agent", (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as StreamEvent;
      setEvents((prev) => [...prev, data]);
      setActive(data.agent);
      setSeen((prev) => new Set(prev).add(data.agent));
    });

    es.addEventListener("done", (ev) => {
      const summary = JSON.parse((ev as MessageEvent).data) as RunSummary;
      setDone(summary);
      setActive(null);
      setRunning(false);
      es.close();
    });

    es.addEventListener("error", (ev) => {
      const me = ev as MessageEvent;
      if (me.data) {
        try {
          setError(JSON.parse(me.data).message ?? "Pipeline error");
        } catch {
          setError("Pipeline error");
        }
        setRunning(false);
        es.close();
      } else if (running) {
        setError("Connection to the pipeline stream was lost. Is the backend running on :8000?");
        setRunning(false);
        es.close();
      }
    });
  }

  function stop() {
    esRef.current?.close();
    setRunning(false);
    setActive(null);
  }

  return (
    <div>
      <div className="mb-7 flex items-end justify-between">
        <div>
          <Kicker className="mb-2">Operations</Kicker>
          <h1 className="font-display text-[34px] font-semibold leading-none tracking-tight text-ink">Pipeline</h1>
          <p className="mt-2.5 text-[14px] text-muted">Watch six agents reason over the circular in real time.</p>
        </div>
        {running && (
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald/25 bg-emerald-soft px-3.5 py-1.5 font-mono text-[10.5px] uppercase tracking-[0.14em] text-emerald">
            <span className="h-1.5 w-1.5 animate-breathe rounded-full bg-emerald" /> executing
          </span>
        )}
      </div>

      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-5">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1.5">
            <span className="kicker">Source circular</span>
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              disabled={running}
              className="rounded-xl border border-line bg-raised px-3.5 py-2.5 font-body text-[14px] text-ink outline-none focus:border-emerald/50 focus:shadow-ring"
            >
              {circulars.length === 0 && <option>No circulars found</option>}
              {circulars.map((c) => (
                <option key={c.path} value={c.path}>
                  {c.title.slice(0, 48)} · {c.classification}
                </option>
              ))}
            </select>
          </label>

          <label className="flex w-[200px] flex-col gap-1.5">
            <span className="kicker">Max paragraphs · {maxParas}</span>
            <input
              type="range"
              min={1}
              max={12}
              value={maxParas}
              disabled={running}
              onChange={(e) => setMaxParas(Number(e.target.value))}
              className="accent-emerald"
            />
          </label>

          <CircularUpload
            variant="compact"
            onUploaded={(c) => {
              setCirculars((prev) => [c, ...prev.filter((x) => x.path !== c.path)]);
              setSelected(c.path);
            }}
          />

          {!running ? (
            <button
              onClick={start}
              disabled={!selected}
              className="ml-auto inline-flex items-center gap-2 rounded-xl bg-ink px-5 py-2.5 font-body text-[14px] font-semibold text-paper transition-transform hover:-translate-y-px disabled:opacity-40"
            >
              <Play className="h-4 w-4" fill="currentColor" /> Run pipeline
            </button>
          ) : (
            <button
              onClick={stop}
              className="ml-auto inline-flex items-center gap-2 rounded-xl border border-claret/40 bg-claret/[0.06] px-5 py-2.5 font-body text-[14px] font-semibold text-claret"
            >
              <Square className="h-4 w-4" fill="currentColor" /> Stop
            </button>
          )}
        </div>
      </Card>

      <Card className="mt-3.5 p-6">
        <SectionTitle kicker="Topology" title="Agent flow" />
        <AgentFlow active={active} seen={seen} done={!!done} />
      </Card>

      {done && <RunResult summary={done} />}
      {error && (
        <Card className="mt-3.5 border-claret/30 p-4">
          <div className="flex items-center gap-2 text-claret">
            <AlertOctagon className="h-4 w-4" />
            <span className="font-display text-[15px] font-semibold">Run failed</span>
          </div>
          <p className="mt-1.5 text-[13px] text-muted">{error}</p>
        </Card>
      )}

      <Card className="mt-3.5 p-6">
        <SectionTitle
          kicker="Reasoning"
          title="Live agent stream"
          right={<span className="font-mono text-[11px] text-subtle tnum">{events.length} events</span>}
        />
        {events.length === 0 ? (
          <EmptyState
            title={running ? "Waiting for the first agent…" : "No run in progress"}
            hint="Configure the run above and hit Run pipeline. Each agent's reasoning streams here as it happens."
          />
        ) : (
          <div className="max-h-[540px] overflow-y-auto pr-1">
            <EventStream events={events} />
          </div>
        )}
      </Card>
    </div>
  );
}

function RunResult({ summary }: { summary: RunSummary }) {
  const cards = [
    { label: "Controls", value: summary.total_maps, color: "#211F1A" },
    { label: "Approved", value: summary.approved, color: "#0F6E50" },
    { label: "Rejected", value: summary.rejected, color: "#B5882E" },
    { label: "Violations", value: summary.violations, color: "#A8324A" },
    { label: "Escalations", value: summary.escalations, color: "#B05A35" },
  ];
  return (
    <Card className="mt-3.5 p-6" raised>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald" />
          <span className="font-display text-[16px] font-semibold text-ink">Run complete</span>
          <Badge tone="info">{summary.classification}</Badge>
        </div>
        <Link
          href={`/maps?run=${summary.run_id}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong bg-surface px-3.5 py-2 font-body text-[12.5px] font-medium text-ink hover:border-emerald/45"
        >
          <FileText className="h-3.5 w-3.5" /> Controls &amp; report
        </Link>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3.5 md:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border border-line bg-paper/40 p-4">
            <div className="kicker">{c.label}</div>
            <div className="mt-1.5 font-display text-[28px] font-semibold tnum" style={{ color: c.color }}>
              {c.value}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
