"use client";

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useState } from "react";
import { CopyButton } from "@/components/common/CopyButton";
import { Markdown } from "@/components/markdown/Markdown";
import { Button } from "@/components/ui/button";
import { citationPlace } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useViewer } from "@/stores/viewer";

export function ViewerHeader({ citation, onClose }: { citation: Citation; onClose: () => void }) {
  const siblings = useViewer((s) => s.siblings);
  const step = useViewer((s) => s.step);
  const [expanded, setExpanded] = useState(false);
  const position = siblings.findIndex((c) => c.index === citation.index);

  return (
    <div className="border-b px-5 pt-4 pb-2">
      <div className="flex items-start gap-3">
        <span className="cite-chip mt-1 shrink-0" aria-hidden>
          {citation.index}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-serif text-base font-semibold">{citation.filename}</h2>
          <p className="text-muted-foreground truncate text-sm">{citationPlace(citation)}</p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close the PDF panel">
          <X />
        </Button>
      </div>
      <div className={cn("mt-3 overflow-hidden", !expanded && "max-h-24 [mask-image:linear-gradient(to_bottom,black_60%,transparent)]")}>
        <Markdown className="text-sm leading-relaxed">{citation.text}</Markdown>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1">
        <Button variant="ghost" size="sm" onClick={() => setExpanded((e) => !e)}>
          {expanded ? "Show less" : "Show the whole passage"}
        </Button>
        <CopyButton text={citation.text} label="Copy passage" />
        {siblings.length > 1 && (
          <div className="ml-auto flex items-center gap-1 text-sm">
            <Button variant="ghost" size="icon" disabled={position <= 0} onClick={() => step(-1)} aria-label="Previous source">
              <ChevronLeft />
            </Button>
            <span className="tabular-nums">
              Source {position + 1} of {siblings.length}
            </span>
            <Button variant="ghost" size="icon" disabled={position >= siblings.length - 1} onClick={() => step(1)} aria-label="Next source">
              <ChevronRight />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
