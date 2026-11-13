"use client";

import { Ellipsis, FileText, LoaderCircle, TriangleAlert } from "lucide-react";
import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { paperFacts, paperTitle } from "@/lib/format";
import type { DocumentInfo } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isProcessing, useLibrary } from "@/stores/library";
import { useResearch } from "@/stores/research";
import { useUi } from "@/stores/ui";

function ScoreBadge({ score, explanation }: { score: number; explanation: string | null }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Relevance ${score} of 100`}
          className={cn(
            "min-w-9 rounded-sm px-1.5 py-0.5 text-sm font-bold tabular-nums",
            score >= 70 && "bg-highlight text-highlight-foreground",
            score >= 40 && score < 70 && "border-foreground/40 border",
            score < 40 && "text-muted-foreground",
          )}
        >
          {score}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 text-sm">
        <p className="font-semibold">Relevance to your brief: {score} of 100</p>
        {explanation && <p className="text-muted-foreground mt-2 leading-relaxed">{explanation}</p>}
      </PopoverContent>
    </Popover>
  );
}

function PaperStatus({ doc }: { doc: DocumentInfo }) {
  const scoring = useResearch((s) => s.scoring.includes(doc.id));
  if (isProcessing(doc)) {
    return (
      <p className="text-muted-foreground mt-1.5 flex items-center gap-1.5 text-xs">
        <LoaderCircle className="size-3.5 animate-spin" /> {doc.progress ?? "Waiting to start"}
      </p>
    );
  }
  if (doc.status === "error") {
    return (
      <p className="text-destructive mt-1.5 text-xs">
        <TriangleAlert className="mr-1 inline size-3.5" />
        Couldn&apos;t process this paper. {doc.error}
      </p>
    );
  }
  const s = doc.stats;
  const lowPages = s?.low_coverage_pages ?? [];
  return (
    <div className="text-muted-foreground mt-1.5 space-y-0.5 text-xs">
      <p>{paperFacts(doc)}</p>
      {doc.mode === "basic" && <p>Figures weren&apos;t described (no Gemini key when it was added).</p>}
      {lowPages.length > 0 && <p>Some text may be missing on page {lowPages.join(", ")}.</p>}
      {scoring && (
        <p className="flex items-center gap-1.5">
          <LoaderCircle className="size-3.5 animate-spin" /> Scoring against your brief
        </p>
      )}
    </div>
  );
}

export function PaperRow({ doc }: { doc: DocumentInfo }) {
  const inScope = useLibrary((s) => s.scope.includes(doc.id));
  const toggleScope = useLibrary((s) => s.toggleScope);
  const remove = useLibrary((s) => s.remove);
  const score = useResearch((s) => s.score);
  const hasBrief = useResearch((s) => Boolean(s.research?.topic));
  const showAnalysis = useUi((s) => s.showAnalysis);
  const [confirming, setConfirming] = useState(false);
  const ready = doc.status === "ready";
  const title = paperTitle(doc);

  return (
    <li className="flex gap-3 border-b px-4 py-3">
      <Checkbox
        checked={inScope}
        disabled={!ready}
        onCheckedChange={() => toggleScope(doc.id)}
        aria-label={`Ask only about ${title}`}
        className="mt-1"
      />
      <div className="min-w-0 flex-1">
        <p className="font-serif leading-snug font-semibold">{title}</p>
        <p className="text-muted-foreground mt-0.5 flex items-center gap-1 truncate text-xs">
          <FileText className="size-3.5 shrink-0" /> {doc.filename}
        </p>
        <PaperStatus doc={doc} />
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-7" aria-label={`Actions for ${title}`}>
              <Ellipsis />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled={!ready} onSelect={() => showAnalysis(doc.id)}>
              Summarise paper
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!ready || !hasBrief} onSelect={() => void score(doc.id)}>
              Score against brief
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={() => setConfirming(true)}>
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        {doc.score !== null && <ScoreBadge score={doc.score} explanation={doc.score_explanation} />}
      </div>

      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {title}?</AlertDialogTitle>
            <AlertDialogDescription>
              Its PDF, figures and search index are deleted from the server. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction onClick={() => void remove(doc.id)}>Remove</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </li>
  );
}
