"use client";

import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { Markdown } from "@/components/markdown/Markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { plural } from "@/lib/format";
import type { ResearchInfo } from "@/lib/types";
import { useLibrary } from "@/stores/library";
import { useResearch } from "@/stores/research";

function BriefForm({ research }: { research: ResearchInfo | null }) {
  const saving = useResearch((s) => s.saving);
  const save = useResearch((s) => s.save);
  const [topic, setTopic] = useState(research?.topic ?? "");
  const [description, setDescription] = useState(research?.description ?? "");

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save(topic, description);
      }}
    >
      <div className="space-y-1.5">
        <Label htmlFor="topic">Topic</Label>
        <Input id="topic" value={topic} maxLength={300} onChange={(e) => setTopic(e.target.value)} placeholder="Attention mechanisms for translation" />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="description">What you need from the papers</Label>
        <Textarea
          id="description"
          rows={5}
          value={description}
          maxLength={5000}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Architectures that replace recurrence, and how they are evaluated."
        />
      </div>
      <Button type="submit" disabled={!topic.trim() || saving}>
        {saving && <LoaderCircle className="animate-spin" />}
        Save brief
      </Button>
    </form>
  );
}

export function ResearchPanel() {
  const research = useResearch((s) => s.research);
  const scoreAll = useResearch((s) => s.scoreAll);
  const busy = useResearch((s) => s.scoring.length > 0);
  const readyCount = useLibrary((s) => s.documents.filter((d) => d.status === "ready").length);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
      <h2 className="font-serif text-lg font-semibold">Research brief</h2>
      <p className="text-muted-foreground mt-1 mb-4 text-sm">
        Describe what you&apos;re looking for. PaperSense breaks it down and can rate each paper against it.
      </p>
      <BriefForm key={research?.updated_at ?? "empty"} research={research} />

      {research?.breakdown && (
        <section className="mt-6">
          <h3 className="mb-2 text-sm font-semibold">How papers are judged</h3>
          <Markdown className="text-[0.95rem]">{research.breakdown}</Markdown>
        </section>
      )}

      {research && readyCount > 0 && (
        <div className="mt-6 border-t pt-4">
          <Button variant="secondary" onClick={() => void scoreAll()} disabled={busy}>
            {busy && <LoaderCircle className="animate-spin" />}
            Score {plural(readyCount, "paper")}
          </Button>
          <p className="text-muted-foreground mt-2 text-xs">Uses one request per paper from your key&apos;s free allowance.</p>
        </div>
      )}
    </div>
  );
}
