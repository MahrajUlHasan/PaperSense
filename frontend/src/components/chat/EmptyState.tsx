"use client";

import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { pickPdfFiles } from "@/lib/hooks";
import { useChat } from "@/stores/chat";
import { useLibrary } from "@/stores/library";

const SUGGESTIONS = [
  "What is the main contribution of this paper?",
  "Which datasets and evaluation metrics are used?",
  "What limitations do the authors mention?",
];

export function EmptyState({ hasPapers }: { hasPapers: boolean }) {
  const upload = useLibrary((s) => s.upload);
  const send = useChat((s) => s.send);

  if (!hasPapers) {
    return (
      <div className="mx-auto max-w-lg py-16">
        <p className="answer-prose text-muted-foreground">
          <span className="relative">
            Every answer points to the passage it came from.
            <span className="pdf-highlight" style={{ inset: "-1px -3px" }} />
          </span>
          <span className="cite-chip" aria-hidden>1</span>
        </p>
        <h1 className="mt-8 font-serif text-2xl font-semibold">Start with a paper</h1>
        <p className="text-muted-foreground mt-2">
          Add a PDF and ask anything about it. PaperSense reads the text, tables, figures and formulas, and every answer
          opens the PDF at the exact passage.
        </p>
        <Button className="mt-6" onClick={() => pickPdfFiles((files) => void upload(files))}>
          <Upload /> Add PDFs
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg py-16">
      <h1 className="font-serif text-2xl font-semibold">Ask about your papers</h1>
      <p className="text-muted-foreground mt-2">Answers cite their sources. Click a number to open the PDF at that passage.</p>
      <ul className="mt-6 space-y-1">
        {SUGGESTIONS.map((q) => (
          <li key={q}>
            <button
              type="button"
              onClick={() => void send(q)}
              className="hover:bg-secondary w-full rounded-md px-3 py-2 text-left transition-colors"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
