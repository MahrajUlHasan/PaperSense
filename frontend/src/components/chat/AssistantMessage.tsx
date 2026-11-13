"use client";

import { TriangleAlert } from "lucide-react";
import { CopyButton } from "@/components/common/CopyButton";
import { Markdown } from "@/components/markdown/Markdown";
import { Button } from "@/components/ui/button";
import { formatTime } from "@/lib/format";
import type { ChatMessage, Citation } from "@/lib/types";
import { useChat } from "@/stores/chat";
import { useViewer } from "@/stores/viewer";
import { CitationChip } from "./CitationChip";
import { SourcesFooter } from "./SourcesFooter";

export function AssistantMessage({ message }: { message: ChatMessage }) {
  const show = useViewer((s) => s.show);
  const retry = useChat((s) => s.retry);

  if (message.error) {
    return (
      <div role="alert" className="border-destructive/40 flex items-start gap-3 rounded-md border px-4 py-3 text-sm">
        <TriangleAlert className="text-destructive mt-0.5 size-4 shrink-0" />
        <p className="flex-1">{message.content}</p>
        {message.retryOf && (
          <Button size="sm" variant="outline" onClick={() => void retry(message.id)}>Try again</Button>
        )}
      </div>
    );
  }

  const citations = message.citations ?? [];
  const byIndex = new Map(citations.map((c) => [c.index, c]));
  const open = (citation: Citation) => show(citation, citations);
  const rewritten = message.searchQuery && message.question && message.searchQuery !== message.question;

  return (
    <article className="space-y-3">
      <Markdown
        maxCitation={citations.length || undefined}
        renderCitation={(n) => {
          const citation = byIndex.get(n);
          return citation ? <CitationChip citation={citation} onOpen={() => open(citation)} /> : null;
        }}
      >
        {message.content}
      </Markdown>
      {citations.length > 0 && <SourcesFooter citations={citations} onOpen={open} />}
      <div className="text-muted-foreground flex flex-wrap items-center gap-x-3 text-xs">
        <time dateTime={message.createdAt}>{formatTime(message.createdAt)}</time>
        {rewritten && <span>Searched for: {message.searchQuery}</span>}
        <CopyButton text={message.content} label="Copy answer" />
      </div>
    </article>
  );
}
