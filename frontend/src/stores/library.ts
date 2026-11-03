import { toast } from "sonner";
import { create } from "zustand";
import { api } from "@/lib/api";
import { notifyError } from "@/lib/errors";
import { paperTitle } from "@/lib/format";
import type { AnalysisResponse, DocumentInfo } from "@/lib/types";
import { useUi } from "./ui";

const MAX_BYTES = 50 * 1024 * 1024;
const POLL_MS = 2000;
const PROCESSING: DocumentInfo["status"][] = ["queued", "parsing", "enriching", "embedding"];

export const isProcessing = (doc: DocumentInfo) => PROCESSING.includes(doc.status);

let pollTimer: ReturnType<typeof setTimeout> | null = null;

interface LibraryState {
  documents: DocumentInfo[];
  loaded: boolean;
  /** Names of files that are being sent to the server right now. */
  sending: string[];
  /** Papers the next question is limited to; empty means all papers. */
  scope: string[];
  analyses: Record<string, AnalysisResponse>;
  analyzing: string | null;
  load: () => Promise<void>;
  upload: (files: File[]) => Promise<void>;
  remove: (id: string) => Promise<void>;
  patch: (id: string, changes: Partial<DocumentInfo>) => void;
  toggleScope: (id: string) => void;
  clearScope: () => void;
  analyze: (id: string) => Promise<void>;
}

export const useLibrary = create<LibraryState>()((set, get) => ({
  documents: [],
  loaded: false,
  sending: [],
  scope: [],
  analyses: {},
  analyzing: null,

  /** Loads the library and keeps polling while any paper is still being processed. */
  load: async () => {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = null;
    const before = new Map(get().documents.map((d) => [d.id, d.status]));
    try {
      const documents = await api.listDocuments();
      for (const doc of documents) {
        const was = before.get(doc.id);
        if (!was || !PROCESSING.includes(was)) continue;
        if (doc.status === "ready") toast.success(`${paperTitle(doc)} is ready.`);
        if (doc.status === "error") toast.error(`${doc.filename} couldn't be processed.`, { description: doc.error ?? undefined });
      }
      set((s) => ({
        documents,
        loaded: true,
        scope: s.scope.filter((id) => documents.some((d) => d.id === id && d.status === "ready")),
      }));
      if (documents.some(isProcessing)) pollTimer = setTimeout(() => void get().load(), POLL_MS);
    } catch (error) {
      set({ loaded: true });
      notifyError(error, "Couldn't load your papers.");
    }
  },

  upload: async (files) => {
    for (const file of files) {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error(`${file.name} isn't a PDF.`);
        continue;
      }
      if (file.size > MAX_BYTES) {
        toast.error(`${file.name} is larger than 50 MB.`);
        continue;
      }
      set((s) => ({ sending: [...s.sending, file.name] }));
      try {
        const doc = await api.uploadDocument(file);
        set((s) => ({ documents: [...s.documents.filter((d) => d.id !== doc.id), doc] }));
      } catch (error) {
        notifyError(error, `Couldn't upload ${file.name}.`);
      } finally {
        set((s) => {
          const i = s.sending.indexOf(file.name);
          return { sending: s.sending.filter((_, j) => j !== i) };
        });
      }
    }
    await get().load();
  },

  remove: async (id) => {
    try {
      await api.deleteDocument(id);
      set((s) => ({ documents: s.documents.filter((d) => d.id !== id), scope: s.scope.filter((x) => x !== id) }));
      toast.success("Paper removed.");
    } catch (error) {
      notifyError(error, "Couldn't remove the paper.");
    }
  },

  patch: (id, changes) =>
    set((s) => ({ documents: s.documents.map((d) => (d.id === id ? { ...d, ...changes } : d)) })),

  toggleScope: (id) =>
    set((s) => ({ scope: s.scope.includes(id) ? s.scope.filter((x) => x !== id) : [...s.scope, id] })),

  clearScope: () => set({ scope: [] }),

  /** Whole-paper summary. Kept for the session, because each one costs a request. */
  analyze: async (id) => {
    if (get().analyses[id] || get().analyzing === id) return;
    set({ analyzing: id });
    try {
      const analysis = await api.analyzeDocument(id);
      set((s) => ({ analyses: { ...s.analyses, [id]: analysis } }));
    } catch (error) {
      notifyError(error, "Couldn't summarise this paper.");
      useUi.getState().showAnalysis(null);
    } finally {
      set({ analyzing: null });
    }
  },
}));
