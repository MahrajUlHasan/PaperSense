import { create } from "zustand";
import { createJSONStorage, persist, type StateStorage } from "zustand/middleware";
import type { ProviderId } from "@/lib/types";

/**
 * Keys live in sessionStorage (gone when the tab closes) unless "Remember keys on this
 * device" is on; then they move to localStorage. Never both.
 */
export const keyStorage: StateStorage = {
  getItem: (name) => localStorage.getItem(name) ?? sessionStorage.getItem(name),
  setItem: (name, value) => {
    const remember = Boolean(JSON.parse(value)?.state?.remember);
    (remember ? localStorage : sessionStorage).setItem(name, value);
    (remember ? sessionStorage : localStorage).removeItem(name);
  },
  removeItem: (name) => {
    localStorage.removeItem(name);
    sessionStorage.removeItem(name);
  },
};

interface KeysState {
  keys: Partial<Record<ProviderId, string>>;
  remember: boolean;
  setKey: (provider: ProviderId, key: string) => void;
  setRemember: (remember: boolean) => void;
  forgetAll: () => void;
}

export const useKeys = create<KeysState>()(
  persist(
    (set) => ({
      keys: {},
      remember: false,
      setKey: (provider, key) => set((s) => ({ keys: { ...s.keys, [provider]: key.trim() } })),
      setRemember: (remember) => set({ remember }),
      forgetAll: () => set({ keys: {} }),
    }),
    {
      name: "papersense.keys",
      storage: createJSONStorage(() => keyStorage),
      partialize: (s) => ({ keys: s.keys, remember: s.remember }),
    },
  ),
);
