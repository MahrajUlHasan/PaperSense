"use client";

import React, { useRef } from "react";
import {
  Plus, FileText, Trash2, Loader2, AlertCircle, CheckCircle2,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import type { Source } from "@/types";

interface Props {
  sources: Source[];
  collapsed: boolean;
  onToggle: () => void;
  onAdd: (files: FileList) => void;
  onDelete: (id: string) => void;
  onSelect: (src: Source) => void;
  selectedId?: string;
}

function badge(status: Source["status"]) {
  switch (status) {
    case "uploading":
    case "processing":
    case "scoring":
      return (
        <span className="badge badge-sm badge-warning gap-1">
          <Loader2 size={10} className="animate-spin" />
          {status === "scoring" ? "Scoring…" : status === "processing" ? "Processing…" : "Uploading…"}
        </span>
      );
    case "ready":
      return (
        <span className="badge badge-sm badge-success gap-1">
          <CheckCircle2 size={10} /> Ready
        </span>
      );
    case "error":
      return (
        <span className="badge badge-sm badge-error gap-1">
          <AlertCircle size={10} /> Error
        </span>
      );
  }
}

export default function SourcesSidebar({
  sources, collapsed, onToggle, onAdd, onDelete, onSelect, selectedId,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div
      className={`h-full flex flex-col bg-base-200 border-r border-base-300 transition-all duration-200
        ${collapsed ? "w-12" : "w-72"}`}
    >
      {/* Toggle */}
      <button
        onClick={onToggle}
        className="btn btn-ghost btn-sm self-end m-1"
        aria-label="Toggle sources"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>

      {collapsed ? (
        <div className="flex flex-col items-center gap-3 mt-4">
          <button onClick={() => fileRef.current?.click()} className="btn btn-circle btn-sm btn-primary">
            <Plus size={14} />
          </button>
          {sources.map((s) => (
            <div key={s.documentId} className="tooltip tooltip-right" data-tip={s.filename}>
              <button
                onClick={() => s.status === "ready" && onSelect(s)}
                className={`btn btn-circle btn-sm ${s.documentId === selectedId ? "btn-primary" : "btn-ghost"}`}
              >
                <FileText size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="px-3 pb-2">
            <h2 className="font-bold text-sm mb-2">Sources</h2>
            <button
              onClick={() => fileRef.current?.click()}
              className="btn btn-primary btn-sm w-full gap-1"
            >
              <Plus size={14} /> Add PDF
            </button>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto px-2 space-y-1">
            {sources.length === 0 && (
              <p className="text-xs text-base-content/50 text-center mt-6 px-2">
                No sources yet. Upload a PDF to get started.
              </p>
            )}
            {sources.map((s) => (
              <div
                key={s.documentId}
                onClick={() => s.status === "ready" && onSelect(s)}
                className={`group flex items-start gap-2 p-2 rounded-lg cursor-pointer transition
                  ${s.documentId === selectedId ? "bg-primary/10" : "hover:bg-base-300"}`}
              >
                <FileText size={16} className="mt-0.5 shrink-0 opacity-60" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{s.filename}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {badge(s.status)}
                    {s.score !== undefined && (
                      <span className={`badge badge-sm ${s.score >= 70 ? "badge-success" : s.score >= 40 ? "badge-warning" : "badge-error"}`}>
                        {s.score}/100
                      </span>
                    )}
                  </div>
                  {s.error && <p className="text-xs text-error mt-1 truncate">{s.error}</p>}
                </div>
                {s.status === "ready" && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete(s.documentId); }}
                    className="btn btn-ghost btn-xs opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      <input
        ref={fileRef} type="file" accept=".pdf" multiple className="hidden"
        onChange={(e) => e.target.files && onAdd(e.target.files)}
      />
    </div>
  );
}
