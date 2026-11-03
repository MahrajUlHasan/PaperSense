import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "@/lib/api";
import { errorText, notifyError } from "@/lib/errors";
import { newId } from "@/lib/ids";
import type { ChatMessage } from "@/lib/types";
import { useLibrary } from "./library";

const KEEP_MESSAGES = 100;
const now = () => new Date().toISOString();

interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  pending: boolean;
  send: (question: string) => Promise<void>;
  retry: (messageId: string) => Promise<void>;
  newChat: () => Promise<void>;
}

export const useChat = create<ChatState>()(
  persist(
    (set, get) => ({
      sessionId: newId("chat"),
      messages: [],
      pending: false,

      send: async (question) => {
        const text = question.trim();
        if (!text || get().pending) return;
        const add = (message: ChatMessage) =>
          set((s) => ({ messages: [...s.messages, message].slice(-KEEP_MESSAGES) }));
        add({ id: newId("m"), role: "user", content: text, createdAt: now() });
        set({ pending: true });
        try {
          const result = await api.query(text, useLibrary.getState().scope);
          add({
            id: newId("m"),
            role: "assistant",
            content: result.answer,
            createdAt: now(),
            citations: result.citations,
            question: result.question,
            searchQuery: result.search_query,
          });
        } catch (error) {
          notifyError(error, "The question couldn't be answered.");
          add({ id: newId("m"), role: "assistant", content: errorText(error), createdAt: now(), error: true, retryOf: text });
        } finally {
          set({ pending: false });
        }
      },

      /** Removes a failed answer (and the question before it) and asks again. */
      retry: async (messageId) => {
        const messages = get().messages;
        const i = messages.findIndex((m) => m.id === messageId);
        const failed = messages[i];
        if (!failed?.retryOf) return;
        const question = messages[i - 1];
        const dropQuestion = question?.role === "user" && question.content === failed.retryOf;
        set({ messages: messages.filter((_, j) => j !== i && !(dropQuestion && j === i - 1)) });
        await get().send(failed.retryOf);
      },

      newChat: async () => {
        await api.clearSession().catch(() => undefined);
        set({ sessionId: newId("chat"), messages: [] });
      },
    }),
    { name: "papersense.chat", version: 1, partialize: (s) => ({ sessionId: s.sessionId, messages: s.messages }) },
  ),
);
