import type {
  AuditChainStatus,
  AuditEntry,
  ChatResponse,
  Circular,
  DashboardStats,
  LlmStatus,
  MapRow,
  RunDetail,
  RunSummary,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string }>("/api/v1/health"),
  llmStatus: () => get<LlmStatus>("/api/v1/pipeline/llm/status"),
  dashboard: () => get<DashboardStats>("/api/v1/dashboard/stats"),
  circulars: () => get<Circular[]>("/api/v1/circulars"),
  circular: (id: string) => get<Circular>(`/api/v1/circulars/${id}`),
  uploadCircular: async (file: File): Promise<Circular> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/circulars/upload`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      let detail = `Upload failed (${res.status})`;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {
      }
      throw new Error(detail);
    }
    return res.json() as Promise<Circular>;
  },
  runs: () => get<RunSummary[]>("/api/v1/pipeline/runs"),
  run: (id: string) => get<RunDetail>(`/api/v1/pipeline/runs/${id}`),
  maps: (runId?: string) =>
    get<MapRow[]>(`/api/v1/maps${runId ? `?run_id=${runId}` : ""}`),
  auditEntries: (limit = 500) =>
    get<AuditEntry[]>(`/api/v1/audit/entries?limit=${limit}`),
  auditChain: () => get<AuditChainStatus>("/api/v1/audit/chain"),
  chat: (question: string, run_id?: string | null) =>
    post<ChatResponse>("/api/v1/chat", { question, run_id }),
  runSync: (circular_path: string, max_paragraphs: number) =>
    post<RunSummary>("/api/v1/pipeline/run", { circular_path, max_paragraphs }),
  streamUrl: (circular_path: string, max_paragraphs: number) => {
    const q = new URLSearchParams({
      circular_path,
      max_paragraphs: String(max_paragraphs),
    });
    return `${API_BASE}/api/v1/pipeline/stream?${q.toString()}`;
  },
};
