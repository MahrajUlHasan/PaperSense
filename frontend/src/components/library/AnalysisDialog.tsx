"use client";

import { useEffect } from "react";
import { Markdown } from "@/components/markdown/Markdown";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { paperTitle } from "@/lib/format";
import { useLibrary } from "@/stores/library";
import { useUi } from "@/stores/ui";

export function AnalysisDialog() {
  const id = useUi((s) => s.analysisDocumentId);
  const showAnalysis = useUi((s) => s.showAnalysis);
  const doc = useLibrary((s) => s.documents.find((d) => d.id === id));
  const analysis = useLibrary((s) => (id ? s.analyses[id] : undefined));
  const analyze = useLibrary((s) => s.analyze);

  useEffect(() => {
    if (id) void analyze(id);
  }, [id, analyze]);

  return (
    <Dialog open={id !== null} onOpenChange={(open) => !open && showAnalysis(null)}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">{doc ? paperTitle(doc) : "Summary"}</DialogTitle>
          <DialogDescription>A summary of the whole paper, written from its text.</DialogDescription>
        </DialogHeader>
        {!analysis ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-4/5" />
            <p className="text-muted-foreground text-sm">Reading the paper…</p>
          </div>
        ) : (
          <div className="space-y-5">
            <section>
              <h3 className="mb-1 font-semibold">Summary</h3>
              <Markdown>{analysis.summary}</Markdown>
            </section>
            <section>
              <h3 className="mb-1 font-semibold">Key findings</h3>
              <Markdown>{analysis.key_findings.map((f) => `- ${f}`).join("\n")}</Markdown>
            </section>
            <section>
              <h3 className="mb-1 font-semibold">Methodology</h3>
              <Markdown>{analysis.methodology}</Markdown>
            </section>
            <section>
              <h3 className="mb-1 font-semibold">Limitations</h3>
              <Markdown>{analysis.limitations.map((l) => `- ${l}`).join("\n")}</Markdown>
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
