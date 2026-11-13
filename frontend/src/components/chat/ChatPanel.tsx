"use client";

import { LoaderCircle } from "lucide-react";
import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/hooks";
import { useChat } from "@/stores/chat";
import { useLibrary } from "@/stores/library";
import { AssistantMessage } from "./AssistantMessage";
import { Composer } from "./Composer";
import { EmptyState } from "./EmptyState";
import { KeyBanner } from "./KeyBanner";
import { UserMessage } from "./UserMessage";

export function ChatPanel() {
  const messages = useChat((s) => s.messages);
  const pending = useChat((s) => s.pending);
  const hasPapers = useLibrary((s) => s.documents.length > 0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "end" });
  }, [messages.length, pending]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-8">
          {messages.length === 0 ? (
            <EmptyState hasPapers={hasPapers} />
          ) : (
            <ol className="space-y-8" aria-label="Conversation">
              {messages.map((m) => (
                <li key={m.id}>{m.role === "user" ? <UserMessage message={m} /> : <AssistantMessage message={m} />}</li>
              ))}
              {pending && (
                <li className="text-muted-foreground flex items-center gap-2 text-sm" aria-live="polite">
                  <LoaderCircle className="size-4 animate-spin" /> Searching your papers and writing an answer…
                </li>
              )}
            </ol>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <div className="bg-background border-t">
        <div className="mx-auto w-full max-w-3xl px-4 py-3 sm:px-8">
          <KeyBanner />
          <Composer />
        </div>
      </div>
    </div>
  );
}
