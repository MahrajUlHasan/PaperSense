"use client";

import { ArrowUp } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { paperTitle } from "@/lib/format";
import { useChat } from "@/stores/chat";
import { useLibrary } from "@/stores/library";

const MAX_HEIGHT = 200;

function ScopeLine() {
  const scope = useLibrary((s) => s.scope);
  const documents = useLibrary((s) => s.documents);
  const clearScope = useLibrary((s) => s.clearScope);
  const names = useMemo(
    () => documents.filter((d) => scope.includes(d.id)).map(paperTitle),
    [documents, scope],
  );

  return (
    <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 text-xs">
      <span className="min-w-0 truncate">
        {names.length === 0 ? "Asking about all papers" : `Asking about ${names.join(", ")}`}
        {names.length > 0 && (
          <button type="button" className="ml-2 underline underline-offset-2" onClick={clearScope}>
            Ask about all papers
          </button>
        )}
      </span>
      <span className="hidden sm:inline">Enter sends, Shift+Enter starts a new line</span>
    </div>
  );
}

export function Composer() {
  const send = useChat((s) => s.send);
  const pending = useChat((s) => s.pending);
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const resize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  };

  const submit = () => {
    if (!text.trim() || pending) return;
    void send(text);
    setText("");
    requestAnimationFrame(resize);
  };

  return (
    <form
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="bg-card focus-within:ring-ring/40 flex items-end gap-2 rounded-lg border p-2 focus-within:ring-2">
        <Textarea
          ref={ref}
          rows={1}
          value={text}
          aria-label="Question"
          placeholder="Ask about your papers"
          onChange={(e) => {
            setText(e.target.value);
            resize();
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          className="max-h-[200px] min-h-0 resize-none border-0 bg-transparent p-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <Button type="submit" size="icon" disabled={!text.trim() || pending} aria-label="Send question">
          <ArrowUp />
        </Button>
      </div>
      <ScopeLine />
    </form>
  );
}
