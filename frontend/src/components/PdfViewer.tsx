"use client";

import React, { useState } from "react";
import { X, FileText, BookOpen, Copy, CheckCircle2 } from "lucide-react";
import type { Citation, Source } from "@/types";

interface Props {
  isOpen: boolean;
  citation: Citation | null;
  source: Source | null;
  onClose: () => void;
}

export default function PdfViewer({ isOpen, citation, source, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  if (!isOpen || !source) return null;

  const page = citation?.page ?? 1;
  const pdfUrl = `${source.blobUrl}#page=${page}&toolbar=1`;

  const handleCopy = () => {
    if (citation?.text) {
      navigator.clipboard.writeText(citation.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="relative ml-auto w-full max-w-4xl bg-base-100 shadow-2xl flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="navbar bg-base-200 min-h-0 px-4 py-2">
          <div className="flex-1 gap-2 min-w-0">
            <FileText size={16} className="shrink-0 opacity-60" />
            <span className="text-sm font-medium truncate">{source.filename}</span>
            {citation && (
              <span className="badge badge-sm badge-outline">Page {page}</span>
            )}
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm btn-circle">
            <X size={16} />
          </button>
        </div>

        {/* Citation context */}
        {citation && (
          <div className="px-4 py-2 bg-primary/5 border-b border-base-300 space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-primary">
              <BookOpen size={14} />
              Citation [{citation.index}] — {citation.section}
              <span className="ml-auto opacity-60">
                {(citation.score * 100).toFixed(0)}% match
              </span>
            </div>

            {citation.text && (
              <div className="relative">
                <div className="bg-base-100 rounded-lg p-2.5 border border-primary/20 text-sm max-h-28 overflow-y-auto leading-relaxed">
                  &ldquo;{citation.text}&rdquo;
                </div>
                <button
                  onClick={handleCopy}
                  className="absolute top-1.5 right-1.5 btn btn-ghost btn-xs btn-circle"
                  title="Copy"
                >
                  {copied ? <CheckCircle2 size={12} className="text-success" /> : <Copy size={12} />}
                </button>
                <p className="text-xs opacity-50 mt-1">
                  Use <kbd className="kbd kbd-xs">Ctrl+F</kbd> in the PDF to find this text.
                </p>
              </div>
            )}
          </div>
        )}

        {/* PDF iframe */}
        <div className="flex-1 min-h-0">
          <iframe src={pdfUrl} className="w-full h-full border-0" title={source.filename} />
        </div>
      </div>
    </div>
  );
}
