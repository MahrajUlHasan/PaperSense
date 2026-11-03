import { create } from "zustand";
import { api } from "@/lib/api";
import type { ProvidersResponse } from "@/lib/types";

export type SettingsTab = "keys" | "guide";
export type MobilePanel = "library" | "research" | null;

interface UiState {
  settingsOpen: boolean;
  settingsTab: SettingsTab;
  providers: ProvidersResponse | null;
  analysisDocumentId: string | null;
  mobilePanel: MobilePanel;
  openSettings: (tab?: SettingsTab) => void;
  setSettingsOpen: (open: boolean) => void;
  setSettingsTab: (tab: SettingsTab) => void;
  loadProviders: () => Promise<void>;
  showAnalysis: (documentId: string | null) => void;
  setMobilePanel: (panel: MobilePanel) => void;
}

export const useUi = create<UiState>()((set) => ({
  settingsOpen: false,
  settingsTab: "keys",
  providers: null,
  analysisDocumentId: null,
  mobilePanel: null,
  openSettings: (tab = "keys") => set({ settingsOpen: true, settingsTab: tab }),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  setSettingsTab: (settingsTab) => set({ settingsTab }),
  loadProviders: async () => set({ providers: await api.providers() }),
  showAnalysis: (analysisDocumentId) => set({ analysisDocumentId }),
  setMobilePanel: (mobilePanel) => set({ mobilePanel }),
}));
