import clsx from "clsx";
import { AGENT_ORDER } from "@/lib/types";
import { agentMeta } from "@/lib/agents";
import { Check, RotateCcw } from "lucide-react";

/**
 * Horizontal six-node pipeline visualiser. The active node lifts and glows;
 * completed nodes show a check; the Validator→Mapper retry loop is annotated
 * because that conditional edge is the spine of the system.
 */
export default function AgentFlow({
  active,
  seen,
  done,
}: {
  active: string | null;
  seen: Set<string>;
  done: boolean;
}) {
  return (
    <div className="relative overflow-x-auto">
      <div className="flex min-w-[680px] items-stretch gap-0 px-1 py-2">
        {AGENT_ORDER.map((key, i) => {
          const meta = agentMeta(key);
          const isActive = active === key && !done;
          const isSeen = seen.has(key);
          const isDone = (done || (isSeen && active !== key)) && isSeen;
          return (
            <div key={key} className="flex flex-1 items-center">
              <div className="flex flex-1 flex-col items-center">
                <div
                  className={clsx(
                    "relative grid h-12 w-12 place-items-center rounded-2xl border transition-all duration-300",
                    isActive ? "-translate-y-0.5 scale-105" : "scale-100",
                  )}
                  style={{
                    borderColor: isSeen || isActive ? `${meta.color}55` : "#E4DECF",
                    background: isActive ? `${meta.color}1a` : isSeen ? `${meta.color}0f` : "#FCFAF4",
                    boxShadow: isActive ? `0 0 0 4px ${meta.color}1f, 0 8px 20px ${meta.color}26` : "none",
                  }}
                >
                  <span
                    className="font-display text-lg font-semibold"
                    style={{ color: isSeen || isActive ? meta.color : "#9A937F" }}
                  >
                    {meta.label[0]}
                  </span>
                  {isDone && !isActive && (
                    <span
                      className="absolute -bottom-1 -right-1 grid h-4 w-4 place-items-center rounded-full border-2 border-surface"
                      style={{ background: meta.color }}
                    >
                      <Check className="h-2.5 w-2.5 text-white" strokeWidth={3.5} />
                    </span>
                  )}
                  {isActive && (
                    <span
                      className="absolute inset-0 animate-breathe rounded-2xl"
                      style={{ boxShadow: `0 0 0 1px ${meta.color}66` }}
                    />
                  )}
                </div>
                <div className="mt-2.5 text-center">
                  <div
                    className="font-body text-[12px] font-semibold"
                    style={{ color: isSeen || isActive ? "#211F1A" : "#9A937F" }}
                  >
                    {meta.label}
                  </div>
                  <div className="font-mono text-[8.5px] uppercase tracking-wider text-subtle">{meta.role}</div>
                </div>
              </div>

              {i < AGENT_ORDER.length - 1 && (
                <div className="relative mx-1 flex w-10 shrink-0 items-center self-start pt-5">
                  <div
                    className="h-[2px] w-full rounded-full"
                    style={{ background: isSeen ? "#D3CAB5" : "#E4DECF" }}
                  />
                  <div
                    className="absolute right-0 h-0 w-0"
                    style={{
                      borderTop: "4px solid transparent",
                      borderBottom: "4px solid transparent",
                      borderLeft: `5px solid ${isSeen ? "#D3CAB5" : "#E4DECF"}`,
                    }}
                  />
                  {key === "validator" && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <RotateCcw className="h-3 w-3 text-gold" />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 px-1 font-mono text-[9.5px] uppercase tracking-wider text-subtle">
        <RotateCcw className="h-3 w-3 text-gold" />
        Validator can reject → Mapper retries with cited feedback
      </div>
    </div>
  );
}
