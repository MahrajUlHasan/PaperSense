"use client";

import { figureUrl } from "@/lib/api";
import { citationPlace } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { useSettings } from "@/stores/settings";

/** The answer's sources, numbered like the chips. The backend has already removed duplicates. */
export function SourcesFooter({ citations, onOpen }: { citations: Citation[]; onOpen: (citation: Citation) => void }) {
  const workspaceId = useSettings((s) => s.workspaceId);
  const unique = citations.filter((c, i) => citations.findIndex((x) => x.index === c.index) === i);

  return (
    <section aria-label="Sources" className="border-t pt-3">
      <ol className="space-y-1">
        {unique.map((c) => (
          <li key={c.index}>
            <button
              type="button"
              data-citation-chip
              onClick={() => onOpen(c)}
              className="hover:bg-secondary flex w-full items-start gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
            >
              <span className="cite-chip mt-0.5 shrink-0" aria-hidden>
                {c.index}
              </span>
              {c.figure_index ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={figureUrl(c.document_id, c.figure_index, workspaceId)}
                  alt=""
                  className="h-12 w-16 shrink-0 rounded border bg-white object-contain"
                />
              ) : null}
              <span className="min-w-0">
                <span className="block truncate font-medium">{c.filename}</span>
                <span className="text-muted-foreground block truncate text-xs">{citationPlace(c)}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
