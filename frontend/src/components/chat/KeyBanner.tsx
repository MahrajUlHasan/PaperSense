"use client";

import { Button } from "@/components/ui/button";
import { useKeys } from "@/stores/keys";
import { useSettings } from "@/stores/settings";
import { useUi } from "@/stores/ui";

/** Shown above the question box until a key is set (unless the server has its own key). */
export function KeyBanner() {
  const provider = useSettings((s) => s.provider);
  const hasKey = useKeys((s) => Boolean(s.keys[provider]));
  const providers = useUi((s) => s.providers);
  const openSettings = useUi((s) => s.openSettings);
  if (hasKey || !providers || providers.server_key_available) return null;

  return (
    <div className="bg-highlight/35 mb-2 flex flex-wrap items-center justify-between gap-2 rounded-md px-3 py-2 text-sm">
      <span>Add a free API key to ask questions. It stays in this browser.</span>
      <div className="flex gap-1">
        <Button size="sm" variant="ghost" onClick={() => openSettings("guide")}>How to get one</Button>
        <Button size="sm" onClick={() => openSettings("keys")}>Add key</Button>
      </div>
    </div>
  );
}
