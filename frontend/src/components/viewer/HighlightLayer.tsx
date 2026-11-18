"use client";

import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/hooks";
import { boxToRect } from "@/lib/pdf/geometry";
import type { Box } from "@/lib/types";

/** Highlighter boxes over a rendered page. After each render the first box is scrolled into view. */
export function HighlightLayer({ boxes, scale, renderTick }: { boxes: Box[]; scale: number; renderTick: number }) {
  const first = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (renderTick === 0) return;
    first.current?.scrollIntoView({
      block: "center",
      inline: "center",
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
  }, [renderTick]);

  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden>
      {boxes.map((box, i) => {
        const rect = boxToRect(box, scale);
        return (
          <div
            key={`${box.page}-${i}`}
            ref={i === 0 ? first : undefined}
            className="pdf-highlight"
            style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
          />
        );
      })}
    </div>
  );
}
