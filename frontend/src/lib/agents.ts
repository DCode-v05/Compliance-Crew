// Shared agent + status metadata (Ledger warm palette) used across the app.

export interface AgentMeta {
  key: string;
  label: string;
  role: string;
  color: string; // hex
}

export const AGENTS: Record<string, AgentMeta> = {
  ingestor: { key: "ingestor", label: "Ingestor", role: "Parse & classify", color: "#3F6E8C" },
  mapper: { key: "mapper", label: "Mapper", role: "Derive controls", color: "#6E5A93" },
  validator: { key: "validator", label: "Validator", role: "Adversarial review", color: "#B5882E" },
  assigner: { key: "assigner", label: "Assigner", role: "Route & escalate", color: "#2C7E84" },
  evidence_checker: { key: "evidence_checker", label: "Evidence", role: "Check bank data", color: "#0F6E50" },
  auditor: { key: "auditor", label: "Auditor", role: "Assemble report", color: "#A8324A" },
  chatbot: { key: "chatbot", label: "Assistant", role: "Compliance Q&A", color: "#2C7E84" },
};

export function agentMeta(key: string): AgentMeta {
  return (
    AGENTS[key] ?? {
      key,
      label: key.replace(/_/g, " "),
      role: "",
      color: "#6C6557",
    }
  );
}

export const RISK_COLOR: Record<string, string> = {
  low: "#0F6E50",
  medium: "#B5882E",
  high: "#B05A35",
  critical: "#A8324A",
};

export const PRIORITY_COLOR: Record<string, string> = {
  routine: "#6C6557",
  elevated: "#B5882E",
  urgent: "#B05A35",
  critical: "#A8324A",
};

export function classifyBadge(summary: string): "pass" | "flag" | "info" {
  const s = summary.toUpperCase();
  if (s.includes("REJECT") || s.includes("VIOLATION") || s.includes("NON-COMPLIANT") || s.includes("ESCALATED"))
    return "flag";
  if (s.includes("APPROVED") || s.includes("COMPLIANT") || s.includes("OK")) return "pass";
  return "info";
}
