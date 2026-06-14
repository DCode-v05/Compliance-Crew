"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Quote, ShieldCheck, ShieldAlert, Sparkles, User } from "lucide-react";
import { api } from "@/lib/api";
import type { Citation } from "@/lib/types";
import { Card, Kicker, Spinner } from "@/components/ui";

interface Msg {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  grounded?: boolean;
}

const SUGGESTIONS = [
  "How often must high-risk customers have KYC updated?",
  "Which controls are non-compliant, and why?",
  "What was escalated to the CCO and on what deadline?",
  "Summarise the compliance posture for this circular.",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  async function ask(q: string) {
    const question = q.trim();
    if (!question || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.chat(question);
      setMessages((m) => [...m, { role: "assistant", text: res.answer, citations: res.citations, grounded: res.grounded }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "The assistant is unreachable. Is the backend running on :8000?", grounded: false }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-7.5rem)] flex-col">
      <div className="mb-5">
        <Kicker className="mb-2">Assistant</Kicker>
        <h1 className="font-display text-[34px] font-semibold leading-none tracking-tight text-ink">
          Compliance Q&amp;A
        </h1>
        <p className="mt-2.5 text-[14px] text-muted">
          Grounded in the latest run. Every regulatory claim is cited; if the answer isn&apos;t in the analysis, it says so.
        </p>
      </div>

      <Card className="flex min-h-0 flex-1 flex-col p-0">
        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-5 text-center">
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-emerald/25 bg-emerald-soft">
                <Sparkles className="h-6 w-6 text-emerald" />
              </div>
              <div>
                <div className="font-display text-[17px] font-semibold text-ink">Ask about the compliance analysis</div>
                <div className="mt-1 text-[13px] text-muted">Pick a question or type your own.</div>
              </div>
              <div className="flex max-w-xl flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    className="rounded-xl border border-line bg-paper/60 px-3.5 py-2 text-left font-body text-[12.5px] text-muted transition-colors hover:border-emerald/45 hover:text-ink"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((m, i) => (
                <Bubble key={i} m={m} />
              ))}
              {loading && (
                <div className="flex items-center gap-2 pl-12">
                  <Spinner label="Reasoning over the run context…" />
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="flex items-center gap-2.5 border-t border-line p-3.5"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about controls, violations, escalations…"
            className="flex-1 rounded-xl border border-line bg-raised px-4 py-3 text-[14px] text-ink outline-none placeholder:text-subtle focus:border-emerald/50 focus:shadow-ring"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="grid h-11 w-11 place-items-center rounded-xl bg-ink text-paper transition-transform hover:-translate-y-px disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </Card>
    </div>
  );
}

function Bubble({ m }: { m: Msg }) {
  if (m.role === "user") {
    return (
      <div className="flex items-start justify-end gap-3">
        <div className="max-w-[80%] rounded-2xl rounded-tr-md border border-line-strong bg-paper-2 px-4 py-2.5 text-[14px] text-ink">
          {m.text}
        </div>
        <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-line bg-paper-2">
          <User className="h-4 w-4 text-muted" />
        </div>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-emerald/25 bg-emerald-soft">
        <Sparkles className="h-4 w-4 text-emerald" />
      </div>
      <div className="max-w-[80%]">
        <div className="rounded-2xl rounded-tl-md border border-line bg-paper/50 px-4 py-3 text-[14px] leading-relaxed text-ink">
          <div className="mb-1.5 flex items-center gap-1.5">
            {m.grounded ? (
              <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-wider text-emerald"><ShieldCheck className="h-3 w-3" /> grounded</span>
            ) : (
              <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-wider text-gold"><ShieldAlert className="h-3 w-3" /> not in context</span>
            )}
          </div>
          {m.text}
          {m.citations && m.citations.length > 0 && (
            <div className="mt-3 space-y-1.5">
              {m.citations.map((c, i) => (
                <div key={i} className="rounded-xl border-l-2 border-emerald/40 bg-surface px-3 py-1.5">
                  <div className="font-mono text-[9px] uppercase tracking-wider text-subtle">{c.paragraph_id}</div>
                  <div className="mt-0.5 flex items-start gap-1.5 font-display text-[12.5px] italic text-muted">
                    <Quote className="mt-0.5 h-2.5 w-2.5 shrink-0 text-emerald" /> &ldquo;{c.verbatim_quote}&rdquo;
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
