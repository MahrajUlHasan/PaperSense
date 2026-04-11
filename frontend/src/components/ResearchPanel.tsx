"use client";

import React, { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Loader2, FlaskConical } from "lucide-react";
import type { ResearchData } from "@/types";

interface Props {
  collapsed: boolean;
  onToggle: () => void;
  research: ResearchData;
  onSave: (topic: string, description: string) => Promise<void>;
  isSaving: boolean;
}

export default function ResearchPanel({
  collapsed, onToggle, research, onSave, isSaving,
}: Props) {
  const [topic, setTopic] = useState(research.topic);
  const [desc, setDesc] = useState(research.description);
  const dirty = topic !== research.topic || desc !== research.description;

  useEffect(() => {
    setTopic(research.topic);
    setDesc(research.description);
  }, [research.topic, research.description]);

  const handleSave = () => {
    if (!topic.trim()) return;
    onSave(topic.trim(), desc.trim());
  };

  return (
    <div
      className={`h-full flex flex-col bg-base-200 border-l border-base-300 transition-all duration-200
        ${collapsed ? "w-12" : "w-80"}`}
    >
      {/* Toggle */}
      <button
        onClick={onToggle}
        className="btn btn-ghost btn-sm self-start m-1"
        aria-label="Toggle research"
      >
        {collapsed ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>

      {collapsed ? (
        <div className="flex flex-col items-center mt-4">
          <div className="tooltip tooltip-left" data-tip="Research topic">
            <button onClick={onToggle} className="btn btn-circle btn-sm btn-ghost">
              <FlaskConical size={16} />
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col px-3 pb-3 overflow-y-auto">
          <h2 className="font-bold text-sm mb-3 flex items-center gap-1.5">
            <FlaskConical size={14} /> Research Context
          </h2>

          {/* Topic */}
          <label className="label text-xs font-semibold">Topic</label>
          <input
            type="text"
            placeholder="e.g. Federated Learning in IoT"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="input input-bordered input-sm w-full"
          />

          {/* Description */}
          <label className="label text-xs font-semibold mt-2">Description</label>
          <textarea
            placeholder="Describe your research goals, methodology, key questions…"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className="textarea textarea-bordered text-sm w-full flex-1 min-h-32 resize-none"
          />

          {/* Save */}
          <button
            onClick={handleSave}
            disabled={!topic.trim() || isSaving || !dirty}
            className="btn btn-primary btn-sm mt-3 w-full gap-1"
          >
            {isSaving ? <Loader2 size={14} className="animate-spin" /> : null}
            {isSaving ? "Saving…" : "Save Research"}
          </button>

          {/* Breakdown preview */}
          {research.breakdown && (
            <div className="mt-3">
              <div className="collapse collapse-arrow bg-base-300 rounded-lg">
                <input type="checkbox" />
                <div className="collapse-title text-xs font-semibold py-2 min-h-0">
                  Research Breakdown
                </div>
                <div className="collapse-content text-xs leading-relaxed opacity-80 max-h-48 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{research.breakdown}</pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
