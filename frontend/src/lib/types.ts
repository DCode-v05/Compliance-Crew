export interface Citation {
  paragraph_id: string;
  verbatim_quote: string;
  confidence: number;
  source_doc_id: string;
}

export type Verdict = "approved" | "rejected" | "pending";
export type Risk = "low" | "medium" | "high" | "critical";
export type Priority = "routine" | "elevated" | "urgent" | "critical";

export interface MapRow {
  map_id: string;
  paragraph_id: string;
  control_title: string;
  control_description: string;
  evidence_type: string;
  risk_category: Risk;
  attempt_number: number;
  citation: Citation | null;
  verdict: Verdict | null;
  rejection_category: string | null;
  validation_reasoning: string | null;
  cited_text: string | null;
  department: string | null;
  priority: Priority | null;
  deadline_days: number | null;
  dependencies: string[];
  evidence_compliant: boolean | null;
  evidence_evaluated: boolean | null;
  violations_found: number | null;
  sample_violation_ids: string[];
  escalated: boolean;
}

export interface RunSummary {
  run_id: string;
  circular: string;
  source_doc_id: string;
  classification: string;
  urgency_score: number;
  paragraphs: number;
  total_maps: number;
  approved: number;
  rejected: number;
  violations: number;
  escalations: number;
  created_at: string;
  status: string;
}

export interface StreamEvent {
  agent: string;
  summary: string;
  detail: string;
}

export interface RunDetail extends RunSummary {
  maps: MapRow[];
  events: StreamEvent[];
  report_markdown: string;
}

export interface Circular {
  source_doc_id: string;
  title: string;
  reference_number: string;
  classification: string;
  urgency_score: number;
  effective_date: string;
  paragraph_count: number;
  synopsis: string;
  path: string;
}

export interface DepartmentLoad {
  department: string;
  count: number;
}
export interface RiskLoad {
  risk_category: string;
  count: number;
}

export interface DashboardStats {
  total_runs: number;
  circulars_available: number;
  controls_derived: number;
  controls_approved: number;
  validator_rejections: number;
  total_violations: number;
  open_escalations: number;
  audit_entries: number;
  chain_intact: boolean;
  compliance_rate: number;
  by_department: DepartmentLoad[];
  by_risk: RiskLoad[];
  recent_runs: RunSummary[];
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  grounded: boolean;
  run_id: string | null;
}

export interface LlmStatus {
  provider: string;
  model: string;
  configured: boolean;
  reachable: boolean;
  detail: string;
}

export interface AuditEntry {
  entry_id: string;
  agent_name: string;
  provider: string;
  latency_ms: number;
  tokens_used: number;
  timestamp: string;
  input_hash: string;
  prev_hash: string;
  entry_hash: string;
}

export interface AuditChainStatus {
  intact: boolean;
  total: number;
  broken_at: number | null;
  detail: string;
}

export const AGENT_ORDER = [
  "ingestor",
  "mapper",
  "validator",
  "assigner",
  "evidence_checker",
  "auditor",
] as const;
export type AgentName = (typeof AGENT_ORDER)[number];
