"use client";

import { KeyRound, PanelLeft, PanelRight, SquarePen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useChat } from "@/stores/chat";
import { useKeys } from "@/stores/keys";
import { useSettings } from "@/stores/settings";
import { useUi } from "@/stores/ui";
import { ThemeToggle } from "./ThemeToggle";

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={label} onClick={onClick}>
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export function AppHeader({ isLarge, isWide }: { isLarge: boolean; isWide: boolean }) {
  const togglePanel = useSettings((s) => s.togglePanel);
  const provider = useSettings((s) => s.provider);
  const hasKey = useKeys((s) => Boolean(s.keys[provider]));
  const serverKey = useUi((s) => s.providers?.server_key_available ?? false);
  const openSettings = useUi((s) => s.openSettings);
  const setMobilePanel = useUi((s) => s.setMobilePanel);
  const newChat = useChat((s) => s.newChat);
  const hasMessages = useChat((s) => s.messages.length > 0);

  return (
    <header className="flex h-14 shrink-0 items-center gap-1 border-b px-2 sm:px-3">
      <IconButton label="Library" onClick={() => (isLarge ? togglePanel("library") : setMobilePanel("library"))}>
        <PanelLeft />
      </IconButton>
      <span className="ml-1 font-serif text-lg font-semibold">PaperSense</span>
      <div className="ml-auto flex items-center gap-1">
        <Button variant="ghost" size="sm" onClick={() => void newChat()} disabled={!hasMessages}>
          <SquarePen /> <span className="hidden sm:inline">New chat</span>
        </Button>
        <Button variant={hasKey || serverKey ? "ghost" : "outline"} size="sm" onClick={() => openSettings("keys")}>
          <KeyRound /> <span className="hidden sm:inline">{hasKey ? "API keys" : "Add API key"}</span>
        </Button>
        <ThemeToggle />
        <IconButton label="Research brief" onClick={() => (isWide ? togglePanel("research") : setMobilePanel("research"))}>
          <PanelRight />
        </IconButton>
      </div>
    </header>
  );
}
