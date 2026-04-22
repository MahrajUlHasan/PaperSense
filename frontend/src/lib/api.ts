import type {
  UploadResponse,
  QueryResponse,
  ResearchResponse,
  ScoreResponse,
} from "@/types";

const API =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "http://localhost:8000";

/* ── Upload ────────────────────────────────────────────────────── */

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API}/upload`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    return { success: false, error: err.detail || err.error || res.statusText };
  }
  return res.json();
}

/* ── Query ─────────────────────────────────────────────────────── */

export async function queryDocuments(
  question: string,
  documentId?: string,
  topK = 5,
  useHybrid = true
): Promise<QueryResponse> {
  const res = await fetch(`${API}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      document_id: documentId || undefined,
      top_k: topK,
      use_hybrid: useHybrid,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    return { success: false, error: err.detail || err.error || res.statusText };
  }
  return res.json();
}

/* ── Delete ────────────────────────────────────────────────────── */

export async function deleteDocument(
  docId: string
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/documents/${docId}`, { method: "DELETE" });
  return res.json();
}

/* ── Research ──────────────────────────────────────────────────── */

export async function setResearch(
  topic: string,
  description: string
): Promise<ResearchResponse> {
  const res = await fetch(`${API}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    return { success: false, error: err.detail || err.error || res.statusText };
  }
  return res.json();
}

export async function getResearch(): Promise<ResearchResponse> {
  const res = await fetch(`${API}/research`);
  return res.json();
}

/* ── Score ──────────────────────────────────────────────────────── */

export async function scoreDocument(docId: string): Promise<ScoreResponse> {
  const res = await fetch(`${API}/score/${docId}`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    return { success: false, error: err.detail || err.error || res.statusText };
  }
  return res.json();
}
