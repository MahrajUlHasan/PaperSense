"use client";

import React, { useRef } from "react";
import { Plus, FileText, Trash2, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Source } from "@/types";

interface SidebarProps {
  sources: Source[];
  onAddSource: (files: FileList) => void;
  onDeleteSource: (documentId: string) => void;
  onSelectSource: (source: Source) => void;
  selectedSourceId?: string;
}

const statusConfig = {
  uploading: { icon: Loader2, color: "text-yellow-400", label: "Uploading…", spin: true },
  processing: { icon: Loader2, color: "text-blue-400", label: "Processing…", spin: true },
  scoring: { icon: Loader2, color: "text-purple-400", label: "Scoring...", spin: true },
  ready: { icon: CheckCircle2, color: "text-green-400", label: "Ready", spin: false },
  error: { icon: AlertCircle, color: "text-red-400", label: "Error", spin: false },
};

export default function Sidebar({
  sources,
  onAddSource,
  onDeleteSource,
  onSelectSource,
  selectedSourceId,
}: SidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <aside className="w-72 bg-gray-900 text-gray-100 flex flex-col h-full border-r border-gray-800">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-lg font-bold tracking-tight flex items-center gap-2">
          <span className="text-2xl">🔬</span> PaperSense
        </h1>
      </div>

      {/* Add source */}
      <div className="p-3">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5
                     bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-medium
                     transition-colors"
        >
          <Plus size={18} /> Add Source
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && onAddSource(e.target.files)}
        />
      </div>

      {/* Source list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {sources.length === 0 && (
          <p className="text-gray-500 text-sm text-center mt-8 px-4">
            No sources yet. Upload a PDF to get started.
          </p>
        )}

        {sources.map((src) => {
          const cfg = statusConfig[src.status];
          const Icon = cfg.icon;
          const isSelected = src.documentId === selectedSourceId;

          return (
            <div
              key={src.documentId}
              onClick={() => src.status === "ready" && onSelectSource(src)}
              className={`group flex items-start gap-3 p-3 rounded-lg mb-1 cursor-pointer
                transition-colors ${
                  isSelected
                    ? "bg-gray-700"
                    : "hover:bg-gray-800"
                }`}
            >
              <FileText size={18} className="mt-0.5 text-gray-400 shrink-0" />

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{src.filename}</p>
                <div className={`flex items-center gap-1.5 text-xs mt-1 ${cfg.color}`}>
                  <Icon size={12} className={cfg.spin ? "animate-spin" : ""} />
                  {cfg.label}
                </div>
                {src.error && (

                  <p className="text-xs text-red-400 mt-1 truncate">{src.error}</p>


                )}
              </div>

              {src.status === "ready" && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSource(src.documentId);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400
                             transition-opacity"
                  title="Delete source"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
