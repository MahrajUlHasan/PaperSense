"use client";

import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fileUrl } from "@/lib/api";
import { prefersReducedMotion, useElementWidth } from "@/lib/hooks";
import { fitZoomForBox, groupBoxesByPage } from "@/lib/pdf/geometry";
import { escapeHtml, snippetMatcher } from "@/lib/pdf/text-match";
import type { Citation } from "@/lib/types";
import { useSettings } from "@/stores/settings";
import { HighlightLayer } from "./HighlightLayer";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const ZOOMS = [0.75, 1, 1.25, 1.5, 2, 3];
const PAGE_GUTTER = 48;

function PageSkeleton() {
  return <Skeleton className="mx-auto aspect-[3/4] w-full max-w-xl" />;
}

interface PageViewProps {
  citation: Citation;
  numPages: number;
  containerWidth: number;
}

/** One page with its toolbar. It is keyed by citation, so a new citation starts with a fresh view. */
function PageView({ citation, numPages, containerWidth }: PageViewProps) {
  const wholePage = citation.content_type === "page_text";
  const groups = useMemo(() => (wholePage ? [] : groupBoxesByPage(citation.boxes)), [citation.boxes, wholePage]);
  const matcher = useMemo(
    () => (!wholePage && citation.boxes.length === 0 ? snippetMatcher(citation.text) : null),
    [citation, wholePage],
  );
  const [groupIndex, setGroupIndex] = useState(0);
  const [page, setPage] = useState(() => Math.min(groups[0]?.page ?? citation.page ?? 1, numPages));
  const [zoom, setZoom] = useState(1);
  const [pageWidth, setPageWidth] = useState<number | null>(null);
  const [renderTick, setRenderTick] = useState(0);
  const autoZoomed = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const renderWidth = Math.max(200, (containerWidth - PAGE_GUTTER) * zoom);
  const scale = pageWidth ? renderWidth / pageWidth : 1;
  const highlights = groups.find((g) => g.page === page)?.boxes ?? [];

  const goToPage = (n: number) => setPage(Math.min(Math.max(1, n), numPages));
  const goToGroup = (i: number) => {
    setGroupIndex(i);
    setPage(groups[i].page);
  };
  const zoomIn = () => setZoom(ZOOMS.find((z) => z > zoom + 0.001) ?? zoom);
  const zoomOut = () => setZoom([...ZOOMS].reverse().find((z) => z < zoom - 0.001) ?? zoom);

  const onPageLoad = (loaded: { originalWidth: number }) => {
    setPageWidth(loaded.originalWidth);
    if (autoZoomed.current) return;
    autoZoomed.current = true;
    const target = highlights[0];
    if (target && (citation.content_type === "figure" || citation.content_type === "table")) {
      setZoom(fitZoomForBox(target, loaded.originalWidth));
    }
  };

  const onTextLayer = () => {
    if (!matcher) return;
    scrollRef.current
      ?.querySelector("mark.pdf-text-hit")
      ?.scrollIntoView({ block: "center", behavior: prefersReducedMotion() ? "auto" : "smooth" });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b px-3 py-1.5 text-sm">
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => goToPage(page - 1)} disabled={page <= 1} aria-label="Previous page">
            <ChevronLeft />
          </Button>
          <label className="flex items-center gap-1.5">
            <span className="sr-only">Page</span>
            <input
              type="number"
              min={1}
              max={numPages}
              value={page}
              onChange={(e) => goToPage(Number(e.target.value) || 1)}
              className="bg-background w-12 rounded-sm border px-1 py-0.5 text-center tabular-nums"
            />
            <span className="text-muted-foreground">of {numPages}</span>
          </label>
          <Button variant="ghost" size="icon" onClick={() => goToPage(page + 1)} disabled={page >= numPages} aria-label="Next page">
            <ChevronRight />
          </Button>
        </div>

        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={zoomOut} disabled={zoom <= ZOOMS[0]} aria-label="Zoom out">
            <ZoomOut />
          </Button>
          <button type="button" onClick={() => setZoom(1)} className="hover:bg-secondary min-w-16 rounded-sm px-1.5 py-1 tabular-nums">
            {zoom === 1 ? "Fit width" : `${Math.round(zoom * 100)}%`}
          </button>
          <Button variant="ghost" size="icon" onClick={zoomIn} disabled={zoom >= ZOOMS[ZOOMS.length - 1]} aria-label="Zoom in">
            <ZoomIn />
          </Button>
        </div>

        {groups.length > 1 && (
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={() => goToGroup(groupIndex - 1)} disabled={groupIndex <= 0} aria-label="Previous part of the passage">
              <ChevronLeft />
            </Button>
            <span className="tabular-nums">
              Passage on page {groups[groupIndex].page} ({groupIndex + 1} of {groups.length})
            </span>
            <Button variant="ghost" size="icon" onClick={() => goToGroup(groupIndex + 1)} disabled={groupIndex >= groups.length - 1} aria-label="Next part of the passage">
              <ChevronRight />
            </Button>
          </div>
        )}
        {wholePage && <span className="text-muted-foreground ml-auto text-xs">This source is the whole page.</span>}
        {matcher && <span className="text-muted-foreground ml-auto text-xs">The exact position isn&apos;t known; matching lines are marked.</span>}
      </div>

      <div ref={scrollRef} className="bg-muted min-h-0 flex-1 overflow-auto p-6">
        <div className="relative mx-auto w-fit bg-white shadow-sm">
          <Page
            pageNumber={page}
            width={renderWidth}
            onLoadSuccess={onPageLoad}
            onRenderSuccess={() => setRenderTick((t) => t + 1)}
            onRenderTextLayerSuccess={onTextLayer}
            renderAnnotationLayer={false}
            customTextRenderer={
              matcher
                ? ({ str }) => (matcher(str) ? `<mark class="pdf-text-hit">${escapeHtml(str)}</mark>` : escapeHtml(str))
                : undefined
            }
            loading={<PageSkeleton />}
          />
          {pageWidth && <HighlightLayer boxes={highlights} scale={scale} renderTick={renderTick} />}
        </div>
      </div>
    </div>
  );
}

/** Keeps the PDF loaded while the citation changes; only the page view is reset. */
export default function PdfViewer({ citation }: { citation: Citation }) {
  const workspaceId = useSettings((s) => s.workspaceId);
  const url = useMemo(() => fileUrl(citation.document_id, workspaceId), [citation.document_id, workspaceId]);
  const [numPages, setNumPages] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const containerWidth = useElementWidth(containerRef);

  return (
    <div ref={containerRef} className="flex min-h-0 flex-1 flex-col">
      <Document
        file={url}
        onLoadSuccess={(pdf) => setNumPages(pdf.numPages)}
        loading={
          <div className="p-6">
            <PageSkeleton />
          </div>
        }
        error={
          <p className="p-6 text-sm">
            The PDF couldn&apos;t be loaded. Check that the backend is running and the paper is still in your library.
          </p>
        }
        className="flex min-h-0 flex-1 flex-col"
      >
        {numPages > 0 && containerWidth > 0 && (
          <PageView
            key={`${citation.document_id}-${citation.index}-${citation.text.length}`}
            citation={citation}
            numPages={numPages}
            containerWidth={containerWidth}
          />
        )}
      </Document>
    </div>
  );
}
