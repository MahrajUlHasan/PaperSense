"use client";

import { useRef, useState } from "react";
import { useLibrary } from "@/stores/library";

const hasFiles = (e: React.DragEvent) => Array.from(e.dataTransfer.types).includes("Files");

export function UploadDropzone({ children }: { children: React.ReactNode }) {
  const upload = useLibrary((s) => s.upload);
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);

  return (
    <div
      className="relative flex min-h-0 flex-1"
      onDragEnter={(e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        depth.current += 1;
        setDragging(true);
      }}
      onDragOver={(e) => {
        if (hasFiles(e)) e.preventDefault();
      }}
      onDragLeave={() => {
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        depth.current = 0;
        setDragging(false);
        void upload(Array.from(e.dataTransfer.files));
      }}
    >
      {children}
      {dragging && (
        <div className="border-primary bg-background/90 pointer-events-none absolute inset-3 z-30 grid place-items-center rounded-lg border-2 border-dashed">
          <p className="font-serif text-xl font-semibold">Drop PDFs to add them to your library</p>
        </div>
      )}
    </div>
  );
}
