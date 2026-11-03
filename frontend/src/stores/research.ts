import { toast } from "sonner";
import { create } from "zustand";
import { api } from "@/lib/api";
import { notifyError } from "@/lib/errors";
import type { ResearchInfo } from "@/lib/types";
import { useLibrary } from "./library";

interface ResearchState {
  research: ResearchInfo | null;
  saving: boolean;
  /** Ids of papers being scored right now. */
  scoring: string[];
  load: () => Promise<void>;
  save: (topic: string, description: string) => Promise<void>;
  score: (documentId: string) => Promise<boolean>;
  scoreAll: () => Promise<void>;
}

export const useResearch = create<ResearchState>()((set, get) => ({
  research: null,
  saving: false,
  scoring: [],

  load: async () => {
    try {
      const research = await api.getResearch();
      set({ research: research.topic ? research : null });
    } catch (error) {
      notifyError(error, "Couldn't load your research brief.");
    }
  },

  save: async (topic, description) => {
    set({ saving: true });
    try {
      set({ research: await api.saveResearch(topic.trim(), description.trim()) });
      toast.success("Research brief saved.");
    } catch (error) {
      notifyError(error, "Couldn't save the research brief.");
    } finally {
      set({ saving: false });
    }
  },

  score: async (documentId) => {
    set((s) => ({ scoring: [...s.scoring, documentId] }));
    try {
      const result = await api.scoreDocument(documentId);
      useLibrary.getState().patch(documentId, { score: result.score, score_explanation: result.explanation });
      return true;
    } catch (error) {
      notifyError(error, "Couldn't score this paper.");
      return false;
    } finally {
      set((s) => ({ scoring: s.scoring.filter((id) => id !== documentId) }));
    }
  },

  /** Scores every ready paper, one at a time, and stops at the first failure (usually the free limit). */
  scoreAll: async () => {
    const ready = useLibrary.getState().documents.filter((d) => d.status === "ready");
    for (const doc of ready) {
      if (!(await get().score(doc.id))) break;
    }
  },
}));
