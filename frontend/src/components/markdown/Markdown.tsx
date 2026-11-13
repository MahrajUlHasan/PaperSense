"use client";

import ReactMarkdown, { type Components, type Options } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { normalizeMath } from "@/lib/markdown/normalize-math";
import { remarkCitations } from "@/lib/markdown/remark-citations";
import { cn } from "@/lib/utils";

interface MarkdownProps {
  children: string;
  className?: string;
  /** When given, [n] markers become whatever this returns (citation chips). */
  renderCitation?: (n: number) => React.ReactNode;
  maxCitation?: number;
}

const rehypePlugins: Options["rehypePlugins"] = [[rehypeKatex, { throwOnError: false, strict: "ignore" }]];

export function Markdown({ children, className, renderCitation, maxCitation }: MarkdownProps) {
  const remarkPlugins: Options["remarkPlugins"] = renderCitation
    ? [remarkGfm, remarkMath, [remarkCitations, { max: maxCitation }]]
    : [remarkGfm, remarkMath];

  const components: Components = {
    sup: ({ node, ...props }) => {
      void node;
      const n = Number((props as Record<string, unknown>)["data-cite"]);
      if (n && renderCitation) return <>{renderCitation(n)}</>;
      return <sup {...props} />;
    },
    a: ({ node, ...props }) => {
      void node;
      return <a {...props} target="_blank" rel="noreferrer" />;
    },
    table: ({ node, ...props }) => {
      void node;
      return (
        <div className="table-wrap">
          <table {...props} />
        </div>
      );
    },
  };

  return (
    <div className={cn("answer-prose", className)}>
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins} components={components}>
        {normalizeMath(children)}
      </ReactMarkdown>
    </div>
  );
}
