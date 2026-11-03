"use client";

import { useEffect } from "react";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { AnalysisDialog } from "@/components/library/AnalysisDialog";
import { LibraryPanel } from "@/components/library/LibraryPanel";
import { ResearchPanel } from "@/components/research/ResearchPanel";
import { SettingsDialog } from "@/components/settings/SettingsDialog";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { ViewerPanel } from "@/components/viewer/ViewerPanel";
import { configureApi } from "@/lib/api";
import { useMediaQuery } from "@/lib/hooks";
import { useChat } from "@/stores/chat";
import { useKeys } from "@/stores/keys";
import { useLibrary } from "@/stores/library";
import { useResearch } from "@/stores/research";
import { useSettings } from "@/stores/settings";
import { useUi } from "@/stores/ui";
import { AppHeader } from "./AppHeader";

configureApi(() => {
  const { workspaceId, provider, models } = useSettings.getState();
  const { keys } = useKeys.getState();
  return {
    workspaceId,
    sessionId: useChat.getState().sessionId,
    provider,
    model: models[provider],
    llmKey: keys[provider],
    geminiKey: provider === "gemini" ? undefined : keys.gemini,
  };
});

export default function AppShell() {
  const libraryOpen = useSettings((s) => s.libraryOpen);
  const researchOpen = useSettings((s) => s.researchOpen);
  const mobilePanel = useUi((s) => s.mobilePanel);
  const setMobilePanel = useUi((s) => s.setMobilePanel);
  const isLarge = useMediaQuery("(min-width: 1024px)");
  const isWide = useMediaQuery("(min-width: 1280px)");

  useEffect(() => {
    void useLibrary.getState().load();
    void useResearch.getState().load();
    useUi.getState().loadProviders().catch(() => undefined);
  }, []);

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader isLarge={isLarge} isWide={isWide} />
      <div className="flex min-h-0 flex-1">
        {isLarge && libraryOpen && (
          <aside aria-label="Library" className="bg-shelf flex w-80 shrink-0 flex-col border-r">
            <LibraryPanel />
          </aside>
        )}
        <main className="flex min-w-0 flex-1 flex-col">
          <ChatPanel />
        </main>
        {isWide && researchOpen && (
          <aside aria-label="Research brief" className="bg-shelf flex w-80 shrink-0 flex-col border-l">
            <ResearchPanel />
          </aside>
        )}
      </div>

      <Sheet open={mobilePanel !== null} onOpenChange={(open) => !open && setMobilePanel(null)}>
        <SheetContent side={mobilePanel === "research" ? "right" : "left"} className="bg-shelf flex w-[min(22rem,90vw)] flex-col gap-0 p-0">
          <SheetTitle className="sr-only">{mobilePanel === "research" ? "Research brief" : "Library"}</SheetTitle>
          {mobilePanel === "research" ? <ResearchPanel /> : <LibraryPanel />}
        </SheetContent>
      </Sheet>

      <ViewerPanel />
      <SettingsDialog />
      <AnalysisDialog />
    </div>
  );
}
