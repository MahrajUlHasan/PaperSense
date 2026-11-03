import type {
  AnalysisResponse,
  DocumentInfo,
  KeyTestResponse,
  ProviderId,
  ProvidersResponse,
  QueryResponse,
  ResearchInfo,
  ScoreResponse,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

/** Who is asking, in which chat, and with which key. */
export interface RequestIdentity {
  workspaceId: string;
  sessionId?: string;
  provider?: ProviderId;
  model?: string;
  llmKey?: string;
  geminiKey?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly helpUrl?: string | null;
  readonly retryAfter?: number | null;

  constructor(
    status: number,
    message: string,
    extra: { code?: string; helpUrl?: string | null; retryAfter?: number | null } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = extra.code;
    this.helpUrl = extra.helpUrl;
    this.retryAfter = extra.retryAfter;
  }
}

let currentIdentity: () => RequestIdentity = () => ({ workspaceId: "" });

/** Tells the client where to read the workspace id, chat id and keys from (the stores, see AppShell). */
export function configureApi(identity: () => RequestIdentity): void {
  currentIdentity = identity;
}

/**
 * Request headers. Keys are added only to requests that call an LLM, so listing papers or
 * downloading a PDF never carries a key.
 */
export function buildHeaders(identity: RequestIdentity, withKeys: boolean): Record<string, string> {
  const headers: Record<string, string> = {};
  if (identity.workspaceId) headers["X-Workspace-Id"] = identity.workspaceId;
  if (identity.sessionId) headers["X-Session-Id"] = identity.sessionId;
  if (!withKeys) return headers;
  if (identity.provider) headers["X-LLM-Provider"] = identity.provider;
  const model = identity.model?.trim();
  if (model) headers["X-LLM-Model"] = model;
  const llmKey = identity.llmKey?.trim();
  if (llmKey) headers["X-LLM-Key"] = llmKey;
  const geminiKey = identity.geminiKey?.trim();
  if (geminiKey) headers["X-Gemini-Key"] = geminiKey;
  return headers;
}

interface ErrorDetail {
  code?: string;
  message?: string;
  help_url?: string | null;
  retry_after?: number | null;
}

/** FastAPI errors come as {detail: string}, {detail: [validation errors]} or {detail: {code, message, …}}. */
export async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return new ApiError(response.status, detail);
  if (Array.isArray(detail)) {
    return new ApiError(response.status, "Some fields are missing or invalid.", { code: "validation" });
  }
  if (detail && typeof detail === "object") {
    const d = detail as ErrorDetail;
    return new ApiError(response.status, d.message ?? `Request failed (${response.status}).`, {
      code: d.code,
      helpUrl: d.help_url,
      retryAfter: d.retry_after,
    });
  }
  return new ApiError(response.status, `Request failed (${response.status}).`);
}

interface RequestOptions extends RequestInit {
  withKeys?: boolean;
}

async function request<T>(path: string, { withKeys = false, headers, ...init }: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { ...buildHeaders(currentIdentity(), withKeys), ...(headers as Record<string, string> | undefined) },
    });
  } catch {
    throw new ApiError(0, "Can't reach the PaperSense server. Check that the backend is running.", {
      code: "offline",
    });
  }
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

function postJson(body: unknown, withKeys = false): RequestOptions {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), withKeys };
}

export const api = {
  providers: () => request<ProvidersResponse>("/config/providers"),
  testKey: (provider: ProviderId, apiKey: string, model?: string) =>
    request<KeyTestResponse>("/keys/test", postJson({ provider, api_key: apiKey, model: model?.trim() || null })),
  listDocuments: async () => (await request<{ documents: DocumentInfo[] }>("/documents")).documents,
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentInfo>("/documents", { method: "POST", body: form, withKeys: true });
  },
  deleteDocument: (id: string) => request<{ success: boolean }>(`/documents/${id}`, { method: "DELETE" }),
  query: (question: string, documentIds: string[]) =>
    request<QueryResponse>(
      "/query",
      postJson({ question, document_ids: documentIds.length ? documentIds : null }, true),
    ),
  clearSession: () => request<{ success: boolean }>("/sessions/current", { method: "DELETE" }),
  getResearch: () => request<ResearchInfo>("/research"),
  saveResearch: (topic: string, description: string) =>
    request<ResearchInfo>("/research", postJson({ topic, description }, true)),
  scoreDocument: (id: string) =>
    request<ScoreResponse>(`/documents/${id}/score`, { method: "POST", withKeys: true }),
  analyzeDocument: (id: string) => request<AnalysisResponse>(`/documents/${id}/analysis`, { withKeys: true }),
};

export function fileUrl(documentId: string, workspaceId: string): string {
  return `${API_URL}/documents/${documentId}/file?ws=${encodeURIComponent(workspaceId)}`;
}

export function figureUrl(documentId: string, figureIndex: number, workspaceId: string): string {
  return `${API_URL}/documents/${documentId}/figures/${figureIndex}?ws=${encodeURIComponent(workspaceId)}`;
}
