"use client";

import { Markdown } from "@/components/markdown/Markdown";
import { figureUrl } from "@/lib/api";
import { citationPlace } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { useSettings } from "@/stores/settings";

export function CitationPreview({ citation }: { citation: Citation }) {
  const workspaceId = useSettings((s) => s.workspaceId);
  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm leading-snug font-semibold">{citation.filename}</p>
        <p className="text-muted-foreground text-xs">{citationPlace(citation)}</p>
      </div>
      {citation.figure_index ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={figureUrl(citation.document_id, citation.figure_index, workspaceId)}
          alt={`Figure from ${citation.filename}`}
          className="max-h-40 w-full rounded border bg-white object-contain"
        />
      ) : null}
      <div className="max-h-44 overflow-hidden [mask-image:linear-gradient(to_bottom,black_70%,transparent)]">
        <Markdown className="text-sm leading-relaxed">{citation.text}</Markdown>
      </div>
      <p className="text-muted-foreground text-xs">Click the number to open the PDF at this passage.</p>
    </div>
  );
}
