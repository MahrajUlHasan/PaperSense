"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";
import { useSettings } from "@/stores/settings";
import { useViewer } from "@/stores/viewer";
import { SlideOver } from "./SlideOver";
import { ViewerHeader } from "./ViewerHeader";

const PdfViewer = dynamic(() => import("./PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="space-y-3 p-6">
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="aspect-[3/4] w-full" />
    </div>
  ),
});

export function ViewerPanel() {
  const open = useViewer((s) => s.open);
  const citation = useViewer((s) => s.citation);
  const close = useViewer((s) => s.close);
  const width = useSettings((s) => s.viewerWidth);
  const setWidth = useSettings((s) => s.setViewerWidth);

  return (
    <SlideOver open={open} width={width} onWidthChange={setWidth} onClose={close} label="PDF viewer">
      {citation && (
        <>
          <ViewerHeader key={`${citation.document_id}-${citation.index}-${citation.text.length}`} citation={citation} onClose={close} />
          <PdfViewer citation={citation} />
        </>
      )}
    </SlideOver>
  );
}
