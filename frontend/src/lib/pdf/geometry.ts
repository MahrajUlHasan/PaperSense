import type { Box } from "@/lib/types";

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * A box in PDF points (top-left origin, as the backend sends it) → CSS pixels on a page
 * rendered at `scale` pixels per point. `padding` is in points and keeps the mark off the letters.
 */
export function boxToRect(box: Box, scale: number, padding = 2): Rect {
  const left = Math.min(box.l, box.r);
  const right = Math.max(box.l, box.r);
  const top = Math.min(box.t, box.b);
  const bottom = Math.max(box.t, box.b);
  return {
    left: (left - padding) * scale,
    top: (top - padding) * scale,
    width: (right - left + 2 * padding) * scale,
    height: (bottom - top + 2 * padding) * scale,
  };
}

export interface PageBoxes {
  page: number;
  boxes: Box[];
}

/** Boxes grouped per page, pages in order. A passage that runs over two pages gives two groups. */
export function groupBoxesByPage(boxes: Box[]): PageBoxes[] {
  const byPage = new Map<number, Box[]>();
  for (const box of boxes) byPage.set(box.page, [...(byPage.get(box.page) ?? []), box]);
  return [...byPage.entries()].sort(([a], [b]) => a - b).map(([page, list]) => ({ page, boxes: list }));
}

/** Zoom (relative to "fit width") that makes a figure or table about 90% as wide as the panel. */
export function fitZoomForBox(box: Box, pageWidth: number, maxZoom = 3): number {
  const width = Math.abs(box.r - box.l);
  if (width <= 0) return 1;
  return Math.min(maxZoom, Math.max(1, (0.9 * pageWidth) / width));
}
