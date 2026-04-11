export interface Source {
  documentId: string;
  filename: string;
  status: "uploading" | "processing" | "scoring" | "ready" | "error";
  file: File;
  blobUrl: string;
  score?: number;
  scoreExplanation?: string;
  error?: string;
}

export interface Citation {
  index: number;
  section: string;
  score: number;
  document_id: string;
  filename?: string;
  text?: string;
  content_type?: string;
  page?: number;
}

export interface SourceInfo {
  document_id: string;
  filename: string;
  metadata?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  sources?: SourceInfo[];
  timestamp: Date;
}

export interface UploadResponse {
  success: boolean;
  document_id?: string;
  filename?: string;
  metadata?: Record<string, unknown>;
  statistics?: Record<string, unknown>;
  error?: string;
}

export interface QueryResponse {
  success: boolean;
  question?: string;
  answer?: string;
  citations?: Citation[];
  sources?: SourceInfo[];
  context_used?: number;
  error?: string;
}

export interface ResearchData {
  topic: string;
  description: string;
  breakdown?: string;
}

export interface ResearchResponse {
  success: boolean;
  topic?: string;
  description?: string;
  breakdown?: string;
  error?: string;
}

export interface ScoreResponse {
  success: boolean;
  document_id?: string;
  filename?: string;
  score?: number;
  explanation?: string;
  error?: string;
}
