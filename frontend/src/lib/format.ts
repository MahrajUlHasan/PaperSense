import type { Citation, DocumentInfo } from "./types";

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function paperTitle(doc: DocumentInfo): string {
  return doc.stats?.title?.trim() || doc.filename.replace(/\.pdf$/i, "");
}

/** "15 pages, 6 figures, 4 tables, 5 formulas" */
export function paperFacts(doc: DocumentInfo): string {
  const s = doc.stats;
  const parts: string[] = [];
  if (doc.page_count) parts.push(plural(doc.page_count, "page"));
  if (s?.figures) parts.push(plural(s.figures, "figure"));
  if (s?.tables) parts.push(plural(s.tables, "table"));
  if (s?.formulas) parts.push(plural(s.formulas, "formula"));
  return parts.join(", ");
}

export function pageLabel(citation: Citation): string {
  const pages = citation.pages.length ? citation.pages : citation.page ? [citation.page] : [];
  if (!pages.length) return "";
  return pages.length === 1 ? `page ${pages[0]}` : `pages ${pages[0]}–${pages[pages.length - 1]}`;
}

/** "5.3 Optimizer, page 7"; figures and tables without a section say what they are. */
export function citationPlace(citation: Citation): string {
  const kind = citation.content_type === "figure" ? "Figure" : citation.content_type === "table" ? "Table" : "";
  return [citation.section || kind, pageLabel(citation)].filter(Boolean).join(", ");
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
