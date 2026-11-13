"use client";

import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import type { Citation } from "@/lib/types";
import { CitationPreview } from "./CitationPreview";

/** The highlighter number in an answer. Hover for a preview; click to open the PDF at the passage. */
export function CitationChip({ citation, onOpen }: { citation: Citation; onOpen: () => void }) {
  return (
    <HoverCard openDelay={150} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          data-citation-chip
          className="cite-chip"
          onClick={onOpen}
          aria-label={`Source ${citation.index}: ${citation.filename}${citation.page ? `, page ${citation.page}` : ""}`}
        >
          {citation.index}
        </button>
      </HoverCardTrigger>
      <HoverCardContent side="top" align="start" className="w-96">
        <CitationPreview citation={citation} />
      </HoverCardContent>
    </HoverCard>
  );
}
