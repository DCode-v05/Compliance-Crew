"use client";

import { useRef, useState } from "react";
import { UploadCloud, FileUp, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import type { Circular } from "@/lib/types";

const ACCEPT = ".pdf,.txt,.md";

export default function CircularUpload({
  variant = "full",
  onUploaded,
}: {
  variant?: "full" | "compact";
  onUploaded: (c: Circular) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okName, setOkName] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file || busy) return;
    setError(null);
    setOkName(null);
    setBusy(true);
    try {
      const circular = await api.uploadCircular(file);
      setOkName(circular.title || file.name);
      onUploaded(circular);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  const pick = () => inputRef.current?.click();

  const hiddenInput = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPT}
      className="hidden"
      onChange={(e) => handleFile(e.target.files?.[0])}
    />
  );

  if (variant === "compact") {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="kicker">Add your own</span>
        <button
          type="button"
          onClick={pick}
          disabled={busy}
          className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3.5 py-2.5 font-body text-[13px] font-medium text-muted transition-colors hover:border-emerald/40 hover:text-ink disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin text-emerald" /> : <FileUp className="h-4 w-4" />}
          {busy ? "Uploading…" : "Upload PDF"}
        </button>
        {error && <span className="text-[10.5px] text-claret">{error}</span>}
        {okName && !error && <span className="truncate text-[10.5px] text-emerald">Added · {okName}</span>}
        {hiddenInput}
      </div>
    );
  }

  return (
    <div>
      <div
        onClick={pick}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        className={`group flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed px-6 py-10 text-center transition-colors ${
          drag ? "border-emerald bg-emerald-soft" : "border-line-strong bg-surface hover:border-emerald/45"
        }`}
      >
        <div className="grid h-12 w-12 place-items-center rounded-2xl border border-emerald/25 bg-emerald-soft">
          {busy ? (
            <Loader2 className="h-6 w-6 animate-spin text-emerald" />
          ) : (
            <UploadCloud className="h-6 w-6 text-emerald" />
          )}
        </div>
        <div>
          <div className="font-display text-[15px] font-semibold text-ink">
            {busy ? "Analysing document…" : "Drop an RBI circular here, or click to browse"}
          </div>
          <div className="mt-1 font-mono text-[10.5px] uppercase tracking-wider text-subtle">
            PDF · TXT · MD · up to 15 MB
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-2 flex items-center gap-2 rounded-xl border border-claret/25 bg-claret/[0.06] px-3 py-2 text-[12px] text-claret">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {error}
        </div>
      )}
      {okName && !error && (
        <div className="mt-2 flex items-center gap-2 rounded-xl border border-emerald/25 bg-emerald-soft px-3 py-2 text-[12px] text-emerald">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0" /> Uploaded &amp; classified · {okName}
        </div>
      )}
      {hiddenInput}
    </div>
  );
}
