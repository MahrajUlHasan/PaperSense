/** Shapes returned by the PaperSense v2 API (backend/models/schemas.py). */

export type ProviderId = "gemini" | "groq" | "openrouter";

export type DocumentStatus = "queued" | "parsing" | "enriching" | "embedding" | "ready" | "error";

export interface DocumentStats {
  title?: string;
  chunks?: number;
  tables?: number;
  figures?: number;
  figures_described?: number;
  formulas?: number;
  formulas_decoded?: number;
  formulas_read?: number;
  coverage?: number;
  low_coverage_pages?: number[];
  ocr_used?: boolean;
  parse_seconds?: number;
  notes?: string[];
}

export interface DocumentInfo {
  id: string;
  filename: string;
  status: DocumentStatus;
  progress: string | null;
  error: string | null;
  mode: "full" | "basic" | null;
  page_count: number | null;
  stats: DocumentStats | null;
  score: number | null;
  score_explanation: string | null;
  created_at: string;
  updated_at: string;
}

/** A rectangle on a PDF page in PDF points, origin at the top-left corner. */
export interface Box {
  page: number;
  l: number;
  t: number;
  r: number;
  b: number;
}

export interface Citation {
  index: number;
  document_id: string;
  filename: string;
  section: string;
  content_type: string;
  pages: number[];
  page: number | null;
  boxes: Box[];
  relevance: number;
  text: string;
  figure_index: number | null;
}

export interface QueryResponse {
  success: boolean;
  question: string;
  answer: string;
  citations: Citation[];
  search_query: string;
  contexts: string[];
}

export interface ProviderInfo {
  id: ProviderId;
  name: string;
  default_model: string;
  supports_images: boolean;
  key_url: string;
}

export interface ProvidersResponse {
  default_provider: ProviderId;
  providers: ProviderInfo[];
  server_key_available: boolean;
}

export interface KeyTestResponse {
  ok: boolean;
  message: string;
  code: string | null;
}

export interface ResearchInfo {
  topic: string;
  description: string;
  breakdown: string;
  updated_at: string | null;
}

export interface ScoreResponse {
  document_id: string;
  score: number;
  explanation: string;
}

export interface AnalysisResponse {
  document_id: string;
  summary: string;
  key_findings: string[];
  methodology: string;
  limitations: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations?: Citation[];
  question?: string;
  searchQuery?: string;
  error?: boolean;
  retryOf?: string;
}
