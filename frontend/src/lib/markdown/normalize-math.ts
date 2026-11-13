const CODE = /(```[\s\S]*?```|`[^`\n]+`)/g;
const DISPLAY = /\$\$([\s\S]+?)\$\$/g;
const BRACKET_DISPLAY = /\\\[([\s\S]+?)\\\]/g;
const PAREN_INLINE = /\\\(([\s\S]+?)\\\)/g;

const block = (_match: string, body: string) => `\n$$\n${body.trim()}\n$$\n`;

/** Rewrites math delimiters for remark-math. Code spans and code blocks are left alone. */
export function normalizeMath(markdown: string): string {
  return markdown
    .split(CODE)
    .map((part, i) =>
      i % 2 === 1
        ? part
        : part
            .replace(DISPLAY, block)
            .replace(BRACKET_DISPLAY, block)
            .replace(PAREN_INLINE, (_match: string, body: string) => `$${body.trim()}$`),
    )
    .join("");
}
