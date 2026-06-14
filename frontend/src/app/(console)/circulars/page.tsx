"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Hash, CalendarClock, Layers, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import type { Circular } from "@/lib/types";
import { Card, EmptyState, Kicker, Badge } from "@/components/ui";
import CircularUpload from "@/components/CircularUpload";

function urgencyTone(score: number) {
  if (score >= 0.66) return { label: "High", color: "#A8324A" };
  if (score >= 0.45) return { label: "Elevated", color: "#B5882E" };
  return { label: "Routine", color: "#0F6E50" };
}

export default function CircularsPage() {
  const [items, setItems] = useState<Circular[] | null>(null);

  useEffect(() => {
    api.circulars().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <div>
      <div className="mb-7">
        <Kicker className="mb-2">Intelligence</Kicker>
        <h1 className="font-display text-[34px] font-semibold leading-none tracking-tight text-ink">
          Circular monitor
        </h1>
        <p className="mt-2.5 text-[14px] text-muted">
          Regulation documents on file, classified and scored by urgency. Upload your own to analyse it.
        </p>
      </div>

      <div className="mb-7">
        <CircularUpload
          variant="full"
          onUploaded={(c) =>
            setItems((prev) => [c, ...(prev ?? []).filter((x) => x.source_doc_id !== c.source_doc_id)])
          }
        />
      </div>

      {!items ? (
        <div className="text-[13px] text-muted">Loading…</div>
      ) : items.length === 0 ? (
        <EmptyState title="No circulars found" hint="Drop a .pdf or .txt RBI circular above to get started." />
      ) : (
        <div className="grid gap-3.5 lg:grid-cols-2">
          {items.map((c, i) => {
            const tone = urgencyTone(c.urgency_score);
            return (
              <Card
                key={c.source_doc_id}
                className="animate-fade-up p-6"
                style={{ animationDelay: `${i * 70}ms` } as React.CSSProperties}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-line bg-paper-2">
                      <FileText className="h-[18px] w-[18px] text-assigner" />
                    </div>
                    <div>
                      <h3 className="font-display text-[17px] font-semibold leading-tight text-ink">{c.title}</h3>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Badge tone="info">{c.classification}</Badge>
                        {c.reference_number && (
                          <span className="inline-flex items-center gap-1 font-mono text-[10px] text-subtle">
                            <Hash className="h-2.5 w-2.5" /> {c.reference_number}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <UrgencyRing score={c.urgency_score} color={tone.color} label={tone.label} />
                </div>

                <p className="mt-3.5 line-clamp-3 text-[13px] leading-relaxed text-muted">{c.synopsis}</p>

                <div className="mt-5 flex items-center justify-between border-t border-line pt-3.5">
                  <div className="flex items-center gap-4 font-mono text-[10.5px] text-subtle">
                    <span className="inline-flex items-center gap-1"><Layers className="h-3 w-3" /> {c.paragraph_count} paras</span>
                    {c.effective_date && (
                      <span className="inline-flex items-center gap-1"><CalendarClock className="h-3 w-3" /> {c.effective_date}</span>
                    )}
                  </div>
                  <Link
                    href="/pipeline"
                    className="inline-flex items-center gap-1.5 rounded-xl border border-line-strong bg-surface px-3.5 py-2 font-body text-[12.5px] font-medium text-ink transition-colors hover:border-emerald/45"
                  >
                    Analyse <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function UrgencyRing({ score, color, label }: { score: number; color: string; label: string }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className="grid h-14 w-14 place-items-center rounded-full"
        style={{ background: `conic-gradient(${color} ${pct * 3.6}deg, #EDE9DC 0deg)` }}
      >
        <div className="grid h-11 w-11 place-items-center rounded-full bg-surface">
          <span className="font-display text-[15px] font-semibold tnum" style={{ color }}>{pct}</span>
        </div>
      </div>
      <span className="font-mono text-[9px] uppercase tracking-wider" style={{ color }}>{label}</span>
    </div>
  );
}
