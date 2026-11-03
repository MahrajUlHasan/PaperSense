import { create } from "zustand";
import type { Citation } from "@/lib/types";

interface ViewerState {
  open: boolean;
  citation: Citation | null;
  /** All citations of the same answer, for "previous / next source". */
  siblings: Citation[];
  show: (citation: Citation, siblings: Citation[]) => void;
  close: () => void;
  step: (delta: number) => void;
}

export const useViewer = create<ViewerState>()((set) => ({
  open: false,
  citation: null,
  siblings: [],
  show: (citation, siblings) => set({ open: true, citation, siblings }),
  close: () => set({ open: false }),
  step: (delta) =>
    set((s) => {
      if (!s.citation) return s;
      const i = s.siblings.findIndex((c) => c.index === s.citation?.index);
      const next = s.siblings[i + delta];
      return next ? { citation: next } : s;
    }),
}));
