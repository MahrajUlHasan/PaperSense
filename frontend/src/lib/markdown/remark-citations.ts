import type { PhrasingContent, Root, Text } from "mdast";
import { SKIP, visit } from "unist-util-visit";

const MARKER = /\[(\d+(?:\s*(?:[,;]|[-–])\s*\d+)*)\]/g;
const MAX_RANGE = 20;

/** "1, 3-5" → [1, 3, 4, 5] */
export function parseCitationNumbers(inner: string): number[] {
  const numbers: number[] = [];
  for (const part of inner.split(/\s*[,;]\s*/)) {
    const range = part.match(/^(\d+)\s*[-–]\s*(\d+)$/);
    if (range) {
      const [from, to] = [Number(range[1]), Number(range[2])];
      if (to >= from && to - from < MAX_RANGE) for (let n = from; n <= to; n++) numbers.push(n);
    } else if (/^\d+$/.test(part)) {
      numbers.push(Number(part));
    }
  }
  return numbers;
}

function citationNode(n: number): PhrasingContent {
  const node = {
    type: "text",
    value: `[${n}]`,
    data: { hName: "sup", hProperties: { dataCite: n }, hChildren: [{ type: "text", value: String(n) }] },
  };
  return node as unknown as Text;
}

/**
 * Turns citation markers into <sup data-cite="n"> elements. It works on the Markdown tree,
 * so markers inside math and code are never touched (those aren't text nodes). Repeats right
 * next to each other ("[1][1]") become one, and numbers above `max` are dropped.
 */
export function remarkCitations(options: { max?: number } = {}) {
  return (tree: Root) => {
    visit(tree, "text", (node: Text, index, parent) => {
      if (!parent || index === undefined || parent.type === "link" || parent.type === "linkReference") return;
      const matches = [...node.value.matchAll(MARKER)];
      if (!matches.length) return;

      const pieces: PhrasingContent[] = [];
      let last = 0;
      let previous: number | null = null;
      for (const match of matches) {
        const start = match.index ?? 0;
        const between = node.value.slice(last, start);
        if (between) {
          pieces.push({ type: "text", value: between });
          if (between.trim()) previous = null;
        }
        for (const n of parseCitationNumbers(match[1])) {
          if ((options.max && n > options.max) || n === previous) continue;
          pieces.push(citationNode(n));
          previous = n;
        }
        last = start + match[0].length;
      }
      if (last < node.value.length) pieces.push({ type: "text", value: node.value.slice(last) });

      (parent.children as PhrasingContent[]).splice(index, 1, ...pieces);
      return [SKIP, index + pieces.length];
    });
  };
}
