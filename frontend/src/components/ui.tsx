import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({
  className,
  children,
  raised,
  style,
}: {
  className?: string;
  children: ReactNode;
  raised?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={style}
      className={clsx(
        "relative rounded-2xl border border-line bg-surface",
        raised ? "shadow-raised" : "shadow-card",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("kicker", className)}>{children}</div>;
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  delay = 0,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "emerald" | "claret" | "gold" | "clay";
  delay?: number;
}) {
  const toneColor = {
    default: "#211F1A",
    emerald: "#0F6E50",
    claret: "#A8324A",
    gold: "#B5882E",
    clay: "#B05A35",
  }[tone];
  return (
    <div
      className="animate-fade-up rounded-2xl border border-line bg-surface p-5 shadow-card"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="kicker">{label}</div>
      <div
        className="mt-2.5 font-display text-[34px] font-semibold leading-none tnum"
        style={{ color: toneColor }}
      >
        {value}
      </div>
      {hint && <div className="mt-2 text-[12px] text-subtle">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "info",
  className,
}: {
  children: ReactNode;
  tone?: "pass" | "flag" | "warn" | "info";
  className?: string;
}) {
  const styles = {
    pass: "border-emerald/25 bg-emerald-soft text-emerald",
    flag: "border-claret/25 bg-claret/10 text-claret",
    warn: "border-gold/30 bg-gold/10 text-[#8a6418]",
    info: "border-line-strong bg-paper-2 text-muted",
  }[tone];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider",
        styles,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Dot({ color, pulse }: { color: string; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2">
      {pulse && (
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-50"
          style={{ background: color }}
        />
      )}
      <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: color }} />
    </span>
  );
}

export function PillTag({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider"
      style={{ borderColor: `${color}33`, background: `${color}12`, color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

export function ProgressBar({ value, color = "#0F6E50" }: { value: number; color?: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-paper-2">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%`, background: color }}
      />
    </div>
  );
}

export function SectionTitle({
  kicker,
  title,
  right,
}: {
  kicker?: string;
  title: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4">
      <div>
        {kicker && <Kicker className="mb-1.5">{kicker}</Kicker>}
        <h2 className="font-display text-[22px] font-semibold tracking-tight text-ink">{title}</h2>
      </div>
      {right}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line-strong bg-surface/60 px-6 py-16 text-center">
      <div className="font-display text-base font-medium text-ink">{title}</div>
      {hint && <div className="mt-1.5 max-w-md text-[13px] text-muted">{hint}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-[13px] text-muted">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line-strong border-t-emerald" />
      {label}
    </div>
  );
}
