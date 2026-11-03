import { create } from "zustand";
import { persist } from "zustand/middleware";
import { newId } from "@/lib/ids";
import type { ProviderId } from "@/lib/types";

interface SettingsState {
  /** This browser's library. Made once and kept, so a reload shows the same papers. */
  workspaceId: string;
  provider: ProviderId;
  /** Model per provider; empty means the provider's default. */
  models: Partial<Record<ProviderId, string>>;
  viewerWidth: number;
  libraryOpen: boolean;
  researchOpen: boolean;
  setProvider: (provider: ProviderId) => void;
  setModel: (provider: ProviderId, model: string) => void;
  setViewerWidth: (width: number) => void;
  togglePanel: (panel: "library" | "research") => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      workspaceId: newId("ws"),
      provider: "gemini",
      models: {},
      viewerWidth: 680,
      libraryOpen: true,
      researchOpen: true,
      setProvider: (provider) => set({ provider }),
      setModel: (provider, model) => set((s) => ({ models: { ...s.models, [provider]: model } })),
      setViewerWidth: (viewerWidth) => set({ viewerWidth }),
      togglePanel: (panel) =>
        set((s) => (panel === "library" ? { libraryOpen: !s.libraryOpen } : { researchOpen: !s.researchOpen })),
    }),
    { name: "papersense.settings", version: 1 },
  ),
);
