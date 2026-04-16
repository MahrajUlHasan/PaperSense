"use client";

import React, { useState, useCallback } from "react";
import SourcesSidebar from "@/components/SourcesSidebar";
import ResearchPanel from "@/components/ResearchPanel";
import ChatArea from "@/components/ChatArea";
import PdfViewer from "@/components/PdfViewer";
import {
  uploadDocument, queryDocuments, deleteDocument,
  setResearch, scoreDocument,
} from "@/lib/api";
import type { Source, ChatMessage, Citation, ResearchData } from "@/types";

export default function Home() {
  /* Sources */
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>();

  /* Chat */
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);

  /* Research */
  const [research, setResearchState] = useState<ResearchData>({ topic: "", description: "" });
  const [isSavingResearch, setIsSavingResearch] = useState(false);

  /* Sidebar collapse */
  const [srcCollapsed, setSrcCollapsed] = useState(false);
  const [resCollapsed, setResCollapsed] = useState(false);

  /* PDF viewer */
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerCitation, setViewerCitation] = useState<Citation | null>(null);
  const [viewerSource, setViewerSource] = useState<Source | null>(null);

  /* ── Sources ─────────────────────────────────────────────────── */
  const handleAddSource = useCallback(async (files: FileList) => {
    for (const file of Array.from(files)) {
      const tempId = crypto.randomUUID();
      const blobUrl = URL.createObjectURL(file);
      const src: Source = { documentId: tempId, filename: file.name, status: "uploading", file, blobUrl };
      setSources((p) => [...p, src]);

      try {
        setSources((p) => p.map((s) => (s.documentId === tempId ? { ...s, status: "processing" } : s)));
        const res = await uploadDocument(file);
        if (res.success && res.document_id) {
          const docId = res.document_id;
          setSources((p) => p.map((s) => (s.documentId === tempId ? { ...s, documentId: docId, status: "ready" } : s)));

          // Auto-score if research topic exists
          if (research.topic) {
            setSources((p) => p.map((s) => (s.documentId === docId ? { ...s, status: "scoring" } : s)));
            const sr = await scoreDocument(docId);
            setSources((p) => p.map((s) =>
              s.documentId === docId
                ? { ...s, status: "ready", score: sr.score, scoreExplanation: sr.explanation }
                : s
            ));
          }
        } else {
          setSources((p) => p.map((s) => (s.documentId === tempId ? { ...s, status: "error", error: res.error } : s)));
        }
      } catch (err) {
        setSources((p) => p.map((s) => (s.documentId === tempId ? { ...s, status: "error", error: String(err) } : s)));
      }
    }
  }, [research.topic]);

  const handleDelete = useCallback(async (id: string) => {
    try { await deleteDocument(id); } catch {}
    setSources((p) => { p.find((s) => s.documentId === id && URL.revokeObjectURL(s.blobUrl)); return p.filter((s) => s.documentId !== id); });
    if (selectedSourceId === id) setSelectedSourceId(undefined);
  }, [selectedSourceId]);

  /* ── Research ────────────────────────────────────────────────── */
  const handleSaveResearch = useCallback(async (topic: string, description: string) => {
    setIsSavingResearch(true);
    try {
      const res = await setResearch(topic, description);
      if (res.success) {
        setResearchState({ topic: res.topic || topic, description: res.description || description, breakdown: res.breakdown });

        // Re-score all ready sources
        const readySources = sources.filter((s) => s.status === "ready");
        for (const s of readySources) {
          setSources((p) => p.map((x) => (x.documentId === s.documentId ? { ...x, status: "scoring" } : x)));
          const sr = await scoreDocument(s.documentId);
          setSources((p) => p.map((x) =>
            x.documentId === s.documentId
              ? { ...x, status: "ready", score: sr.score, scoreExplanation: sr.explanation }
              : x
          ));
        }
      }
    } finally {
      setIsSavingResearch(false);
    }
  }, [sources]);

  /* ── Chat ────────────────────────────────────────────────────── */
  const handleSend = useCallback(async (question: string) => {
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question, timestamp: new Date() };
    setMessages((p) => [...p, userMsg]);
    setIsQuerying(true);
    try {
      const res = await queryDocuments(question, selectedSourceId);
      setMessages((p) => [...p, {
        id: crypto.randomUUID(), role: "assistant",
        content: res.answer || res.error || "No response",
        citations: res.citations, sources: res.sources, timestamp: new Date(),
      }]);
    } catch (err) {
      setMessages((p) => [...p, { id: crypto.randomUUID(), role: "assistant", content: `Error: ${err}`, timestamp: new Date() }]);
    } finally { setIsQuerying(false); }
  }, [selectedSourceId]);

  /* ── Citations → PDF ─────────────────────────────────────────── */
  const handleCitation = useCallback((cit: Citation) => {
    // Primary match: by document_id
    let src = sources.find((s) => s.documentId === cit.document_id);
    // Fallback: match by filename (covers id-format mismatches)
    if (!src && cit.filename) {
      src = sources.find((s) => s.filename === cit.filename);
    }
    if (src) {
      setViewerCitation(cit);
      setViewerSource(src);
      setViewerOpen(true);
    } else {
      console.warn("[PaperSense] Citation source not found:", cit);
    }
  }, [sources]);

  /* ── Render ──────────────────────────────────────────────────── */
  return (
    <div className="flex h-screen bg-base-100">
      <SourcesSidebar
        sources={sources} collapsed={srcCollapsed} onToggle={() => setSrcCollapsed(!srcCollapsed)}
        onAdd={handleAddSource} onDelete={handleDelete}
        onSelect={(s) => setSelectedSourceId(s.documentId)} selectedId={selectedSourceId}
      />
      <ChatArea
        messages={messages} isLoading={isQuerying} onSend={handleSend}
        onCitationClick={handleCitation} sources={sources} isEmpty={messages.length === 0}
      />
      <ResearchPanel
        collapsed={resCollapsed} onToggle={() => setResCollapsed(!resCollapsed)}
        research={research} onSave={handleSaveResearch} isSaving={isSavingResearch}
      />
      <PdfViewer
        isOpen={viewerOpen} citation={viewerCitation} source={viewerSource}
        onClose={() => setViewerOpen(false)}
      />
    </div>
  );
}
