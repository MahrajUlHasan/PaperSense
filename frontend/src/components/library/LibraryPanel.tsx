"use client";

import { paperTitle } from "@/lib/format";
import { useLibrary } from "@/stores/library";

export function LibraryPanel() {
  const documents = useLibrary((s) => s.documents);
  return (
    <div className="p-4">
      <h2 className="font-serif font-semibold">Library</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {documents.map((d) => (
          <li key={d.id}>{paperTitle(d)} ({d.status})</li>
        ))}
      </ul>
    </div>
  );
}
