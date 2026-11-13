"use client";

import { LoaderCircle, Plus } from "lucide-react";
import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { pickPdfFiles } from "@/lib/hooks";
import { useLibrary } from "@/stores/library";
import { PaperRow } from "./PaperRow";

export function LibraryPanel() {
  const documents = useLibrary((s) => s.documents);
  const loaded = useLibrary((s) => s.loaded);
  const sending = useLibrary((s) => s.sending);
  const scope = useLibrary((s) => s.scope);
  const clearScope = useLibrary((s) => s.clearScope);
  const upload = useLibrary((s) => s.upload);
  const newestFirst = useMemo(() => [...documents].reverse(), [documents]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-3">
        <h2 className="font-serif text-lg font-semibold">Library</h2>
        <Button size="sm" onClick={() => pickPdfFiles((files) => void upload(files))}>
          <Plus /> Add PDFs
        </Button>
      </div>

      {documents.length > 0 && (
        <div className="flex min-h-10 items-center gap-2 border-y px-4 py-1.5 text-sm">
          <Checkbox id="scope-all" checked={scope.length === 0} onCheckedChange={clearScope} />
          <Label htmlFor="scope-all" className="font-normal">All papers</Label>
          {scope.length > 0 && (
            <span className="text-muted-foreground ml-auto flex items-center gap-1">
              {scope.length} selected
              <Button variant="link" size="sm" className="h-auto px-1" onClick={clearScope}>Clear</Button>
            </span>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {!loaded ? (
          <div className="space-y-3 p-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : documents.length === 0 && sending.length === 0 ? (
          <p className="text-muted-foreground px-4 py-6 text-sm">
            No papers yet. Add a PDF and PaperSense reads it, including its tables, figures and formulas.
          </p>
        ) : (
          <ul>
            {sending.map((name, i) => (
              <li key={`${name}-${i}`} className="text-muted-foreground flex items-center gap-2 border-b px-4 py-3 text-sm">
                <LoaderCircle className="size-4 animate-spin" /> Sending {name}
              </li>
            ))}
            {newestFirst.map((doc) => (
              <PaperRow key={doc.id} doc={doc} />
            ))}
          </ul>
        )}
      </div>

      <p className="text-muted-foreground border-t px-4 py-2 text-xs">Drop PDFs anywhere to add them. Up to 50 MB each.</p>
    </div>
  );
}
