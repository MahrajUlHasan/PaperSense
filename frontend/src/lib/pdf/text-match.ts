const normalize = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();

/**
 * For passages without boxes: a test for pdf.js text items. An item matches when its normalised
 * text (at least 12 characters, so short words don't light up everywhere) occurs in the passage.
 */
export function snippetMatcher(passage: string): (text: string) => boolean {
  const target = normalize(passage);
  return (text) => {
    const item = normalize(text);
    return item.length >= 12 && target.includes(item);
  };
}

export function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
