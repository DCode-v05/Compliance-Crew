"use client";

import { useEffect, useRef } from "react";
import type { StreamEvent } from "@/lib/types";
import { agentMeta, classifyBadge } from "@/lib/agents";
import { Badge } from "./ui";

export default function EventStream({ events }: { events: StreamEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  return (
    <div className="flex flex-col gap-2.5">
      {events.map((e, i) => {
        const meta = agentMeta(e.agent);
        const badge = classifyBadge(e.summary);
        return (
          <div
            key={i}
            className="animate-fade-up rounded-xl border border-line bg-raised p-3.5 pl-4 shadow-card"
            style={{ borderLeft: `3px solid ${meta.color}` }}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
                <span
                  className="font-mono text-[10px] font-medium uppercase tracking-[0.12em]"
                  style={{ color: meta.color }}
                >
                  {meta.label}
                </span>
              </div>
              <Badge tone={badge === "pass" ? "pass" : badge === "flag" ? "flag" : "info"}>
                {badge === "pass" ? "passed" : badge === "flag" ? "flagged" : "in flight"}
              </Badge>
            </div>
            <div className="mt-1.5 text-[13.5px] leading-snug text-ink">{e.summary}</div>
            {e.detail && (
              <div className="mt-2 rounded-lg border border-line bg-paper/60 px-3 py-2 font-mono text-[11px] leading-relaxed text-muted">
                {e.detail}
              </div>
            )}
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}
