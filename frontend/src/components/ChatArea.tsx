"use client";

import React, { useRef, useEffect, useState, useMemo, Fragment } from "react";
import { Send, Loader2, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, Citation, Source } from "@/types";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (q: string) => void;
  onCitationClick: (c: Citation) => void;
  sources: Source[];
  isEmpty: boolean;
}

/* ── Citation injection ───────────────────────────────────────── */

function injectCitations(
  text: string,
  citations: Citation[] | undefined,
  onClick: (c: Citation) => void
) {
  if (!citations?.length) return <>{text}</>;
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/);
        if (m) {
          const cit = citations.find((c) => c.index === parseInt(m[1], 10));
          if (cit) {
            return (
              <button
                key={i}
                onClick={() => onClick(cit)}
                className="badge badge-sm badge-primary mx-0.5 cursor-pointer hover:badge-secondary"
                title={`${cit.filename || cit.section}${cit.page ? ` p.${cit.page}` : ""} (${(cit.score * 100).toFixed(0)}%)`}
              >
                {p}
              </button>
            );
          }
        }
        return <Fragment key={i}>{p}</Fragment>;
      })}
    </>
  );
}

function walk(
  children: React.ReactNode,
  citations: Citation[] | undefined,
  onClick: (c: Citation) => void
): React.ReactNode {
  return React.Children.map(children, (child) =>
    typeof child === "string" ? injectCitations(child, citations, onClick) : child
  );
}

/* ── Markdown renderer ────────────────────────────────────────── */

function Md({
  content, citations, onClick,
}: {
  content: string; citations?: Citation[]; onClick: (c: Citation) => void;
}) {
  const comp = useMemo(() => ({
    p: ({ children, ...ps }: any) => <p className="mb-2 last:mb-0 leading-relaxed" {...ps}>{walk(children, citations, onClick)}</p>,
    li: ({ children, ...ps }: any) => <li className="ml-1" {...ps}>{walk(children, citations, onClick)}</li>,
    strong: ({ children, ...ps }: any) => <strong className="font-bold" {...ps}>{walk(children, citations, onClick)}</strong>,
    em: ({ children, ...ps }: any) => <em {...ps}>{walk(children, citations, onClick)}</em>,
    h1: ({ children }: any) => <h3 className="text-base font-bold mt-3 mb-1">{children}</h3>,
    h2: ({ children }: any) => <h4 className="text-sm font-bold mt-2 mb-1">{children}</h4>,
    h3: ({ children }: any) => <h5 className="text-sm font-semibold mt-2 mb-1">{children}</h5>,
    ul: ({ children }: any) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
    ol: ({ children }: any) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
    table: ({ children }: any) => (
      <div className="overflow-x-auto mb-2"><table className="table table-xs">{children}</table></div>
    ),
    blockquote: ({ children }: any) => (
      <blockquote className="border-l-4 border-primary/40 pl-3 italic opacity-80 mb-2">{children}</blockquote>
    ),
    code: ({ children, className }: any) => {
      const block = className?.includes("language-");
      return block
        ? <pre className="mockup-code text-xs mb-2 p-3 overflow-x-auto"><code>{children}</code></pre>
        : <code className="badge badge-ghost text-xs">{children}</code>;
    },
    hr: () => <div className="divider my-1" />,
  }), [citations, onClick]);

  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={comp}>{content}</ReactMarkdown>;
}

/* ── ChatArea component ───────────────────────────────────────── */

export default function ChatArea({ messages, isLoading, onSend, onCitationClick, sources, isEmpty }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasReady = sources.some((s) => s.status === "ready");

//   useEffect(() => {
//     bottomRef.current?.scroll({ behavior: "smooth" });
//   }, [messages, isLoading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isLoading) return;
    onSend(q);
    setInput("");
  };

  /* Empty state — centered input */
  if (isEmpty) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-6 px-4">
        <MessageSquare size={56} className="opacity-20" />
        <h2 className="text-2xl font-bold opacity-70">PaperSense</h2>
        <p className="text-sm opacity-50 text-center max-w-md">
          Upload research papers on the left, optionally set your research context on the right, then ask questions below.
        </p>
        <form onSubmit={submit} className="join w-full max-w-xl">
          <input
            type="text" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder={hasReady ? "Ask about your papers…" : "Upload a PDF first…"}
            disabled={!hasReady} className="input input-bordered join-item flex-1"
          />
          <button type="submit" disabled={!input.trim() || isLoading || !hasReady} className="btn btn-primary join-item">
            <Send size={18} />
          </button>
        </form>
      </div>
    );
  }

  /* Chat view */
  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div key={msg.id} className={`chat ${isUser ? "chat-end" : "chat-start"}`}>
              <div className={`chat-bubble ${isUser ? "chat-bubble-primary" : "chat-bubble-neutral"} max-w-[75%]`}>
                {isUser ? (
                  <Md content={msg.content} onClick={onCitationClick} />
                ) : (
                  <Md content={msg.content} citations={msg.citations} onClick={onCitationClick} />
                )}
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="chat chat-start">
            <div className="chat-bubble chat-bubble-neutral flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" /> Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={submit} className="border-t border-base-300 p-3 flex gap-2">
        <input
          type="text" value={input} onChange={(e) => setInput(e.target.value)}
          placeholder={hasReady ? "Ask about your papers…" : "Upload a PDF first…"}
          disabled={!hasReady || isLoading}
          className="input input-bordered flex-1 input-sm"
        />
        <button type="submit" disabled={!input.trim() || isLoading || !hasReady} className="btn btn-primary btn-sm">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
